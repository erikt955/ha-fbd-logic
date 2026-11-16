"""Runtime manager: storage, scheduling, HA I/O and dynamic entities."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import deque
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Callable

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import CALLBACK_TYPE, CoreState, Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .blocks import MACRO_PREFIX, knx_is_binary, to_bool, to_num, to_str
from .const import (
    DOMAIN,
    EVENT_SCAN_MIN_GAP,
    MACRO_STORAGE_KEY,
    MAX_TREND_SIGNALS,
    STATE_SAVE_DELAY,
    STATE_STORAGE_KEY,
    STORAGE_KEY,
    STORAGE_VERSION,
    SUBSCRIBE_MIN_PERIOD,
    TREND_MAX_SAMPLES,
)
from .device_class import publish_class
from .engine import Program
from .i18n import set_language, tr

if TYPE_CHECKING:
    from .entity import FbdEntity

_LOGGER = logging.getLogger(__name__)

NODE_SCHEMA = vol.Schema(
    {
        vol.Required("id"): vol.All(str, vol.Length(min=1, max=64)),
        vol.Required("type"): str,
        vol.Optional("x", default=0): vol.Coerce(float),
        vol.Optional("y", default=0): vol.Coerce(float),
        vol.Optional("params", default=dict): dict,
        vol.Optional("consts", default=dict): dict,
        vol.Optional("label", default=""): str,
    },
    extra=vol.ALLOW_EXTRA,
)
LINK_SCHEMA = vol.Schema(
    {
        vol.Required("id"): str,
        vol.Required("from"): str,
        vol.Required("from_port"): str,
        vol.Required("to"): str,
        vol.Required("to_port"): str,
    },
    extra=vol.ALLOW_EXTRA,
)
PROGRAM_SCHEMA = vol.Schema(
    {
        vol.Optional("id"): vol.All(str, vol.Length(min=1, max=64)),
        vol.Required("name"): vol.All(str, vol.Strip, vol.Length(min=1, max=100)),
        vol.Optional("enabled", default=True): bool,
        vol.Optional("interval", default=1.0): vol.All(
            vol.Coerce(float), vol.Range(min=0.1, max=3600)
        ),
        vol.Optional("event_scan", default=True): bool,
        vol.Optional("description", default=""): str,
        vol.Optional("nodes", default=list): vol.All([NODE_SCHEMA], vol.Length(max=2000)),
        vol.Optional("links", default=list): vol.All([LINK_SCHEMA], vol.Length(max=5000)),
        vol.Optional("view", default=dict): dict,
        vol.Optional("pages"): vol.All(
            [vol.Schema({vol.Required("id"): str, vol.Required("name"): str}, extra=vol.ALLOW_EXTRA)],
            vol.Length(max=50),
        ),
    },
    extra=vol.ALLOW_EXTRA,
)
MACRO_SCHEMA = vol.Schema(
    {
        vol.Optional("id"): vol.All(str, vol.Length(min=1, max=64)),
        vol.Required("name"): vol.All(str, vol.Strip, vol.Length(min=1, max=100)),
        vol.Optional("symbol", default="M"): vol.All(str, vol.Length(max=10)),
        vol.Optional("description", default=""): str,
        vol.Optional("nodes", default=list): vol.All([NODE_SCHEMA], vol.Length(max=1000)),
        vol.Optional("links", default=list): vol.All([LINK_SCHEMA], vol.Length(max=3000)),
    },
    extra=vol.ALLOW_EXTRA,
)

PRESS_DOMAINS = {"button", "input_button"}


def _macro_refs(nodes: list[dict[str, Any]]) -> set[str]:
    return {
        str(n.get("type"))[len(MACRO_PREFIX) :]
        for n in nodes
        if str(n.get("type") or "").startswith(MACRO_PREFIX)
    }


def _vkey(program_id: str, node_id: str) -> str:
    return f"{program_id}:{node_id}"


class HassIO:
    """Bridge between blocks and Home Assistant."""

    def __init__(self, manager: FbdManager) -> None:
        self.manager = manager
        self.hass = manager.hass
        self._knx_registered: set[tuple[str, str]] = set()

    # ---------------------------------------------------------------- generic service call
    def call(
        self, program_id: str, node_id: str, domain: str, service: str, data: dict[str, Any]
    ) -> None:
        if not self.hass.services.has_service(domain, service):
            self.manager.set_write_error(
                program_id, node_id, tr("Tjenesten {service} finnes ikke", service=f"{domain}.{service}")
            )
            return
        if domain == "modbus":
            data = self._modbus_data(service, data)
        self.hass.async_create_task(
            self._async_call(program_id, node_id, domain, service, data),
            f"fbd_logic call {domain}.{service}",
        )

    def _modbus_data(self, service: str, data: dict[str, Any]) -> dict[str, Any]:
        """Newer HA versions call the unit address 'device_address' instead of 'slave'."""
        try:
            svc = self.hass.services.async_services_for_domain("modbus").get(service)
        except AttributeError:
            svc = self.hass.services.async_services().get("modbus", {}).get(service)
        schema = getattr(svc, "schema", None)
        if schema is None:
            return data
        try:
            schema(dict(data))
            return data
        except vol.Invalid:
            alt = dict(data)
            alt["device_address"] = alt.pop("slave", 1)
            try:
                schema(dict(alt))
            except vol.Invalid:
                return data
            return alt

    # ---------------------------------------------------------------- KNX
    def knx_listen(self, address: str, dpt: str, read: bool) -> bool:
        if not self.hass.services.has_service("knx", "event_register"):
            return False
        self.manager.ensure_knx_listener()
        key = (address, dpt)
        if key not in self._knx_registered:
            self._knx_registered.add(key)
            self.hass.async_create_task(
                self._async_knx_register(address, dpt, read), f"fbd_logic knx {address}"
            )
        return True

    async def _async_knx_register(self, address: str, dpt: str, read: bool) -> None:
        data: dict[str, Any] = {"address": address}
        if dpt and not knx_is_binary(dpt):
            data["type"] = dpt
        try:
            await self.hass.services.async_call("knx", "event_register", data, blocking=True)
            if read and self.hass.services.has_service("knx", "read"):
                await self.hass.services.async_call(
                    "knx", "read", {"address": address}, blocking=True
                )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("KNX registration of %s failed: %s", address, err)
            self._knx_registered.discard((address, dpt))

    def knx_value(self, address: str) -> tuple[Any, int] | None:
        return self.manager.knx_cache.get(address)

    # ---------------------------------------------------------------- read
    def read(self, entity_id: str, attribute: str) -> Any:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None:
            return None
        if attribute:
            if state.state == STATE_UNAVAILABLE:
                return None
            return state.attributes.get(attribute)
        if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        return state.state

    # ---------------------------------------------------------------- values
    def get_value(self, program_id: str, node_id: str, default: Any) -> Any:
        return self.manager.values.get(_vkey(program_id, node_id), default)

    def publish(self, program_id: str, node_id: str, value: Any) -> None:
        self.manager.publish(program_id, node_id, value)

    # ---------------------------------------------------------------- write
    def write(
        self,
        program_id: str,
        node_id: str,
        entity_id: str,
        action: str,
        value: Any,
        params: dict[str, Any],
    ) -> None:
        try:
            domain, service, data = self.resolve(entity_id, action, value, params)
        except ValueError as err:
            self.manager.set_write_error(program_id, node_id, str(err))
            return
        if not self.hass.services.has_service(domain, service):
            self.manager.set_write_error(
                program_id, node_id, tr("Tjenesten {service} finnes ikke", service=f"{domain}.{service}")
            )
            return
        self.hass.async_create_task(
            self._async_call(program_id, node_id, domain, service, data),
            f"fbd_logic write {entity_id}",
        )

    async def _async_call(
        self, program_id: str, node_id: str, domain: str, service: str, data: dict
    ) -> None:
        try:
            await self.hass.services.async_call(domain, service, data, blocking=True)
        except Exception as err:  # noqa: BLE001
            msg = f"{domain}.{service}: {err}"
            _LOGGER.debug("Write failed (%s/%s): %s", program_id, node_id, msg)
            self.manager.set_write_error(program_id, node_id, msg)
        else:
            self.manager.set_write_error(program_id, node_id, None)

    def resolve(
        self, entity_id: str, action: str, value: Any, params: dict[str, Any]
    ) -> tuple[str, str, dict[str, Any]]:
        """Map (entity, action, value) to a service call."""
        if "." not in entity_id:
            raise ValueError(tr("Ugyldig entitet: {entity_id}", entity_id=entity_id))
        domain = entity_id.split(".", 1)[0]
        is_bool = isinstance(value, bool)
        num = to_num(value)
        data: dict[str, Any] = {"entity_id": entity_id}

        if action == "custom":
            svc = (params.get("service") or "").strip()
            if "." not in svc:
                raise ValueError(tr("Egendefinert tjeneste må være på formen domene.tjeneste"))
            sdomain, sservice = svc.split(".", 1)
            key = (params.get("data_key") or "").strip()
            if key:
                data[key] = value if isinstance(value, (bool, str)) else num
            return sdomain, sservice, data

        if action == "auto":
            if domain in PRESS_DOMAINS or domain in ("scene", "script"):
                action = "press"
            elif domain in ("number", "input_number", "input_text", "text"):
                action = "value"
            elif domain in ("select", "input_select"):
                action = "option"
            elif domain in ("climate", "water_heater"):
                action = "on_off" if is_bool else "temperature"
            elif domain == "light":
                action = "on_off" if is_bool else "brightness"
            elif domain in ("cover", "valve"):
                action = "on_off" if is_bool else "position"
            elif domain == "fan":
                action = "on_off" if is_bool else "percentage"
            else:
                action = "on_off"

        if action == "on_off":
            on = to_bool(value)
            if domain == "cover":
                return domain, "open_cover" if on else "close_cover", data
            if domain == "valve":
                return domain, "open_valve" if on else "close_valve", data
            if domain == "lock":
                return domain, "unlock" if on else "lock", data
            if domain in ("number", "input_number"):
                data["value"] = 1 if on else 0
                return domain, "set_value", data
            service = "turn_on" if on else "turn_off"
            if self.hass.services.has_service(domain, service):
                return domain, service, data
            return "homeassistant", service, data

        if action == "value":
            if domain in ("input_text", "text"):
                data["value"] = to_str(value)
                return domain, "set_value", data
            if domain in ("select", "input_select"):
                data["option"] = to_str(value)
                return domain, "select_option", data
            data["value"] = num
            return domain, "set_value", data

        if action == "option":
            data["option"] = to_str(value)
            return domain, "select_option", data

        if action == "brightness":
            if num <= 0:
                return "light", "turn_off", data
            data["brightness_pct"] = max(0.0, min(100.0, num))
            return "light", "turn_on", data

        if action == "position":
            pos = int(round(max(0.0, min(100.0, num))))
            if domain == "valve":
                data["position"] = pos
                return domain, "set_valve_position", data
            data["position"] = pos
            return "cover", "set_cover_position", data

        if action == "temperature":
            data["temperature"] = num
            return domain if domain in ("climate", "water_heater") else "climate", "set_temperature", data

        if action == "percentage":
            if num <= 0:
                return "fan", "turn_off", data
            data["percentage"] = int(round(max(0.0, min(100.0, num))))
            return "fan", "set_percentage", data

        if action == "press":
            if domain in PRESS_DOMAINS:
                return domain, "press", data
            return domain, "turn_on", data

        raise ValueError(tr("Ukjent handling: {action}", action=action))


class FbdManager:
    """Owns all programs, their schedules and their HA entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._state_store: Store = Store(hass, STORAGE_VERSION, STATE_STORAGE_KEY)
        self._macro_store: Store = Store(hass, STORAGE_VERSION, MACRO_STORAGE_KEY)
        self.macros: dict[str, dict[str, Any]] = {}
        self.forces: dict[str, dict[str, dict[str, Any]]] = {}
        self.trend_signals: dict[str, list[str]] = {}
        self.trend_data: dict[str, dict[str, deque]] = {}
        self._trend_last: dict[str, float] = {}
        self.knx_cache: dict[str, tuple[Any, int]] = {}
        self._knx_seq = 0
        self._knx_unsub: CALLBACK_TYPE | None = None
        self.programs: dict[str, dict[str, Any]] = {}
        self.runtime: dict[str, Program] = {}
        self.values: dict[str, Any] = {}
        self.published: dict[str, Any] = {}
        self._retained: dict[str, dict[str, Any]] = {}
        self._write_errors: dict[str, str] = {}
        self._timers: dict[str, CALLBACK_TYPE] = {}
        # Event scans: state listeners, KNX address -> programs, the queued scan and the last scan time
        self._watchers: dict[str, CALLBACK_TYPE] = {}
        self._knx_watch: dict[str, set[str]] = {}
        self._pending: dict[str, asyncio.Handle] = {}
        self._last_scan: dict[str, float] = {}
        self._push_pending: dict[str, asyncio.Handle] = {}
        self._subscribers: dict[str, set[Callable[[dict[str, Any]], None]]] = {}
        self._last_push: dict[str, float] = {}
        self._adders: dict[str, Callable] = {}
        self.entities: dict[tuple[str, str], FbdEntity] = {}
        self._unsubs: list[CALLBACK_TYPE] = []
        self.started = False
        self.io = HassIO(self)
        # Warnings, block errors and entity texts follow HA's system language
        set_language(hass.config.language)

    # ------------------------------------------------------------------ setup
    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        for prog in data.get("programs", []):
            try:
                valid = PROGRAM_SCHEMA(prog)
            except vol.Invalid as err:
                _LOGGER.error("Ignoring invalid stored program %s: %s", prog.get("id"), err)
                continue
            self.programs[valid["id"]] = valid
        mdata = await self._macro_store.async_load() or {}
        for macro in mdata.get("macros", []):
            try:
                valid = MACRO_SCHEMA(macro)
            except vol.Invalid as err:
                _LOGGER.error("Ignoring invalid stored macro %s: %s", macro.get("id"), err)
                continue
            self.macros[valid["id"]] = valid
        state = await self._state_store.async_load() or {}
        self.values = dict(state.get("values", {}))
        self._retained = dict(state.get("retained", {}))
        self.forces = {k: v for k, v in (state.get("forces") or {}).items() if v}
        self.trend_signals = {k: list(v) for k, v in (state.get("trends") or {}).items() if v}
        for pid in self.programs:
            self.runtime[pid] = self._build(pid)

    def _build(self, pid: str, previous: Program | None = None) -> Program:
        prog = Program(
            self.programs[pid],
            io=self.io,
            previous=previous,
            retained=self._retained.get(pid),
            macros=self.macros,
            forces=self.forces.get(pid),
        )
        if previous is not None:
            prog.last_now = previous.last_now
        for spec in prog.ha_entities():
            if spec["platform"] in ("sensor", "binary_sensor"):
                prog.warnings.extend(publish_class(spec).problems)
        if pid in self.forces:
            if prog.forces:
                self.forces[pid] = prog.forces
            else:
                self.forces.pop(pid)
        return prog

    async def async_start(self) -> None:
        if self.hass.state is CoreState.running:
            self._start_all()
        else:

            @callback
            def _on_started(_event: Event) -> None:
                self._start_all()

            self._unsubs.append(
                self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)
            )
        self._unsubs.append(
            async_track_time_interval(
                self.hass, self._periodic_state_save, timedelta(seconds=STATE_SAVE_DELAY)
            )
        )

    @callback
    def _start_all(self) -> None:
        self.started = True
        for pid in list(self.runtime):
            self._schedule(pid)

    async def async_unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._knx_unsub is not None:
            self._knx_unsub()
            self._knx_unsub = None
        for pid in list(self._timers):
            self._unschedule(pid)
        self.started = False
        await self._state_store.async_save(self._state_data())

    # ------------------------------------------------------------------ scheduling
    def _unschedule(self, pid: str) -> None:
        unsub = self._timers.pop(pid, None)
        if unsub:
            unsub()
        self._unwatch(pid)

    def _schedule(self, pid: str) -> None:
        self._unschedule(pid)
        prog = self.runtime.get(pid)
        if prog is None or not prog.enabled or not self.started:
            return

        @callback
        def _tick(_now: Any = None) -> None:
            self._run(pid)

        self._timers[pid] = async_track_time_interval(
            self.hass, _tick, timedelta(seconds=prog.interval), name=f"fbd_logic {pid}"
        )
        self._watch(pid)
        _tick()

    # ------------------------------------------------------------------ event scans
    def _watch(self, pid: str) -> None:
        """Listen to the inputs of a scheduled program, so a change scans it at once."""
        self._unwatch(pid)
        prog = self.runtime.get(pid)
        if prog is None or not prog.event_scan or pid not in self._timers:
            return
        entities, addresses = prog.inputs_to_watch()
        if entities:

            @callback
            def _changed(_event: Event) -> None:
                self.request_scan(pid)

            self._watchers[pid] = async_track_state_change_event(
                self.hass, sorted(entities), _changed
            )
        for address in addresses:
            self._knx_watch.setdefault(address, set()).add(pid)

    def _unwatch(self, pid: str) -> None:
        unsub = self._watchers.pop(pid, None)
        if unsub:
            unsub()
        for address in [a for a, pids in self._knx_watch.items() if pid in pids]:
            self._knx_watch[address].discard(pid)
            if not self._knx_watch[address]:
                del self._knx_watch[address]
        for queue in (self._pending, self._push_pending):
            handle = queue.pop(pid, None)
            if handle:
                handle.cancel()

    @callback
    def request_scan(self, pid: str) -> None:
        """Scan a program soon because an input changed.

        The scan runs on the next loop iteration, never inside the caller: the change may come
        from a state write made by a scan, and several changes at once give one scan. Scans
        are at least EVENT_SCAN_MIN_GAP apart; the cyclic scan keeps running for the timers.
        """
        prog = self.runtime.get(pid)
        if prog is None or not prog.event_scan or pid not in self._timers or pid in self._pending:
            return
        wait = EVENT_SCAN_MIN_GAP - (time.monotonic() - self._last_scan.get(pid, -1e9))
        if wait > 0:
            self._pending[pid] = self.hass.loop.call_later(wait, self._event_scan, pid)
        else:
            self._pending[pid] = self.hass.loop.call_soon(self._event_scan, pid)

    @callback
    def _event_scan(self, pid: str) -> None:
        self._pending.pop(pid, None)
        if pid in self._timers:
            self._run(pid, event=True)

    @callback
    def _run(self, pid: str, event: bool = False) -> None:
        prog = self.runtime.get(pid)
        if prog is None:
            return
        self._last_scan[pid] = time.monotonic()
        if event:
            prog.event_count += 1
        t0 = time.perf_counter()
        try:
            prog.step(time.monotonic(), dt_util.now())
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Error in program %s", prog.name)
        prog.last_scan_ms = (time.perf_counter() - t0) * 1000
        if self.trend_signals.get(pid):
            self._sample_trend(pid, prog)
        if self._subscribers.get(pid):
            wait = SUBSCRIBE_MIN_PERIOD - (time.monotonic() - self._last_push.get(pid, 0))
            if wait <= 0:
                self._throttled_push(pid)
            elif pid not in self._push_pending:
                # An event scan inside the throttle window must still reach the panel, even
                # when the next cyclic scan is a long way off.
                self._push_pending[pid] = self.hass.loop.call_later(
                    wait, self._throttled_push, pid
                )

    @callback
    def _throttled_push(self, pid: str) -> None:
        self._push_pending.pop(pid, None)
        self._last_push[pid] = time.monotonic()
        if self._subscribers.get(pid):
            self._push(pid)

    # ------------------------------------------------------------------ online view
    def snapshot(self, pid: str) -> dict[str, Any]:
        prog = self.runtime.get(pid)
        if prog is None:
            return {"nodes": {}, "running": False}
        snap = prog.snapshot()
        for nid, entry in snap["nodes"].items():
            werr = self._write_errors.get(_vkey(pid, nid))
            if werr and "e" not in entry:
                entry["e"] = werr
                if "/" in nid:
                    # Show write errors of blocks inside a macro on the instance too.
                    top = nid.split("/", 1)[0]
                    shell = snap["nodes"].get(top)
                    if shell is not None and "e" not in shell:
                        shell["e"] = f"{nid[len(top) + 1 :]}: {werr}"
            node = prog.nodes[nid]
            if node.bdef.ha in ("setpoint", "toggle"):
                entry["v"] = self.values.get(_vkey(pid, nid))
        snap["running"] = bool(self.started and prog.enabled)
        snap["forced"] = sum(len(v) for v in prog.forces.values())
        snap["t"] = round(time.time(), 2)
        snap["warnings"] = prog.warnings
        snap["order"] = {n.id: n.order for n in prog.order}
        return snap

    def _push(self, pid: str) -> None:
        snap = self.snapshot(pid)
        for cb in list(self._subscribers.get(pid, ())):
            try:
                cb(snap)
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Subscriber callback failed", exc_info=True)

    @callback
    def subscribe(self, pid: str, cb: Callable[[dict[str, Any]], None]) -> CALLBACK_TYPE:
        self._subscribers.setdefault(pid, set()).add(cb)
        cb(self.snapshot(pid))

        @callback
        def _unsub() -> None:
            subs = self._subscribers.get(pid)
            if subs:
                subs.discard(cb)

        return _unsub

    # ------------------------------------------------------------------ errors
    def set_write_error(self, pid: str, nid: str, msg: str | None) -> None:
        key = _vkey(pid, nid)
        if msg:
            self._write_errors[key] = msg
        else:
            self._write_errors.pop(key, None)

    # ------------------------------------------------------------------ CRUD
    def list_programs(self) -> list[dict[str, Any]]:
        out = []
        for pid, data in self.programs.items():
            prog = self.runtime.get(pid)
            errors = sum(1 for n in prog.nodes.values() if n.error) if prog else 0
            out.append(
                {
                    "id": pid,
                    "name": data["name"],
                    "enabled": data.get("enabled", True),
                    "interval": data.get("interval", 1.0),
                    "nodes": len(data.get("nodes", [])),
                    "errors": errors,
                    "forced": sum(len(v) for v in self.forces.get(pid, {}).values()),
                    "running": bool(prog and self.started and prog.enabled),
                }
            )
        out.sort(key=lambda p: p["name"].lower())
        return out

    async def async_save_program(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = PROGRAM_SCHEMA(raw)
        if not data.get("id"):
            data["id"] = uuid.uuid4().hex[:12]
        pid = data["id"]
        self.programs[pid] = data
        prog = self._build(pid, self.runtime.get(pid))
        self.runtime[pid] = prog
        self._prune_trends(pid)
        self._clear_write_errors(pid)
        await self._async_save_programs()
        self.sync_entities()
        self._update_device_name(pid)
        self._schedule(pid)
        if not prog.enabled:
            self._push(pid)
        return {"program": data, "warnings": prog.warnings}

    async def async_delete_program(self, pid: str) -> None:
        self._unschedule(pid)
        self.programs.pop(pid, None)
        self.runtime.pop(pid, None)
        self._retained.pop(pid, None)
        self.forces.pop(pid, None)
        self.trend_signals.pop(pid, None)
        self.trend_data.pop(pid, None)
        self._clear_write_errors(pid)
        for key in [k for k in self.values if k.startswith(f"{pid}:")]:
            self.values.pop(key, None)
        await self._async_save_programs()
        self.sync_entities()
        device = self._program_device(pid)
        if device:
            dr.async_get(self.hass).async_remove_device(device.id)
        self._state_store.async_delay_save(self._state_data, 1)

    async def async_set_enabled(self, pid: str, enabled: bool) -> None:
        data = self.programs.get(pid)
        if data is None:
            raise KeyError(pid)
        data["enabled"] = enabled
        prog = self.runtime.get(pid)
        if prog:
            prog.enabled = enabled
            if not enabled:
                prog.last_now = None
        await self._async_save_programs()
        self._schedule(pid)
        ent = self.entities.get(("switch", f"{pid}_enabled"))
        if ent is not None:
            ent.write_state()
        self._push(pid)

    def _clear_write_errors(self, pid: str) -> None:
        for key in [k for k in self._write_errors if k.startswith(f"{pid}:")]:
            self._write_errors.pop(key, None)

    async def _async_save_programs(self) -> None:
        await self._store.async_save({"programs": list(self.programs.values())})

    # ------------------------------------------------------------------ macros
    def list_macros(self) -> list[dict[str, Any]]:
        out = []
        for mid, macro in self.macros.items():
            out.append(
                {
                    "id": mid,
                    "name": macro["name"],
                    "symbol": macro.get("symbol", "M"),
                    "used_by": self.macro_users(mid),
                }
            )
        out.sort(key=lambda m: m["name"].lower())
        return out

    def macro_users(self, mid: str) -> list[str]:
        users = [
            data["name"]
            for data in self.programs.values()
            if mid in _macro_refs(data.get("nodes", []))
        ]
        users += [
            f"makro {m['name']}"
            for other, m in self.macros.items()
            if other != mid and mid in _macro_refs(m.get("nodes", []))
        ]
        return users

    def _macro_closure(self, mid: str, macros: dict[str, dict[str, Any]]) -> set[str]:
        seen: set[str] = set()
        todo = [mid]
        while todo:
            cur = todo.pop()
            macro = macros.get(cur)
            if macro is None:
                continue
            for ref in _macro_refs(macro.get("nodes", [])):
                if ref not in seen:
                    seen.add(ref)
                    todo.append(ref)
        return seen

    async def async_save_macro(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = MACRO_SCHEMA(raw)
        if not data.get("id"):
            data["id"] = uuid.uuid4().hex[:12]
        mid = data["id"]
        candidate = dict(self.macros)
        candidate[mid] = data
        if mid in self._macro_closure(mid, candidate):
            raise vol.Invalid(tr("Makroen kan ikke inneholde seg selv (direkte eller via andre makroer)"))
        self.macros[mid] = data
        await self._macro_store.async_save({"macros": list(self.macros.values())})
        self._rebuild_all()
        return {"macro": data}

    async def async_delete_macro(self, mid: str) -> list[str]:
        users = self.macro_users(mid)
        if users:
            return users
        self.macros.pop(mid, None)
        await self._macro_store.async_save({"macros": list(self.macros.values())})
        self._rebuild_all()
        return []

    def _rebuild_all(self) -> None:
        """Recompile programs after a macro changed (online change keeps state)."""
        for pid in list(self.programs):
            self.runtime[pid] = self._build(pid, self.runtime.get(pid))
            self._prune_trends(pid)
            if pid in self._timers:
                self._watch(pid)  # a macro may read other entities now
        self.sync_entities()
        for pid in self.programs:
            if self._subscribers.get(pid):
                self._push(pid)

    # ------------------------------------------------------------------ forcing
    def set_force(self, pid: str, nid: str, port: str, value: Any) -> dict[str, Any]:
        prog = self.runtime.get(pid)
        if prog is None:
            raise KeyError(pid)
        forces = {k: dict(v) for k, v in self.forces.get(pid, {}).items()}
        if value is None:
            forces.get(nid, {}).pop(port, None)
            if nid in forces and not forces[nid]:
                forces.pop(nid)
        else:
            forces.setdefault(nid, {})[port] = value
        prog.set_forces(forces)
        if prog.forces:
            self.forces[pid] = prog.forces
        else:
            self.forces.pop(pid, None)
        self._state_store.async_delay_save(self._state_data, 2)
        self._push(pid)
        return prog.forces

    def clear_forces(self, pid: str) -> None:
        prog = self.runtime.get(pid)
        if prog is not None:
            prog.set_forces({})
        self.forces.pop(pid, None)
        self._state_store.async_delay_save(self._state_data, 2)
        self._push(pid)

    # ------------------------------------------------------------------ trends
    def set_trend_signals(self, pid: str, signals: list[str]) -> list[str]:
        clean: list[str] = []
        for sig in signals:
            if isinstance(sig, str) and "|" in sig and sig not in clean:
                clean.append(sig)
        clean = clean[:MAX_TREND_SIGNALS]
        if clean:
            self.trend_signals[pid] = clean
        else:
            self.trend_signals.pop(pid, None)
        buf = self.trend_data.get(pid, {})
        for key in [k for k in buf if k not in clean]:
            buf.pop(key)
        self._state_store.async_delay_save(self._state_data, 2)
        prog = self.runtime.get(pid)
        if prog is not None and clean:
            self._trend_last.pop(pid, None)
            self._sample_trend(pid, prog)
        return clean

    def _prune_trends(self, pid: str) -> None:
        prog = self.runtime.get(pid)
        sigs = self.trend_signals.get(pid)
        if prog is None or not sigs:
            return
        keep = [s for s in sigs if s.split("|", 1)[0] in prog.nodes]
        if keep != sigs:
            self.set_trend_signals(pid, keep)

    def _sample_trend(self, pid: str, prog: Program) -> None:
        now = time.time()
        if now - self._trend_last.get(pid, 0.0) < max(1.0, prog.interval) - 0.05:
            return
        self._trend_last[pid] = now
        buf = self.trend_data.setdefault(pid, {})
        t = round(now, 2)
        for key in self.trend_signals.get(pid, ()):
            nid, port = key.split("|", 1)
            value = prog.value(nid, port)
            if isinstance(value, (bool, int, float)):
                buf.setdefault(key, deque(maxlen=TREND_MAX_SAMPLES)).append((t, value))

    def trend(self, pid: str) -> dict[str, Any]:
        buf = self.trend_data.get(pid, {})
        return {
            "signals": list(self.trend_signals.get(pid, [])),
            "data": {k: [list(x) for x in v] for k, v in buf.items()},
        }

    # ------------------------------------------------------------------ KNX telegrams
    @callback
    def ensure_knx_listener(self) -> None:
        if self._knx_unsub is not None:
            return

        @callback
        def _on_knx(event: Event) -> None:
            data = event.data
            if data.get("telegramtype") not in ("GroupValueWrite", "GroupValueResponse"):
                return
            dest = data.get("destination")
            if not dest:
                return
            value = data.get("value")
            if value is None:
                value = data.get("data")
                if isinstance(value, (list, tuple)) and len(value) == 1:
                    value = value[0]
            self._knx_seq += 1
            self.knx_cache[str(dest)] = (value, self._knx_seq)
            for pid in tuple(self._knx_watch.get(str(dest), ())):
                self.request_scan(pid)

        self._knx_unsub = self.hass.bus.async_listen("knx_event", _on_knx)

    # ------------------------------------------------------------------ values / state
    def set_value(self, pid: str, nid: str, value: Any) -> None:
        self.values[_vkey(pid, nid)] = value
        self._state_store.async_delay_save(self._state_data, 5)
        for platform in ("number", "switch"):
            ent = self.entities.get((platform, f"{pid}_{nid}"))
            if ent is not None:
                ent.write_state()
        self.request_scan(pid)

    def publish(self, pid: str, nid: str, value: Any) -> None:
        key = _vkey(pid, nid)
        self.published[key] = value
        for platform in ("sensor", "binary_sensor"):
            ent = self.entities.get((platform, f"{pid}_{nid}"))
            if ent is not None:
                ent.set_published(value)  # type: ignore[attr-defined]

    def _state_data(self) -> dict[str, Any]:
        retained = {}
        for pid, prog in self.runtime.items():
            retained[pid] = prog.retained_state()
        self._retained = retained
        return {
            "values": self.values,
            "retained": retained,
            "forces": self.forces,
            "trends": self.trend_signals,
        }

    @callback
    def _periodic_state_save(self, _now: Any = None) -> None:
        self._state_store.async_delay_save(self._state_data, 1)

    # ------------------------------------------------------------------ entities
    @callback
    def register_platform(self, platform: str, add_entities: Callable) -> None:
        self._adders[platform] = add_entities

    def _desired_specs(self) -> dict[tuple[str, str], dict[str, Any]]:
        desired: dict[tuple[str, str], dict[str, Any]] = {}
        for pid, prog in self.runtime.items():
            desired[("switch", f"{pid}_enabled")] = {
                "platform": "switch",
                "kind": "program_enabled",
                "program_id": pid,
                "node_id": "enabled",
            }
            for spec in prog.ha_entities():
                spec = dict(spec)
                spec["program_id"] = pid
                desired[(spec["platform"], f"{pid}_{spec['node_id']}")] = spec
        return desired

    @callback
    def sync_entities(self, cleanup_registry: bool = False) -> None:
        """Create, update and remove entities to match the programs."""
        from .entity import create_entity  # pylint: disable=import-outside-toplevel

        desired = self._desired_specs()
        ent_reg = er.async_get(self.hass)

        for key in list(self.entities):
            if key not in desired:
                ent = self.entities.pop(key)
                if ent.registry_entry is not None:
                    ent_reg.async_remove(ent.registry_entry.entity_id)
                elif ent.hass is not None:
                    self.hass.async_create_task(ent.async_remove())

        if cleanup_registry:
            platform_by_domain = {"sensor", "binary_sensor", "number", "switch"}
            for reg_entry in er.async_entries_for_config_entry(ent_reg, self.entry.entry_id):
                if reg_entry.domain in platform_by_domain and (
                    (reg_entry.domain, reg_entry.unique_id) not in desired
                ):
                    ent_reg.async_remove(reg_entry.entity_id)

        new: dict[str, list[FbdEntity]] = {}
        for key, spec in desired.items():
            ent = self.entities.get(key)
            if ent is not None:
                ent.update_spec(spec)
                continue
            if spec["platform"] not in self._adders:
                continue
            if spec["platform"] in ("number", "switch") and spec.get("kind") != "program_enabled":
                vkey = _vkey(spec["program_id"], spec["node_id"])
                if vkey not in self.values:
                    initial = spec.get("initial")
                    self.values[vkey] = (
                        bool(initial) if spec["platform"] == "switch" else to_num(initial)
                    )
            ent = create_entity(self, spec)
            self.entities[key] = ent
            new.setdefault(spec["platform"], []).append(ent)
        for platform, ents in new.items():
            self._adders[platform](ents)

    def program_name(self, pid: str) -> str:
        data = self.programs.get(pid)
        return data["name"] if data else pid

    def _program_device(self, pid: str) -> dr.DeviceEntry | None:
        """The device for a program, looked up within this config entry.

        async_get_device(identifiers=...) is deprecated from HA 2026.11 (identifiers are no
        longer unique across config entries); this works on older and newer versions alike.
        """
        dev_reg = dr.async_get(self.hass)
        for device in dr.async_entries_for_config_entry(dev_reg, self.entry.entry_id):
            if (DOMAIN, pid) in device.identifiers:
                return device
        return None

    def _update_device_name(self, pid: str) -> None:
        device = self._program_device(pid)
        name = self.program_name(pid)
        if device and device.name != name:
            dr.async_get(self.hass).async_update_device(device.id, name=name)
