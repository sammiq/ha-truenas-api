"""DataUpdateCoordinator for ha_truenas_api."""

from __future__ import annotations

import asyncio
import logging
import time
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
        start_time = end_time = int(time.time() - 5.0)
        try:
            jobs = {
                "system.info": ("system.info", []),
                "update.status": ("update.status", []),
                "reporting.graph.cpu": (
                    "reporting.graph",
                    [
                        "cpu",
                        {
                            "start": start_time,
                            "end": end_time,
                        },
                    ],
                ),
                "reporting.graph.cputemp": (
                    "reporting.graph",
                    [
                        "cputemp",
                        {
                            "start": start_time,
                            "end": end_time,
                        },
                    ],
                ),
                "pool.query": (
                    "pool.query",
                    [[], {"select": ["name", "allocated", "free", "size"]}],
                ),
                "disk.temperatures": ("disk.temperatures", []),
                "reporting.graph.memory": (
                    "reporting.graph",
                    [
                        "memory",
                        {
                            "start": start_time,
                            "end": end_time,
                        },
                    ],
                ),
                "reporting.graph.arcsize": (
                    "reporting.graph",
                    [
                        "arcsize",
                        {
                            "start": start_time,
                            "end": end_time,
                        },
                    ],
                ),
            }

            # rather than calling these individually, do them all at once
            for job_key, (method, params) in jobs.items():
                future = asyncio.Future()
                self._pending_requests[job_key] = future
                await self.config_entry.runtime_data.client.send_message(
                    job_key, method, params
                )

            try:
                keys = list(self._pending_requests.keys())

                results = await asyncio.wait_for(
                    asyncio.gather(
                        *list(self._pending_requests.values()),
                        return_exceptions=True,
                    ),
                    timeout=10.0,  # 10 second timeout for all polls
                )

                # Update cache with results
                for index, job_key in enumerate(keys):
                    if not isinstance(results[index], Exception):
                        _LOGGER.debug("Updating cache for %s", job_key)
                        self._data_cache[job_key] = results[index]
                    else:
                        _LOGGER.error("Failed to get %s: %s", job_key, results[index])

            except TimeoutError:
                _LOGGER.warning("Timeout waiting for responses from TrueNAS")
                # Clean up pending requests
                for future in self._pending_requests.values():
                    future.cancel()
                self._pending_requests.clear()
                self._data_cache = {}

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
