"""Websocket implementation for ha_truenas_api."""

import asyncio
import contextlib
import json
import logging
from collections.abc import Awaitable, Callable
from urllib.parse import urlunparse

import aiohttp

_LOGGER = logging.getLogger(__name__)


class WebSocketClient:
    """WebSocket client for maintaining connection and handling messages."""

    def __init__(
        self,
        address: str,
        apikey: str,
        max_retries: int | None = None,  # None = infinite retries
        initial_retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
        backoff_factor: float = 2.0,
    ) -> None:
        """
        Initialize the WebSocketClient with the target URL.

        Args:
            address (str): The address to connect to.
            apikey (str): The API Key to use for authorization.

        """
        self.url = urlunparse(("wss", address, "/api/current"))
        self.apikey = apikey
        self.session = None
        self.ws = None
        self._listen_task = None
        self._reconnect_task = None
        self._message_handlers: list[
            Callable[[int | str, dict, bool], Awaitable[None]]
        ] = []
        self._connection_handlers: list[
            Callable[[bool, str | None], Awaitable[None]]
        ] = []
        self._should_reconnect = True
        self._is_connected = False

        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay
        self.backoff_factor = backoff_factor
        self._retry_count = 0

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        return self._is_connected and self.ws is not None and not self.ws.closed

    async def connect(self) -> None:
        """Establish WebSocket connection with retry logic."""
        self._should_reconnect = True
        await self._connect_with_retry()

    async def _connect_with_retry(self) -> None:
        """Connect with exponential backoff (internal method)."""
        if self.session is None:
            self.session = aiohttp.ClientSession()

        while self._should_reconnect:
            try:
                # Check if we've exceeded max retries
                if (
                    self.max_retries is not None
                    and self._retry_count >= self.max_retries
                ):
                    _LOGGER.error(
                        "Max retries (%s) exceeded, giving up", self.max_retries
                    )
                    await self._notify_connection_handlers(
                        False,
                        "Max retries exceeded",
                    )
                    return

                # Attempt connection
                _LOGGER.info(
                    "Connecting to WebSocket at %s (attempt %s)",
                    self.url,
                    self._retry_count + 1,
                )

                timeout = aiohttp.ClientWSTimeout(ws_receive=10.0, ws_close=10.0)
                self.ws = await self.session.ws_connect(
                    self.url,
                    heartbeat=30,  # Send ping every 30 seconds to keep connection alive
                    timeout=timeout,
                )

                _LOGGER.info("WebSocket connected successfully")
                self._is_connected = True
                self._retry_count = 0  # Reset retry count on successful connection

                # Notify connection handlers
                await self._notify_connection_handlers(True, None)

                # Start listening for messages
                self._listen_task = asyncio.create_task(self._listen())

                # Wait for the listen task to complete (connection closed)
                await self._listen_task

            except (TimeoutError, aiohttp.ClientError) as e:
                _LOGGER.warning("Connection failed: %s", e)
                self._is_connected = False
                await self._notify_connection_handlers(False, str(e))

                if self._should_reconnect:
                    # Calculate delay with exponential backoff
                    delay = min(
                        self.initial_retry_delay
                        * (self.backoff_factor**self._retry_count),
                        self.max_retry_delay,
                    )

                    _LOGGER.info("Reconnecting in %.1f seconds...", delay)
                    self._retry_count += 1

                    try:
                        await asyncio.sleep(delay)
                    except asyncio.CancelledError:
                        _LOGGER.info("Reconnection cancelled")
                        return
                else:
                    return

            except Exception as e:
                _LOGGER.exception("Unexpected error during connection")
                self._is_connected = False
                await self._notify_connection_handlers(False, str(e))

                if self._should_reconnect:
                    await asyncio.sleep(self.initial_retry_delay)
                else:
                    return

    async def _listen(self) -> None:
        """Listen for incoming messages continuously."""
        try:
            if self.ws is None:
                _LOGGER.error("WebSocket is not connected.")
                return

            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        _LOGGER.debug("Received: %s", data)
                        msg_id = data.get("id")
                        result = data.get("result")
                        error = data.get("error")

                        if (msg_id is None) or (result is None and error is None):
                            _LOGGER.error("Invalid payload %s", data)
                        else:
                            is_error: bool = error is not None
                            payload = error if is_error else result

                            # Call all registered handlers
                            for handler in self._message_handlers:
                                try:
                                    await handler(msg_id, payload, is_error)
                                except Exception:
                                    _LOGGER.exception("Handler error")
                    except json.JSONDecodeError:
                        _LOGGER.exception("Failed to decode JSON")

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.error("WebSocket error: %s", self.ws.exception())
                    break

                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    _LOGGER.info("WebSocket closed by server")
                    break

                elif msg.type == aiohttp.WSMsgType.PING:
                    _LOGGER.debug("Received ping")

                elif msg.type == aiohttp.WSMsgType.PONG:
                    _LOGGER.debug("Received pong")

        except asyncio.CancelledError:
            _LOGGER.debug("Listen task cancelled")
            raise
        except Exception:
            _LOGGER.exception("Listen error")
        finally:
            self._is_connected = False
            _LOGGER.info("Listen loop ended, connection lost")

    async def send_message(self, msg_id: int | str, method: str, params: list) -> None:
        """Send JSON message to WebSocket."""
        if self.ws is None or self.ws.closed:
            msg = "WebSocket not connected"
            raise ConnectionError(msg)

        data = {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}
        await self.ws.send_json(data)
        _LOGGER.debug("Sent: %s", data)

    def add_message_handler(
        self, handler: Callable[[int | str, dict, bool], Awaitable[None]]
    ) -> None:
        """
        Register a callback for handling incoming messages.

        The handler receives: (msg_id: int | str, payload: dict, is_error: bool)
        """
        self._message_handlers.append(handler)

    def add_connection_handler(
        self, handler: Callable[[bool, str | None], Awaitable[None]]
    ) -> None:
        """
        Register a callback for connection state changes.

        Handler receives: (is_connected: bool, error: Optional[str])
        """
        self._connection_handlers.append(handler)

    async def _notify_connection_handlers(
        self,
        is_connected: bool,
        error: str | None,
    ) -> None:
        """Notify all connection handlers of state change."""
        for handler in self._connection_handlers:
            try:
                await handler(is_connected, error)
            except Exception:
                _LOGGER.exception("Connection handler error")

    async def close(self) -> None:
        """Close WebSocket connection and cleanup."""
        if self._listen_task:
            self._listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listen_task

        if self.ws:
            await self.ws.close()

        if self.session:
            await self.session.close()

        _LOGGER.info("WebSocket closed")

    async def force_reconnect(self) -> None:
        """Force a reconnection (useful for manual retry)."""
        if self.ws is not None and not self.ws.closed:
            await self.ws.close()
