"""FBD Logic – function block programs for Home Assistant.

Programs are drawn in a flow based editor (sidebar panel) and executed
cyclically by a small PLC-like runtime inside Home Assistant.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from . import websocket
from .const import (
    DOMAIN,
    PANEL_COMPONENT,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL_PATH,
    PLATFORMS,
    STATIC_URL,
    VERSION,
)
from .i18n import tr
from .manager import FbdManager

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

FRONTEND_DIR = Path(__file__).parent / "frontend"
PANEL_FILE = "fbd-panel.js"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    websocket.async_register(hass)
    return True


async def _async_register_static(hass: HomeAssistant) -> None:
    flag = f"{DOMAIN}_static_registered"
    if hass.data.get(flag):
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), cache_headers=False)]
    )
    hass.data[flag] = True


def _panel_cache_key() -> str:
    try:
        return f"{VERSION}-{int((FRONTEND_DIR / PANEL_FILE).stat().st_mtime)}"
    except OSError:
        return VERSION


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    manager = FbdManager(hass, entry)
    await manager.async_load()
    hass.data[DOMAIN] = manager

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    manager.sync_entities(cleanup_registry=True)
    await manager.async_start()

    await _async_register_static(hass)
    cache_key = await hass.async_add_executor_job(_panel_cache_key)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title=tr(PANEL_TITLE),
        sidebar_icon=PANEL_ICON,
        module_url=f"{STATIC_URL}/{PANEL_FILE}?v={cache_key}",
        embed_iframe=False,
        require_admin=True,
        config={"version": VERSION},
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    manager: FbdManager | None = hass.data.get(DOMAIN)
    if manager is not None:
        await manager.async_unload()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
    if unloaded:
        hass.data.pop(DOMAIN, None)
    return unloaded
