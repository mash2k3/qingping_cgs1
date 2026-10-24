"""Tests: type 17 history batches must not overwrite live (type 12) readings."""
from __future__ import annotations

import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.qingping_cgs1.const import DOMAIN
from custom_components.qingping_cgs1.sensor import (
    REALTIME_LIVE_WINDOW,
    _json_point_timestamp,
    _select_live_point_from_batch,
    async_setup_entry,
)

NOW = 1_800_000_000


def _point(ts, co2):
    return {"timestamp": {"value": ts}, "co2": {"value": co2}}


# --- helper unit tests ------------------------------------------------------


def test_point_timestamp_formats():
    assert _json_point_timestamp({"timestamp": {"value": 1700000000}}) == 1700000000
    assert _json_point_timestamp({"timestamp": 1700000000}) == 1700000000
    assert _json_point_timestamp({"timestamp": "1700000000"}) == 1700000000
    assert _json_point_timestamp({}) == 0
    assert _json_point_timestamp({"timestamp": "bad"}) == 0


def test_batch_ignored_while_realtime_data_is_flowing():
    batch = [_point(NOW - 60, 630)]
    assert _select_live_point_from_batch(batch, NOW, NOW - 10) is None


def test_batch_used_once_realtime_data_has_stopped():
    batch = [_point(NOW - 60, 630)]
    last_rt = NOW - REALTIME_LIVE_WINDOW - 1
    assert _select_live_point_from_batch(batch, NOW, last_rt)["co2"]["value"] == 630


def test_live_window_covers_slow_update_interval():
    # Default 300 s interval: a batch can arrive ~299 s after the last
    # type 12 message (seen on a real CGS2). A 600 s window must still block it.
    batch = [_point(NOW - 60, 630)]
    assert _select_live_point_from_batch(batch, NOW, NOW - 299, 600) is None
    assert _select_live_point_from_batch(batch, NOW, NOW - 601, 600) is not None
    # Between the base and the widened window: only the widened one blocks.
    assert _select_live_point_from_batch(batch, NOW, NOW - 450, 600) is None
    assert _select_live_point_from_batch(batch, NOW, NOW - 450) is not None


def test_batch_used_when_no_realtime_data_ever_seen():
    batch = [_point(NOW - 60, 630)]
    assert _select_live_point_from_batch(batch, NOW, 0)["co2"]["value"] == 630


def test_picks_newest_by_timestamp_not_list_position():
    batch = [_point(NOW - 10, 870), _point(NOW - 600, 700), _point(NOW - 900, 630)]
    assert _select_live_point_from_batch(batch, NOW, 0)["co2"]["value"] == 870


def test_ignores_timestamps_far_in_the_future():
    batch = [_point(NOW - 60, 870), _point(NOW + 86_400, 1)]
    assert _select_live_point_from_batch(batch, NOW, 0)["co2"]["value"] == 870


def test_falls_back_to_last_item_without_timestamps():
    batch = [{"co2": {"value": 1}}, {"co2": {"value": 2}}]
    assert _select_live_point_from_batch(batch, NOW, 0)["co2"]["value"] == 2


def test_empty_or_invalid_batch():
    assert _select_live_point_from_batch([], NOW, 0) is None
    assert _select_live_point_from_batch(["x"], NOW, 0) is None


# --- end-to-end through the MQTT handler -------------------------------------


@pytest.fixture
async def cgs2(hass):
    """Set up a CGS2 sensor platform and return (send_message, sensors)."""
    entry = MagicMock()
    entry.entry_id = "cgs2_entry"
    entry.data = {"mac": "582D34705CDD", "name": "Air Monitor", "model": "CGS2"}
    entry.options = {}
    coordinator = MagicMock()
    coordinator.data = {}
    hass.data[DOMAIN] = {entry.entry_id: {"coordinator": coordinator, "sensors": []}}

    captured = {}

    async def fake_subscribe(_hass, _topic, callback, *args, **kwargs):
        captured["cb"] = callback

    added = []
    with patch(
        "custom_components.qingping_cgs1.sensor.mqtt.async_subscribe", fake_subscribe
    ), patch(
        "custom_components.qingping_cgs1.sensor.mqtt.async_publish", AsyncMock()
    ), patch(
        "custom_components.qingping_cgs1.sensor.async_track_time_interval",
        MagicMock(),
    ), patch(
        "custom_components.qingping_cgs1.sensor.ensure_mqtt_connected",
        AsyncMock(return_value=False),
    ), patch(
        "custom_components.qingping_cgs1.sensor._import_batch_statistics",
        AsyncMock(),
    ), patch(
        "custom_components.qingping_cgs1.sensor._write_batch_to_influxdb",
        AsyncMock(),
    ):
        await async_setup_entry(hass, entry, added.extend)
        for entity in added:
            entity.hass = hass
            entity.async_write_ha_state = MagicMock()

        def send(payload):
            captured["cb"](SimpleNamespace(payload=json.dumps(payload).encode()))

        yield send, {getattr(e, "_sensor_type", None): e for e in added}
        await hass.async_block_till_done()


def _co2(value, ts):
    return {"timestamp": {"value": ts}, "co2": {"value": value}}


# Setup schedules a delayed config publish (asyncio.sleep(2)) that outlives the test.
@pytest.mark.parametrize("expected_lingering_tasks", [True])
async def test_type17_batch_does_not_overwrite_live_reading(cgs2):
    send, sensors = cgs2
    co2 = sensors["co2"]
    now = int(time.time())

    send({"type": "12", "sensorData": [_co2(870, now)]})
    assert co2.native_value == 870

    # History upload whose last item is an old reading (as seen on a CGS2).
    send({"type": "17", "sensorData": [_co2(869, now - 60), _co2(630, now - 3600)]})
    assert co2.native_value == 870


@pytest.mark.parametrize("expected_lingering_tasks", [True])
async def test_type17_batch_sets_value_when_no_realtime_data(cgs2):
    send, sensors = cgs2
    now = int(time.time())

    send({"type": "17", "sensorData": [_co2(700, now - 120), _co2(650, now - 60)]})
    assert sensors["co2"].native_value == 650
