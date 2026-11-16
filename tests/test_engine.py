"""Unit tests for the block library and the cyclic engine (no HA needed)."""

from datetime import datetime

import pytest

from custom_components.fbd_logic.blocks import LIBRARY, library_json, to_bool, to_num
from custom_components.fbd_logic.engine import Program
from custom_components.fbd_logic.expr import ExpressionError, compile_expression


class FakeIO:
    def __init__(self):
        self.states = {}
        self.writes = []
        self.values = {}
        self.published = {}

    def read(self, entity_id, attribute):
        st = self.states.get(entity_id)
        if st is None:
            return None
        if attribute:
            return st[1].get(attribute)
        return st[0]

    def write(self, program_id, node_id, entity_id, action, value, params):
        self.writes.append((entity_id, action, value))

    def get_value(self, program_id, node_id, default):
        return self.values.get(node_id, default)

    def publish(self, program_id, node_id, value):
        self.published[node_id] = value


def prog(nodes, links=(), io=None, **kw):
    data = {"id": "p1", "name": "Test", "nodes": list(nodes), "links": [
        {"id": f"l{i}", "from": a, "from_port": ap, "to": b, "to_port": bp}
        for i, (a, ap, b, bp) in enumerate(links)
    ]}
    data.update(kw)
    return Program(data, io=io or FakeIO())


def n(id_, type_, x=0, y=0, params=None, consts=None):
    return {"id": id_, "type": type_, "x": x, "y": y, "params": params or {}, "consts": consts or {}}


# ---------------------------------------------------------------- coercion
def test_coercion():
    assert to_bool("on") and to_bool("heat") and to_bool("1") and to_bool(2.0)
    assert not to_bool("off") and not to_bool("0") and not to_bool("unavailable")
    assert to_num("21,5") == 21.5
    assert to_num(True) == 1.0
    assert to_num("on") == 1.0
    assert to_num("abc") == 0.0


def test_library_serialises():
    data = library_json()
    assert len(data["blocks"]) == len(LIBRARY) >= 40
    types = {b["type"] for b in data["blocks"]}
    assert {"and", "pid", "ton", "entity_in", "entity_out", "formula"} <= types


# ---------------------------------------------------------------- logic
def test_and_or_dynamic_inputs():
    p = prog(
        [
            n("a", "const_bool", params={"value": True}),
            n("b", "const_bool", params={"value": False}),
            n("and", "and", x=100, params={"n": 3}),
            n("or", "or", x=100, params={"n": 2}),
        ],
        [("a", "q", "and", "in1"), ("b", "q", "and", "in2"), ("a", "q", "or", "in1"), ("b", "q", "or", "in2")],
    )
    assert [port.name for port in p.nodes["and"].inputs] == ["in1", "in2", "in3"]
    p.step(0)
    assert p.nodes["and"].outputs["q"] is False
    assert p.nodes["or"].outputs["q"] is True


def test_sr_latch_and_retained_state():
    p = prog([n("sr", "sr", consts={"s": True})])
    p.step(0)
    assert p.nodes["sr"].outputs["q"] is True
    retained = p.retained_state()
    assert retained == {"sr": {"type": "sr", "s": {"q": True}}}
    p2 = Program(
        {"id": "p1", "nodes": [n("sr", "sr")], "links": []}, io=FakeIO(), retained=retained
    )
    p2.step(0)
    assert p2.nodes["sr"].outputs["q"] is True


def test_rs_reset_dominant():
    p = prog([n("rs", "rs", consts={"s": True, "r": True})])
    p.step(0)
    assert p.nodes["rs"].outputs["q"] is False


def test_r_trig_no_pulse_on_first_scan():
    io = FakeIO()
    io.states["binary_sensor.x"] = ("on", {})
    p = prog(
        [n("in", "entity_in", params={"entity_id": "binary_sensor.x"}), n("rt", "r_trig", x=100)],
        [("in", "on", "rt", "in")],
        io=io,
    )
    p.step(0)
    assert p.nodes["rt"].outputs["q"] is False
    io.states["binary_sensor.x"] = ("off", {})
    p.step(1)
    io.states["binary_sensor.x"] = ("on", {})
    p.step(2)
    assert p.nodes["rt"].outputs["q"] is True
    p.step(3)
    assert p.nodes["rt"].outputs["q"] is False


# ---------------------------------------------------------------- timers
def test_ton():
    io = FakeIO()
    io.states["binary_sensor.x"] = ("on", {})
    p = prog(
        [n("in", "entity_in", params={"entity_id": "binary_sensor.x"}), n("t", "ton", x=100, consts={"pt": 3})],
        [("in", "on", "t", "in")],
        io=io,
    )
    for t in range(3):
        p.step(t)
        assert p.nodes["t"].outputs["q"] is False
    p.step(3)
    assert p.nodes["t"].outputs["q"] is True
    io.states["binary_sensor.x"] = ("off", {})
    p.step(4)
    assert p.nodes["t"].outputs["q"] is False


def test_tof():
    io = FakeIO()
    io.states["binary_sensor.x"] = ("on", {})
    p = prog(
        [n("in", "entity_in", params={"entity_id": "binary_sensor.x"}), n("t", "tof", x=100, consts={"pt": 2})],
        [("in", "on", "t", "in")],
        io=io,
    )
    p.step(0)
    assert p.nodes["t"].outputs["q"] is True
    io.states["binary_sensor.x"] = ("off", {})
    p.step(1)
    assert p.nodes["t"].outputs["q"] is True
    p.step(2)
    assert p.nodes["t"].outputs["q"] is True
    p.step(3)
    assert p.nodes["t"].outputs["q"] is False


def test_tp_and_blink():
    io = FakeIO()
    io.states["input_boolean.x"] = ("off", {})
    p = prog(
        [
            n("in", "entity_in", params={"entity_id": "input_boolean.x"}),
            n("tp", "tp", x=100, consts={"pt": 2}),
            n("bl", "blink", x=100, y=100, consts={"t_on": 1, "t_off": 1}),
        ],
        [("in", "on", "tp", "in")],
        io=io,
    )
    p.step(0)
    io.states["input_boolean.x"] = ("on", {})
    p.step(1)
    assert p.nodes["tp"].outputs["q"] is True
    io.states["input_boolean.x"] = ("off", {})
    p.step(2)
    assert p.nodes["tp"].outputs["q"] is True
    p.step(3)
    assert p.nodes["tp"].outputs["q"] is False
    blink = []
    for t in (4, 4.5, 5, 5.5, 6):
        p.step(t)
        blink.append(p.nodes["bl"].outputs["q"])
    assert blink == [False, False, True, True, False] or blink.count(True) >= 2


def test_runtime_counter_clock():
    p = prog(
        [
            n("rt", "runtime", consts={"in": True}),
            n("ct", "counter"),
            n("ck", "clock"),
        ]
    )
    p.step(0, datetime(2026, 11, 14, 13, 45))
    p.step(3600, datetime(2026, 11, 14, 14, 45))
    assert p.nodes["rt"].outputs["hours"] == pytest.approx(1.0)
    assert p.nodes["ck"].outputs["hour"] == 14
    assert p.nodes["ck"].outputs["weekend"] is True
    assert p.nodes["ck"].outputs["daymin"] == 14 * 60 + 45


# ---------------------------------------------------------------- math / compare
def test_math_and_compare():
    p = prog(
        [
            n("k1", "const_num", params={"value": 10}),
            n("k2", "const_num", params={"value": 4}),
            n("sub", "sub", x=100),
            n("div", "div", x=100, y=80, consts={"b": 0}),
            n("sc", "scale", x=200, consts={"in_hi": 10, "out_hi": 100}),
            n("gt", "gt", x=300, consts={"b": 50}),
            n("lim", "limit", x=200, y=200, consts={"in": 150}),
            n("hy", "hyst", x=200, y=300, consts={"in": 21}),
        ],
        [
            ("k1", "out", "sub", "a"),
            ("k2", "out", "sub", "b"),
            ("k1", "out", "div", "a"),
            ("sub", "out", "sc", "in"),
            ("sc", "out", "gt", "a"),
        ],
    )
    p.step(0)
    assert p.nodes["sub"].outputs["out"] == 6
    assert p.nodes["div"].outputs == {"out": 0.0, "err": True}
    assert p.nodes["sc"].outputs["out"] == 60
    assert p.nodes["gt"].outputs["q"] is True
    assert p.nodes["lim"].outputs["out"] == 100
    assert p.nodes["hy"].outputs["q"] is False


def test_formula_and_errors():
    p = prog(
        [
            n("k", "const_num", params={"value": 25}),
            n("f", "formula", x=100, params={"expr": "sel(a > 20, a * 2, 0) + b", "n": 2}, consts={"b": 1}),
            n("bad", "formula", y=100, params={"expr": "__import__('os')"}),
        ],
        [("k", "out", "f", "a")],
    )
    p.step(0)
    assert p.nodes["f"].outputs["out"] == 51
    assert p.nodes["f"].error is None
    assert p.nodes["bad"].error
    with pytest.raises(ExpressionError):
        compile_expression("a.__class__", ["a"])
    assert compile_expression("max(a, 3) ** 2", ["a"])({"a": 1}) == 9


# ---------------------------------------------------------------- control
def test_pid_reverse_converges_and_antiwindup():
    p = prog([n("pid", "pid", consts={"pv": 18, "sp": 21, "kp": 10, "ti": 10, "min": 0, "max": 100})])
    for t in range(100):
        p.step(t)
    out = p.nodes["pid"].outputs["out"]
    assert out == 100  # saturated
    assert p.nodes["pid"].state["i"] <= 100  # no windup beyond max
    # Disable -> output to min, and the integral tracks it (bumpless restart from min)
    p.nodes["pid"].consts["en"] = False
    p.step(101)
    assert p.nodes["pid"].outputs["out"] == 0
    assert p.nodes["pid"].outputs["auto"] is False
    assert p.nodes["pid"].state["i"] == -30  # 0 - P (10 * 3)


def test_pid_direct():
    p = prog([n("pid", "pid", params={"direction": "direct"}, consts={"pv": 26, "sp": 24, "kp": 5, "ti": 0})])
    p.step(0)
    assert p.nodes["pid"].outputs["out"] == 10


def test_pid_manual_and_bumpless_transfer():
    p = prog([n("pid", "pid", consts={"pv": 20, "sp": 21, "kp": 10, "ti": 100, "min": 0, "max": 100})])
    for t in range(11):
        p.step(t)
    node = p.nodes["pid"]
    assert node.outputs["out"] == pytest.approx(11)  # P 10 + I 10 s * 0.1/s
    assert node.outputs["auto"] is True

    # Manual: the output follows the manual value, limited to min/max
    node.consts.update(man=True, mv=40)
    p.step(11)
    assert node.outputs["out"] == 40 and node.outputs["auto"] is False
    node.consts["mv"] = 150
    p.step(12)
    assert node.outputs["out"] == 100
    node.consts["mv"] = 40
    p.step(13)

    # Back to automatic: continues from 40 (plus one second of integration), no step back to 11
    node.consts["man"] = False
    p.step(14)
    assert node.outputs["out"] == pytest.approx(40.1)

    # Off and on again: starts from min instead of jumping to the P term
    node.consts["en"] = False
    p.step(15)
    assert node.outputs["out"] == 0
    node.consts["en"] = True
    p.step(16)
    assert node.outputs["out"] == pytest.approx(0.1)
    for t in range(17, 27):
        p.step(t)
    assert node.outputs["out"] == pytest.approx(1.1)  # then integrates as usual


def test_pid_bias_and_deadband():
    # P only with a working point: 50 % at zero error
    p = prog([n("pid", "pid", consts={"pv": 21, "sp": 21, "kp": 10, "ti": 0, "bias": 50})])
    node = p.nodes["pid"]
    p.step(0)
    assert node.outputs["out"] == 50
    node.consts["pv"] = 20
    p.step(1)
    assert node.outputs["out"] == 60
    node.consts["pv"] = 22
    p.step(2)
    assert node.outputs["out"] == 40

    # Deadband: no action inside ±0.5, and no step at the edge
    d = prog([n("pid", "pid", params={"deadband": 0.5}, consts={"pv": 20.8, "sp": 21, "kp": 10, "ti": 100, "bias": 50})])
    node = d.nodes["pid"]
    for t in range(10):
        d.step(t)
    assert node.outputs["out"] == 50 and node.state["i"] == 0
    assert node.outputs["err"] == pytest.approx(0.2)  # the error output is not affected
    node.consts["pv"] = 20.4  # 0.1 outside the band
    d.step(10)
    assert node.outputs["out"] == pytest.approx(50 + 10 * 0.1 + 10 * 0.1 / 100)


def test_pid_integral_survives_save_and_restart():
    data = {
        "id": "p1",
        "name": "Test",
        "nodes": [n("pid", "pid", consts={"pv": 20, "sp": 21, "kp": 10, "ti": 100})],
        "links": [],
    }
    p = Program(data, io=FakeIO())
    for t in range(51):
        p.step(t)
    out = p.nodes["pid"].outputs["out"]
    assert out == pytest.approx(15)

    # Saved without changes (online change): the first scan of the new program has dt = 0
    saved = Program(data, io=FakeIO(), previous=p)
    saved.step(1000)
    assert saved.nodes["pid"].outputs["out"] == pytest.approx(out)

    # Restart: the integral comes back from the stored state
    restarted = Program(data, io=FakeIO(), retained=p.retained_state())
    restarted.step(0)
    assert restarted.nodes["pid"].outputs["out"] == pytest.approx(out)


def test_filter_value_survives_restart():
    data = {"id": "p1", "name": "Test", "nodes": [n("f", "pt1", consts={"in": 0, "tau": 100})], "links": []}
    p = Program(data, io=FakeIO(), retained={"f": {"type": "pt1", "s": {"y": 20.0}}})
    p.step(0)
    assert p.nodes["f"].outputs["out"] == 20.0  # not the input (0) on the first scan
    p.step(1)
    assert 19 < p.nodes["f"].outputs["out"] < 20


def test_pid_lowered_limit_takes_effect_at_once():
    p = prog([n("pid", "pid", consts={"pv": 18, "sp": 21, "kp": 1, "ti": 1, "min": 0, "max": 100})])
    for t in range(200):
        p.step(t)
    node = p.nodes["pid"]
    assert node.outputs["out"] == 100
    node.consts["max"] = 50
    node.consts["pv"] = 24  # error turns negative: the output must come down from 50 at once
    p.step(200)
    p.step(201)
    assert node.outputs["out"] < 50


def test_ramp_and_pt1():
    io = FakeIO()
    p = prog([n("r", "ramp", consts={"in": 10, "rate": 2}), n("f", "pt1", consts={"in": 10, "tau": 0})], io=io)
    p.step(0)
    p.nodes["r"].consts["in"] = 20
    p.step(1)
    assert p.nodes["r"].outputs["out"] == 12
    p.step(10)
    assert p.nodes["r"].outputs["out"] == 20
    assert p.nodes["f"].outputs["out"] == 10


# ---------------------------------------------------------------- HA io blocks
def test_entity_in_invalid_handling():
    io = FakeIO()
    io.states["sensor.t"] = ("21.5", {"hum": 40})
    p = prog(
        [
            n("a", "entity_in", params={"entity_id": "sensor.t"}),
            n("b", "entity_in", y=100, params={"entity_id": "sensor.t", "attribute": "hum"}),
            n("c", "entity_in", y=200, params={"entity_id": "sensor.t", "on_invalid": "fallback", "fallback": -1}),
        ],
        io=io,
    )
    p.step(0)
    assert p.nodes["a"].outputs["value"] == 21.5
    assert p.nodes["b"].outputs["value"] == 40
    io.states["sensor.t"] = ("unavailable", {})
    p.step(1)
    assert p.nodes["a"].outputs["value"] == 21.5
    assert p.nodes["a"].outputs["valid"] is False
    assert p.nodes["c"].outputs["value"] == -1


def test_entity_out_change_only_deadband_interval():
    io = FakeIO()
    p = prog(
        [n("o", "entity_out", params={"entity_id": "number.x", "deadband": 1, "min_interval": 5}, consts={"value": 10.0})],
        io=io,
    )
    p.step(0)
    assert io.writes == [("number.x", "auto", 10.0)]
    p.step(1)
    assert len(io.writes) == 1
    p.nodes["o"].consts["value"] = 10.5  # inside deadband
    p.step(2)
    assert len(io.writes) == 1
    p.nodes["o"].consts["value"] = 12.0  # outside deadband but inside min interval
    p.step(3)
    assert len(io.writes) == 1
    p.step(6)
    assert io.writes[-1] == ("number.x", "auto", 12.0)


def test_publish_change_only_deadband_interval():
    io = FakeIO()
    sent = []
    io.publish = lambda pid, nid, value: sent.append(value)
    p = prog([n("pub", "publish", params={"deadband": 0.5, "min_interval": 5}, consts={"value": 20.0})], io=io)
    p.step(0)
    assert sent == [20.0]
    p.step(1)
    assert sent == [20.0]  # unchanged: nothing new for HA or the recorder
    p.nodes["pub"].consts["value"] = 20.3  # inside the deadband
    p.step(2)
    assert sent == [20.0]
    p.nodes["pub"].consts["value"] = 21.0  # outside the deadband, inside the minimum interval
    p.step(3)
    assert sent == [20.0]
    p.step(5)
    assert sent == [20.0, 21.0]  # the newest value comes out once the interval has passed

    sent.clear()
    b = prog([n("b", "publish", consts={"value": False})], io=io)  # defaults: every change, at once
    for t, v in enumerate((False, True, True, False)):
        b.nodes["b"].consts["value"] = v
        b.step(t)
    assert sent == [False, True, False]


def test_pid_derivative_kick_is_bounded():
    """A PV step seen by a short scan (an event scan) must not kick the output much harder."""

    def kick(dt):
        p = prog([n("pid", "pid", consts={"pv": 20, "sp": 21, "kp": 2, "ti": 0, "td": 30, "min": -1000, "max": 1000})])
        p.step(0)
        p.step(1)
        before = p.nodes["pid"].outputs["out"]
        p.nodes["pid"].consts["pv"] = 21
        p.step(1 + dt)
        return before - p.nodes["pid"].outputs["out"]

    slow, fast = kick(1.0), kick(0.02)
    # P step (kp) plus the filtered D step, at most kp * 10 per unit of PV change
    assert 2 < slow < fast <= 2 + 2 * 10
    assert fast < 1.5 * slow


def test_inputs_to_watch_include_macros():
    macro = {"id": "m", "name": "M", "nodes": [n("in", "entity_in", params={"entity_id": "sensor.inner"})], "links": []}
    data = {
        "id": "p1",
        "name": "Test",
        "nodes": [
            n("a", "entity_in", params={"entity_id": " sensor.outer "}),
            n("b", "entity_in", params={"entity_id": ""}),
            n("k", "knx_read", params={"address": "1/2/3"}),
            {"id": "inst", "type": "macro:m", "x": 0, "y": 0},
        ],
        "links": [],
    }
    p = Program(data, io=FakeIO(), macros={"m": macro})
    assert p.inputs_to_watch() == ({"sensor.outer", "sensor.inner"}, {"1/2/3"})
    assert p.event_scan is True
    assert Program(dict(data, event_scan=False), io=FakeIO(), macros={"m": macro}).event_scan is False


def test_entity_out_bool_and_press():
    io = FakeIO()
    p = prog(
        [
            n("k", "const_bool", params={"value": False}),
            n("o", "entity_out", x=100, params={"entity_id": "light.a"}),
            n("b", "entity_out", x=100, y=100, params={"entity_id": "button.go"}),
        ],
        [("k", "q", "o", "value"), ("k", "q", "b", "value")],
        io=io,
    )
    p.step(0)
    assert io.writes == [("light.a", "auto", False)]
    p.nodes["k"].params["value"] = True
    p.step(1)
    assert ("light.a", "auto", True) in io.writes
    assert ("button.go", "auto", True) in io.writes
    p.step(2)
    assert len(io.writes) == 3


def test_setpoint_toggle_publish_and_specs():
    io = FakeIO()
    io.values["sp"] = 22.0
    p = prog(
        [
            n("sp", "setpoint", params={"name": "Temp SP", "unit": "°C"}),
            n("sw", "toggle", y=100, params={"name": "Manuell"}),
            n("pub", "publish", x=100, params={"name": "Avvik", "unit": "K"}),
            n("pubb", "publish", x=100, y=100, params={"name": "Manuell aktiv"}),
        ],
        [("sp", "value", "pub", "value"), ("sw", "q", "pubb", "value")],
        io=io,
    )
    p.step(0)
    assert io.published == {"pub": 22.0, "pubb": False}
    specs = {s["node_id"]: s for s in p.ha_entities()}
    assert specs["sp"]["platform"] == "number" and specs["sp"]["unit"] == "°C"
    assert specs["sw"]["platform"] == "switch"
    assert specs["pub"]["platform"] == "sensor" and specs["pub"]["unit"] == "K"
    assert specs["pubb"]["platform"] == "binary_sensor"


# ---------------------------------------------------------------- engine
def test_feedback_loop_one_cycle_delay():
    # Counter built from ADD with feedback: out = out(prev) + 1
    p = prog([n("add", "add", consts={"in2": 1})], [("add", "out", "add", "in1")])
    for t in range(5):
        p.step(t)
    assert p.nodes["add"].outputs["out"] == 5


def test_execution_order_follows_signal_flow():
    p = prog(
        [n("c", "not", x=0), n("b", "not", x=300), n("a", "not", x=600)],
        [("a", "q", "b", "in"), ("b", "q", "c", "in")],
    )
    assert [x.id for x in p.order] == ["a", "b", "c"]
    p.step(0)
    # a: not False = True, b: not True = False, c: not False = True, all in the same scan
    assert p.nodes["c"].outputs["q"] is True


def test_online_change_keeps_state():
    p = prog([n("sr", "sr", consts={"s": True}), n("t", "ton", consts={"in": True, "pt": 10})])
    p.step(0)
    p.step(5)
    data = dict(p.data)
    data["nodes"] = [n("sr", "sr"), n("t", "ton", consts={"in": True, "pt": 10}), n("new", "not")]
    p2 = Program(data, io=FakeIO(), previous=p)
    p2.last_now = p.last_now
    p2.step(10)
    assert p2.nodes["sr"].outputs["q"] is True
    assert p2.nodes["t"].outputs["q"] is True


def test_bad_data_is_tolerated():
    p = prog(
        [n("x", "nonexistent"), n("a", "not"), {"id": "a", "type": "not"}],
        [("a", "q", "zzz", "in"), ("a", "nope", "a", "in")],
    )
    p.step(0)
    assert len(p.warnings) >= 3
