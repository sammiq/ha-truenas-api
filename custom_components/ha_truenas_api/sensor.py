"""Sensor platform for ha_truenas_api."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfInformation,
    UnitOfTime,
)

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
    item_key: str
    scale: float | None = None
    index: int | None = None


ENTITY_DESCRIPTIONS = (
    TrueNasSensorEntityDescription(
        key="truenas_version",
        name="TrueNAS Version",
        icon="mdi:package-up",
        entity_category=EntityCategory.DIAGNOSTIC,
        data_key="system.info",
        item_key="version",
    ),
    TrueNasSensorEntityDescription(
        key="truenas_physmem",
        name="Physical Memory",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:memory",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=2,
        data_key="system.info",
        item_key="physmem",
        scale=1000000000.0,
    ),
    TrueNasSensorEntityDescription(
        key="truenas_uptime_seconds",
        name="Uptime",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        data_key="system.info",
        item_key="uptime_seconds",
    ),
    TrueNasSensorEntityDescription(
        key="truenas_logical_cores",
        name="Logical Cores",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:developer-board",
        data_key="system.info",
        item_key="cores",
    ),
    TrueNasSensorEntityDescription(
        key="truenas_physical_cores",
        name="Physical Cores",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:developer-board",
        data_key="system.info",
        item_key="physical_cores",
    ),
    TrueNasSensorEntityDescription(
        key="truenas_load_avg_1min",
        name="1 minute Load Average",
        icon="mdi:equalizer",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        data_key="system.info",
        item_key="loadavg",
        index=0,
        scale=1 / 100.0,
    ),
    TrueNasSensorEntityDescription(
        key="truenas_load_avg_5min",
        name="5 minute Load Average",
        icon="mdi:equalizer",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        data_key="system.info",
        item_key="loadavg",
        index=1,
        scale=1 / 100.0,
    ),
    TrueNasSensorEntityDescription(
        key="truenas_load_avg_15min",
        name="15 minute Load Average",
        icon="mdi:equalizer",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        data_key="system.info",
        item_key="loadavg",
        index=2,
        scale=1 / 100.0,
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
        self.item_key = entity_description.item_key
        self.scale = entity_description.scale
        self.index = entity_description.index

    @property
    def native_value(self) -> str | int | float | None:
        """Return the native value of the sensor."""
        if self.coordinator.data is None:
            return None
        data = self.coordinator.data.get(self.data_key)
        if data is None:
            return None
        raw_value = data.get(self.item_key)
        if raw_value is None:
            return None
        if self.index is not None and isinstance(raw_value, list):
            raw_value = raw_value[self.index]
        if raw_value is None or self.scale is None:
            return raw_value
        try:
            return float(raw_value) / self.scale
        except (ValueError, TypeError):
            return None
