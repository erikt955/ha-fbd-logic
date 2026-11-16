"""Screenshot of the English example for the README (docs/images/editor.png), made with the UI test mock.

Run from the repository root: python tests/ui/screenshot.py
"""
import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)
server = subprocess.Popen([sys.executable, "-m", "http.server", "8766", "--bind", "127.0.0.1"], cwd=ROOT,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get("FBD_CHROME") or None)
        page = browser.new_page(viewport={"width": 1500, "height": 900}, device_scale_factor=1)
        page.add_init_script("""
          window.__demoValues = {
            temp: {value: 21.4, on: true, text: '21.4', valid: true},
            window: {value: 0, on: false, text: 'off', valid: true},
            notwindow: {q: true}, day: {q: true}, sel: {out: 21}, man: {q: false}, sp: {value: 21},
            clock: {hour: 14, minute: 32, daymin: 872, weekday: 3, weekend: false},
            pid: {out: 34.6, err: -0.4, auto: true}, hyst: {q: false}, or: {q: false}, tof: {q: false, et: 0},
          };
          window.__demoTrend = {
            'temp|value': (k) => 21.4 + 0.5 * Math.exp(-k / 40) * Math.cos(k / 9) - 0.1 * Math.sin(k / 23),
            'pid|out': (k) => 34.6 - 14 * Math.exp(-k / 40) * Math.cos(k / 9) + Math.sin(k / 17),
          };
        """)
        page.goto("http://127.0.0.1:8766/tests/ui/index.html?lang=en&clean=1&preload=../../examples/room_control.fbd.json")
        page.wait_for_selector("fbd-logic-panel >> [data-node]")
        page.evaluate("""() => Object.assign(window.__panel.hass.states, {
          'sensor.room_temperature': {entity_id: 'sensor.room_temperature', state: '21.4', attributes: {friendly_name: 'Living room temperature', unit_of_measurement: '°C'}},
          'binary_sensor.window': {entity_id: 'binary_sensor.window', state: 'off', attributes: {friendly_name: 'Living room window'}},
          'number.vav_damper': {entity_id: 'number.vav_damper', state: '40', attributes: {friendly_name: 'VAV damper'}},
          'fan.boost': {entity_id: 'fan.boost', state: 'off', attributes: {friendly_name: 'Boost fan'}},
        })""")
        page.wait_for_timeout(500)
        page.evaluate("async () => { const p = window.__panel; await p._trendSet(['temp|value', 'pid|out']); p._showTrend = true; p._applyLayout(); p._renderTrend(); }")
        page.wait_for_timeout(300)
        root = page.locator("fbd-logic-panel")
        root.locator('[data-node="pid"] .blk-body').click(force=True)
        page.wait_for_timeout(300)
        root.locator('[data-act="fit"]').click()
        page.wait_for_timeout(900)
        page.screenshot(path=str(OUT / "editor.png"))
        browser.close()
finally:
    server.terminate()
print("ok", OUT / "editor.png")
