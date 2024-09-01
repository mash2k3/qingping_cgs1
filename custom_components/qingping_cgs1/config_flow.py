"""Config flow for Qingping CGS1 integration."""
from __future__ import annotations

import voluptuous as vol
import logging
from typing import Any
import asyncio

from homeassistant import config_entries
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.components import mqtt
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, MQTT_TOPIC_PREFIX

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Qingping CGS1."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._discovered_devices = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        try:
            if user_input is None:
                # Discover available devices
                await self._async_discover_devices()

                # Check if there are any available devices
                if not self._discovered_devices:
                    return self.async_show_form(
                        step_id="no_devices",
                        errors=errors,
                    )

                # Create the schema with the dropdown
                data_schema = vol.Schema({
                    vol.Required(CONF_MAC): vol.In(self._discovered_devices),
                    vol.Required(CONF_NAME): str,
                })

                return self.async_show_form(
                    step_id="user",
                    data_schema=data_schema,
                    errors=errors,
                )

            # Validate the input
            mac = user_input[CONF_MAC]
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()

            # Create the config entry
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        except Exception as ex:
            _LOGGER.error("Unexpected exception in Qingping CGS1 config flow: %s", ex)
            errors["base"] = "unknown"
            return self.async_show_form(
                step_id="user",
                errors=errors,
            )

    async def async_step_no_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the case when no devices are found."""
        if user_input is None:
            return self.async_show_form(
                step_id="no_devices",
                data_schema=vol.Schema({}),
            )

        # User clicked "Add Manually" button
        return await self.async_step_manual()

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual device configuration."""
        errors = {}

        if user_input is None:
            return self.async_show_form(
                step_id="manual",
                data_schema=vol.Schema({
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_MAC): str,
                }),
            )

        try:
            mac = user_input[CONF_MAC]
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        except Exception as ex:
            _LOGGER.warning("Unexpected exception in manual config: %s", ex)
            errors["base"] = "Device already configured, try a different mac address."
            return self.async_show_form(
                step_id="manual",
                data_schema=vol.Schema({
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_MAC): str,
                }),
                errors=errors,
            )

    async def _async_discover_devices(self):
        """Discover available Qingping CGS1 devices via MQTT."""
        try:
            # Get list of already configured devices
            configured_devices = {
                entry.unique_id for entry in self._async_current_entries()
            }

            def _handle_message(msg):
                """Handle received MQTT messages."""
                try:
                    # Extract MAC address from the topic
                    mac = msg.topic.split('/')[-2]
                    if mac and mac not in configured_devices and mac not in self._discovered_devices:
                        self._discovered_devices[mac] = f"Qingping CGS1 ({mac})"
                except Exception as ex:
                    _LOGGER.error("Error handling MQTT message: %s", ex)

            # Subscribe to the MQTT topic
            await mqtt.async_subscribe(
                self.hass, f"{MQTT_TOPIC_PREFIX}/#", _handle_message
            )

            # Wait for a short time to collect messages
            await asyncio.sleep(10)  # Increased to 10 seconds for better discovery

            _LOGGER.info(f"Discovered {len(self._discovered_devices)} new Qingping CGS1 devices")

        except HomeAssistantError as ex:
            _LOGGER.error("Error discovering Qingping CGS1 devices: %s", ex)
        except Exception as ex:
            _LOGGER.error("Unexpected error in device discovery: %s", ex)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Qingping CGS1."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                # Add any configurable options here
            }),
        )