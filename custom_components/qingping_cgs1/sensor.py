"""Support for Qingping CGS1 sensors."""
from __future__ import annotations

import json
import logging
from datetime import timedelta
import time
import asyncio

from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_MAC
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN, MQTT_TOPIC_PREFIX,
    SENSOR_BATTERY, SENSOR_CO2, SENSOR_HUMIDITY, SENSOR_PM10, SENSOR_PM25, SENSOR_TEMPERATURE, SENSOR_TVOC,
    PERCENTAGE, PPM, PPB, TEMP_CELSIUS, CONCENTRATION,
    CONF_TEMPERATURE_OFFSET, CONF_HUMIDITY_OFFSET,
    ATTR_TYPE, ATTR_UP_ITVL, ATTR_DURATION,
    DEFAULT_TYPE, DEFAULT_UP_ITVL, DEFAULT_DURATION,
    RECONNECTION_INTERVAL
)

_LOGGER = logging.getLogger(__name__)

OFFLINE_TIMEOUT = 300  # 5 minutes in seconds
MQTT_PUBLISH_RETRY_LIMIT = 3
MQTT_PUBLISH_RETRY_DELAY = 5  # seconds

async def ensure_mqtt_connected(hass):
    """Ensure MQTT is connected before publishing."""
    for _ in range(5):  # Try up to 5 times
        if mqtt.is_connected(hass):
            return True
        await asyncio.sleep(1)
    return False

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qingping CGS1 sensor based on a config entry."""
    mac = config_entry.data[CONF_MAC]
    name = config_entry.data[CONF_NAME]

    async def async_update_data():
        """Fetch data from API endpoint."""
        # This is a placeholder. In a real scenario, you might
        # fetch data from an API or process local data here.
        return {}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="sensor",
        update_method=async_update_data,
        update_interval=timedelta(seconds=60),
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()

    device_info = {
        "identifiers": {(DOMAIN, mac)},
        "name": name,
        "manufacturer": "Qingping",
        "model": "CGS1",
    }

    status_sensor = QingpingCGS1StatusSensor(coordinator, config_entry, mac, name, device_info)

    sensors = [
        status_sensor,
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_BATTERY, PERCENTAGE, SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_CO2, PPM, SensorDeviceClass.CO2, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_HUMIDITY, PERCENTAGE, SensorDeviceClass.HUMIDITY, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_PM10, CONCENTRATION, SensorDeviceClass.PM10, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_PM25, CONCENTRATION, SensorDeviceClass.PM25, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_TEMPERATURE, TEMP_CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_TVOC, PPB, SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS, SensorStateClass.MEASUREMENT, device_info),
    ]

    async_add_entities(sensors)

    # Store sensors in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(config_entry.entry_id, {})
    hass.data[DOMAIN][config_entry.entry_id]["sensors"] = sensors

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

            timestamp = payload.get("timestamp")
            if timestamp is not None:
                status_sensor.update_timestamp(timestamp)

            sensor_data = payload.get("sensorData")
            if not isinstance(sensor_data, list) or not sensor_data:
                _LOGGER.error("sensorData is not a non-empty list")
                return

            for data in sensor_data:
                for sensor in sensors[1:]:  # Skip status sensor
                    value = data.get(sensor._sensor_type, {})
                    if isinstance(value, dict):
                        value = value.get("value")
                    if value is not None:
                        sensor.update_from_latest_data(value)

        except json.JSONDecodeError:
            _LOGGER.error("Invalid JSON in MQTT message: %s", message.payload)
        except Exception as e:
            _LOGGER.error("Error processing MQTT message: %s", str(e))

    await mqtt.async_subscribe(
        hass, f"{MQTT_TOPIC_PREFIX}/{mac}/up", message_received, 1
    )

    # Set up timer for periodic publishing
    async def publish_config_wrapper(*args):
        if await ensure_mqtt_connected(hass):
            await sensors[1].publish_config()
        else:
            _LOGGER.error("Failed to connect to MQTT for periodic config publish")

    hass.data[DOMAIN][config_entry.entry_id]["remove_timer"] = async_track_time_interval(
        hass, publish_config_wrapper, timedelta(seconds=RECONNECTION_INTERVAL)
    )

    # Publish config immediately upon setup
    if await ensure_mqtt_connected(hass):
        await publish_config_wrapper()
    else:
        _LOGGER.error("Failed to connect to MQTT for initial config publish")

class QingpingCGS1StatusSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Qingping CGS1 status sensor."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} Status"
        self._attr_unique_id = f"{mac}_status"
        self._attr_device_info = device_info
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_value = "offline"
        self._last_timestamp = 0

    @callback
    def update_timestamp(self, timestamp):
        """Update the last received timestamp."""
        self._last_timestamp = int(timestamp)
        self._update_status()

    @callback
    def _update_status(self):
        """Update the status based on the last timestamp."""
        current_time = int(time.time())
        new_status = "online" if current_time - self._last_timestamp <= OFFLINE_TIMEOUT else "offline"
        if self._attr_native_value != new_status:
            self._attr_native_value = new_status
            self.async_write_ha_state()
            # Update other sensors' availability
            sensors = self.hass.data[DOMAIN][self._config_entry.entry_id].get("sensors", [])
            for sensor in sensors:
                if isinstance(sensor, QingpingCGS1Sensor):
                    sensor.async_write_ha_state()

    async def async_added_to_hass(self):
        """Set up a timer to regularly update the status."""
        await super().async_added_to_hass()

        async def update_status(*_):
            self._update_status()

        self.async_on_remove(async_track_time_interval(
            self.hass, update_status, timedelta(seconds=60)
        ))

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

    async def publish_config(self):
        """Publish configuration message to MQTT."""
        payload = {
            ATTR_TYPE: DEFAULT_TYPE,
            ATTR_UP_ITVL: DEFAULT_UP_ITVL,
            ATTR_DURATION: DEFAULT_DURATION
        }
        topic = f"{MQTT_TOPIC_PREFIX}/{self._mac}/down"

        for attempt in range(MQTT_PUBLISH_RETRY_LIMIT):
            if not await ensure_mqtt_connected(self.hass):
                _LOGGER.error("MQTT is not connected after multiple attempts")
                return

            try:
                await mqtt.async_publish(self.hass, topic, json.dumps(payload))
                _LOGGER.info(f"Published config to {topic}: {payload}")
                return
            except HomeAssistantError as err:
                _LOGGER.warning(f"Failed to publish config (attempt {attempt + 1}): {err}")
                if attempt < MQTT_PUBLISH_RETRY_LIMIT - 1:
                    await asyncio.sleep(MQTT_PUBLISH_RETRY_DELAY)
                else:
                    _LOGGER.error(f"Failed to publish config after {MQTT_PUBLISH_RETRY_LIMIT} attempts")

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        sensors = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id, {}).get("sensors", [])
        status_sensor = next((sensor for sensor in sensors if isinstance(sensor, QingpingCGS1StatusSensor)), None)
        return status_sensor.native_value == "online" if status_sensor else False

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up the timer when entity is removed."""
        if self._config_entry.entry_id in self.hass.data.get(DOMAIN, {}):
            remove_timer = self.hass.data[DOMAIN][self._config_entry.entry_id].get("remove_timer")
            if remove_timer:
                remove_timer()
        await super().async_will_remove_from_hass()