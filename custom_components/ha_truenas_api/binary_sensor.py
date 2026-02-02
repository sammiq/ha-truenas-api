"""Binary sensor platform for ha_truenas_api."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

from .entity import TrueNasEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import TrueNasDataUpdateCoordinator
    from .data import TrueNasConfigEntry


@dataclass(frozen=True, kw_only=True)
class TrueNasBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes TrueNAS binary sensor entities."""

    data_key: str
    item_key: str


ENTITY_DESCRIPTIONS = (
    TrueNasBinarySensorEntityDescription(
        key="truenas_ecc_memory",
        name="ECC Memory",
        entity_category=EntityCategory.DIAGNOSTIC,
        data_key="system.info",
        item_key="ecc_memory",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: TrueNasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    async_add_entities(
        TrueNasBinarySensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class TrueNasBinarySensor(TrueNasEntity, BinarySensorEntity):
    """ha_truenas_api binary_sensor class."""

    def __init__(
        self,
        coordinator: TrueNasDataUpdateCoordinator,
        entity_description: TrueNasBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(entity_description.key, coordinator)
        self.entity_description = entity_description
        self.data_key = entity_description.data_key
        self.item_key = entity_description.item_key

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary_sensor is on."""
        if self.coordinator.data is None:
            return None
        data = self.coordinator.data.get(self.data_key)
        if data is None:
            return None
        return data.get(self.item_key)
