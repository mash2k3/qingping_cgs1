"""The Qingping Device integration."""
from __future__ import annotations

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr, translation
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from functools import partial
import logging
import os
import voluptuous as vol

from .const import DOMAIN, CONF_TEMPERATURE_OFFSET, CONF_HUMIDITY_OFFSET, DEFAULT_OFFSET, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
from .const import CONF_MAC, CONF_MODEL, JSON_MODELS, CONF_SHOW_ALARMS_PANEL, DEFAULT_SHOW_ALARMS_PANEL
from .alarms import (
    QingpingAlarmManager, RINGTONES, WEEKDAYS, SIGNAL_ALARMS_UPDATED,
    days_to_repeat, ringtone_id, time_to_hhmmss,
)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.SELECT, Platform.SWITCH, Platform.BUTTON, Platform.TIME]

_LOGGER = logging.getLogger(__name__)

PANEL_URL_PATH = "qingping-alarms"
PANEL_COMPONENT = "qingping-alarms-panel"
PANEL_STATIC_URL = f"/{DOMAIN}_frontend"
PANEL_FILE = os.path.join(os.path.dirname(__file__), "frontend", f"{PANEL_COMPONENT}.js")
PANEL_DATA = f"{DOMAIN}_panel"

SERVICE_ADD_ALARM = "add_alarm"
SERVICE_UPDATE_ALARM = "update_alarm"
SERVICE_DELETE_ALARM = "delete_alarm"

ALARM_FIELDS = {
    vol.Optional("days"): vol.All(cv.ensure_list, [vol.In(WEEKDAYS)]),
    vol.Optional("ringtone"): vol.In(list(RINGTONES.values())),
    vol.Optional("snooze"): cv.boolean,
    vol.Optional("enabled"): cv.boolean,
}
ADD_ALARM_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("time"): cv.time,
    **ALARM_FIELDS,
})
UPDATE_ALARM_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("alarm_id"): vol.Coerce(int),
    vol.Optional("time"): cv.time,
    **ALARM_FIELDS,
})
DELETE_ALARM_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("alarm_id"): vol.Coerce(int),
})


def _alarm_fields(data: dict) -> dict:
    """Convert service data to device alarm fields."""
    fields = {}
    if "time" in data:
        fields["hhmmss"] = time_to_hhmmss(data["time"])
    if "days" in data:
        fields["repeat"] = days_to_repeat(data["days"])
    if "ringtone" in data:
        fields["ringtone"] = ringtone_id(data["ringtone"])
    if "snooze" in data:
        fields["delayable"] = int(data["snooze"])
    if "enabled" in data:
        fields["enabled"] = int(data["enabled"])
    return fields


def _alarm_managers(hass: HomeAssistant) -> dict[str, QingpingAlarmManager]:
    """Return alarm managers of loaded devices that support alarms, by entry id."""
    return {
        entry_id: data["alarm_manager"]
        for entry_id, data in hass.data.get(DOMAIN, {}).items()
        if isinstance(data, dict) and "alarm_manager" in data and data["alarm_manager"].supported
    }


def _panel_managers(hass: HomeAssistant) -> dict[str, QingpingAlarmManager]:
    """Alarm managers of the devices whose options keep them on the alarms page."""
    managers = {}
    for entry_id, manager in _alarm_managers(hass).items():
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry and entry.options.get(CONF_SHOW_ALARMS_PANEL, DEFAULT_SHOW_ALARMS_PANEL):
            managers[entry_id] = manager
    return managers


def _get_alarm_manager(hass: HomeAssistant, device_id: str) -> QingpingAlarmManager:
    """Return the alarm manager of a device."""
    device = dr.async_get(hass).async_get(device_id)
    entry_ids = []
    if device:
        entry_ids = [device.config_entry_id] if hasattr(device, "config_entry_id") else device.config_entries
    managers = _alarm_managers(hass)
    manager = next((managers[e] for e in entry_ids if e in managers), None)
    if manager is None:
        raise ServiceValidationError("Unknown Qingping device or alarms are not supported")
    return manager


def _get_alarm(hass: HomeAssistant, data: dict) -> tuple[QingpingAlarmManager, int]:
    """Return the alarm manager and alarm id from service data."""
    manager = _get_alarm_manager(hass, data["device_id"])
    if data["alarm_id"] not in manager.alarms:
        raise ServiceValidationError(f"Alarm {data['alarm_id']} does not exist on the device")
    return manager, data["alarm_id"]


@callback
def _alarms_snapshot(hass: HomeAssistant) -> list[dict]:
    """Return all devices with their alarms for the panel."""
    registry = dr.async_get(hass)
    devices = []
    for entry_id, manager in _panel_managers(hass).items():
        device = next(
            (d for d in dr.async_entries_for_config_entry(registry, entry_id) if (DOMAIN, manager.mac) in d.identifiers),
            None,
        )
        if device is None:
            continue
        entry = hass.config_entries.async_get_entry(entry_id)
        devices.append({
            "device_id": device.id,
            "name": device.name_by_user or device.name or (entry.title if entry else manager.mac),
            "alarms": manager.as_list(),
        })
    return sorted(devices, key=lambda d: d["name"])


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/alarms/subscribe"})
@callback
def _ws_subscribe_alarms(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Send the alarm list now and on every change."""
    @callback
    def _send() -> None:
        connection.send_message(websocket_api.event_message(msg["id"], {"devices": _alarms_snapshot(hass)}))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(hass, SIGNAL_ALARMS_UPDATED, _send)
    connection.send_result(msg["id"])
    _send()


async def _async_setup_alarm_support(hass: HomeAssistant) -> None:
    """Prepare the alarms panel files, websocket API and update listener once."""
    if PANEL_DATA in hass.data:
        return
    panel = hass.data[PANEL_DATA] = {"registered": False, "services": False, "version": 0}
    await hass.http.async_register_static_paths([
        StaticPathConfig(PANEL_STATIC_URL, os.path.dirname(PANEL_FILE), False)
    ])
    panel["version"] = int(await hass.async_add_executor_job(os.path.getmtime, PANEL_FILE))
    websocket_api.async_register_command(hass, _ws_subscribe_alarms)
    async_dispatcher_connect(hass, SIGNAL_ALARMS_UPDATED, partial(_async_update_alarm_features, hass))


async def _async_register_panel(hass: HomeAssistant, version: int) -> None:
    """Add the alarms page to the sidebar, titled in the server language."""
    texts = await translation.async_get_translations(hass, hass.config.language, "selector", [DOMAIN])
    title = texts.get(f"component.{DOMAIN}.selector.panel.options.title", "Qingping")
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_COMPONENT,
        frontend_url_path=PANEL_URL_PATH,
        sidebar_title=title,
        sidebar_icon="mdi:alarm",
        module_url=f"{PANEL_STATIC_URL}/{PANEL_COMPONENT}.js?v={version}",
        require_admin=False,
    )


@callback
def _async_update_alarm_features(hass: HomeAssistant) -> None:
    """Offer services while a device with alarms is loaded, the panel while one of them wants it."""
    panel = hass.data.get(PANEL_DATA)
    if panel is None:
        return
    supported = bool(_alarm_managers(hass))
    if supported and not panel["services"]:
        panel["services"] = True
        _async_register_services(hass)
    elif not supported and panel["services"]:
        panel["services"] = False
        for service in (SERVICE_ADD_ALARM, SERVICE_UPDATE_ALARM, SERVICE_DELETE_ALARM):
            hass.services.async_remove(DOMAIN, service)
    wanted = bool(_panel_managers(hass))
    if wanted and not panel["registered"]:
        panel["registered"] = True
        hass.async_create_task(_async_register_panel(hass, panel["version"]))
    elif not wanted and panel["registered"]:
        panel["registered"] = False
        frontend.async_remove_panel(hass, PANEL_URL_PATH)


@callback
def _async_register_services(hass: HomeAssistant) -> None:
    """Register alarm services."""

    async def add_alarm(call: ServiceCall) -> None:
        await _get_alarm_manager(hass, call.data["device_id"]).async_add(**_alarm_fields(call.data))

    async def update_alarm(call: ServiceCall) -> None:
        manager, local_id = _get_alarm(hass, call.data)
        await manager.async_update(local_id, **_alarm_fields(call.data))

    async def delete_alarm(call: ServiceCall) -> None:
        manager, local_id = _get_alarm(hass, call.data)
        await manager.async_delete(local_id)

    hass.services.async_register(DOMAIN, SERVICE_ADD_ALARM, add_alarm, schema=ADD_ALARM_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_UPDATE_ALARM, update_alarm, schema=UPDATE_ALARM_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_DELETE_ALARM, delete_alarm, schema=DELETE_ALARM_SCHEMA)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Qingping Device from a config entry."""
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

    if entry.data.get(CONF_MODEL) in JSON_MODELS:
        hass.data[DOMAIN][entry.entry_id]["alarm_manager"] = QingpingAlarmManager(hass, entry, entry.data[CONF_MAC])
        await _async_setup_alarm_support(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # the "show alarms page" option applies without a reload
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    async_dispatcher_send(hass, SIGNAL_ALARMS_UPDATED)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    async_dispatcher_send(hass, SIGNAL_ALARMS_UPDATED)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        async_dispatcher_send(hass, SIGNAL_ALARMS_UPDATED)
    return unload_ok