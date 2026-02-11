"""TrueNasEntity class."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import TrueNasDataUpdateCoordinator


def property_from_path(data: dict[str, Any] | None, path: str) -> Any | None:
    """Navigate to a property given a set of keys to traverse."""
    parts = path.split(":")

    this_data = data
    for part in parts:
        if this_data is None:
            return None
        this_data = this_data.get(part)
    return this_data


def find_data_item(
    data: Any,
    match: dict[str, Any] | None = None,
) -> Any:
    """
    Find an item in data using either a match dict or an index.

    Args:
        data: The data to search (list or dict)
        match: Dictionary of key-value pairs to match against list items

    Returns:
        The matched item, or None if not found

    """
    if match:
        if isinstance(data, list):
            # Find first item where all match criteria are met
            for item in data:
                if isinstance(item, dict) and all(
                    item.get(k) == v for k, v in match.items()
                ):
                    return item
        elif isinstance(data, dict) and all(data.get(k) == v for k, v in match.items()):
            return data

    return None


class TrueNasEntity(CoordinatorEntity[TrueNasDataUpdateCoordinator]):
    """TrueNasEntity class."""

    def __init__(
        self, unique_id: str, coordinator: TrueNasDataUpdateCoordinator
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    coordinator.config_entry.domain,
                    coordinator.config_entry.entry_id,
                ),
            },
        )
