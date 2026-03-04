"""Tests for Change B: batch history data import to statistics."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from custom_components.qingping_cgs1.sensor import _import_batch_statistics


@pytest.mark.asyncio
async def test_import_batch_statistics_creates_correct_metadata(hass):
    """Should create StatisticMetaData with correct fields."""
    batch_data = [
        {"timestamp": 1709500000, "temperature": 22.5, "humidity": 55.0},
        {"timestamp": 1709500300, "temperature": 22.8, "humidity": 54.5},
    ]
    sensor_mappings = {
        "temperature": ("Temperature", "°C"),
        "humidity": ("Humidity", "%"),
    }

    with patch(
        "custom_components.qingping_cgs1.sensor.async_import_statistics"
    ) as mock_import:
        await _import_batch_statistics(
            hass, "582D348611F9", "Test Device", batch_data, sensor_mappings
        )

        assert mock_import.call_count == 2  # Once per sensor type

        # Check temperature call
        temp_call = mock_import.call_args_list[0]
        metadata = temp_call[0][1]
        assert metadata.source == "qingping_cgs1"
        assert metadata.statistic_id == "qingping_cgs1:582d348611f9_temperature"
        assert metadata.unit_of_measurement == "°C"
        assert metadata.has_mean is True
        assert metadata.has_sum is False


@pytest.mark.asyncio
async def test_import_batch_statistics_aligns_timestamps(hass):
    """Timestamps should be floored to 5-minute boundaries."""
    # 1709500123 is NOT on a 5-min boundary
    # Floor: 1709500123 - (1709500123 % 300) = 1709500123 - 223 = 1709499900
    batch_data = [
        {"timestamp": 1709500123, "temperature": 22.5},
    ]
    sensor_mappings = {"temperature": ("Temperature", "°C")}

    with patch(
        "custom_components.qingping_cgs1.sensor.async_import_statistics"
    ) as mock_import:
        await _import_batch_statistics(
            hass, "582D348611F9", "Test", batch_data, sensor_mappings
        )

        stats = mock_import.call_args[0][2]
        assert len(stats) == 1
        expected_dt = datetime.fromtimestamp(1709499900, tz=timezone.utc)
        assert stats[0].start == expected_dt


@pytest.mark.asyncio
async def test_import_batch_statistics_skips_zero_timestamps(hass):
    """Points with timestamp=0 should be skipped."""
    batch_data = [
        {"timestamp": 0, "temperature": 22.5},
        {"timestamp": 1709500000, "temperature": 23.0},
    ]
    sensor_mappings = {"temperature": ("Temperature", "°C")}

    with patch(
        "custom_components.qingping_cgs1.sensor.async_import_statistics"
    ) as mock_import:
        await _import_batch_statistics(
            hass, "582D348611F9", "Test", batch_data, sensor_mappings
        )

        stats = mock_import.call_args[0][2]
        assert len(stats) == 1
        assert stats[0].mean == 23.0


@pytest.mark.asyncio
async def test_import_batch_statistics_skips_missing_sensor_keys(hass):
    """Points missing a sensor key should be skipped for that sensor."""
    batch_data = [
        {"timestamp": 1709500000, "temperature": 22.5},
        {"timestamp": 1709500300, "humidity": 55.0},  # No temperature
    ]
    sensor_mappings = {
        "temperature": ("Temperature", "°C"),
        "humidity": ("Humidity", "%"),
    }

    with patch(
        "custom_components.qingping_cgs1.sensor.async_import_statistics"
    ) as mock_import:
        await _import_batch_statistics(
            hass, "582D348611F9", "Test", batch_data, sensor_mappings
        )

        # Should be called twice (once per sensor type)
        assert mock_import.call_count == 2

        # Temperature: 1 point
        temp_stats = mock_import.call_args_list[0][0][2]
        assert len(temp_stats) == 1

        # Humidity: 1 point
        hum_stats = mock_import.call_args_list[1][0][2]
        assert len(hum_stats) == 1


@pytest.mark.asyncio
async def test_import_batch_statistics_empty_data(hass):
    """Empty batch data should not call async_import_statistics."""
    with patch(
        "custom_components.qingping_cgs1.sensor.async_import_statistics"
    ) as mock_import:
        await _import_batch_statistics(
            hass, "582D348611F9", "Test", [], {"temperature": ("Temperature", "°C")}
        )
        mock_import.assert_not_called()
