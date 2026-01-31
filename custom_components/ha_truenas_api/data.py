"""Custom types for ha_truenas_api."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import TrueNasApiClient
    from .coordinator import TrueNasDataUpdateCoordinator


type TrueNasConfigEntry = ConfigEntry[TrueNasData]


@dataclass
class TrueNasData:
    """Data for the TrueNas integration."""

    client: TrueNasApiClient
    coordinator: TrueNasDataUpdateCoordinator
    integration: Integration
