"""Tests for Change A: auto-switch report mode guard."""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.qingping_cgs1.const import (
    CONF_AUTO_SWITCH_REPORT_MODE,
    CONF_REPORT_MODE,
    DOMAIN,
    REPORT_MODE_HISTORIC,
    REPORT_MODE_REALTIME,
)
from custom_components.qingping_cgs1.sensor import (
    _auto_switch_report_mode_on_battery_state,
)


@pytest.mark.asyncio
async def test_auto_switch_disabled_by_default(
    hass, mock_config_entry, mock_coordinator
):
    """When auto_switch option is not set (default False), should return immediately."""
    # options is empty → defaults to False
    mock_config_entry.options = {}

    hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {"coordinator": mock_coordinator}
    }

    with patch(
        "custom_components.qingping_cgs1.sensor.mqtt"
    ) as mock_mqtt:
        await _auto_switch_report_mode_on_battery_state(
            hass, mock_config_entry, "582D348611F9", True, "CGP22W"
        )
        # Should NOT have published anything
        mock_mqtt.async_publish.assert_not_called()


@pytest.mark.asyncio
async def test_auto_switch_disabled_explicitly(
    hass, mock_config_entry, mock_coordinator
):
    """When auto_switch is explicitly False, should return immediately."""
    mock_config_entry.options = {CONF_AUTO_SWITCH_REPORT_MODE: False}

    hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {"coordinator": mock_coordinator}
    }

    with patch(
        "custom_components.qingping_cgs1.sensor.mqtt"
    ) as mock_mqtt:
        await _auto_switch_report_mode_on_battery_state(
            hass, mock_config_entry, "582D348611F9", True, "CGP22W"
        )
        mock_mqtt.async_publish.assert_not_called()


@pytest.mark.asyncio
async def test_auto_switch_enabled_sends_realtime_on_charge(
    hass, mock_config_entry, mock_coordinator
):
    """When auto_switch is True and charging, should send real-time command."""
    mock_config_entry.options = {CONF_AUTO_SWITCH_REPORT_MODE: True}

    hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {"coordinator": mock_coordinator}
    }

    with patch(
        "custom_components.qingping_cgs1.sensor.mqtt"
    ) as mock_mqtt:
        mock_mqtt.async_publish = AsyncMock()
        await _auto_switch_report_mode_on_battery_state(
            hass, mock_config_entry, "582D348611F9", True, "CGP22W"
        )
        # Should have published a TLV command
        mock_mqtt.async_publish.assert_called_once()
        call_args = mock_mqtt.async_publish.call_args
        assert call_args[0][1] == "qingping/582D348611F9/down"
        # Coordinator should be set to realtime
        assert mock_coordinator.data[CONF_REPORT_MODE] == REPORT_MODE_REALTIME


@pytest.mark.asyncio
async def test_auto_switch_skips_non_tlv_models(
    hass, mock_config_entry, mock_coordinator
):
    """Auto-switch should skip JSON models like CGS1."""
    mock_config_entry.options = {CONF_AUTO_SWITCH_REPORT_MODE: True}

    hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {"coordinator": mock_coordinator}
    }

    with patch(
        "custom_components.qingping_cgs1.sensor.mqtt"
    ) as mock_mqtt:
        await _auto_switch_report_mode_on_battery_state(
            hass, mock_config_entry, "582D3400E7E9", True, "CGS1"
        )
        mock_mqtt.async_publish.assert_not_called()
