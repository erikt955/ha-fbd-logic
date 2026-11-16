"""Function block library.

Every block is described by a BlockDef: its pins, parameters and an
execute function ``fn(ctx, i, p, s) -> dict`` where

* ``i`` – input values (already coerced to the pin type)
* ``p`` – parameter values (from the editor)
* ``s`` – per-instance state dict that survives between scan cycles
* return value – dict with output pin values

This module has no Home Assistant imports so it can be unit tested alone.
Home Assistant specific blocks talk to HA through ``ctx.io``.
"""

from __future__ import annotations

import copy
import math
import struct
from dataclasses import dataclass, field
from typing import Any, Callable

from .expr import ExpressionError, compile_expression
from .i18n import tr, translate_block

BOOL = "bool"
NUM = "num"
STR = "str"
ANY = "any"

ON_STATES = {
    "on",
    "true",
    "yes",
    "open",
    "opening",
    "home",
    "playing",
    "unlocked",
    "active",
    "heat",
    "cool",
    "heat_cool",
    "auto",
    "dry",
    "fan_only",
}

CATEGORIES: list[tuple[str, str]] = [
    ("io", "Home Assistant"),
    ("logic", "Logikk"),
    ("compare", "Sammenligning"),
    ("math", "Matematikk"),
    ("time", "Tid"),
    ("control", "Regulering"),
    ("bus", "KNX / Modbus"),
    ("misc", "Annet"),
    ("macro", "Makroer"),
    ("macro_io", "Makro-tilkoblinger"),
]

MACRO_PREFIX = "macro:"


# --------------------------------------------------------------------------
# Value coercion
# --------------------------------------------------------------------------
def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0 and not math.isnan(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ON_STATES:
            return True
        try:
            return float(s.replace(",", ".")) != 0
        except ValueError:
            return False
    return bool(value)


def to_num(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        f = float(value)
        return 0.0 if math.isnan(f) or math.isinf(f) else f
    if isinstance(value, str):
        s = value.strip()
        try:
            f = float(s.replace(",", "."))
            return 0.0 if math.isnan(f) or math.isinf(f) else f
        except ValueError:
            return 1.0 if s.lower() in ON_STATES else 0.0
    return 0.0


def to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.6g}"
    return str(value)


def coerce(value: Any, ptype: str) -> Any:
    if ptype == BOOL:
        return to_bool(value)
    if ptype == NUM:
        return to_num(value)
    if ptype == STR:
        return to_str(value)
    if value is None:
        return 0.0
    if isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    return value


def is_valid_raw(value: Any) -> bool:
    return value is not None and not (
        isinstance(value, str) and value in ("unavailable", "unknown", "")
    )


# --------------------------------------------------------------------------
# Definitions
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Port:
    name: str
    type: str
    default: Any = None
    label: str | None = None
    # Hidden ports exist in the engine but are not shown in the editor
    # (used by connectors that are wired implicitly at compile time).
    hidden: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "default": self.default,
            "label": self.label if self.label is not None else self.name,
        }


@dataclass(frozen=True)
class Param:
    name: str
    type: str  # text | number | bool | select | entity | textarea | schedule
    default: Any = None
    label: str = ""
    options: tuple[tuple[str, str], ...] = ()
    min: float | None = None
    max: float | None = None
    step: float | None = None
    help: str = ""
    show_if: tuple[str, tuple[Any, ...]] | None = None
    # Suggestions for a text field (value, label); free text is still allowed.
    suggest: tuple[tuple[str, str], ...] = ()

    def to_json(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "default": self.default,
            "label": self.label or self.name,
        }
        if self.options:
            data["options"] = [{"value": v, "label": lbl} for v, lbl in self.options]
        if self.suggest:
            data["suggest"] = [{"value": v, "label": lbl} for v, lbl in self.suggest]
        for key in ("min", "max", "step"):
            if getattr(self, key) is not None:
                data[key] = getattr(self, key)
        if self.help:
            data["help"] = self.help
        if self.show_if:
            data["show_if"] = {"param": self.show_if[0], "in": list(self.show_if[1])}
        return data


BlockFn = Callable[[Any, dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]]


@dataclass
class BlockDef:
    type: str
    category: str
    title: str
    symbol: str
    description: str
    inputs: list[Port] = field(default_factory=list)
    outputs: list[Port] = field(default_factory=list)
    params: list[Param] = field(default_factory=list)
    fn: BlockFn | None = None
    # Variable input count: {"param", "prefix" | "names" | "pairs", "type", "default",
    # "min", "max", "start" (first index, default 1), "after" (after fixed inputs)}
    dynamic: dict[str, Any] | None = None
    retain: tuple[str, ...] = ()
    ha: str | None = None  # entity_in | entity_out | setpoint | toggle | publish
    width: int = 120

    def param_defaults(self) -> dict[str, Any]:
        return {p.name: copy.deepcopy(p.default) for p in self.params}

    def dynamic_count(self, params: dict[str, Any]) -> int:
        dyn = self.dynamic
        if not dyn:
            return 0
        try:
            n = int(float(params.get(dyn["param"], dyn.get("count", 2))))
        except (TypeError, ValueError):
            n = int(dyn.get("count", 2))
        return max(int(dyn.get("min", 1)), min(int(dyn.get("max", 8)), n))

    def input_ports(self, params: dict[str, Any]) -> list[Port]:
        dyn = self.dynamic
        if not dyn:
            return list(self.inputs)
        n = self.dynamic_count(params)
        start = int(dyn.get("start", 1))
        names = dyn.get("names")
        pairs = dyn.get("pairs")
        ports: list[Port] = []
        for idx in range(n):
            if pairs:
                for prefix, ptype, default in pairs:
                    ports.append(Port(f"{prefix}{idx + start}", ptype, default))
            else:
                name = names[idx] if names else f"{dyn['prefix']}{idx + start}"
                ports.append(Port(name, dyn["type"], dyn.get("default")))
        if dyn.get("after"):
            return list(self.inputs) + ports
        return ports + list(self.inputs)

    def to_json(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "category": self.category,
            "title": self.title,
            "symbol": self.symbol,
            "description": self.description,
            "inputs": [p.to_json() for p in self.inputs if not p.hidden],
            "outputs": [p.to_json() for p in self.outputs if not p.hidden],
            "params": [p.to_json() for p in self.params],
            "dynamic": self.dynamic,
            "ha": self.ha,
            "width": self.width,
        }


LIBRARY: dict[str, BlockDef] = {}


def register(bdef: BlockDef) -> BlockDef:
    LIBRARY[bdef.type] = bdef
    return bdef


def _dyn(prefix: str, ptype: str, default: Any, count: int = 2, max_n: int = 8) -> dict[str, Any]:
    return {
        "param": "n",
        "prefix": prefix,
        "type": ptype,
        "default": default,
        "count": count,
        "min": 2,
        "max": max_n,
    }


def _n_param(count: int = 2, max_n: int = 8) -> Param:
    return Param("n", "number", count, "Antall innganger", min=2, max=max_n, step=1)


def _dyn_values(i: dict[str, Any], prefix: str, start: int = 1) -> list[Any]:
    vals = []
    idx = start
    while f"{prefix}{idx}" in i:
        vals.append(i[f"{prefix}{idx}"])
        idx += 1
    return vals


# --------------------------------------------------------------------------
# Home Assistant I/O blocks
# --------------------------------------------------------------------------
def _entity_in(ctx, i, p, s):
    raw = ctx.io.read(p.get("entity_id") or "", (p.get("attribute") or "").strip())
    valid = is_valid_raw(raw)
    if valid:
        s["last"] = raw
    elif p.get("on_invalid", "hold") == "hold" and "last" in s:
        raw = s["last"]
    else:
        raw = p.get("fallback", 0)
    return {
        "value": to_num(raw),
        "on": to_bool(raw),
        "text": to_str(raw),
        "valid": valid,
    }


register(
    BlockDef(
        type="entity_in",
        category="io",
        title="Les entitet",
        symbol="IN",
        description="Leser tilstanden (eller et attributt) til en HA-entitet.",
        outputs=[
            Port("value", NUM, label="verdi"),
            Port("on", BOOL, label="på"),
            Port("text", STR, label="tekst"),
            Port("valid", BOOL, label="gyldig"),
        ],
        params=[
            Param("entity_id", "entity", "", "Entitet"),
            Param("attribute", "text", "", "Attributt (valgfritt)"),
            Param(
                "on_invalid",
                "select",
                "hold",
                "Ved utilgjengelig",
                options=(("hold", "Hold siste verdi"), ("fallback", "Bruk reserveverdi")),
            ),
            Param("fallback", "number", 0, "Reserveverdi", show_if=("on_invalid", ("fallback",))),
        ],
        fn=_entity_in,
        ha="entity_in",
        width=150,
    )
)


def _values_differ(a: Any, b: Any, deadband: float) -> bool:
    num_a = isinstance(a, (int, float)) and not isinstance(a, bool)
    num_b = isinstance(b, (int, float)) and not isinstance(b, bool)
    if num_a and num_b:
        if deadband > 0:
            return abs(a - b) >= deadband
        return a != b
    return a != b


PRESS_DOMAINS = {"button", "input_button", "scene", "script"}


def _entity_out(ctx, i, p, s):
    entity_id = (p.get("entity_id") or "").strip()
    value = i["value"]
    enabled = i["en"]
    prev_en = s.get("en", True)
    s["en"] = enabled
    if not entity_id or not enabled:
        return {}
    action = p.get("action", "auto")
    domain = entity_id.split(".", 1)[0]

    if action == "press" or (action == "auto" and domain in PRESS_DOMAINS):
        level = to_bool(value)
        rising = level and not s.get("prev", level)
        s["prev"] = level
        if rising:
            ctx.io.write(ctx.program_id, ctx.node_id, entity_id, action, value, p)
        return {}

    deadband = to_num(p.get("deadband", 0))
    if "last" not in s:
        need = bool(p.get("write_on_start", True))
        if not need:
            s["last"] = value
    else:
        need = _values_differ(value, s["last"], deadband) or (enabled and not prev_en)
    if need:
        min_interval = to_num(p.get("min_interval", 0))
        if ctx.now - s.get("t", -1e12) >= min_interval:
            ctx.io.write(ctx.program_id, ctx.node_id, entity_id, action, value, p)
            s["last"] = value
            s["t"] = ctx.now
    return {}


register(
    BlockDef(
        type="entity_out",
        category="io",
        title="Skriv entitet",
        symbol="OUT",
        description=(
            "Skriver verdien til en HA-entitet via riktig tjeneste. Skriver bare "
            "når verdien endres (med valgfritt dødbånd og minste intervall)."
        ),
        inputs=[Port("value", ANY, 0, "verdi"), Port("en", BOOL, True, "aktiv")],
        params=[
            Param("entity_id", "entity", "", "Entitet"),
            Param(
                "action",
                "select",
                "auto",
                "Handling",
                options=(
                    ("auto", "Automatisk (etter domene)"),
                    ("on_off", "Av/på"),
                    ("value", "Sett verdi"),
                    ("brightness", "Lysstyrke %"),
                    ("position", "Posisjon %"),
                    ("temperature", "Temperatur"),
                    ("option", "Velg alternativ"),
                    ("press", "Trykk (på stigende flanke)"),
                    ("custom", "Egendefinert tjeneste"),
                ),
            ),
            Param(
                "service",
                "text",
                "",
                "Tjeneste",
                help="f.eks. light.turn_on",
                show_if=("action", ("custom",)),
            ),
            Param(
                "data_key",
                "text",
                "",
                "Datafelt for verdien",
                help="f.eks. brightness (tomt = ingen verdi sendes)",
                show_if=("action", ("custom",)),
            ),
            Param("deadband", "number", 0, "Dødbånd", min=0),
            Param("min_interval", "number", 0, "Minste intervall (s)", min=0),
            Param("write_on_start", "bool", True, "Skriv ved oppstart"),
        ],
        fn=_entity_out,
        ha="entity_out",
        width=150,
    )
)


def _setpoint(ctx, i, p, s):
    return {"value": to_num(ctx.io.get_value(ctx.program_id, ctx.node_id, p.get("initial", 0)))}


register(
    BlockDef(
        type="setpoint",
        category="io",
        title="Settpunkt (HA)",
        symbol="SP",
        description=(
            "Lager en number-entitet i HA som kan justeres fra dashboard, "
            "og gir verdien ut i programmet."
        ),
        outputs=[Port("value", NUM, label="verdi")],
        params=[
            Param("name", "text", "Settpunkt", "Navn"),
            Param("initial", "number", 21, "Startverdi"),
            Param("min", "number", 0, "Min"),
            Param("max", "number", 100, "Maks"),
            Param("step", "number", 0.5, "Steg"),
            Param("unit", "text", "", "Enhet"),
            Param(
                "mode",
                "select",
                "box",
                "Visning",
                options=(("box", "Tallfelt"), ("slider", "Glidebryter"), ("auto", "Auto")),
            ),
        ],
        fn=_setpoint,
        ha="setpoint",
        width=140,
    )
)


def _toggle(ctx, i, p, s):
    return {"q": to_bool(ctx.io.get_value(ctx.program_id, ctx.node_id, bool(p.get("initial", False))))}


register(
    BlockDef(
        type="toggle",
        category="io",
        title="Bryter (HA)",
        symbol="SW",
        description="Lager en switch-entitet i HA (f.eks. manuell overstyring) og gir tilstanden ut.",
        outputs=[Port("q", BOOL)],
        params=[
            Param("name", "text", "Bryter", "Navn"),
            Param("initial", "bool", False, "Startverdi"),
        ],
        fn=_toggle,
        ha="toggle",
        width=140,
    )
)


def _publish(ctx, i, p, s):
    # Every new value is a state change in HA and a row in the recorder, so only real changes go out.
    value = i["value"]
    if "last" in s:
        if not _values_differ(value, s["last"], to_num(p.get("deadband", 0))):
            return {}
        if ctx.now - s["t"] < to_num(p.get("min_interval", 0)):
            return {}  # sent on the first scan after the interval, with the newest value
    s["last"] = value
    s["t"] = ctx.now
    ctx.io.publish(ctx.program_id, ctx.node_id, value)
    return {}


# Common device classes for building automation. HA's own names; checked against HA on save (device_class.py).
_PUBLISH_DEVICE_CLASSES = (
    ("temperature", "Temperatur (tall)"),
    ("temperature_delta", "Temperaturdifferanse (tall)"),
    ("humidity", "Relativ fuktighet (tall)"),
    ("carbon_dioxide", "CO₂ (tall)"),
    ("volatile_organic_compounds_parts", "VOC (tall)"),
    ("pm25", "Svevestøv PM2.5 (tall)"),
    ("pressure", "Trykk (tall)"),
    ("volume_flow_rate", "Volumstrøm (tall)"),
    ("power", "Effekt (tall)"),
    ("energy", "Energi (tall)"),
    ("voltage", "Spenning (tall)"),
    ("current", "Strøm (tall)"),
    ("power_factor", "Effektfaktor (tall)"),
    ("frequency", "Frekvens (tall)"),
    ("illuminance", "Belysningsstyrke (tall)"),
    ("wind_speed", "Vindhastighet (tall)"),
    ("duration", "Varighet (tall)"),
    ("battery", "Batteri (tall eller av/på)"),
    ("running", "I drift (av/på)"),
    ("problem", "Feil/alarm (av/på)"),
    ("heat", "Varme (av/på)"),
    ("cold", "Kulde (av/på)"),
    ("door", "Dør (av/på)"),
    ("window", "Vindu (av/på)"),
    ("opening", "Åpen/lukket (av/på)"),
    ("motion", "Bevegelse (av/på)"),
    ("occupancy", "Tilstedeværelse (av/på)"),
    ("moisture", "Fukt/lekkasje (av/på)"),
    ("smoke", "Røyk (av/på)"),
)


register(
    BlockDef(
        type="publish",
        category="io",
        title="Publiser verdi",
        symbol="PUB",
        description=(
            "Gjør et internt signal tilgjengelig som sensor/binary_sensor i HA "
            "(til dashboard, historikk og automasjoner)."
        ),
        inputs=[Port("value", ANY, 0, "verdi")],
        params=[
            Param("name", "text", "Signal", "Navn"),
            Param(
                "kind",
                "select",
                "auto",
                "Type",
                options=(
                    ("auto", "Automatisk"),
                    ("num", "Tall (sensor)"),
                    ("bool", "Av/på (binary_sensor)"),
                    ("text", "Tekst (sensor)"),
                ),
            ),
            Param("unit", "text", "", "Enhet"),
            Param(
                "device_class",
                "text",
                "",
                "Device class (valgfritt)",
                help="HA-navnet med små bokstaver, f.eks. temperature. Velg fra listen eller skriv selv.",
                suggest=_PUBLISH_DEVICE_CLASSES,
            ),
            Param("decimals", "number", 2, "Desimaler", min=0, max=6, step=1),
            Param(
                "deadband",
                "number",
                0,
                "Dødbånd",
                min=0,
                help="Tall sendes til HA først når de har endret seg minst så mye. 0 = hver endring.",
            ),
            Param(
                "min_interval",
                "number",
                0,
                "Minste intervall (s)",
                min=0,
                help="Høyst én ny verdi så ofte. Siste verdi kommer alltid fram.",
            ),
        ],
        fn=_publish,
        ha="publish",
        width=140,
    )
)


# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
register(
    BlockDef(
        type="const_num",
        category="misc",
        title="Konstant (tall)",
        symbol="K",
        description="Fast tallverdi.",
        outputs=[Port("out", NUM)],
        params=[Param("value", "number", 0, "Verdi")],
        fn=lambda ctx, i, p, s: {"out": to_num(p.get("value", 0))},
        width=100,
    )
)
register(
    BlockDef(
        type="const_bool",
        category="misc",
        title="Konstant (av/på)",
        symbol="K",
        description="Fast av/på-verdi.",
        outputs=[Port("q", BOOL)],
        params=[Param("value", "bool", True, "Verdi")],
        fn=lambda ctx, i, p, s: {"q": bool(p.get("value", True))},
        width=100,
    )
)
register(
    BlockDef(
        type="comment",
        category="misc",
        title="Kommentar",
        symbol="",
        description="Fritekst på tegningen. Påvirker ikke logikken.",
        params=[Param("text", "textarea", "Kommentar", "Tekst")],
        fn=None,
        width=180,
    )
)


# --------------------------------------------------------------------------
# Logic
# --------------------------------------------------------------------------
register(
    BlockDef(
        type="and",
        category="logic",
        title="OG (AND)",
        symbol="&",
        description="Utgangen er på når alle innganger er på.",
        outputs=[Port("q", BOOL)],
        params=[_n_param()],
        dynamic=_dyn("in", BOOL, True),
        fn=lambda ctx, i, p, s: {"q": all(_dyn_values(i, "in"))},
        width=90,
    )
)
register(
    BlockDef(
        type="or",
        category="logic",
        title="ELLER (OR)",
        symbol="≥1",
        description="Utgangen er på når minst én inngang er på.",
        outputs=[Port("q", BOOL)],
        params=[_n_param()],
        dynamic=_dyn("in", BOOL, False),
        fn=lambda ctx, i, p, s: {"q": any(_dyn_values(i, "in"))},
        width=90,
    )
)
register(
    BlockDef(
        type="xor",
        category="logic",
        title="XOR",
        symbol="=1",
        description="Utgangen er på når et odde antall innganger er på.",
        outputs=[Port("q", BOOL)],
        params=[_n_param()],
        dynamic=_dyn("in", BOOL, False),
        fn=lambda ctx, i, p, s: {"q": sum(1 for v in _dyn_values(i, "in") if v) % 2 == 1},
        width=90,
    )
)
register(
    BlockDef(
        type="not",
        category="logic",
        title="IKKE (NOT)",
        symbol="1o",
        description="Inverterer inngangen.",
        inputs=[Port("in", BOOL, False)],
        outputs=[Port("q", BOOL)],
        fn=lambda ctx, i, p, s: {"q": not i["in"]},
        width=90,
    )
)


def _sr(ctx, i, p, s):
    if i["s"]:
        s["q"] = True
    elif i["r"]:
        s["q"] = False
    return {"q": s.get("q", False)}


def _rs(ctx, i, p, s):
    if i["r"]:
        s["q"] = False
    elif i["s"]:
        s["q"] = True
    return {"q": s.get("q", False)}


register(
    BlockDef(
        type="sr",
        category="logic",
        title="SR-lås (sett dominant)",
        symbol="SR",
        description="Sett/tilbakestill-lås. Sett vinner hvis begge er på. Huskes over omstart.",
        inputs=[Port("s", BOOL, False), Port("r", BOOL, False)],
        outputs=[Port("q", BOOL)],
        fn=_sr,
        retain=("q",),
        width=100,
    )
)
register(
    BlockDef(
        type="rs",
        category="logic",
        title="RS-lås (tilbakestill dominant)",
        symbol="RS",
        description="Sett/tilbakestill-lås. Tilbakestill vinner hvis begge er på. Huskes over omstart.",
        inputs=[Port("s", BOOL, False), Port("r", BOOL, False)],
        outputs=[Port("q", BOOL)],
        fn=_rs,
        retain=("q",),
        width=100,
    )
)


def _r_trig(ctx, i, p, s):
    level = i["in"]
    prev = s.get("prev", level)
    s["prev"] = level
    return {"q": level and not prev}


def _f_trig(ctx, i, p, s):
    level = i["in"]
    prev = s.get("prev", level)
    s["prev"] = level
    return {"q": prev and not level}


register(
    BlockDef(
        type="r_trig",
        category="logic",
        title="Stigende flanke",
        symbol="R_TRIG",
        description="Gir én puls (ett skann) når inngangen går fra av til på.",
        inputs=[Port("in", BOOL, False)],
        outputs=[Port("q", BOOL)],
        fn=_r_trig,
        width=100,
    )
)
register(
    BlockDef(
        type="f_trig",
        category="logic",
        title="Fallende flanke",
        symbol="F_TRIG",
        description="Gir én puls (ett skann) når inngangen går fra på til av.",
        inputs=[Port("in", BOOL, False)],
        outputs=[Port("q", BOOL)],
        fn=_f_trig,
        width=100,
    )
)


def _toggle_ff(ctx, i, p, s):
    level = i["in"]
    prev = s.get("prev", level)
    s["prev"] = level
    if i["r"]:
        s["q"] = False
    elif level and not prev:
        s["q"] = not s.get("q", False)
    return {"q": s.get("q", False)}


register(
    BlockDef(
        type="toggle_ff",
        category="logic",
        title="Impulsrelé (toggle)",
        symbol="T",
        description="Hver stigende flanke på inngangen veksler utgangen. Huskes over omstart.",
        inputs=[Port("in", BOOL, False), Port("r", BOOL, False)],
        outputs=[Port("q", BOOL)],
        fn=_toggle_ff,
        retain=("q",),
        width=100,
    )
)


# --------------------------------------------------------------------------
# Compare
# --------------------------------------------------------------------------
def _cmp_block(type_: str, symbol: str, title: str, op: Callable[[float, float], bool]) -> None:
    register(
        BlockDef(
            type=type_,
            category="compare",
            title=title,
            symbol=symbol,
            description=f"Utgangen er på når A {symbol} B.",
            inputs=[Port("a", NUM, 0, "A"), Port("b", NUM, 0, "B")],
            outputs=[Port("q", BOOL)],
            fn=lambda ctx, i, p, s: {"q": op(i["a"], i["b"])},
            width=90,
        )
    )


_cmp_block("gt", ">", "Større enn", lambda a, b: a > b)
_cmp_block("ge", "≥", "Større eller lik", lambda a, b: a >= b)
_cmp_block("lt", "<", "Mindre enn", lambda a, b: a < b)
_cmp_block("le", "≤", "Mindre eller lik", lambda a, b: a <= b)
_cmp_block("eq", "=", "Lik", lambda a, b: abs(a - b) < 1e-9)
_cmp_block("ne", "≠", "Ulik", lambda a, b: abs(a - b) >= 1e-9)


def _hyst(ctx, i, p, s):
    x, hi, lo = i["in"], i["high"], i["low"]
    if "q" not in s:
        s["q"] = x >= hi
    if x >= hi:
        s["q"] = True
    elif x <= lo:
        s["q"] = False
    return {"q": s["q"]}


register(
    BlockDef(
        type="hyst",
        category="compare",
        title="Hysterese",
        symbol="HYST",
        description="På når inngang ≥ høy, av når inngang ≤ lav, ellers uendret.",
        inputs=[Port("in", NUM, 0), Port("high", NUM, 22, "høy"), Port("low", NUM, 20, "lav")],
        outputs=[Port("q", BOOL)],
        fn=_hyst,
        width=100,
    )
)
register(
    BlockDef(
        type="in_range",
        category="compare",
        title="Innenfor område",
        symbol="LO≤x≤HI",
        description="På når lav ≤ inngang ≤ høy.",
        inputs=[Port("in", NUM, 0), Port("low", NUM, 0, "lav"), Port("high", NUM, 100, "høy")],
        outputs=[Port("q", BOOL)],
        fn=lambda ctx, i, p, s: {"q": i["low"] <= i["in"] <= i["high"]},
        width=110,
    )
)


def _sel(ctx, i, p, s):
    return {"out": i["in1"] if i["g"] else i["in0"]}


register(
    BlockDef(
        type="sel",
        category="compare",
        title="Velger (SEL)",
        symbol="SEL",
        description="Gir ut in1 når g er på, ellers in0.",
        inputs=[Port("g", BOOL, False), Port("in0", ANY, 0.0), Port("in1", ANY, 0.0)],
        outputs=[Port("out", ANY)],
        fn=_sel,
        width=100,
    )
)


def _text_eq(ctx, i, p, s):
    a = i["in"]
    b = str(p.get("text", ""))
    if p.get("ignore_case", True):
        return {"q": a.strip().lower() == b.strip().lower()}
    return {"q": a.strip() == b.strip()}


register(
    BlockDef(
        type="text_eq",
        category="compare",
        title="Tekst lik",
        symbol="TXT=",
        description="På når teksten er lik oppgitt verdi (f.eks. hvac-modus 'heat').",
        inputs=[Port("in", STR, "")],
        outputs=[Port("q", BOOL)],
        params=[
            Param("text", "text", "", "Tekst"),
            Param("ignore_case", "bool", True, "Ignorer store/små bokstaver"),
        ],
        fn=_text_eq,
        width=110,
    )
)


# --------------------------------------------------------------------------
# Math
# --------------------------------------------------------------------------
register(
    BlockDef(
        type="add",
        category="math",
        title="Addisjon",
        symbol="+",
        description="Summerer inngangene.",
        outputs=[Port("out", NUM)],
        params=[_n_param()],
        dynamic=_dyn("in", NUM, 0.0),
        fn=lambda ctx, i, p, s: {"out": sum(_dyn_values(i, "in"))},
        width=90,
    )
)
register(
    BlockDef(
        type="sub",
        category="math",
        title="Subtraksjon",
        symbol="−",
        description="out = A − B",
        inputs=[Port("a", NUM, 0, "A"), Port("b", NUM, 0, "B")],
        outputs=[Port("out", NUM)],
        fn=lambda ctx, i, p, s: {"out": i["a"] - i["b"]},
        width=90,
    )
)


def _mul(ctx, i, p, s):
    out = 1.0
    for v in _dyn_values(i, "in"):
        out *= v
    return {"out": out}


register(
    BlockDef(
        type="mul",
        category="math",
        title="Multiplikasjon",
        symbol="×",
        description="Multipliserer inngangene.",
        outputs=[Port("out", NUM)],
        params=[_n_param()],
        dynamic=_dyn("in", NUM, 1.0),
        fn=_mul,
        width=90,
    )
)


def _div(ctx, i, p, s):
    if i["b"] == 0:
        return {"out": 0.0, "err": True}
    return {"out": i["a"] / i["b"], "err": False}


register(
    BlockDef(
        type="div",
        category="math",
        title="Divisjon",
        symbol="÷",
        description="out = A ÷ B. Ved deling på null blir out 0 og err på.",
        inputs=[Port("a", NUM, 0, "A"), Port("b", NUM, 1, "B")],
        outputs=[Port("out", NUM), Port("err", BOOL)],
        fn=_div,
        width=90,
    )
)
register(
    BlockDef(
        type="min",
        category="math",
        title="Minimum",
        symbol="MIN",
        description="Laveste av inngangene.",
        outputs=[Port("out", NUM)],
        params=[_n_param()],
        dynamic=_dyn("in", NUM, 0.0),
        fn=lambda ctx, i, p, s: {"out": min(_dyn_values(i, "in"))},
        width=90,
    )
)
register(
    BlockDef(
        type="max",
        category="math",
        title="Maksimum",
        symbol="MAX",
        description="Høyeste av inngangene.",
        outputs=[Port("out", NUM)],
        params=[_n_param()],
        dynamic=_dyn("in", NUM, 0.0),
        fn=lambda ctx, i, p, s: {"out": max(_dyn_values(i, "in"))},
        width=90,
    )
)


def _avg(ctx, i, p, s):
    vals = _dyn_values(i, "in")
    return {"out": sum(vals) / len(vals) if vals else 0.0}


register(
    BlockDef(
        type="avg",
        category="math",
        title="Gjennomsnitt",
        symbol="AVG",
        description="Gjennomsnitt av inngangene.",
        outputs=[Port("out", NUM)],
        params=[_n_param()],
        dynamic=_dyn("in", NUM, 0.0),
        fn=_avg,
        width=90,
    )
)
register(
    BlockDef(
        type="abs",
        category="math",
        title="Absoluttverdi",
        symbol="ABS",
        description="out = |in|",
        inputs=[Port("in", NUM, 0)],
        outputs=[Port("out", NUM)],
        fn=lambda ctx, i, p, s: {"out": abs(i["in"])},
        width=90,
    )
)
register(
    BlockDef(
        type="limit",
        category="math",
        title="Begrensning",
        symbol="LIMIT",
        description="Begrenser inngangen til [min, maks].",
        inputs=[Port("in", NUM, 0), Port("min", NUM, 0), Port("max", NUM, 100, "maks")],
        outputs=[Port("out", NUM)],
        fn=lambda ctx, i, p, s: {"out": max(i["min"], min(i["max"], i["in"]))},
        width=100,
    )
)


def _scale(ctx, i, p, s):
    x, x0, x1, y0, y1 = i["in"], i["in_lo"], i["in_hi"], i["out_lo"], i["out_hi"]
    if x1 == x0:
        return {"out": y0}
    y = y0 + (x - x0) * (y1 - y0) / (x1 - x0)
    if p.get("clamp", True):
        lo, hi = min(y0, y1), max(y0, y1)
        y = max(lo, min(hi, y))
    return {"out": y}


register(
    BlockDef(
        type="scale",
        category="math",
        title="Skalering (lineær)",
        symbol="SCALE",
        description="Lineær skalering fra [inn lav, inn høy] til [ut lav, ut høy].",
        inputs=[
            Port("in", NUM, 0),
            Port("in_lo", NUM, 0, "inn lav"),
            Port("in_hi", NUM, 100, "inn høy"),
            Port("out_lo", NUM, 0, "ut lav"),
            Port("out_hi", NUM, 100, "ut høy"),
        ],
        outputs=[Port("out", NUM)],
        params=[Param("clamp", "bool", True, "Begrens til utområdet")],
        fn=_scale,
        width=110,
    )
)


def _round(ctx, i, p, s):
    dec = int(to_num(p.get("decimals", 0)))
    return {"out": round(i["in"], dec)}


register(
    BlockDef(
        type="round",
        category="math",
        title="Avrunding",
        symbol="ROUND",
        description="Runder av til valgt antall desimaler.",
        inputs=[Port("in", NUM, 0)],
        outputs=[Port("out", NUM)],
        params=[Param("decimals", "number", 0, "Desimaler", min=0, max=6, step=1)],
        fn=_round,
        width=90,
    )
)

FORMULA_VARS = list("abcdefgh")


def _formula(ctx, i, p, s):
    expr = p.get("expr", "")
    if s.get("_src") != expr:
        s["_src"] = expr
        s["_fn"] = None
        s["_err"] = None
        try:
            s["_fn"] = compile_expression(expr, FORMULA_VARS)
        except ExpressionError as err:
            s["_err"] = str(err)
    func = s.get("_fn")
    if func is None:
        raise ExpressionError(s.get("_err") or tr("Ugyldig uttrykk"))
    values = {k: i.get(k, 0.0) for k in FORMULA_VARS}
    result = func(values)
    num = to_num(result)
    return {"out": num, "q": to_bool(result)}


register(
    BlockDef(
        type="formula",
        category="math",
        title="Formel",
        symbol="f(x)",
        description=(
            "Fritt uttrykk med innganger a…h, f.eks. 'a*0.5 + b' eller "
            "'sel(a > 20, b, c)'. Funksjoner: abs, min, max, round, sqrt, "
            "clamp, sel, floor, ceil, sin, cos, log, exp."
        ),
        outputs=[Port("out", NUM), Port("q", BOOL)],
        params=[
            Param("expr", "text", "a + b", "Uttrykk"),
            Param("n", "number", 2, "Antall innganger", min=1, max=8, step=1),
        ],
        dynamic={
            "param": "n",
            "names": FORMULA_VARS,
            "type": NUM,
            "default": 0.0,
            "count": 2,
            "min": 1,
            "max": 8,
        },
        fn=_formula,
        width=130,
    )
)


# --------------------------------------------------------------------------
# Time
# --------------------------------------------------------------------------
def _ton(ctx, i, p, s):
    pt = max(0.0, i["pt"])
    if i["in"]:
        if s.get("start") is None:
            s["start"] = ctx.now
        et = min(pt, ctx.now - s["start"])
        return {"q": ctx.now - s["start"] >= pt, "et": et}
    s["start"] = None
    return {"q": False, "et": 0.0}


def _tof(ctx, i, p, s):
    pt = max(0.0, i["pt"])
    if i["in"]:
        s["q"] = True
        s["start"] = None
        return {"q": True, "et": 0.0}
    if not s.get("q"):
        return {"q": False, "et": 0.0}
    if s.get("start") is None:
        s["start"] = ctx.now
    et = ctx.now - s["start"]
    if et >= pt:
        s["q"] = False
        s["start"] = None
        return {"q": False, "et": pt}
    return {"q": True, "et": et}


def _tp(ctx, i, p, s):
    pt = max(0.0, i["pt"])
    level = i["in"]
    prev = s.get("prev", level)
    s["prev"] = level
    if s.get("start") is None and level and not prev:
        s["start"] = ctx.now
    if s.get("start") is not None:
        et = ctx.now - s["start"]
        if et < pt:
            return {"q": True, "et": et}
        if not level:
            s["start"] = None
            return {"q": False, "et": 0.0}
        return {"q": False, "et": pt}
    return {"q": False, "et": 0.0}


_TIMER_IO = dict(
    inputs=[Port("in", BOOL, False), Port("pt", NUM, 5, "tid s")],
    outputs=[Port("q", BOOL), Port("et", NUM, label="gått s")],
    width=100,
)

register(
    BlockDef(
        type="ton",
        category="time",
        title="Innkoblingsforsinkelse",
        symbol="TON",
        description="Utgangen går på når inngangen har vært på i 'tid' sekunder.",
        fn=_ton,
        **_TIMER_IO,
    )
)
register(
    BlockDef(
        type="tof",
        category="time",
        title="Utkoblingsforsinkelse",
        symbol="TOF",
        description="Utgangen går av 'tid' sekunder etter at inngangen gikk av.",
        fn=_tof,
        **_TIMER_IO,
    )
)
register(
    BlockDef(
        type="tp",
        category="time",
        title="Puls",
        symbol="TP",
        description="Stigende flanke gir en puls med fast lengde ('tid' sekunder).",
        fn=_tp,
        **_TIMER_IO,
    )
)


def _blink(ctx, i, p, s):
    if not i["en"]:
        s["start"] = None
        return {"q": False}
    t_on, t_off = max(0.05, i["t_on"]), max(0.05, i["t_off"])
    if s.get("start") is None:
        s["start"] = ctx.now
    phase = (ctx.now - s["start"]) % (t_on + t_off)
    return {"q": phase < t_on}


register(
    BlockDef(
        type="blink",
        category="time",
        title="Pulsgenerator",
        symbol="BLINK",
        description="Blinker med valgt på- og av-tid mens aktiv.",
        inputs=[
            Port("en", BOOL, True, "aktiv"),
            Port("t_on", NUM, 1, "på s"),
            Port("t_off", NUM, 1, "av s"),
        ],
        outputs=[Port("q", BOOL)],
        fn=_blink,
        width=100,
    )
)


def _clock(ctx, i, p, s):
    t = ctx.local
    wd = t.isoweekday()
    return {
        "hour": float(t.hour),
        "minute": float(t.minute),
        "daymin": float(t.hour * 60 + t.minute),
        "weekday": float(wd),
        "weekend": wd >= 6,
    }


register(
    BlockDef(
        type="clock",
        category="time",
        title="Klokke",
        symbol="CLOCK",
        description="Lokal tid: time, minutt, minutter siden midnatt, ukedag (1=man) og helg.",
        outputs=[
            Port("hour", NUM, label="time"),
            Port("minute", NUM, label="min"),
            Port("daymin", NUM, label="dagmin"),
            Port("weekday", NUM, label="ukedag"),
            Port("weekend", BOOL, label="helg"),
        ],
        fn=_clock,
        width=110,
    )
)


def _runtime(ctx, i, p, s):
    if i["reset"]:
        s["sec"] = 0.0
    elif i["in"]:
        s["sec"] = s.get("sec", 0.0) + ctx.dt
    return {"hours": s.get("sec", 0.0) / 3600.0}


register(
    BlockDef(
        type="runtime",
        category="time",
        title="Driftstid",
        symbol="RUNTIME",
        description="Teller driftstimer mens inngangen er på. Huskes over omstart.",
        inputs=[Port("in", BOOL, False), Port("reset", BOOL, False)],
        outputs=[Port("hours", NUM, label="timer")],
        fn=_runtime,
        retain=("sec",),
        width=110,
    )
)


def _counter(ctx, i, p, s):
    level = i["cu"]
    prev = s.get("prev", level)
    s["prev"] = level
    if i["reset"]:
        s["count"] = 0.0
    elif level and not prev:
        s["count"] = s.get("count", 0.0) + 1.0
    return {"count": s.get("count", 0.0)}


register(
    BlockDef(
        type="counter",
        category="time",
        title="Teller",
        symbol="CTU",
        description="Teller stigende flanker. Huskes over omstart.",
        inputs=[Port("cu", BOOL, False), Port("reset", BOOL, False)],
        outputs=[Port("count", NUM)],
        fn=_counter,
        retain=("count",),
        width=100,
    )
)


# --------------------------------------------------------------------------
# Control
# --------------------------------------------------------------------------
def _deadband(err: float, band: float) -> float:
    """Continuous deadband: zero inside ±band, and no step in the error at the edge."""
    if err > band:
        return err - band
    if err < -band:
        return err + band
    return 0.0


def _pid(ctx, i, p, s):
    pv, sp = i["pv"], i["sp"]
    kp, ti, td = i["kp"], i["ti"], i["td"]
    lo, hi = i["min"], i["max"]
    if hi < lo:
        lo, hi = hi, lo
    bias = i["bias"]
    direct = p.get("direction", "reverse") == "direct"
    err = (pv - sp) if direct else (sp - pv)
    e = _deadband(err, max(0.0, to_num(p.get("deadband", 0))))
    prev_pv = s.get("pv", pv)
    s["pv"] = pv
    dt = ctx.dt

    p_term = kp * e
    d_term = 0.0
    if td > 0:
        # Derivative on PV with the usual first-order filter (Tf = Td/10). Unfiltered, a PV step
        # seen by a short scan (event scans come right after the change) would give a huge kick.
        tf = td / 10
        d_term = s.get("d", 0.0)
        if dt > 0:
            dpv = pv - prev_pv
            d_term = (tf * d_term + kp * td * (dpv if direct else -dpv)) / (tf + dt)
    s["d"] = d_term
    pd = p_term + d_term

    if not i["en"] or i["man"]:
        # Off (output at min) or manual (output = manual value). The integral tracks the output,
        # so the return to automatic starts from where the output is: no step (bumpless).
        out = lo if not i["en"] else max(lo, min(hi, i["mv"]))
        s["i"] = out - bias - pd if ti > 0 else 0.0
        return {"out": out, "err": err, "auto": False}

    integral = s.get("i", 0.0)
    if ti <= 0:
        integral = 0.0
    elif dt > 0:  # dt is 0 on the first scan after a save or restart: keep the integral as it was
        inc = kp * e * dt / ti
        cand = integral + inc
        u_try = bias + pd + cand
        if inc > 0 and u_try > hi:
            integral = max(integral, min(cand, hi - bias - pd))
        elif inc < 0 and u_try < lo:
            integral = min(integral, max(cand, lo - bias - pd))
        else:
            integral = cand
    # Keep the integral within the output range (a lowered limit takes effect at once). It may lie
    # further out only as far as P and D need, so that the output can sit at a limit after tracking.
    integral = max(lo - bias - max(0.0, pd), min(hi - bias - min(0.0, pd), integral))
    s["i"] = integral
    out = max(lo, min(hi, bias + pd + integral))
    return {"out": out, "err": err, "auto": True}


register(
    BlockDef(
        type="pid",
        category="control",
        title="PID-regulator",
        symbol="PID",
        description=(
            "Generell PID-regulator med anti-windup, for alle slags prosesser (temperatur, trykk, "
            "fukt, CO₂, nivå, lys). Revers: utgangen øker når PV er under SP (f.eks. varme, befukting). "
            "Direkte: utgangen øker når PV er over SP (f.eks. kjøling, CO₂ til ventilasjon). "
            "Ti = integraltid i sekunder (0 = av), Td = derivattid i sekunder "
            "(derivatet virker på PV og er filtrert med Td/10). "
            "Aktiv av gir min ut, manuell gir den manuelle verdien ut. Overgangen tilbake til "
            "automatikk er støtfri: utgangen fortsetter der den var. Arbeidspunktet legges til "
            "utgangen (nyttig for ren P-regulering eller foroverkobling)."
        ),
        inputs=[
            Port("pv", NUM, 0, "PV"),
            Port("sp", NUM, 21, "SP"),
            Port("en", BOOL, True, "aktiv"),
            Port("man", BOOL, False, "manuell"),
            Port("mv", NUM, 0, "man. verdi"),
            Port("kp", NUM, 5, "Kp"),
            Port("ti", NUM, 120, "Ti s"),
            Port("td", NUM, 0, "Td s"),
            Port("bias", NUM, 0, "arb.punkt"),
            Port("min", NUM, 0),
            Port("max", NUM, 100, "maks"),
        ],
        outputs=[Port("out", NUM), Port("err", NUM, label="avvik"), Port("auto", BOOL)],
        params=[
            Param(
                "direction",
                "select",
                "reverse",
                "Virkning",
                options=(
                    ("reverse", "Revers: øker når PV < SP (f.eks. varme)"),
                    ("direct", "Direkte: øker når PV > SP (f.eks. kjøling)"),
                ),
            ),
            Param(
                "deadband",
                "number",
                0,
                "Dødbånd",
                min=0,
                help=(
                    "Avvik innenfor ± dødbåndet regnes som 0, så pådraget står stille nær SP "
                    "(sparer spjeld- og ventilmotorer). Samme enhet som PV. 0 = av."
                ),
            ),
        ],
        fn=_pid,
        retain=("i",),
        width=120,
    )
)


def _ramp(ctx, i, p, s):
    target, rate = i["in"], abs(i["rate"])
    cur = s.get("out", target)
    if rate <= 0:
        cur = target
    else:
        step = rate * ctx.dt
        if abs(target - cur) <= step:
            cur = target
        else:
            cur += step if target > cur else -step
    s["out"] = cur
    return {"out": cur}


register(
    BlockDef(
        type="ramp",
        category="control",
        title="Rampe",
        symbol="RAMP",
        description="Utgangen følger inngangen med maks endring 'rate' per sekund.",
        inputs=[Port("in", NUM, 0), Port("rate", NUM, 1, "rate/s")],
        outputs=[Port("out", NUM)],
        fn=_ramp,
        retain=("out",),
        width=100,
    )
)


def _pt1(ctx, i, p, s):
    x, tau = i["in"], max(0.0, i["tau"])
    y = s.get("y", x)
    if tau <= 0:
        y = x
    elif ctx.dt > 0:  # dt is 0 on the first scan after a save or restart: keep the stored value
        y += (x - y) * ctx.dt / (tau + ctx.dt)
    s["y"] = y
    return {"out": y}


register(
    BlockDef(
        type="pt1",
        category="control",
        title="Lavpassfilter",
        symbol="PT1",
        description="Førsteordens filter med tidskonstant tau (sekunder).",
        inputs=[Port("in", NUM, 0), Port("tau", NUM, 10, "tau s")],
        outputs=[Port("out", NUM)],
        fn=_pt1,
        retain=("y",),
        width=100,
    )
)


# --------------------------------------------------------------------------
# Selectors with many inputs
# --------------------------------------------------------------------------
def _mux(ctx, i, p, s):
    vals = _dyn_values(i, "in", 0)
    k = int(round(i["k"]))
    err = k < 0 or k >= len(vals)
    k = max(0, min(len(vals) - 1, k))
    return {"out": vals[k], "err": err}


register(
    BlockDef(
        type="mux",
        category="compare",
        title="Multiplekser (MUX)",
        symbol="MUX",
        description=(
            "Gir ut inngangen som indeksen k peker på (in0, in1, …). "
            "Ugyldig indeks begrenses til nærmeste inngang og setter err."
        ),
        inputs=[Port("k", NUM, 0)],
        outputs=[Port("out", ANY), Port("err", BOOL)],
        params=[Param("n", "number", 3, "Antall innganger", min=2, max=16, step=1)],
        dynamic={
            "param": "n",
            "prefix": "in",
            "start": 0,
            "after": True,
            "type": ANY,
            "default": 0.0,
            "count": 3,
            "min": 2,
            "max": 16,
        },
        fn=_mux,
        width=100,
    )
)


def _prio(ctx, i, p, s):
    idx = 1
    while f"g{idx}" in i:
        if i[f"g{idx}"]:
            return {"out": i[f"in{idx}"], "idx": float(idx)}
        idx += 1
    return {"out": i["else"], "idx": 0.0}


register(
    BlockDef(
        type="prio",
        category="compare",
        title="Prioritetsvelger",
        symbol="PRIO",
        description=(
            "Gir ut verdien til første aktive prioritet (g1 høyest), ellers 'ellers'. "
            "Typisk: manuell > alarm > tidsprogram > auto. idx = aktiv prioritet (0 = ingen)."
        ),
        inputs=[Port("else", ANY, 0.0, "ellers")],
        outputs=[Port("out", ANY), Port("idx", NUM)],
        params=[Param("n", "number", 3, "Antall prioriteter", min=1, max=8, step=1)],
        dynamic={
            "param": "n",
            "pairs": [["g", BOOL, False], ["in", ANY, 0.0]],
            "count": 3,
            "min": 1,
            "max": 8,
        },
        fn=_prio,
        width=110,
    )
)


def _bit_get(ctx, i, p, s):
    bit = int(max(0, min(63, round(i["bit"]))))
    return {"q": bool((int(i["in"]) >> bit) & 1)}


register(
    BlockDef(
        type="bit_get",
        category="math",
        title="Hent bit",
        symbol="BIT",
        description="Henter én bit (0 = minst signifikant) ut av et heltall, f.eks. et Modbus statusord.",
        inputs=[Port("in", NUM, 0), Port("bit", NUM, 0)],
        outputs=[Port("q", BOOL)],
        fn=_bit_get,
        width=90,
    )
)


# --------------------------------------------------------------------------
# Weekly schedule
# --------------------------------------------------------------------------
WEEK_MIN = 7 * 1440


def parse_hhmm(value: Any) -> int | None:
    """'07:30' -> 450 minutes. '24:00' is allowed. None if invalid."""
    try:
        hh, mm = str(value).strip().split(":", 1)
        h, m = int(hh), int(mm)
    except (ValueError, AttributeError):
        return None
    if not (0 <= h <= 24 and 0 <= m < 60) or (h == 24 and m):
        return None
    return h * 60 + m


def parse_periods(raw: Any) -> list[tuple[int, int, frozenset[int]]]:
    out = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        on, off = parse_hhmm(item.get("on")), parse_hhmm(item.get("off"))
        days = frozenset(
            int(d) for d in (item.get("days") or []) if str(d).isdigit() and 1 <= int(d) <= 7
        )
        if on is None or off is None or on == off or not days:
            continue
        out.append((on, off, days))
    return out


def schedule_active(periods, wd: int, minute: float) -> bool:
    prev = 7 if wd == 1 else wd - 1
    for on, off, days in periods:
        if on < off:
            if wd in days and on <= minute < off:
                return True
        elif (wd in days and minute >= on) or (prev in days and minute < off):
            return True
    return False


def _schedule_eval(periods, wd: int, minute: float) -> tuple[bool, float]:
    """Return (active, minutes until the state changes, -1 if never)."""
    active = schedule_active(periods, wd, minute)
    now_w = (wd - 1) * 1440 + minute
    events = set()
    for on, off, days in periods:
        for d in days:
            base = (d - 1) * 1440
            events.add((base + on) % WEEK_MIN)
            events.add((base + off + (1440 if off < on else 0)) % WEEK_MIN)
    deltas = sorted({(e - now_w) % WEEK_MIN or WEEK_MIN for e in events})
    for delta in deltas:
        t = (now_w + delta) % WEEK_MIN
        if schedule_active(periods, int(t // 1440) + 1, t % 1440) != active:
            return active, float(delta)
    return active, -1.0


def _schedule(ctx, i, p, s):
    t = ctx.local
    if s.get("_src") is not p.get("periods"):
        s["_src"] = p.get("periods")
        s["_p"] = parse_periods(p.get("periods"))
        s["_key"] = None
    key = (t.isoweekday(), t.hour * 60 + t.minute)
    if s.get("_key") != key:
        s["_key"] = key
        s["_res"] = _schedule_eval(s["_p"], key[0], key[1])
    active, nxt = s["_res"]
    if nxt > 0:
        nxt = max(0.0, nxt - t.second / 60.0)
    q = active and i["en"]
    return {
        "q": q,
        "value": to_num(p.get("on_value", 1)) if q else to_num(p.get("off_value", 0)),
        "next": nxt,
    }


register(
    BlockDef(
        type="schedule",
        category="time",
        title="Ukeplan",
        symbol="UKE",
        description=(
            "Tidsprogram med perioder per ukedag. q er på i periodene, value gir "
            "verdi for på/av (f.eks. 21/18 °C), next er minutter til neste skift. "
            "En periode der av er før på, går over midnatt. aktiv = av gir q av (f.eks. helligdag)."
        ),
        inputs=[Port("en", BOOL, True, "aktiv")],
        outputs=[Port("q", BOOL), Port("value", NUM, label="verdi"), Port("next", NUM, label="neste min")],
        params=[
            Param(
                "periods",
                "schedule",
                [{"days": [1, 2, 3, 4, 5], "on": "07:00", "off": "16:00"}],
                "Perioder",
            ),
            Param("on_value", "number", 1, "Verdi i periode"),
            Param("off_value", "number", 0, "Verdi utenfor periode"),
        ],
        fn=_schedule,
        width=130,
    )
)


# --------------------------------------------------------------------------
# Connectors (across pages) and macro pins
# --------------------------------------------------------------------------
def _passthrough(ctx, i, p, s):
    ptype = p.get("type", ANY)
    if ptype not in (BOOL, NUM, STR, ANY):
        ptype = ANY
    return {"value": coerce(i["value"], ptype)}


register(
    BlockDef(
        type="page_out",
        category="misc",
        title="Koblingspunkt (sender)",
        symbol="→",
        description=(
            "Sender et signal under et navn. Hentes med «Koblingspunkt (mottaker)» "
            "med samme navn, på samme eller en annen side."
        ),
        inputs=[Port("value", ANY, 0.0, "verdi")],
        outputs=[Port("value", ANY, hidden=True)],
        params=[Param("name", "text", "signal1", "Navn")],
        fn=_passthrough,
        width=120,
    )
)
register(
    BlockDef(
        type="page_in",
        category="misc",
        title="Koblingspunkt (mottaker)",
        symbol="←",
        description="Henter signalet fra koblingspunktet (sender) med samme navn.",
        inputs=[Port("value", ANY, 0.0, hidden=True)],
        outputs=[Port("value", ANY, label="verdi")],
        params=[Param("name", "text", "signal1", "Navn")],
        fn=_passthrough,
        width=120,
    )
)

_PIN_TYPES = (("num", "Tall"), ("bool", "Av/på"), ("str", "Tekst"), ("any", "Valgfri"))

register(
    BlockDef(
        type="macro_in",
        category="macro_io",
        title="Makro-inngang",
        symbol="IN▸",
        description="En inngang på makroblokken. Rekkefølgen på blokken følger høyden på tegningen.",
        inputs=[Port("value", ANY, 0.0, hidden=True)],
        outputs=[Port("value", ANY, label="verdi")],
        params=[
            Param("name", "text", "inn1", "Navn på pinnen"),
            Param("type", "select", "num", "Type", options=_PIN_TYPES),
            Param("default", "text", "0", "Standardverdi (når pinnen ikke er koblet)"),
        ],
        fn=_passthrough,
        width=120,
    )
)
register(
    BlockDef(
        type="macro_out",
        category="macro_io",
        title="Makro-utgang",
        symbol="▸OUT",
        description="En utgang på makroblokken. Rekkefølgen følger høyden på tegningen.",
        inputs=[Port("value", ANY, 0.0, "verdi")],
        outputs=[Port("value", ANY, hidden=True)],
        params=[
            Param("name", "text", "ut1", "Navn på pinnen"),
            Param("type", "select", "num", "Type", options=_PIN_TYPES),
        ],
        fn=_passthrough,
        width=120,
    )
)


def _parse_default(raw: Any, ptype: str) -> Any:
    if ptype == BOOL:
        return to_bool(raw)
    if ptype == NUM:
        return to_num(raw)
    if ptype == STR:
        return to_str(raw)
    if isinstance(raw, str):
        s = raw.strip()
        try:
            return float(s.replace(",", "."))
        except ValueError:
            return s
    return raw


def macro_pins(macro: dict[str, Any]) -> tuple[list[tuple[str, Port]], list[tuple[str, Port]]]:
    """Return ([(inner node id, Port)], [(inner node id, Port)]) ordered by position."""

    def collect(kind: str) -> list[tuple[str, Port]]:
        nodes = [n for n in macro.get("nodes", []) if n.get("type") == kind]
        nodes.sort(key=lambda n: (float(n.get("y", 0) or 0), float(n.get("x", 0) or 0)))
        seen: set[str] = set()
        out = []
        for n in nodes:
            p = n.get("params") or {}
            name = str(p.get("name") or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            ptype = p.get("type", "num")
            if ptype not in (BOOL, NUM, STR, ANY):
                ptype = ANY
            default = _parse_default(p.get("default", 0), ptype) if kind == "macro_in" else None
            out.append((str(n.get("id")), Port(name, ptype, default)))
        return out

    return collect("macro_in"), collect("macro_out")


def macro_blockdef(macro: dict[str, Any], lang: str | None = None) -> BlockDef:
    ins, outs = macro_pins(macro)
    longest = max([len(p.name) for _, p in ins] + [0]) + max([len(p.name) for _, p in outs] + [0])
    return BlockDef(
        type=MACRO_PREFIX + str(macro.get("id")),
        category="macro",
        title=str(macro.get("name") or tr("Makro", lang)),
        symbol=str(macro.get("symbol") or "M")[:10],
        description=str(macro.get("description") or tr("Egendefinert makroblokk.", lang)),
        inputs=[p for _, p in ins],
        outputs=[p for _, p in outs],
        fn=None,
        width=max(110, min(220, 40 + longest * 7)),
    )


# --------------------------------------------------------------------------
# KNX / Modbus
# --------------------------------------------------------------------------
KNX_BINARY = {"1.001", "1.002", "1.003", "1.008", "1.009", "1.010", "1.011", "1.017", "1.018", "1.019"}
KNX_INT = {"5.001", "5.003", "5.004", "5.010", "6.001", "6.010", "7.001", "7.012", "8.001", "12.001", "13.001", "17.001"}

_KNX_DPTS = (
    ("1.001", "1.001 Av/på"),
    ("1.008", "1.008 Opp/ned"),
    ("1.009", "1.009 Åpne/lukk"),
    ("5.001", "5.001 Prosent 0–100 %"),
    ("5.010", "5.010 Heltall 0–255"),
    ("7.001", "7.001 Heltall 0–65535"),
    ("9.001", "9.001 Temperatur °C"),
    ("9.004", "9.004 Lux"),
    ("9.007", "9.007 Fuktighet %"),
    ("9.008", "9.008 CO₂ ppm"),
    ("13.001", "13.001 Heltall 32 bit"),
    ("14.056", "14.056 Effekt W (float)"),
    ("17.001", "17.001 Scene 0–63"),
    ("custom", "Annen DPT…"),
)


def knx_dpt(p: dict[str, Any]) -> str:
    dpt = str(p.get("dpt") or "1.001").strip()
    if dpt == "custom":
        dpt = str(p.get("dpt_custom") or "").strip()
    return dpt


def knx_is_binary(dpt: str) -> bool:
    return dpt in KNX_BINARY or dpt in ("1", "binary", "switch") or dpt.startswith("1.")


def _send_gate(ctx, s: dict[str, Any], value: Any, p: dict[str, Any], enabled: bool) -> bool:
    """Change-only write with deadband, minimum interval and optional cyclic resend."""
    prev_en = s.get("en", True)
    s["en"] = enabled
    if not enabled:
        return False
    deadband = to_num(p.get("deadband", 0))
    if "last" not in s:
        need = bool(p.get("write_on_start", True))
        if not need:
            s["last"] = value
    else:
        need = _values_differ(value, s["last"], deadband) or not prev_en
    cyclic = to_num(p.get("cyclic", 0))
    if not need and cyclic > 0 and "t" in s and ctx.now - s["t"] >= cyclic:
        need = True
    if need and ctx.now - s.get("t", -1e12) >= to_num(p.get("min_interval", 0)):
        s["last"] = value
        s["t"] = ctx.now
        return True
    return False


_SEND_PARAMS = [
    Param("deadband", "number", 0, "Dødbånd", min=0),
    Param("min_interval", "number", 0, "Minste intervall (s)", min=0),
    Param("cyclic", "number", 0, "Send syklisk hvert (s, 0 = av)", min=0),
    Param("write_on_start", "bool", True, "Send ved oppstart"),
]


def knx_payload(value: Any, dpt: str) -> tuple[Any, str | None]:
    """Return (payload, type) for knx.send."""
    if knx_is_binary(dpt):
        return (1 if to_bool(value) else 0), None
    if dpt in KNX_INT:
        return int(round(to_num(value))), dpt
    return to_num(value), dpt or None


def _knx_send(ctx, i, p, s):
    address = str(p.get("address") or "").strip()
    if not address:
        return {}
    dpt = knx_dpt(p)
    value = i["value"]
    value = to_bool(value) if knx_is_binary(dpt) else to_num(value)
    if _send_gate(ctx, s, value, p, i["en"]):
        payload, typ = knx_payload(value, dpt)
        data: dict[str, Any] = {"address": address, "payload": payload}
        if typ:
            data["type"] = typ
        ctx.io.call(ctx.program_id, ctx.node_id, "knx", "send", data)
    return {}


register(
    BlockDef(
        type="knx_send",
        category="bus",
        title="KNX send",
        symbol="KNX▸",
        description=(
            "Sender verdien til en KNX-gruppeadresse (knx.send) med valgt DPT. "
            "Sender bare ved endring, med dødbånd, minste intervall og valgfri syklisk sending."
        ),
        inputs=[Port("value", ANY, 0, "verdi"), Port("en", BOOL, True, "aktiv")],
        params=[
            Param("address", "text", "", "Gruppeadresse", help="f.eks. 1/2/3"),
            Param("dpt", "select", "1.001", "Datatype (DPT)", options=_KNX_DPTS),
            Param(
                "dpt_custom",
                "text",
                "",
                "DPT / type",
                help="f.eks. 9.005 eller percent",
                show_if=("dpt", ("custom",)),
            ),
            *_SEND_PARAMS,
        ],
        fn=_knx_send,
        width=140,
    )
)


def _knx_read(ctx, i, p, s):
    address = str(p.get("address") or "").strip()
    dpt = knx_dpt(p)
    if not address:
        return {"value": 0.0, "on": False, "valid": False, "new": False}
    reg = (address, dpt)
    if s.get("_reg") != reg:
        if not ctx.io.knx_listen(address, dpt, bool(p.get("read_on_start", True))):
            raise RuntimeError(tr("KNX-integrasjonen er ikke lastet i Home Assistant"))
        s["_reg"] = reg
    tel = ctx.io.knx_value(address)
    new = False
    if tel is not None:
        value, seq = tel
        if seq != s.get("seq"):
            new = True
            s["seq"] = seq
            s["v"] = value
    has = "v" in s
    raw = s.get("v", 0)
    return {"value": to_num(raw), "on": to_bool(raw), "valid": has, "new": new and has}


register(
    BlockDef(
        type="knx_read",
        category="bus",
        title="KNX lytt",
        symbol="▸KNX",
        description=(
            "Lytter på telegrammer til en KNX-gruppeadresse (knx_event) og gir ut siste verdi. "
            "'ny' er en puls når et telegram kommer. Kan sende leseforespørsel ved oppstart."
        ),
        outputs=[
            Port("value", NUM, label="verdi"),
            Port("on", BOOL, label="på"),
            Port("valid", BOOL, label="gyldig"),
            Port("new", BOOL, label="ny"),
        ],
        params=[
            Param("address", "text", "", "Gruppeadresse", help="f.eks. 1/2/3"),
            Param("dpt", "select", "1.001", "Datatype (DPT)", options=_KNX_DPTS),
            Param("dpt_custom", "text", "", "DPT / type", show_if=("dpt", ("custom",))),
            Param("read_on_start", "bool", True, "Send leseforespørsel ved oppstart"),
        ],
        fn=_knx_read,
        retain=("v",),
        width=140,
    )
)


def modbus_registers(value: float, dtype: str, word_order: str) -> int | list[int]:
    """Encode a number as one or two 16-bit Modbus registers."""
    if dtype == "uint16":
        return int(max(0, min(65535, round(value))))
    if dtype == "int16":
        return int(max(-32768, min(32767, round(value)))) & 0xFFFF
    if dtype == "float32":
        raw = struct.pack(">f", float(value))
    elif dtype == "int32":
        raw = struct.pack(">i", int(max(-(2**31), min(2**31 - 1, round(value)))))
    else:  # uint32
        raw = struct.pack(">I", int(max(0, min(2**32 - 1, round(value)))))
    hi, lo = struct.unpack(">HH", raw)
    return [lo, hi] if word_order == "little" else [hi, lo]


def _modbus_write(ctx, i, p, s):
    hub = str(p.get("hub") or "").strip()
    if not hub:
        return {}
    kind = p.get("kind", "register")
    value = to_bool(i["value"]) if kind == "coil" else to_num(i["value"])
    if not _send_gate(ctx, s, value, p, i["en"]):
        return {}
    data: dict[str, Any] = {
        "hub": hub,
        "slave": int(to_num(p.get("slave", 1))),
        "address": int(to_num(p.get("address", 0))),
    }
    if kind == "coil":
        data["state"] = bool(value)
        ctx.io.call(ctx.program_id, ctx.node_id, "modbus", "write_coil", data)
    else:
        raw = value * to_num(p.get("scale", 1) if p.get("scale") is not None else 1)
        data["value"] = modbus_registers(raw, p.get("dtype", "int16"), p.get("word_order", "big"))
        ctx.io.call(ctx.program_id, ctx.node_id, "modbus", "write_register", data)
    return {}


register(
    BlockDef(
        type="modbus_write",
        category="bus",
        title="Modbus skriv",
        symbol="MB▸",
        description=(
            "Skriver til et holding-register eller en coil via HAs Modbus-integrasjon "
            "(modbus.write_register / write_coil). Råverdi = verdi × skala. Les Modbus-verdier "
            "med «Les entitet» mot en Modbus-sensor."
        ),
        inputs=[Port("value", ANY, 0, "verdi"), Port("en", BOOL, True, "aktiv")],
        params=[
            Param("hub", "text", "modbus_hub", "Hub (navn i modbus-oppsettet)"),
            Param("slave", "number", 1, "Enhetsadresse (slave)", min=0, max=255, step=1),
            Param("address", "number", 0, "Registeradresse", min=0, max=65535, step=1),
            Param(
                "kind",
                "select",
                "register",
                "Type",
                options=(("register", "Holding-register"), ("coil", "Coil")),
            ),
            Param(
                "dtype",
                "select",
                "int16",
                "Datatype",
                options=(
                    ("int16", "int16"),
                    ("uint16", "uint16"),
                    ("int32", "int32 (2 reg.)"),
                    ("uint32", "uint32 (2 reg.)"),
                    ("float32", "float32 (2 reg.)"),
                ),
                show_if=("kind", ("register",)),
            ),
            Param(
                "word_order",
                "select",
                "big",
                "Ordrekkefølge (32 bit)",
                options=(("big", "Høy først (big)"), ("little", "Lav først (swap)")),
                show_if=("kind", ("register",)),
            ),
            Param("scale", "number", 1, "Skala", show_if=("kind", ("register",))),
            *_SEND_PARAMS,
        ],
        fn=_modbus_write,
        width=140,
    )
)


def library_json(macros: dict[str, dict[str, Any]] | None = None, lang: str = "nb") -> dict[str, Any]:
    """The block library for the panel, in Norwegian ('nb') or English ('en').

    Only the built-in texts are translated; names and descriptions of the user's macros are kept.
    """
    blocks = [translate_block(b.to_json(), lang) for b in LIBRARY.values()]
    for macro in (macros or {}).values():
        blocks.append(macro_blockdef(macro, lang).to_json())
    return {
        "categories": [{"id": cid, "title": tr(title, lang)} for cid, title in CATEGORIES],
        "blocks": blocks,
    }
