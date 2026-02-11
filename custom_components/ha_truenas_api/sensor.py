"""Sensor platform for ha_truenas_api."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfInformation,
    UnitOfTemperature,
    UnitOfTime,
)

from .entity import TrueNasEntity, find_data_item, property_from_path

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import TrueNasDataUpdateCoordinator
    from .data import TrueNasConfigEntry


@dataclass(frozen=True, kw_only=True)
class TrueNasSensorEntityDescription(SensorEntityDescription):
    """Describes TrueNAs sensor entities."""

    data_key: str
    data_match: dict[str, Any] | None = None
    item_key: str
    item_index: int | None = None


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
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:memory",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=2,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        data_key="system.info",
        item_key="physmem",
    ),
    TrueNasSensorEntityDescription(
        key="truenas_uptime_seconds",
        name="Uptime",
        icon="mdi:timer-outline",
        state_class=SensorStateClass.MEASUREMENT,
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
    ),
    TrueNasSensorEntityDescription(
        key="truenas_mem_free",
        name="Free Memory",
        device_class=SensorDeviceClass.DATA_SIZE,
        icon="mdi:memory",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=2,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        data_key="reporting.graph.memory",
        data_match={"name": "memory"},
        item_key="aggregations:mean:available",
    ),
    TrueNasSensorEntityDescription(
        key="truenas_arc_size",
        name="ZFS Cache Size",
        device_class=SensorDeviceClass.DATA_SIZE,
        icon="mdi:memory",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=2,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        data_key="reporting.graph.arcsize",
        data_match={"name": "arcsize"},
        item_key="aggregations:mean:size",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: TrueNasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = entry.runtime_data.coordinator

    await coordinator.async_config_entry_first_refresh()

    entities = []

    entities.extend(
        TrueNasSensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )

    # dynamically work out what cpu data is available
    cpu_data = coordinator.data.get("reporting.graph.cpu")
    if isinstance(cpu_data, list) and cpu_data:
        mean_map = property_from_path(cpu_data[0], "aggregations:mean")

        if isinstance(mean_map, dict):
            entities.extend(
                TrueNasSensor(
                    coordinator=coordinator,
                    entity_description=TrueNasSensorEntityDescription(
                        key=f"truenas_usage_{key}",
                        name=f"{key.upper()} Usage",
                        icon="mdi:cpu-64-bit",
                        native_unit_of_measurement=PERCENTAGE,
                        suggested_display_precision=0,
                        data_key="reporting.graph.cpu",
                        data_match={"name": "cpu"},
                        # should be largely irrelevant which I use, as its a single data point
                        item_key=f"aggregations:mean:{key}",
                    ),
                )
                for key in mean_map
            )

    # dynamically work out what temperature data is available
    cputemp_data = coordinator.data.get("reporting.graph.cputemp")
    if isinstance(cputemp_data, list) and cputemp_data:
        mean_map = property_from_path(cputemp_data[0], "aggregations:mean")

        if isinstance(mean_map, dict):
            entities.extend(
                TrueNasSensor(
                    coordinator=coordinator,
                    entity_description=TrueNasSensorEntityDescription(
                        key=f"truenas_temperature_{key}",
                        name=f"{key.upper()} Temperature",
                        icon="mdi:thermometer",
                        device_class=SensorDeviceClass.TEMPERATURE,
                        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                        state_class=SensorStateClass.MEASUREMENT,
                        suggested_display_precision=0,
                        data_key="reporting.graph.cputemp",
                        data_match={"name": "cputemp"},
                        # should be largely irrelevant which I use, as its a single data point
                        item_key=f"aggregations:mean:{key}",
                    ),
                )
                for key in mean_map
            )

    # dynamically work out what pool data is available
    pool_data = coordinator.data.get("pool.query")
    if isinstance(pool_data, list):
        for pool in pool_data:
            pool_name = pool.get("name")
            if not pool_name:
                continue
            entities.extend(
                [
                    TrueNasSensor(
                        coordinator=coordinator,
                        entity_description=TrueNasSensorEntityDescription(
                            key=f"truenas_pool_free_{pool_name}",
                            name=f"{pool_name} Pool Free Space",
                            icon="mdi:harddisk",
                            device_class=SensorDeviceClass.DATA_SIZE,
                            native_unit_of_measurement=UnitOfInformation.BYTES,
                            suggested_display_precision=2,
                            suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
                            data_key="pool.query",
                            data_match={"name": pool_name},
                            item_key="free",
                        ),
                    ),
                    TrueNasSensor(
                        coordinator=coordinator,
                        entity_description=TrueNasSensorEntityDescription(
                            key=f"truenas_pool_allocated_{pool_name}",
                            name=f"{pool_name} Pool Allocated Space",
                            icon="mdi:harddisk",
                            device_class=SensorDeviceClass.DATA_SIZE,
                            native_unit_of_measurement=UnitOfInformation.BYTES,
                            suggested_display_precision=2,
                            suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
                            data_key="pool.query",
                            data_match={"name": pool_name},
                            item_key="allocated",
                        ),
                    ),
                    TrueNasSensor(
                        coordinator=coordinator,
                        entity_description=TrueNasSensorEntityDescription(
                            key=f"truenas_pool_size_{pool_name}",
                            name=f"{pool_name} Pool Size",
                            icon="mdi:harddisk",
                            device_class=SensorDeviceClass.DATA_SIZE,
                            native_unit_of_measurement=UnitOfInformation.BYTES,
                            suggested_display_precision=2,
                            suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
                            data_key="pool.query",
                            data_match={"name": pool_name},
                            item_key="size",
                        ),
                    ),
                ]
            )

    # dynamically work out what temperature data is available
    disktemp_data = coordinator.data.get("disk.temperatures")
    if isinstance(disktemp_data, dict):
        entities.extend(
            TrueNasSensor(
                coordinator=coordinator,
                entity_description=TrueNasSensorEntityDescription(
                    key=f"truenas_disk_temperature_{key}",
                    name=f"{key} Disk Temperature",
                    icon="mdi:thermometer",
                    device_class=SensorDeviceClass.TEMPERATURE,
                    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                    state_class=SensorStateClass.MEASUREMENT,
                    suggested_display_precision=0,
                    data_key="disk.temperatures",
                    item_key=key,
                ),
            )
            for key in disktemp_data
        )

    async_add_entities(entities)


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
        self.data_match = entity_description.data_match
        self.item_key = entity_description.item_key
        self.item_index = entity_description.item_index

    @property
    def native_value(self) -> str | int | float | None:
        """Return the native value of the sensor."""
        if self.coordinator.data is None:
            return None

        data = self.coordinator.data.get(self.data_key)
        if self.data_match is not None:
            data = find_data_item(data, self.data_match)

        data = property_from_path(data, self.item_key)
        if self.item_index is not None and isinstance(data, list):
            data = data[self.item_index]

        return data
