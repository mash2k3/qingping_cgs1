"""Alarm clock support for Qingping JSON devices."""
from __future__ import annotations

import datetime
import json
import logging
import time

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, MQTT_TOPIC_PREFIX, CONF_ALARMS

_LOGGER = logging.getLogger(__name__)

ALARM_MESSAGE_TYPE = "40"
ALARM_ACTION_SYNC = "alarmSync"
ALARM_ACTION_QUERY = "alarmQuery"
SIGNAL_ALARMS_UPDATED = f"{DOMAIN}_alarms_updated"

RINGTONES = {
    "1d019fd6": "Exotic Guitar",
    "6e70b659": "Lively Piano",
    "8f004886": "Story Piano",
    "fdc366a5": "Beep",
    "ea2d4c02": "Cuckoo",
    "0961bb77": "Digital Ringtone",
    "ba2c2c8c": "Digital Ringtone 2",
    "791bacb3": "Telephone Ringtone",
}
RINGTONE_IDS = {v: k for k, v in RINGTONES.items()}
DEFAULT_RINGTONE = "6e70b659"

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def repeat_to_days(repeat: str) -> list[int]:
    """Convert device repeat string to a sorted list of day numbers (1 = Monday)."""
    days = set()
    for part in str(repeat or "").split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= 7:
            days.add(int(part))
    return sorted(days)


def days_to_repeat(days) -> str:
    """Convert day numbers or weekday names to device repeat string."""
    nums = set()
    for day in days or []:
        if isinstance(day, str) and day.lower() in WEEKDAYS:
            nums.add(WEEKDAYS.index(day.lower()) + 1)
        elif str(day).isdigit() and 1 <= int(day) <= 7:
            nums.add(int(day))
    return ",".join(str(d) for d in sorted(nums))


def hhmmss_to_time(value) -> datetime.time:
    """Convert device hhmmss integer (60000 = 06:00:00) to time."""
    value = int(value or 0)
    return datetime.time(hour=value // 10000, minute=value // 100 % 100, second=value % 100)


def time_to_hhmmss(value: datetime.time) -> int:
    """Convert time to device hhmmss integer."""
    return value.hour * 10000 + value.minute * 100


def ringtone_name(ringtone_id: str) -> str:
    """Return ringtone display name, falling back to the raw id."""
    return RINGTONES.get(ringtone_id, ringtone_id)


def ringtone_id(name_or_id: str) -> str:
    """Return ringtone id for a display name or id."""
    return RINGTONE_IDS.get(name_or_id, name_or_id)


class QingpingAlarmManager:
    """Keep the device alarm list in sync over MQTT."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, mac: str) -> None:
        """Initialize the manager with the alarms stored in the config entry."""
        self.hass = hass
        self.config_entry = config_entry
        self.mac = mac
        self.alarms: dict[int, dict] = {
            int(alarm["local_id"]): alarm
            for alarm in config_entry.data.get(CONF_ALARMS, [])
        }
        self._message_id = int(time.time()) % 1000000

    @property
    def supported(self) -> bool:
        """Return True once the device has reported its alarm list."""
        return CONF_ALARMS in self.config_entry.data

    def _next_message_id(self) -> int:
        self._message_id += 1
        return self._message_id

    @property
    def topic(self) -> str:
        """Return the device downlink topic."""
        return f"{MQTT_TOPIC_PREFIX}/{self.mac}/down"

    def as_list(self) -> list[dict]:
        """Return the alarms in a frontend friendly format."""
        return [
            {
                "id": local_id,
                "time": hhmmss_to_time(alarm.get("hhmmss")).strftime("%H:%M"),
                "days": [WEEKDAYS[d - 1] for d in repeat_to_days(alarm.get("repeat"))],
                "ringtone": ringtone_name(alarm.get("ringtone")),
                "snooze": bool(alarm.get("delayable")),
                "enabled": bool(alarm.get("enabled")),
            }
            for local_id, alarm in sorted(self.alarms.items(), key=lambda item: (item[1].get("hhmmss", 0), item[0]))
        ]

    async def async_request(self) -> None:
        """Ask the device to report its alarm list."""
        payload = {"type": ALARM_MESSAGE_TYPE, "action": ALARM_ACTION_QUERY, "id": self._next_message_id()}
        await mqtt.async_publish(self.hass, self.topic, json.dumps(payload))

    @callback
    def handle_message(self, payload: dict) -> None:
        """Handle a type 40 message from the device."""
        if payload.get("action") != ALARM_ACTION_SYNC:
            _LOGGER.debug("[%s] Unknown alarm action: %s", self.mac, payload.get("action"))
            return

        if "ack_id" in payload:
            if payload.get("code") not in (0, "0"):
                _LOGGER.warning("[%s] Device rejected alarm list (code %s)", self.mac, payload.get("code"))
            return

        alarms = payload.get("alarms")
        if isinstance(alarms, list):
            self._set_alarms(alarms)
            _LOGGER.info("[%s] Alarm list synced from device: %d alarms", self.mac, len(alarms))

        if payload.get("need_ack") == 1 and "id" in payload:
            ack = {
                "type": ALARM_MESSAGE_TYPE,
                "action": ALARM_ACTION_SYNC,
                "ack_id": payload["id"],
                "code": 0,
            }
            self.hass.async_create_task(mqtt.async_publish(self.hass, self.topic, json.dumps(ack)))

    @callback
    def _set_alarms(self, alarms: list[dict]) -> None:
        self.alarms = {
            int(alarm["local_id"]): alarm
            for alarm in alarms
            if isinstance(alarm, dict) and "local_id" in alarm
        }
        new_data = dict(self.config_entry.data)
        new_data[CONF_ALARMS] = list(self.alarms.values())
        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
        async_dispatcher_send(self.hass, SIGNAL_ALARMS_UPDATED)

    async def _async_write(self, alarms: list[dict]) -> None:
        self._set_alarms(alarms)
        payload = {
            "type": ALARM_MESSAGE_TYPE,
            "action": ALARM_ACTION_SYNC,
            "id": self._next_message_id(),
            "need_ack": 1,
            "alarms": sorted(alarms, key=lambda a: (a.get("hhmmss", 0), a["local_id"])),
        }
        await mqtt.async_publish(self.hass, self.topic, json.dumps(payload))
        _LOGGER.info("[%s] Published alarm list: %d alarms", self.mac, len(alarms))

    async def async_update(self, local_id: int, **changes) -> None:
        """Change fields of an existing alarm."""
        if local_id not in self.alarms:
            raise KeyError(local_id)
        alarms = [
            {**alarm, **changes} if lid == local_id else alarm
            for lid, alarm in self.alarms.items()
        ]
        await self._async_write(alarms)

    async def async_add(self, **fields) -> int:
        """Add a new alarm and return its local id."""
        local_id = max(self.alarms, default=0) + 1
        alarm = {
            "delayable": 0,
            "enabled": 1,
            "hhmmss": 0,
            "local_id": local_id,
            "name": "",
            "repeat": "",
            "ringtone": DEFAULT_RINGTONE,
            **fields,
        }
        await self._async_write([*self.alarms.values(), alarm])
        return local_id

    async def async_delete(self, local_id: int) -> None:
        """Delete an alarm."""
        if local_id not in self.alarms:
            raise KeyError(local_id)
        await self._async_write([a for lid, a in self.alarms.items() if lid != local_id])
