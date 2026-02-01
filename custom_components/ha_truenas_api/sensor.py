"""Sensor platform for ha_truenas_api."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription

from .entity import TrueNasEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import TrueNasDataUpdateCoordinator
    from .data import TrueNasConfigEntry


ENTITY_DESCRIPTIONS = (
    (
        SensorEntityDescription(
            key="ha_truenas_api",
            name="TrueNAS Version",
            icon="mdi:package-up",
        ),
        "version",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: TrueNasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        TrueNasSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
            data_key=data_key,
        )
        for (entity_description, data_key) in ENTITY_DESCRIPTIONS
    )


class TrueNasSensor(TrueNasEntity, SensorEntity):
    """ha_truenas_api Sensor class."""

    def __init__(
        self,
        coordinator: TrueNasDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
        data_key: str,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self.data_key = data_key

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        if self.coordinator.data is None:
            return None
        else:
            return self.coordinator.data.get(self.data_key)
