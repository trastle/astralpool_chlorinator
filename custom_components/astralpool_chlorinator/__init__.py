"""The Astral Pool Viron eQuilibrium Chlorinator integration - MQTT edition.

Forked from https://github.com/pbutterworth/astralpool_chlorinator to
consume state from an MQTT bridge running on a Raspberry Pi near the pool
equipment (https://github.com/trastle/astral-pool-api-reverse-engineering),
instead of talking BLE directly from Home Assistant - solves the
Bluetooth-range problem this integration otherwise has when the chlorinator
isn't within BLE range of the HA host itself.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_MQTT_NAME, DOMAIN
from .coordinator import ChlorinatorDataUpdateCoordinator
from .models import ChlorinatorData

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.NUMBER, Platform.SELECT, Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Chlorinator (MQTT edition) from a config entry."""

    mqtt_name: str = entry.data[CONF_MQTT_NAME]

    coordinator = ChlorinatorDataUpdateCoordinator(hass, mqtt_name, entry)
    await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ChlorinatorData(
        entry.title, coordinator.chlorinator, coordinator
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    entry.async_on_unload(coordinator.async_stop)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = True
    for platform in PLATFORMS:
        if not await hass.config_entries.async_forward_entry_unload(entry, platform):
            unload_ok = False

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
