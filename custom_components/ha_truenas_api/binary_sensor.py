"""Binary sensor platform for ha_truenas_api."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .entity import TrueNasEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import TrueNasDataUpdateCoordinator
    from .data import TrueNasConfigEntry

ENTITY_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="ha_truenas_api",
        name="TrueNAS API Binary Sensor",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
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
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.get("title", "") == "foo"
