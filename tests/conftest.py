"""Fixtures for qingping_cgs1 tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.qingping_cgs1.const import (
    DOMAIN,
    CONF_REPORT_MODE,
    REPORT_MODE_HISTORIC,
    REPORT_MODE_REALTIME,
    CONF_AUTO_SWITCH_REPORT_MODE,
    CONF_OFFLINE_TIMEOUT_MINUTES,
    CONF_UPDATE_INTERVAL,
)


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Create a mock config entry with default data and empty options."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        "mac": "582D348611F9",
        "name": "Test Device",
        "model": "CGP22W",
    }
    entry.options = {}
    return entry


@pytest.fixture
def mock_config_entry_with_options() -> ConfigEntry:
    """Create a mock config entry with custom options."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        "mac": "582D348611F9",
        "name": "Test Device",
        "model": "CGP22W",
    }
    entry.options = {
        CONF_AUTO_SWITCH_REPORT_MODE: True,
        CONF_OFFLINE_TIMEOUT_MINUTES: 120,
    }
    return entry


@pytest.fixture
def mock_coordinator(hass: HomeAssistant) -> DataUpdateCoordinator:
    """Create a mock coordinator."""
    coordinator = MagicMock(spec=DataUpdateCoordinator)
    coordinator.data = {
        CONF_REPORT_MODE: REPORT_MODE_HISTORIC,
        CONF_UPDATE_INTERVAL: 300,
    }
    return coordinator


@pytest.fixture
def mock_hass_data(hass: HomeAssistant, mock_config_entry, mock_coordinator):
    """Set up hass.data with domain data."""
    hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {
            "config": mock_config_entry.data,
            "coordinator": mock_coordinator,
            "sensors": [],
        }
    }
    return hass.data[DOMAIN]
