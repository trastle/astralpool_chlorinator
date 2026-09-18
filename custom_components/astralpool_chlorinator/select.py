"""Platform for select integration."""
from __future__ import annotations

import logging
import asyncio
import time

from pychlorinator import chlorinator_parsers
from homeassistant.components.select import (
    SelectEntity,
)
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .coordinator import ChlorinatorDataUpdateCoordinator
from .models import ChlorinatorData
from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)

# How long an optimistic value is trusted over the coordinator's own data
# before giving up on it - see _OptimisticOptionMixin.
_OPTIMISTIC_OPTION_TIMEOUT_SECONDS = 30


class _OptimisticOptionMixin:
    """Shows the just-selected option immediately after a write succeeds,
    instead of the pre-write value the coordinator hasn't caught up to yet.
    Without this, picking a new option flickers back to the old one for
    the few seconds it takes the Pi bridge to write, re-poll, and
    republish state, then jumps to the real value once that arrives (seen
    live 2026-09-18 - see home-assistant/pool/session-notes-2026-09-18.md
    in the docs repo). Expires after _OPTIMISTIC_OPTION_TIMEOUT_SECONDS
    even without confirmation, so a write that silently didn't take (or
    got overtaken by something else) doesn't leave the entity stuck
    showing a wrong value indefinitely - falls back to whatever the
    coordinator actually reports instead."""

    _optimistic_option: str | None = None
    _optimistic_option_expires: float = 0.0

    def _resolve_optimistic(self, actual: str) -> str:
        if self._optimistic_option is not None:
            if (
                actual == self._optimistic_option
                or time.monotonic() > self._optimistic_option_expires
            ):
                self._optimistic_option = None
            else:
                return self._optimistic_option
        return actual

    def _set_optimistic(self, option: str) -> None:
        self._optimistic_option = option
        self._optimistic_option_expires = time.monotonic() + _OPTIMISTIC_OPTION_TIMEOUT_SECONDS
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Chlorinator from a config entry."""
    data: ChlorinatorData = hass.data[DOMAIN][entry.entry_id]
    entities = [
        ChlorinatorModeSelect(data.coordinator),
        ChlorinatorSpeedSelect(data.coordinator),
        ChlorinatorDefaultManualSpeedSelect(data.coordinator),
    ]
    async_add_entities(entities)


class ChlorinatorModeSelect(
    _OptimisticOptionMixin, CoordinatorEntity[ChlorinatorDataUpdateCoordinator], SelectEntity
):
    """Representation of a Clorinator Select entity."""

    _attr_icon = "mdi:power"
    _attr_options = ["Off", "Auto", "Manual"]
    _attr_name = "Mode"
    _attr_unique_id = "pool01_mode_select"

    def __init__(
        self,
        coordinator: ChlorinatorDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo | None:
        return {
            "identifiers": {(DOMAIN, "POOL01")},
            "name": "POOL01",
            "model": "Viron eQuilibrium",
            "manufacturer": "Astral Pool",
        }

    @property
    def current_option(self):
        mode = self.coordinator.data.get("mode")
        if mode is chlorinator_parsers.Modes.Off:
            actual = "Off"
        elif mode is chlorinator_parsers.Modes.Auto:
            actual = "Auto"
        else:
            actual = "Manual"
        return self._resolve_optimistic(actual)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option"""
        if option == "Off":
            action = chlorinator_parsers.ChlorinatorActions.Off
        elif option == "Auto":
            action = chlorinator_parsers.ChlorinatorActions.Auto
        elif option == "Manual":
            action = chlorinator_parsers.ChlorinatorActions.Manual
        else:
            action = chlorinator_parsers.ChlorinatorActions.NoAction
        async with self.coordinator._ble_lock:
            await self.coordinator.chlorinator.async_write_action(action)
        self._set_optimistic(option)
        await asyncio.sleep(2)
        await self.coordinator.async_request_refresh()

class ChlorinatorSpeedSelect(
    _OptimisticOptionMixin, CoordinatorEntity[ChlorinatorDataUpdateCoordinator], SelectEntity
):
    """Representation of a Clorinator Select entity."""

    _attr_icon = "mdi:pump"
    _attr_options = ["Low", "Medium", "High"]
    _attr_name = "Pump Speed"
    _attr_unique_id = "pool01_speed_select"

    def __init__(
        self,
        coordinator: ChlorinatorDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo | None:
        return {
            "identifiers": {(DOMAIN, "POOL01")},
            "name": "POOL01",
            "model": "Viron eQuilibrium",
            "manufacturer": "Astral Pool",
        }

    @property
    def current_option(self):
        speed = self.coordinator.data.get("pump_speed")
        if speed is chlorinator_parsers.SpeedLevels.Low:
            actual = "Low"
        elif speed is chlorinator_parsers.SpeedLevels.Medium:
            actual = "Medium"
        elif speed is chlorinator_parsers.SpeedLevels.AI:
            actual = "AI"
        else:
            actual = "High"
        return self._resolve_optimistic(actual)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option"""
        if option == "Low":
            action = chlorinator_parsers.ChlorinatorActions.Low
        elif option == "Medium":
            action = chlorinator_parsers.ChlorinatorActions.Medium
        elif option == "High":
            action = chlorinator_parsers.ChlorinatorActions.High
        else:
            action = chlorinator_parsers.ChlorinatorActions.NoAction
        async with self.coordinator._ble_lock:
            await self.coordinator.chlorinator.async_write_action(action)
        self._set_optimistic(option)
        await asyncio.sleep(2)
        await self.coordinator.async_request_refresh()

class ChlorinatorDefaultManualSpeedSelect(
    _OptimisticOptionMixin, CoordinatorEntity[ChlorinatorDataUpdateCoordinator], SelectEntity
):
    """Representation of a Chlorinator Default Manual Speed Select entity."""

    _attr_icon = "mdi:speedometer"
    _attr_options = ["Low", "Medium", "High"]
    _attr_name = "Default Manual Speed"
    _attr_unique_id = "pool01_default_manual_speed_select"

    def __init__(
        self,
        coordinator: ChlorinatorDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo | None:
        return {
            "identifiers": {(DOMAIN, "POOL01")},
            "name": "POOL01",
            "model": "Viron eQuilibrium",
            "manufacturer": "Astral Pool",
        }

    @property
    def current_option(self):
        speed = self.coordinator.data.get("default_manual_on_speed")
        if speed is chlorinator_parsers.SpeedLevels.Low:
            actual = "Low"
        elif speed is chlorinator_parsers.SpeedLevels.Medium:
            actual = "Medium"
        else:
            actual = "High"
        return self._resolve_optimistic(actual)

    async def async_select_option(self, option: str) -> None:
        """Change the default manual speed."""
        from pychlorinator.chlorinator_parsers import SpeedLevels
        if option == "Low":
            speed = SpeedLevels.Low
        elif option == "Medium":
            speed = SpeedLevels.Medium
        else:
            speed = SpeedLevels.High
        async with self.coordinator._ble_lock:
            await self.coordinator.chlorinator.async_write_setup(
                default_manual_on_speed=speed
            )
        self._set_optimistic(option)
        await asyncio.sleep(2)
        await self.coordinator.async_request_refresh()