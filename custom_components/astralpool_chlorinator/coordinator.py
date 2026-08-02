"""Data coordinator for receiving Chlorinator updates over MQTT.

Forked from pbutterworth/astralpool_chlorinator to consume state from an
MQTT bridge (https://github.com/trastle/astral-pool-api-reverse-engineering)
running on a Raspberry Pi near the pool equipment, instead of talking BLE
directly from Home Assistant - solves the Bluetooth-range problem this
integration otherwise has when the chlorinator isn't within BLE range of
the HA host itself.

Push-based, not polling: data arrives whenever the Pi bridge publishes a
new MQTT message (its own poll interval, independent of this component),
so there's no update_interval/_async_update_data here - just
async_set_updated_data() called from the MQTT subscription callback.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from typing import Any

from pychlorinator.chlorinator_parsers import (
    AcidDosingInhibitStatuses,
    ChlorineControlStatuses,
    ChlorineControlTypes,
    InfoMessages,
    Modes,
    PhControlTypes,
    SpeedLevels,
)

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .mqtt_client import MqttChlorinatorClient, topics

_LOGGER = logging.getLogger(__name__)


def _enum_by_value(enum_cls, raw):
    """int -> enum member. mode/pump_speed/chlorine_control_status/
    default_manual_on_speed are published as the raw pychlorinator enum
    .value by the Pi bridge."""
    try:
        return enum_cls(raw)
    except ValueError:
        # The upstream project's own gateway notes real-world glitches here
        # (out-of-range values like 16, 31, 117 seen for 'mode') - don't
        # crash the whole update over one bad field, just pass it through.
        _LOGGER.warning("Unknown %s value: %s", enum_cls.__name__, raw)
        return raw


def _enum_by_name(enum_cls, raw):
    """name string -> enum member. Fields that are plain Enum (not
    IntEnum) - ph_control_type/chlorine_control_type/
    acid_dosing_inhibit_status/info_message - are published by name since
    a bare int wouldn't let the fork reconstruct the same member via `==`/
    `is` comparisons the way mode/pump_speed's IntEnum-like handling does."""
    try:
        return enum_cls[raw]
    except KeyError:
        _LOGGER.warning("Unknown %s name: %s", enum_cls.__name__, raw)
        return raw


def parse_mqtt_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct pychlorinator's dict shape (real enums/timedeltas) from
    the flat JSON the Pi bridge publishes, so entity code written against
    ChlorinatorState/async_gatherdata()'s original shape needs no changes."""
    data = dict(payload)

    if "mode" in data:
        data["mode"] = _enum_by_value(Modes, data["mode"])
    if "pump_speed" in data:
        data["pump_speed"] = _enum_by_value(SpeedLevels, data["pump_speed"])
    if "default_manual_on_speed" in data:
        data["default_manual_on_speed"] = _enum_by_value(SpeedLevels, data["default_manual_on_speed"])
    if "chlorine_control_status" in data:
        data["chlorine_control_status"] = _enum_by_value(ChlorineControlStatuses, data["chlorine_control_status"])
    if "info_message" in data:
        data["info_message"] = _enum_by_name(InfoMessages, data["info_message"])
    if "ph_control_type" in data:
        data["ph_control_type"] = _enum_by_name(PhControlTypes, data["ph_control_type"])
    if "chlorine_control_type" in data:
        data["chlorine_control_type"] = _enum_by_name(ChlorineControlTypes, data["chlorine_control_type"])
    if "acid_dosing_inhibit_status" in data:
        data["acid_dosing_inhibit_status"] = _enum_by_name(AcidDosingInhibitStatuses, data["acid_dosing_inhibit_status"])

    if "cell_running_time_days" in data:
        data["cell_running_time"] = timedelta(days=data.pop("cell_running_time_days"))
    if "low_salt_cell_running_time_days" in data:
        data["low_salt_cell_running_time"] = timedelta(days=data.pop("low_salt_cell_running_time_days"))

    if "pool_volume_litres" in data:
        data["pool_volume"] = data.pop("pool_volume_litres")
    if "spa_volume_litres" in data:
        data["spa_volume"] = data.pop("spa_volume_litres")

    return data


class ChlorinatorDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Push-based coordinator fed by MQTT instead of periodic BLE polling."""

    def __init__(self, hass: HomeAssistant, mqtt_name: str, entry: ConfigEntry) -> None:
        """Initialise the coordinator."""
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.data = {}
        self._entry = entry
        self._mqtt_name = mqtt_name
        self._unsubscribe = None
        # Kept the name _ble_lock (not renamed to e.g. _write_lock) so
        # select.py/number.py/button.py - which all do
        # `async with self.coordinator._ble_lock:` before a write - work
        # completely unmodified. It's a write-serialization lock now,
        # nothing BLE about it.
        self._ble_lock = asyncio.Lock()
        self.chlorinator = MqttChlorinatorClient(hass, mqtt_name)
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, mqtt_name)},
            manufacturer="Astral Pool",
            name=mqtt_name.upper(),
        )

    async def async_start(self) -> None:
        """Subscribe to the Pi bridge's MQTT state topic."""
        state_topic = topics(self._mqtt_name)["state"]

        @callback
        def _message_received(msg) -> None:
            try:
                payload = json.loads(msg.payload)
            except (json.JSONDecodeError, TypeError) as exc:
                _LOGGER.warning("Bad MQTT state payload on %s: %s", state_topic, exc)
                return
            if "error" in payload:
                _LOGGER.warning("Chlorinator gateway reported an error: %s", payload["error"])
                return
            self.async_set_updated_data(parse_mqtt_state(payload))

        self._unsubscribe = await mqtt.async_subscribe(self.hass, state_topic, _message_received)
        _LOGGER.info("Subscribed to %s", state_topic)

    async def async_stop(self) -> None:
        """Unsubscribe on unload."""
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None
