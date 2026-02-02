"""Binary sensor platform for ha_truenas_api."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.update import (
    UpdateEntity,
    UpdateEntityDescription,
)
from homeassistant.const import EntityCategory

from .entity import TrueNasEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import TrueNasDataUpdateCoordinator
    from .data import TrueNasConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: TrueNasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the update platform."""
    update_desc = UpdateEntityDescription(
        key="truenas_version_update",
        name="Version Update",
        entity_category=EntityCategory.CONFIG,
    )

    async_add_entities(
        [
            TrueNasUpdateEntity(
                coordinator=entry.runtime_data.coordinator,
                entity_description=update_desc,
            )
        ]
    )


class TrueNasUpdateEntity(TrueNasEntity, UpdateEntity):
    """ha_truenas_api update class."""

    def __init__(
        self,
        coordinator: TrueNasDataUpdateCoordinator,
        entity_description: UpdateEntityDescription,
    ) -> None:
        """Initialize the update class."""
        super().__init__(entity_description.key, coordinator)
        self.entity_description = entity_description

    def _property_from_path(self, data: dict[str, Any], path: str) -> Any | None:
        parts = path.split(":")

        this_data = data
        for part in parts:
            this_data = this_data.get(part)
            if this_data is None:
                return None
        return this_data

    @property
    def current_version(self) -> str | None:
        """Return the latest version available."""
        if self.coordinator.data is None:
            return None
        return self._property_from_path(
            self.coordinator.data,
            "system.info:version",
        )

    @property
    def latest_version(self) -> str | None:
        """Return the latest version available."""
        if self.coordinator.data is None:
            return None
        return self._property_from_path(
            self.coordinator.data,
            "update.status:status:new_version:version",
        )

    @property
    def release_url(self) -> str | None:
        """Return the release notes of the latest version."""
        if self.coordinator.data is None:
            return None
        return self._property_from_path(
            self.coordinator.data,
            "update.status:status:new_version:release_notes_url",
        )

    @property
    def in_progress(self) -> bool | None:
        """Return whether update is in progress."""
        if self.coordinator.data is None:
            return None
        return (
            self._property_from_path(
                self.coordinator.data,
                "update.status:update_download_progress",
            )
            is not None
        )

    @property
    def update_percentage(self) -> float | None:
        """Return percentage of update in progress."""
        if self.coordinator.data is None:
            return None
        return self._property_from_path(
            self.coordinator.data,
            "update.status:update_download_progress:percent",
        )
