"""Support for Qingping CGS1 offset number inputs."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_MAC
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_TEMPERATURE_OFFSET, CONF_HUMIDITY_OFFSET, DEFAULT_OFFSET

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qingping CGS1 number inputs from a config entry."""
    mac = config_entry.data[CONF_MAC]
    name = config_entry.data[CONF_NAME]
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    device_info = {
        "identifiers": {(DOMAIN, mac)},
        "name": name,
        "manufacturer": "Qingping",
        "model": "CGS1",
    }

    async_add_entities([
        QingpingCGS1OffsetNumber(coordinator, config_entry, mac, name, "Temperature Offset", CONF_TEMPERATURE_OFFSET, device_info, "°C"),
        QingpingCGS1OffsetNumber(coordinator, config_entry, mac, name, "Humidity Offset", CONF_HUMIDITY_OFFSET, device_info, "%"),
    ])

class QingpingCGS1OffsetNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Qingping CGS1 offset number input."""

    def __init__(self, coordinator, config_entry, mac, name, offset_name, offset_key, device_info, unit_of_measurement):
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
        self._attr_native_step = 0.5
        self._attr_native_unit_of_measurement = unit_of_measurement

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data.get(self._offset_key, DEFAULT_OFFSET)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self.coordinator.data[self._offset_key] = value
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
        
        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[self._offset_key] = value
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

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