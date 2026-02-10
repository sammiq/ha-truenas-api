"""Sensor platform for ha_truenas_api."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfInformation,
    UnitOfTemperature,
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
    data_index: int | None = None
    item_key: str
    item_index: int | None = None
    scale: float | None = None


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
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        data_key="system.info",
        item_key="uptime_seconds",
    ),
    TrueNasSensorEntityDescription(
        key="truenas_logical_cores",
        name="Logical Cores",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        icon="mdi:developer-board",
        data_key="system.info",
        item_key="cores",
    ),
    TrueNasSensorEntityDescription(
        key="truenas_physical_cores",
        name="Physical Cores",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        icon="mdi:developer-board",
        data_key="system.info",
        item_key="physical_cores",
    ),
    TrueNasSensorEntityDescription(
        key="truenas_load_avg_1min",
        name="1 minute Load Average",
        icon="mdi:equalizer",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        data_key="system.info",
        item_key="loadavg",
        item_index=0,
        scale=1.0,
    ),
    TrueNasSensorEntityDescription(
        key="truenas_load_avg_5min",
        name="5 minute Load Average",
        icon="mdi:equalizer",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        data_key="system.info",
        item_key="loadavg",
        item_index=1,
        scale=1.0,
    ),
    TrueNasSensorEntityDescription(
        key="truenas_load_avg_15min",
        name="15 minute Load Average",
        icon="mdi:equalizer",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        data_key="system.info",
        item_key="loadavg",
        item_index=2,
        scale=1.0,
    ),
    TrueNasSensorEntityDescription(
        key="truenas_cpu_temperature",
        name="CPU Temperature",
        icon="mdi:equalizer",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=0,
        data_key="reporting.graph.cputemp",
        data_index=0,
        # should be largely irrelevant which I use, as its a single data point
        item_key="aggregations:mean:cpu",
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
        self.data_index = entity_description.data_index
        self.item_key = entity_description.item_key
        self.item_index = entity_description.item_index
        self.scale = entity_description.scale

    @property
    def unique_id(self) -> str:
        return f"{self.coordinator.config_entry.entry_id}_{self.entity_description.key}"

    @property
    def native_value(self) -> str | int | float | None:
        """Return the native value of the sensor."""
        if self.coordinator.data is None:
            return None
        data = self.coordinator.data.get(self.data_key)

        if self.data_index is not None and isinstance(data, list):
            data = data[self.data_index]

        data = self._property_from_path(data, self.item_key)

        if self.item_index is not None and isinstance(data, list):
            data = data[self.item_index]

        if data is None or self.scale is None:
            return data
        try:
            return float(data) / self.scale
        except (ValueError, TypeError):
            return None
