"""Integration tests for 0.2 features inside a real Home Assistant core."""

from datetime import timedelta

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.fbd_logic.const import DOMAIN


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="FBD Logic", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _tick(hass: HomeAssistant, seconds: float = 1.1) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))
    await hass.async_block_till_done()


async def _ws(client, msg):
    await client.send_json_auto_id(msg)
    res = await client.receive_json()
    while res.get("type") == "event":
        res = await client.receive_json()
    return res


MACRO = {
    "id": "term",
    "name": "Termostat",
    "symbol": "TERM",
    "nodes": [
        {"id": "pv", "type": "macro_in", "y": 0, "params": {"name": "pv", "type": "num", "default": "0"}},
        {"id": "sp", "type": "macro_in", "y": 60, "params": {"name": "sp", "type": "num", "default": "21"}},
        {"id": "lt", "type": "lt", "x": 150},
        {"id": "o", "type": "macro_out", "x": 300, "params": {"name": "varme", "type": "bool"}},
        {"id": "set", "type": "setpoint", "x": 0, "y": 200, "params": {"name": "Komfort", "initial": 22}},
    ],
    "links": [
        {"id": "a", "from": "pv", "from_port": "value", "to": "lt", "to_port": "a"},
        {"id": "b", "from": "sp", "from_port": "value", "to": "lt", "to_port": "b"},
        {"id": "c", "from": "lt", "from_port": "q", "to": "o", "to_port": "value"},
    ],
}


async def test_macro_lifecycle(hass: HomeAssistant, hass_ws_client) -> None:
    hass.states.async_set("sensor.t", "19")
    light_on = async_mock_service(hass, "light", "turn_on")
    await _setup(hass)
    client = await hass_ws_client(hass)

    res = await _ws(client, {"type": "fbd_logic/macro/save", "macro": MACRO})
    assert res["success"], res
    res = await _ws(client, {"type": "fbd_logic/blocks"})
    mdef = next(b for b in res["result"]["blocks"] if b["type"] == "macro:term")
    assert [p["name"] for p in mdef["inputs"]] == ["pv", "sp"]

    prog = {
        "id": "rom",
        "name": "Rom",
        "nodes": [
            {"id": "t", "type": "entity_in", "params": {"entity_id": "sensor.t"}},
            {"id": "m", "type": "macro:term", "x": 200, "label": "Stue"},
            {"id": "o", "type": "entity_out", "x": 400, "params": {"entity_id": "light.varme"}},
        ],
        "links": [
            {"id": "1", "from": "t", "from_port": "value", "to": "m", "to_port": "pv"},
            {"id": "2", "from": "m", "from_port": "varme", "to": "o", "to_port": "value"},
        ],
    }
    res = await _ws(client, {"type": "fbd_logic/program/save", "program": prog})
    assert res["success"] and res["result"]["warnings"] == [], res
    await hass.async_block_till_done()
    assert len(light_on) == 1
    # the setpoint inside the macro became an entity named after the instance
    ent_id = er.async_get(hass).async_get_entity_id("number", DOMAIN, "rom_m/set")
    assert ent_id and hass.states.get(ent_id).name.endswith("Stue Komfort")

    # macro in use cannot be deleted
    res = await _ws(client, {"type": "fbd_logic/macro/delete", "macro_id": "term"})
    assert not res["success"] and res["error"]["code"] == "in_use"

    # changing the macro recompiles the program (sp default 10 -> 19 < 10 false)
    changed = dict(MACRO)
    changed["nodes"] = [dict(n) for n in MACRO["nodes"]]
    changed["nodes"][1] = {**changed["nodes"][1], "params": {"name": "sp", "type": "num", "default": "10"}}
    res = await _ws(client, {"type": "fbd_logic/macro/save", "macro": changed})
    assert res["success"]
    await _tick(hass)
    snap = hass.data[DOMAIN].snapshot("rom")
    assert snap["nodes"]["m"]["o"]["varme"] is False

    # a macro containing itself is rejected
    bad = {"id": "loop", "name": "Loop", "nodes": [{"id": "x", "type": "macro:loop"}]}
    res = await _ws(client, {"type": "fbd_logic/macro/save", "macro": bad})
    assert not res["success"]

    res = await _ws(client, {"type": "fbd_logic/macros"})
    assert res["result"]["macros"][0]["used_by"] == ["Rom"]


async def test_force_and_trend(hass: HomeAssistant, hass_ws_client) -> None:
    hass.states.async_set("sensor.t", "20")
    entry = await _setup(hass)
    client = await hass_ws_client(hass)
    prog = {
        "id": "f",
        "name": "Force",
        "nodes": [
            {"id": "t", "type": "entity_in", "params": {"entity_id": "sensor.t"}},
            {"id": "gt", "type": "gt", "x": 200, "consts": {"b": 25}},
            {"id": "pub", "type": "publish", "x": 400, "params": {"name": "Alarm"}},
        ],
        "links": [
            {"id": "1", "from": "t", "from_port": "value", "to": "gt", "to_port": "a"},
            {"id": "2", "from": "gt", "from_port": "q", "to": "pub", "to_port": "value"},
        ],
    }
    assert (await _ws(client, {"type": "fbd_logic/program/save", "program": prog}))["success"]
    await hass.async_block_till_done()
    alarm = er.async_get(hass).async_get_entity_id("binary_sensor", DOMAIN, "f_pub")
    assert hass.states.get(alarm).state == "off"

    res = await _ws(client, {"type": "fbd_logic/force", "program_id": "f", "node_id": "t", "port": "value", "value": 30})
    assert res["success"] and res["result"]["forces"] == {"t": {"value": 30.0}}
    await _tick(hass)
    assert hass.states.get(alarm).state == "on"
    snap = hass.data[DOMAIN].snapshot("f")
    assert snap["forced"] == 1 and snap["nodes"]["t"]["f"] == {"value": 30.0}

    # trends
    res = await _ws(client, {"type": "fbd_logic/trend/set", "program_id": "f", "signals": ["t|value", "gt|q", "t|value"]})
    assert res["result"]["signals"] == ["t|value", "gt|q"]
    for _ in range(3):
        await _tick(hass, 1.2)
    res = await _ws(client, {"type": "fbd_logic/trend/get", "program_id": "f"})
    data = res["result"]["data"]
    assert len(data["t|value"]) >= 1 and data["t|value"][-1][1] == 30.0
    assert data["gt|q"][-1][1] is True

    # forces and trend signals survive a reload
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    manager = hass.data[DOMAIN]
    assert manager.forces == {"f": {"t": {"value": 30.0}}}
    assert manager.trend_signals == {"f": ["t|value", "gt|q"]}

    # release
    res = await _ws(client, {"type": "fbd_logic/force", "program_id": "f", "node_id": "t", "port": "value", "value": None})
    assert res["result"]["forces"] == {}
    await _tick(hass)
    assert hass.states.get(alarm).state == "off"
    await _ws(client, {"type": "fbd_logic/force", "program_id": "f", "node_id": "t", "port": "value", "value": 40})
    assert (await _ws(client, {"type": "fbd_logic/force/clear", "program_id": "f"}))["success"]
    assert manager.forces == {}


async def test_knx_and_modbus(hass: HomeAssistant, hass_ws_client) -> None:
    knx_send = async_mock_service(hass, "knx", "send")
    knx_reg = async_mock_service(hass, "knx", "event_register")
    knx_read = async_mock_service(hass, "knx", "read")
    mb_reg = async_mock_service(hass, "modbus", "write_register")
    await _setup(hass)
    client = await hass_ws_client(hass)
    prog = {
        "id": "bus",
        "name": "Bus",
        "nodes": [
            {"id": "rd", "type": "knx_read", "params": {"address": "3/1/1", "dpt": "9.001"}},
            {"id": "tx", "type": "knx_send", "x": 200, "params": {"address": "3/1/2", "dpt": "9.001"}},
            {"id": "mb", "type": "modbus_write", "x": 200, "y": 200, "params": {"hub": "h", "address": 7, "dtype": "float32"}},
        ],
        "links": [
            {"id": "1", "from": "rd", "from_port": "value", "to": "tx", "to_port": "value"},
            {"id": "2", "from": "rd", "from_port": "value", "to": "mb", "to_port": "value"},
        ],
    }
    assert (await _ws(client, {"type": "fbd_logic/program/save", "program": prog}))["success"]
    await hass.async_block_till_done()
    assert knx_reg[0].data == {"address": "3/1/1", "type": "9.001"}
    assert knx_read[0].data == {"address": "3/1/1"}
    assert knx_send[0].data == {"address": "3/1/2", "payload": 0.0, "type": "9.001"}

    hass.bus.async_fire(
        "knx_event",
        {"destination": "3/1/1", "telegramtype": "GroupValueWrite", "value": 21.5, "data": [12, 99], "direction": "Incoming"},
    )
    await _tick(hass)
    assert knx_send[-1].data["payload"] == 21.5
    assert mb_reg[-1].data == {"hub": "h", "slave": 1, "address": 7, "value": [0x41AC, 0x0000]}
    snap = hass.data[DOMAIN].snapshot("bus")
    assert snap["nodes"]["rd"]["o"]["valid"] is True


async def test_knx_missing_integration_shows_error(hass: HomeAssistant, hass_ws_client) -> None:
    await _setup(hass)
    client = await hass_ws_client(hass)
    prog = {"id": "k", "name": "K", "nodes": [{"id": "rd", "type": "knx_read", "params": {"address": "1/1/1"}}]}
    assert (await _ws(client, {"type": "fbd_logic/program/save", "program": prog}))["success"]
    await hass.async_block_till_done()
    assert "KNX" in hass.data[DOMAIN].snapshot("k")["nodes"]["rd"]["e"]


async def test_pages_roundtrip(hass: HomeAssistant, hass_ws_client) -> None:
    await _setup(hass)
    client = await hass_ws_client(hass)
    prog = {
        "id": "pg",
        "name": "Sider",
        "pages": [{"id": "a", "name": "Inn"}, {"id": "b", "name": "Ut"}],
        "nodes": [
            {"id": "k", "type": "const_num", "page": "a", "params": {"value": 5}},
            {"id": "tx", "type": "page_out", "page": "a", "x": 150, "params": {"name": "v"}},
            {"id": "rx", "type": "page_in", "page": "b", "params": {"name": "v"}},
            {"id": "pub", "type": "publish", "page": "b", "x": 150, "params": {"name": "Verdi"}},
        ],
        "links": [
            {"id": "1", "from": "k", "from_port": "out", "to": "tx", "to_port": "value", "mx": 120},
            {"id": "2", "from": "rx", "from_port": "value", "to": "pub", "to_port": "value", "my": 90},
        ],
    }
    res = await _ws(client, {"type": "fbd_logic/program/save", "program": prog})
    assert res["success"] and res["result"]["warnings"] == []
    await hass.async_block_till_done()
    res = await _ws(client, {"type": "fbd_logic/program/get", "program_id": "pg"})
    assert res["result"]["program"]["pages"][1]["name"] == "Ut"
    assert res["result"]["program"]["nodes"][2]["page"] == "b"
    # Hand-placed wire bends are kept as drawn
    links = {l["id"]: l for l in res["result"]["program"]["links"]}
    assert links["1"]["mx"] == 120 and links["2"]["my"] == 90
    sensor = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "pg_pub")
    assert hass.states.get(sensor).state == "5.0"
