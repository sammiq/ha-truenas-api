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
    _MAX_LOGIN_RETRIES = 10

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
        self._pending_requests = {}

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
        # wait for connection and login to happen before sending commands
        retry = 0
        while (
            not (self._connection_ok and self._logged_in)
            and retry < self._MAX_LOGIN_RETRIES
        ):
            retry += 1
            await asyncio.sleep(1)

        if not (self._connection_ok and self._logged_in):
            msg = "Connection or login to server failed"
            raise TimeoutError(msg)

        _LOGGER.debug("Requesting data from websocket")
        try:
            future_a = asyncio.Future()
            self._pending_requests["system.info"] = future_a
            await self.config_entry.runtime_data.client.send_message(
                "system.info", "system.info", []
            )

            future_b = asyncio.Future()
            self._pending_requests["update.status"] = future_b
            await self.config_entry.runtime_data.client.send_message(
                "update.status", "update.status", []
            )

            future_c = asyncio.Future()
            self._pending_requests["disk.details"] = future_c
            await self.config_entry.runtime_data.client.send_message(
                "disk.details",
                "disk.details",
                [{"join_partitions": False, "type": "USED"}],
            )

            try:
                system_info, update_status, disk_details = await asyncio.wait_for(
                    asyncio.gather(
                        future_a, future_b, future_c, return_exceptions=True
                    ),
                    timeout=10.0,  # 10 second timeout for all polls
                )

                # Update cache with results
                if not isinstance(system_info, Exception):
                    self._data_cache["system.info"] = system_info
                else:
                    _LOGGER.error("Failed to get system.info: %s", system_info)

                if not isinstance(update_status, Exception):
                    self._data_cache["update.status"] = update_status
                else:
                    _LOGGER.error("Failed to get update.status: %s", update_status)

                if not isinstance(disk_details, Exception):
                    self._data_cache["disk.details"] = disk_details
                else:
                    _LOGGER.error("Failed to get disk.details: %s", disk_details)

            except TimeoutError:
                _LOGGER.warning("Timeout waiting for responses from TrueNAS")
                # Clean up pending requests
                self._pending_requests.pop("system.info", None)
                self._pending_requests.pop("update.status", None)
                self._pending_requests.pop("disk.details", None)

        except Exception as exception:
            _LOGGER.exception("Error during update")
            raise UpdateFailed(exception) from exception

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
                self._logged_in = False
                _LOGGER.exception("failed to send login")
        else:
            self._logged_in = False
            _LOGGER.warning("WebSocket disconnected: %s", error)

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
            return

        if is_error:
            _LOGGER.error("error returned from request: %s error: %s", msg_id, data)
            if msg_id in self._pending_requests:
                future = self._pending_requests.pop(msg_id)
                if not future.done():
                    future.set_exception(Exception(f"TrueNAS error: {data}"))
            return

        _LOGGER.debug("Got %s data from websocket", msg_id)
        if msg_id in self._pending_requests:
            future = self._pending_requests.pop(msg_id)
            if not future.done():
                future.set_result(data)
        else:
            # Unsolicited message
            self._data_cache[msg_id] = data
            self.async_set_updated_data(self._data_cache)

    async def async_force_reconnect(self) -> None:
        """Manually trigger reconnection."""
        await self.config_entry.runtime_data.client.force_reconnect()

    async def async_shutdown(self) -> None:
        """Clean shutdown of WebSocket."""
        await self.config_entry.runtime_data.client.close()
