"""Support for Qingping Device time entities."""
from __future__ import annotations

import datetime
import logging

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_MAC, CONF_MODEL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, CONF_NIGHT_MODE_START_TIME, CONF_NIGHT_MODE_END_TIME, ADV_MODELS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qingping Device time entities from a config entry."""
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

    # CGDN1-specific time entities
    if model == "CGDN1":
        entities.extend([
            QingpingDeviceTimeEntity(coordinator, config_entry, mac, name, "Night Mode Start Time", CONF_NIGHT_MODE_START_TIME, device_info, 1260),
            QingpingDeviceTimeEntity(coordinator, config_entry, mac, name, "Night Mode End Time", CONF_NIGHT_MODE_END_TIME, device_info, 360),
        ])

    if entities:
        async_add_entities(entities)


class QingpingDeviceTimeEntity(CoordinatorEntity, TimeEntity):
    """Representation of a Qingping Device time entity."""

    def __init__(self, coordinator, config_entry, mac, name, time_name, time_key, device_info, default_minutes):
        """Initialize the time entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._time_key = time_key
        self._default_minutes = default_minutes
        self._attr_name = f"{name} {time_name}"
        self._attr_unique_id = f"{mac}_{time_key}"
        self._attr_device_info = device_info
        self._attr_entity_category = EntityCategory.CONFIG
        
    @property
    def native_value(self) -> datetime.time | None:
        """Return the current time value."""
        minutes = self.coordinator.data.get(self._time_key, self._default_minutes)
        hours = minutes // 60
        mins = minutes % 60
        return datetime.time(hour=hours, minute=mins)

    async def async_set_value(self, value: datetime.time) -> None:
        """Update the current time value."""
        # Convert time to minutes since midnight
        minutes = value.hour * 60 + value.minute
        
        self.coordinator.data[self._time_key] = minutes
        self.async_write_ha_state()
        
        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[self._time_key] = minutes
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
        
        await self.coordinator.async_request_refresh()
        
        # Publish setting change to device
        from .sensor import publish_setting_change
        await publish_setting_change(self.hass, self._mac, self._time_key, minutes)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._time_key not in self.coordinator.data:
            self.coordinator.data[self._time_key] = self._config_entry.data.get(self._time_key, self._default_minutes)
        self.async_write_ha_state()