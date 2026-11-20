"""Constants for FBD Logic."""

DOMAIN = "fbd_logic"
VERSION = "0.4.1"

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.programs"
STATE_STORAGE_KEY = f"{DOMAIN}.state"
MACRO_STORAGE_KEY = f"{DOMAIN}.macros"

PANEL_URL_PATH = "fbd-logic"
PANEL_COMPONENT = "fbd-logic-panel"
PANEL_TITLE = "Funksjonsblokker"
PANEL_ICON = "mdi:function-variant"
STATIC_URL = "/fbd_logic_static"

PLATFORMS = ["sensor", "binary_sensor", "number", "switch"]

MANUFACTURER = "FBD Logic"
MODEL = "Funksjonsblokkprogram"

# Online-view updates are throttled to at most this rate (seconds)
SUBSCRIBE_MIN_PERIOD = 0.25
# Scans caused by input changes come at most this often per program (seconds), so a chattering
# input or a feedback loop cannot flood the event loop. The first change after a quiet spell runs at once.
EVENT_SCAN_MIN_GAP = 0.02
# How often retained block state is flushed to disk (seconds)
STATE_SAVE_DELAY = 60
# Trend recording in the panel: max signals per program and samples per signal
MAX_TREND_SIGNALS = 8
TREND_MAX_SAMPLES = 3600
