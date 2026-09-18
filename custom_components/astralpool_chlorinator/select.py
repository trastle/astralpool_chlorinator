"""Platform for select integration."""
from __future__ import annotations

import logging
import asyncio

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

# The BLE connection to this device can fail outright on a single write -
# not a slow confirmation, a dropped command with nothing else retrying it
# (observed 2026-09-18: a mode-change command failed with "device
# disappeared" and the select entity just sat on the old value for over an
# hour until someone noticed and re-sent it manually - see
# home-assistant/pool/session-notes-2026-09-18.md in the docs repo). Retry
# the write itself here, in the entity, so both a person using the control
# and anything else calling select.select_option (e.g. an automation) get
# the same reliability for free.
_WRITE_RETRY_ATTEMPTS = 3
_WRITE_RETRY_DELAY_SECONDS = 15


async def _write_with_retries(coordinator, write_coro_factory, entity_name: str) -> None:
    """Attempt a BLE write up to _WRITE_RETRY_ATTEMPTS times, _WRITE_RETRY_DELAY_SECONDS apart."""
    last_exc: Exception | None = None
    for attempt in range(1, _WRITE_RETRY_ATTEMPTS + 1):
        try:
            async with coordinator._ble_lock:
                await write_coro_factory()
            return
        except Exception as exc:  # noqa: BLE001 - retry-and-reraise, not swallow
            last_exc = exc
            _LOGGER.warning(
                "%s: BLE write attempt %d/%d failed: %s",
                entity_name, attempt, _WRITE_RETRY_ATTEMPTS, exc,
            )
            if attempt < _WRITE_RETRY_ATTEMPTS:
                await asyncio.sleep(_WRITE_RETRY_DELAY_SECONDS)
    _LOGGER.error(
        "%s: all %d BLE write attempts failed, giving up",
        entity_name, _WRITE_RETRY_ATTEMPTS,
    )
    raise last_exc


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
    CoordinatorEntity[ChlorinatorDataUpdateCoordinator], SelectEntity
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
            return "Off"
        elif mode is chlorinator_parsers.Modes.Auto:
            return "Auto"
        else:
            return "Manual"

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
        await _write_with_retries(
            self.coordinator,
            lambda: self.coordinator.chlorinator.async_write_action(action),
            self._attr_name,
        )
        await asyncio.sleep(2)
        await self.coordinator.async_request_refresh()

class ChlorinatorSpeedSelect(
    CoordinatorEntity[ChlorinatorDataUpdateCoordinator], SelectEntity
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
            return "Low"
        elif speed is chlorinator_parsers.SpeedLevels.Medium:
            return "Medium"
        elif speed is chlorinator_parsers.SpeedLevels.AI:
            return "AI"
        else:
            return "High"

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
        await _write_with_retries(
            self.coordinator,
            lambda: self.coordinator.chlorinator.async_write_action(action),
            self._attr_name,
        )
        await asyncio.sleep(2)
        await self.coordinator.async_request_refresh()

class ChlorinatorDefaultManualSpeedSelect(
    CoordinatorEntity[ChlorinatorDataUpdateCoordinator], SelectEntity
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
            return "Low"
        elif speed is chlorinator_parsers.SpeedLevels.Medium:
            return "Medium"
        else:
            return "High"

    async def async_select_option(self, option: str) -> None:
        """Change the default manual speed."""
        from pychlorinator.chlorinator_parsers import SpeedLevels
        if option == "Low":
            speed = SpeedLevels.Low
        elif option == "Medium":
            speed = SpeedLevels.Medium
        else:
            speed = SpeedLevels.High
        await _write_with_retries(
            self.coordinator,
            lambda: self.coordinator.chlorinator.async_write_setup(
                default_manual_on_speed=speed
            ),
            self._attr_name,
        )
        await asyncio.sleep(2)
        await self.coordinator.async_request_refresh()