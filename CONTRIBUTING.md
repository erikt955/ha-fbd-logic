# Contributing

Bug reports, ideas and pull requests are welcome. Please open an issue first for larger changes.

## Layout

```
custom_components/fbd_logic/
  blocks.py        the block library (no HA imports): BlockDef, Port, Param and each block's function
  engine.py        Program: compiles a drawing (macros, connectors, forces) and runs a scan
  expr.py          the safe expression interpreter of the Formula block
  manager.py       storage, scheduling, scan on change, HA I/O (services, KNX, Modbus), entities, trend
  websocket.py     the fbd_logic/* websocket API used by the panel
  entity.py        the number, switch, sensor and binary_sensor entities
  device_class.py  device class and state class for Publish value, with warnings
  i18n.py          language choice and tr(); i18n_en.py holds the English texts
  frontend/fbd-panel.js   the editor: one web component, no build step
tests/
  test_engine.py, test_features.py   blocks and the runtime (plain Python)
  test_integration*.py, test_event_scan.py, test_i18n.py   inside a real Home Assistant core
  ui/run_ui.py     the editor in headless Chrome/Edge against a mocked connection
```

A block is a `BlockDef` with inputs, outputs, parameters and a function `fn(ctx, i, p, s) -> dict`. `i` are the input values, `p` the parameters, `s` the state of the instance, and the function returns the new output values. State named in `retain` survives a restart.

Two rules for blocks with state:
- `ctx.dt` is irregular (scans on change come at any time) and is 0 on the first scan after a save or a restart. Keep the state when `dt` is 0, and filter anything that divides by `dt`.
- A block must never stop the scan. Raise an exception for an error; the runtime shows it on the block.

## Texts and languages

The integration is written in Norwegian, and English is looked up by the Norwegian text:
- Block texts (titles, descriptions, labels, help, options) are translated by `i18n_en.EN`. Texts that are the same in both languages go in `i18n_en.SAME`.
- Backend messages are written as `tr("Norwegian text {value}", value=...)`.
- The panel uses `t("Norwegian text")` and `tn(n, "{n} blokk", "{n} blokker")`, with the English texts in `EN` near the top of `fbd-panel.js`.

`tests/test_i18n.py` fails for every text that has no English version. Another language can be added the same way: a catalog per language and a rule in `language_for()` / `setLanguage()`.

## Tests

Linux / macOS:

```
python -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt playwright
python -m pytest tests -q
python tests/ui/run_ui.py   # Chrome/Edge, or Playwright's Chromium (FBD_CHROME can point to a browser)
```

Windows: `powershell -ExecutionPolicy Bypass -File tests\run_tests.ps1 -UI`. The first-time setup is at the top of the script; `tests/winstubs` stands in for the Linux-only modules the HA core imports.

When you change blocks, regenerate the libraries the UI test uses (CRLF line endings, so the diff stays small):

```
python -c "import json; from custom_components.fbd_logic.blocks import library_json; [open(f, 'w', encoding='utf-8', newline='\r\n').write(json.dumps(library_json(lang=l), ensure_ascii=False, indent=1)) for f, l in (('tests/ui/library.json', 'nb'), ('tests/ui/library_en.json', 'en'))]"
```

The README screenshot is made with `python tests/ui/screenshot.py` (the UI test mock with fixed demo values).

## Releases

Bump the version in `manifest.json`, `const.py`, `fbd-panel.js` (`FBD_VERSION`) and `tests/ui/index.html`, add the changes to `CHANGELOG.md`, and create a GitHub release with the tag `vX.Y.Z`. HACS offers the releases as updates.
