"""Integration tests running the custom component inside a real Home Assistant core."""

from datetime import timedelta

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from custom_components.fbd_logic.const import DOMAIN, PANEL_URL_PATH


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="FBD Logic", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _program(**kw):
    prog = {
        "id": "vent",
        "name": "Ventilasjon",
        "interval": 1,
        "enabled": True,
        "nodes": [
            {"id": "tin", "type": "entity_in", "x": 0, "y": 0, "params": {"entity_id": "sensor.room_temp"}},
            {"id": "sp", "type": "setpoint", "x": 0, "y": 120, "params": {"name": "Romtemp SP", "initial": 21, "unit": "°C", "min": 15, "max": 28}},
            {"id": "man", "type": "toggle", "x": 0, "y": 240, "params": {"name": "Manuell drift"}},
            {"id": "gt", "type": "gt", "x": 200, "y": 0},
            {"id": "or", "type": "or", "x": 350, "y": 0, "params": {"n": 2}},
            {"id": "out", "type": "entity_out", "x": 500, "y": 0, "params": {"entity_id": "light.fan"}},
            {"id": "sub", "type": "sub", "x": 200, "y": 160},
            {"id": "pub", "type": "publish", "x": 350, "y": 160, "params": {"name": "Avvik", "unit": "K", "decimals": 1}},
            {"id": "pubb", "type": "publish", "x": 650, "y": 0, "params": {"name": "Vifte på"}},
            {"id": "num", "type": "entity_out", "x": 500, "y": 160, "params": {"entity_id": "input_number.target"}},
        ],
        "links": [
            {"id": "l1", "from": "tin", "from_port": "value", "to": "gt", "to_port": "a"},
            {"id": "l2", "from": "sp", "from_port": "value", "to": "gt", "to_port": "b"},
            {"id": "l3", "from": "gt", "from_port": "q", "to": "or", "to_port": "in1"},
            {"id": "l4", "from": "man", "from_port": "q", "to": "or", "to_port": "in2"},
            {"id": "l5", "from": "or", "from_port": "q", "to": "out", "to_port": "value"},
            {"id": "l6", "from": "tin", "from_port": "value", "to": "sub", "to_port": "a"},
            {"id": "l7", "from": "sp", "from_port": "value", "to": "sub", "to_port": "b"},
            {"id": "l8", "from": "sub", "from_port": "out", "to": "pub", "to_port": "value"},
            {"id": "l9", "from": "or", "from_port": "q", "to": "pubb", "to_port": "value"},
            {"id": "l10", "from": "sp", "from_port": "value", "to": "num", "to_port": "value"},
        ],
    }
    prog.update(kw)
    return prog


async def _tick(hass: HomeAssistant, seconds: float = 1.1) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))
    await hass.async_block_till_done()


async def test_setup_registers_panel(hass: HomeAssistant) -> None:
    await _setup(hass)
    panels = hass.data["frontend_panels"]
    assert PANEL_URL_PATH in panels
    panel = panels[PANEL_URL_PATH].to_response()
    assert panel["component_name"] == "custom"
    assert panel["config"]["_panel_custom"]["name"] == "fbd-logic-panel"
    assert panel["require_admin"] is True


async def test_full_program_flow(hass: HomeAssistant, hass_ws_client) -> None:
    await async_setup_component(
        hass, "input_number", {"input_number": {"target": {"min": 0, "max": 50, "step": 0.5}}}
    )
    hass.states.async_set("sensor.room_temp", "23.4")
    light_on = async_mock_service(hass, "light", "turn_on")
    light_off = async_mock_service(hass, "light", "turn_off")
    await _setup(hass)
    client = await hass_ws_client(hass)

    # Block library
    await client.send_json_auto_id({"type": "fbd_logic/blocks"})
    res = await client.receive_json()
    assert res["success"]
    assert any(b["type"] == "pid" for b in res["result"]["blocks"])

    # Save program
    await client.send_json_auto_id({"type": "fbd_logic/program/save", "program": _program()})
    res = await client.receive_json()
    assert res["success"], res
    assert res["result"]["warnings"] == []
    await hass.async_block_till_done()

    # First scan ran on save: 23.4 > 21 -> fan on
    assert len(light_on) == 1 and light_on[0].data["entity_id"] == "light.fan"
    assert float(hass.states.get("input_number.target").state) == 21.0

    # Entities were created under a device named after the program
    ent_reg = er.async_get(hass)
    sp_id = ent_reg.async_get_entity_id("number", DOMAIN, "vent_sp")
    man_id = ent_reg.async_get_entity_id("switch", DOMAIN, "vent_man")
    pub_id = ent_reg.async_get_entity_id("sensor", DOMAIN, "vent_pub")
    pubb_id = ent_reg.async_get_entity_id("binary_sensor", DOMAIN, "vent_pubb")
    run_id = ent_reg.async_get_entity_id("switch", DOMAIN, "vent_enabled")
    assert all((sp_id, man_id, pub_id, pubb_id, run_id)), (sp_id, man_id, pub_id, pubb_id, run_id)
    assert sp_id == "number.ventilasjon_romtemp_sp"
    assert hass.states.get(sp_id).state == "21.0"
    assert hass.states.get(sp_id).attributes["unit_of_measurement"] == "°C"
    assert hass.states.get(pub_id).state == "2.4"
    assert hass.states.get(pubb_id).state == "on"
    dev = hass.data[DOMAIN]._program_device("vent")
    assert dev is not None and dev.name == "Ventilasjon"
    assert dev.id == dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "vent")}).id

    # Change setpoint from HA -> program reacts on next scan
    await hass.services.async_call("number", "set_value", {"entity_id": sp_id, "value": 25}, blocking=True)
    await _tick(hass)
    assert len(light_off) == 1
    assert hass.states.get(pubb_id).state == "off"
    assert float(hass.states.get("input_number.target").state) == 25.0
    assert hass.states.get(pub_id).state == "-1.6"

    # Manual override switch
    await hass.services.async_call("switch", "turn_on", {"entity_id": man_id}, blocking=True)
    await _tick(hass)
    assert len(light_on) == 2

    # No rewrite when nothing changes
    await _tick(hass)
    await _tick(hass)
    assert len(light_on) == 2 and len(light_off) == 1

    # Online subscription
    await client.send_json_auto_id({"type": "fbd_logic/subscribe", "program_id": "vent"})
    res = await client.receive_json()
    assert res["success"]
    event = await client.receive_json()
    snap = event["event"]
    assert snap["running"] is True
    assert snap["nodes"]["gt"]["o"]["q"] is False
    assert snap["nodes"]["or"]["o"]["q"] is True
    assert snap["nodes"]["sp"]["v"] == 25.0
    assert snap["order"]["tin"] < snap["order"]["gt"] < snap["order"]["or"] < snap["order"]["out"]

    # set_value from panel
    await client.send_json_auto_id(
        {"type": "fbd_logic/set_value", "program_id": "vent", "node_id": "sp", "value": 19}
    )
    res = await client.receive_json()
    while res.get("type") == "event":
        res = await client.receive_json()
    assert res["success"], res
    assert hass.states.get(sp_id).state == "19.0"

    # List programs
    await client.send_json_auto_id({"type": "fbd_logic/programs"})
    res = await client.receive_json()
    while res.get("type") == "event":
        res = await client.receive_json()
    assert res["result"]["programs"][0]["name"] == "Ventilasjon"

    # Disable program via switch
    await hass.services.async_call("switch", "turn_off", {"entity_id": run_id}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get(run_id).state == "off"
    hass.states.async_set("sensor.room_temp", "30")
    calls_before = len(light_on) + len(light_off)
    await _tick(hass)
    assert len(light_on) + len(light_off) == calls_before
    assert hass.states.get(pub_id).state == "-1.6"  # frozen

    # Remove a block -> its entity disappears; renaming the program renames the device
    prog = _program()
    prog["name"] = "Ventilasjon 2"
    prog["nodes"] = [n for n in prog["nodes"] if n["id"] != "pubb"]
    prog["links"] = [l for l in prog["links"] if l["to"] != "pubb"]
    await client.send_json_auto_id({"type": "fbd_logic/program/save", "program": prog})
    res = await client.receive_json()
    while res.get("type") == "event":
        res = await client.receive_json()
    assert res["success"]
    await hass.async_block_till_done()
    assert ent_reg.async_get_entity_id("binary_sensor", DOMAIN, "vent_pubb") is None
    assert hass.states.get(pubb_id) is None
    assert hass.data[DOMAIN]._program_device("vent").name == "Ventilasjon 2"

    # Delete whole program -> device and entities gone
    await client.send_json_auto_id({"type": "fbd_logic/program/delete", "program_id": "vent"})
    res = await client.receive_json()
    while res.get("type") == "event":
        res = await client.receive_json()
    assert res["success"]
    await hass.async_block_till_done()
    assert ent_reg.async_get_entity_id("number", DOMAIN, "vent_sp") is None
    assert hass.data[DOMAIN]._program_device("vent") is None
    assert dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "vent")}) is None


async def test_publish_device_class(hass: HomeAssistant, hass_ws_client) -> None:
    """Device class is matched without regard to case, and problems come back as save warnings."""
    await _setup(hass)
    client = await hass_ws_client(hass)

    def pub(nid, name, dc, unit="", kind="num"):
        params = {"name": name, "device_class": dc, "unit": unit, "kind": kind}
        return {"id": nid, "type": "publish", "params": params}

    prog = {
        "id": "dc",
        "name": "Klasser",
        "nodes": [
            {"id": "k", "type": "const_num", "params": {"value": 21.5}},
            {"id": "b", "type": "const_bool", "params": {"value": True}},
            pub("temp", "Temp", "Temperature", "°C"),  # seen in a real installation: capital letter
            pub("energy", "Energi", "energy", "kWh"),
            pub("nounit", "Uten enhet", "temperature"),
            pub("typo", "Skrivefeil", "tempratur", "°C"),
            pub("win", "Vindu", "Window", kind="bool"),
            pub("badwin", "Feil vindu", "temperature", kind="bool"),
        ],
        "links": [
            {"id": f"l{n}", "from": "b" if n in ("win", "badwin") else "k",
             "from_port": "q" if n in ("win", "badwin") else "out", "to": n, "to_port": "value"}
            for n in ("temp", "energy", "nounit", "typo", "win", "badwin")
        ],
    }
    await client.send_json_auto_id({"type": "fbd_logic/program/save", "program": prog})
    res = await client.receive_json()
    assert res["success"], res
    await hass.async_block_till_done()
    warnings = res["result"]["warnings"]
    assert len(warnings) == 4, warnings
    assert any("Energi" in w and "langtidsstatistikk" in w for w in warnings)
    assert any("Uten enhet" in w and "°C" in w for w in warnings)
    assert any("Skrivefeil" in w and "tempratur" in w for w in warnings)
    assert any("Feil vindu" in w for w in warnings)
    assert not any("«Temp»" in w or "«Vindu»" in w for w in warnings)

    ent_reg = er.async_get(hass)

    def attrs(platform, nid):
        return hass.states.get(ent_reg.async_get_entity_id(platform, DOMAIN, f"dc_{nid}")).attributes

    assert attrs("sensor", "temp")["device_class"] == "temperature"
    assert attrs("sensor", "temp")["state_class"] == "measurement"
    assert attrs("sensor", "energy")["device_class"] == "energy"
    assert "state_class" not in attrs("sensor", "energy")
    assert "device_class" not in attrs("sensor", "typo")
    assert attrs("sensor", "typo")["state_class"] == "measurement"
    assert attrs("binary_sensor", "win")["device_class"] == "window"
    assert "device_class" not in attrs("binary_sensor", "badwin")

    # The suggestions reach the panel and are all valid HA device classes
    await client.send_json_auto_id({"type": "fbd_logic/blocks"})
    res = await client.receive_json()
    param = next(
        p for b in res["result"]["blocks"] if b["type"] == "publish" for p in b["params"] if p["name"] == "device_class"
    )
    from homeassistant.components.binary_sensor import BinarySensorDeviceClass
    from homeassistant.components.sensor import SensorDeviceClass

    valid = {c.value for c in SensorDeviceClass} | {c.value for c in BinarySensorDeviceClass}
    assert param["suggest"] and all(s["value"] in valid for s in param["suggest"])


async def test_invalid_program_rejected(hass: HomeAssistant, hass_ws_client) -> None:
    await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "fbd_logic/program/save", "program": {"nodes": []}})
    res = await client.receive_json()
    assert not res["success"]
    assert res["error"]["code"] == "invalid_format"


async def test_state_survives_reload(hass: HomeAssistant, hass_ws_client) -> None:
    hass.states.async_set("binary_sensor.door", "on")
    entry = await _setup(hass)
    client = await hass_ws_client(hass)
    prog = {
        "id": "latch",
        "name": "Lås",
        "nodes": [
            {"id": "door", "type": "entity_in", "params": {"entity_id": "binary_sensor.door"}},
            {"id": "sr", "type": "sr", "x": 200},
            {"id": "sp", "type": "setpoint", "y": 200, "params": {"name": "Grense", "initial": 5}},
            {"id": "pub", "type": "publish", "x": 400, "params": {"name": "Alarm"}},
        ],
        "links": [
            {"id": "a", "from": "door", "from_port": "on", "to": "sr", "to_port": "s"},
            {"id": "b", "from": "sr", "from_port": "q", "to": "pub", "to_port": "value"},
        ],
    }
    await client.send_json_auto_id({"type": "fbd_logic/program/save", "program": prog})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    ent_reg = er.async_get(hass)
    sp_id = ent_reg.async_get_entity_id("number", DOMAIN, "latch_sp")
    alarm_id = ent_reg.async_get_entity_id("binary_sensor", DOMAIN, "latch_pub")
    await hass.services.async_call("number", "set_value", {"entity_id": sp_id, "value": 7}, blocking=True)
    assert hass.states.get(alarm_id).state == "on"

    hass.states.async_set("binary_sensor.door", "off")
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    # Latch retained over reload, setpoint value kept
    assert hass.states.get(alarm_id).state == "on"
    assert hass.states.get(sp_id).state == "7.0"


async def test_service_resolution(hass: HomeAssistant) -> None:
    await _setup(hass)
    for domain, service in [
        ("cover", "set_cover_position"),
        ("cover", "open_cover"),
        ("climate", "set_temperature"),
        ("light", "turn_on"),
        ("switch", "turn_off"),
        ("button", "press"),
        ("select", "select_option"),
    ]:
        async_mock_service(hass, domain, service)
    io = hass.data[DOMAIN].io
    assert io.resolve("cover.x", "auto", 40.0, {})[1] == "set_cover_position"
    assert io.resolve("cover.x", "auto", True, {})[1] == "open_cover"
    assert io.resolve("climate.x", "auto", 21.5, {}) == ("climate", "set_temperature", {"entity_id": "climate.x", "temperature": 21.5})
    assert io.resolve("light.x", "auto", 0.0, {})[1] == "turn_off"
    assert io.resolve("light.x", "auto", 55.0, {})[2]["brightness_pct"] == 55.0
    assert io.resolve("switch.x", "auto", False, {})[:2] == ("switch", "turn_off")
    assert io.resolve("button.x", "auto", True, {})[1] == "press"
    assert io.resolve("select.x", "auto", "eco", {})[2]["option"] == "eco"
    assert io.resolve("knx.x", "custom", 3.0, {"service": "knx.send", "data_key": "payload"}) == (
        "knx",
        "send",
        {"entity_id": "knx.x", "payload": 3.0},
    )


async def test_write_error_reported(hass: HomeAssistant, hass_ws_client) -> None:
    await _setup(hass)
    client = await hass_ws_client(hass)
    prog = {
        "id": "err",
        "name": "Feil",
        "nodes": [
            {"id": "k", "type": "const_bool", "params": {"value": True}},
            {"id": "o", "type": "entity_out", "x": 200, "params": {"entity_id": "nosuch.thing"}},
        ],
        "links": [{"id": "a", "from": "k", "from_port": "q", "to": "o", "to_port": "value"}],
    }
    await client.send_json_auto_id({"type": "fbd_logic/program/save", "program": prog})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    snap = hass.data[DOMAIN].snapshot("err")
    assert "finnes ikke" in snap["nodes"]["o"]["e"]
