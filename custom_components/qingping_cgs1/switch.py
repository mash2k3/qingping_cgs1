"""Support for Qingping Device switch entities."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_MAC, CONF_MODEL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, CONF_CO2_ASC, TLV_MODELS, CONF_LED_INDICATOR, ADV_MODELS
from .tlv_encoder import tlv_encode

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qingping Device switch entities from a config entry."""
    mac = config_entry.data[CONF_MAC]
    name = config_entry.data[CONF_NAME]
    model = config_entry.data[CONF_MODEL]
    if model in ADV_MODELS:
        return
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    device_info = {
        "identifiers": {(DOMAIN, mac)},
        "name": name,
        "manufacturer": "Qingping",
        "model": model,
    }

    entities = []

     # CGDN1-specific switches
    if model == "CGDN1":
        entities.append(
            QingpingDeviceCO2ASCSwitch(coordinator, config_entry, mac, name, device_info)
        )

    # Add CO2 ASC switch for TLV devices with CO2 sensor
    if model in TLV_MODELS and model in ["CGP22C", "CGR1W", "CGR1PW"]:
        entities.append(
            QingpingTLVCO2ASCSwitch(coordinator, config_entry, mac, name, device_info)
        )
    
    # Add LED Indicator switch for "CGR1W", "CGR1PW"
    if model in ["CGR1W", "CGR1PW"]:
        entities.append(
            QingpingTLVLEDSwitch(coordinator, config_entry, mac, name, device_info)
        )

    if entities:
        async_add_entities(entities)


class QingpingTLVCO2ASCSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Qingping TLV device CO2 ASC switch."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} CO2 Auto Calibration"
        self._attr_unique_id = f"{mac}_co2_asc"
        self._attr_device_info = device_info
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:molecule-co2"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.data.get(CONF_CO2_ASC, False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        self.coordinator.data[CONF_CO2_ASC] = True
        self.async_write_ha_state()

        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[CONF_CO2_ASC] = True
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        await self.coordinator.async_request_refresh()

        # Send TLV command to device (KEY 0x40)
        # 1 = Enable ASC
        packets = {
            0x40: bytes([1])
        }
        payload = tlv_encode(0x32, packets)

        topic = f"qingping/{self._mac}/down"
        await mqtt.async_publish(self.hass, topic, payload)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        self.coordinator.data[CONF_CO2_ASC] = False
        self.async_write_ha_state()

        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[CONF_CO2_ASC] = False
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        await self.coordinator.async_request_refresh()

        # Send TLV command to device (KEY 0x40)
        # 0 = Disable ASC
        packets = {
            0x40: bytes([0])
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
        if CONF_CO2_ASC not in self.coordinator.data:
            self.coordinator.data[CONF_CO2_ASC] = self._config_entry.data.get(CONF_CO2_ASC, False)
        self.async_write_ha_state()

class QingpingTLVLEDSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Qingping "CGR1W", "CGR1PW" LED Indicator switch."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} LED Indicator"
        self._attr_unique_id = f"{mac}_led_indicator"
        self._attr_device_info = device_info
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:led-on"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.data.get(CONF_LED_INDICATOR, True)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        self.coordinator.data[CONF_LED_INDICATOR] = True
        self.async_write_ha_state()

        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[CONF_LED_INDICATOR] = True
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        await self.coordinator.async_request_refresh()

        # Send TLV command to device (KEY 0x63)
        # 1 = LED On
        packets = {
            0x63: bytes([1])
        }
        payload = tlv_encode(0x32, packets)

        topic = f"qingping/{self._mac}/down"
        await mqtt.async_publish(self.hass, topic, payload)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        self.coordinator.data[CONF_LED_INDICATOR] = False
        self.async_write_ha_state()

        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[CONF_LED_INDICATOR] = False
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        await self.coordinator.async_request_refresh()

        # Send TLV command to device (KEY 0x63)
        # 0 = LED Off
        packets = {
            0x63: bytes([0])
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
        if CONF_LED_INDICATOR not in self.coordinator.data:
            self.coordinator.data[CONF_LED_INDICATOR] = self._config_entry.data.get(CONF_LED_INDICATOR, True)
        self.async_write_ha_state()

class QingpingDeviceCO2ASCSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to enable/disable CO2 Automatic Self-Calibration."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} CO2 Auto Calibration"
        self._attr_unique_id = f"{mac}_co2_asc"
        self._attr_device_info = device_info
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:molecule-co2"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.data.get(CONF_CO2_ASC, 1) == 1

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self._set_value(1)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self._set_value(0)

    async def _set_value(self, value: int) -> None:
        """Set the CO2 ASC value."""
        self.coordinator.data[CONF_CO2_ASC] = value
        self.async_write_ha_state()

        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[CONF_CO2_ASC] = value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        await self.coordinator.async_request_refresh()

        # Publish setting change to device
        from .sensor import publish_setting_change
        await publish_setting_change(self.hass, self._mac, CONF_CO2_ASC, value)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if CONF_CO2_ASC not in self.coordinator.data:
            self.coordinator.data[CONF_CO2_ASC] = self._config_entry.data.get(CONF_CO2_ASC, 1)
        self.async_write_ha_state()