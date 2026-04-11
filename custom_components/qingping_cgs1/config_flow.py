"""Config flow for Qingping CGxx integration."""
from __future__ import annotations

import voluptuous as vol
import logging
from typing import Any
import asyncio
import json
import time

from homeassistant import config_entries
from homeassistant.const import CONF_MAC, CONF_NAME, CONF_MODEL
from homeassistant.data_entry_flow import FlowResult
from homeassistant.components import mqtt
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, MQTT_TOPIC_PREFIX, QP_MODELS, DEFAULT_MODEL

_LOGGER = logging.getLogger(__name__)
DISCOVERY_CACHE_TTL = 24 * 60 * 60  # 24 hours

def clean_mac_address(mac: str) -> str:
    """Remove colons from MAC address if present."""
    return mac.replace(":", "")

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Qingping CGxx."""

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
                    vol.Required(CONF_MODEL): vol.In(QP_MODELS),
                })

                return self.async_show_form(
                    step_id="user",
                    data_schema=data_schema,
                    errors=errors,
                )

            # Validate the input
            mac = clean_mac_address(user_input[CONF_MAC])
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()

            validated_data = {
                CONF_MAC: mac,
                CONF_NAME: user_input[CONF_NAME],
                CONF_MODEL: user_input.get(CONF_MODEL, DEFAULT_MODEL),  # Get the model or use default
            }

            # Create the config entry
            _LOGGER.debug("Creating entry with data: %s", validated_data)
            return self.async_create_entry(title=validated_data[CONF_NAME], data=validated_data)

        except Exception as ex:
            _LOGGER.error("Unexpected exception in Qingping CGxx config flow: %s", ex)
            errors["base"] = "unknown"
            return self.async_show_form(
                step_id="user",
                 data_schema=vol.Schema({
                    vol.Required(CONF_MAC): vol.In(self._discovered_devices),
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_MODEL): vol.In(QP_MODELS),
                }),
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
                    vol.Required(CONF_MODEL): vol.In(QP_MODELS),
                }),
            )

        try:
            mac = clean_mac_address(user_input[CONF_MAC])
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()

            validated_data = {
                CONF_MAC: mac,
                CONF_NAME: user_input[CONF_NAME],
                CONF_MODEL: user_input.get(CONF_MODEL, DEFAULT_MODEL),  # Get the model or use default
            }

            _LOGGER.debug("Creating manual entry with data: %s", validated_data)
            return self.async_create_entry(title=validated_data[CONF_NAME], data=validated_data)
        except Exception as ex:
            _LOGGER.warning("Unexpected exception in manual config: %s", ex)
            errors["base"] = "Device already configured, try a different mac address."
            return self.async_show_form(
                step_id="manual",
                data_schema=vol.Schema({
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_MAC): str,
                    vol.Required(CONF_MODEL): vol.In(QP_MODELS),
                }),
                errors=errors,
            )

    async def _async_discover_devices(self):
        """Discover available Qingping devices via MQTT and keep a cache of discovered BLE devices."""
        try:
            configured_devices = {
                entry.unique_id for entry in self._async_current_entries()
            }

            domain_data = self.hass.data.setdefault(DOMAIN, {})
            discovered_cache = domain_data.setdefault("discovered_devices_cache", {})
            now = time.time()

            # Cleanup old cache entries
            expired = [
                mac for mac, info in discovered_cache.items()
                if now - info.get("last_seen", 0) > DISCOVERY_CACHE_TTL
            ]
            for mac in expired:
                discovered_cache.pop(mac, None)

            # Seed current discovery dialog from cache
            self._discovered_devices = {
                mac: info["name"]
                for mac, info in discovered_cache.items()
                if mac not in configured_devices
            }

            def _remember_device(mac: str, device_name: str) -> None:
                discovered_cache[mac] = {
                    "name": device_name,
                    "last_seen": time.time(),
                }
                if mac not in configured_devices:
                    self._discovered_devices[mac] = device_name

            def _handle_message(msg):
                """Handle received MQTT messages."""
                try:
                    mac = None
                    device_name = None

                    # TLV devices published directly
                    if msg.payload[:2] == b"CG":
                        topic_parts = msg.topic.split("/")
                        if len(topic_parts) >= 3:
                            mac = clean_mac_address(topic_parts[-2])
                            if mac:
                                device_name = f"Qingping TLV Device ({mac})"

                    else:
                        try:
                            payload = json.loads(msg.payload.decode("utf-8", errors="ignore"))
                        except Exception:
                            return

                        msg_type = str(payload.get("type", ""))

                        # BLE relay packet from gateway
                        if msg_type == "9" and payload.get("mac") and payload.get("adv_data"):
                            mac = clean_mac_address(payload["mac"])
                            if mac:
                                device_name = f"Qingping BLE Device ({mac})"

                        # Regular JSON devices
                        else:
                            topic_parts = msg.topic.split("/")
                            if len(topic_parts) >= 3:
                                topic_mac = clean_mac_address(topic_parts[-2])
                                if topic_mac and msg_type in {"13", "15", "17", "21", "25", "26", "27"}:
                                    mac = topic_mac
                                    device_name = f"Qingping JSON ({mac})"

                    if mac and device_name:
                        was_known = mac in self._discovered_devices
                        _remember_device(mac, device_name)
                        if not was_known and mac not in configured_devices:
                            _LOGGER.info("Discovered device: %s", device_name)

                except Exception as ex:
                    _LOGGER.error("Error handling MQTT message: %s", ex)

            unsubscribe = await mqtt.async_subscribe(
                self.hass, f"{MQTT_TOPIC_PREFIX}/#", _handle_message, 1, encoding=None
            )

            try:
                # Short live scan window for newly arrived packets.
                # Previously seen devices are still shown from cache.
                await asyncio.sleep(10)
            finally:
                unsubscribe()

            _LOGGER.info(
                "Discovered %s Qingping devices (including cached BLE devices)",
                len(self._discovered_devices),
            )

        except HomeAssistantError as ex:
            _LOGGER.error("Error discovering Qingping devices: %s", ex)
        except Exception as ex:
            _LOGGER.error("Unexpected error in device discovery: %s", ex)
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler()
    
class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Qingping CGS1."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update the config entry
            new_data = {
                **self.config_entry.data,
                CONF_MODEL: user_input[CONF_MODEL]
            }
            
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data,
            )
            
            # Reload the integration to apply changes
            await self.hass.config_entries.async_reload(self._config_entry_id)
            
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_MODEL,
                    default=self.config_entry.data.get(CONF_MODEL, DEFAULT_MODEL)
                ): vol.In(QP_MODELS),
            }),
        )
		