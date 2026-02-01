"""Sensor platform for ha_truenas_api."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import UnitOfInformation, UnitOfTime

from .entity import TrueNasEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import TrueNasDataUpdateCoordinator
    from .data import TrueNasConfigEntry


@dataclass(frozen=True, kw_only=True)
class TrueNasSensorEntityDescription(SensorEntityDescription):
    """Describes TrueNAs sensor entities."""

    data_key: str
    scale: float | None = None


# Note that you cannot extend SensorEntityDescription or HA gets grumpy, making this noodly tuple thing
# the easiest way for the moment to work around it.
ENTITY_DESCRIPTIONS = (
    TrueNasSensorEntityDescription(
        key="truenas_version",
        name="TrueNAS Version",
        icon="mdi:package-up",
        data_key="version",
    ),
    TrueNasSensorEntityDescription(
        key="truenas_physmem",
        name="Physical Memory",
        icon="mdi:memory",
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=2,
        data_key="physmem",
        scale=1000000.0,
    ),
    TrueNasSensorEntityDescription(
        key="truenas_uptime_seconds",
        name="Uptime",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        data_key="uptime_seconds",
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
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class TrueNasSensor(TrueNasEntity, SensorEntity):
    """ha_truenas_api Sensor class."""

    def __init__(
        self,
        coordinator: TrueNasDataUpdateCoordinator,
        entity_description: TrueNasSensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(entity_description.key, coordinator)
        self.entity_description = entity_description
        self.data_key = entity_description.data_key
        self.scale = entity_description.scale

    @property
    def native_value(self) -> str | int | float | None:
        """Return the native value of the sensor."""
        if self.coordinator.data is None:
            return None
        raw_value = self.coordinator.data.get(self.data_key)
        if raw_value is None or self.scale is None:
            return raw_value
        try:
            return float(raw_value) / self.scale
        except (ValueError, TypeError):
            return None
