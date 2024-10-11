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
from homeassistant.const import CONF_NAME, CONF_MAC, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN, MQTT_TOPIC_PREFIX,
    SENSOR_BATTERY, SENSOR_CO2, SENSOR_HUMIDITY, SENSOR_PM10, SENSOR_PM25, SENSOR_TEMPERATURE, SENSOR_TVOC,
    PERCENTAGE, PPM, PPB, CONCENTRATION, CONF_TVOC_UNIT,
    CONF_TEMPERATURE_OFFSET, CONF_HUMIDITY_OFFSET, CONF_UPDATE_INTERVAL,
    ATTR_TYPE, ATTR_UP_ITVL, ATTR_DURATION,
    DEFAULT_TYPE, DEFAULT_DURATION
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
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    native_temp_unit = hass.config.units.temperature_unit

    async def async_update_data():
        """Fetch data from API endpoint."""
        # This is a placeholder. In a real scenario, you might
        # fetch data from an API or process local data here.
        return {}

    device_info = {
        "identifiers": {(DOMAIN, mac)},
        "name": name,
        "manufacturer": "Qingping",
        "model": "CGS1",
    }

    status_sensor = QingpingCGS1StatusSensor(coordinator, config_entry, mac, name, device_info)
    firmware_sensor = QingpingCGS1FirmwareSensor(coordinator, config_entry, mac, name, device_info)
    type_sensor = QingpingCGS1TypeSensor(coordinator, config_entry, mac, name, device_info)
    mac_sensor = QingpingCGS1MACSensor(coordinator, config_entry, mac, name, device_info)
    battery_state = QingpingCGS1BatteryStateSensor(coordinator, config_entry, mac, name, device_info)

    sensors = [
        status_sensor,
        firmware_sensor,
        type_sensor,
        mac_sensor,
        battery_state,
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_BATTERY, PERCENTAGE, SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_CO2, PPM, SensorDeviceClass.CO2, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_HUMIDITY, PERCENTAGE, SensorDeviceClass.HUMIDITY, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_PM10, CONCENTRATION, SensorDeviceClass.PM10, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_PM25, CONCENTRATION, SensorDeviceClass.PM25, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_TEMPERATURE, native_temp_unit, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, device_info),
        QingpingCGS1Sensor(coordinator, config_entry, mac, name, SENSOR_TVOC, PPB, SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS, SensorStateClass.MEASUREMENT, device_info),
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

            firmware_version = payload.get("version")
            if firmware_version is not None:
                firmware_sensor.update_version(firmware_version)

            device_type = payload.get("type")
            if device_type is not None:
                type_sensor.update_type(device_type)

            timestamp = payload.get("timestamp")
            if timestamp is not None:
                status_sensor.update_timestamp(timestamp)

            mac_address = payload.get("mac")
            if mac_address is not None:
                mac_sensor.update_mac(mac_address)

            sensor_data = payload.get("sensorData")
            if not isinstance(sensor_data, list) or not sensor_data:
                _LOGGER.error("sensorData is not a non-empty list")
                return
            if len(sensor_data) == 1:
                #ignore type 17 sensor data                
                for data in sensor_data:
                    battery_charging = None
                    if SENSOR_BATTERY in data:
                        battery_data = data[SENSOR_BATTERY]
                        if isinstance(battery_data, dict):
                            battery_charging = battery_data.get("status") == 1
                    for sensor in sensors[4:]:  # Skip status, firmware, mac and type sensors
                        if isinstance(sensor, QingpingCGS1BatteryStateSensor):
                            if battery_charging is not None:
                                sensor.update_battery_state(battery_charging)
                        elif sensor._sensor_type in data:
                            value = data[sensor._sensor_type]
                            if isinstance(value, dict):
                                value = value.get("value")
                            if value is not None:
                                sensor.update_from_latest_data(value)
                                if sensor._sensor_type == SENSOR_BATTERY and battery_charging is not None:
                                    sensor.update_battery_charging(battery_charging)
            else:
                _LOGGER.info("sensorData is type 17")
                return

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
            await sensors[5].publish_config()
        else:
            _LOGGER.error("Failed to connect to MQTT for periodic config publish")

    hass.data[DOMAIN][config_entry.entry_id]["remove_timer"] = async_track_time_interval(
        hass, publish_config_wrapper, timedelta(seconds=int(DEFAULT_DURATION))
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
        self._last_status = "online"

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
            # Call publish_config when status changes from offline to online
            if self._last_status == "offline" and new_status == "online":
                asyncio.create_task(self._publish_config_on_status_change())
            
            self._last_status = new_status

    async def _publish_config_on_status_change(self):
        """Publish config when status changes from offline to online."""
        sensors = self.hass.data[DOMAIN][self._config_entry.entry_id].get("sensors", [])
        for sensor in sensors:
            if isinstance(sensor, QingpingCGS1Sensor):
                await sensor.publish_config()
                break  # We only need to call it once                

    async def async_added_to_hass(self):
        """Set up a timer to regularly update the status."""
        await super().async_added_to_hass()

        async def update_status(*_):
            self._update_status()

        self.async_on_remove(async_track_time_interval(
            self.hass, update_status, timedelta(seconds=60)
        ))

class QingpingCGS1FirmwareSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Qingping CGS1 firmware sensor."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} Firmware"
        self._attr_unique_id = f"{mac}_firmware"
        self._attr_device_info = device_info
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_value = None

    @callback
    def update_version(self, version):
        """Update the firmware version."""
        self._attr_native_value = version
        self.async_write_ha_state()

class QingpingCGS1MACSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Qingping CGS1 mac sensor."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} MAC Address"
        self._attr_unique_id = f"{mac}_mac"
        self._attr_device_info = device_info
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_value = None

    @callback
    def update_mac(self, mac):
        """Update the mac address."""
        self._attr_native_value = mac
        self.async_write_ha_state()

class QingpingCGS1BatteryStateSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Qingping CGS1 battery state sensor."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} Battery State"
        self._attr_unique_id = f"{mac}_battery_state"
        self._attr_device_info = device_info
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_value = None

    @callback
    def update_battery_state(self, status):
        """Update the battery state."""
        self._attr_native_value = "Charging" if status == 1 else "Discharging"
        self.async_write_ha_state()

class QingpingCGS1TypeSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Qingping CGS1 type sensor."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} Report Type"
        self._attr_unique_id = f"{mac}_report_type"
        self._attr_device_info = device_info
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_value = None

    @callback
    def update_type(self, device_type):
        """Update the device type."""
        self._attr_native_value = device_type
        self.async_write_ha_state()

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
        self._battery_charging = False

    @callback
    def update_from_latest_data(self, value):
        """Update the sensor with the latest data."""
        try:
            if self._sensor_type == SENSOR_TEMPERATURE:
                offset = self.coordinator.data.get(CONF_TEMPERATURE_OFFSET, 0)
                temp_celsius = float(value)
                if self._attr_native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT:
                    # Convert to Fahrenheit
                    temp_fahrenheit = (temp_celsius * 9/5) + 32
                    self._attr_native_value = round(float(temp_fahrenheit) + offset, 1)
                else:
                    self._attr_native_value = round(float(temp_celsius) + offset, 1)
            elif self._sensor_type == SENSOR_HUMIDITY:
                offset = self.coordinator.data.get(CONF_HUMIDITY_OFFSET, 0)
                self._attr_native_value = round(float(value) + offset, 1)
            elif self._sensor_type == SENSOR_TVOC:
                tvoc_unit = self.coordinator.data.get(CONF_TVOC_UNIT, "ppb")
                tvoc_value = int(value)
                if tvoc_unit == "ppm":
                    tvoc_value /= 1000
                elif tvoc_unit == "mg/m³":
                    tvoc_value /= 1000 
                    tvoc_value *= 0.0409 
                    tvoc_value *= 111.1  # Approximate conversion factor
                self._attr_native_value = round(tvoc_value, 3)
                self._attr_native_unit_of_measurement = tvoc_unit
            else:
                self._attr_native_value = int(value)
            self.async_write_ha_state()
        except ValueError:
            _LOGGER.error("Invalid value received for %s: %s", self._sensor_type, value)

    @callback
    def update_battery_charging(self, is_charging):
        """Update the battery charging state."""
        if self._sensor_type == SENSOR_BATTERY:
            self._battery_charging = is_charging
            self.async_write_ha_state()

    @property
    def icon(self):
        """Return the icon of the sensor."""
        if self._sensor_type == SENSOR_BATTERY:
            if self._battery_charging:
                return "mdi:battery-charging"
            elif self._attr_native_value is not None:
                battery_level = int(self._attr_native_value)
                if battery_level <= 10:
                    return "mdi:battery-10"
                elif battery_level <= 20:
                    return "mdi:battery-20"
                elif battery_level <= 30:
                    return "mdi:battery-30"
                elif battery_level <= 40:
                    return "mdi:battery-40"
                elif battery_level <= 50:
                    return "mdi:battery-50"
                elif battery_level <= 60:
                    return "mdi:battery-60"
                elif battery_level <= 70:
                    return "mdi:battery-70"
                elif battery_level <= 80:
                    return "mdi:battery-80"
                elif battery_level <= 90:
                    return "mdi:battery-90"
                else:
                    return "mdi:battery"
        return super().icon

    async def publish_config(self):
        """Publish configuration message to MQTT."""
        update_interval = self.coordinator.data.get(CONF_UPDATE_INTERVAL, 15)
        payload = {
            ATTR_TYPE: DEFAULT_TYPE,
            ATTR_UP_ITVL: f"{int(update_interval)}",
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