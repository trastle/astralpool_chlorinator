"""The chlorinator integration models (MQTT edition)."""
from __future__ import annotations

from dataclasses import dataclass

from .coordinator import ChlorinatorDataUpdateCoordinator
from .mqtt_client import MqttChlorinatorClient


@dataclass
class ChlorinatorData:
    """Data for the chlorinator integration."""

    title: str
    device: MqttChlorinatorClient
    coordinator: ChlorinatorDataUpdateCoordinator
