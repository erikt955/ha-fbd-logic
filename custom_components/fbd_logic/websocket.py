"""Websocket API used by the editor panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .blocks import LIBRARY, library_json
from .const import DOMAIN
from .i18n import language_for, tr


def _manager(hass: HomeAssistant, connection, msg) -> Any:
    manager = hass.data.get(DOMAIN)
    if manager is None:
        connection.send_error(msg["id"], "not_loaded", tr("FBD Logic er ikke lastet"))
    return manager


@callback
def async_register(hass: HomeAssistant) -> None:
    for handler in (
        ws_blocks,
        ws_programs,
        ws_program_get,
        ws_program_save,
        ws_program_delete,
        ws_program_enable,
        ws_subscribe,
        ws_set_value,
        ws_force,
        ws_force_clear,
        ws_trend_get,
        ws_trend_set,
        ws_macros,
        ws_macro_get,
        ws_macro_save,
        ws_macro_delete,
    ):
        websocket_api.async_register_command(hass, handler)


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/blocks", vol.Optional("language"): vol.Any(str, None)}
)
@callback
def ws_blocks(hass: HomeAssistant, connection, msg) -> None:
    """The block library in the panel user's language (Norwegian, otherwise English)."""
    manager = hass.data.get(DOMAIN)
    lang = language_for(msg.get("language") or hass.config.language)
    connection.send_result(msg["id"], library_json(manager.macros if manager else None, lang))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/programs"})
@callback
def ws_programs(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return
    connection.send_result(msg["id"], {"programs": manager.list_programs()})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/program/get", vol.Required("program_id"): str}
)
@callback
def ws_program_get(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return
    data = manager.programs.get(msg["program_id"])
    if data is None:
        connection.send_error(msg["id"], "not_found", tr("Programmet finnes ikke"))
        return
    connection.send_result(msg["id"], {"program": data})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/program/save", vol.Required("program"): dict}
)
@websocket_api.async_response
async def ws_program_save(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return
    try:
        result = await manager.async_save_program(msg["program"])
    except vol.Invalid as err:
        connection.send_error(msg["id"], "invalid_format", tr("Ugyldig program: {err}", err=err))
        return
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/program/delete", vol.Required("program_id"): str}
)
@websocket_api.async_response
async def ws_program_delete(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return
    await manager.async_delete_program(msg["program_id"])
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/program/enable",
        vol.Required("program_id"): str,
        vol.Required("enabled"): bool,
    }
)
@websocket_api.async_response
async def ws_program_enable(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return
    try:
        await manager.async_set_enabled(msg["program_id"], msg["enabled"])
    except KeyError:
        connection.send_error(msg["id"], "not_found", tr("Programmet finnes ikke"))
        return
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/subscribe", vol.Required("program_id"): str}
)
@callback
def ws_subscribe(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return

    @callback
    def forward(snapshot: dict[str, Any]) -> None:
        connection.send_message(websocket_api.event_message(msg["id"], snapshot))

    connection.send_result(msg["id"])
    connection.subscriptions[msg["id"]] = manager.subscribe(msg["program_id"], forward)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/set_value",
        vol.Required("program_id"): str,
        vol.Required("node_id"): str,
        vol.Required("value"): vol.Any(bool, vol.Coerce(float)),
    }
)
@callback
def ws_set_value(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return
    prog = manager.runtime.get(msg["program_id"])
    node = prog.nodes.get(msg["node_id"]) if prog else None
    if node is None or node.bdef.ha not in ("setpoint", "toggle"):
        connection.send_error(msg["id"], "not_found", tr("Fant ikke settpunkt/bryter"))
        return
    value = msg["value"]
    if node.bdef.ha == "toggle":
        value = bool(value)
    else:
        value = float(value)
    manager.set_value(msg["program_id"], msg["node_id"], value)
    connection.send_result(msg["id"])


# ---------------------------------------------------------------------- forcing
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/force",
        vol.Required("program_id"): str,
        vol.Required("node_id"): str,
        vol.Required("port"): str,
        vol.Required("value"): vol.Any(None, bool, int, float, str),
    }
)
@callback
def ws_force(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return
    try:
        forces = manager.set_force(msg["program_id"], msg["node_id"], msg["port"], msg["value"])
    except KeyError:
        connection.send_error(msg["id"], "not_found", tr("Programmet finnes ikke"))
        return
    connection.send_result(msg["id"], {"forces": forces})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/force/clear", vol.Required("program_id"): str}
)
@callback
def ws_force_clear(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return
    manager.clear_forces(msg["program_id"])
    connection.send_result(msg["id"])


# ---------------------------------------------------------------------- trends
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/trend/get", vol.Required("program_id"): str}
)
@callback
def ws_trend_get(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return
    connection.send_result(msg["id"], manager.trend(msg["program_id"]))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/trend/set",
        vol.Required("program_id"): str,
        vol.Required("signals"): [str],
    }
)
@callback
def ws_trend_set(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return
    if msg["program_id"] not in manager.programs:
        connection.send_error(msg["id"], "not_found", tr("Programmet finnes ikke"))
        return
    manager.set_trend_signals(msg["program_id"], msg["signals"])
    connection.send_result(msg["id"], manager.trend(msg["program_id"]))


# ---------------------------------------------------------------------- macros
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/macros"})
@callback
def ws_macros(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return
    connection.send_result(msg["id"], {"macros": manager.list_macros()})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/macro/get", vol.Required("macro_id"): str}
)
@callback
def ws_macro_get(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return
    data = manager.macros.get(msg["macro_id"])
    if data is None:
        connection.send_error(msg["id"], "not_found", tr("Makroen finnes ikke"))
        return
    connection.send_result(msg["id"], {"macro": data, "used_by": manager.macro_users(msg["macro_id"])})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/macro/save", vol.Required("macro"): dict}
)
@websocket_api.async_response
async def ws_macro_save(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return
    try:
        result = await manager.async_save_macro(msg["macro"])
    except vol.Invalid as err:
        connection.send_error(msg["id"], "invalid_format", tr("Ugyldig makro: {err}", err=err))
        return
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/macro/delete", vol.Required("macro_id"): str}
)
@websocket_api.async_response
async def ws_macro_delete(hass: HomeAssistant, connection, msg) -> None:
    if (manager := _manager(hass, connection, msg)) is None:
        return
    users = await manager.async_delete_macro(msg["macro_id"])
    if users:
        connection.send_error(
            msg["id"], "in_use", tr("Makroen er i bruk i: {users}", users=", ".join(users))
        )
        return
    connection.send_result(msg["id"])


__all__ = ["async_register", "LIBRARY"]
