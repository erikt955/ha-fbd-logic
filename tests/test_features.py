"""Tests for the 0.2 features: MUX/PRIO, schedule, connectors, macros, forcing, KNX/Modbus."""

from datetime import datetime

import pytest

from custom_components.fbd_logic.blocks import (
    LIBRARY,
    library_json,
    macro_blockdef,
    modbus_registers,
    parse_periods,
    schedule_active,
)
from custom_components.fbd_logic.engine import Program


class FakeIO:
    def __init__(self):
        self.states = {}
        self.writes = []
        self.calls = []
        self.values = {}
        self.published = {}
        self.knx = {}
        self.listening = []
        self.knx_ok = True

    def read(self, entity_id, attribute):
        st = self.states.get(entity_id)
        return None if st is None else st

    def write(self, program_id, node_id, entity_id, action, value, params):
        self.writes.append((entity_id, action, value))

    def get_value(self, program_id, node_id, default):
        return self.values.get(node_id, default)

    def publish(self, program_id, node_id, value):
        self.published[node_id] = value

    def call(self, program_id, node_id, domain, service, data):
        self.calls.append((domain, service, data))

    def knx_listen(self, address, dpt, read):
        self.listening.append((address, dpt, read))
        return self.knx_ok

    def knx_value(self, address):
        return self.knx.get(address)

    def location(self):
        return (59.91, 10.75)


def n(id_, type_, x=0, y=0, params=None, consts=None, **kw):
    d = {"id": id_, "type": type_, "x": x, "y": y, "params": params or {}, "consts": consts or {}}
    d.update(kw)
    return d


def links(*items):
    return [
        {"id": f"l{i}", "from": a, "from_port": ap, "to": b, "to_port": bp}
        for i, (a, ap, b, bp) in enumerate(items)
    ]


def prog(nodes, lnks=(), io=None, macros=None, **kw):
    data = {"id": "p1", "name": "Test", "nodes": list(nodes), "links": links(*lnks)}
    data.update(kw)
    return Program(data, io=io or FakeIO(), macros=macros)


# ---------------------------------------------------------------- selectors
def test_mux_index_and_port_order():
    p = prog([n("m", "mux", params={"n": 4}, consts={"in0": 10, "in1": 11, "in2": 12, "in3": 13, "k": 2})])
    assert [x.name for x in p.nodes["m"].inputs] == ["k", "in0", "in1", "in2", "in3"]
    p.step(0)
    assert p.nodes["m"].outputs == {"out": 12, "err": False}
    p.nodes["m"].consts["k"] = 9
    p.step(1)
    assert p.nodes["m"].outputs == {"out": 13, "err": True}


def test_prio_selector():
    p = prog([n("p", "prio", params={"n": 3}, consts={"in1": 1, "in2": 2, "in3": 3, "else": 99, "g2": True, "g3": True})])
    assert [x.name for x in p.nodes["p"].inputs] == ["g1", "in1", "g2", "in2", "g3", "in3", "else"]
    p.step(0)
    assert p.nodes["p"].outputs == {"out": 2, "idx": 2.0}
    p.nodes["p"].consts.update({"g2": False, "g3": False})
    p.step(1)
    assert p.nodes["p"].outputs == {"out": 99, "idx": 0.0}


def test_bit_get():
    p = prog([n("b", "bit_get", consts={"in": 0b1010, "bit": 3}), n("c", "bit_get", y=50, consts={"in": 0b1010, "bit": 2})])
    p.step(0)
    assert p.nodes["b"].outputs["q"] is True
    assert p.nodes["c"].outputs["q"] is False


def test_dynamic_json_and_hidden_ports():
    blocks = {b["type"]: b for b in library_json()["blocks"]}
    assert blocks["mux"]["dynamic"]["after"] is True
    assert blocks["page_in"]["inputs"] == []  # hidden input not exposed to the editor
    assert blocks["page_out"]["outputs"] == []
    assert {"knx_send", "knx_read", "modbus_write", "schedule", "mux", "prio"} <= set(blocks)


# ---------------------------------------------------------------- schedule
def test_schedule_periods_and_midnight_wrap():
    periods = parse_periods(
        [
            {"days": [1, 2, 3, 4, 5], "on": "07:00", "off": "16:00"},
            {"days": [5], "on": "22:00", "off": "02:00"},
            {"days": [9], "on": "x", "off": "y"},  # ignored
        ]
    )
    assert len(periods) == 2
    assert schedule_active(periods, 1, 7 * 60)
    assert not schedule_active(periods, 1, 16 * 60)
    assert schedule_active(periods, 5, 23 * 60)  # Friday night
    assert schedule_active(periods, 6, 60)  # continues into Saturday
    assert not schedule_active(periods, 6, 3 * 60)


def test_schedule_block_outputs():
    p = prog(
        [
            n(
                "s",
                "schedule",
                params={"periods": [{"days": [1, 2, 3, 4, 5], "on": "07:00", "off": "16:00"}], "on_value": 21, "off_value": 18},
            )
        ]
    )
    # Monday 2026-11-16 06:30:00 -> off, 30 minutes to start
    p.step(0, datetime(2026, 11, 16, 6, 30, 0))
    out = p.nodes["s"].outputs
    assert out["q"] is False and out["value"] == 18 and out["next"] == pytest.approx(30)
    p.step(1, datetime(2026, 11, 16, 7, 0, 30))
    out = p.nodes["s"].outputs
    assert out["q"] is True and out["value"] == 21 and out["next"] == pytest.approx(9 * 60 - 0.5)
    # Friday 16:00 -> next start is Monday 07:00
    p.step(2, datetime(2026, 11, 20, 16, 0, 0))
    assert p.nodes["s"].outputs["next"] == pytest.approx((2 * 24 + 15) * 60)
    # en = off (holiday) forces q off
    p.nodes["s"].consts["en"] = False
    p.step(3, datetime(2026, 11, 16, 9, 0, 0))
    assert p.nodes["s"].outputs["q"] is False


# ---------------------------------------------------------------- connectors / pages
def test_page_connectors_across_pages():
    p = prog(
        [
            n("k", "const_num", params={"value": 7}, page="a"),
            n("tx", "page_out", x=100, params={"name": "temp"}, page="a"),
            n("rx", "page_in", x=0, params={"name": "temp"}, page="b"),
            n("add", "add", x=100, consts={"in2": 1}, page="b"),
            n("orphan", "page_in", y=200, params={"name": "nope"}, page="b"),
        ],
        [("k", "out", "tx", "value"), ("rx", "value", "add", "in1")],
        pages=[{"id": "a", "name": "Side 1"}, {"id": "b", "name": "Side 2"}],
    )
    assert p.nodes["tx"].order < p.nodes["rx"].order < p.nodes["add"].order
    p.step(0)
    assert p.nodes["add"].outputs["out"] == 8
    assert p.nodes["orphan"].error and "nope" in p.nodes["orphan"].error
    snap = p.snapshot()
    assert snap["nodes"]["tx"]["i"]["value"] == 7
    assert any("nope" in w for w in p.warnings)


# ---------------------------------------------------------------- macros
HYST_MACRO = {
    "id": "m1",
    "name": "Termostat",
    "symbol": "TERM",
    "nodes": [
        n("pv", "macro_in", y=0, params={"name": "pv", "type": "num", "default": "0"}),
        n("sp", "macro_in", y=50, params={"name": "sp", "type": "num", "default": "21"}),
        n("lt", "lt", x=150),
        n("sr", "sr", x=300),
        n("q", "macro_out", x=450, params={"name": "varme", "type": "bool"}),
        n("sp_ha", "setpoint", x=0, y=200, params={"name": "Grense"}),
    ],
    "links": links(("pv", "value", "lt", "a"), ("sp", "value", "lt", "b"), ("lt", "q", "sr", "s"), ("sr", "q", "q", "value")),
}


def test_macro_blockdef_pins():
    bdef = macro_blockdef(HYST_MACRO)
    assert bdef.type == "macro:m1"
    assert [p.name for p in bdef.inputs] == ["pv", "sp"]
    assert bdef.inputs[1].default == 21
    assert [(p.name, p.type) for p in bdef.outputs] == [("varme", "bool")]
    blocks = {b["type"]: b for b in library_json({"m1": HYST_MACRO})["blocks"]}
    assert blocks["macro:m1"]["category"] == "macro"


def test_macro_instance_runs_and_mirrors_outputs():
    io = FakeIO()
    p = prog(
        [
            n("k", "const_num", params={"value": 18}),
            n("t1", "macro:m1", x=200, label="Stue"),
            n("t2", "macro:m1", x=200, y=200, consts={"sp": 10}),
            n("pub", "publish", x=400, params={"name": "Varme"}),
        ],
        [("k", "out", "t1", "pv"), ("k", "out", "t2", "pv"), ("t1", "varme", "pub", "value")],
        io=io,
        macros={"m1": HYST_MACRO},
    )
    assert not p.warnings, p.warnings
    assert "t1/lt" in p.nodes and "t2/sr" in p.nodes
    assert p.nodes["t1"].bdef.fn is None
    p.step(0)
    assert p.nodes["t1"].outputs["varme"] is True  # 18 < 21 (default sp)
    assert p.nodes["t2"].outputs["varme"] is False  # 18 < 10 is false
    assert io.published["pub"] is True
    # setpoint inside a macro gets its own entity, named after the instance
    specs = {s["node_id"]: s for s in p.ha_entities()}
    assert specs["t1/sp_ha"]["name"] == "Stue Grense"
    assert specs["t2/sp_ha"]["name"] == "Termostat Grense"
    # SR latch state inside the macro is retained by full id
    assert "t1/sr" in p.retained_state()


def test_macro_nested_and_recursion_guard():
    outer = {
        "id": "m2",
        "name": "Dobbel",
        "nodes": [
            n("i", "macro_in", params={"name": "x"}),
            n("a", "macro:m1", x=100),
            n("o", "macro_out", x=300, params={"name": "y", "type": "bool"}),
        ],
        "links": links(("i", "value", "a", "pv"), ("a", "varme", "o", "value")),
    }
    loop = {"id": "m3", "name": "Loop", "nodes": [n("x", "macro:m3")], "links": []}
    macros = {"m1": HYST_MACRO, "m2": outer, "m3": loop}
    p = prog([n("d", "macro:m2", consts={"x": 30}), n("l", "macro:m3", y=100)], macros=macros)
    assert "d/a/lt" in p.nodes
    p.step(0)
    assert p.nodes["d"].outputs["y"] is False  # 30 < 21 is false
    assert any("i seg selv" in w for w in p.warnings)


def test_macro_online_change_keeps_inner_state():
    macros = {"m1": HYST_MACRO}
    nodes = [n("t", "macro:m1", consts={"pv": 10})]
    p = prog(nodes, macros=macros)
    p.step(0)
    assert p.nodes["t/sr"].outputs["q"] is True
    data = dict(p.data)
    data["nodes"] = [n("t", "macro:m1", consts={"pv": 30})]
    p2 = Program(data, io=FakeIO(), previous=p, macros=macros)
    p2.step(1)
    assert p2.nodes["t"].outputs["varme"] is True  # latch kept


def test_unknown_macro_is_warning():
    p = prog([n("x", "macro:missing")])
    assert any("missing" in w for w in p.warnings)


# ---------------------------------------------------------------- forcing
def test_force_output_overrides_block_and_downstream():
    io = FakeIO()
    io.states["sensor.t"] = "20"
    p = prog(
        [
            n("in", "entity_in", params={"entity_id": "sensor.t"}),
            n("gt", "gt", x=100, consts={"b": 25}),
        ],
        [("in", "value", "gt", "a")],
        io=io,
    )
    p.step(0)
    assert p.nodes["gt"].outputs["q"] is False
    p.set_forces({"in": {"value": "30"}, "gt": {"nope": 1}, "missing": {"q": True}})
    assert p.forces == {"in": {"value": 30.0}}
    p.step(1)
    assert p.nodes["in"].outputs["value"] == 30.0
    assert p.nodes["gt"].outputs["q"] is True
    assert p.snapshot()["nodes"]["in"]["f"] == {"value": 30.0}
    p.set_forces({})
    p.step(2)
    assert p.nodes["gt"].outputs["q"] is False


def test_force_macro_output_redirects_to_inner_pin():
    p = prog(
        [n("t", "macro:m1", consts={"pv": 30}), n("not", "not", x=200)],
        [("t", "varme", "not", "in")],
        macros={"m1": HYST_MACRO},
        forces=None,
    )
    p.set_forces({"t": {"varme": True}})
    p.step(0)
    assert p.nodes["t"].outputs["varme"] is True
    assert p.nodes["not"].outputs["q"] is False


# ---------------------------------------------------------------- KNX / Modbus
def test_knx_send_payloads_and_change_only():
    io = FakeIO()
    p = prog(
        [
            n("sw", "knx_send", params={"address": "1/1/1", "dpt": "1.001"}, consts={"value": True}),
            n("pct", "knx_send", y=100, params={"address": "1/1/2", "dpt": "5.001", "deadband": 2}, consts={"value": 42.4}),
            n("t", "knx_send", y=200, params={"address": "1/1/3", "dpt": "9.001", "cyclic": 10}, consts={"value": 21.5}),
            n("none", "knx_send", y=300, params={"address": ""}),
        ],
        io=io,
    )
    p.step(0)
    assert ("knx", "send", {"address": "1/1/1", "payload": 1}) in io.calls
    assert ("knx", "send", {"address": "1/1/2", "payload": 42, "type": "5.001"}) in io.calls
    assert ("knx", "send", {"address": "1/1/3", "payload": 21.5, "type": "9.001"}) in io.calls
    assert len(io.calls) == 3
    p.nodes["pct"].consts["value"] = 43.0  # inside deadband
    p.step(1)
    assert len(io.calls) == 3
    p.step(11)  # cyclic resend of the temperature
    assert len(io.calls) == 4 and io.calls[-1][2]["address"] == "1/1/3"


def test_knx_read_listens_and_pulses():
    io = FakeIO()
    p = prog([n("r", "knx_read", params={"address": "2/2/2", "dpt": "9.001"})], io=io)
    p.step(0)
    assert io.listening == [("2/2/2", "9.001", True)]
    assert p.nodes["r"].outputs["valid"] is False
    io.knx["2/2/2"] = (21.3, 1)
    p.step(1)
    assert p.nodes["r"].outputs == {"value": 21.3, "on": True, "valid": True, "new": True}
    p.step(2)
    assert p.nodes["r"].outputs["new"] is False
    assert len(io.listening) == 1
    io.knx_ok = False
    p2 = prog([n("r", "knx_read", params={"address": "2/2/3"})], io=io)
    p2.step(0)
    assert "KNX" in p2.nodes["r"].error


def test_modbus_encoding_and_write():
    assert modbus_registers(-1, "int16", "big") == 0xFFFF
    assert modbus_registers(70000, "uint16", "big") == 65535
    assert modbus_registers(1.0, "float32", "big") == [0x3F80, 0x0000]
    assert modbus_registers(1.0, "float32", "little") == [0x0000, 0x3F80]
    assert modbus_registers(65536 + 5, "uint32", "big") == [1, 5]
    io = FakeIO()
    p = prog(
        [
            n("r", "modbus_write", params={"hub": "hub1", "slave": 3, "address": 100, "scale": 10}, consts={"value": 21.5}),
            n("c", "modbus_write", y=100, params={"hub": "hub1", "address": 5, "kind": "coil"}, consts={"value": True}),
        ],
        io=io,
    )
    p.step(0)
    assert ("modbus", "write_register", {"hub": "hub1", "slave": 3, "address": 100, "value": 215}) in io.calls
    assert ("modbus", "write_coil", {"hub": "hub1", "slave": 1, "address": 5, "state": True}) in io.calls


def test_all_blocks_survive_default_scan():
    """Every block type runs one scan with defaults without raising."""
    nodes = [n(f"b{i}", t, y=i * 60) for i, t in enumerate(LIBRARY) if t not in ("page_in", "knx_read")]
    p = prog(nodes)
    p.step(0, datetime(2026, 11, 16, 12, 0))
    errors = {nid: node.error for nid, node in p.nodes.items() if node.error}
    assert not errors, errors
