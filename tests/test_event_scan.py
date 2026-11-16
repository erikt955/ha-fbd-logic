"""Event scans: a program reacts to an input change at once, without waiting for its cyclic scan."""

import asyncio
from datetime import timedelta

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.fbd_logic.const import DOMAIN, EVENT_SCAN_MIN_GAP, SUBSCRIBE_MIN_PERIOD


async def _setup(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="FBD Logic", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _ws(client, msg):
    await client.send_json_auto_id(msg)
    res = await client.receive_json()
    while res.get("type") == "event":
        res = await client.receive_json()
    return res


async def _settle(hass: HomeAssistant) -> None:
    """Let a queued (rate-limited) event scan run."""
    await asyncio.sleep(EVENT_SCAN_MIN_GAP * 3)
    await hass.async_block_till_done()


def _program(event_scan: bool = True) -> dict:
    return {
        "id": "ev",
        "name": "Hendelse",
        "interval": 60,  # the cyclic scan is far away: any quick reaction is an event scan
        "event_scan": event_scan,
        "nodes": [
            {"id": "in", "type": "entity_in", "params": {"entity_id": "sensor.t"}},
            {"id": "sp", "type": "setpoint", "y": 120, "params": {"name": "Grense", "initial": 25}},
            {"id": "gt", "type": "gt", "x": 200},
            {"id": "out", "type": "entity_out", "x": 400, "params": {"entity_id": "light.l"}},
            {"id": "rd", "type": "knx_read", "y": 240, "params": {"address": "1/1/1", "dpt": "9.001"}},
            {"id": "pub", "type": "publish", "x": 400, "y": 240, "params": {"name": "KNX"}},
        ],
        "links": [
            {"id": "1", "from": "in", "from_port": "value", "to": "gt", "to_port": "a"},
            {"id": "2", "from": "sp", "from_port": "value", "to": "gt", "to_port": "b"},
            {"id": "3", "from": "gt", "from_port": "q", "to": "out", "to_port": "value"},
            {"id": "4", "from": "rd", "from_port": "value", "to": "pub", "to_port": "value"},
        ],
    }


async def test_event_scan(hass: HomeAssistant, hass_ws_client) -> None:
    hass.states.async_set("sensor.t", "20")
    on = async_mock_service(hass, "light", "turn_on")
    off = async_mock_service(hass, "light", "turn_off")
    async_mock_service(hass, "knx", "event_register")
    async_mock_service(hass, "knx", "read")
    await _setup(hass)
    client = await hass_ws_client(hass)
    assert (await _ws(client, {"type": "fbd_logic/program/save", "program": _program()}))["success"]
    await hass.async_block_till_done()
    mgr = hass.data[DOMAIN]
    assert len(off) == 1 and not on  # first scan on save: 20 > 25 is false

    # An entity change scans at once
    hass.states.async_set("sensor.t", "30")
    await _settle(hass)
    assert len(on) == 1
    assert mgr.runtime["ev"].event_count == 1

    # Changes in a burst give one scan, with the newest value
    hass.states.async_set("sensor.t", "10")
    hass.states.async_set("sensor.t", "12")
    await _settle(hass)
    assert len(off) == 2
    assert mgr.runtime["ev"].event_count == 2

    # A setpoint changed from HA scans at once
    sp_id = er.async_get(hass).async_get_entity_id("number", DOMAIN, "ev_sp")
    await hass.services.async_call("number", "set_value", {"entity_id": sp_id, "value": 5}, blocking=True)
    await _settle(hass)
    assert len(on) == 2  # 12 > 5
    assert mgr.runtime["ev"].event_count == 3

    # A KNX telegram on a listened address scans at once
    hass.bus.async_fire(
        "knx_event",
        {"destination": "1/1/1", "telegramtype": "GroupValueWrite", "value": 21.5, "direction": "Incoming"},
    )
    await _settle(hass)
    pub_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "ev_pub")
    assert float(hass.states.get(pub_id).state) == 21.5
    assert mgr.runtime["ev"].event_count == 4

    # The snapshot reports event scans to the panel
    assert mgr.snapshot("ev")["events"] == 4

    # The panel gets the result of an event scan that falls inside its update throttle
    snaps = []
    unsub = mgr.subscribe("ev", snaps.append)
    hass.states.async_set("sensor.t", "40")
    await _settle(hass)  # pushed at once
    hass.states.async_set("sensor.t", "41")
    await _settle(hass)  # inside the throttle window: pushed a little later, not at the next cyclic scan
    await asyncio.sleep(SUBSCRIBE_MIN_PERIOD)
    await hass.async_block_till_done()
    assert snaps[-1]["nodes"]["in"]["o"]["value"] == 41
    unsub()

    # Switched off: only the cyclic scan sees the change
    assert (await _ws(client, {"type": "fbd_logic/program/save", "program": _program(event_scan=False)}))["success"]
    await hass.async_block_till_done()
    assert "ev" not in mgr._watchers and not mgr._knx_watch
    hass.states.async_set("sensor.t", "1")
    await _settle(hass)
    assert len(off) == 2 and mgr.runtime["ev"].event_count == 0
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done()
    assert len(off) == 3

    # Deleting the program removes its listeners
    assert (await _ws(client, {"type": "fbd_logic/program/save", "program": _program()}))["success"]
    await hass.async_block_till_done()
    assert "ev" in mgr._watchers and mgr._knx_watch == {"1/1/1": {"ev"}}
    assert (await _ws(client, {"type": "fbd_logic/program/delete", "program_id": "ev"}))["success"]
    assert not mgr._watchers and not mgr._knx_watch and not mgr._pending and not mgr._push_pending


async def test_event_scan_feedback_loop_is_rate_limited(hass: HomeAssistant, hass_ws_client) -> None:
    """A program that inverts its own input oscillates, but no faster than the minimum gap."""
    hass.states.async_set("input_boolean.x", "off")
    await _setup(hass)
    client = await hass_ws_client(hass)

    async def _toggle(call):
        cur = hass.states.get("input_boolean.x").state
        hass.states.async_set("input_boolean.x", "off" if cur == "on" else "on")

    hass.services.async_register("input_boolean", "turn_on", _toggle)
    hass.services.async_register("input_boolean", "turn_off", _toggle)
    prog = {
        "id": "loop",
        "name": "Sløyfe",
        "interval": 60,
        "nodes": [
            {"id": "in", "type": "entity_in", "params": {"entity_id": "input_boolean.x"}},
            {"id": "not", "type": "not", "x": 200},
            {"id": "out", "type": "entity_out", "x": 400, "params": {"entity_id": "input_boolean.x"}},
        ],
        "links": [
            {"id": "1", "from": "in", "from_port": "on", "to": "not", "to_port": "in"},
            {"id": "2", "from": "not", "from_port": "q", "to": "out", "to_port": "value"},
        ],
    }
    assert (await _ws(client, {"type": "fbd_logic/program/save", "program": prog}))["success"]
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()
    count = hass.data[DOMAIN].runtime["loop"].event_count
    # 0.2 s at one scan per 20 ms at most is about 10; allow for timer slack
    assert 3 <= count <= 0.2 / EVENT_SCAN_MIN_GAP + 2, count
    assert (await _ws(client, {"type": "fbd_logic/program/delete", "program_id": "loop"}))["success"]
