"""Headless browser test of the editor panel against a mocked HA connection."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tests" / "ui" / "out"
OUT.mkdir(exist_ok=True)


def find_browser():
    """Chrome/Edge executable: FBD_CHROME env, else a known install path."""
    candidates = [
        os.environ.get("FBD_CHROME"),
        "/usr/bin/google-chrome",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None  # fall back to Playwright's bundled Chromium

server = subprocess.Popen(
    [sys.executable, "-m", "http.server", "8765", "--bind", "127.0.0.1"],
    cwd=ROOT,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
time.sleep(0.8)
errors = []


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("  ok:", msg)


try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=find_browser(), args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1400, "height": 860})
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" and "404" not in m.text else None)
        page.on("response", lambda r: errors.append(f"404: {r.url}") if r.status == 404 and not r.url.endswith("favicon.ico") else None)

        # ------------------------------------------------------------ empty start
        print("1. Empty start")
        page.goto("http://127.0.0.1:8765/tests/ui/index.html")
        root = page.locator("fbd-logic-panel")
        page.wait_for_selector("fbd-logic-panel >> .palette .item")
        n_items = root.locator(".palette .item").count()
        check(n_items == 58, f"palette shows all blocks except macro pins ({n_items})")
        check(root.locator('.palette .item[data-type="macro_in"]').count() == 0, "macro pins hidden outside macro mode")
        fit = page.evaluate(
            "() => [window.__panel.getBoundingClientRect().height, innerHeight, document.scrollingElement.scrollHeight]"
        )
        check(abs(fit[0] - fit[1]) < 2 and fit[2] <= fit[1] + 1, f"panel fills the viewport without page scroll ({fit})")
        page.screenshot(path=str(OUT / "01_empty.png"))

        # ------------------------------------------------------------ add blocks
        print("2. Add blocks by click and by drag")
        root.locator('.palette .item[data-type="entity_in"]').click()
        page.wait_for_timeout(120)
        check(root.locator("[data-node]").count() == 1, "click adds a block")
        # drag & drop from palette
        canvas = root.locator(".canvas-wrap")
        cb = canvas.bounding_box()
        root.locator('.palette .item[data-type="gt"]').drag_to(canvas, target_position={"x": 480, "y": 200})
        page.wait_for_timeout(120)
        check(root.locator("[data-node]").count() == 2, "drag from palette adds a block")
        root.locator('.palette .item[data-type="entity_out"]').drag_to(canvas, target_position={"x": 720, "y": 220})
        page.wait_for_timeout(120)
        check(root.locator("[data-node]").count() == 3, "third block added")

        nodes = page.evaluate("() => window.__panel._prog.nodes.map(n => [n.id, n.type])")
        ids = {t: i for i, t in nodes}

        # ------------------------------------------------------------ properties
        print("3. Edit properties")
        root.locator(f'[data-node="{ids["entity_in"]}"] .blk-body').click(force=True)
        page.wait_for_timeout(120)
        ent = root.locator('.props input[data-f="param:entity_id"]')
        ent.fill("sensor.romtemp")
        ent.dispatch_event("change")
        page.wait_for_timeout(100)
        hint = root.locator(".props [data-enthint]").inner_text()
        check("Romtemperatur stue" in hint and "22.8" in hint, f"entity hint shows friendly name/state ({hint})")
        info = root.locator(f'[data-node="{ids["entity_in"]}"] .blk-info').text_content()
        check("Romtemperatur" in info, "block shows friendly name")

        root.locator(f'[data-node="{ids["gt"]}"] .blk-body').click(force=True)
        page.wait_for_timeout(120)
        const_b = root.locator('.props input[data-f="const:b"]')
        const_b.fill("21.5")
        const_b.dispatch_event("change")
        root.locator(f'[data-node="{ids["entity_out"]}"] .blk-body').click(force=True)
        page.wait_for_timeout(120)
        eo = root.locator('.props input[data-f="param:entity_id"]')
        eo.fill("light.gang")
        eo.dispatch_event("change")

        # ------------------------------------------------------------ connect wires
        print("4. Connect wires by dragging pins")

        def box(sel, pg=None):
            pg = pg or page
            pg.wait_for_timeout(60)
            return pg.evaluate(
                """(sel) => { const el = window.__panel.shadowRoot.querySelector(sel);
                if (!el) return null; const r = el.getBoundingClientRect();
                return {x: r.x, y: r.y, width: r.width, height: r.height}; }""",
                sel,
            )

        def drag_pin(src, dst):
            a = box(f'[data-port="{src}"]')
            b = box(f'[data-port="{dst}"]')
            page.mouse.move(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2)
            page.mouse.down()
            page.mouse.move((a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2, steps=5)
            page.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, steps=5)
            page.mouse.up()
            page.wait_for_timeout(50)

        drag_pin(f'{ids["entity_in"]}|out|value', f'{ids["gt"]}|in|a')
        drag_pin(f'{ids["gt"]}|out|q', f'{ids["entity_out"]}|in|value')
        links = page.evaluate("() => window.__panel._prog.links")
        check(len(links) == 2, f"two links created ({len(links)})")
        check({(l["from_port"], l["to_port"]) for l in links} == {("value", "a"), ("q", "value")}, "links have correct ports")
        # reverse drag (input -> output) replaces existing link on the input
        drag_pin(f'{ids["entity_in"]}|out|valid', f'{ids["gt"]}|in|a')
        links = page.evaluate("() => window.__panel._prog.links")
        check(len(links) == 2 and any(l["from_port"] == "valid" for l in links), "new wire replaces old wire on same input")
        page.keyboard.press("Control+z")
        page.wait_for_timeout(120)
        links = page.evaluate("() => window.__panel._prog.links")
        check(any(l["from_port"] == "value" for l in links), "undo restores previous wire")

        # ------------------------------------------------------------ move block
        print("5. Move a block (snap to grid)")
        before = page.evaluate(f"() => window.__panel._prog.nodes.find(n => n.id === '{ids['gt']}')")
        bb = box(f'[data-node="{ids['gt']}"] .blk-body')
        page.mouse.move(bb["x"] + 30, bb["y"] + 10)
        page.mouse.down()
        page.mouse.move(bb["x"] + 30 + 57, bb["y"] + 10 + 33, steps=6)
        page.mouse.up()
        after = page.evaluate(f"() => window.__panel._prog.nodes.find(n => n.id === '{ids['gt']}')")
        check(after["x"] - before["x"] in (50, 60) and after["y"] - before["y"] in (30, 40), f"moved and snapped ({after['x']-before['x']},{after['y']-before['y']})")
        check(after["x"] % 10 == 0 and after["y"] % 10 == 0, "position on grid")

        # ------------------------------------------------------------ save
        print("6. Save program")
        root.locator('input.name').fill("Testprogram")
        root.locator('input.name').dispatch_event("change")
        root.locator('.toolbar > [data-act="save"]').click()
        page.wait_for_timeout(120)
        page.wait_for_function("() => window.__saved.length === 1")
        saved = page.evaluate("() => window.__saved[0]")
        check(saved["name"] == "Testprogram" and len(saved["nodes"]) == 3, "save payload correct")
        page.wait_for_function("() => window.__subs() === 1")
        check(True, "online subscription started after first save")
        page.wait_for_timeout(500)
        vals = page.evaluate("() => [...window.__panel.shadowRoot.querySelectorAll('.val')].filter(e => e.textContent).length")
        check(vals >= 5, f"live values rendered on outputs ({vals})")
        page.screenshot(path=str(OUT / "02_small_program_online.png"))
        (OUT / "saved_payload.json").write_text(json.dumps(saved, indent=1, ensure_ascii=False))

        # ------------------------------------------------------------ copy/paste/delete/box select
        print("7. Copy/paste, box select, delete")
        root.locator(f'[data-node="{ids["gt"]}"] .blk-body').click(force=True)
        page.wait_for_timeout(120)
        page.keyboard.press("Control+c")
        page.wait_for_timeout(120)
        page.keyboard.press("Control+v")
        page.wait_for_timeout(120)
        check(root.locator("[data-node]").count() == 4, "paste duplicates block")
        page.keyboard.press("Delete")
        page.wait_for_timeout(120)
        check(root.locator("[data-node]").count() == 3, "delete removes pasted block")
        # box select everything
        r = box(".canvas-wrap")
        page.keyboard.down("Shift")
        page.mouse.move(r["x"] + 5, r["y"] + 5)
        page.mouse.down()
        page.mouse.move(r["x"] + r["width"] - 10, r["y"] + r["height"] - 50, steps=8)
        page.mouse.up()
        page.keyboard.up("Shift")
        nsel = page.evaluate("() => window.__panel._sel.size")
        check(nsel == 3, f"box select picks all blocks ({nsel})")
        check("3 blokker valgt" in root.locator(".props h3").inner_text(), "props shows multi selection")
        page.keyboard.press("Escape")
        page.wait_for_timeout(120)

        # ------------------------------------------------------------ dynamic inputs
        print("8. Dynamic input count")
        root.locator('.palette .item[data-type="and"]').click()
        page.wait_for_timeout(120)
        and_id = page.evaluate("() => [...window.__panel._sel][0]")
        n_field = root.locator('.props input[data-f="param:n"]')
        n_field.fill("4")
        n_field.dispatch_event("change")
        page.wait_for_timeout(80)
        ports = root.locator(f'[data-port^="{and_id}|in|"]').count()
        check(ports == 4, f"AND block shows 4 inputs ({ports})")

        # ------------------------------------------------------------ load example
        print("9. Load full example program")
        page.goto("http://127.0.0.1:8765/tests/ui/index.html?preload=example.json")
        page.wait_for_selector("fbd-logic-panel >> [data-node]")
        page.wait_for_timeout(700)
        check(root.locator("[data-node]").count() == 16, "example renders 16 blocks")
        check(root.locator("path.wire").count() == 14, "example renders 14 wires")
        check(root.locator(".blk.err").count() == 1, "write error is highlighted on block")
        page.screenshot(path=str(OUT / "03_example_online.png"))
        root.locator('[data-node="pid"] .blk-body').click(force=True)
        page.wait_for_timeout(120)
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "04_pid_selected.png"))
        live = root.locator('.props [data-live="pid|o|out"]').inner_text()
        check(live not in ("", "–"), f"props shows live output value ({live})")
        pid_ports = [root.locator(f'[data-port="pid|in|{x}"]').count() for x in ("man", "mv", "bias")]
        check(pid_ports == [1, 1, 1], f"PID shows manual, manual value and working point inputs ({pid_ports})")
        check(root.locator('[data-port="pid|out|auto"]').count() == 1, "PID shows the auto output")
        db = root.locator('.props input[data-f="param:deadband"]')
        check(db.count() == 1 and float(db.input_value()) == 0, "PID has a deadband field (default 0)")
        db.fill("0.5")
        db.dispatch_event("change")
        page.wait_for_timeout(150)
        sub = root.locator('g.blk[data-node="pid"] .blk-info').text_content()
        check("Revers" in sub and ("±0,5" in sub or "±0.5" in sub), f"PID subtitle shows direction and deadband ({sub!r})")
        db.fill("0")
        db.dispatch_event("change")
        page.wait_for_timeout(100)
        # wire selection
        root.locator('[data-node="spjeld"] .blk-body').click(force=True)
        page.wait_for_timeout(120)
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "05_entity_out_props.png"))
        # Setpoint live set
        root.locator('[data-node="sp"] .blk-body').click(force=True)
        page.wait_for_timeout(120)
        root.locator('.props [data-liveinput="sp"]').fill("22.5")
        root.locator('.props [data-act="set-live"]').click()
        page.wait_for_timeout(120)
        page.wait_for_timeout(400)
        check(page.evaluate("() => window.__wsLog.includes('fbd_logic/set_value')"), "setpoint can be set from panel")

        # zoom / fit
        root.locator('[data-act="zoom-out"]').click()
        page.wait_for_timeout(120)
        k1 = page.evaluate("() => window.__panel._view.k")
        root.locator('[data-act="fit"]').click()
        page.wait_for_timeout(120)
        k2 = page.evaluate("() => window.__panel._view.k")
        check(k1 != k2, "zoom and fit change view")

        # offline toggle stops subscription
        root.locator('[data-act="online"]').click()
        page.wait_for_timeout(120)
        page.wait_for_timeout(100)
        check(page.evaluate("() => window.__subs()") == 0, "offline mode unsubscribes")
        check(page.evaluate("() => [...window.__panel.shadowRoot.querySelectorAll('.val')].filter(e => e.textContent).length") == 0, "no live values offline")
        root.locator('[data-act="online"]').click()
        page.wait_for_timeout(120)
        page.wait_for_timeout(400)

        # unsaved changes guard on new program
        root.locator('[data-node="hyst"] .blk-body').click(force=True)
        page.wait_for_timeout(120)
        page.keyboard.press("Delete")
        page.wait_for_timeout(120)
        root.locator('.toolbar > [data-act="new"]').click()
        page.wait_for_timeout(120)
        root.locator('.newmenu [data-act="new-program"]').click()
        page.wait_for_timeout(120)
        page.wait_for_selector("fbd-logic-panel >> .modal")
        page.screenshot(path=str(OUT / "06_discard_dialog.png"))
        root.locator(".modal .cancel").click()
        page.wait_for_timeout(120)
        check(root.locator("[data-node]").count() == 15, "cancel keeps current program")

        # ------------------------------------------------------------ dark + narrow
        print("10. Dark theme and phone layout")
        page.goto("http://127.0.0.1:8765/tests/ui/index.html?preload=example.json&dark=1")
        page.wait_for_selector("fbd-logic-panel >> [data-node]")
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUT / "07_dark.png"))
        phone = browser.new_page(viewport={"width": 390, "height": 800}, has_touch=True, is_mobile=True)
        phone.on("pageerror", lambda e: errors.append(f"pageerror(phone): {e}"))
        phone.goto("http://127.0.0.1:8765/tests/ui/index.html?preload=example.json&narrow=1")
        phone.wait_for_selector("fbd-logic-panel >> [data-node]")
        phone.wait_for_timeout(600)
        proot = phone.locator("fbd-logic-panel")
        check(not proot.locator(".palette").is_visible(), "palette hidden on phone by default")
        phone.screenshot(path=str(OUT / "08_phone.png"))
        tb = phone.evaluate("() => window.__panel.shadowRoot.querySelector('.toolbar').getBoundingClientRect().height")
        check(tb < 60, f"phone toolbar is a single row ({tb:.0f}px)")
        proot.locator('.toolbar > [data-act="more"]').click()
        phone.wait_for_timeout(150)
        phone.screenshot(path=str(OUT / "08b_phone_menu.png"))
        proot.locator('.moremenu [data-act="program-settings"]').click()
        phone.wait_for_timeout(150)
        check(proot.locator(".props").is_visible() and "Program" in proot.locator(".props h3").inner_text(), "program settings reachable from menu")
        proot.locator('[data-act="toggle-props"]').click()
        phone.wait_for_timeout(100)
        proot.locator('[data-act="toggle-palette"]').click()
        phone.wait_for_timeout(120)
        phone.wait_for_timeout(200)
        phone.screenshot(path=str(OUT / "09_phone_palette.png"))
        proot.locator('.palette .item[data-type="ton"]').click()
        phone.wait_for_timeout(120)
        check(proot.locator("[data-node]").count() == 17, "tap on palette adds block on phone")
        phone.close()

        # ------------------------------------------------------------ 0.2 features
        def props_change(sel, value):
            el = root.locator(f".props {sel}")
            el.fill(value)
            el.dispatch_event("change")
            page.wait_for_timeout(80)

        def select_node(nid):
            root.locator(f'[data-node="{nid}"] .blk-body').click(force=True)
            page.wait_for_timeout(150)

        print("11. MUX / PRIO dynamic ports")
        page.goto("http://127.0.0.1:8765/tests/ui/index.html")
        page.wait_for_selector("fbd-logic-panel >> .palette .item")
        root.locator('.palette .item[data-type="mux"]').click()
        page.wait_for_timeout(120)
        mux = page.evaluate("() => [...window.__panel._sel][0]")
        ports = page.evaluate(f"() => [...window.__panel.shadowRoot.querySelectorAll('[data-port^=\"{mux}|in|\"]')].map(e => e.dataset.port.split('|')[2])")
        check(ports == ["k", "in0", "in1", "in2"], f"MUX ports k, in0.. ({ports})")
        root.locator('.palette .item[data-type="prio"]').click()
        page.wait_for_timeout(120)
        prio = page.evaluate("() => [...window.__panel._sel][0]")
        ports = page.evaluate(f"() => [...window.__panel.shadowRoot.querySelectorAll('[data-port^=\"{prio}|in|\"]')].map(e => e.dataset.port.split('|')[2])")
        check(ports[:2] == ["g1", "in1"] and ports[-1] == "else", f"PRIO pairs + else ({ports})")

        print("12. Weekly schedule editor")
        root.locator('.palette .item[data-type="schedule"]').click()
        page.wait_for_timeout(120)
        sid = page.evaluate("() => [...window.__panel._sel][0]")
        info = root.locator(f'[data-node="{sid}"] .blk-info').text_content()
        check(info.startswith("Ma–Fr 07:00–16:00"), f"schedule summary on block ({info})")
        root.locator('.props [data-act="sched-day"][data-i="0"][data-d="6"]').click()
        page.wait_for_timeout(80)
        root.locator('.props [data-act="sched-add"]').click()
        page.wait_for_timeout(80)
        props_change('input[data-f="sched:1:off"]', "02:30")
        periods = page.evaluate(f"() => window.__panel._node('{sid}').params.periods")
        check(periods[0]["days"] == [1, 2, 3, 4, 5, 6] and len(periods) == 2 and periods[1]["off"] == "02:30", f"periods edited ({periods})")
        page.screenshot(path=str(OUT / "10_schedule.png"))

        print("12b. Publish: device class suggestions")
        root.locator('.palette .item[data-type="publish"]').click()
        page.wait_for_timeout(120)
        pid_pub = page.evaluate("() => [...window.__panel._sel][0]")
        lst = root.locator('.props input[data-f="param:device_class"]').get_attribute("list")
        opts = page.evaluate(
            "(id) => [...window.__panel.shadowRoot.getElementById(id).options].map(o => o.value)", lst
        )
        check("temperature" in opts and "window" in opts, f"device class field suggests HA names ({len(opts)} forslag)")
        props_change('input[data-f="param:device_class"]', "temperature")
        dc = page.evaluate(f"() => window.__panel._node('{pid_pub}').params.device_class")
        check(dc == "temperature", f"device class stored ({dc})")
        for f, want in (("deadband", 0), ("min_interval", 0)):
            el = root.locator(f'.props input[data-f="param:{f}"]')
            check(el.count() == 1 and float(el.input_value()) == want, f"publish has {f} (default {want})")

        print("12c. Program setting: scan on input change")
        page.evaluate("() => { const p = window.__panel; p._sel.clear(); p._selLink = null; p._renderProps(); }")
        ev = root.locator('.props input[data-f="prog:event_scan"]')
        check(ev.is_checked(), "scan on input change is on by default")
        ev.uncheck()
        page.wait_for_timeout(80)
        off = page.evaluate("() => window.__panel._prog.event_scan")
        root.locator('.props input[data-f="prog:event_scan"]').check()
        page.wait_for_timeout(80)
        on = page.evaluate("() => window.__panel._prog.event_scan")
        check(off is False and on is True, f"setting can be switched off and on ({off}, {on})")

        print("13. Pages")
        before = root.locator("[data-node]").count()
        root.locator('.pages [data-act="page-add"]').click()
        page.wait_for_timeout(150)
        check(root.locator("[data-node]").count() == 0, "new page is empty")
        root.locator('.palette .item[data-type="page_in"]').click()
        page.wait_for_timeout(120)
        check(root.locator("[data-node]").count() == 1, "block added on page 2")
        root.locator('.pages [data-page="p1"]').click()
        page.wait_for_timeout(150)
        check(root.locator("[data-node]").count() == before, "page 1 shows its own blocks")
        select_node(mux)
        root.locator('.props select[data-f="move-page"]').select_option("p2")
        page.wait_for_timeout(150)
        check(root.locator("[data-node]").count() == before - 1, "move block to another page")
        root.locator('.toolbar > [data-act="save"]').click()
        page.wait_for_function("() => window.__saved.length === 1")
        saved = page.evaluate("() => window.__saved[0]")
        check(len(saved["pages"]) == 2 and sum(1 for n in saved["nodes"] if n["page"] == "p2") == 2, "pages saved with nodes")
        check(saved.get("event_scan") is True, "event scan setting saved with the program")

        print("14. Force and trend on example")
        page.goto("http://127.0.0.1:8765/tests/ui/index.html?preload=example.json")
        page.wait_for_selector("fbd-logic-panel >> [data-node]")
        page.wait_for_timeout(600)
        select_node("temp")
        page.wait_for_timeout(400)
        root.locator('.props [data-fzin="value"]').fill("30")
        root.locator('.props [data-act="force-set"][data-port="value"]').click()
        page.wait_for_timeout(900)
        check(page.evaluate("() => window.__forces.eksempel_rom && window.__forces.eksempel_rom.temp.value") == 30, "force sent to backend")
        txt = root.locator('[data-v="temp|value"]').text_content()
        check(txt.startswith("F "), f"forced value marked on canvas ({txt})")
        check("tvangsstyrt" in root.locator(".status").inner_text(), "status shows forced count")
        page.screenshot(path=str(OUT / "11_forced.png"))
        root.locator('.props [data-act="force-release"][data-port="value"]').click()
        page.wait_for_timeout(900)
        check(not page.evaluate("() => window.__forces.eksempel_rom && window.__forces.eksempel_rom.temp"), "force released")
        root.locator('.props [data-act="trend-add"][data-sig="temp|value"]').click()
        page.wait_for_timeout(400)
        root.locator('[data-act="fit"]').click()  # the trend pane took space from the canvas
        page.wait_for_timeout(200)
        select_node("or")
        root.locator('.props [data-act="trend-add"][data-sig="or|q"]').click()
        page.wait_for_timeout(1500)
        check(root.locator(".trend").is_visible(), "trend pane opens")
        check(root.locator(".trend path.line").count() == 2, "two trend lanes drawn")
        tb = box(".trend svg")
        page.mouse.move(tb["x"] + tb["width"] * 0.6, tb["y"] + 30)
        page.wait_for_timeout(150)
        check(root.locator(".trend .tip").is_visible(), "trend crosshair tooltip")
        page.screenshot(path=str(OUT / "12_trend.png"))
        root.locator('.trend [data-act="trend-rm"]').first.click()
        page.wait_for_timeout(300)
        check(root.locator(".trend path.line").count() == 1, "remove signal from trend")
        page.set_viewport_size({"width": 980, "height": 860})
        page.wait_for_timeout(1300)
        narrow = page.evaluate(
            """() => { const L = window.__panel._trendL; const sr = window.__panel.shadowRoot;
            const s = sr.querySelector('.trend svg').getBoundingClientRect();
            const rm = sr.querySelector('.trend [data-act="trend-rm"]').getBoundingClientRect();
            return {compact: L.compact, x0: L.X0, x1: L.X1, sw: s.width, rm: rm.right - s.x}; }"""
        )
        check(
            narrow["compact"] and narrow["x0"] <= 40 and narrow["x1"] <= narrow["sw"] and narrow["rm"] <= narrow["sw"] + 1,
            f"narrow trend puts labels above the lane ({narrow})",
        )
        short = page.evaluate("() => window.__panel._sigLabelShort('temp|value', 8)")
        check(short.endswith(".verdi"), f"short trend label keeps the port name ({short})")
        page.screenshot(path=str(OUT / "12b_trend_narrow.png"))
        page.set_viewport_size({"width": 1400, "height": 860})
        page.wait_for_timeout(300)

        print("15. Macros")
        root.locator('.toolbar > [data-act="new"]').click()
        page.wait_for_timeout(100)
        root.locator('.newmenu [data-act="new-macro"]').click()
        page.wait_for_timeout(200)
        if root.locator(".modal").count():
            root.locator(".modal .ok").click()
            page.wait_for_timeout(200)
        check(root.locator('.palette .item[data-type="macro_in"]').count() == 1, "macro pins in palette in macro mode")
        check(root.locator(".progonly").first.is_hidden(), "interval hidden in macro mode")
        m_in, m_out = page.evaluate("() => window.__panel._prog.nodes.map(n => n.id)")
        root.locator('.palette .item[data-type="not"]').click()
        page.wait_for_timeout(120)
        not_id = page.evaluate("() => [...window.__panel._sel][0]")
        drag_pin(f"{m_in}|out|value", f"{not_id}|in|in")
        drag_pin(f"{not_id}|out|q", f"{m_out}|in|value")
        root.locator('input.name').fill("Inverter")
        root.locator('input.name').dispatch_event("change")
        root.locator('.toolbar > [data-act="save"]').click()
        page.wait_for_timeout(400)
        mids = page.evaluate("() => Object.keys(window.__macros)")
        check(len(mids) == 1, "macro saved")
        check(root.locator(f'.palette .item[data-type="macro:{mids[0]}"]').count() == 0, "macro does not list itself")
        page.screenshot(path=str(OUT / "13_macro_edit.png"))
        root.locator(".progsel").select_option("eksempel_rom")
        page.wait_for_timeout(600)
        root.locator(f'.palette .item[data-type="macro:{mids[0]}"]').click()
        page.wait_for_timeout(150)
        inst = page.evaluate("() => [...window.__panel._sel][0]")
        check(root.locator(f'[data-port="{inst}|in|inn1"]').count() == 1, "macro instance has its pin")
        check(root.locator('.props [data-act="open-macro"]').count() == 1, "instance offers 'open macro'")
        # make macro from selection: hyst + or
        root.locator('[data-node="hyst"] .blk-body').click(force=True)
        root.locator('[data-node="or"] .blk-body').click(force=True, modifiers=["Shift"])
        page.wait_for_timeout(150)
        root.locator('.props [data-act="make-macro"]').click()
        page.wait_for_selector("fbd-logic-panel >> .modal")
        root.locator(".modal input").fill("Hysterese+ELLER")
        root.locator(".modal .ok").click()
        page.wait_for_timeout(600)
        check(len(page.evaluate("() => Object.keys(window.__macros)")) == 2, "macro created from selection")
        nodes = page.evaluate("() => window.__panel._prog.nodes.map(n => n.id)")
        check("hyst" not in nodes and "or" not in nodes, "selection replaced by instance")
        new_inst = page.evaluate("() => [...window.__panel._sel][0]")
        links = page.evaluate(f"() => window.__panel._prog.links.filter(l => l.to === '{new_inst}' || l.from === '{new_inst}').length")
        check(links >= 3, f"external wires reconnected to the instance ({links})")
        page.screenshot(path=str(OUT / "14_macro_from_selection.png"))
        # live view inside the instance after saving
        root.locator('.toolbar > [data-act="save"]').click()
        page.wait_for_timeout(500)
        root.locator('.props [data-act="open-macro-live"]').click()
        page.wait_for_timeout(900)
        check(root.locator(".banner").is_visible() and "Live" in root.locator(".banner").inner_text(), "live macro banner")
        vals = page.evaluate("() => [...window.__panel.shadowRoot.querySelectorAll('.val')].filter(e => e.textContent).length")
        check(vals >= 2, f"live values inside macro ({vals})")
        page.screenshot(path=str(OUT / "15_macro_live.png"))
        root.locator('.banner [data-act="back-live"]').click()
        page.wait_for_timeout(500)
        check(page.evaluate("() => window.__panel._kind") == "program", "back to program from live macro")

        # ------------------------------------------------------------ English
        print("16. English (HA language other than Norwegian)")
        page.evaluate("() => localStorage.clear()")
        page.goto("http://127.0.0.1:8765/tests/ui/index.html?lang=en")
        page.wait_for_selector("fbd-logic-panel >> .palette .item")
        page.wait_for_timeout(300)
        blocks_msg = page.evaluate("() => window.__wsMsgs.find((m) => m.type === 'fbd_logic/blocks')")
        check(blocks_msg and blocks_msg.get("language") == "en", f"panel asks for the English library ({blocks_msg})")
        check(root.locator('.toolbar > [data-act="save"]').inner_text().strip() == "Save", "toolbar in English")
        cats = root.locator(".palette summary").all_text_contents()  # shown in upper case by CSS
        check("Logic" in cats and "Control" in cats, f"palette categories in English ({cats[:4]})")
        check(page.evaluate("() => window.__panel._prog.name") == "New program", "new program gets an English name")
        root.locator('.palette .item[data-type="pid"]').click()
        page.wait_for_timeout(150)
        check(root.locator(".props h3").inner_text() == "PID controller", "block title in English")
        sub = root.locator("g.blk .blk-info").first.text_content()
        check(sub == "Reverse", f"block info line in English ({sub!r})")
        status = root.locator(".status").inner_text()
        check("Not saved yet" in status and "1 block" in status, f"status bar in English ({status!r})")
        visible = page.evaluate("() => window.__panel.shadowRoot.querySelector('.app').innerText")
        leftovers = sorted({c for c in visible if c in "æøåÆØÅ"})
        check(not leftovers, f"no Norwegian letters in the English panel ({leftovers})")
        page.screenshot(path=str(OUT / "16_english.png"))

        browser.close()
finally:
    server.terminate()

if errors:
    print("BROWSER ERRORS:")
    for e in errors:
        print("  ", e)
    sys.exit(1)
print("ALL UI CHECKS PASSED")
