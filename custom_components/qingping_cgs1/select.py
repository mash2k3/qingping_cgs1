"""Support for Qingping CGSx select entities."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, CONF_TVOC_UNIT, CONF_ETVOC_UNIT, MODEL_CGS2, SENSOR_NOISE, MODEL_CGS1


TVOC_UNIT_OPTIONS = ["ppb", "ppm", "mg/m³"]
ETVOC_UNIT_OPTIONS = ["index", "ppb", "mg/m³"]

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qingping CGSx select entities from a config entry."""
    mac = config_entry.data[CONF_MAC]
    name = config_entry.data[CONF_NAME]
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    model = MODEL_CGS2 if SENSOR_NOISE in coordinator.data else MODEL_CGS1

    device_info = {
        "identifiers": {(DOMAIN, mac)},
        "name": name,
        "manufacturer": "Qingping",
        "model": model,
    }

    if model == MODEL_CGS1:
        async_add_entities([
            QingpingCGSxTVOCUnitSelect(coordinator, config_entry, mac, name, device_info, CONF_TVOC_UNIT, TVOC_UNIT_OPTIONS),
        ])
    else:  # CGS2
        async_add_entities([
            QingpingCGSxTVOCUnitSelect(coordinator, config_entry, mac, name, device_info, CONF_ETVOC_UNIT, ETVOC_UNIT_OPTIONS),
        ])

class QingpingCGSxTVOCUnitSelect(CoordinatorEntity, SelectEntity):
    """Representation of a Qingping CGSx TVOC unit select entity."""

    def __init__(self, coordinator, config_entry, mac, name, device_info, conf_unit, unit_options):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac = mac
        self._conf_unit = conf_unit
        self._unit_options = unit_options
        self._attr_name = f"{name} {'ETVOC' if conf_unit == CONF_ETVOC_UNIT else 'TVOC'} Unit"
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
        if self._conf_unit not in self.coordinator.data:
            self.coordinator.data[self._conf_unit] = self._config_entry.data.get(self._conf_unit, self._unit_options[0])
        self.async_write_ha_state()