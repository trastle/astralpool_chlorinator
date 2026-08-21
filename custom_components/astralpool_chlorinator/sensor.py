"""Platform for sensor integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from pychlorinator.chlorinator_parsers import SpeedLevels

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
    SensorDeviceClass,
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

# Fixed 4 timer slots (matches pychlorinator's
# NUMBER_OF_PUMP_TIMERS_SUPPORTED) - the Pi bridge publishes these as
# coordinator.data["pump_timers"], a list of 4 dicts
# ({start_time, stop_time, enabled, speed_level}, see mqtt_bridge.py's
# build_state_payload()). Read-only for now; enable/disable and editing
# are a separate, later phase that needs new BLE write support.
NUMBER_OF_PUMP_TIMERS = 4

_LOGGER = logging.getLogger(__name__)

CHLORINATOR_SENSOR_TYPES: dict[str, SensorEntityDescription] = {
    "ph_measurement": SensorEntityDescription(
        key="ph_measurement",
        icon="mdi:ph",
        name="pH",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "mode": SensorEntityDescription(
        key="mode",
        icon="mdi:power",
        name="Mode",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
    ),
    "pump_speed": SensorEntityDescription(
        key="pump_speed",
        icon="mdi:speedometer",
        name="Pump speed",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
    ),
    "chlorine_control_status": SensorEntityDescription(
        key="chlorine_control_status",
        icon="mdi:beaker-outline",
        name="Chlorine status",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
    ),
    "info_message": SensorEntityDescription(
        key="info_message",
        icon="mdi:information-outline",
        name="Info message",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
    ),
    "ph_control_setpoint": SensorEntityDescription(
        key="ph_control_setpoint",
        icon="mdi:ph",
        name="pH setpoint",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "chlorine_control_setpoint": SensorEntityDescription(
        key="chlorine_control_setpoint",
        icon="mdi:beaker-check-outline",
        name="ORP setpoint",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "ph_control_type": SensorEntityDescription(
        key="ph_control_type",
        icon="mdi:ph",
        name="pH control",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
    ),
    "chlorine_control_type": SensorEntityDescription(
        key="chlorine_control_type",
        icon="mdi:beaker-outline",
        name="ORP control",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
    ),
    "highest_ph_measured": SensorEntityDescription(
        key="highest_ph_measured",
        icon="mdi:ph",
        name="Highest pH measured",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "lowest_ph_measured": SensorEntityDescription(
        key="lowest_ph_measured",
        icon="mdi:ph",
        name="Lowest pH measured",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "highest_orp_measured": SensorEntityDescription(
        key="highest_orp_measured",
        icon="mdi:beaker-outline",
        name="Highest ORP measured",
        native_unit_of_measurement="mV",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "lowest_orp_measured": SensorEntityDescription(
        key="lowest_orp_measured",
        icon="mdi:beaker-outline",
        name="Lowest ORP measured",
        native_unit_of_measurement="mV",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "cell_reversal_count": SensorEntityDescription(
        key="cell_reversal_count",
        icon="mdi:swap-horizontal",
        name="Cell reversal count",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "cell_running_time": SensorEntityDescription(
        key="cell_running_time",
        icon="mdi:timer-outline",
        name="Cell running time",
        native_unit_of_measurement="h",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "low_salt_cell_running_time": SensorEntityDescription(
        key="low_salt_cell_running_time",
        icon="mdi:timer-alert-outline",
        name="Low salt cell running time",
        native_unit_of_measurement="h",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "previous_days_cell_load": SensorEntityDescription(
        key="previous_days_cell_load",
        icon="mdi:chart-bar",
        name="Previous day cell load",
        native_unit_of_measurement="%",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "acid_dosing_inhibit_status": SensorEntityDescription(
        key="acid_dosing_inhibit_status",
        icon="mdi:beaker-off-outline",
        name="Acid dosing inhibit status",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
    ),
    "acid_dosing_inhibit_time_remaining": SensorEntityDescription(
        key="acid_dosing_inhibit_time_remaining",
        icon="mdi:timer-outline",
        name="Acid dosing inhibit time remaining",
        native_unit_of_measurement="min",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Chlorinator from a config entry."""
    data: ChlorinatorData = hass.data[DOMAIN][entry.entry_id]
    entities = [
        ChlorinatorSensor(data.coordinator, sensor_desc)
        for sensor_desc in CHLORINATOR_SENSOR_TYPES
    ]
    entities += [
        ChlorinatorTimerSensor(data.coordinator, i) for i in range(NUMBER_OF_PUMP_TIMERS)
    ]
    async_add_entities(entities)


class ChlorinatorSensor(
    CoordinatorEntity[ChlorinatorDataUpdateCoordinator], SensorEntity
):
    """Representation of a Clorinator Sensor."""

    _attr_has_entity_name = True
    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: ChlorinatorDataUpdateCoordinator,
        sensor: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor = sensor
        self._attr_unique_id = f"POOL01_{sensor}".lower()
        self._attr_name = CHLORINATOR_SENSOR_TYPES[sensor].name
        self.entity_description = CHLORINATOR_SENSOR_TYPES[sensor]
        self._attr_native_unit_of_measurement = CHLORINATOR_SENSOR_TYPES[
            sensor
        ].native_unit_of_measurement

    @property
    def device_info(self) -> DeviceInfo | None:
        return {
            "identifiers": {(DOMAIN, "POOL01")},
            "name": "POOL01",
            "model": "Viron eQuilibrium",
            "manufacturer": "Astral Pool",
        }

    @property
    def native_value(self):
        value = self.coordinator.data.get(self._sensor)
        if isinstance(value, timedelta):
            return value.total_seconds() / 3600
        return value


class ChlorinatorTimerSensor(
    CoordinatorEntity[ChlorinatorDataUpdateCoordinator], SensorEntity
):
    """One pump timer slot. State is a human-readable summary; the
    individual fields (also available raw over MQTT/pychlorinator) are
    exposed as extra state attributes for anyone who wants exact values
    - e.g. for automations/templates, or as the read side that a future
    switch/time entity (enable/disable, edit) would pair with."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: ChlorinatorDataUpdateCoordinator, index: int) -> None:
        """Initialize the sensor. index is 0-based; timer slots are
        numbered from 1 in the entity name/id to match the pump's own app
        and astral-pool-webui's dashboard, which both call them Timer 1-4."""
        super().__init__(coordinator)
        self._index = index
        slot = index + 1
        self._attr_unique_id = f"POOL01_pump_timer_{slot}".lower()
        self._attr_name = f"Pump timer {slot}"

    @property
    def device_info(self) -> DeviceInfo | None:
        return {
            "identifiers": {(DOMAIN, "POOL01")},
            "name": "POOL01",
            "model": "Viron eQuilibrium",
            "manufacturer": "Astral Pool",
        }

    def _timer(self) -> dict | None:
        timers = self.coordinator.data.get("pump_timers") or []
        return timers[self._index] if self._index < len(timers) else None

    @property
    def native_value(self):
        timer = self._timer()
        if timer is None:
            return None
        if not timer["enabled"]:
            return "Disabled"
        speed = SpeedLevels(timer["speed_level"]).name
        return f"{timer['start_time'][:5]}–{timer['stop_time'][:5]} ({speed})"

    @property
    def extra_state_attributes(self):
        timer = self._timer()
        if timer is None:
            return None
        return {
            "start_time": timer["start_time"],
            "stop_time": timer["stop_time"],
            "enabled": timer["enabled"],
            "speed_level": SpeedLevels(timer["speed_level"]).name,
        }