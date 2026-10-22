"""Tests for Change C: configurable offline timeout."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from custom_components.qingping_cgs1.const import (
    CONF_OFFLINE_TIMEOUT_MINUTES,
    CONF_REPORT_MODE,
    DEFAULT_OFFLINE_TIMEOUT_MINUTES,
    DOMAIN,
    REPORT_MODE_HISTORIC,
    REPORT_MODE_REALTIME,
    CONF_MODEL,
)
from custom_components.qingping_cgs1.sensor import (
    QingpingDeviceStatusSensor,
    OFFLINE_TIMEOUT_REALTIME,
)


def _make_status_sensor(
    hass, config_entry, coordinator, model="CGP22W"
):
    """Helper to create a QingpingDeviceStatusSensor."""
    config_entry.data = {**config_entry.data, "model": model}
    device_info = {
        "identifiers": {(DOMAIN, "582D348611F9")},
        "name": "Test",
        "manufacturer": "Qingping",
        "model": model,
    }
    sensor = QingpingDeviceStatusSensor(
        coordinator, config_entry, "582D348611F9", "Test", device_info
    )
    sensor.hass = hass
    return sensor


def test_historic_timeout_uses_default_65min(
    hass, mock_config_entry, mock_coordinator
):
    """Without options, Historic mode timeout should be 65*60=3900 seconds."""
    mock_config_entry.options = {}
    mock_coordinator.data = {CONF_REPORT_MODE: REPORT_MODE_HISTORIC}
    sensor = _make_status_sensor(hass, mock_config_entry, mock_coordinator)

    # Simulate a message received 64 minutes ago → should be online
    sensor._last_timestamp = int(time.time()) - (64 * 60)
    sensor._update_status()
    assert sensor._attr_native_value == "online"

    # Simulate a message received 66 minutes ago → should be offline
    sensor._last_timestamp = int(time.time()) - (66 * 60)
    sensor._update_status()
    assert sensor._attr_native_value == "offline"


def test_historic_timeout_uses_configured_value(
    hass, mock_config_entry, mock_coordinator
):
    """With 120 min configured, timeout should be 120*60=7200 seconds."""
    mock_config_entry.options = {CONF_OFFLINE_TIMEOUT_MINUTES: 120}
    mock_coordinator.data = {CONF_REPORT_MODE: REPORT_MODE_HISTORIC}
    sensor = _make_status_sensor(hass, mock_config_entry, mock_coordinator)

    # 119 minutes ago → online
    sensor._last_timestamp = int(time.time()) - (119 * 60)
    sensor._update_status()
    assert sensor._attr_native_value == "online"

    # 121 minutes ago → offline
    sensor._last_timestamp = int(time.time()) - (121 * 60)
    sensor._update_status()
    assert sensor._attr_native_value == "offline"


def test_realtime_timeout_always_300s(
    hass, mock_config_entry, mock_coordinator
):
    """Real-time mode should always use 300s regardless of options."""
    mock_config_entry.options = {CONF_OFFLINE_TIMEOUT_MINUTES: 1440}
    mock_coordinator.data = {CONF_REPORT_MODE: REPORT_MODE_REALTIME}
    sensor = _make_status_sensor(hass, mock_config_entry, mock_coordinator)

    # 4 minutes ago → online
    sensor._last_timestamp = int(time.time()) - (4 * 60)
    sensor._update_status()
    assert sensor._attr_native_value == "online"

    # 6 minutes ago → offline (300s = 5min)
    sensor._last_timestamp = int(time.time()) - (6 * 60)
    sensor._update_status()
    assert sensor._attr_native_value == "offline"


def test_json_device_uses_configurable_timeout(
    hass, mock_config_entry, mock_coordinator
):
    """JSON devices (CGS1) should also use configurable timeout."""
    mock_config_entry.options = {CONF_OFFLINE_TIMEOUT_MINUTES: 65}
    mock_coordinator.data = {}
    sensor = _make_status_sensor(
        hass, mock_config_entry, mock_coordinator, model="CGS1"
    )

    # 64 minutes ago → online
    sensor._last_timestamp = int(time.time()) - (64 * 60)
    sensor._update_status()
    assert sensor._attr_native_value == "online"

    # 66 minutes ago → offline
    sensor._last_timestamp = int(time.time()) - (66 * 60)
    sensor._update_status()
    assert sensor._attr_native_value == "offline"
