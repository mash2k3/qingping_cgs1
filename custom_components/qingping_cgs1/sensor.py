"""Support for Qingping CGS1 sensors."""
from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_MAC
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN, MQTT_TOPIC_PREFIX,
    SENSOR_BATTERY, SENSOR_CO2, SENSOR_HUMIDITY, SENSOR_PM10, SENSOR_PM25, SENSOR_TEMPERATURE, SENSOR_TVOC,
    PERCENTAGE, PPM, PPB, TEMP_CELSIUS, CONCENTRATION,
    CONF_TEMPERATURE_OFFSET, CONF_HUMIDITY_OFFSET
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
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    device_info = {
        "identifiers": {(DOMAIN, mac)},
        "name": name,
        "manufacturer": "Qingping",
        "model": "CGS1",
    }

    sensors = [
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_BATTERY, PERCENTAGE, SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_CO2, PPM, SensorDeviceClass.CO2, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_HUMIDITY, PERCENTAGE, SensorDeviceClass.HUMIDITY, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_PM10, CONCENTRATION, SensorDeviceClass.PM10, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_PM25, CONCENTRATION, SensorDeviceClass.PM25, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_TEMPERATURE, TEMP_CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_TVOC, PPB, SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS, SensorStateClass.MEASUREMENT, device_info),
    ]

    async_add_entities(sensors)

    @callback
    def message_received(message):
        """Handle new MQTT messages."""
        try:
            payload = json.loads(message.payload)
            if not isinstance(payload, dict):
                _LOGGER.error("Payload is not a dictionary")
                return

            if payload.get("mac") != mac:
                _LOGGER.debug("Received message for a different device")
                return

            sensor_data = payload.get("sensorData")
            if not isinstance(sensor_data, list) or not sensor_data:
                _LOGGER.error("sensorData is not a non-empty list")
                return

            for data in sensor_data:
                for sensor in sensors:
                    value = data.get(sensor._sensor_type, {}).get("value")
                    if value is not None:
                        sensor.update_from_latest_data(value)

        except json.JSONDecodeError:
            _LOGGER.error("Invalid JSON in MQTT message: %s", message.payload)
        except Exception as e:
            _LOGGER.error("Error processing MQTT message: %s", str(e))

    await mqtt.async_subscribe(
        hass, f"{MQTT_TOPIC_PREFIX}/{mac}/up", message_received, 1
    )

class QingpingCGS1Sensor(CoordinatorEntity, SensorEntity):
    """Representation of a Qingping CGS1 sensor."""

    def __init__(self, coordinator, config_entry, mac, name, sensor_type, unit, device_class, state_class, device_info):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._sensor_type = sensor_type
        self._attr_name = f"{name} {sensor_type.capitalize()}"
        self._attr_unique_id = f"{mac}_{sensor_type}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = device_info

    @callback
    def update_from_latest_data(self, value):
        """Update the sensor with the latest data."""
        try:
            if self._sensor_type == SENSOR_TEMPERATURE:
                offset = self.coordinator.data.get(CONF_TEMPERATURE_OFFSET, 0)
                self._attr_native_value = round(float(value) + offset, 1)
            elif self._sensor_type == SENSOR_HUMIDITY:
                offset = self.coordinator.data.get(CONF_HUMIDITY_OFFSET, 0)
                self._attr_native_value = round(float(value) + offset, 1)
            else:
                self._attr_native_value = int(value)
            self.async_write_ha_state()
        except ValueError:
            _LOGGER.error("Invalid value received for %s: %s", self._sensor_type, value)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success