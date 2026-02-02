"""DataUpdateCoordinator for ha_truenas_api."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from datetime import timedelta

    from homeassistant.core import HomeAssistant

    from .data import TrueNasConfigEntry

_LOGGER = logging.getLogger(__name__)


class TrueNasDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: TrueNasConfigEntry
    _MAX_LOGIN_RETRIES = 5

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        name: str,
        update_interval: timedelta | None = None,
    ) -> None:
        """Initialize the TrueNasDataUpdateCoordinator."""
        super().__init__(
            hass,
            logger,
            name=name,
            update_interval=update_interval,
        )

        self._connection_ok = False
        self._logged_in = False
        self._data_cache = {}

    async def _async_setup(self) -> None:
        """Set up the WebSocket connection."""
        # Register handler for incoming messages
        self.config_entry.runtime_data.client.add_message_handler(self._handle_message)
        self.config_entry.runtime_data.client.add_connection_handler(
            self._handle_connection_change
        )

        await self.config_entry.runtime_data.client.connect()

        _LOGGER.info("WebSocket coordinator setup complete")

    async def _async_update_data(self) -> Any:
        """Update data via library."""
        _LOGGER.debug("Requesting data from websocket")
        if self._connection_ok:
            try:
                # wait for login to happen before sending commands
                retry = 0
                while (
                    self._connection_ok
                    and not self._logged_in
                    and retry < self._MAX_LOGIN_RETRIES
                ):
                    retry += 1
                    await asyncio.sleep(1)

                if self._logged_in:
                    await self.config_entry.runtime_data.client.send_message(
                        "system.info", "system.info", []
                    )
                    await self.config_entry.runtime_data.client.send_message(
                        "update.status", "update.status", []
                    )

            except Exception as exception:
                raise UpdateFailed(exception) from exception
        else:
            _LOGGER.info("Connection not yet ready")
        # return the latest data we have, as updates will be async
        return self._data_cache

    async def _handle_connection_change(
        self,
        is_connected: bool,
        error: str | None,
    ) -> None:
        """Handle WebSocket connection state changes."""
        self._connection_ok = is_connected

        if is_connected:
            _LOGGER.info("WebSocket connected")
            try:
                await self.config_entry.runtime_data.client.send_login(
                    "auth.login_with_api_key"
                )
            except Exception:
                _LOGGER.exception("failed to send login")
        else:
            self._logged_in = False
            _LOGGER.warning("WebSocket disconnected: %s", error)
            # HMMM: do I want to mark entities as unavailable?
            # self._data_cache = {}
            # self.async_set_updated_data(self._data_cache)

    async def _handle_message(
        self,
        msg_id: int | str,
        data: dict,
        is_error: bool,
    ) -> None:
        """Handle incoming WebSocket message."""
        # Update coordinator data
        if msg_id == "auth.login_with_api_key":
            if is_error:
                self._logged_in = False
                _LOGGER.warning("Failed to authenticate")
            else:
                self._logged_in = True
                _LOGGER.info("Authentication successful")
        elif is_error:
            _LOGGER.error("error returned from request: %s error: %s", msg_id, data)
        else:
            _LOGGER.debug("Got %s data from websocket", msg_id)
            self._data_cache[msg_id] = data
            # HMMM: do I want to do this here or just wait for the update date call?
            # self.async_set_updated_data(self._data_cache)
            self.data = self._data_cache

    async def async_force_reconnect(self) -> None:
        """Manually trigger reconnection."""
        await self.config_entry.runtime_data.client.force_reconnect()

    async def async_shutdown(self) -> None:
        """Clean shutdown of WebSocket."""
        await self.config_entry.runtime_data.client.close()
