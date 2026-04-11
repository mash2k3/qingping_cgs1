"""Support for Qingping Device number entities."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_MAC, CONF_MODEL, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import (
    DOMAIN, CONF_TEMPERATURE_OFFSET, CONF_HUMIDITY_OFFSET, DEFAULT_OFFSET,
    CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL,
    CONF_REPORT_INTERVAL, CONF_SAMPLE_INTERVAL,
    CONF_CO2_OFFSET, CONF_PM25_OFFSET, CONF_PM10_OFFSET,
    CONF_NOISE_OFFSET, CONF_TVOC_OFFSET, CONF_TVOC_INDEX_OFFSET, CONF_PRESSURE_OFFSET,
    CONF_POWER_OFF_TIME, CONF_AUTO_SLIDING_TIME, DEFAULT_SENSOR_OFFSET,
    CONF_SCREENSAVER_TYPE, CONF_TIMEZONE,
    TLV_MODELS, JSON_MODELS, ADV_MODELS
)
from .tlv_encoder import tlv_encode, int_to_bytes_little_endian

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qingping Device number inputs from a config entry."""
    mac = config_entry.data[CONF_MAC]
    name = config_entry.data[CONF_NAME]
    model = config_entry.data[CONF_MODEL]
    if model in ADV_MODELS:
        return
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    native_temp_unit = hass.config.units.temperature_unit

    device_info = {
        "identifiers": {(DOMAIN, mac)},
        "name": name,
        "manufacturer": "Qingping",
        "model": model,
    }

    entities = []

    # TLV devices (CGP22C, CGP23W, CGP22W, CGR1W, CGR1PW)
    if model in TLV_MODELS:
        # Report and Sample intervals (for historic mode)
        entities.append(
            QingpingTLVReportIntervalNumber(
                coordinator, config_entry, mac, name, device_info
            )
        )
        entities.append(
            QingpingTLVSampleIntervalNumber(
                coordinator, config_entry, mac, name, device_info
            )
        )
        
        # Temperature offset - use native temperature unit
        if native_temp_unit == UnitOfTemperature.FAHRENHEIT:
            temp_min, temp_max = -18.0, 18.0  # About -10°C to +10°C in Fahrenheit
            temp_step = 0.2
        else:
            temp_min, temp_max = -10.0, 10.0
            temp_step = 0.1
            
        entities.append(
            QingpingTLVOffsetNumber(
                coordinator, config_entry, mac, name, "Temperature Offset",
                CONF_TEMPERATURE_OFFSET, device_info, 0x46,
                temp_min, temp_max, temp_step, native_temp_unit
            )
        )
        # Humidity offset
        entities.append(
            QingpingTLVOffsetNumber(
                coordinator, config_entry, mac, name, "Humidity Offset",
                CONF_HUMIDITY_OFFSET, device_info, 0x48,
                -20.0, 20.0, 0.1, "%"
            )
        )
        # CO2 offset (only for models with CO2)
        if model in ["CGP22C", "CGR1W", "CGR1PW"]:
            entities.append(
                QingpingTLVOffsetNumber(
                    coordinator, config_entry, mac, name, "CO2 Offset",
                    CONF_CO2_OFFSET, device_info, 0x45,
                    -500, 500, 1, "ppm"
                )
            )
        
        # Pressure offset (only for CGP23W)
        if model == "CGP23W":
            entities.append(
                QingpingTLVOffsetNumber(
                    coordinator, config_entry, mac, name, "Pressure Offset",
                    CONF_PRESSURE_OFFSET, device_info, 0x31,
                    -10.0, 10.0, 0.1, "kPa"
                )
            )
        
        # PM2.5 and PM10 offsets (for "CGR1W", "CGR1PW")
        if model in ["CGR1W", "CGR1PW"]:
            entities.append(
                QingpingTLVOffsetNumber(
                    coordinator, config_entry, mac, name, "PM2.5 Offset",
                    CONF_PM25_OFFSET, device_info, 0x4B,
                    -500, 500, 1, "µg/m³"
                )
            )
            entities.append(
                QingpingTLVOffsetNumber(
                    coordinator, config_entry, mac, name, "PM10 Offset",
                    CONF_PM10_OFFSET, device_info, 0x4D,
                    -500, 500, 1, "µg/m³"
                )
            )
        # Power off time
        if model == "CGP22C":
            entities.append(
                QingpingTLVPowerOffTimeNumber(
                    coordinator, config_entry, mac, name, device_info
                )
            )        
            # CO2 work interval (only for CGP22C with CO2 sensor)        
            entities.append(
                QingpingTLVCO2WorkIntervalNumber(
                    coordinator, config_entry, mac, name, device_info
                )
            )

    # JSON devices (CGS1, CGS2, CGDN1) - Use existing offset system
    else:
        step = 0.1 if native_temp_unit == UnitOfTemperature.FAHRENHEIT else 1
        
        entities.extend([
            QingpingDeviceOffsetNumber(
                coordinator, config_entry, mac, name, "Temp Offset",
                CONF_TEMPERATURE_OFFSET, device_info, native_temp_unit, step
            ),
            QingpingDeviceOffsetNumber(
                coordinator, config_entry, mac, name, "Humidity Offset",
                CONF_HUMIDITY_OFFSET, device_info, "%", step
            ),
            QingpingDeviceUpdateIntervalNumber(
                coordinator, config_entry, mac, name, device_info
            ),
            QingpingDeviceSensorOffsetNumber(
                coordinator, config_entry, mac, name, "CO2 Offset",
                CONF_CO2_OFFSET, device_info, "ppm"
            ),
        ])

        # Model-specific entities
        if model in ["CGS1", "CGS2", "CGDN1"]:
            entities.append(
                QingpingDeviceSensorOffsetNumber(
                    coordinator, config_entry, mac, name, "PM2.5 Offset",
                    CONF_PM25_OFFSET, device_info, "µg/m³"
                )
            )
            entities.append(
                QingpingDeviceSensorOffsetNumber(
                    coordinator, config_entry, mac, name, "PM10 Offset",
                    CONF_PM10_OFFSET, device_info, "µg/m³"
                )
            )

        if model == "CGS1":
            entities.append(
                QingpingDeviceSensorOffsetNumber(
                    coordinator, config_entry, mac, name, "TVOC Offset",
                    CONF_TVOC_OFFSET, device_info, "%"
                )
            )

        if model == "CGS2":
            entities.extend([
                QingpingDeviceSensorOffsetNumber(
                    coordinator, config_entry, mac, name, "Noise Offset",
                    CONF_NOISE_OFFSET, device_info, "dB"
                ),
                QingpingDeviceSensorOffsetNumber(
                    coordinator, config_entry, mac, name, "eTVOC Index Offset",
                    CONF_TVOC_INDEX_OFFSET, device_info, "%"
                ),
            ])

        if model == "CGDN1":
            entities.extend([
                QingpingDeviceTimeNumber(coordinator, config_entry, mac, name, "Power Off Time", CONF_POWER_OFF_TIME, device_info, 0, 1440, 1, 0, "minutes", NumberMode.BOX),
                QingpingDeviceTimeNumber(coordinator, config_entry, mac, name, "Auto Sliding Time", CONF_AUTO_SLIDING_TIME, device_info, 0, 60, 1, 30, "seconds", NumberMode.BOX),
                QingpingDeviceTimezoneNumber(coordinator, config_entry, mac, name, device_info),
            ])

    async_add_entities(entities)


class QingpingTLVReportIntervalNumber(CoordinatorEntity, NumberEntity):
    """Number entity for TLV device report interval (historic mode only)."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} Report Interval"
        self._attr_unique_id = f"{mac}_report_interval"
        self._attr_device_info = device_info
        self._attr_native_min_value = 10
        self._attr_native_max_value = 60
        self._attr_native_step = 5
        self._attr_native_unit_of_measurement = "min"
        self._attr_mode = NumberMode.BOX
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> int:
        """Return the current value."""
        return self.coordinator.data.get(CONF_REPORT_INTERVAL, 10)

    async def async_set_native_value(self, value: float) -> None:
        """Update the value and send to device."""
        int_value = int(value)
        self.coordinator.data[CONF_REPORT_INTERVAL] = int_value
        self.async_write_ha_state()

        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[CONF_REPORT_INTERVAL] = int_value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        await self.coordinator.async_request_refresh()

        # Send TLV command (KEY 0x04) - device must be plugged in
        packets = {
            0x04: int_to_bytes_little_endian(int_value, 2)
        }
        payload = tlv_encode(0x32, packets)
        topic = f"qingping/{self._mac}/down"
        await mqtt.async_publish(self.hass, topic, payload)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if CONF_REPORT_INTERVAL not in self.coordinator.data:
            self.coordinator.data[CONF_REPORT_INTERVAL] = self._config_entry.data.get(CONF_REPORT_INTERVAL, 5)
        self.async_write_ha_state()


class QingpingTLVSampleIntervalNumber(CoordinatorEntity, NumberEntity):
    """Number entity for TLV device sample interval (historic mode only)."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} Sample Interval"
        self._attr_unique_id = f"{mac}_sample_interval"
        self._attr_device_info = device_info
        self._attr_native_min_value = 10
        self._attr_native_max_value = 300
        self._attr_native_step = 10
        self._attr_native_unit_of_measurement = "s"
        self._attr_mode = NumberMode.BOX
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:timer-outline"

    @property
    def native_value(self) -> int:
        """Return the current value."""
        return self.coordinator.data.get(CONF_SAMPLE_INTERVAL, 60)

    async def async_set_native_value(self, value: float) -> None:
        """Update the value and send to device."""
        int_value = int(value)
        self.coordinator.data[CONF_SAMPLE_INTERVAL] = int_value
        self.async_write_ha_state()

        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[CONF_SAMPLE_INTERVAL] = int_value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        await self.coordinator.async_request_refresh()

        # Send TLV command (KEY 0x05) - device must be plugged in
        packets = {
            0x05: int_to_bytes_little_endian(int_value, 2)
        }
        payload = tlv_encode(0x32, packets)
        topic = f"qingping/{self._mac}/down"
        await mqtt.async_publish(self.hass, topic, payload)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if CONF_SAMPLE_INTERVAL not in self.coordinator.data:
            self.coordinator.data[CONF_SAMPLE_INTERVAL] = self._config_entry.data.get(CONF_SAMPLE_INTERVAL, 60)
        self.async_write_ha_state()


class QingpingTLVOffsetNumber(CoordinatorEntity, NumberEntity):
    """Number entity for TLV device offsets using TLV commands."""

    def __init__(self, coordinator, config_entry, mac, name, display_name, 
                 conf_key, device_info, tlv_key, min_value, max_value, step, unit):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._conf_key = conf_key
        self._tlv_key = tlv_key
        self._attr_name = f"{name} {display_name}"
        self._attr_unique_id = f"{mac}_{conf_key}"
        self._attr_device_info = device_info
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_mode = NumberMode.BOX
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data.get(self._conf_key, 0)

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        self.coordinator.data[self._conf_key] = value
        self.async_write_ha_state()

        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[self._conf_key] = value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        await self.coordinator.async_request_refresh()

        # Send TLV command to device
        # For temperature offset, convert F to C if needed (device expects Celsius)
        if self._conf_key == CONF_TEMPERATURE_OFFSET and self._attr_native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT:
            # Convert F to C: (F - 32) × 5/9
            celsius_value = (value * 5) / 9
            device_value = int(celsius_value * 10)
        elif self._attr_native_step == 0.1 or self._attr_native_step == 0.2:
            device_value = int(value * 10)
        else:
            device_value = int(value)

        packets = {
            self._tlv_key: int_to_bytes_little_endian(device_value, 2, signed=True)
        }
        payload = tlv_encode(0x32, packets)

        topic = f"qingping/{self._mac}/down"
        await mqtt.async_publish(self.hass, topic, payload)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._conf_key not in self.coordinator.data:
            self.coordinator.data[self._conf_key] = self._config_entry.data.get(self._conf_key, 0)
        self.async_write_ha_state()


class QingpingTLVPowerOffTimeNumber(CoordinatorEntity, NumberEntity):
    """Number entity for TLV device power off time."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} Power Off Time"
        self._attr_unique_id = f"{mac}_power_off_time"
        self._attr_device_info = device_info
        self._attr_native_min_value = 0
        self._attr_native_max_value = 1440
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "min"
        self._attr_mode = NumberMode.BOX
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self) -> int:
        """Return the current value."""
        return self.coordinator.data.get(CONF_POWER_OFF_TIME, 0)

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        int_value = int(value)
        self.coordinator.data[CONF_POWER_OFF_TIME] = int_value
        self.async_write_ha_state()

        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[CONF_POWER_OFF_TIME] = int_value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        await self.coordinator.async_request_refresh()

        # Send TLV command (KEY 0x3D)
        packets = {
            0x3D: int_to_bytes_little_endian(int_value, 2)
        }
        payload = tlv_encode(0x32, packets)

        topic = f"qingping/{self._mac}/down"
        await mqtt.async_publish(self.hass, topic, payload)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if CONF_POWER_OFF_TIME not in self.coordinator.data:
            self.coordinator.data[CONF_POWER_OFF_TIME] = self._config_entry.data.get(CONF_POWER_OFF_TIME, 0)
        self.async_write_ha_state()


# Legacy JSON device number entities (existing code for CGS1, CGS2, CGDN1)

class QingpingTLVCO2WorkIntervalNumber(CoordinatorEntity, NumberEntity):
    """Number entity for TLV device CO2 work interval."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} CO2 Interval"
        self._attr_unique_id = f"{mac}_co2_work_interval"
        self._attr_device_info = device_info
        self._attr_native_min_value = 1
        self._attr_native_max_value = 60
        self._attr_native_step = 1  # Allow any value, but recommend specific steps
        self._attr_native_unit_of_measurement = "min"
        self._attr_mode = NumberMode.BOX
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self) -> int:
        """Return the current value."""
        return self.coordinator.data.get("co2_work_interval", 5)

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        int_value = int(value)
        self.coordinator.data["co2_work_interval"] = int_value
        self.async_write_ha_state()

        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data["co2_work_interval"] = int_value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        await self.coordinator.async_request_refresh()

        # Send TLV command (KEY 0x3C)
        packets = {
            0x3B: int_to_bytes_little_endian(int_value, 2)
        }
        payload = tlv_encode(0x32, packets)

        topic = f"qingping/{self._mac}/down"
        await mqtt.async_publish(self.hass, topic, payload)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if "co2_work_interval" not in self.coordinator.data:
            self.coordinator.data["co2_work_interval"] = self._config_entry.data.get("co2_work_interval", 5)
        self.async_write_ha_state()


class QingpingDeviceOffsetNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Qingping Device offset number input."""

    def __init__(self, coordinator, config_entry, mac, name, offset_name, offset_key, device_info, unit_of_measurement, step):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._offset_key = offset_key
        self._attr_name = f"{name} {offset_name}"
        self._attr_unique_id = f"{mac}_{offset_key}"
        self._attr_device_info = device_info
        self._attr_native_min_value = -10
        self._attr_native_max_value = 10
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_mode = NumberMode.BOX  # Use number box instead of slider

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data.get(self._offset_key, DEFAULT_OFFSET)

    @property
    def mode(self) -> NumberMode:
        """Return the mode of the number entity."""
        return NumberMode.BOX

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self.coordinator.data[self._offset_key] = value
        self.async_write_ha_state()
        
        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[self._offset_key] = value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
        
        await self.coordinator.async_request_refresh()
        
        # Publish setting change to device
        from .sensor import publish_setting_change
        
        if self._offset_key == CONF_TEMPERATURE_OFFSET:
            if self._attr_native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT:
                    # Convert to Fahrenheit
                    temp_fahrenheit = ((32+value) - 32) * 5/9

                    value = round(float(temp_fahrenheit), 0)
            device_value = int(value * 100)
        else:  # CONF_HUMIDITY_OFFSET
            device_value = int(value * 10)
        await publish_setting_change(self.hass, self._mac, self._offset_key, device_value)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._offset_key not in self.coordinator.data:
            self.coordinator.data[self._offset_key] = self._config_entry.data.get(self._offset_key, DEFAULT_OFFSET)
        self.async_write_ha_state()


class QingpingDeviceUpdateIntervalNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Qingping Device update interval number input."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the number input."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} Update Interval"
        self._attr_unique_id = f"{mac}_update_interval"
        self._attr_device_info = device_info
        self._attr_native_min_value = 5
        self._attr_native_max_value = 300
        self._attr_native_step = 10
        self._attr_native_unit_of_measurement = "s"
        self._attr_mode = NumberMode.BOX
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self) -> int:
        """Return the current value."""
        return self.coordinator.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        int_value = int(value)
        self.coordinator.data[CONF_UPDATE_INTERVAL] = int_value
        self.async_write_ha_state()

        new_data = dict(self._config_entry.data)
        new_data[CONF_UPDATE_INTERVAL] = int_value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        await self.coordinator.async_request_refresh()

        sensors = self.hass.data[DOMAIN][self._config_entry.entry_id].get("sensors", [])
        for sensor in sensors:
            if hasattr(sensor, 'publish_config'):
                await sensor.publish_config()
                break

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if CONF_UPDATE_INTERVAL not in self.coordinator.data:
            self.coordinator.data[CONF_UPDATE_INTERVAL] = self._config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        self.async_write_ha_state()


class QingpingDeviceSensorOffsetNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Qingping Device sensor offset number input."""

    def __init__(self, coordinator, config_entry, mac, name, offset_name, offset_key, device_info, unit_of_measurement):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._offset_key = offset_key
        self._attr_name = f"{name} {offset_name}"
        self._attr_unique_id = f"{mac}_{offset_key}"
        self._attr_device_info = device_info
        self._attr_native_min_value = -500
        self._attr_native_max_value = 500
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self) -> int:
        """Return the current value."""
        return self.coordinator.data.get(self._offset_key, DEFAULT_SENSOR_OFFSET)

    async def async_set_native_value(self, value: int) -> None:
        """Update the current value."""
        self.coordinator.data[self._offset_key] = value
        self.async_write_ha_state()
        
        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[self._offset_key] = value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
        
        await self.coordinator.async_request_refresh()
        
        # Publish setting change to device
        from .sensor import publish_setting_change
        if self._offset_key == CONF_TVOC_OFFSET:
            device_value = int(value * 10)
        elif self._offset_key == CONF_TVOC_INDEX_OFFSET:
            device_value = int(value * 10)    
        else:
            device_value = int(value)
        await publish_setting_change(self.hass, self._mac, self._offset_key, device_value)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._offset_key not in self.coordinator.data:
            self.coordinator.data[self._offset_key] = self._config_entry.data.get(self._offset_key, DEFAULT_SENSOR_OFFSET)
        self.async_write_ha_state()


class QingpingDeviceTimeNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Qingping Device time setting number input."""

    def __init__(self, coordinator, config_entry, mac, name, time_name, time_key, device_info, min_val, max_val, step, default_val, unit, mode=NumberMode.BOX):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._time_key = time_key
        self._default_val = default_val
        self._attr_name = f"{name} {time_name}"
        self._attr_unique_id = f"{mac}_{time_key}"
        self._attr_device_info = device_info
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_unit_of_measurement = unit
        self._attr_mode = mode

    @property
    def native_value(self) -> int:
        """Return the current value."""
        return self.coordinator.data.get(self._time_key, self._default_val)

    async def async_set_native_value(self, value: int) -> None:
        """Update the current value."""
        self.coordinator.data[self._time_key] = value
        self.async_write_ha_state()
        
        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[self._time_key] = value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
        
        await self.coordinator.async_request_refresh()
        
        # Publish setting change to device
        from .sensor import publish_setting_change
        await publish_setting_change(self.hass, self._mac, self._time_key, int(value))

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._time_key not in self.coordinator.data:
            self.coordinator.data[self._time_key] = self._config_entry.data.get(self._time_key, self._default_val)
        self.async_write_ha_state()

class QingpingDeviceTimezoneNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Qingping Device timezone setting number input."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} Time Zone"
        self._attr_unique_id = f"{mac}_timezone"
        self._attr_device_info = device_info
        self._attr_native_min_value = -12
        self._attr_native_max_value = 14
        self._attr_native_step = 0.5
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_mode = NumberMode.BOX

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data.get(CONF_TIMEZONE, 0)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self.coordinator.data[CONF_TIMEZONE] = value
        self.async_write_ha_state()
        
        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[CONF_TIMEZONE] = value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
        
        await self.coordinator.async_request_refresh()
        
        # Publish setting change to device (value * 10 for device)
        from .sensor import publish_setting_change
        device_value = int(value * 10)
        await publish_setting_change(self.hass, self._mac, CONF_TIMEZONE, device_value)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if CONF_TIMEZONE not in self.coordinator.data:
            self.coordinator.data[CONF_TIMEZONE] = self._config_entry.data.get(CONF_TIMEZONE, 0)
        self.async_write_ha_state()