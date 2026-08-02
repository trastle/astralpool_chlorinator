"""Config flow for the Astral Pool Chlorinator integration - MQTT edition.

No Bluetooth discovery, no access code - the Pi bridge already holds those
and publishes decrypted state over MQTT. This just needs the device name
segment used in its chlorinator/<name>/... topics.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from .const import CONF_MQTT_NAME, DEFAULT_MQTT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the MQTT-backed eQuilibrium Chlorinator."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the MQTT device name segment."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mqtt_name = user_input[CONF_MQTT_NAME].strip().lower()
            await self.async_set_unique_id(mqtt_name)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=mqtt_name.upper(),
                data={CONF_MQTT_NAME: mqtt_name},
            )

        data_schema = vol.Schema(
            {vol.Required(CONF_MQTT_NAME, default=DEFAULT_MQTT_NAME): str}
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "example": "If the Pi bridge publishes to chlorinator/pool01/state, enter pool01."
            },
        )
