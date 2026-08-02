"""MQTT-backed shim matching pychlorinator's ChlorinatorAPI write interface.

This fork replaces the direct-BLE ChlorinatorAPI with a Pi-side MQTT bridge
(https://github.com/trastle/astral-pool-api-reverse-engineering) that owns
the actual BLE connection - this component only ever talks MQTT, using
Home Assistant's own already-configured MQTT connection (no separate broker
credentials needed here).
"""
from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def topics(name: str) -> dict[str, str]:
    base = f"chlorinator/{name}"
    return {"state": f"{base}/state", "action": f"{base}/action", "setup": f"{base}/setup"}


class MqttChlorinatorClient:
    """Publishes action/setup commands to MQTT instead of writing over BLE.

    Same method names/signatures as pychlorinator's ChlorinatorAPI so
    select.py/number.py/button.py (which call
    coordinator.chlorinator.async_write_action(...) /
    .async_write_setup(...)) work completely unmodified.
    """

    def __init__(self, hass: HomeAssistant, name: str) -> None:
        self.hass = hass
        self._topics = topics(name)

    async def async_write_action(self, action, **kwargs) -> None:
        payload = {"action": int(action)}
        payload.update(kwargs)
        _LOGGER.debug("Publishing action to %s: %s", self._topics["action"], payload)
        await mqtt.async_publish(self.hass, self._topics["action"], json.dumps(payload))

    async def async_write_setup(self, **kwargs) -> None:
        _LOGGER.debug("Publishing setup to %s: %s", self._topics["setup"], kwargs)
        await mqtt.async_publish(self.hass, self._topics["setup"], json.dumps(kwargs))
