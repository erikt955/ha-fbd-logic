"""Cyclic function block runtime (no Home Assistant imports).

A Program is compiled from its JSON description into an ordered list of
nodes. Each call to ``step()`` executes one scan: every node reads its
inputs (from the upstream node's output or from the configured constant),
runs its block function and stores its outputs.

Feedback loops are allowed: the node that closes a loop reads the value
its source produced in the previous scan (one-cycle delay), just like a
PLC / EBO function block program.

Macro instances are flattened at compile time: the macro's inner nodes
are added with ids ``<instance id>/<inner id>`` and the wires to/from the
instance are re-routed to the macro's pin blocks. The instance itself is
kept as a non-running "shell" node whose outputs mirror the inner pins
(for the online view). Connectors (page_out → page_in) are resolved by
name within the same macro scope.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from .blocks import (
    ANY,
    BOOL,
    LIBRARY,
    MACRO_PREFIX,
    NUM,
    STR,
    BlockDef,
    Port,
    coerce,
    macro_blockdef,
    macro_pins,
)
from .i18n import tr

_LOGGER = logging.getLogger(__name__)

MAX_MACRO_DEPTH = 8


class IOAdapter(Protocol):
    """Interface the HA layer provides to the blocks."""

    def read(self, entity_id: str, attribute: str) -> Any: ...

    def write(
        self,
        program_id: str,
        node_id: str,
        entity_id: str,
        action: str,
        value: Any,
        params: dict[str, Any],
    ) -> None: ...

    def get_value(self, program_id: str, node_id: str, default: Any) -> Any: ...

    def publish(self, program_id: str, node_id: str, value: Any) -> None: ...

    def call(
        self, program_id: str, node_id: str, domain: str, service: str, data: dict[str, Any]
    ) -> None: ...

    def knx_listen(self, address: str, dpt: str, read: bool) -> bool: ...

    def knx_value(self, address: str) -> tuple[Any, int] | None: ...


class NullIO:
    """IO adapter that does nothing (used for validation/tests)."""

    def read(self, entity_id, attribute):
        return None

    def write(self, program_id, node_id, entity_id, action, value, params):
        return None

    def get_value(self, program_id, node_id, default):
        return default

    def publish(self, program_id, node_id, value):
        return None

    def call(self, program_id, node_id, domain, service, data):
        return None

    def knx_listen(self, address, dpt, read):
        return True

    def knx_value(self, address):
        return None


@dataclass
class Ctx:
    io: Any
    program_id: str
    now: float = 0.0
    dt: float = 0.0
    local: datetime = field(default_factory=datetime.now)
    node_id: str = ""


def _default_for(port: Port) -> Any:
    if port.type == BOOL:
        return False
    if port.type == NUM:
        return 0.0
    if port.type == STR:
        return ""
    return 0.0


@dataclass
class Node:
    id: str
    type: str
    bdef: BlockDef
    params: dict[str, Any]
    consts: dict[str, Any]
    inputs: list[Port]
    outputs: dict[str, Any]
    in_links: dict[str, tuple[str, str]] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    order: int = 0
    x: float = 0.0
    y: float = 0.0
    scope: str = ""
    label_prefix: str = ""
    static_error: str | None = None  # compile-time problem shown while running


@dataclass
class Shell:
    """A macro instance (not executed itself)."""

    id: str
    macro_id: str
    ins: dict[str, str]
    outs: dict[str, str]
    members: list[Node] = field(default_factory=list)


class Program:
    """A compiled, runnable function block program."""

    def __init__(
        self,
        data: dict[str, Any],
        io: Any = None,
        previous: Program | None = None,
        retained: dict[str, Any] | None = None,
        macros: dict[str, dict[str, Any]] | None = None,
        forces: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.data = data
        self.id: str = data["id"]
        self.name: str = data.get("name") or self.id
        self.enabled: bool = bool(data.get("enabled", True))
        try:
            interval = float(data.get("interval", 1.0))
        except (TypeError, ValueError):
            interval = 1.0
        self.interval: float = max(0.1, min(3600.0, interval))
        # Also scan as soon as an input (entity, KNX address, setpoint/switch) changes.
        self.event_scan: bool = bool(data.get("event_scan", True))
        self.io = io or NullIO()
        self.macros: dict[str, dict[str, Any]] = macros or {}
        self.warnings: list[str] = []
        self.nodes: dict[str, Node] = {}
        self.order: list[Node] = []
        self.shells: list[Shell] = []
        # (shell id, pin) -> (inner node id, port) for wires and forces
        self.redirect: dict[tuple[str, str], tuple[str, str]] = {}
        self.forces: dict[str, dict[str, Any]] = {}
        self._eff_forces: dict[str, dict[str, Any]] = {}
        self.last_now: float | None = None
        self.scan_count = 0
        self.event_count = 0
        self.last_scan_ms = 0.0
        self._compile(previous, retained or {})
        if forces:
            self.set_forces(forces)

    # ------------------------------------------------------------------
    @property
    def macro_ids(self) -> set[str]:
        return {sh.macro_id for sh in self.shells}

    def inputs_to_watch(self) -> tuple[set[str], set[str]]:
        """Entity ids and KNX group addresses this program reads, macros included."""
        entities: set[str] = set()
        addresses: set[str] = set()
        for node in self.nodes.values():
            if node.type == "entity_in":
                eid = str(node.params.get("entity_id") or "").strip()
                if eid:
                    entities.add(eid)
            elif node.type == "knx_read":
                address = str(node.params.get("address") or "").strip()
                if address:
                    addresses.add(address)
        return entities, addresses

    def _flatten(
        self,
        nodes: list[dict[str, Any]],
        links: list[dict[str, Any]],
        prefix: str,
        label_prefix: str,
        stack: tuple[str, ...],
    ) -> tuple[list[dict[str, Any]], list[tuple[Any, Any, Any, Any]], list[tuple[Shell, dict]]]:
        """Expand macro instances. Returns (nodes, links, shells) with full ids."""
        flat_nodes: list[dict[str, Any]] = []
        flat_links: list[tuple[Any, Any, Any, Any]] = []
        shells: list[tuple[Shell, dict]] = []
        local: dict[str, Shell] = {}
        for raw in nodes:
            nid = str(raw.get("id", ""))
            btype = str(raw.get("type") or "")
            full = prefix + nid
            if nid and btype.startswith(MACRO_PREFIX):
                mid = btype[len(MACRO_PREFIX) :]
                macro = self.macros.get(mid)
                if macro is None:
                    self.warnings.append(tr("Ukjent makro '{mid}' ({full}) ignorert", mid=mid, full=full))
                    continue
                if mid in stack or len(stack) >= MAX_MACRO_DEPTH:
                    self.warnings.append(
                        tr("Makroen «{name}» brukes i seg selv ({full}) – ignorert", name=macro.get("name", mid), full=full)
                    )
                    continue
                label = str(raw.get("label") or macro.get("name") or nid)
                inner_nodes, inner_links, inner_shells = self._flatten(
                    macro.get("nodes", []),
                    macro.get("links", []),
                    full + "/",
                    f"{label_prefix}{label} ",
                    stack + (mid,),
                )
                pins_in, pins_out = macro_pins(macro)
                shell = Shell(
                    id=full,
                    macro_id=mid,
                    ins={port.name: f"{full}/{iid}" for iid, port in pins_in},
                    outs={port.name: f"{full}/{iid}" for iid, port in pins_out},
                )
                consts = raw.get("consts") or {}
                by_id = {n["id"]: n for n in inner_nodes}
                for iid, port in pins_in:
                    inner = by_id.get(f"{full}/{iid}")
                    if inner is not None:
                        inner["consts"] = {"value": consts.get(port.name, port.default)}
                local[nid] = shell
                shells.append((shell, raw))
                shells.extend(inner_shells)
                flat_nodes.extend(inner_nodes)
                flat_links.extend(inner_links)
            else:
                node = dict(raw)
                node["id"] = full
                node["_scope"] = prefix
                node["_lp"] = label_prefix
                flat_nodes.append(node)
        for raw in links:
            a, pa = str(raw.get("from")), raw.get("from_port")
            b, pb = str(raw.get("to")), raw.get("to_port")
            if a in local:
                src = local[a].outs.get(pa)
                if src is None:
                    self.warnings.append(tr("Ukjent makroutgang {pin} ignorert", pin=f"{prefix}{a}.{pa}"))
                    continue
                src_id, src_port = src, "value"
            else:
                src_id, src_port = prefix + a, pa
            if b in local:
                dst = local[b].ins.get(pb)
                if dst is None:
                    self.warnings.append(tr("Ukjent makroinngang {pin} ignorert", pin=f"{prefix}{b}.{pb}"))
                    continue
                dst_id, dst_port = dst, "value"
            else:
                dst_id, dst_port = prefix + b, pb
            flat_links.append((src_id, src_port, dst_id, dst_port))
        return flat_nodes, flat_links, shells

    def _compile(self, previous: Program | None, retained: dict[str, Any]) -> None:
        raw_nodes, raw_links, shells = self._flatten(
            self.data.get("nodes", []), self.data.get("links", []), "", "", ()
        )
        for raw in raw_nodes:
            node_id = str(raw.get("id", ""))
            btype = raw.get("type")
            bdef = LIBRARY.get(btype)
            if not node_id or bdef is None:
                self.warnings.append(tr("Ukjent blokktype '{btype}' ({node_id}) ignorert", btype=btype, node_id=node_id))
                continue
            if node_id in self.nodes:
                self.warnings.append(tr("Duplisert node-id {node_id} ignorert", node_id=node_id))
                continue
            params = bdef.param_defaults()
            params.update(raw.get("params") or {})
            inputs = bdef.input_ports(params)
            consts = {}
            raw_consts = raw.get("consts") or {}
            for port in inputs:
                consts[port.name] = raw_consts.get(port.name, port.default)
            node = Node(
                id=node_id,
                type=btype,
                bdef=bdef,
                params=params,
                consts=consts,
                inputs=inputs,
                outputs={p.name: _default_for(p) for p in bdef.outputs},
                x=float(raw.get("x", 0) or 0),
                y=float(raw.get("y", 0) or 0),
                scope=str(raw.get("_scope", "")),
                label_prefix=str(raw.get("_lp", "")),
            )
            prev_node = previous.nodes.get(node_id) if previous else None
            if prev_node is not None and prev_node.type == btype:
                if prev_node.params == params:
                    node.state = prev_node.state
                    node.outputs.update(
                        {k: v for k, v in prev_node.outputs.items() if k in node.outputs}
                    )
                else:
                    node.state = {
                        k: v for k, v in prev_node.state.items() if k in bdef.retain
                    }
            elif node_id in retained:
                saved = retained[node_id]
                if saved.get("type") == btype:
                    node.state = {
                        k: v for k, v in (saved.get("s") or {}).items() if k in bdef.retain
                    }
            self.nodes[node_id] = node

        # Macro shells (outputs mirror the inner pins, never executed)
        for shell, raw in shells:
            if shell.id in self.nodes:
                self.warnings.append(tr("Duplisert node-id {node_id} ignorert", node_id=shell.id))
                continue
            bdef = macro_blockdef(self.macros[shell.macro_id])
            consts = raw.get("consts") or {}
            self.nodes[shell.id] = Node(
                id=shell.id,
                type=str(raw.get("type")),
                bdef=bdef,
                params={},
                consts={p.name: consts.get(p.name, p.default) for p in bdef.inputs},
                inputs=list(bdef.inputs),
                outputs={p.name: _default_for(p) for p in bdef.outputs},
                x=float(raw.get("x", 0) or 0),
                y=float(raw.get("y", 0) or 0),
            )
            for pin, inner in shell.outs.items():
                self.redirect[(shell.id, pin)] = (inner, "value")
            shell.members = [n for nid, n in self.nodes.items() if nid.startswith(shell.id + "/")]
            self.shells.append(shell)

        for src, src_port, dst, dst_port in raw_links:
            src_node, dst_node = self.nodes.get(src), self.nodes.get(dst)
            if src_node is None or dst_node is None:
                self.warnings.append(tr("Tråd til ukjent blokk ignorert"))
                continue
            if src_port not in src_node.outputs:
                self.warnings.append(tr("Ukjent utgang {port} ignorert", port=f"{src}.{src_port}"))
                continue
            if dst_port not in {p.name for p in dst_node.inputs}:
                self.warnings.append(tr("Ukjent inngang {port} ignorert", port=f"{dst}.{dst_port}"))
                continue
            if dst_port in dst_node.in_links:
                self.warnings.append(tr("Inngang {port} har flere tråder – siste brukes", port=f"{dst}.{dst_port}"))
            dst_node.in_links[dst_port] = (src, src_port)

        # Connectors: page_in reads the hidden output of the page_out with the same name
        senders: dict[tuple[str, str], str] = {}
        for node in self.nodes.values():
            if node.type == "page_out":
                key = (node.scope, str(node.params.get("name") or "").strip())
                if key in senders:
                    self.warnings.append(tr("Koblingspunktet «{name}» finnes flere ganger – første brukes", name=key[1]))
                else:
                    senders[key] = node.id
        for node in self.nodes.values():
            if node.type == "page_in":
                key = (node.scope, str(node.params.get("name") or "").strip())
                src = senders.get(key)
                if src is None:
                    self.warnings.append(tr("Koblingspunktet «{name}» har ingen sender", name=key[1]))
                    node.static_error = node.error = tr("Ingen sender med navnet «{name}»", name=key[1])
                else:
                    node.in_links["value"] = (src, "value")

        self.order = self._sort()
        for idx, node in enumerate(self.order, start=1):
            node.order = idx

    def _sort(self) -> list[Node]:
        """Topological sort; loops are broken by position (top-left first)."""
        runnable = {nid: n for nid, n in self.nodes.items() if n.bdef.fn is not None}
        indeg = {nid: 0 for nid in runnable}
        children: dict[str, list[str]] = {nid: [] for nid in runnable}
        for nid, node in runnable.items():
            for src, _port in node.in_links.values():
                if src in runnable and src != nid:
                    indeg[nid] += 1
                    children[src].append(nid)

        def pos(nid: str) -> tuple[float, float, str]:
            n = runnable[nid]
            return (n.x, n.y, nid)

        result: list[Node] = []
        ready = sorted([nid for nid, d in indeg.items() if d == 0], key=pos)
        remaining = set(runnable)
        while remaining:
            if not ready:
                # Loop: pick the left/top-most remaining node.
                pick = min(remaining, key=pos)
                ready = [pick]
                indeg[pick] = 0
            nid = ready.pop(0)
            if nid not in remaining:
                continue
            remaining.discard(nid)
            result.append(runnable[nid])
            new_ready = []
            for child in children[nid]:
                if child in remaining:
                    indeg[child] -= 1
                    if indeg[child] <= 0:
                        new_ready.append(child)
            ready = sorted(set(ready) | set(new_ready), key=pos)
        return result

    # ------------------------------------------------------------------
    def step(self, now: float, local: datetime | None = None) -> None:
        """Execute one scan cycle."""
        dt = 0.0 if self.last_now is None else max(0.0, now - self.last_now)
        self.last_now = now
        ctx = Ctx(io=self.io, program_id=self.id, now=now, dt=dt, local=local or datetime.now())
        nodes = self.nodes
        for node in self.order:
            ins: dict[str, Any] = {}
            for port in node.inputs:
                link = node.in_links.get(port.name)
                if link is not None:
                    value = nodes[link[0]].outputs.get(link[1])
                else:
                    value = node.consts.get(port.name, port.default)
                ins[port.name] = coerce(value, port.type)
            ctx.node_id = node.id
            out = None
            try:
                out = node.bdef.fn(ctx, ins, node.params, node.state)
                node.error = node.static_error
            except Exception as err:  # noqa: BLE001 - a block must never stop the scan
                node.error = str(err) or type(err).__name__
            if out:
                for key, value in out.items():
                    if key in node.outputs:
                        node.outputs[key] = value
            forced = self._eff_forces.get(node.id)
            if forced:
                node.outputs.update(forced)
        for shell in self.shells:
            snode = nodes[shell.id]
            for pin, inner in shell.outs.items():
                inner_node = nodes.get(inner)
                if inner_node is not None:
                    snode.outputs[pin] = inner_node.outputs.get("value")
            snode.error = next(
                (f"{m.id[len(shell.id) + 1 :]}: {m.error}" for m in shell.members if m.error), None
            )
        self.scan_count += 1

    # ------------------------------------------------------------------
    def set_forces(self, forces: dict[str, dict[str, Any]]) -> None:
        """Force output pins to fixed values ({node id: {port: value}})."""
        self.forces = {}
        self._eff_forces = {}
        for nid, ports in (forces or {}).items():
            node = self.nodes.get(nid)
            if node is None or not isinstance(ports, dict):
                continue
            types = {p.name: p.type for p in node.bdef.outputs if not p.hidden}
            for port, value in ports.items():
                if port not in types:
                    continue
                v = coerce(value, types[port])
                self.forces.setdefault(nid, {})[port] = v
                eff_id, eff_port = self.redirect.get((nid, port), (nid, port))
                self._eff_forces.setdefault(eff_id, {})[eff_port] = v
                node.outputs[port] = v
                if eff_id in self.nodes:
                    self.nodes[eff_id].outputs[eff_port] = v

    def value(self, node_id: str, port: str) -> Any:
        node = self.nodes.get(node_id)
        return None if node is None else node.outputs.get(port)

    def snapshot(self) -> dict[str, Any]:
        """Current outputs and errors for the online view."""
        nodes: dict[str, Any] = {}
        for node in self.nodes.values():
            entry: dict[str, Any] = {"o": dict(node.outputs)}
            if node.error:
                entry["e"] = node.error
            if node.id in self.forces:
                entry["f"] = dict(self.forces[node.id])
            if not any(not p.hidden for p in node.bdef.outputs):
                # Sinks (write/publish/connector): show the incoming value.
                link = node.in_links.get("value")
                if link is not None:
                    entry["i"] = {"value": self.nodes[link[0]].outputs.get(link[1])}
            nodes[node.id] = entry
        return {
            "nodes": nodes,
            "scan": self.scan_count,
            "events": self.event_count,
            "ms": round(self.last_scan_ms, 3),
        }

    def retained_state(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for node in self.nodes.values():
            if not node.bdef.retain:
                continue
            keep = {k: copy.deepcopy(v) for k, v in node.state.items() if k in node.bdef.retain}
            if keep:
                out[node.id] = {"type": node.type, "s": keep}
        return out

    def ha_entities(self) -> list[dict[str, Any]]:
        """Specs for HA entities this program needs (setpoints, toggles, published)."""
        specs: list[dict[str, Any]] = []
        for node in self.nodes.values():
            kind = node.bdef.ha
            p = node.params
            lp = node.label_prefix
            if kind == "setpoint":
                specs.append(
                    {
                        "platform": "number",
                        "node_id": node.id,
                        "name": lp + str(p.get("name") or "Settpunkt"),
                        "min": float(p.get("min", 0) or 0),
                        "max": float(p.get("max", 100) or 100),
                        "step": float(p.get("step", 0.5) or 0.5),
                        "unit": str(p.get("unit") or "") or None,
                        "mode": p.get("mode", "box"),
                        "initial": p.get("initial", 0),
                    }
                )
            elif kind == "toggle":
                specs.append(
                    {
                        "platform": "switch",
                        "node_id": node.id,
                        "name": lp + str(p.get("name") or "Bryter"),
                        "initial": bool(p.get("initial", False)),
                    }
                )
            elif kind == "publish":
                ptype = p.get("kind", "auto")
                if ptype == "auto":
                    link = node.in_links.get("value")
                    src_type = ANY
                    if link is not None:
                        src = self.nodes[link[0]]
                        for port in src.bdef.outputs:
                            if port.name == link[1]:
                                src_type = port.type
                    ptype = {BOOL: "bool", STR: "text"}.get(src_type, "num")
                specs.append(
                    {
                        "platform": "binary_sensor" if ptype == "bool" else "sensor",
                        "node_id": node.id,
                        "name": lp + str(p.get("name") or "Signal"),
                        "kind": ptype,
                        "unit": (str(p.get("unit") or "") or None) if ptype == "num" else None,
                        "device_class": str(p.get("device_class") or "") or None,
                        "decimals": int(float(p.get("decimals", 2) or 0)),
                    }
                )
        return specs
