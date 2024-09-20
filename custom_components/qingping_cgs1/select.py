"""Support for Qingping CGS1 select entities."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, CONF_TVOC_UNIT

TVOC_UNIT_OPTIONS = ["ppb", "ppm", "mg/m³"]

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qingping CGS1 select entities from a config entry."""
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
        QingpingCGS1TVOCUnitSelect(coordinator, config_entry, mac, name, device_info),
    ])

class QingpingCGS1TVOCUnitSelect(CoordinatorEntity, SelectEntity):
    """Representation of a Qingping CGS1 TVOC unit select entity."""

    def __init__(self, coordinator, config_entry, mac, name, device_info):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._attr_name = f"{name} TVOC Unit"
        self._attr_unique_id = f"{mac}_tvoc_unit"
        self._attr_device_info = device_info
        self._attr_options = TVOC_UNIT_OPTIONS
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self.coordinator.data.get(CONF_TVOC_UNIT, TVOC_UNIT_OPTIONS[0])

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""
        self.coordinator.data[CONF_TVOC_UNIT] = option
        self.async_write_ha_state()

        # Update config entry
        new_data = dict(self._config_entry.data)
        new_data[CONF_TVOC_UNIT] = option
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if CONF_TVOC_UNIT not in self.coordinator.data:
            self.coordinator.data[CONF_TVOC_UNIT] = self._config_entry.data.get(CONF_TVOC_UNIT, TVOC_UNIT_OPTIONS[0])
        self.async_write_ha_state()