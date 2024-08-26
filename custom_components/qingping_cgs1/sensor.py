"""Support for Qingping CGS1 sensors."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta

from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_MAC
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN, MQTT_TOPIC_PREFIX,
    SENSOR_BATTERY, SENSOR_CO2, SENSOR_HUMIDITY, SENSOR_PM10, SENSOR_PM25, SENSOR_TEMPERATURE, SENSOR_TVOC,
    PERCENTAGE, PPM, TEMP_CELSIUS, CONCENTRATION,
    ATTR_TYPE, ATTR_UP_ITVL, ATTR_DURATION,
    DEFAULT_TYPE, DEFAULT_UP_ITVL, DEFAULT_DURATION,
    RECONNECTION_INTERVAL
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qingping CGS1 sensor based on a config entry."""
    mac = config_entry.data[CONF_MAC]
    name = config_entry.data[CONF_NAME]

    sensors = [
        QingpingCGS1Sensor(hass, config_entry, mac, name, SENSOR_BATTERY, PERCENTAGE, SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT),
        QingpingCGS1Sensor(hass, config_entry, mac, name, SENSOR_CO2, PPM, SensorDeviceClass.CO2, SensorStateClass.MEASUREMENT),
        QingpingCGS1Sensor(hass, config_entry, mac, name, SENSOR_HUMIDITY, PERCENTAGE, SensorDeviceClass.HUMIDITY, SensorStateClass.MEASUREMENT),
        QingpingCGS1Sensor(hass, config_entry, mac, name, SENSOR_PM10, CONCENTRATION, SensorDeviceClass.PM10, SensorStateClass.MEASUREMENT),
        QingpingCGS1Sensor(hass, config_entry, mac, name, SENSOR_PM25, CONCENTRATION, SensorDeviceClass.PM25, SensorStateClass.MEASUREMENT),
        QingpingCGS1Sensor(hass, config_entry, mac, name, SENSOR_TEMPERATURE, TEMP_CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
        QingpingCGS1Sensor(hass, config_entry, mac, name, SENSOR_TVOC, PPM, SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS, SensorStateClass.MEASUREMENT),
    ]

    async_add_entities(sensors)

class QingpingCGS1Sensor(SensorEntity):
    """Representation of a Qingping CGS1 sensor."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, mac: str, name: str, sensor_type: str, unit: str, device_class: str, state_class: str) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._config_entry = config_entry
        self._mac = mac
        self._sensor_type = sensor_type
        self._attr_name = f"{name} {sensor_type.capitalize()}"
        self._attr_unique_id = f"{mac}_{sensor_type}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = {
            "identifiers": {(DOMAIN, mac)},
            "name": name,
            "manufacturer": "Qingping",
            "model": "CGS1",
        }
        self._available = False
        self._remove_timer = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT events and set up timer."""
        await super().async_added_to_hass()

        @callback
        def message_received(message):
            """Handle new MQTT messages."""
            try:
                payload = json.loads(message.payload)
                if payload.get("mac") == self._mac:
                    sensor_data = payload["sensorData"][0]
                    if self._sensor_type in sensor_data:
                        value = sensor_data[self._sensor_type]["value"]
                        
                        # Process temperature and humidity values
                        if self._sensor_type == SENSOR_TEMPERATURE:
                            value = round(float(value), 1) if '.' in str(value) else value
                        elif self._sensor_type == SENSOR_HUMIDITY:
                            value = round(float(value), 1) if '.' in str(value) else int(value)
                        
                        self._attr_native_value = value
                        if not self._available:
                            self._available = True
                            asyncio.create_task(self.publish_config())
                        self.async_write_ha_state()
            except json.JSONDecodeError:
                _LOGGER.error("Invalid JSON in MQTT message")
            except KeyError:
                _LOGGER.error("Unexpected message format")

        await mqtt.async_subscribe(
            self.hass, f"{MQTT_TOPIC_PREFIX}/{self._mac}/up", message_received, 1
        )

        # Set up timer for periodic publishing
        self._remove_timer = async_track_time_interval(
            self.hass,
            self.publish_config,
            timedelta(seconds=RECONNECTION_INTERVAL)
        )

        # Publish config immediately upon setup
        await self.publish_config()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up the timer when entity is removed."""
        if self._remove_timer:
            self._remove_timer()

    async def publish_config(self, *args):
        """Publish configuration message to MQTT."""
        payload = {
            ATTR_TYPE: DEFAULT_TYPE,
            ATTR_UP_ITVL: DEFAULT_UP_ITVL,
            ATTR_DURATION: DEFAULT_DURATION
        }
        topic = f"{MQTT_TOPIC_PREFIX}/{self._mac}/down"
        await mqtt.async_publish(self.hass, topic, json.dumps(payload))
        _LOGGER.info(f"Published config to {topic}: {payload}")

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available