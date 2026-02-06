"""Support for Qingping Device sensors."""
from __future__ import annotations

import json
import logging
from datetime import timedelta
import time, math
import asyncio

from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_MAC, CONF_MODEL, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN, MQTT_TOPIC_PREFIX,
    SENSOR_BATTERY, SENSOR_CO2, SENSOR_HUMIDITY, SENSOR_PM10, SENSOR_PM25, SENSOR_TEMPERATURE, SENSOR_TVOC, SENSOR_ETVOC,
    SENSOR_NOISE, SENSOR_PRESSURE, SENSOR_LIGHT, SENSOR_SIGNAL_STRENGTH, SENSOR_TLV_ETVOC,
    PERCENTAGE, PPM, PPB, CONCENTRATION, CONF_TVOC_UNIT, CONF_ETVOC_UNIT, DB,
    CONF_TEMPERATURE_OFFSET, CONF_HUMIDITY_OFFSET, CONF_UPDATE_INTERVAL,
    CONF_REPORT_INTERVAL, CONF_SAMPLE_INTERVAL,
    ATTR_TYPE, ATTR_UP_ITVL, ATTR_DURATION,
    DEFAULT_TYPE, DEFAULT_DURATION, TLV_MODELS, JSON_MODELS,
    CONF_REPORT_MODE, REPORT_MODE_HISTORIC, REPORT_MODE_REALTIME
)
from .tlv_decoder import tlv_decode, is_tlv_format
from .tlv_encoder import tlv_encode, int_to_bytes_little_endian

_LOGGER = logging.getLogger(__name__)

OFFLINE_TIMEOUT_REALTIME = 300  # 5 minutes for real-time mode
OFFLINE_TIMEOUT_HISTORIC = 900  # 15 minutes for historic mode
MQTT_PUBLISH_RETRY_LIMIT = 3
MQTT_PUBLISH_RETRY_DELAY = 5  # seconds
SETTING_CHANGE_DELAY = 5  # seconds delay before publishing setting changes

# Store pending setting publishes to debounce rapid changes
_pending_setting_publishes = {}

async def ensure_mqtt_connected(hass):
    """Ensure MQTT is connected before publishing."""
    for _ in range(5):  # Try up to 5 times
        if mqtt.is_connected(hass):
            return True
        await asyncio.sleep(1)
    return False

async def _auto_switch_report_mode_on_battery_state(hass, config_entry, mac, is_charging, model):
    """Automatically switch report mode based on battery charging state."""
    if model not in ["CGP22C", "CGP23W", "CGP22W"]:
        return
    
    from .tlv_encoder import tlv_encode, int_to_bytes_little_endian
    from .const import CONF_REPORT_MODE, REPORT_MODE_HISTORIC, REPORT_MODE_REALTIME
    
    # Get coordinator
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    # Determine mode based on charging state
    if is_charging:
        # Real-time mode when charging
        packets = {
            0x42: int_to_bytes_little_endian(21600, 2),   # Real-time for 6 hours
        }
        mode_name = "REAL-TIME (charging)"
        new_mode = REPORT_MODE_REALTIME
    else:
        # Historic mode when on battery
        packets = {
            0x42: int_to_bytes_little_endian(0, 2),   # Disable real-time
        }
        mode_name = "HISTORIC (on battery)"
        new_mode = REPORT_MODE_HISTORIC
    
    payload = tlv_encode(0x32, packets)
    topic = f"qingping/{mac}/down"
    
    await mqtt.async_publish(hass, topic, payload)
    
    # Update coordinator data
    coordinator.data[CONF_REPORT_MODE] = new_mode
    
    # Update config entry data
    new_data = dict(config_entry.data)
    new_data[CONF_REPORT_MODE] = new_mode
    hass.config_entries.async_update_entry(config_entry, data=new_data)
    
    # Refresh coordinator to update all entities
    await coordinator.async_request_refresh()
    
    _LOGGER.info(f"[{mac}] Auto-switched to {mode_name} based on battery state (timeout: {'5min' if is_charging else '15min'})")
    
async def publish_setting_change(hass: HomeAssistant, mac: str, setting_key: str, value: any) -> None:
    """Publish a single setting change to the device with debounce."""
    # Cancel any pending publish for this setting
    publish_key = f"{mac}_{setting_key}"
    if publish_key in _pending_setting_publishes:
        _pending_setting_publishes[publish_key].cancel()
    
    async def _delayed_publish():
        """Publish after delay."""
        try:
            await asyncio.sleep(SETTING_CHANGE_DELAY)
            
            if not await ensure_mqtt_connected(hass):
                _LOGGER.error("MQTT is not connected, cannot publish setting change")
                return
            
            payload = {
                "type": "17",
                "setting": {
                    setting_key: value
                }
            }
            
            topic = f"{MQTT_TOPIC_PREFIX}/{mac}/down"
            await mqtt.async_publish(hass, topic, json.dumps(payload))
            _LOGGER.info("Published setting change to %s: %s = %s", mac, setting_key, value)
            
        except Exception as err:
            _LOGGER.error("Failed to publish setting change: %s", err)
        finally:
            # Clean up the pending publish
            if publish_key in _pending_setting_publishes:
                del _pending_setting_publishes[publish_key]
    
    # Schedule the delayed publish
    task = asyncio.create_task(_delayed_publish())
    _pending_setting_publishes[publish_key] = task

async def _update_settings_from_device(hass: HomeAssistant, config_entry: ConfigEntry, settings: dict, model: str) -> None:
    """Update Home Assistant entities when settings are changed on the device."""
    _LOGGER.info("Starting _update_settings_from_device with settings: %s", settings)
    
    from .const import (
        CONF_TEMPERATURE_OFFSET, CONF_HUMIDITY_OFFSET,
        CONF_CO2_OFFSET, CONF_PM25_OFFSET, CONF_PM10_OFFSET,
        CONF_NOISE_OFFSET, CONF_TVOC_OFFSET, CONF_TVOC_INDEX_OFFSET,
        CONF_POWER_OFF_TIME, CONF_DISPLAY_OFF_TIME, CONF_NIGHT_MODE_START_TIME,
        CONF_NIGHT_MODE_END_TIME, CONF_AUTO_SLIDING_TIME, CONF_SCREENSAVER_TYPE,
        CONF_CO2_ASC
    )
    
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    native_temp_unit = hass.config.units.temperature_unit
    if native_temp_unit == UnitOfTemperature.FAHRENHEIT:
            unit_based_calc = (CONF_TEMPERATURE_OFFSET, lambda x: round((x / 100) * 9/5, 1))
    else:
            unit_based_calc = (CONF_TEMPERATURE_OFFSET, lambda x: round(x / 100, 1))
    updated = False
    
    # Map device settings to HA entity keys and conversion functions
    setting_mappings = {
        # Temperature offset: device sends value * 100, we need to divide by 100
        "temperature_offset": unit_based_calc,
        # Humidity offset: device sends value * 10, we need to divide by 10
        "humidity_offset": (CONF_HUMIDITY_OFFSET, lambda x: round(x / 10, 1)),
        # Other offsets: direct integer values
        "co2_offset": (CONF_CO2_OFFSET, int),
        "pm25_offset": (CONF_PM25_OFFSET, int),
        "pm10_offset": (CONF_PM10_OFFSET, int),
        "noise_offset": (CONF_NOISE_OFFSET, int),
        "tvoc_zoom": (CONF_TVOC_OFFSET, lambda x: round(x / 10, 1)),
        "tvoc_index_zoom": (CONF_TVOC_INDEX_OFFSET, lambda x: round(x / 10, 1)),
        # CGDN1 specific settings
        "power_off_time": (CONF_POWER_OFF_TIME, int),
        "display_off_time": (CONF_DISPLAY_OFF_TIME, int),
        "night_mode_start_time": (CONF_NIGHT_MODE_START_TIME, int),
        "night_mode_end_time": (CONF_NIGHT_MODE_END_TIME, int),
        "auto_slideing_time": (CONF_AUTO_SLIDING_TIME, int),
        "screensaver_type": (CONF_SCREENSAVER_TYPE, int),
        "co2_asc": (CONF_CO2_ASC, int),
    }
    
    for device_key, value in settings.items():
        _LOGGER.info("Processing setting: %s = %s", device_key, value)
        if device_key in setting_mappings:
            ha_key, converter = setting_mappings[device_key]
            try:
                converted_value = converter(value)
                _LOGGER.info("Converted %s: %s -> %s", device_key, value, converted_value)
                
                # Update coordinator data
                if coordinator.data.get(ha_key) != converted_value:
                    coordinator.data[ha_key] = converted_value
                    updated = True
                    _LOGGER.info("Updated %s from device: %s", ha_key, converted_value)
                    
                    # Update config entry
                    new_data = dict(config_entry.data)
                    new_data[ha_key] = converted_value
                    hass.config_entries.async_update_entry(config_entry, data=new_data)
                else:
                    _LOGGER.info("Setting %s already has value %s, no update needed", ha_key, converted_value)
                    
            except (ValueError, TypeError) as err:
                _LOGGER.error("Failed to convert setting %s with value %s: %s", device_key, value, err)
        else:
            _LOGGER.debug("Unknown setting key from device: %s", device_key)
    
    # Refresh coordinator to update all entities
    if updated:
        _LOGGER.info("Settings updated, refreshing coordinator")
        await coordinator.async_request_refresh()
    else:
        _LOGGER.info("No settings were updated")


async def _send_initial_tlv_config(hass, config_entry, mac, model):
    """Send initial default configuration to TLV device on first setup."""
    from .tlv_encoder import tlv_encode, int_to_bytes_little_endian
    from .const import (
        CONF_REPORT_MODE, REPORT_MODE_REALTIME, CONF_REPORT_INTERVAL, 
        CONF_SAMPLE_INTERVAL, CONF_TEMPERATURE_UNIT
    )
    
    # Check if this is first time setup (no report mode set yet)
    if CONF_REPORT_MODE in config_entry.data:
        _LOGGER.info(f"[{mac}] Device already configured, skipping initial config")
        return
    
    _LOGGER.info(f"[{mac}] Sending initial default configuration to new TLV device")
    
    # Get Home Assistant's native temperature unit
    native_temp_unit = hass.config.units.temperature_unit
    temp_unit = "fahrenheit" if native_temp_unit == UnitOfTemperature.FAHRENHEIT else "celsius"
    
    # Set default values in config entry
    new_data = dict(config_entry.data)
    new_data[CONF_REPORT_MODE] = REPORT_MODE_REALTIME  # Real-time by default
    new_data[CONF_REPORT_INTERVAL] = 10  # 10 minutes (minimum)
    new_data[CONF_SAMPLE_INTERVAL] = 60  # 60 seconds
    new_data[CONF_TEMPERATURE_UNIT] = temp_unit
    
    # Add CO2 work interval for CGP22C
    if model == "CGP22C":
        new_data["co2_work_interval"] = 10  # 10 minutes
    
    hass.config_entries.async_update_entry(config_entry, data=new_data)
    
    # Send default configuration commands
    packets = {
        0x42: int_to_bytes_little_endian(21600, 2),  # Real-time for 6 hours
        0x19: bytes([1 if temp_unit == "fahrenheit" else 0])  # Temperature unit
    }
    
    # Add CO2 work interval for CGP22C
    if model == "CGP22C":
        packets[0x3C] = int_to_bytes_little_endian(10, 2)
    
    payload = tlv_encode(0x32, packets)
    topic = f"qingping/{mac}/down"
    
    await mqtt.async_publish(hass, topic, payload)
    _LOGGER.info(f"[{mac}] Initial config sent: Real-time mode, temp unit: {temp_unit}")


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qingping Device sensor based on a config entry."""
    mac = config_entry.data[CONF_MAC]
    name = config_entry.data[CONF_NAME]
    model = config_entry.data[CONF_MODEL]
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    native_temp_unit = hass.config.units.temperature_unit
    
    # Initialize coordinator data with default values to prevent "None" warnings
    if model == "CGS1" and CONF_TVOC_UNIT not in coordinator.data:
        coordinator.data[CONF_TVOC_UNIT] = config_entry.data.get(CONF_TVOC_UNIT, "ppb")
    elif model == "CGS2" and CONF_ETVOC_UNIT not in coordinator.data:
        coordinator.data[CONF_ETVOC_UNIT] = config_entry.data.get(CONF_ETVOC_UNIT, "index")

    async def async_update_data():
        """Fetch data from API endpoint."""
        # This is a placeholder. In a real scenario, you might
        # fetch data from an API or process local data here.
        return {}

    device_info = {
        "identifiers": {(DOMAIN, mac)},
        "name": name,
        "manufacturer": "Qingping",
        "model": model,
    }

    status_sensor = QingpingDeviceStatusSensor(coordinator, config_entry, mac, name, device_info)
    firmware_sensor = QingpingDeviceFirmwareSensor(coordinator, config_entry, mac, name, device_info)
    mac_sensor = QingpingDeviceMACSensor(coordinator, config_entry, mac, name, device_info)
    battery_state = QingpingDeviceBatteryStateSensor(coordinator, config_entry, mac, name, device_info)

    # Only create type_sensor for JSON devices (not TLV)
    if model in JSON_MODELS:
        type_sensor = QingpingDeviceTypeSensor(coordinator, config_entry, mac, name, device_info)
        sensors = [
            status_sensor,
            firmware_sensor,
            type_sensor,
            mac_sensor,
        ]
    else:
        # TLV devices - no type sensor
        sensors = [
            status_sensor,
            firmware_sensor,
            mac_sensor,
        ]

    #sensors.append(QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_BATTERY, "Battery", PERCENTAGE, SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, device_info))
    if model in ["CGS1", "CGS2", "CGDN1", "CGP22C", "CGP22W", "CGP23W"]:
        sensors.append(battery_state)
        battery_sensor = QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_BATTERY, "Battery", PERCENTAGE, SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, device_info)
        battery_sensor._attr_entity_category = EntityCategory.DIAGNOSTIC
        sensors.append(battery_sensor)
    sensors.append(QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_TEMPERATURE, "Temperature", native_temp_unit, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, device_info))
    sensors.append(QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_HUMIDITY, "Humidity", PERCENTAGE, SensorDeviceClass.HUMIDITY, SensorStateClass.MEASUREMENT, device_info))

    
    # Add CO2 for models that have it
    if model in ["CGS1", "CGS2", "CGDN1", "CGP22C", "CGR1W", "CGR1PW"]:
        sensors.append(QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_CO2, "CO2", PPM, SensorDeviceClass.CO2, SensorStateClass.MEASUREMENT, device_info))
    
    # Add PM sensors only for models that have them
    if model in ["CGS1", "CGS2", "CGDN1", "CGR1W", "CGR1PW"]:
        sensors.append(QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_PM10, "PM10", CONCENTRATION, SensorDeviceClass.PM10, SensorStateClass.MEASUREMENT, device_info))
        sensors.append(QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_PM25, "PM25", CONCENTRATION, SensorDeviceClass.PM25, SensorStateClass.MEASUREMENT, device_info))
        



    if model == "CGS1":
        sensors.append(QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_TVOC, "TVOC", PPB, SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS, SensorStateClass.MEASUREMENT, device_info))
    elif model == "CGS2":
        sensors.append(QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_ETVOC, "eTVOC", None, SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS, SensorStateClass.MEASUREMENT, device_info))
        sensors.append(QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_NOISE, "Noise", DB, SensorDeviceClass.SOUND_PRESSURE, SensorStateClass.MEASUREMENT, device_info))
    elif model == "CGP23W":  # NEW
        sensors.append(QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_PRESSURE, "Pressure", "kPa", SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT, device_info))
    elif model in ["CGR1W", "CGR1PW"]:  # NEW
        sensors.append(QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_LIGHT, "Light", "lx", SensorDeviceClass.ILLUMINANCE, SensorStateClass.MEASUREMENT, device_info))
        sensors.append(QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_TLV_ETVOC, "eTVOC", None, SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS, SensorStateClass.MEASUREMENT, device_info))
        sensors.append(QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_NOISE, "Noise", DB, SensorDeviceClass.SOUND_PRESSURE, SensorStateClass.MEASUREMENT, device_info))
    
    # Add signal strength for TLV devices
    if model in TLV_MODELS:
        signal_sensor = QingpingDeviceSensor(coordinator, config_entry, mac, name, SENSOR_SIGNAL_STRENGTH, "Signal Strength", "dBm", SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, device_info)
        signal_sensor._attr_entity_category = EntityCategory.DIAGNOSTIC
        sensors.append(signal_sensor)

    async_add_entities(sensors)

    # Store sensors in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(config_entry.entry_id, {})
    hass.data[DOMAIN][config_entry.entry_id]["sensors"] = sensors
    
    # Send initial configuration for new TLV devices
    if model in TLV_MODELS:
        await _send_initial_tlv_config(hass, config_entry, mac, model)

    @callback
    def message_received(message):
        """Handle new MQTT messages."""
        try:
            # Check if TLV binary format
            if is_tlv_format(message.payload):
                _handle_tlv_message(message)
                return
            
            # Otherwise handle as JSON
            payload = json.loads(message.payload)
            
            if not isinstance(payload, dict):
                _LOGGER.error("Payload is not a dictionary")
                return

            # Check message type first - type 28 (settings) messages don't include MAC
            message_type = payload.get("type")
            
            # For messages with MAC, verify it matches
            received_mac = payload.get("mac", "").replace(":", "").upper()
            expected_mac = mac.replace(":", "").upper()
            
            # Skip MAC check for messages without MAC (type 28, 13, 10, 17, etc.)
            # We're subscribed to this device's specific topic, so we know it's for us
            if received_mac and received_mac != expected_mac:
                _LOGGER.debug("Received message for a different device. Expected: %s, Got: %s", expected_mac, received_mac)
                return
            
            _LOGGER.debug("Processing MQTT message type %s for device %s", message_type, mac)
            
            # Update timestamp first - any message from device means it's online
            # Always use current system time, not device's timestamp which may be unreliable
            current_timestamp = int(time.time())
            if status_sensor.hass:
                status_sensor.update_timestamp(current_timestamp)

            firmware_version = payload.get("version")
            if firmware_version is not None:
                if firmware_sensor.hass:
                    firmware_sensor.update_version(firmware_version)

            device_type = payload.get("type")
            if device_type is not None:
                if type_sensor.hass:
                    type_sensor.update_type(device_type)

            mac_address = payload.get("mac")
            if mac_address is not None:
                if mac_sensor.hass:
                    mac_sensor.update_mac(mac_address)

            # Handle type 28 messages (device settings update) - Check BEFORE sensorData
            if message_type == 28 or message_type == "28":
                _LOGGER.info("Type 28 settings update received for device %s", mac)
                settings = payload.get("setting", {})
                if settings:
                    hass.async_create_task(_update_settings_from_device(hass, config_entry, settings, model))
                else:
                    _LOGGER.warning("Type 28 message has no settings dict")
                return  # Don't process as sensor data

            sensor_data = payload.get("sensorData")
            if not isinstance(sensor_data, list) or not sensor_data:
                _LOGGER.debug("No valid sensorData in payload, possibly a config response or device just powered on")
                # Device is online, just waiting for sensor data
                return
            #if len(sensor_data) == 1:
            if message_type not in [17, 13, "17", "13"]:
                #ignore type 17 sensor data                
                for data in sensor_data:
                    battery_charging = None
                    battery_status = None
                    if SENSOR_BATTERY in data:
                        battery_data = data[SENSOR_BATTERY]
                        if isinstance(battery_data, dict):
                            battery_status = battery_data.get("status")
                            if battery_status is not None:
                                battery_charging = (battery_status == 1)  # Explicitly True or False
                    
                    # Update battery state sensor first if we have status
                    if battery_status is not None and battery_state.hass:
                        battery_state.update_battery_state(battery_status)
                    
                    for sensor in sensors[5:]:  # Skip status, firmware, mac, type, and battery_state sensors
                        if not sensor.hass:
                            continue
                        if sensor._sensor_type in data:
                            sensor_data = data[sensor._sensor_type]
                            if isinstance(sensor_data, dict):
                                value = sensor_data.get("value")
                                status = sensor_data.get("status")
                                # Check if PM sensor is disabled (value=99999)
                                if sensor._sensor_type in [SENSOR_PM10, SENSOR_PM25] and value == 99999:
                                    sensor.set_unavailable()
                                elif value is not None:
                                    sensor.update_from_latest_data(value)
                                    if sensor._sensor_type == SENSOR_BATTERY and battery_charging is not None:
                                        sensor.update_battery_charging(battery_charging)
                            else:
                                # Handle non-dict values (backward compatibility)
                                value = sensor_data
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

    def _handle_tlv_message(message):
        """Handle TLV binary format messages."""
        try:
            cmd = message.payload[2] if len(message.payload) > 2 else 0
            # Map CMD codes to descriptions for logging
            cmd_names = {
                0x31: "Unknown/Reserved",
                0x32: "Configuration",
                0x34: "Event Reporting",
                0x35: "Button Press",
                0x39: "Configuration Query",
                0x41: "Current Reading",
                0x42: "Historical Data",
                0x43: "Regular Data",
                0x47: "Server Config Push",
            }
            cmd_name = cmd_names.get(cmd, "Unknown")
            _LOGGER.debug(f"[TLV] Received CMD: 0x{cmd:02x} ({cmd_name})")

            decoded = tlv_decode(message.payload)
            if not decoded:
                return
            
            # Update status
            current_timestamp = int(time.time())
            if status_sensor.hass:
                status_sensor.update_timestamp(current_timestamp)
            
            # Update firmware
            if "version" in decoded and firmware_sensor.hass:
                firmware_sensor.update_version(decoded["version"])
            
            # Update MAC
            if mac_sensor.hass:
                mac_sensor.update_mac(mac)
            
            # Update battery state and auto-switch report mode
            if "batteryCharging" in decoded and battery_state.hass:
                new_charging_state = decoded["batteryCharging"]
                old_charging_state = battery_state._attr_native_value == "Charging"
                
                battery_state.update_battery_state(1 if new_charging_state else 0)
                
                # Auto-switch report mode if charging state changed
                if new_charging_state != old_charging_state:
                    _LOGGER.info(f"[{mac}] Battery charging state changed: {old_charging_state} -> {new_charging_state}")
                    asyncio.create_task(
                        _auto_switch_report_mode_on_battery_state(
                            hass, config_entry, mac, new_charging_state, model
                        )
                    )
            
            # Process sensor data
            sensor_data = decoded.get("sensorData", [])
            if not sensor_data:
                return
            
            # IMPORTANT: Prioritize current data based on CMD type
            # CMD 0x41 = current reading (use first/only entry)
            # CMD 0x42 = historical data (use LAST entry which is most recent)
            # CMD 0x43 = real-time data (use first/only entry)
            if cmd == 0x42 and isinstance(sensor_data, list) and len(sensor_data) > 1:
                # For historical data (CMD 0x42), use the LAST (most recent) reading
                data = sensor_data[-1]
                _LOGGER.debug(f"[TLV] CMD 0x42: Using most recent historical data (entry {len(sensor_data)} of {len(sensor_data)})")
            else:
                # For current/real-time data, use first entry
                data = sensor_data[0] if isinstance(sensor_data, list) else sensor_data
            if model in ["CGR1W", "CGR1PW"]:
                all_sensors = sensors[3:]
            else:
                all_sensors = sensors[4:]
            # Update sensors
            for sensor in all_sensors:
                if not sensor.hass:
                    continue
                
                value = None
                if sensor._sensor_type == SENSOR_TEMPERATURE and "temperature" in data:
                    value = data["temperature"]
                elif sensor._sensor_type == SENSOR_HUMIDITY and "humidity" in data:
                    value = data["humidity"]
                elif sensor._sensor_type == SENSOR_CO2 and "co2" in data:
                    value = data["co2"]
                elif sensor._sensor_type == SENSOR_PM25 and "pm25" in data:
                    value = data["pm25"]
                elif sensor._sensor_type == SENSOR_PM10 and "pm10" in data:
                    value = data["pm10"]
                elif sensor._sensor_type == SENSOR_TVOC and "tvoc" in data:
                    value = data["tvoc"]
                elif sensor._sensor_type == SENSOR_TLV_ETVOC and "tvoc" in data:
                    value = data["tvoc"]
                elif sensor._sensor_type == SENSOR_NOISE and "noise" in data:
                    value = data["noise"]
                elif sensor._sensor_type == SENSOR_LIGHT and "light" in data:
                    value = data["light"]
                elif sensor._sensor_type == SENSOR_PRESSURE and "pressure" in data:
                    value = data["pressure"]
                elif sensor._sensor_type == SENSOR_BATTERY:
                    # Battery can be in decoded (top level) or data (sensorData)
                    if "battery" in decoded:
                        value = decoded["battery"]
                    elif "battery" in data:
                        value = data["battery"]
                    if decoded.get("batteryCharging") or data.get("batteryCharging"):
                        sensor.update_battery_charging(True)
                elif sensor._sensor_type == SENSOR_SIGNAL_STRENGTH:
                    # Signal can be signalStrength (top) or rssi (sensorData)
                    if "signalStrength" in decoded:
                        value = decoded["signalStrength"]
                        if value >= 128:
                            value -= 256
                    elif "rssi" in data:
                        value = data["rssi"]
                
                if value is not None:
                    sensor.update_from_latest_data(value)
        
        except Exception as e:
            _LOGGER.error("Error processing TLV message: %s", str(e))

    await mqtt.async_subscribe(
        hass, f"{MQTT_TOPIC_PREFIX}/{mac}/up", message_received, 1, encoding=None
    )
    _LOGGER.info("Subscribed to MQTT topic: %s/%s/up", MQTT_TOPIC_PREFIX, mac)

    # Set up timer for periodic publishing
    async def publish_config_wrapper(*args):
        if await ensure_mqtt_connected(hass):
            # Find first sensor with publish_config method
            for sensor in sensors:
                if isinstance(sensor, QingpingDeviceSensor) and hasattr(sensor, 'publish_config'):
                    await sensor.publish_config()
                    break
        else:
            _LOGGER.error("Failed to connect to MQTT for periodic config publish")

    hass.data[DOMAIN][config_entry.entry_id]["remove_timer"] = async_track_time_interval(
        hass, publish_config_wrapper, timedelta(seconds=int(DEFAULT_DURATION))
    )

    # Publish config immediately upon setup with a delay to ensure entities are ready
    async def delayed_publish():
        await asyncio.sleep(2)  # Wait 2 seconds for entities to be fully added
        if await ensure_mqtt_connected(hass):
            await publish_config_wrapper()
        else:
            _LOGGER.error("Failed to connect to MQTT for initial config publish")
    
    asyncio.create_task(delayed_publish())

class QingpingDeviceStatusSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Qingping Device status sensor."""

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
        old_timestamp = self._last_timestamp
        self._last_timestamp = int(timestamp)
        old_status = self._attr_native_value
        if old_timestamp == 0 or old_status == "offline":
            _LOGGER.info("Device %s came online (timestamp: %s)", self._mac, timestamp)
        self._update_status()
        # Log if status changed unexpectedly
        if old_status == "online" and self._attr_native_value == "offline":
            _LOGGER.error("Device %s immediately went offline after timestamp update! old_ts=%s, new_ts=%s, current_time=%s", 
                         self._mac, old_timestamp, self._last_timestamp, int(time.time()))

    @callback
    def _update_status(self):
        """Update the status based on the last timestamp."""
        if not self.hass:
            return
        
        # Get model and report mode to determine timeout
        model = self._config_entry.data.get(CONF_MODEL, "CGS1")
        
        # Determine timeout based on device type and mode
        if model in TLV_MODELS:
            report_mode = self.coordinator.data.get(CONF_REPORT_MODE, REPORT_MODE_HISTORIC)
            timeout = OFFLINE_TIMEOUT_REALTIME if report_mode == REPORT_MODE_REALTIME else OFFLINE_TIMEOUT_HISTORIC
        else:
            # JSON devices use standard timeout
            timeout = OFFLINE_TIMEOUT_REALTIME
        
        current_time = int(time.time())
        time_since_last_msg = current_time - self._last_timestamp
        new_status = "online" if time_since_last_msg <= timeout else "offline"
        
        if self._attr_native_value != new_status:
            old_status = self._attr_native_value
            self._attr_native_value = new_status
            self.async_write_ha_state()
            _LOGGER.info("Device %s status changed from %s to %s (time since last message: %s seconds, timeout: %s)", 
                        self._mac, old_status, new_status, time_since_last_msg, timeout)
            
            # Update other sensors' availability
            sensors = self.hass.data[DOMAIN][self._config_entry.entry_id].get("sensors", [])
            for sensor in sensors:
                if isinstance(sensor, QingpingDeviceSensor) and sensor.hass:
                    sensor.async_write_ha_state()
            
            # Call publish_config when status changes from offline to online
            if self._last_status == "offline" and new_status == "online":
                _LOGGER.info("Device %s recovered from offline, publishing config", self._mac)
                asyncio.create_task(self._publish_config_on_status_change())
            
            self._last_status = new_status

    async def _publish_config_on_status_change(self):
        """Publish config when status changes from offline to online."""
        if not self.hass:
            return
        # Add a small delay to let the device fully come online
        await asyncio.sleep(2)
        sensors = self.hass.data[DOMAIN][self._config_entry.entry_id].get("sensors", [])
        for sensor in sensors:
            if isinstance(sensor, QingpingDeviceSensor):
                await sensor.publish_config()
                break  # We only need to call it once                

    async def async_added_to_hass(self):
        """Set up a timer to regularly update the status."""
        await super().async_added_to_hass()

        # Immediately check if we should be online based on recent activity
        self._update_status()

        async def update_status(*_):
            self._update_status()

        self.async_on_remove(async_track_time_interval(
            self.hass, update_status, timedelta(seconds=60)
        ))

class QingpingDeviceFirmwareSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Qingping Device firmware sensor."""

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

class QingpingDeviceMACSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Qingping Device mac sensor."""

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

class QingpingDeviceBatteryStateSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Qingping Device battery state sensor."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} Battery State"
        self._attr_unique_id = f"{mac}_battery_state"
        self._attr_device_info = device_info
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_value = "Discharging"

    @callback
    def update_battery_state(self, status):
        """Update the battery state."""
        self._previous_charging_state = (self._attr_native_value == "Charging")
        
        if status == 1:
            self._attr_native_value = "Charging"
        elif status == 2:
            self._attr_native_value = "Fully Charged"
        elif status == 0:
            self._attr_native_value = "Discharging"
        else:
            self._attr_native_value = "Unknown"
        self.async_write_ha_state()

class QingpingDeviceTypeSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Qingping Device type sensor."""

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
        self._attr_force_update = False
        self._attr_entity_registry_enabled_default = False

    @callback
    def update_type(self, device_type):
        """Update the device type."""
        self._attr_native_value = device_type
        self.async_write_ha_state()


def _get_voc_device_class(unit: str) -> SensorDeviceClass:
    """Get appropriate device class for VOC sensor based on unit."""
    if unit == "index":
        return SensorDeviceClass.AQI  # Air Quality Index
    elif unit in ["ppb", "ppm"]:
        return SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS
    elif unit == "mg/m³":
        return SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS
    else:
        return SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS  # default


class QingpingDeviceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Qingping Device sensor."""

    def __init__(self, coordinator, config_entry, mac, name, sensor_type, cln_name, unit, device_class, state_class, device_info):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._sensor_type = sensor_type
        self._attr_name = f"{name} {cln_name}"
        self._attr_unique_id = f"{mac}_{sensor_type}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = device_info
        self._battery_charging = False
        self._is_unavailable = False

    @callback
    def update_from_latest_data(self, value):
        """Update the sensor with the latest data."""
        try:
            if self._sensor_type == SENSOR_TEMPERATURE:
                temp_celsius = float(value)
                if self._attr_native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT:
                    # Convert to Fahrenheit
                    temp_fahrenheit = (temp_celsius * 9/5) + 32
                    self._attr_native_value = round(float(temp_fahrenheit), 1)
                else:
                    self._attr_native_value = round(float(temp_celsius), 1)
            elif self._sensor_type == SENSOR_HUMIDITY:
                self._attr_native_value = round(float(value), 1)
            elif self._sensor_type == SENSOR_PRESSURE:
                self._attr_native_value = round(float(value), 2)
            elif self._sensor_type == SENSOR_TLV_ETVOC or self._sensor_type == SENSOR_TVOC:
                model = self._config_entry.data.get(CONF_MODEL)    
                if model == "CGS1":
                    # CGS1 JSON device - uses TVOC with ppb/ppm/mg/m³
                    tvoc_unit = self.coordinator.data.get(CONF_TVOC_UNIT, "ppb")
                    if tvoc_unit and tvoc_unit != self._attr_native_unit_of_measurement:
                        old_unit = self._attr_native_unit_of_measurement
                        current_value = self._attr_native_value 
                    if tvoc_unit is None or tvoc_unit == "":
                        tvoc_unit = "ppb"
                    tvoc_value = int(value)
                    if tvoc_unit == "ppm":
                        tvoc_value /= 1000
                    elif tvoc_unit == "mg/m³":
                        tvoc_value /= 218.77
                    self._attr_native_value = round(tvoc_value, 3)
                    self._attr_native_unit_of_measurement = tvoc_unit
                    self._attr_device_class = _get_voc_device_class(tvoc_unit)
                else:
                    # TLV devices ("CGR1W", "CGR1PW") - uses eTVOC with index/ppb/mg/m³
                    etvoc_unit = self.coordinator.data.get(CONF_ETVOC_UNIT, "index")
                    if etvoc_unit and etvoc_unit != self._attr_native_unit_of_measurement:
                        old_unit = self._attr_native_unit_of_measurement
                        current_value = self._attr_native_value                         
                    etvoc_value = int(value)
                    if etvoc_unit == "ppb":
                        # Convert VOC index to ppb
                        etvoc_value = (math.log(501-etvoc_value) - 6.24) * -2215.4
                        etvoc_value = int(round(float(etvoc_value), 0))
                    elif etvoc_unit == "mg/m³":
                        # Convert VOC index to mg/m³
                        etvoc_value = (math.log(501-etvoc_value) - 6.24) * -2215.4
                        etvoc_value = (etvoc_value*4.5*10 + 5) / 10 / 1000
                        etvoc_value = round(etvoc_value, 3)
                    self._attr_native_value = etvoc_value
                    # Set unit to None if "index" is selected (no unit), otherwise use the unit
                    self._attr_native_unit_of_measurement = None if etvoc_unit == "index" else etvoc_unit
                    self._attr_device_class = _get_voc_device_class(etvoc_unit)
            elif self._sensor_type == SENSOR_ETVOC:
                etvoc_unit = self.coordinator.data.get(CONF_ETVOC_UNIT, "index")
                if etvoc_unit and etvoc_unit != self._attr_native_unit_of_measurement:
                    old_unit = self._attr_native_unit_of_measurement
                    current_value = self._attr_native_value
                etvoc_value = int(value)
                if etvoc_unit == "ppb":
                    # Convert VOC index to ppb (this is an approximate conversion)
                    #etvoc_value = (etvoc_value * 5) + 35
                    etvoc_value = (math.log(501-etvoc_value) - 6.24) * -2215.4
                    etvoc_value = int(round(float(etvoc_value), 0))
                elif etvoc_unit == "mg/m³":
                    # Convert VOC index to mg/m³ (this is an approximate conversion)
                    etvoc_value = (math.log(501-etvoc_value) - 6.24) * -2215.4
                    etvoc_value = (etvoc_value*4.5*10 + 5) / 10 / 1000
                    etvoc_value = round(etvoc_value, 3)
                self._attr_native_value = etvoc_value
                # Set unit to None if "index" is selected (no unit), otherwise use the unit
                self._attr_native_unit_of_measurement = None if etvoc_unit == "index" else etvoc_unit
                self._attr_device_class = _get_voc_device_class(etvoc_unit)
            else:
                self._attr_native_value = int(value)
            self._is_unavailable = False
            self.async_write_ha_state()
        except ValueError:
            _LOGGER.error("Invalid value received for %s: %s", self._sensor_type, value)

    @callback
    def update_battery_charging(self, is_charging):
        """Update the battery charging state."""
        if self._sensor_type == SENSOR_BATTERY:
            self._battery_charging = is_charging
            self.async_write_ha_state()

    @callback
    def set_unavailable(self):
        """Set sensor as unavailable."""
        self._is_unavailable = True
        self._attr_native_value = None
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
        # Check if entity has been added to hass yet
        if not self.hass:
            _LOGGER.debug(f"[{self._mac}] Sensor not yet added to hass, skipping config publish")
            return
            
        update_interval = self.coordinator.data.get(CONF_UPDATE_INTERVAL, 15)
        topic = f"{MQTT_TOPIC_PREFIX}/{self._mac}/down"
        
        # Check if TLV device
        model = self._config_entry.data.get(CONF_MODEL, "CGS1")
        if model in TLV_MODELS:
            # Use TLV binary format (CMD 0x32)
            # TLV devices use report mode instead of numeric interval
            report_mode = self._config_entry.data.get(CONF_REPORT_MODE, REPORT_MODE_HISTORIC)
            
            packets = {}
            
            if report_mode == REPORT_MODE_REALTIME:
                # Real-time mode: Enable real-time for 6 hours
                packets[0x42] = int_to_bytes_little_endian(21600, 2)
                _LOGGER.info(f"[{self._mac}] TLV config: REAL-TIME mode (fast updates, drains battery)")
            else:
                # Historic mode: Disable real-time
                packets[0x42] = int_to_bytes_little_endian(0, 2)
                _LOGGER.info(f"[{self._mac}] TLV config: HISTORIC mode (slow updates, saves battery)")
            
            payload = tlv_encode(0x32, packets)
        else:
            # Use JSON format for old devices (CGS1, CGS2, CGDN1)
            payload = json.dumps({
                ATTR_TYPE: DEFAULT_TYPE,
                ATTR_UP_ITVL: f"{int(update_interval)}",
                ATTR_DURATION: DEFAULT_DURATION
            })

        for attempt in range(MQTT_PUBLISH_RETRY_LIMIT):
            if not await ensure_mqtt_connected(self.hass):
                _LOGGER.error("MQTT is not connected")
                return
            try:
                await mqtt.async_publish(self.hass, topic, payload)
                _LOGGER.info(f"Published config to {topic}")
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
        if not self.hass:
            return False
        sensors = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id, {}).get("sensors", [])
        status_sensor = next((sensor for sensor in sensors if isinstance(sensor, QingpingDeviceStatusSensor)), None)
        is_online = status_sensor.native_value == "online" if status_sensor else False
        
        # For PM sensors, also check if they are disabled
        if self._sensor_type in [SENSOR_PM10, SENSOR_PM25]:
            return is_online and not self._is_unavailable
        
        return is_online

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up the timer when entity is removed."""
        if self.hass and self._config_entry.entry_id in self.hass.data.get(DOMAIN, {}):
            remove_timer = self.hass.data[DOMAIN][self._config_entry.entry_id].get("remove_timer")
            if remove_timer:
                remove_timer()
        await super().async_will_remove_from_hass()