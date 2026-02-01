"""DataUpdateCoordinator for ha_truenas_api."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from .data import TrueNasConfigEntry

_LOGGER = logging.getLogger(__name__)


class TrueNasDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: TrueNasConfigEntry

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
        try:
            return await self.config_entry.runtime_data.client.send_message(
                "system.info", "system.info", []
            )
        except Exception as exception:
            raise UpdateFailed(exception) from exception

    async def _handle_connection_change(
        self,
        is_connected: bool,
        error: str | None,
    ) -> None:
        """Handle WebSocket connection state changes."""
        self._connection_ok = is_connected

        if is_connected:
            _LOGGER.info("WebSocket connected")
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
        if not self._connection_ok:
            return

        # Update coordinator data
        if is_error:
            _LOGGER.error("error returned from request: %s", data)
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
