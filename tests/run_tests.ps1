# Kjører testene på Windows.
# HA-kjernen er laget for Linux, så tests/winstubs gir små erstatninger for
# fcntl/resource. Miljøet ligger lokalt (ikke på NAS) i %LOCALAPPDATA%\fbd_logic_venv.
#
# Første gang:
#   py -3.13 -m venv $env:LOCALAPPDATA\fbd_logic_venv
#   & $env:LOCALAPPDATA\fbd_logic_venv\Scripts\python.exe -m pip install uv
#   "lru-dict>=1.3.0" | Out-File -Encoding ascii $env:TEMP\ovr.txt
#   & $env:LOCALAPPDATA\fbd_logic_venv\Scripts\uv.exe pip install --python $env:LOCALAPPDATA\fbd_logic_venv\Scripts\python.exe --override $env:TEMP\ovr.txt pytest-homeassistant-custom-component home-assistant-frontend playwright
#
# Bruk:  .\tests\run_tests.ps1          (Python-tester)
#        .\tests\run_tests.ps1 -UI      (også editor-testen i headless Chrome/Edge)
param([switch]$UI)
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $env:LOCALAPPDATA "fbd_logic_venv\Scripts\python.exe"
$env:PYTHONPATH = Join-Path $root "tests\winstubs"
Push-Location $root
try {
    & $py -m pytest tests -q -p no:cacheprovider
    if ($UI) { & $py tests\ui\run_ui.py }
} finally {
    Pop-Location
}
