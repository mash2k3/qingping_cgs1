"""Exercise batch imports against Home Assistant's recorder."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest import TestCase

from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import get_metadata, statistics_during_period

from custom_components.qingping_cgs1.sensor import _import_batch_statistics


async def test_import_batch_statistics_persists_hourly_means(recorder_mock, hass):
    """Persist averages without deprecated APIs or duplicate repeat imports."""
    start = datetime(2026, 11, 1, tzinfo=timezone.utc)
    batch = [
        {"timestamp": int(start.timestamp()) + 100, "temperature": 20.0, "co2": 500.0, "pm25": 4.0},
        {"timestamp": int(start.timestamp()) + 200, "temperature": 24.0, "co2": 700.0, "pm25": 8.0},
    ]
    mappings = {
        "temperature": ("Temperature", "°C"),
        "co2": ("CO2", "ppm"),
        "pm25": ("PM2.5", "µg/m³"),
    }
    expected = {
        "temperature": ("temperature", 22.0),
        "co2": ("unitless", 600.0),
        "pm25": (None, 6.0),
    }
    ids = {f"qingping_cgs1:582d348611f9_{key}" for key in mappings}
    for _ in range(2):
        with TestCase().assertNoLogs("homeassistant.helpers.frame", "WARNING"):
            await _import_batch_statistics(hass, "582D348611F9", "Test", batch, mappings)
        await recorder_mock.async_block_till_done()
        metadata = await recorder_mock.async_add_executor_job(
            lambda: get_metadata(hass, statistic_ids=ids)
        )
        assert set(metadata) == ids
        rows = await recorder_mock.async_add_executor_job(
            lambda: statistics_during_period(
                hass, start, start + timedelta(hours=1), ids, "hour", None, {"mean"}
            )
        )
        for key, (unit_class, mean) in expected.items():
            statistic_id = f"qingping_cgs1:582d348611f9_{key}"
            item = metadata[statistic_id][1]
            assert item["mean_type"] is StatisticMeanType.ARITHMETIC
            assert item["unit_class"] == unit_class
            assert [row["mean"] for row in rows[statistic_id]] == [mean]
