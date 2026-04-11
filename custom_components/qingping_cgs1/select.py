"""Support for Qingping Device select entities."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_MAC, CONF_MODEL, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import (
    DOMAIN, CONF_TVOC_UNIT, CONF_ETVOC_UNIT, CONF_SCREENSAVER_TYPE,
    CONF_REPORT_MODE, REPORT_MODE_HISTORIC, REPORT_MODE_REALTIME, TLV_MODELS,
    CONF_TEMPERATURE_UNIT, ADV_MODELS
)
from .tlv_encoder import tlv_encode

TVOC_UNIT_OPTIONS = ["ppb", "ppm", "mg/m³"]
ETVOC_UNIT_OPTIONS = ["index", "ppb", "mg/m³"]

# Mapping between display names and values for screensaver types
SCREENSAVER_OPTIONS = {
    "All sensors": 0,
    "Current sensor": 1,
    "Clock and all sensors": 2,
    "Clock and current sensor": 3,
}

# Reverse mapping for looking up names from values
SCREENSAVER_VALUES = {v: k for k, v in SCREENSAVER_OPTIONS.items()}

REPORT_MODE_OPTIONS = ["Historic (report interval)", "Real-time (4 sec)"]
REPORT_MODE_MAP = {
    "Historic (report interval)": REPORT_MODE_HISTORIC,
    "Real-time (4 sec)": REPORT_MODE_REALTIME,
}
REPORT_MODE_REVERSE = {v: k for k, v in REPORT_MODE_MAP.items()}

TEMPERATURE_UNIT_OPTIONS = ["Celsius (°C)", "Fahrenheit (°F)"]
TEMPERATURE_UNIT_MAP = {
    "Celsius (°C)": "celsius",
    "Fahrenheit (°F)": "fahrenheit",
}
TEMPERATURE_UNIT_REVERSE = {v: k for k, v in TEMPERATURE_UNIT_MAP.items()}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qingping Device select entities from a config entry."""
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

    # Add report mode select for TLV devices
    if model in TLV_MODELS:
        entities.append(
            QingpingDeviceReportModeSelect(coordinator, config_entry, mac, name, device_info)
        )
        # Add temperature unit select for TLV devices
        entities.append(
            QingpingDeviceTemperatureUnitSelect(coordinator, config_entry, mac, name, device_info, native_temp_unit)
        )

    if model == "CGS1":
        entities.append(
            QingpingDeviceTVOCUnitSelect(coordinator, config_entry, mac, name, device_info, CONF_TVOC_UNIT, TVOC_UNIT_OPTIONS)
        )
    elif model == "CGS2":
        entities.append(
            QingpingDeviceTVOCUnitSelect(coordinator, config_entry, mac, name, device_info, CONF_ETVOC_UNIT, ETVOC_UNIT_OPTIONS)
        )
    elif model in ["CGR1W", "CGR1PW"]:
        # "CGR1W", "CGR1PW" uses TLV commands for eTVOC unit
        entities.append(
            QingpingTLVeTVOCUnitSelect(coordinator, config_entry, mac, name, device_info)
        )
    elif model == "CGDN1":
        entities.append(
            QingpingDeviceScreensaverTypeSelect(coordinator, config_entry, mac, name, device_info)
        )

    if entities:
        async_add_entities(entities)

class QingpingDeviceTVOCUnitSelect(CoordinatorEntity, SelectEntity):
    """Representation of a Qingping Device TVOC unit select entity."""

    def __init__(self, coordinator, config_entry, mac, name, device_info, conf_unit, unit_options):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._conf_unit = conf_unit
        self._unit_options = unit_options
        self._attr_name = f"{name} {'eTVOC' if conf_unit == CONF_ETVOC_UNIT else 'TVOC'} Unit"
        self._attr_unique_id = f"{mac}_{conf_unit}"
        self._attr_device_info = device_info
        self._attr_options = unit_options
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self.coordinator.data.get(self._conf_unit, self._unit_options[0])

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""
        self.coordinator.data[self._conf_unit] = option
        self.async_write_ha_state()

        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[self._conf_unit] = option
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if CONF_TVOC_UNIT not in self.coordinator.data:
            self.coordinator.data[self._conf_unit] = self._config_entry.data.get(self._conf_unit, self._unit_options[0])
        self.async_write_ha_state()

class QingpingTLVeTVOCUnitSelect(CoordinatorEntity, SelectEntity):
    """Representation of a Qingping "CGR1W", "CGR1PW" eTVOC unit select entity with TLV commands."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} eTVOC Unit"
        self._attr_unique_id = f"{mac}_etvoc_unit"
        self._attr_device_info = device_info
        self._attr_options = ETVOC_UNIT_OPTIONS  # ["index", "ppb", "mg/m³"]
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self.coordinator.data.get(CONF_ETVOC_UNIT, "index")

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""
        self.coordinator.data[CONF_ETVOC_UNIT] = option
        self.async_write_ha_state()

        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[CONF_ETVOC_UNIT] = option
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        await self.coordinator.async_request_refresh()

        # Send TLV command to device (KEY 0x62 - VOC unit display)
        # According to protocol: 1=index, 3=mg/m³, 4=ppb
        if option == "index":
            tlv_value = 1
        elif option == "mg/m³":
            tlv_value = 3
        elif option == "ppb":
            tlv_value = 4
        else:
            tlv_value = 1  # default to index
        
        packets = {
            0x62: bytes([tlv_value])
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
        if CONF_ETVOC_UNIT not in self.coordinator.data:
            self.coordinator.data[CONF_ETVOC_UNIT] = self._config_entry.data.get(CONF_ETVOC_UNIT, "index")
        self.async_write_ha_state()

class QingpingDeviceScreensaverTypeSelect(CoordinatorEntity, SelectEntity):
    """Representation of a Qingping Device screensaver type select input."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} Screensaver Type"
        self._attr_unique_id = f"{mac}_screensaver_type"
        self._attr_device_info = device_info
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = list(SCREENSAVER_OPTIONS.keys())

    @property
    def current_option(self) -> str:
        """Return the current option."""
        value = self.coordinator.data.get(CONF_SCREENSAVER_TYPE, 1)
        return SCREENSAVER_VALUES.get(value, "Current sensor")

    async def async_select_option(self, option: str) -> None:
        """Update the current option."""
        value = SCREENSAVER_OPTIONS.get(option)
        if value is None:
            return
        
        self.coordinator.data[CONF_SCREENSAVER_TYPE] = value
        self.async_write_ha_state()
        
        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[CONF_SCREENSAVER_TYPE] = value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
        
        await self.coordinator.async_request_refresh()
        
        # Publish setting change to device
        from .sensor import publish_setting_change
        await publish_setting_change(self.hass, self._mac, CONF_SCREENSAVER_TYPE, int(value))

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if CONF_SCREENSAVER_TYPE not in self.coordinator.data:
            self.coordinator.data[CONF_SCREENSAVER_TYPE] = self._config_entry.data.get(CONF_SCREENSAVER_TYPE, 1)
        self.async_write_ha_state()

class QingpingDeviceReportModeSelect(CoordinatorEntity, SelectEntity):
    """Representation of a Qingping TLV device report mode select entity."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} Report Mode"
        self._attr_unique_id = f"{mac}_report_mode"
        self._attr_device_info = device_info
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = REPORT_MODE_OPTIONS
        self._attr_icon = "mdi:clock-fast"

    @property
    def current_option(self) -> str:
        """Return the current option."""
        value = self.coordinator.data.get(CONF_REPORT_MODE, REPORT_MODE_HISTORIC)
        return REPORT_MODE_REVERSE.get(value, REPORT_MODE_OPTIONS[0])

    async def async_select_option(self, option: str) -> None:
        """Update the current option."""
        value = REPORT_MODE_MAP.get(option)
        if value is None:
            return
        
        self.coordinator.data[CONF_REPORT_MODE] = value
        self.async_write_ha_state()
        
        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[CONF_REPORT_MODE] = value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
        
        await self.coordinator.async_request_refresh()
        
        # Trigger config publish to apply new mode
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
        if CONF_REPORT_MODE not in self.coordinator.data:
            self.coordinator.data[CONF_REPORT_MODE] = self._config_entry.data.get(CONF_REPORT_MODE, REPORT_MODE_HISTORIC)
        self.async_write_ha_state()

class QingpingDeviceTemperatureUnitSelect(CoordinatorEntity, SelectEntity):
    """Representation of a Qingping TLV device temperature unit select entity."""

    def __init__(self, coordinator, config_entry, mac, name, device_info, native_temp_unit):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} Temperature Unit"
        self._attr_unique_id = f"{mac}_temperature_unit"
        self._attr_device_info = device_info
        self._attr_native_unit_of_measurement = native_temp_unit
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = TEMPERATURE_UNIT_OPTIONS
        self._attr_icon = "mdi:thermometer"

    @property
    def current_option(self) -> str:
        """Return the current option."""
        unit = "fahrenheit" if self._attr_native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT else "celsius"
        value = self.coordinator.data.get(CONF_TEMPERATURE_UNIT, unit)
        return TEMPERATURE_UNIT_REVERSE.get(value, TEMPERATURE_UNIT_OPTIONS[0])

    async def async_select_option(self, option: str) -> None:
        """Update the current option."""
        value = TEMPERATURE_UNIT_MAP.get(option)
        if value is None:
            return
        
        self.coordinator.data[CONF_TEMPERATURE_UNIT] = value
        self.async_write_ha_state()
        
        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[CONF_TEMPERATURE_UNIT] = value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
        
        await self.coordinator.async_request_refresh()
        
        # Send TLV command to device (KEY 0x19)
        # 0 = Celsius, 1 = Fahrenheit
        tlv_value = 1 if value == "fahrenheit" else 0
        packets = {
            0x19: bytes([tlv_value])
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
        unit = "fahrenheit" if self._attr_native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT else "celsius"
        if CONF_TEMPERATURE_UNIT not in self.coordinator.data:
            self.coordinator.data[CONF_TEMPERATURE_UNIT] = self._config_entry.data.get(CONF_TEMPERATURE_UNIT, unit)
        self.async_write_ha_state()