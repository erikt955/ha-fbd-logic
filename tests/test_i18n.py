"""Language support: Norwegian for nb/nn/no, English for every other language, and no text left out."""

import re
from pathlib import Path

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.fbd_logic.blocks import library_json
from custom_components.fbd_logic.const import DOMAIN, MODEL, PANEL_TITLE
from custom_components.fbd_logic.i18n import language_for
from custom_components.fbd_logic.i18n_en import EN, SAME

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "fbd_logic"
NORWEGIAN = re.compile(r"[æøåÆØÅ]")
STRING = r'"((?:[^"\\]|\\.)*)"'


def _texts(block):
    yield block["title"]
    yield block["description"]
    for port in block["inputs"] + block["outputs"]:
        yield port["label"]
    for param in block["params"]:
        yield param["label"]
        if param.get("help"):
            yield param["help"]
        for opt in (param.get("options") or []) + (param.get("suggest") or []):
            yield opt["label"]


def test_language_choice() -> None:
    assert {language_for(c) for c in ("nb", "nn", "no", "nb-NO", "NB")} == {"nb"}
    assert {language_for(c) for c in ("en", "en-GB", "de", "sv", "da", None, "")} == {"en"}


def test_every_library_text_has_english() -> None:
    lib = library_json()
    texts = [t for b in lib["blocks"] for t in _texts(b)] + [c["title"] for c in lib["categories"]]
    missing = sorted({t for t in texts if t and t not in EN and t not in SAME})
    assert not missing, missing


def test_english_library() -> None:
    lib = library_json(lang="en")
    bad = [t for b in lib["blocks"] for t in _texts(b) if t and NORWEGIAN.search(t)]
    bad += [c["title"] for c in lib["categories"] if NORWEGIAN.search(c["title"])]
    assert not bad, bad
    blocks = {b["type"]: b for b in lib["blocks"]}
    assert blocks["pid"]["title"] == "PID controller"
    params = {p["name"]: p for p in blocks["setpoint"]["params"]}
    assert params["name"]["default"] == "Setpoint"  # default names of new blocks are translated
    params = {p["name"]: p for p in blocks["entity_out"]["params"]}
    assert params["action"]["default"] == "auto"  # select values never are
    assert library_json() == library_json(lang="nb")


def test_user_macros_keep_their_texts() -> None:
    macro = {"id": "m1", "name": "Puls", "description": "Min egen", "nodes": [], "links": []}
    blocks = {b["type"]: b for b in library_json({"m1": macro}, "en")["blocks"]}
    assert (blocks["macro:m1"]["title"], blocks["macro:m1"]["description"]) == ("Puls", "Min egen")
    blocks = {b["type"]: b for b in library_json({"m2": {"id": "m2", "nodes": [], "links": []}}, "en")["blocks"]}
    assert blocks["macro:m2"]["title"] == "Macro"


def test_every_tr_call_has_english() -> None:
    calls = []
    for path in COMPONENT.glob("*.py"):
        calls += re.findall(r"\btr\(\s*" + STRING, path.read_text(encoding="utf-8"))
    assert len(calls) > 40
    missing = sorted({c for c in calls if c not in EN})
    assert not missing, missing
    assert MODEL in EN and PANEL_TITLE in EN  # passed to tr() by name


def test_every_panel_text_has_english() -> None:
    src = (COMPONENT / "frontend" / "fbd-panel.js").read_text(encoding="utf-8")
    start, end = src.index("const EN = {"), src.index("/* eslint-enable quote-props */")
    catalog = dict(re.findall(r"^\s*" + STRING + r": " + STRING + r",$", src[start:end], re.M))
    code = src[:start] + src[end:]
    used = re.findall(r'\btn?\(\s*(?:[^,()"]+,\s*)?' + STRING, code)  # t("x") and the first form of tn(n, ...)
    used += re.findall(r'\btn\([^"\n)]*"[^"\n]*",\s*' + STRING, code)  # the plural form of tn()
    assert len(used) > 150
    missing = sorted({u for u in used if u not in catalog})
    assert not missing, missing
    assert not [v for v in catalog.values() if NORWEGIAN.search(v)]
    # Outside t(), Norwegian letters only appear in the Norwegian day names and in input/file name patterns
    allowed = ("DAY_NAMES_NB", "æøåÆØÅ", "på|on")
    stray = [
        line.strip()
        for line in code.splitlines()
        if NORWEGIAN.search(line) and not re.search(r"\btn?\(", line) and not any(a in line for a in allowed)
    ]
    assert not stray, stray


def test_example_programs_compile() -> None:
    import json

    from custom_components.fbd_logic.engine import Program

    examples = sorted((COMPONENT.parents[1] / "examples").glob("*.fbd.json"))
    assert len(examples) >= 2
    for path in examples:
        prog = Program(json.loads(path.read_text(encoding="utf-8")))
        prog.step(0)
        assert not prog.warnings, (path.name, prog.warnings)


async def test_english_installation(hass: HomeAssistant, hass_ws_client) -> None:
    hass.config.language = "en"
    entry = MockConfigEntry(domain=DOMAIN, title="FBD Logic", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)

    # The block library follows the panel's language, else the system language
    for language, title in ((None, "PID controller"), ("nb", "PID-regulator"), ("en-GB", "PID controller")):
        msg = {"type": "fbd_logic/blocks"} | ({"language": language} if language else {})
        await client.send_json_auto_id(msg)
        res = await client.receive_json()
        assert {b["type"]: b for b in res["result"]["blocks"]}["pid"]["title"] == title

    # Save warnings and websocket errors follow the system language
    prog = {
        "id": "en",
        "name": "Fan",
        "nodes": [
            {"id": "k", "type": "const_num", "params": {"value": 1}},
            {"id": "p", "type": "publish", "x": 200, "params": {"name": "Temp", "device_class": "temperature"}},
            {"id": "r", "type": "page_in", "y": 100, "params": {"name": "nowhere"}},
        ],
        "links": [{"id": "a", "from": "k", "from_port": "out", "to": "p", "to_port": "value"}],
    }
    await client.send_json_auto_id({"type": "fbd_logic/program/save", "program": prog})
    res = await client.receive_json()
    assert res["success"], res
    await hass.async_block_till_done()
    warnings = res["result"]["warnings"]
    assert any("does not fit" in w for w in warnings), warnings
    assert any("has no sender" in w for w in warnings), warnings
    await client.send_json_auto_id({"type": "fbd_logic/program/get", "program_id": "nope"})
    res = await client.receive_json()
    assert res["error"]["message"] == "The program does not exist"

    # The program switch is named from translations/en.json
    switch = er.async_get(hass).async_get_entity_id("switch", DOMAIN, "en_enabled")
    assert switch == "switch.fan_running"
    assert hass.states.get(switch).attributes["friendly_name"] == "Fan Running"


async def test_norwegian_installation(hass: HomeAssistant, hass_ws_client) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="FBD Logic", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "fbd_logic/program/save", "program": {"id": "v", "name": "Vifte", "nodes": []}})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    switch = er.async_get(hass).async_get_entity_id("switch", DOMAIN, "v_enabled")
    assert switch == "switch.vifte_kjorer"
    assert hass.states.get(switch).attributes["friendly_name"] == "Vifte Kjører"
