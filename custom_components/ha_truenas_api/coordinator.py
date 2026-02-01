"""DataUpdateCoordinator for ha_truenas_api."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from .data import TrueNasConfigEntry

_LOGGER = logging.getLogger(__name__)


class TrueNasDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: TrueNasConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        name: str,
        update_interval: timedelta | None = None,
    ):
        super().__init__(
            hass,
            logger,
            name=name,
            update_interval=update_interval,
        )

        self._connection_ok = False

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
                return await self.config_entry.runtime_data.client.send_message(
                    "system.info", "system.info", []
                )
            except Exception as exception:
                raise UpdateFailed(exception) from exception
        else:
            _LOGGER.info("Connection not yet ready")

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
            _LOGGER.warning("WebSocket disconnected: %s", error)
            # Optionally mark entities as unavailable
            self.async_set_updated_data({})

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
                _LOGGER.warning("Failed to authenticate")
            else:
                _LOGGER.info("Authentication successful")
        elif is_error:
            _LOGGER.error("error returned from request: %s", msg_id, data)
        elif msg_id == "system.info":
            _LOGGER.debug("Got system.info data from websocket")
            self.async_set_updated_data(data)
        else:
            _LOGGER.error("unexpected data received %s:%s", msg_id, data)

    async def async_force_reconnect(self) -> None:
        """Manually trigger reconnection."""
        await self.config_entry.runtime_data.client.force_reconnect()

    async def async_shutdown(self) -> None:
        """Clean shutdown of WebSocket."""
        await self.config_entry.runtime_data.client.close()
