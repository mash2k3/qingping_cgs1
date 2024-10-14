"""The Qingping CGSx integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import logging

from .const import DOMAIN, CONF_TEMPERATURE_OFFSET, CONF_HUMIDITY_OFFSET, DEFAULT_OFFSET, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.SELECT]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Qingping CGSx from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    async def async_update_data():
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        # Note: This is a placeholder. In a real scenario, you might
        # fetch data from an API or process local data here.
        return {}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="sensor",
        update_method=async_update_data,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=None  # We're not polling regularly, only when offsets change
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        CONF_TEMPERATURE_OFFSET: entry.data.get(CONF_TEMPERATURE_OFFSET, DEFAULT_OFFSET),
        CONF_HUMIDITY_OFFSET: entry.data.get(CONF_HUMIDITY_OFFSET, DEFAULT_OFFSET),
        CONF_UPDATE_INTERVAL: entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        "coordinator": coordinator,
    }

    coordinator.data = hass.data[DOMAIN][entry.entry_id]

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok