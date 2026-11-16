/* FBD Logic – function block editor panel for Home Assistant.
 * Plain web component, no build step. Talks to the backend over the
 * HA websocket API (fbd_logic/*).
 */
const FBD_VERSION = "0.4.0";
const GRID = 10;
const ROW = 18;
const HEAD = 22;
const INFO = 16;
const STUB = 8;

const CAT_COLORS = {
  io: "#1e6fd9",
  logic: "#7b3fb5",
  compare: "#00897b",
  math: "#6d4c41",
  time: "#e07000",
  control: "#c62828",
  bus: "#ad1457",
  misc: "#546e7a",
  macro: "#283593",
  macro_io: "#455a64",
};
const MACRO_PREFIX = "macro:";

// ------------------------------------------------------------------ language
// The panel is written in Norwegian. Every other language gets English: EN maps each Norwegian text to
// its English version. Add the English text to EN when you add or change a text (tests/test_i18n.py checks it).
let LANG = "nb";
function setLanguage(code) {
  LANG = /^(nb|nn|no)([-_]|$)/i.test(code || "") ? "nb" : "en";
}
function t(s, vars) {
  let out = LANG === "en" && Object.prototype.hasOwnProperty.call(EN, s) ? EN[s] : s;
  if (vars) out = out.replace(/\{(\w+)\}/g, (m, k) => (Object.prototype.hasOwnProperty.call(vars, k) ? String(vars[k]) : m));
  return out;
}
/* A count with the right word form, e.g. tn(n, "{n} blokk", "{n} blokker"). */
function tn(n, one, many, vars) {
  return t(n === 1 ? one : many, { n, ...(vars || {}) });
}
const DAY_NAMES_NB = ["Ma", "Ti", "On", "To", "Fr", "Lø", "Sø"];
const DAY_NAMES_EN = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];
const dayNames = () => (LANG === "en" ? DAY_NAMES_EN : DAY_NAMES_NB);

/* eslint-disable quote-props */
const EN = {
  // toolbar and menus
  "Meny": "Menu",
  "Vis/skjul blokkpalett": "Show/hide block palette",
  "Velg program": "Select program",
  "Nytt program eller ny makro": "New program or macro",
  "＋ Nytt": "＋ New",
  "Programnavn": "Program name",
  "Navn": "Name",
  "Syklustid i sekunder": "Cycle time in seconds",
  "Programmet kjører": "The program is running",
  "Aktiv": "Enabled",
  "Angre (Ctrl+Z)": "Undo (Ctrl+Z)",
  "Gjør om (Ctrl+Y)": "Redo (Ctrl+Y)",
  "Vis live verdier": "Show live values",
  "Vis/skjul trend": "Show/hide trend",
  "Last ned programmet som JSON": "Download the program as JSON",
  "Importer program fra JSON": "Import a program from JSON",
  "Dupliser program": "Duplicate program",
  "Slett program": "Delete program",
  "Flere valg": "More",
  "Lagre og last inn (Ctrl+S)": "Save and load (Ctrl+S)",
  "Lagre": "Save",
  "Vis/skjul egenskaper": "Show/hide properties",
  "＋ Nytt program": "＋ New program",
  "＋ Ny makro": "＋ New macro",
  "＋ Ny makro (egen blokk)": "＋ New macro (custom block)",
  "↶ Angre": "↶ Undo",
  "↷ Gjør om": "↷ Redo",
  "⚙ Programinnstillinger": "⚙ Program settings",
  "⤓ Eksporter": "⤓ Export",
  "⤒ Importer": "⤒ Import",
  "⧉ Dupliser": "⧉ Duplicate",
  "🗑 Slett program": "🗑 Delete program",
  "Zoom ut": "Zoom out",
  "Zoom inn": "Zoom in",
  "Tilpass visning": "Fit view",
  "Laster…": "Loading…",
  "Uten navn": "Untitled",
  // messages
  "Kunne ikke laste FBD Logic: {err}": "Could not load FBD Logic: {err}",
  "Kunne ikke starte online-visning: {err}": "Could not start the online view: {err}",
  "Lagret med advarsler: {list}": "Saved with warnings: {list}",
  "Makro lagret – programmer som bruker den er lastet inn på nytt": "Macro saved – programs that use it have been reloaded",
  "Program opprettet og startet": "Program created and started",
  "Lagret – programmet er lastet inn": "Saved – the program is loaded",
  "Lagring feilet: {err}": "Saving failed: {err}",
  "Alle tvangsstyringer er frigitt": "All forces are released",
  "Feil: {err}": "Error: {err}",
  "makro": "macro",
  "{name} (kopi)": "{name} (copy)",
  "Kopi opprettet – trykk Lagre for å ta den i bruk": "Copy created – press Save to start using it",
  "Verdi satt": "Value set",
  "Kunne ikke sette verdi: {err}": "Could not set the value: {err}",
  "Nytt program": "New program",
  "Nytt program – trykk Lagre når du vil starte det": "New program – press Save when you want to start it",
  "Ny makro": "New macro",
  "inn1": "in1",
  "ut1": "out1",
  "Ny makro – tegn logikken mellom inn- og utgangene og trykk Lagre": "New macro – draw the logic between the inputs and outputs and press Save",
  "Du har ulagrede endringer i dette programmet. Forkaste dem?": "You have unsaved changes in this program. Discard them?",
  "Forkast": "Discard",
  "Slette makroen «{name}»? Det går bare hvis den ikke er i bruk.": "Delete the macro “{name}”? This only works when it is not in use.",
  "Slette programmet «{name}»? Entitetene det har laget fjernes også.": "Delete the program “{name}”? The entities it created are removed too.",
  "Slett": "Delete",
  "Makro slettet": "Macro deleted",
  "Program slettet": "Program deleted",
  "Sletting feilet: {err}": "Deleting failed: {err}",
  "Filen inneholder ikke et FBD-program": "The file does not contain an FBD program",
  "Importert": "Imported",
  "{name} (importert)": "{name} (imported)",
  "Importert – {n} ukjente blokker ignoreres": "Imported – {n} unknown blocks are ignored",
  "Importert – trykk Lagre for å starte": "Imported – press Save to start",
  "Import feilet: {err}": "Import failed: {err}",
  "Tilbake": "Back",
  "Makro – endringer gjelder alle steder den brukes": "Macro – changes apply everywhere it is used",
  " (stoppet)": " (stopped)",
  "(ikke lagret)": "(not saved)",
  "Programmer": "Programs",
  "Makroer": "Macros",
  "(ingen programmer)": "(no programs)",
  // pages
  "Side {n}": "Page {n}",
  "Dobbeltklikk for å gi nytt navn": "Double-click to rename",
  "Ny side": "New page",
  "Slett denne siden": "Delete this page",
  "Slette siden «{page}» og {n} blokk på den?": "Delete the page “{page}” and the block on it?",
  "Slette siden «{page}» og {n} blokker på den?": "Delete the page “{page}” and the {n} blocks on it?",
  "Slett side": "Delete page",
  "Navn på siden": "Page name",
  "{n} blokk flyttet til «{page}». Tråder til andre sider vises som ⇢-merker – bruk gjerne koblingspunkter.": "{n} block moved to “{page}”. Wires to other pages are shown as ⇢ marks – connectors are a good alternative.",
  "{n} blokker flyttet til «{page}». Tråder til andre sider vises som ⇢-merker – bruk gjerne koblingspunkter.": "{n} blocks moved to “{page}”. Wires to other pages are shown as ⇢ marks – connectors are a good alternative.",
  // block info lines
  "(velg entitet)": "(select entity)",
  "PÅ (1)": "ON (1)",
  "AV (0)": "OFF (0)",
  "Direkte": "Direct",
  "Revers": "Reverse",
  "(uten navn)": "(no name)",
  "tall": "number",
  "av/på": "on/off",
  "tekst": "text",
  "valgfri": "any",
  "(adresse)": "(address)",
  "(ukjent makro)": "(unknown macro)",
  "(ingen perioder)": "(no periods)",
  // canvas
  "Dra blokker inn fra paletten til venstre (eller trykk på dem) for å starte.": "Drag blocks in from the palette on the left (or tap them) to start.",
  "Koble utgang → inngang ved å dra fra pinnene. Lagre for å starte programmet.": "Connect output → input by dragging from the pins. Save to start the program.",
  "Signaler mellom sider: bruk «Koblingspunkt (sender)» og «(mottaker)» med samme navn.": "Signals between pages: use “Connector (sender)” and “(receiver)” with the same name.",
  "Ukjent blokk: {type}": "Unknown block: {type}",
  // status bar
  "Ikke lagret ennå": "Not saved yet",
  "Makro – åpne «Vis live» fra en instans for online-verdier": "Macro – open “Show live” from an instance for online values",
  "Kjører": "Running",
  "Stoppet": "Stopped",
  "skann {n}": "scan {n}",
  "skann {n} ({e} ved endring)": "scan {n} ({e} on change)",
  "{n} tvangsstyrt": "{n} forced",
  "{n} blokk med feil": "{n} block with errors",
  "{n} blokker med feil": "{n} blocks with errors",
  "{n} advarsel": "{n} warning",
  "{n} advarsler": "{n} warnings",
  "Offline-visning": "Offline view",
  "Ulagrede endringer": "Unsaved changes",
  "{n} blokk": "{n} block",
  "{n} blokker": "{n} blocks",
  "{v} av {n} blokker": "{v} of {n} blocks",
  // palette and properties
  "Søk blokk…": "Search blocks…",
  "Ingen treff": "No matches",
  "Finnes ikke": "Does not exist",
  "domene.entitet": "domain.entity",
  "Fjern perioden": "Remove the period",
  "på": "on",
  "av": "off",
  "＋ Legg til periode": "＋ Add period",
  "Er av-tiden før på-tiden, varer perioden over midnatt.": "If the off time is before the on time, the period runs past midnight.",
  "Konstant verdi": "Constant value",
  "Tråd": "Wire",
  "Verdi:": "Value:",
  "Slett tråd": "Delete wire",
  "Legg i trend": "Add to trend",
  "{n} blokker valgt": "{n} blocks selected",
  "Dra for å flytte. Ctrl+C / Ctrl+V for å kopiere, Delete for å slette.": "Drag to move. Ctrl+C / Ctrl+V to copy, Delete to delete.",
  "Dupliser": "Duplicate",
  "Erstatt utvalget med en ny makroblokk": "Replace the selection with a new macro block",
  "▣ Lag makro av utvalget": "▣ Make a macro of the selection",
  "Tråder inn til og ut av utvalget blir inn- og utganger på makroen.": "Wires into and out of the selection become inputs and outputs of the macro.",
  "Ukjent blokk": "Unknown block",
  "Blokktypen «{type}» finnes ikke i denne versjonen.": "The block type “{type}” does not exist in this version.",
  "Navn på tegningen (valgfritt)": "Name on the drawing (optional)",
  "Innstillinger": "Settings",
  "Innganger": "Inputs",
  "Utganger": "Outputs",
  "Frigi tvangsstyringen": "Release the force",
  "Frigi": "Release",
  "Verdi å tvinge til": "Value to force to",
  "verdi": "value",
  "Tving utgangen til verdien": "Force the output to the value",
  "Tving": "Force",
  "Tving overstyrer utgangen i det kjørende programmet (som i en PLS) til du frigir den. Gjelder til den frigis, også etter omstart.": "Force overrides the output in the running program (as in a PLC) until you release it. It stays until released, also after a restart.",
  "Makro": "Macro",
  "▣ Åpne makro": "▣ Open macro",
  "● Vis live innhold": "● Show live content",
  "Endringer i makroen gjelder alle steder den brukes.": "Changes to the macro apply everywhere it is used.",
  "Verdi i HA": "Value in HA",
  "På": "On",
  "Sett": "Set",
  "Nå:": "Now:",
  "Kan også endres fra dashboard (entiteten opprettes ved lagring).": "Can also be changed from a dashboard (the entity is created on save).",
  "Skriver bare ved endring. Handling «Automatisk» velger tjeneste ut fra domenet: lys (av/på eller lysstyrke %), cover/valve (posisjon), climate (temperatur), number (sett verdi), select (alternativ), knapp/script/scene (trykk).": "Writes only on change. The action “Automatic” picks the service from the domain: light (on/off or brightness %), cover/valve (position), climate (temperature), number (set value), select (option), button/script/scene (press).",
  "Slett blokk": "Delete block",
  "Flytt til side": "Move to page",
  "ingen ennå": "none yet",
  "Symbol (vises i blokkhodet)": "Symbol (shown in the block header)",
  "Beskrivelse": "Description",
  "Pinner": "Pins",
  "Innganger:": "Inputs:",
  "Utganger:": "Outputs:",
  "Legg til «Makro-inngang» og «Makro-utgang» fra paletten. Rekkefølgen følger høyden på tegningen.": "Add “Macro input” and “Macro output” from the palette. The order follows the height on the drawing.",
  "Bruk": "Usage",
  "Brukt i:": "Used in:",
  "Makroen er ikke lagret. Trykk <b>Lagre</b> – da dukker den opp under «Makroer» i paletten.": "The macro is not saved. Press <b>Save</b> – it then shows up under “Macros” in the palette.",
  "Om": "About",
  "En makro er en egen blokk satt sammen av andre blokker. Hver instans har sin egen tilstand (timere, låser, PID).": "A macro is a custom block made of other blocks. Each instance has its own state (timers, latches, PID).",
  "Syklustid (sekunder)": "Cycle time (seconds)",
  "Skann straks når en inngang endres": "Scan at once when an input changes",
  "Gjelder Les entitet, KNX lytt, Settpunkt og Bryter. Gir rask respons uten kort syklustid. Det faste skannet går fortsatt, blant annet for timerne.": "Applies to Read entity, KNX listen, Setpoint and Switch. Gives a fast response without a short cycle time. The cyclic scan still runs, among other things for the timers.",
  "Aktiv (kjører)": "Enabled (running)",
  "Programmet er ikke lagret ennå. Trykk <b>Lagre</b> for å opprette og starte det.": "The program is not saved yet. Press <b>Save</b> to create and start it.",
  "Tilstand:": "State:",
  "Skann:": "Scans:",
  "Skann ved endring:": "Scans on change:",
  "Tvangsstyrt:": "Forced:",
  "Frigi alle tvangsstyringer": "Release all forces",
  "Frigi alle": "Release all",
  "Hurtigtaster": "Shortcuts",
  "Dra fra utgang til inngang for å koble.": "Drag from an output to an input to connect.",
  "Dra en tilkoblet inngang for å flytte tråden.": "Drag a connected input to move the wire.",
  "Shift/Ctrl + dra på lerretet: velg flere.": "Shift/Ctrl + drag on the canvas: select several.",
  "Delete: slett · Ctrl+Z/Y: angre/gjør om": "Delete: delete · Ctrl+Z/Y: undo/redo",
  "Ctrl+C/V/D: kopier/lim inn/dupliser": "Ctrl+C/V/D: copy/paste/duplicate",
  "Ctrl+S: lagre · Piltaster: flytt · Hjul: zoom": "Ctrl+S: save · Arrow keys: move · Wheel: zoom",
  "Dobbeltklikk på blokk: egenskaper": "Double-click a block: properties",
  "Dobbeltklikk på sidefane: gi nytt navn": "Double-click a page tab: rename",
  "Programmet kjøres syklisk i Home Assistant, og straks en inngang endres hvis det er slått på. Lagring laster det inn på nytt uten å nullstille timere og låser som ikke er endret.": "The program runs cyclically in Home Assistant, and at once when an input changes if that is switched on. Saving reloads it without resetting timers and latches that have not changed.",
  // forcing and trend
  "Tvangsstyringen av «{port}» er frigitt": "The force on “{port}” is released",
  "Utgangen «{port}» er tvunget til {value}": "The output “{port}” is forced to {value}",
  "Tvangsstyring feilet: {err}": "Forcing failed: {err}",
  "Kunne ikke endre trend: {err}": "Could not change the trend: {err}",
  "Maks 8 signaler i trenden – fjern ett først": "At most 8 signals in the trend – remove one first",
  "{sig} (slettet)": "{sig} (deleted)",
  "Tidsvindu": "Time window",
  "Last ned verdiene som CSV (tabell)": "Download the values as CSV (table)",
  "{n} av 8 signaler": "{n} of 8 signals",
  "Trend er tilgjengelig for lagrede programmer.": "Trend is available for saved programs.",
  "Velg en blokk og trykk 📈 ved en utgang (eller velg en tråd og «Legg i trend»). Verdiene samples hvert sekund (eller hver syklus) og de siste 60 minuttene huskes så lenge HA kjører.": "Select a block and press 📈 next to an output (or select a wire and “Add to trend”). Values are sampled every second (or every cycle), and the last 60 minutes are kept while HA is running.",
  "Fjern fra trend": "Remove from trend",
  "tid": "time",
  // macros from a selection, dialogs
  "Utvalget kan ikke inneholde makro-pinner": "The selection cannot contain macro pins",
  "Navn på den nye makroen": "Name of the new macro",
  "Kunne ikke lage makro: {err}": "Could not make the macro: {err}",
  "Makroen «{name}» er laget. Trykk Lagre for å ta den i bruk her.": "The macro “{name}” is made. Press Save to start using it here.",
  "Avbryt": "Cancel",
};
/* eslint-enable quote-props */
// Categorical trend colours (validated, fixed order) – light / dark surface
const TREND_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];
const TREND_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"];
const TREND_WINDOWS = [
  [300, "5 min"],
  [900, "15 min"],
  [1800, "30 min"],
  [3600, "60 min"],
];

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const uid = (p) => p + Math.random().toString(36).slice(2, 8) + Date.now().toString(36).slice(-4);
const snapG = (v) => Math.round(v / GRID) * GRID;
const clone = (o) => JSON.parse(JSON.stringify(o));
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

function fmt(v) {
  if (v === null || v === undefined) return "–";
  if (typeof v === "boolean") return v ? "1" : "0";
  if (typeof v === "number") {
    if (!isFinite(v)) return "–";
    const a = Math.abs(v);
    if (a >= 10000) return v.toFixed(0);
    if (a >= 100) return String(Math.round(v * 10) / 10);
    return String(Math.round(v * 100) / 100);
  }
  const s = String(v);
  return s.length > 14 ? s.slice(0, 13) + "…" : s;
}

function trunc(s, n) {
  s = String(s ?? "");
  return s.length > n ? s.slice(0, Math.max(1, n - 1)) + "…" : s;
}

const STYLE = `
:host { display:block; height:100vh; height:100dvh; overflow:hidden; color:var(--primary-text-color,#212121);
  background:var(--primary-background-color,#fafafa);
  font-family:var(--ha-font-family-body, var(--paper-font-body1_-_font-family, Roboto, "Segoe UI", sans-serif));
  font-size:14px; --fbd-accent:var(--primary-color,#03a9f4); }
* { box-sizing:border-box; }
.app { display:flex; flex-direction:column; height:100%; }
.toolbar { display:flex; align-items:center; gap:6px; padding:6px 8px; min-height:52px; flex-wrap:wrap;
  background:var(--app-header-background-color,var(--primary-color,#03a9f4)); color:var(--app-header-text-color,#fff);
  border-bottom:1px solid var(--app-header-border-bottom-color, var(--divider-color,transparent)); }
.toolbar .sep { width:1px; align-self:stretch; background:color-mix(in srgb, currentColor 30%, transparent); margin:4px 2px; }
.toolbar .grow { flex:1; }
.toolbar select, .toolbar input[type=text], .toolbar input[type=number] {
  background:color-mix(in srgb, currentColor 7%, transparent); color:inherit;
  border:1px solid color-mix(in srgb, currentColor 35%, transparent); border-radius:4px;
  padding:5px 6px; font:inherit; outline:none; }
.toolbar select:focus, .toolbar input:focus { border-color:var(--primary-color,#03a9f4); }
.toolbar select option { color:#212121; background:#fff; }
.toolbar input.name { width:170px; }
.toolbar input.interval { width:62px; }
.toolbar label { display:flex; align-items:center; gap:4px; font-size:13px; white-space:nowrap; }
button { font:inherit; cursor:pointer; border-radius:4px; border:1px solid transparent; padding:5px 10px;
  background:color-mix(in srgb, currentColor 9%, transparent); color:inherit; white-space:nowrap; }
button:hover { background:color-mix(in srgb, currentColor 18%, transparent); }
button:disabled { opacity:.4; cursor:default; }
button.icon { padding:5px 8px; min-width:32px; }
button.primary { background:var(--primary-color,#03a9f4); color:var(--text-primary-color,#fff); font-weight:600;
  border-color:color-mix(in srgb, var(--app-header-text-color,#fff) 45%, transparent); }
button.primary:hover { filter:brightness(1.08); background:var(--primary-color,#03a9f4); }
button.primary.dirty { box-shadow:0 0 0 2px #ffb300; }
button.on { background:color-mix(in srgb, currentColor 24%, transparent); }
.main { flex:1; display:flex; min-height:0; position:relative; }
.palette { width:220px; flex:none; overflow:auto; border-right:1px solid var(--divider-color,#e0e0e0);
  background:var(--card-background-color,#fff); padding:8px; }
.palette input.search { width:100%; padding:6px 8px; border:1px solid var(--divider-color,#ccc); border-radius:4px;
  background:var(--primary-background-color,#fff); color:inherit; font:inherit; margin-bottom:6px; }
.palette details { margin-bottom:4px; }
.palette summary { cursor:pointer; font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.04em;
  color:var(--secondary-text-color,#666); padding:6px 2px; }
.palette .item { display:flex; align-items:center; gap:8px; padding:4px 6px; border-radius:4px; cursor:grab;
  font-size:13px; user-select:none; }
.palette .item:hover { background:var(--secondary-background-color,#eee); }
.palette .sym { flex:none; min-width:44px; text-align:center; color:#fff; border-radius:3px; font-size:10px;
  font-weight:700; padding:2px 3px; font-family:monospace; }
.canvas-wrap { flex:1; position:relative; overflow:hidden; outline:none; min-width:0; }
svg.canvas { width:100%; height:100%; display:block; touch-action:none; user-select:none; -webkit-user-select:none; }
.status { position:absolute; left:8px; bottom:6px; font-size:12px; color:var(--secondary-text-color,#666);
  background:var(--card-background-color,#fff); border:1px solid var(--divider-color,#ddd); border-radius:4px;
  padding:3px 8px; pointer-events:none; opacity:.92; }
.status .run { color:#2e7d32; font-weight:600; } .status .stop { color:#c62828; font-weight:600; }
.status .warn { color:#e65100; }
.zoom { position:absolute; right:8px; bottom:6px; display:flex; gap:4px; }
.zoom button { background:var(--card-background-color,#fff); color:var(--primary-text-color,#333);
  border:1px solid var(--divider-color,#ddd); }
.props { width:290px; flex:none; overflow:auto; border-left:1px solid var(--divider-color,#e0e0e0);
  background:var(--card-background-color,#fff); padding:10px 12px 40px; }
.props h3 { margin:2px 0 4px; font-size:16px; }
.props h4 { margin:14px 0 6px; font-size:12px; text-transform:uppercase; letter-spacing:.04em; color:var(--secondary-text-color,#666); }
.props .desc { font-size:12px; color:var(--secondary-text-color,#666); margin-bottom:8px; line-height:1.35; }
.props .field { margin-bottom:8px; }
.props .field > span { display:block; font-size:12px; color:var(--secondary-text-color,#666); margin-bottom:2px; }
.props input[type=text], .props input[type=number], .props select, .props textarea {
  width:100%; padding:5px 7px; border:1px solid var(--divider-color,#ccc); border-radius:4px; font:inherit;
  background:var(--primary-background-color,#fff); color:inherit; }
.props textarea { min-height:70px; resize:vertical; }
.props .row { display:flex; align-items:center; gap:6px; margin-bottom:5px; font-size:13px; }
.props .row .pn { min-width:64px; font-family:monospace; font-size:12px; }
.props .row input { flex:1; min-width:0; }
.props .linked { color:var(--secondary-text-color,#666); font-size:12px; flex:1; }
.props .live { font-family:monospace; font-weight:600; }
.props .hint { font-size:11px; color:var(--secondary-text-color,#777); margin-top:2px; }
.props .err { color:var(--error-color,#c62828); font-size:13px; margin:6px 0; white-space:pre-wrap; }
.props .btns { display:flex; gap:6px; flex-wrap:wrap; margin-top:14px; }
.props .btns button, .props button.small { background:var(--secondary-background-color,#eee); color:var(--primary-text-color,#333);
  border:1px solid var(--divider-color,#ddd); }
.props .btns button.danger { color:var(--error-color,#c62828); }
.props .kbd { font-size:12px; color:var(--secondary-text-color,#666); line-height:1.6; }
.props code { font-size:11px; }
.narrow-only { display:none; }
.narrow .narrow-only { display:inline-block; }
.narrow .toolbar .wide { display:none; }
.narrow .toolbar { gap:4px; padding:4px 6px; min-height:48px; flex-wrap:nowrap; }
.narrow .toolbar select.progsel { min-width:0; flex:1; max-width:none; }
.narrow .toolbar .grow { display:none; }
.toolbar { position:relative; }
.moremenu { position:absolute; right:6px; top:100%; z-index:40; display:flex; flex-direction:column; min-width:210px;
  background:var(--card-background-color,#fff); border-radius:6px; box-shadow:0 4px 16px rgba(0,0,0,.3); padding:4px 0; }
.moremenu button { background:none; color:var(--primary-text-color,#222); text-align:left; border-radius:0; padding:10px 16px; }
.moremenu button:hover { background:var(--secondary-background-color,#eee); }
.narrow .status { right:118px; font-size:11px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.props .row input[type=checkbox] { flex:none; }
.narrow .palette, .narrow .props { position:absolute; top:0; bottom:0; z-index:5; box-shadow:0 0 12px rgba(0,0,0,.3); }
.narrow .palette { left:0; } .narrow .props { right:0; width:min(310px, 92%); }
.hidden { display:none !important; }
.toast { position:absolute; left:50%; bottom:46px; transform:translateX(-50%); background:#323232; color:#fff;
  padding:8px 14px; border-radius:4px; font-size:13px; z-index:20; max-width:80%; box-shadow:0 2px 8px rgba(0,0,0,.3); }
.toast.error { background:#b71c1c; }
.modal { position:absolute; inset:0; background:rgba(0,0,0,.4); display:flex; align-items:center; justify-content:center; z-index:30; }
.modal .box { background:var(--card-background-color,#fff); color:var(--primary-text-color,#222); padding:18px 20px; border-radius:8px;
  max-width:380px; width:90%; box-shadow:0 4px 20px rgba(0,0,0,.35); }
.modal .box p { margin:0 0 16px; line-height:1.4; }
.modal .box .acts { display:flex; justify-content:flex-end; gap:8px; }
.modal .box button { background:var(--secondary-background-color,#eee); color:inherit; border:1px solid var(--divider-color,#ddd); }
.modal .box button.ok { background:var(--primary-color,#03a9f4); color:#fff; }
.loading { padding:40px; text-align:center; color:var(--secondary-text-color,#666); }

/* SVG */
.grid-dot { fill:var(--divider-color,#d0d0d0); }
.blk-body { fill:var(--card-background-color,#fff); stroke:var(--secondary-text-color,#888); stroke-width:1; }
.blk.sel .blk-body { stroke:var(--fbd-accent); stroke-width:2.2; }
.blk.err .blk-body { stroke:var(--error-color,#d32f2f); stroke-width:2; }
.blk-head-t { fill:#fff; font-size:11px; font-weight:700; font-family:monospace; }
.blk-ord { fill:rgba(255,255,255,.75); font-size:9px; font-family:monospace; }
.blk-label { fill:var(--primary-text-color,#333); font-size:11px; font-weight:600; }
.blk-info { fill:var(--secondary-text-color,#555); font-size:10px; }
.pin-lbl { fill:var(--primary-text-color,#333); font-size:10px; font-family:monospace; }
.pin-stub { stroke:var(--secondary-text-color,#888); stroke-width:1; }
.pin-dot { fill:var(--card-background-color,#fff); stroke:var(--secondary-text-color,#888); stroke-width:1.2; }
.pin-dot.bool { stroke:#8e44ad; } .pin-dot.num { stroke:#1565c0; } .pin-dot.str { stroke:#ef6c00; }
.pin-hit { fill:transparent; cursor:crosshair; }
.pin-hit:hover + .pin-dot, .pin-dot.hot { fill:var(--fbd-accent); }
.const { fill:var(--secondary-text-color,#999); font-size:10px; font-family:monospace; }
.const.set { fill:var(--primary-text-color,#333); font-weight:600; }
.val { font-size:10px; font-family:monospace; font-weight:700; }
.val.t { fill:#2e7d32; } .val.f { fill:#9e9e9e; } .val.n { fill:#1565c0; } .val.s { fill:#ef6c00; }
.wire { fill:none; stroke-width:1.6; }
.wire.bool { stroke:#8e44ad; } .wire.num { stroke:#1565c0; } .wire.str { stroke:#ef6c00; stroke-dasharray:5 3; }
.wire.any { stroke:#607d8b; }
.wire.on { stroke:#2e7d32; stroke-width:2.6; } .wire.off { stroke:#9e9e9e; }
.wire.sel { stroke:var(--fbd-accent) !important; stroke-width:3; }
.wire-hit { fill:none; stroke:transparent; stroke-width:10; cursor:pointer; }
.wire.temp { stroke:var(--fbd-accent); stroke-dasharray:4 3; pointer-events:none; }
.boxsel { fill:rgba(3,169,244,.08); stroke:var(--fbd-accent); stroke-dasharray:4 3; pointer-events:none; }
.cmt-body { fill:#fff7c2; stroke:#d4b200; stroke-width:1; }
.blk.sel .cmt-body { stroke:var(--fbd-accent); stroke-width:2; }
.cmt-t { fill:#5d4b00; font-size:11px; }
.blk { cursor:move; }
.empty-hint { fill:var(--secondary-text-color,#999); font-size:14px; }
.val.fz { fill:#e65100; }
.fz-mark { fill:#e65100; font-size:9px; font-weight:700; font-family:monospace; }
.offpage { fill:var(--secondary-text-color,#777); font-size:9px; font-style:italic; }
.offpage-l { stroke:var(--secondary-text-color,#999); stroke-dasharray:2 2; }
.blk.macro .blk-body { stroke-width:1.6; }

/* layout additions */
.center { flex:1; display:flex; flex-direction:column; min-width:0; min-height:0; }
.pages { position:absolute; left:8px; top:6px; display:flex; gap:3px; align-items:center; z-index:3; max-width:calc(100% - 16px);
  overflow-x:auto; }
.pages button { background:var(--card-background-color,#fff); color:var(--secondary-text-color,#555); border:1px solid var(--divider-color,#ddd);
  font-size:12px; padding:3px 9px; }
.pages button.cur { color:var(--primary-text-color,#222); border-color:var(--fbd-accent); font-weight:600; }
.pages button.x { padding:3px 6px; }
.banner { position:absolute; right:8px; top:6px; z-index:3; font-size:12px; padding:3px 8px; border-radius:4px;
  background:#283593; color:#fff; max-width:60%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.status .fz { color:#e65100; font-weight:600; }
.newmenu { position:absolute; z-index:40; display:flex; flex-direction:column; min-width:180px; background:var(--card-background-color,#fff);
  border-radius:6px; box-shadow:0 4px 16px rgba(0,0,0,.3); padding:4px 0; }
.newmenu button { background:none; color:var(--primary-text-color,#222); text-align:left; border-radius:0; padding:9px 16px; }
.newmenu button:hover { background:var(--secondary-background-color,#eee); }
.props .row .fzin { flex:0 0 58px; width:58px; }
.props .row button.small { padding:2px 7px; font-size:12px; }
.props .row .live.fz { color:#e65100; }
.props button.tiny { padding:1px 6px; font-size:11px; background:var(--secondary-background-color,#eee);
  color:var(--primary-text-color,#333); border:1px solid var(--divider-color,#ddd); }
.sched { border:1px solid var(--divider-color,#ddd); border-radius:4px; padding:6px; margin-bottom:6px; }
.sched .days { display:flex; gap:2px; margin-bottom:5px; }
.sched .days button { flex:1; padding:3px 0; font-size:11px; background:var(--secondary-background-color,#eee);
  color:var(--secondary-text-color,#666); border:1px solid var(--divider-color,#ddd); }
.sched .days button.on { background:var(--primary-color,#03a9f4); color:#fff; border-color:transparent; }
.sched .times { display:flex; gap:6px; align-items:center; font-size:12px; }
.sched .times input { width:auto; flex:1; min-width:0; }

/* trend pane */
.trend { flex:none; height:230px; display:flex; flex-direction:column; border-top:1px solid var(--divider-color,#e0e0e0);
  background:var(--card-background-color,#fff); position:relative; }
.trend .thead { display:flex; align-items:center; gap:6px; padding:4px 8px; font-size:12px; color:var(--secondary-text-color,#666); }
.trend .thead b { color:var(--primary-text-color,#222); font-weight:600; }
.trend .thead select, .trend .thead button { font-size:12px; padding:2px 6px; background:var(--secondary-background-color,#eee);
  color:var(--primary-text-color,#333); border:1px solid var(--divider-color,#ddd); border-radius:4px; }
.trend .tbody { flex:1; overflow-y:auto; overflow-x:hidden; position:relative; }
.trend .tempty { padding:14px; font-size:13px; color:var(--secondary-text-color,#777); }
.trend svg { display:block; width:100%; }
.trend .grid { stroke:var(--fbd-grid,#e1e0d9); stroke-width:1; }
.trend .axis { fill:var(--secondary-text-color,#898781); font-size:10px; font-variant-numeric:tabular-nums; }
.trend .lname { fill:var(--primary-text-color,#222); font-size:11px; }
.trend .lval { fill:var(--primary-text-color,#222); font-size:11px; font-weight:600; font-variant-numeric:tabular-nums; }
.trend .line { fill:none; stroke-width:2; stroke-linejoin:round; stroke-linecap:round; }
.trend .xh { stroke:var(--secondary-text-color,#888); stroke-width:1; pointer-events:none; }
.trend .rm { cursor:pointer; fill:var(--secondary-text-color,#888); font-size:12px; }
.trend .rm:hover { fill:var(--error-color,#c62828); }
.trend .tip { position:absolute; pointer-events:none; background:var(--card-background-color,#fff); color:var(--primary-text-color,#222);
  border:1px solid var(--divider-color,#ccc); border-radius:4px; padding:5px 8px; font-size:11px; box-shadow:0 2px 8px rgba(0,0,0,.2);
  white-space:nowrap; z-index:4; }
.trend .tip .tr { display:flex; align-items:center; gap:6px; }
.trend .tip .k { width:12px; height:2px; flex:none; }
.trend .tip .v { font-weight:700; font-variant-numeric:tabular-nums; }
.trend .tip .n { color:var(--secondary-text-color,#777); }
`;

class FbdLogicPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._narrow = false;
    this._blocks = {};
    this._categories = [];
    this._programs = [];
    this._macros = [];
    this._kind = "program"; // "program" | "macro"
    this._live = null; // macro opened live from an instance: {pid, prefix, title}
    this._page = null;
    this._views = {};
    this._trend = { signals: [], data: {} };
    this._trendSlots = {};
    this._showTrend = false;
    this._trendWin = 900;
    this._prog = null;
    this._isNew = false;
    this._dirty = false;
    this._sel = new Set();
    this._selLink = null;
    this._view = { x: 40, y: 40, k: 1 };
    this._online = true;
    this._snap = null;
    this._unsub = null;
    this._undo = [];
    this._redo = [];
    this._drag = null;
    this._pointers = new Map();
    this._clip = null;
    this._rafPending = false;
    this._showPalette = true;
    this._showProps = true;
    this._addOffset = 0;
  }

  // ------------------------------------------------------------------ HA hooks
  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      setLanguage(hass.language || (hass.locale && hass.locale.language) || document.documentElement.lang);
      this._build();
      this._init();
    } else this._onHassUpdate();
  }
  get hass() {
    return this._hass;
  }
  set narrow(v) {
    const changed = this._narrow !== !!v;
    this._narrow = !!v;
    if (changed) {
      this._showPalette = !this._narrow;
      this._showProps = !this._narrow;
    }
    this._applyLayout();
  }
  get narrow() {
    return this._narrow;
  }
  set panel(p) {
    this._haPanel = p;
  }
  get panel() {
    return this._haPanel;
  }
  set route(r) {
    this._haRoute = r;
  }
  get route() {
    return this._haRoute;
  }

  disconnectedCallback() {
    this._unsubscribe();
  }
  connectedCallback() {
    if (this._hass && this._prog && this._online && !this._unsub && !this._isNew) this._subscribe();
  }

  // ------------------------------------------------------------------ DOM skeleton
  _build() {
    const root = this.shadowRoot;
    root.innerHTML = `
      <style>${STYLE}</style>
      <div class="app">
        <div class="toolbar">
          <button class="icon menu hidden" data-act="menu" title="${t("Meny")}">☰</button>
          <button class="icon" data-act="toggle-palette" title="${t("Vis/skjul blokkpalett")}">▤</button>
          <select class="progsel" title="${t("Velg program")}"></select>
          <button class="wide" data-act="new" title="${t("Nytt program eller ny makro")}">${t("＋ Nytt")}</button>
          <input type="text" class="name wide" placeholder="${t("Programnavn")}" title="${t("Navn")}">
          <label class="wide progonly" title="${t("Syklustid i sekunder")}">⏱ <input type="number" class="interval" min="0.1" max="3600" step="0.1"> s</label>
          <label class="wide progonly" title="${t("Programmet kjører")}"><input type="checkbox" class="enabled"> ${t("Aktiv")}</label>
          <span class="sep wide"></span>
          <button class="icon wide" data-act="undo" title="${t("Angre (Ctrl+Z)")}">↶</button>
          <button class="icon wide" data-act="redo" title="${t("Gjør om (Ctrl+Y)")}">↷</button>
          <span class="sep wide"></span>
          <button data-act="online" class="online on" title="${t("Vis live verdier")}">●<span class="wide"> Online</span></button>
          <button data-act="trend" class="trendbtn" title="${t("Vis/skjul trend")}">📈<span class="wide"> Trend</span></button>
          <span class="grow"></span>
          <button class="wide" data-act="export" title="${t("Last ned programmet som JSON")}">⤓</button>
          <button class="wide" data-act="import" title="${t("Importer program fra JSON")}">⤒</button>
          <button class="wide" data-act="duplicate" title="${t("Dupliser program")}">⧉</button>
          <button class="wide" data-act="delete" title="${t("Slett program")}">🗑</button>
          <button class="icon narrow-only" data-act="more" title="${t("Flere valg")}">⋯</button>
          <button class="primary save" data-act="save" title="${t("Lagre og last inn (Ctrl+S)")}">${t("Lagre")}</button>
          <button class="icon" data-act="toggle-props" title="${t("Vis/skjul egenskaper")}">☷</button>
          <div class="moremenu hidden">
            <button data-act="new-program">${t("＋ Nytt program")}</button>
            <button data-act="new-macro">${t("＋ Ny makro")}</button>
            <button data-act="undo">${t("↶ Angre")}</button>
            <button data-act="redo">${t("↷ Gjør om")}</button>
            <button data-act="program-settings">${t("⚙ Programinnstillinger")}</button>
            <button data-act="export">${t("⤓ Eksporter")}</button>
            <button data-act="import">${t("⤒ Importer")}</button>
            <button data-act="duplicate">${t("⧉ Dupliser")}</button>
            <button data-act="delete">${t("🗑 Slett program")}</button>
          </div>
        </div>
        <div class="main">
          <div class="palette"></div>
          <div class="center">
            <div class="canvas-wrap" tabindex="0">
              <svg class="canvas" xmlns="http://www.w3.org/2000/svg">
                <defs><pattern id="fbdgrid" patternUnits="userSpaceOnUse" width="20" height="20">
                  <circle class="grid-dot" cx="1" cy="1" r="1"></circle></pattern></defs>
                <rect class="bg" x="0" y="0" width="100%" height="100%" fill="url(#fbdgrid)"></rect>
                <g class="vp"></g>
              </svg>
              <div class="pages"></div>
              <div class="banner hidden"></div>
              <div class="status"></div>
              <div class="zoom">
                <button class="icon" data-act="zoom-out" title="${t("Zoom ut")}">−</button>
                <button class="icon" data-act="zoom-in" title="${t("Zoom inn")}">+</button>
                <button class="icon" data-act="fit" title="${t("Tilpass visning")}">⤢</button>
              </div>
            </div>
            <div class="trend hidden"></div>
          </div>
          <div class="props"><div class="loading">${t("Laster…")}</div></div>
        </div>
        <input type="file" class="file hidden" accept=".json,application/json">
      </div>`;
    const q = (s) => root.querySelector(s);
    this.$app = q(".app");
    this.$progsel = q(".progsel");
    this.$name = q("input.name");
    this.$interval = q("input.interval");
    this.$enabled = q("input.enabled");
    this.$palette = q(".palette");
    this.$wrap = q(".canvas-wrap");
    this.$svg = q("svg.canvas");
    this.$vp = q("g.vp");
    this.$pattern = q("#fbdgrid");
    this.$status = q(".status");
    this.$props = q(".props");
    this.$file = q("input.file");
    this.$pages = q(".pages");
    this.$banner = q(".banner");
    this.$trend = q(".trend");

    root.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-act]");
      if (!e.target.closest(".newmenu") && !(btn && btn.dataset.act === "new")) {
        const nm = root.querySelector(".newmenu");
        if (nm) nm.remove();
      }
      if (btn && !btn.disabled) this._action(btn.dataset.act, btn, e);
      else if (!e.target.closest(".moremenu")) root.querySelector(".moremenu").classList.add("hidden");
    });
    this.$pages.addEventListener("dblclick", (e) => {
      const b = e.target.closest("[data-page]");
      if (b) this._renamePage(b.dataset.page);
    });
    this.$trend.addEventListener("pointermove", (e) => this._trendHover(e));
    this.$trend.addEventListener("pointerleave", () => this._trendHover(null));
    this.$trend.addEventListener("change", (e) => {
      if (e.target.classList.contains("twin")) {
        this._trendWin = parseInt(e.target.value, 10) || 900;
        this._renderTrend();
      }
    });
    this.$progsel.addEventListener("change", () => this._switchProgram(this.$progsel.value));
    this.$name.addEventListener("change", () => this._setProgField("name", this.$name.value.trim() || t("Uten navn")));
    this.$interval.addEventListener("change", () => {
      const v = parseFloat(this.$interval.value);
      if (isFinite(v)) this._setProgField("interval", clamp(v, 0.1, 3600));
    });
    this.$enabled.addEventListener("change", () => this._setProgField("enabled", this.$enabled.checked));
    this.$file.addEventListener("change", () => this._importFile());

    const svg = this.$svg;
    svg.addEventListener("pointerdown", (e) => this._onPointerDown(e));
    svg.addEventListener("pointermove", (e) => this._onPointerMove(e));
    svg.addEventListener("pointerup", (e) => this._onPointerUp(e));
    svg.addEventListener("pointercancel", (e) => this._onPointerUp(e, true));
    svg.addEventListener("wheel", (e) => this._onWheel(e), { passive: false });
    svg.addEventListener("dblclick", (e) => this._onDblClick(e));
    this.$wrap.addEventListener("keydown", (e) => this._onKey(e));
    this.$wrap.addEventListener("dragover", (e) => {
      if (e.dataTransfer && [...e.dataTransfer.types].includes("application/x-fbd-block")) {
        e.preventDefault();
        e.dataTransfer.dropEffect = "copy";
      }
    });
    this.$wrap.addEventListener("drop", (e) => {
      const type = e.dataTransfer && e.dataTransfer.getData("application/x-fbd-block");
      if (!type) return;
      e.preventDefault();
      const w = this._toWorld(e.clientX, e.clientY);
      this._addNode(type, w.x - 40, w.y - 10);
    });
    this.$palette.addEventListener("dragstart", (e) => {
      const item = e.target.closest(".item");
      if (!item) return;
      e.dataTransfer.setData("application/x-fbd-block", item.dataset.type);
      e.dataTransfer.effectAllowed = "copy";
    });
    this.$palette.addEventListener("click", (e) => {
      const item = e.target.closest(".item");
      if (!item) return;
      this._addNodeCentered(item.dataset.type);
      if (this._narrow) {
        this._showPalette = false;
        this._applyLayout();
      }
    });
    this.$palette.addEventListener("input", (e) => {
      if (e.target.classList.contains("search")) this._renderPalette(e.target.value);
    });
    this.$props.addEventListener("change", (e) => this._onPropsChange(e));
    this.$props.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.target.tagName === "INPUT") e.target.blur();
    });
    this._resizeObs = new ResizeObserver(() => {
      // Some HA containers do not give custom panels an explicit height.
      if (this.isConnected && this.clientHeight < 150 && !this.style.height) this.style.height = "100vh";
      this._scheduleRender();
      if (this._showTrend) this._renderTrend();
    });
    this._resizeObs.observe(this);
    this._resizeObs.observe(this.$wrap);
    this._applyLayout();
  }

  _applyLayout() {
    if (!this.$app) return;
    this.$app.classList.toggle("narrow", this._narrow);
    this.$trend.classList.toggle("hidden", !this._showTrend);
    this.shadowRoot.querySelector("[data-act=trend]").classList.toggle("on", this._showTrend);
    for (const el of this.shadowRoot.querySelectorAll(".progonly")) el.classList.toggle("hidden", this._kind !== "program");
    this.shadowRoot.querySelector("[data-act=menu]").classList.toggle("hidden", !this._narrow);
    this.$palette.classList.toggle("hidden", !this._showPalette);
    this.$props.classList.toggle("hidden", !this._showProps);
    this.shadowRoot.querySelector("[data-act=toggle-palette]").classList.toggle("on", this._showPalette);
    this.shadowRoot.querySelector("[data-act=toggle-props]").classList.toggle("on", this._showProps);
  }

  // ------------------------------------------------------------------ backend
  _ws(msg) {
    return this._hass.connection.sendMessagePromise(msg);
  }

  async _init() {
    try {
      await this._loadLibrary();
      await this._loadPrograms();
      let last = null;
      try {
        last = localStorage.getItem("fbd_logic_last");
      } catch (_e) {
        /* ignore */
      }
      const isMacro = last && last.startsWith("m:");
      const pick = isMacro
        ? this._macros.find((m) => "m:" + m.id === last) && last
        : (this._programs.find((p) => p.id === last) || this._programs[0] || {}).id;
      if (pick) await this._openProgram(pick);
      else this._newProgram(true);
    } catch (err) {
      this.$props.innerHTML = `<div class="err">${esc(t("Kunne ikke laste FBD Logic: {err}", { err: err.message || err }))}</div>`;
    }
  }

  async _loadLibrary() {
    const lib = await this._ws({ type: "fbd_logic/blocks", language: LANG });
    this._categories = lib.categories;
    this._blocks = {};
    for (const b of lib.blocks) this._blocks[b.type] = b;
    const s = this.$palette.querySelector(".search");
    this._renderPalette(s ? s.value : "");
  }

  async _loadPrograms() {
    const res = await this._ws({ type: "fbd_logic/programs" });
    this._programs = res.programs || [];
    try {
      const m = await this._ws({ type: "fbd_logic/macros" });
      this._macros = m.macros || [];
    } catch (_e) {
      this._macros = [];
    }
    this._renderProgramSelect();
  }

  /* id: program id, or "m:<macro id>" for a macro */
  async _openProgram(id, live) {
    if (id.startsWith("m:")) {
      const res = await this._ws({ type: "fbd_logic/macro/get", macro_id: id.slice(2) });
      const macro = res.macro;
      macro.used_by = res.used_by || [];
      this._setProgram(macro, false, "macro", live || null);
    } else {
      const res = await this._ws({ type: "fbd_logic/program/get", program_id: id });
      this._setProgram(res.program, false, "program");
    }
    try {
      localStorage.setItem("fbd_logic_last", id);
    } catch (_e) {
      /* ignore */
    }
  }

  get _selId() {
    return this._prog ? (this._kind === "macro" ? "m:" : "") + this._prog.id : "";
  }

  _setProgram(prog, isNew, kind = "program", live = null) {
    this._unsubscribe();
    this._kind = kind;
    this._live = live;
    const base =
      kind === "macro"
        ? { nodes: [], links: [], description: "", symbol: "M" }
        : { enabled: true, interval: 1, event_scan: true, nodes: [], links: [], description: "" };
    this._prog = Object.assign(base, prog);
    for (const n of this._prog.nodes) {
      n.params = n.params || {};
      n.consts = n.consts || {};
    }
    this._ensurePages();
    this._page = this._prog.pages[0].id;
    this._views = {};
    this._isNew = isNew;
    this._dirty = isNew && this._prog.nodes.length > 0;
    this._sel = new Set();
    this._selLink = null;
    this._undo = [];
    this._redo = [];
    this._snap = null;
    this._trend = { signals: [], data: {} };
    this._loadView();
    this._syncToolbar();
    this._applyLayout();
    this._renderProgramSelect();
    this._renderPalette((this.$palette.querySelector(".search") || {}).value || "");
    this._renderPages();
    this._renderProps();
    this._scheduleRender();
    this._renderTrend();
    if (this._online && !isNew) this._subscribe();
    if (kind === "program" && !isNew) this._loadTrend();
  }

  _viewKey() {
    return `fbd_logic_view_${this._selId}${this._page && this._page !== this._prog.pages[0].id ? "_" + this._page : ""}`;
  }

  _loadView() {
    let view = this._views[this._page] || null;
    if (!view) {
      try {
        view = JSON.parse(localStorage.getItem(this._viewKey()) || "null");
      } catch (_e) {
        view = null;
      }
    }
    if (view && isFinite(view.k)) this._view = { ...view };
    else this._fitView();
  }

  /* The program id whose runtime feeds the online view (and forces/trends). */
  get _livePid() {
    if (this._kind === "macro") return this._live ? this._live.pid : null;
    return this._isNew ? null : this._prog && this._prog.id;
  }

  _fullId(nid) {
    return this._live ? this._live.prefix + nid : nid;
  }

  async _subscribe() {
    this._unsubscribe();
    const pid = this._livePid;
    if (!this._prog || !pid || !this._hass) return;
    const token = this._selId;
    this._propsRefresh = true;
    try {
      this._unsub = await this._hass.connection.subscribeMessage(
        (snap) => {
          if (!this._prog || this._selId !== token) return;
          this._snap = this._live ? this._scopeSnapshot(snap, this._live.prefix) : snap;
          if (this._propsRefresh) {
            this._propsRefresh = false;
            this._renderProps();
          }
          this._applySnapshot();
          this._trendFromSnapshot();
        },
        { type: "fbd_logic/subscribe", program_id: pid }
      );
    } catch (err) {
      this._toast(t("Kunne ikke starte online-visning: {err}", { err: err.message || err }), true);
    }
  }

  /* Map a program snapshot onto the nodes of a macro instance (ids "<prefix><inner id>"). */
  _scopeSnapshot(snap, prefix) {
    const nodes = {};
    const order = {};
    for (const [k, v] of Object.entries(snap.nodes || {})) {
      if (!k.startsWith(prefix)) continue;
      const rest = k.slice(prefix.length);
      if (rest.includes("/")) continue; // deeper nesting is shown when that macro is opened
      nodes[rest] = v;
    }
    for (const [k, v] of Object.entries(snap.order || {})) if (k.startsWith(prefix)) order[k.slice(prefix.length)] = v;
    return { ...snap, nodes, order, warnings: [] };
  }

  _unsubscribe() {
    if (this._unsub) {
      try {
        const r = this._unsub();
        if (r && r.catch) r.catch(() => {});
      } catch (_e) {
        /* ignore */
      }
      this._unsub = null;
    }
  }

  async _save() {
    if (!this._prog) return;
    const payload = clone(this._prog);
    delete payload.used_by;
    const wasNew = this._isNew;
    try {
      let warnings = [];
      if (this._kind === "macro") {
        const res = await this._ws({ type: "fbd_logic/macro/save", macro: payload });
        this._prog.id = res.macro.id;
        await this._loadLibrary();
      } else {
        const res = await this._ws({ type: "fbd_logic/program/save", program: payload });
        this._prog.id = res.program.id;
        warnings = res.warnings || [];
      }
      this._isNew = false;
      this._dirty = false;
      await this._loadPrograms();
      this._syncToolbar();
      try {
        localStorage.setItem("fbd_logic_last", this._selId);
      } catch (_e) {
        /* ignore */
      }
      if (warnings.length) {
        this._toast(t("Lagret med advarsler: {list}", { list: warnings.join("; ") }), true);
      } else if (this._kind === "macro") {
        this._toast(t("Makro lagret – programmer som bruker den er lastet inn på nytt"));
      } else {
        this._toast(wasNew ? t("Program opprettet og startet") : t("Lagret – programmet er lastet inn"));
      }
      if (this._online && (wasNew || !this._unsub)) this._subscribe();
      if (this._kind === "program" && wasNew) this._loadTrend();
      this._renderProps();
      this._scheduleRender();
    } catch (err) {
      this._toast(t("Lagring feilet: {err}", { err: err.message || err }), true);
    }
  }

  // ------------------------------------------------------------------ toolbar actions
  async _action(act, btn) {
    const menu = this.shadowRoot.querySelector(".moremenu");
    if (act !== "more") menu.classList.add("hidden");
    switch (act) {
      case "more":
        menu.classList.toggle("hidden");
        break;
      case "program-settings":
        this._sel = new Set();
        this._selLink = null;
        this._showProps = true;
        if (this._narrow) this._showPalette = false;
        this._applyLayout();
        this._renderProps();
        this._scheduleRender();
        break;
      case "menu":
        this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
        break;
      case "toggle-palette":
        this._showPalette = !this._showPalette;
        if (this._narrow && this._showPalette) this._showProps = false;
        this._applyLayout();
        break;
      case "toggle-props":
        this._showProps = !this._showProps;
        if (this._narrow && this._showProps) this._showPalette = false;
        this._applyLayout();
        break;
      case "new":
        this._showNewMenu(btn);
        break;
      case "new-program":
        if (await this._confirmDiscard()) this._newProgram(false);
        break;
      case "new-macro":
        if (await this._confirmDiscard()) this._newMacro();
        break;
      case "trend":
        this._showTrend = !this._showTrend;
        this._applyLayout();
        this._renderTrend();
        break;
      case "trend-add":
        await this._trendAdd(btn.dataset.sig);
        break;
      case "trend-rm":
        await this._trendSet(this._trend.signals.filter((s) => s !== btn.dataset.sig));
        break;
      case "trend-csv":
        this._trendCsv();
        break;
      case "page-sel":
        this._switchPage(btn.dataset.page);
        break;
      case "page-add":
        this._addPage();
        break;
      case "page-del":
        await this._deletePage(this._page);
        break;
      case "force-set":
      case "force-release": {
        const port = btn.dataset.port;
        const nid = btn.dataset.node;
        let value = null;
        if (act === "force-set") {
          const inp = this.$props.querySelector(`[data-fzin="${CSS.escape(port)}"]`);
          if (!inp) break;
          value = inp.type === "checkbox" ? inp.checked : this._parseAny(inp.value);
          if (value === "") break;
        }
        await this._force(nid, port, value);
        break;
      }
      case "force-clear":
        try {
          await this._ws({ type: "fbd_logic/force/clear", program_id: this._livePid });
          this._toast(t("Alle tvangsstyringer er frigitt"));
        } catch (err) {
          this._toast(t("Feil: {err}", { err: err.message || err }), true);
        }
        break;
      case "open-macro":
      case "open-macro-live": {
        const node = this._node(btn.dataset.node);
        if (!node || !node.type.startsWith(MACRO_PREFIX)) break;
        if (!(await this._confirmDiscard())) break;
        const mid = node.type.slice(MACRO_PREFIX.length);
        const live =
          act === "open-macro-live"
            ? {
                pid: this._livePid,
                prefix: this._fullId(node.id) + "/",
                title: `${this._live ? this._live.title + " › " : (this._prog.name || "") + " › "}${node.label || this._blocks[node.type]?.title || t("makro")}`,
                back: this._live ? this._live.back : this._prog.id,
              }
            : null;
        await this._openProgram("m:" + mid, live);
        break;
      }
      case "back-live":
        if (this._live && (await this._confirmDiscard())) await this._openProgram(this._live.back);
        break;
      case "make-macro":
        await this._makeMacroFromSelection();
        break;
      case "sched-day":
      case "sched-add":
      case "sched-del":
        this._schedAction(act, btn);
        break;
      case "save":
        await this._save();
        break;
      case "undo":
        this._undoStep();
        break;
      case "redo":
        this._redoStep();
        break;
      case "online":
        this._online = !this._online;
        btn.classList.toggle("on", this._online);
        if (this._online) this._subscribe();
        else {
          this._unsubscribe();
          this._snap = null;
          this._scheduleRender();
          this._renderProps();
        }
        break;
      case "export":
        this._export();
        break;
      case "import":
        if (await this._confirmDiscard()) this.$file.click();
        break;
      case "duplicate":
        if (await this._confirmDiscard()) {
          const copy = clone(this._prog);
          delete copy.used_by;
          copy.id = uid(this._kind === "macro" ? "m" : "p");
          copy.name = t("{name} (kopi)", { name: copy.name || "Program" });
          this._setProgram(copy, true, this._kind);
          this._toast(t("Kopi opprettet – trykk Lagre for å ta den i bruk"));
        }
        break;
      case "delete":
        await this._deleteProgram();
        break;
      case "zoom-in":
        this._zoomAt(1.2);
        break;
      case "zoom-out":
        this._zoomAt(1 / 1.2);
        break;
      case "fit":
        this._fitView();
        this._scheduleRender();
        break;
      case "del-node":
        this._deleteSelection();
        break;
      case "dup-node":
        this._copy();
        this._paste();
        break;
      case "del-link":
        this._deleteSelection();
        break;
      case "set-live": {
        const nid = btn.dataset.node;
        const input = this.$props.querySelector(`[data-liveinput="${CSS.escape(nid)}"]`);
        if (!input) break;
        const node = this._node(nid);
        const value = node && node.type === "toggle" ? input.checked : parseFloat(input.value);
        if (node && node.type !== "toggle" && !isFinite(value)) break;
        try {
          await this._ws({ type: "fbd_logic/set_value", program_id: this._prog.id, node_id: nid, value });
          this._toast(t("Verdi satt"));
        } catch (err) {
          this._toast(t("Kunne ikke sette verdi: {err}", { err: err.message || err }), true);
        }
        break;
      }
      default:
        break;
    }
  }

  _newProgram(silent) {
    const prog = { id: uid("p"), name: t("Nytt program"), enabled: true, interval: 1, event_scan: true, nodes: [], links: [], description: "" };
    this._view = { x: 40, y: 40, k: 1 };
    this._setProgram(prog, true, "program");
    if (!silent) this._toast(t("Nytt program – trykk Lagre når du vil starte det"));
  }

  _newMacro() {
    const macro = {
      id: uid("m"),
      name: t("Ny makro"),
      symbol: "M",
      description: "",
      nodes: [
        { id: uid("n"), type: "macro_in", x: 40, y: 60, params: { name: t("inn1"), type: "num", default: "0" }, consts: {}, label: "" },
        { id: uid("n"), type: "macro_out", x: 400, y: 60, params: { name: t("ut1"), type: "num" }, consts: {}, label: "" },
      ],
      links: [],
    };
    this._setProgram(macro, true, "macro");
    this._fitView();
    this._scheduleRender();
    this._toast(t("Ny makro – tegn logikken mellom inn- og utgangene og trykk Lagre"));
  }

  _showNewMenu(btn) {
    const old = this.shadowRoot.querySelector(".newmenu");
    if (old) {
      old.remove();
      return;
    }
    const m = document.createElement("div");
    m.className = "newmenu";
    m.innerHTML = `<button data-act="new-program">${t("＋ Nytt program")}</button><button data-act="new-macro">${t("＋ Ny makro (egen blokk)")}</button>`;
    const r = btn.getBoundingClientRect();
    const ar = this.$app.getBoundingClientRect();
    m.style.left = `${r.left - ar.left}px`;
    m.style.top = `${r.bottom - ar.top + 4}px`;
    this.$app.appendChild(m);
  }

  async _switchProgram(id) {
    if (!this._prog || id === this._selId) return;
    if (!(await this._confirmDiscard())) {
      this.$progsel.value = this._selId;
      return;
    }
    await this._openProgram(id);
  }

  async _confirmDiscard() {
    if (!this._dirty) return true;
    return this._confirm(t("Du har ulagrede endringer i dette programmet. Forkaste dem?"), t("Forkast"));
  }

  async _deleteProgram() {
    if (!this._prog) return;
    const macro = this._kind === "macro";
    const ok = await this._confirm(
      macro
        ? t("Slette makroen «{name}»? Det går bare hvis den ikke er i bruk.", { name: esc(this._prog.name) })
        : t("Slette programmet «{name}»? Entitetene det har laget fjernes også.", { name: esc(this._prog.name) }),
      t("Slett")
    );
    if (!ok) return;
    try {
      if (!this._isNew) {
        if (macro) await this._ws({ type: "fbd_logic/macro/delete", macro_id: this._prog.id });
        else await this._ws({ type: "fbd_logic/program/delete", program_id: this._prog.id });
      }
      this._dirty = false;
      if (macro) await this._loadLibrary();
      await this._loadPrograms();
      if (this._programs.length) await this._openProgram(this._programs[0].id);
      else this._newProgram(true);
      this._toast(macro ? t("Makro slettet") : t("Program slettet"));
    } catch (err) {
      this._toast(t("Sletting feilet: {err}", { err: err.message || err }), true);
    }
  }

  _export() {
    if (!this._prog) return;
    const data = clone(this._prog);
    delete data.used_by;
    data.fbd_logic_version = FBD_VERSION;
    if (this._kind === "macro") data.kind = "macro";
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = (this._prog.name || "program").replace(/[^\wæøåÆØÅ\- ]+/g, "_") + ".fbd.json";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(a.href);
      a.remove();
    }, 500);
  }

  async _importFile() {
    const file = this.$file.files && this.$file.files[0];
    this.$file.value = "";
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      if (!Array.isArray(data.nodes)) throw new Error(t("Filen inneholder ikke et FBD-program"));
      const kind = data.kind === "macro" ? "macro" : "program";
      delete data.fbd_logic_version;
      delete data.kind;
      data.id = uid(kind === "macro" ? "m" : "p");
      data.name = t("{name} (importert)", { name: data.name || t("Importert") });
      data.links = Array.isArray(data.links) ? data.links : [];
      const unknown = data.nodes.filter((n) => !this._blocks[n.type]).length;
      this._setProgram(data, true, kind);
      this._toast(unknown ? t("Importert – {n} ukjente blokker ignoreres", { n: unknown }) : t("Importert – trykk Lagre for å starte"));
    } catch (err) {
      this._toast(t("Import feilet: {err}", { err: err.message || err }), true);
    }
  }

  _setProgField(field, value) {
    if (!this._prog || this._prog[field] === value) return;
    this._pushUndo();
    this._prog[field] = value;
    this._markDirty();
    this._renderProgramSelect();
    if (!this._sel.size && !this._selLink) this._renderProps();
  }

  _syncToolbar() {
    if (!this._prog) return;
    this.$name.value = this._prog.name || "";
    this.$interval.value = this._prog.interval ?? 1;
    this.$enabled.checked = !!this._prog.enabled;
    if (this._live) {
      this.$banner.innerHTML = `Live: ${esc(this._live.title)} <button class="tiny" data-act="back-live" style="margin-left:6px">${t("Tilbake")}</button>`;
      this.$banner.classList.remove("hidden");
    } else if (this._kind === "macro") {
      this.$banner.textContent = t("Makro – endringer gjelder alle steder den brukes");
      this.$banner.classList.remove("hidden");
    } else this.$banner.classList.add("hidden");
    this.shadowRoot.querySelector(".save").classList.toggle("dirty", this._dirty);
    for (const b of this.shadowRoot.querySelectorAll("[data-act=undo]")) b.disabled = !this._undo.length;
    for (const b of this.shadowRoot.querySelectorAll("[data-act=redo]")) b.disabled = !this._redo.length;
  }

  _renderProgramSelect() {
    const cur = this._selId;
    const progOpts = this._programs.map(
      (p) =>
        `<option value="${esc(p.id)}">${esc(p.id === cur ? this._prog.name : p.name)}${p.enabled ? "" : t(" (stoppet)")}${p.errors ? " ⚠" : ""}${p.forced ? " ⚑" : ""}</option>`
    );
    const macroOpts = this._macros.map(
      (m) => `<option value="m:${esc(m.id)}">▣ ${esc("m:" + m.id === cur ? this._prog.name : m.name)}</option>`
    );
    if (this._prog && this._isNew) {
      const o = `<option value="${esc(cur)}">${esc(this._prog.name)} ${t("(ikke lagret)")}</option>`;
      (this._kind === "macro" ? macroOpts : progOpts).push(o);
    }
    let html = "";
    if (progOpts.length) html += `<optgroup label="${t("Programmer")}">${progOpts.join("")}</optgroup>`;
    if (macroOpts.length) html += `<optgroup label="${t("Makroer")}">${macroOpts.join("")}</optgroup>`;
    this.$progsel.innerHTML = html || `<option value="">${t("(ingen programmer)")}</option>`;
    if (this._prog) this.$progsel.value = cur;
  }

  _markDirty() {
    this._dirty = true;
    this._syncToolbar();
    this._scheduleRender();
  }

  // ------------------------------------------------------------------ undo / redo
  _editState() {
    const p = this._prog;
    return JSON.stringify({
      name: p.name,
      interval: p.interval,
      event_scan: p.event_scan,
      enabled: p.enabled,
      description: p.description,
      symbol: p.symbol,
      nodes: p.nodes,
      links: p.links,
      pages: p.pages,
    });
  }
  _restoreState(json) {
    const s = JSON.parse(json);
    Object.assign(this._prog, s);
    this._ensurePages();
    if (!this._prog.pages.some((pg) => pg.id === this._page)) this._page = this._prog.pages[0].id;
    this._renderPages();
    const ids = new Set(this._prog.nodes.map((n) => n.id));
    this._sel = new Set([...this._sel].filter((id) => ids.has(id)));
    if (this._selLink && !this._prog.links.some((l) => l.id === this._selLink)) this._selLink = null;
    this._dirty = true;
    this._syncToolbar();
    this._renderProgramSelect();
    this._renderProps();
    this._scheduleRender();
  }
  _pushUndo() {
    if (!this._prog) return;
    this._undo.push(this._editState());
    if (this._undo.length > 100) this._undo.shift();
    this._redo = [];
    this._syncToolbar();
  }
  _undoStep() {
    if (!this._undo.length) return;
    this._redo.push(this._editState());
    this._restoreState(this._undo.pop());
  }
  _redoStep() {
    if (!this._redo.length) return;
    this._undo.push(this._editState());
    this._restoreState(this._redo.pop());
  }

  // ------------------------------------------------------------------ model helpers
  _node(id) {
    return this._prog ? this._prog.nodes.find((n) => n.id === id) : null;
  }

  _inputPorts(def, params) {
    const ports = [];
    const dyn = def.dynamic;
    if (!dyn) return def.inputs.slice();
    let n = parseInt(params && params[dyn.param] !== undefined ? params[dyn.param] : dyn.count ?? 2, 10);
    if (!isFinite(n)) n = dyn.count ?? 2;
    n = clamp(n, dyn.min ?? 1, dyn.max ?? 8);
    const start = dyn.start ?? 1;
    for (let i = 0; i < n; i++) {
      if (dyn.pairs) {
        for (const [prefix, type, def0] of dyn.pairs) {
          const name = `${prefix}${i + start}`;
          ports.push({ name, type, default: def0, label: name });
        }
      } else {
        const name = dyn.names ? dyn.names[i] : `${dyn.prefix}${i + start}`;
        ports.push({ name, type: dyn.type, default: dyn.default, label: name });
      }
    }
    return dyn.after ? def.inputs.concat(ports) : ports.concat(def.inputs);
  }

  // ------------------------------------------------------------------ pages
  _ensurePages() {
    const p = this._prog;
    if (!Array.isArray(p.pages) || !p.pages.length) p.pages = [{ id: "p1", name: t("Side {n}", { n: 1 }) }];
    const ids = new Set(p.pages.map((pg) => pg.id));
    for (const n of p.nodes) if (!n.page || !ids.has(n.page)) n.page = p.pages[0].id;
  }

  _visible() {
    return this._prog ? this._prog.nodes.filter((n) => n.page === this._page) : [];
  }

  _pageName(id) {
    const pg = this._prog.pages.find((x) => x.id === id);
    return pg ? pg.name : "?";
  }

  _renderPages() {
    if (!this._prog) return;
    const pages = this._prog.pages;
    const tabs = pages.map(
      (pg) =>
        `<button data-act="page-sel" data-page="${esc(pg.id)}" class="${pg.id === this._page ? "cur" : ""}" title="${t("Dobbeltklikk for å gi nytt navn")}">${esc(pg.name)}</button>`
    );
    tabs.push(`<button data-act="page-add" title="${t("Ny side")}">＋</button>`);
    if (pages.length > 1) tabs.push(`<button class="x" data-act="page-del" title="${t("Slett denne siden")}">✕</button>`);
    this.$pages.innerHTML = tabs.join("");
  }

  _switchPage(id) {
    if (!this._prog || id === this._page || !this._prog.pages.some((p) => p.id === id)) return;
    this._views[this._page] = { ...this._view };
    this._page = id;
    this._sel = new Set();
    this._selLink = null;
    this._loadView();
    this._renderPages();
    this._renderProps();
    this._scheduleRender();
  }

  _addPage() {
    this._pushUndo();
    const ids = new Set(this._prog.pages.map((p) => p.id));
    let i = this._prog.pages.length + 1;
    while (ids.has("p" + i)) i++;
    this._prog.pages.push({ id: "p" + i, name: t("Side {n}", { n: this._prog.pages.length + 1 }) });
    this._markDirty();
    this._switchPage("p" + i);
    this._view = { x: 60, y: 60, k: 1 };
    this._scheduleRender();
  }

  async _deletePage(id) {
    if (this._prog.pages.length < 2) return;
    const count = this._prog.nodes.filter((n) => n.page === id).length;
    if (count && !(await this._confirm(tn(count, "Slette siden «{page}» og {n} blokk på den?", "Slette siden «{page}» og {n} blokker på den?", { page: esc(this._pageName(id)) }), t("Slett side")))) return;
    this._pushUndo();
    const gone = new Set(this._prog.nodes.filter((n) => n.page === id).map((n) => n.id));
    this._prog.nodes = this._prog.nodes.filter((n) => !gone.has(n.id));
    this._prog.links = this._prog.links.filter((l) => !gone.has(l.from) && !gone.has(l.to));
    this._prog.pages = this._prog.pages.filter((p) => p.id !== id);
    this._page = null;
    this._markDirty();
    this._switchPage(this._prog.pages[0].id);
  }

  async _renamePage(id) {
    const name = await this._prompt(t("Navn på siden"), this._pageName(id));
    if (!name) return;
    const pg = this._prog.pages.find((p) => p.id === id);
    if (!pg || pg.name === name) return;
    this._pushUndo();
    pg.name = name;
    this._markDirty();
    this._renderPages();
  }

  _moveSelectionToPage(page) {
    if (!this._sel.size || !this._prog.pages.some((p) => p.id === page) || page === this._page) return;
    this._pushUndo();
    for (const id of this._sel) {
      const n = this._node(id);
      if (n) n.page = page;
    }
    const moved = this._sel.size;
    this._sel = new Set();
    this._markDirty();
    this._renderProps();
    this._toast(tn(moved, "{n} blokk flyttet til «{page}». Tråder til andre sider vises som ⇢-merker – bruk gjerne koblingspunkter.", "{n} blokker flyttet til «{page}». Tråder til andre sider vises som ⇢-merker – bruk gjerne koblingspunkter.", { page: this._pageName(page) }));
  }

  _paramDefaults(def) {
    const p = {};
    for (const x of def.params) p[x.name] = x.default !== null && typeof x.default === "object" ? clone(x.default) : x.default;
    return p;
  }

  _linkTo(nid, port) {
    return this._prog.links.find((l) => l.to === nid && l.to_port === port);
  }

  _addNode(type, x, y) {
    const def = this._blocks[type];
    if (!def || !this._prog) return null;
    this._pushUndo();
    const node = { id: uid("n"), type, x: snapG(x), y: snapG(y), params: this._paramDefaults(def), consts: {}, label: "", page: this._page };
    this._prog.nodes.push(node);
    this._sel = new Set([node.id]);
    this._selLink = null;
    this._markDirty();
    this._renderProps();
    return node;
  }

  _addNodeCentered(type) {
    const r = this.$svg.getBoundingClientRect();
    const w = this._toWorld(r.left + r.width / 2, r.top + r.height / 2);
    this._addOffset = (this._addOffset + 20) % 120;
    this._addNode(type, w.x - 50 + this._addOffset, w.y - 30 + this._addOffset);
  }

  _deleteSelection() {
    if (!this._prog) return;
    if (!this._sel.size && !this._selLink) return;
    this._pushUndo();
    if (this._sel.size) {
      this._prog.nodes = this._prog.nodes.filter((n) => !this._sel.has(n.id));
      this._prog.links = this._prog.links.filter((l) => !this._sel.has(l.from) && !this._sel.has(l.to));
    }
    if (this._selLink) this._prog.links = this._prog.links.filter((l) => l.id !== this._selLink);
    this._sel = new Set();
    this._selLink = null;
    this._markDirty();
    this._renderProps();
  }

  _copy() {
    if (!this._sel.size) return;
    const nodes = this._prog.nodes.filter((n) => this._sel.has(n.id));
    const links = this._prog.links.filter((l) => this._sel.has(l.from) && this._sel.has(l.to));
    this._clip = clone({ nodes, links });
  }

  _paste() {
    if (!this._clip || !this._prog) return;
    this._pushUndo();
    const map = {};
    const sel = new Set();
    for (const n of this._clip.nodes) {
      const c = clone(n);
      c.id = uid("n");
      c.x += 30;
      c.y += 30;
      c.page = this._page;
      map[n.id] = c.id;
      sel.add(c.id);
      this._prog.nodes.push(c);
    }
    for (const l of this._clip.links) {
      this._prog.links.push({ id: uid("l"), from: map[l.from], from_port: l.from_port, to: map[l.to], to_port: l.to_port });
    }
    for (const n of this._clip.nodes) {
      n.x += 30;
      n.y += 30;
    }
    this._sel = sel;
    this._selLink = null;
    this._markDirty();
    this._renderProps();
  }

  _connect(a, b) {
    // a/b: {nid, dir, port}
    let src = a;
    let dst = b;
    if (a.dir === "in") {
      src = b;
      dst = a;
    }
    if (src.dir !== "out" || dst.dir !== "in") return;
    this._pushUndo();
    this._prog.links = this._prog.links.filter((l) => !(l.to === dst.nid && l.to_port === dst.port));
    this._prog.links.push({ id: uid("l"), from: src.nid, from_port: src.port, to: dst.nid, to_port: dst.port });
    this._markDirty();
    if (this._sel.size === 1) this._renderProps();
  }

  _pruneLinks(node) {
    const def = this._blocks[node.type];
    const names = new Set(this._inputPorts(def, node.params).map((p) => p.name));
    this._prog.links = this._prog.links.filter((l) => l.to !== node.id || names.has(l.to_port));
  }

  // ------------------------------------------------------------------ geometry
  _geom(node) {
    const def = this._blocks[node.type];
    const x = node.x;
    const y = node.y;
    if (!def) return { x, y, w: 120, h: 40, ins: [], outs: [], def: null };
    const w = def.width || 120;
    if (node.type === "comment") {
      const lines = this._commentLines(node, w);
      return { x, y, w, h: Math.max(30, lines.length * 14 + 12), ins: [], outs: [], def, lines };
    }
    const ins = this._inputPorts(def, node.params);
    const outs = def.outputs;
    const info = this._info(node, def);
    const infoH = info !== null ? INFO : 0;
    const rows = Math.max(ins.length, outs.length, 1);
    const top = y + HEAD + infoH;
    const h = HEAD + infoH + rows * ROW + 4;
    const mk = (p, i, dir) => ({
      ...p,
      py: top + ROW * i + ROW / 2 + 2,
      cx: dir === "in" ? x - STUB : x + w + STUB,
    });
    return { x, y, w, h, def, info, ins: ins.map((p, i) => mk(p, i, "in")), outs: outs.map((p, i) => mk(p, i, "out")) };
  }

  _commentLines(node, w) {
    const text = String(node.params?.text ?? "");
    const max = Math.max(8, Math.floor((w - 12) / 6.2));
    const out = [];
    for (const raw of text.split("\n")) {
      let line = raw;
      while (line.length > max) {
        let cut = line.lastIndexOf(" ", max);
        if (cut < max / 2) cut = max;
        out.push(line.slice(0, cut));
        line = line.slice(cut).trimStart();
      }
      out.push(line);
    }
    return out.slice(0, 40);
  }

  _entityName(eid) {
    if (!eid) return null;
    const st = this._hass && this._hass.states && this._hass.states[eid];
    return (st && st.attributes && st.attributes.friendly_name) || eid;
  }

  _info(node, def) {
    const p = node.params || {};
    switch (node.type) {
      case "entity_in":
      case "entity_out": {
        const n = this._entityName(p.entity_id) || t("(velg entitet)");
        return p.attribute ? `${n} · ${p.attribute}` : n;
      }
      case "setpoint":
      case "toggle":
      case "publish":
        return p.name || "";
      case "const_num":
        return fmt(Number(p.value ?? 0));
      case "const_bool":
        return p.value ? t("PÅ (1)") : t("AV (0)");
      case "formula":
        return p.expr || "";
      case "text_eq":
        return `= "${p.text ?? ""}"`;
      case "pid":
        return (p.direction === "direct" ? t("Direkte") : t("Revers")) + (Number(p.deadband) > 0 ? ` · ±${fmt(Number(p.deadband))}` : "");
      case "schedule":
        return this._schedSummary(p.periods);
      case "page_in":
      case "page_out":
        return p.name || t("(uten navn)");
      case "macro_in":
      case "macro_out":
        return `${p.name || "?"} · ${{ num: t("tall"), bool: t("av/på"), str: t("tekst"), any: t("valgfri") }[p.type] || p.type}`;
      case "knx_send":
      case "knx_read": {
        const dpt = p.dpt === "custom" ? p.dpt_custom || "?" : p.dpt;
        return `${p.address || t("(adresse)")} · ${dpt}`;
      }
      case "modbus_write":
        return `${p.hub || "?"} #${p.slave ?? 1} @${p.address ?? 0}${p.kind === "coil" ? " coil" : ""}`;
      default:
        if (node.type.startsWith(MACRO_PREFIX)) return def && def.title ? def.title : t("(ukjent makro)");
        return null;
    }
  }

  _schedSummary(periods) {
    if (!Array.isArray(periods) || !periods.length) return t("(ingen perioder)");
    const days = (ds) => {
      const s = [...new Set(ds)].map(Number).filter((d) => d >= 1 && d <= 7).sort();
      if (!s.length) return "–";
      const contiguous = s.every((d, i) => i === 0 || d === s[i - 1] + 1);
      if (s.length > 2 && contiguous) return `${dayNames()[s[0] - 1]}–${dayNames()[s[s.length - 1] - 1]}`;
      return s.map((d) => dayNames()[d - 1]).join(",");
    };
    const first = periods[0];
    const more = periods.length > 1 ? ` (+${periods.length - 1})` : "";
    return `${days(first.days || [])} ${first.on}–${first.off}${more}`;
  }

  _route(x1, y1, x2, y2, bottom) {
    if (x2 >= x1 + 4) {
      const mx = Math.round((x1 + x2) / 2 / 5) * 5;
      return `M${x1},${y1} H${mx} V${y2} H${x2}`;
    }
    const yc = bottom + 14;
    return `M${x1},${y1} H${x1 + 10} V${yc} H${x2 - 10} V${y2} H${x2}`;
  }

  _toWorld(cx, cy) {
    const r = this.$svg.getBoundingClientRect();
    return { x: (cx - r.left - this._view.x) / this._view.k, y: (cy - r.top - this._view.y) / this._view.k };
  }

  _hitPort(w, dir) {
    if (!this._prog) return null;
    const thr = Math.max(12, 16 / this._view.k);
    let best = null;
    let bestD = thr;
    for (const node of this._visible()) {
      const g = this._geom(node);
      if (w.x < g.x - 40 || w.x > g.x + g.w + 40 || w.y < g.y - 20 || w.y > g.y + g.h + 20) continue;
      const list = dir === "in" ? g.ins : g.outs;
      for (const p of list) {
        // Accept drops on the stub as well as inside the block near the pin label.
        const px = dir === "in" ? clamp(w.x, g.x - STUB - 4, g.x + 30) : clamp(w.x, g.x + g.w - 30, g.x + g.w + STUB + 4);
        const d = Math.hypot(w.x - px, w.y - p.py);
        if (d < bestD) {
          bestD = d;
          best = { nid: node.id, dir, port: p.name };
        }
      }
    }
    return best;
  }

  _fitView() {
    const vis = this._visible();
    if (!vis.length) {
      this._view = { x: 60, y: 50, k: 1 };
      return;
    }
    let x0 = Infinity;
    let y0 = Infinity;
    let x1 = -Infinity;
    let y1 = -Infinity;
    for (const n of vis) {
      const g = this._geom(n);
      x0 = Math.min(x0, g.x - 40);
      y0 = Math.min(y0, g.y - 30);
      x1 = Math.max(x1, g.x + g.w + 60);
      y1 = Math.max(y1, g.y + g.h + 30);
    }
    const r = this.$wrap.getBoundingClientRect();
    const W = r.width || 800;
    const H = r.height || 600;
    y0 -= 24; // room for the page tabs
    const k = clamp(Math.min(W / (x1 - x0), H / (y1 - y0)), 0.25, 1.5);
    this._view = { k, x: (W - (x1 - x0) * k) / 2 - x0 * k, y: (H - (y1 - y0) * k) / 2 - y0 * k };
    this._saveView();
  }

  _zoomAt(f, cx, cy) {
    const r = this.$svg.getBoundingClientRect();
    if (cx === undefined) {
      cx = r.left + r.width / 2;
      cy = r.top + r.height / 2;
    }
    const v = this._view;
    const k2 = clamp(v.k * f, 0.2, 3);
    const sx = cx - r.left;
    const sy = cy - r.top;
    const wx = (sx - v.x) / v.k;
    const wy = (sy - v.y) / v.k;
    this._view = { k: k2, x: sx - wx * k2, y: sy - wy * k2 };
    this._saveView();
    this._scheduleRender();
  }

  _saveView() {
    if (!this._prog) return;
    clearTimeout(this._viewTimer);
    this._views[this._page] = { ...this._view };
    const key = this._viewKey();
    this._viewTimer = setTimeout(() => {
      try {
        localStorage.setItem(key, JSON.stringify(this._view));
      } catch (_e) {
        /* ignore */
      }
    }, 400);
  }

  // ------------------------------------------------------------------ pointer interaction
  _onPointerDown(e) {
    if (!this._prog) return;
    this.$wrap.focus({ preventScroll: true });
    this._pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    try {
      this.$svg.setPointerCapture(e.pointerId);
    } catch (_e) {
      /* ignore */
    }
    if (this._pointers.size === 2) {
      const [a, b] = [...this._pointers.values()];
      this._drag = {
        mode: "pinch",
        d0: Math.hypot(a.x - b.x, a.y - b.y) || 1,
        view0: { ...this._view },
        c0: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 },
      };
      return;
    }
    if (this._pointers.size > 2) return;
    const w = this._toWorld(e.clientX, e.clientY);
    if (e.button === 1 || e.button === 2) {
      this._drag = { mode: "pan", sx: e.clientX, sy: e.clientY, vx: this._view.x, vy: this._view.y, moved: true };
      return;
    }
    const t = e.target;
    const portEl = t.closest && t.closest("[data-port]");
    const nodeEl = t.closest && t.closest("[data-node]");
    const linkEl = t.closest && t.closest("[data-link]");
    if (portEl) {
      const [nid, dir, port] = portEl.dataset.port.split("|");
      if (dir === "in") {
        const existing = this._linkTo(nid, port);
        if (existing && !e.shiftKey) {
          // Lift the existing wire off the input and keep dragging it from its source.
          this._pushUndo();
          this._prog.links = this._prog.links.filter((l) => l !== existing);
          this._markDirty();
          this._drag = { mode: "link", nid: existing.from, dir: "out", port: existing.from_port, x: w.x, y: w.y, lifted: true };
          this._scheduleRender();
          return;
        }
      }
      this._drag = { mode: "link", nid, dir, port, x: w.x, y: w.y };
      this._scheduleRender();
      return;
    }
    if (nodeEl) {
      const nid = nodeEl.dataset.node;
      const additive = e.shiftKey || e.ctrlKey || e.metaKey;
      if (additive) {
        if (this._sel.has(nid)) this._sel.delete(nid);
        else this._sel.add(nid);
      } else if (!this._sel.has(nid)) {
        this._sel = new Set([nid]);
      }
      this._selLink = null;
      const orig = new Map();
      for (const id of this._sel) {
        const n = this._node(id);
        if (n) orig.set(id, { x: n.x, y: n.y });
      }
      this._drag = { mode: "move", start: w, orig, moved: false, nid, additive };
      this._renderProps();
      this._scheduleRender();
      return;
    }
    if (linkEl) {
      this._selLink = linkEl.dataset.link;
      this._sel = new Set();
      this._drag = null;
      this._renderProps();
      this._scheduleRender();
      return;
    }
    if (e.shiftKey || e.ctrlKey || e.metaKey) {
      this._drag = { mode: "box", start: w, cur: w, additive: true };
    } else {
      this._drag = { mode: "pan", sx: e.clientX, sy: e.clientY, vx: this._view.x, vy: this._view.y, moved: false };
    }
  }

  _onPointerMove(e) {
    if (this._pointers.has(e.pointerId)) this._pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const d = this._drag;
    if (!d) return;
    if (d.mode === "pinch") {
      if (this._pointers.size < 2) return;
      const [a, b] = [...this._pointers.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y) || 1;
      const c = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
      const r = this.$svg.getBoundingClientRect();
      const v0 = d.view0;
      const k = clamp(v0.k * (dist / d.d0), 0.2, 3);
      const wx = (d.c0.x - r.left - v0.x) / v0.k;
      const wy = (d.c0.y - r.top - v0.y) / v0.k;
      this._view = { k, x: c.x - r.left - wx * k, y: c.y - r.top - wy * k };
      this._saveView();
      this._scheduleRender();
      return;
    }
    const w = this._toWorld(e.clientX, e.clientY);
    if (d.mode === "pan") {
      const dx = e.clientX - d.sx;
      const dy = e.clientY - d.sy;
      if (Math.abs(dx) + Math.abs(dy) > 3) d.moved = true;
      this._view.x = d.vx + dx;
      this._view.y = d.vy + dy;
      this._saveView();
    } else if (d.mode === "move") {
      const dx = snapG(w.x - d.start.x);
      const dy = snapG(w.y - d.start.y);
      if (!d.moved && (dx || dy)) {
        d.moved = true;
        this._pushUndo();
      }
      if (d.moved) {
        for (const [id, o] of d.orig) {
          const n = this._node(id);
          if (n) {
            n.x = o.x + dx;
            n.y = o.y + dy;
          }
        }
        this._dirty = true;
      }
    } else if (d.mode === "link") {
      d.x = w.x;
      d.y = w.y;
      d.hot = this._hitPort(w, d.dir === "out" ? "in" : "out");
    } else if (d.mode === "box") {
      d.cur = w;
    }
    this._scheduleRender();
  }

  _onPointerUp(e, cancelled) {
    this._pointers.delete(e.pointerId);
    try {
      this.$svg.releasePointerCapture(e.pointerId);
    } catch (_e) {
      /* ignore */
    }
    const d = this._drag;
    if (!d) return;
    if (d.mode === "pinch") {
      if (this._pointers.size === 0) this._drag = null;
      else this._drag = null;
      return;
    }
    this._drag = null;
    if (cancelled) {
      this._scheduleRender();
      return;
    }
    const w = this._toWorld(e.clientX, e.clientY);
    if (d.mode === "link") {
      const target = this._hitPort(w, d.dir === "out" ? "in" : "out");
      if (target) this._connect({ nid: d.nid, dir: d.dir, port: d.port }, target);
      else if (d.lifted && this._sel.size === 1) this._renderProps();
    } else if (d.mode === "pan" && !d.moved) {
      if (this._sel.size || this._selLink) {
        this._sel = new Set();
        this._selLink = null;
        this._renderProps();
      }
    } else if (d.mode === "box") {
      const x0 = Math.min(d.start.x, d.cur.x);
      const x1 = Math.max(d.start.x, d.cur.x);
      const y0 = Math.min(d.start.y, d.cur.y);
      const y1 = Math.max(d.start.y, d.cur.y);
      for (const n of this._visible()) {
        const g = this._geom(n);
        if (g.x >= x0 && g.x + g.w <= x1 && g.y >= y0 && g.y + g.h <= y1) this._sel.add(n.id);
      }
      this._selLink = null;
      this._renderProps();
    } else if (d.mode === "move") {
      if (d.moved) this._markDirty();
      else if (!d.additive && this._sel.size > 1) {
        this._sel = new Set([d.nid]);
        this._renderProps();
      }
    }
    this._scheduleRender();
  }

  _onWheel(e) {
    e.preventDefault();
    if (e.ctrlKey || Math.abs(e.deltaY) >= Math.abs(e.deltaX)) {
      const f = Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0015));
      this._zoomAt(f, e.clientX, e.clientY);
    } else {
      this._view.x -= e.deltaX;
      this._saveView();
      this._scheduleRender();
    }
  }

  _nodeAt(w) {
    if (!this._prog) return null;
    const vis = this._visible();
    for (let i = vis.length - 1; i >= 0; i--) {
      const n = vis[i];
      const g = this._geom(n);
      if (w.x >= g.x && w.x <= g.x + g.w && w.y >= g.y && w.y <= g.y + g.h) return n;
    }
    return null;
  }

  _onDblClick(e) {
    const hit = this._nodeAt(this._toWorld(e.clientX, e.clientY));
    if (hit) {
      this._sel = new Set([hit.id]);
      this._showProps = true;
      if (this._narrow) this._showPalette = false;
      this._applyLayout();
      this._renderProps();
      const first = this.$props.querySelector("input,select,textarea");
      if (first) first.focus();
    } else {
      this._showPalette = true;
      if (this._narrow) this._showProps = false;
      this._applyLayout();
      const s = this.$palette.querySelector(".search");
      if (s) s.focus();
    }
  }

  _onKey(e) {
    const tag = (e.composedPath()[0] || {}).tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    const mod = e.ctrlKey || e.metaKey;
    const k = e.key.toLowerCase();
    if (k === "delete" || k === "backspace") {
      this._deleteSelection();
      e.preventDefault();
    } else if (mod && k === "z" && !e.shiftKey) {
      this._undoStep();
      e.preventDefault();
    } else if (mod && (k === "y" || (k === "z" && e.shiftKey))) {
      this._redoStep();
      e.preventDefault();
    } else if (mod && k === "c") {
      this._copy();
      e.preventDefault();
    } else if (mod && k === "v") {
      this._paste();
      e.preventDefault();
    } else if (mod && k === "d") {
      this._copy();
      this._paste();
      e.preventDefault();
    } else if (mod && k === "a") {
      this._sel = new Set(this._visible().map((n) => n.id));
      this._renderProps();
      this._scheduleRender();
      e.preventDefault();
    } else if (mod && k === "s") {
      this._save();
      e.preventDefault();
    } else if (k === "escape") {
      this._sel = new Set();
      this._selLink = null;
      this._renderProps();
      this._scheduleRender();
    } else if (k.startsWith("arrow") && this._sel.size) {
      const step = e.shiftKey ? GRID * 5 : GRID;
      const dx = k === "arrowleft" ? -step : k === "arrowright" ? step : 0;
      const dy = k === "arrowup" ? -step : k === "arrowdown" ? step : 0;
      this._pushUndo();
      for (const id of this._sel) {
        const n = this._node(id);
        if (n) {
          n.x += dx;
          n.y += dy;
        }
      }
      this._markDirty();
      e.preventDefault();
    }
  }

  // ------------------------------------------------------------------ rendering: canvas
  _scheduleRender() {
    if (this._rafPending) return;
    this._rafPending = true;
    requestAnimationFrame(() => {
      this._rafPending = false;
      this._render();
    });
  }

  _render() {
    if (!this._prog) return;
    const v = this._view;
    this.$vp.setAttribute("transform", `translate(${v.x},${v.y}) scale(${v.k})`);
    const gs = 20 * v.k;
    this.$pattern.setAttribute("width", gs);
    this.$pattern.setAttribute("height", gs);
    this.$pattern.setAttribute("x", v.x % gs);
    this.$pattern.setAttribute("y", v.y % gs);
    this.$pattern.firstElementChild.setAttribute("r", Math.max(0.6, v.k));

    const snapNodes = (this._snap && this._snap.nodes) || {};
    const order = (this._snap && this._snap.order) || {};
    const geoms = new Map();
    const vis = this._visible();
    for (const n of vis) geoms.set(n.id, this._geom(n));

    const wires = [];
    for (const l of this._prog.links) {
      const gs1 = geoms.get(l.from);
      const gs2 = geoms.get(l.to);
      if (!gs1 && !gs2) continue;
      if (!gs1 || !gs2) {
        // Wire to/from another page: draw a short dashed stub with the page name.
        const other = this._node(gs1 ? l.to : l.from);
        if (!other) continue;
        const pname = this._pageName(other.page);
        if (gs2) {
          const ip = gs2.ins.find((p) => p.name === l.to_port);
          if (!ip) continue;
          wires.push(
            `<line class="offpage-l" x1="${ip.cx - 26}" y1="${ip.py}" x2="${ip.cx}" y2="${ip.py}"></line><text class="offpage" x="${ip.cx - 28}" y="${ip.py + 3}" text-anchor="end">⇠ ${esc(trunc(pname, 14))}: ${esc(trunc(other.label || this._blocks[other.type]?.symbol || other.type, 12))}.${esc(l.from_port)}</text>`
          );
        } else {
          const op = gs1.outs.find((p) => p.name === l.from_port);
          if (!op) continue;
          wires.push(
            `<line class="offpage-l" x1="${op.cx}" y1="${op.py + 6}" x2="${op.cx + 20}" y2="${op.py + 6}"></line><text class="offpage" x="${op.cx + 22}" y="${op.py + 9}">⇢ ${esc(trunc(pname, 14))}</text>`
          );
        }
        continue;
      }
      const op = gs1.outs.find((p) => p.name === l.from_port);
      const ip = gs2.ins.find((p) => p.name === l.to_port);
      if (!op || !ip) continue;
      const bottom = Math.max(gs1.y + gs1.h, gs2.y + gs2.h);
      const d = this._route(op.cx, op.py, ip.cx, ip.py, bottom);
      const sv = snapNodes[l.from] && snapNodes[l.from].o ? snapNodes[l.from].o[l.from_port] : undefined;
      const cls = this._wireClass(op.type, sv, l.id === this._selLink);
      wires.push(
        `<path class="wire-hit" data-link="${esc(l.id)}" d="${d}"></path><path class="${cls}" data-wv="${esc(l.from)}|${esc(l.from_port)}" data-wt="${op.type}"${l.id === this._selLink ? ' data-sel="1"' : ""} d="${d}" pointer-events="none"></path>`
      );
    }

    const blocks = [];
    for (const n of vis) {
      blocks.push(this._nodeSvg(n, geoms.get(n.id), snapNodes[n.id], order[n.id]));
    }

    let overlay = "";
    const d = this._drag;
    if (d && d.mode === "link") {
      const g = geoms.get(d.nid);
      const list = g ? (d.dir === "out" ? g.outs : g.ins) : [];
      const p = list.find((x) => x.name === d.port);
      if (p) {
        let tx = d.x;
        let ty = d.y;
        if (d.hot) {
          const hg = geoms.get(d.hot.nid);
          const hp = hg && (d.hot.dir === "in" ? hg.ins : hg.outs).find((x) => x.name === d.hot.port);
          if (hp) {
            tx = hp.cx;
            ty = hp.py;
          }
        }
        const path = d.dir === "out" ? this._route(p.cx, p.py, tx, ty, Math.max(g.y + g.h, ty)) : this._route(tx, ty, p.cx, p.py, Math.max(g.y + g.h, ty));
        overlay += `<path class="wire temp" d="${path}"></path>`;
      }
    } else if (d && d.mode === "box") {
      const x = Math.min(d.start.x, d.cur.x);
      const y = Math.min(d.start.y, d.cur.y);
      overlay += `<rect class="boxsel" x="${x}" y="${y}" width="${Math.abs(d.cur.x - d.start.x)}" height="${Math.abs(d.cur.y - d.start.y)}"></rect>`;
    }

    let empty = "";
    if (!vis.length) {
      empty = `<text class="empty-hint" x="20" y="40">${t("Dra blokker inn fra paletten til venstre (eller trykk på dem) for å starte.")}</text>
        <text class="empty-hint" x="20" y="64" style="font-size:12px">${t("Koble utgang → inngang ved å dra fra pinnene. Lagre for å starte programmet.")}</text>`;
      if (this._prog.pages.length > 1)
        empty += `<text class="empty-hint" x="20" y="88" style="font-size:12px">${t("Signaler mellom sider: bruk «Koblingspunkt (sender)» og «(mottaker)» med samme navn.")}</text>`;
    }

    this.$vp.innerHTML = `<g class="wires">${wires.join("")}</g><g class="blocks">${blocks.join("")}</g>${overlay}${empty}`;
    this._renderStatus();
  }

  _wireClass(type, v, sel) {
    let cls = "wire " + type;
    if (type === "bool" && typeof v === "boolean") cls += v ? " on" : " off";
    if (sel) cls += " sel";
    return cls;
  }

  _valClass(v) {
    return "val " + (typeof v === "boolean" ? (v ? "t" : "f") : typeof v === "number" ? "n" : "s");
  }

  _infoMax(w) {
    return Math.floor((w - 10) / 5.6);
  }

  /* Update only the live parts of the drawing (values, wire states, errors). */
  _updateLive() {
    const s = this._snap || {};
    const nodes = s.nodes || {};
    const order = s.order || {};
    for (const el of this.$vp.querySelectorAll("text[data-v]")) {
      const [nid, port] = el.dataset.v.split("|");
      const lv = this._liveVal(nodes[nid], port);
      if (!lv) {
        if (el.textContent) el.textContent = "";
        continue;
      }
      if (el.textContent !== lv.txt) el.textContent = lv.txt;
      if (el.getAttribute("class") !== lv.cls) el.setAttribute("class", lv.cls);
    }
    for (const el of this.$vp.querySelectorAll("path[data-wv]")) {
      const [nid, port] = el.dataset.wv.split("|");
      const o = nodes[nid] && nodes[nid].o;
      const cls = this._wireClass(el.dataset.wt, o ? o[port] : undefined, !!el.dataset.sel);
      if (el.getAttribute("class") !== cls) el.setAttribute("class", cls);
    }
    for (const g of this.$vp.querySelectorAll("g.blk[data-node]")) {
      const nid = g.dataset.node;
      const sn = nodes[nid];
      const err = sn && sn.e ? sn.e : "";
      if (g.dataset.kind === "comment") continue;
      g.classList.toggle("err", !!err);
      const mark = g.querySelector("[data-errmark]");
      if (mark && mark.textContent !== (err ? " ⚠" : "")) mark.textContent = err ? " ⚠" : "";
      const title = g.querySelector("title");
      if (title) {
        const t = (title.dataset.base || "") + (err ? "\n⚠ " + err : "");
        if (title.textContent !== t) title.textContent = t;
      }
      const ord = g.querySelector("[data-ord]");
      const ot = order[nid] ? "#" + order[nid] : "";
      if (ord && ord.textContent !== ot) ord.textContent = ot;
      const info = g.querySelector("[data-infobase]");
      if (info && sn && sn.v !== undefined && sn.v !== null) {
        const t = trunc(`${info.dataset.infobase}: ${fmt(sn.v)}`, parseInt(info.dataset.max, 10) || 20);
        if (info.textContent !== t) info.textContent = t;
      }
    }
    this._renderStatus();
  }

  /* Text and class for a live output value ("F" prefix when forced). */
  _liveVal(sn, port) {
    const o = sn && sn.o;
    if (!o || !Object.prototype.hasOwnProperty.call(o, port)) return null;
    const fz = !!(sn.f && Object.prototype.hasOwnProperty.call(sn.f, port));
    return { txt: (fz ? "F " : "") + fmt(o[port]), cls: this._valClass(o[port]) + (fz ? " fz" : ""), fz };
  }

  _nodeSvg(n, g, sn, ord) {
    const def = g.def;
    const sel = this._sel.has(n.id);
    const err = sn && sn.e;
    if (!def) {
      return `<g class="blk err" data-node="${esc(n.id)}"><rect class="blk-body" x="${g.x}" y="${g.y}" width="${g.w}" height="${g.h}" rx="4"></rect>
        <text class="blk-info" x="${g.x + 6}" y="${g.y + 24}">${esc(t("Ukjent blokk: {type}", { type: n.type }))}</text></g>`;
    }
    if (n.type === "comment") {
      const lines = g.lines.map((ln, i) => `<tspan x="${g.x + 6}" y="${g.y + 16 + i * 14}">${esc(ln)}</tspan>`).join("");
      return `<g class="blk${sel ? " sel" : ""}" data-node="${esc(n.id)}" data-kind="comment"><rect class="cmt-body" x="${g.x}" y="${g.y}" width="${g.w}" height="${g.h}" rx="2"></rect>
        <text class="cmt-t">${lines}</text></g>`;
    }
    const color = CAT_COLORS[def.category] || "#546e7a";
    const { x, y, w, h } = g;
    const parts = [];
    const tbase = `${def.title}${n.label ? " – " + n.label : ""}`;
    const isMacro = n.type.startsWith(MACRO_PREFIX);
    parts.push(`<g class="blk${sel ? " sel" : ""}${err ? " err" : ""}${isMacro ? " macro" : ""}" data-node="${esc(n.id)}">`);
    parts.push(`<title data-base="${esc(tbase)}">${esc(tbase)}${err ? "\n⚠ " + esc(err) : ""}</title>`);
    if (n.label) parts.push(`<text class="blk-label" x="${x}" y="${y - 5}">${esc(trunc(n.label, 40))}</text>`);
    parts.push(`<rect class="blk-body" x="${x}" y="${y}" width="${w}" height="${h}" rx="4"></rect>`);
    parts.push(`<path d="M${x},${y + 4} a4,4 0 0 1 4,-4 H${x + w - 4} a4,4 0 0 1 4,4 V${y + HEAD} H${x} Z" fill="${color}"></path>`);
    parts.push(`<text class="blk-head-t" x="${x + 6}" y="${y + 15}">${esc(def.symbol)}<tspan data-errmark="1">${err ? " ⚠" : ""}</tspan></text>`);
    parts.push(`<text class="blk-ord" data-ord="1" x="${x + w - 5}" y="${y + 14}" text-anchor="end">${ord ? "#" + ord : ""}</text>`);
    if (g.info !== null && g.info !== undefined) {
      const maxc = this._infoMax(w);
      let info = g.info;
      const live = n.type === "setpoint" || n.type === "toggle";
      if (live && sn && sn.v !== undefined && sn.v !== null) info = `${info}: ${fmt(sn.v)}`;
      const extra = live ? ` data-infobase="${esc(g.info)}" data-max="${maxc}"` : "";
      parts.push(`<text class="blk-info"${extra} x="${x + 5}" y="${y + HEAD + 12}">${esc(trunc(info, maxc))}</text>`);
    }
    for (const p of g.ins) {
      const linked = this._linkTo(n.id, p.name);
      parts.push(`<line class="pin-stub" x1="${p.cx}" y1="${p.py}" x2="${x}" y2="${p.py}"></line>`);
      parts.push(`<text class="pin-lbl" x="${x + 4}" y="${p.py + 3.5}">${esc(p.label)}</text>`);
      if (!linked) {
        const set = n.consts && Object.prototype.hasOwnProperty.call(n.consts, p.name);
        const val = set ? n.consts[p.name] : p.default;
        if (val !== null && val !== undefined && val !== "") {
          parts.push(`<text class="const${set ? " set" : ""}" x="${p.cx - 4}" y="${p.py + 3.5}" text-anchor="end">${esc(fmt(val))}</text>`);
        }
      }
      const hot = this._drag && this._drag.hot && this._drag.hot.nid === n.id && this._drag.hot.dir === "in" && this._drag.hot.port === p.name;
      parts.push(`<circle class="pin-hit" data-port="${esc(n.id)}|in|${esc(p.name)}" cx="${p.cx}" cy="${p.py}" r="8"></circle>`);
      parts.push(`<circle class="pin-dot ${p.type}${hot ? " hot" : ""}" cx="${p.cx}" cy="${p.py}" r="3.2" pointer-events="none"></circle>`);
    }
    for (const p of g.outs) {
      parts.push(`<line class="pin-stub" x1="${x + w}" y1="${p.py}" x2="${p.cx}" y2="${p.py}"></line>`);
      parts.push(`<text class="pin-lbl" x="${x + w - 4}" y="${p.py + 3.5}" text-anchor="end">${esc(p.label)}</text>`);
      const hot = this._drag && this._drag.hot && this._drag.hot.nid === n.id && this._drag.hot.dir === "out" && this._drag.hot.port === p.name;
      parts.push(`<circle class="pin-hit" data-port="${esc(n.id)}|out|${esc(p.name)}" cx="${p.cx}" cy="${p.py}" r="8"></circle>`);
      parts.push(`<circle class="pin-dot ${p.type}${hot ? " hot" : ""}" cx="${p.cx}" cy="${p.py}" r="3.2" pointer-events="none"></circle>`);
      const lv = this._liveVal(sn, p.name);
      parts.push(
        `<text class="${lv ? lv.cls : "val"}" data-v="${esc(n.id)}|${esc(p.name)}" x="${p.cx + 5}" y="${p.py - 3}">${lv ? esc(lv.txt) : ""}</text>`
      );
    }
    parts.push("</g>");
    return parts.join("");
  }

  _renderStatus() {
    const s = this._snap;
    const bits = [];
    if (this._isNew) bits.push(`<span class="warn">${t("Ikke lagret ennå")}</span>`);
    else if (this._kind === "macro" && !this._live) bits.push(t("Makro – åpne «Vis live» fra en instans for online-verdier"));
    else if (this._online && s) {
      bits.push(s.running ? `<span class="run">● ${t("Kjører")}</span>` : `<span class="stop">■ ${t("Stoppet")}</span>`);
      bits.push(s.events ? t("skann {n} ({e} ved endring)", { n: s.scan ?? 0, e: s.events }) : t("skann {n}", { n: s.scan ?? 0 }));
      if (s.ms !== undefined) bits.push(`${s.ms} ms`);
      if (s.forced) bits.push(`<span class="fz">⚑ ${t("{n} tvangsstyrt", { n: s.forced })}</span>`);
      const errs = Object.values(s.nodes || {}).filter((x) => x.e).length;
      if (errs) bits.push(`<span class="warn">⚠ ${tn(errs, "{n} blokk med feil", "{n} blokker med feil")}</span>`);
      if (s.warnings && s.warnings.length) bits.push(`<span class="warn">${tn(s.warnings.length, "{n} advarsel", "{n} advarsler")}</span>`);
    } else if (!this._online) bits.push(t("Offline-visning"));
    if (this._dirty && !this._isNew) bits.push(`<span class="warn">${t("Ulagrede endringer")}</span>`);
    if (!this._narrow) {
      const nv = this._visible().length;
      const nt = this._prog.nodes.length;
      bits.push(nv === nt ? tn(nt, "{n} blokk", "{n} blokker") : t("{v} av {n} blokker", { v: nv, n: nt }));
      bits.push(`${Math.round(this._view.k * 100)} %`);
    }
    this.$status.innerHTML = bits.join(" · ");
  }

  _applySnapshot() {
    if (!this._rafPending && this._prog) this._updateLive();
    const s = this._snap;
    if (!s) return;
    for (const el of this.$props.querySelectorAll("[data-live]")) {
      const [nid, kind, port] = el.dataset.live.split("|");
      let v;
      if (nid === "prog") {
        if (kind === "scan") v = s.scan;
        else if (kind === "events") v = s.events;
        else if (kind === "ms") v = s.ms;
        else if (kind === "running") v = s.running ? t("Kjører") : t("Stoppet");
        else if (kind === "forced") v = s.forced || 0;
        el.textContent = v ?? "–";
        continue;
      }
      const sn = s.nodes && s.nodes[nid];
      if (!sn) continue;
      if (kind === "o") {
        const lv = this._liveVal(sn, port);
        el.textContent = lv ? lv.txt : "–";
        el.classList.toggle("fz", !!(lv && lv.fz));
        continue;
      } else if (kind === "v") v = sn.v;
      else if (kind === "src") {
        const [snid, sport] = port.split(":");
        const ss = s.nodes[snid];
        v = ss && ss.o ? ss.o[sport] : undefined;
      } else if (kind === "e") {
        el.textContent = sn.e ? "⚠ " + sn.e : "";
        continue;
      }
      el.textContent = fmt(v);
    }
  }

  // ------------------------------------------------------------------ rendering: palette
  _renderPalette(filter) {
    const f = (filter || "").trim().toLowerCase();
    const search = this.$palette.querySelector(".search");
    const html = [];
    const macroMode = this._kind === "macro";
    const self = macroMode && this._prog ? MACRO_PREFIX + this._prog.id : null;
    const cats = macroMode ? [...this._categories].sort((a, b) => (b.id === "macro_io") - (a.id === "macro_io")) : this._categories;
    for (const cat of cats) {
      if (cat.id === "macro_io" && !macroMode) continue;
      const items = Object.values(this._blocks).filter(
        (b) =>
          b.category === cat.id &&
          b.type !== self &&
          (!f || b.title.toLowerCase().includes(f) || b.type.includes(f) || b.symbol.toLowerCase().includes(f) || b.description.toLowerCase().includes(f))
      );
      if (!items.length) continue;
      const color = CAT_COLORS[cat.id] || "#546e7a";
      html.push(`<details open${cat.id === "macro_io" ? ' class="mio"' : ""}><summary>${esc(cat.title)}</summary>`);
      for (const b of items) {
        html.push(
          `<div class="item" draggable="true" data-type="${esc(b.type)}" title="${esc(b.description)}"><span class="sym" style="background:${color}">${esc(b.symbol || "¶")}</span><span>${esc(b.title)}</span></div>`
        );
      }
      html.push(`</details>`);
    }
    if (!search) {
      this.$palette.innerHTML = `<input class="search" type="search" placeholder="${t("Søk blokk…")}"><div class="cats">${html.join("")}</div>`;
    } else {
      this.$palette.querySelector(".cats").innerHTML = html.join("") || `<div class="hint">${t("Ingen treff")}</div>`;
    }
  }

  // ------------------------------------------------------------------ rendering: properties
  _entityDatalist() {
    const states = (this._hass && this._hass.states) || {};
    const ids = Object.keys(states).sort();
    return `<datalist id="fbd-entities">${ids
      .map((id) => `<option value="${esc(id)}">${esc(states[id].attributes?.friendly_name || "")}</option>`)
      .join("")}</datalist>`;
  }

  _entityHint(eid) {
    if (!eid) return "";
    const st = this._hass && this._hass.states && this._hass.states[eid];
    if (!st) return `<span style="color:var(--error-color,#c62828)">${t("Finnes ikke")}</span>`;
    const unit = st.attributes?.unit_of_measurement ? " " + st.attributes.unit_of_measurement : "";
    return `${esc(st.attributes?.friendly_name || eid)} · <b>${esc(st.state)}${esc(unit)}</b>`;
  }

  _paramField(node, p) {
    const val = node.params[p.name] !== undefined ? node.params[p.name] : p.default;
    const f = `param:${p.name}`;
    let input;
    switch (p.type) {
      case "bool":
        return `<label class="row"><input type="checkbox" data-f="${esc(f)}" ${val ? "checked" : ""}> ${esc(p.label)}</label>`;
      case "number":
        input = `<input type="number" data-f="${esc(f)}" value="${esc(val)}" step="${p.step ?? "any"}" ${p.min !== undefined ? `min="${p.min}"` : ""} ${p.max !== undefined ? `max="${p.max}"` : ""}>`;
        break;
      case "select":
        input = `<select data-f="${esc(f)}">${(p.options || [])
          .map((o) => `<option value="${esc(o.value)}" ${o.value === val ? "selected" : ""}>${esc(o.label)}</option>`)
          .join("")}</select>`;
        break;
      case "textarea":
        input = `<textarea data-f="${esc(f)}">${esc(val)}</textarea>`;
        break;
      case "schedule":
        return `<div class="field"><span>${esc(p.label)}</span>${this._schedEditor(Array.isArray(val) ? val : [])}</div>`;
      case "entity":
        input = `<input type="text" data-f="${esc(f)}" value="${esc(val)}" list="fbd-entities" placeholder="${t("domene.entitet")}" autocomplete="off" spellcheck="false">
          <div class="hint" data-enthint="${esc(val)}">${this._entityHint(val)}</div>`;
        break;
      default:
        if (p.suggest && p.suggest.length) {
          // Free text with suggestions; the list id is per field, only one block is edited at a time.
          const id = `fbd-sug-${p.name}`;
          input = `<input type="text" data-f="${esc(f)}" value="${esc(val)}" list="${esc(id)}" autocomplete="off" spellcheck="false">
            <datalist id="${esc(id)}">${p.suggest.map((o) => `<option value="${esc(o.value)}">${esc(o.label)}</option>`).join("")}</datalist>`;
        } else {
          input = `<input type="text" data-f="${esc(f)}" value="${esc(val)}" spellcheck="false">`;
        }
    }
    return `<div class="field"><span>${esc(p.label)}</span>${input}${p.help ? `<div class="hint">${esc(p.help)}</div>` : ""}</div>`;
  }

  _schedEditor(periods) {
    const rows = periods.map((per, i) => {
      const days = new Set((per.days || []).map(Number));
      const btns = dayNames().map(
        (d, j) => `<button data-act="sched-day" data-i="${i}" data-d="${j + 1}" class="${days.has(j + 1) ? "on" : ""}">${d}</button>`
      ).join("");
      return `<div class="sched"><div class="days">${btns}</div>
        <div class="times">${t("på")} <input type="time" data-f="sched:${i}:on" value="${esc(per.on || "07:00")}">
        ${t("av")} <input type="time" data-f="sched:${i}:off" value="${esc(per.off || "16:00")}">
        <button class="tiny" data-act="sched-del" data-i="${i}" title="${t("Fjern perioden")}">✕</button></div></div>`;
    });
    return `${rows.join("")}<button class="tiny" data-act="sched-add">${t("＋ Legg til periode")}</button>
      <div class="hint">${t("Er av-tiden før på-tiden, varer perioden over midnatt.")}</div>`;
  }

  _schedAction(act, btn) {
    const node = this._sel.size === 1 ? this._node([...this._sel][0]) : null;
    if (!node || node.type !== "schedule") return;
    this._pushUndo();
    const periods = clone(Array.isArray(node.params.periods) ? node.params.periods : []);
    const i = parseInt(btn.dataset.i, 10);
    if (act === "sched-add") {
      const last = periods[periods.length - 1];
      periods.push(last ? clone(last) : { days: [1, 2, 3, 4, 5], on: "07:00", off: "16:00" });
    } else if (act === "sched-del" && periods[i]) {
      periods.splice(i, 1);
    } else if (act === "sched-day" && periods[i]) {
      const d = parseInt(btn.dataset.d, 10);
      const set = new Set((periods[i].days || []).map(Number));
      if (set.has(d)) set.delete(d);
      else set.add(d);
      periods[i].days = [...set].sort();
    }
    node.params.periods = periods;
    this._markDirty();
    this._renderProps();
  }

  _constField(node, port) {
    const set = Object.prototype.hasOwnProperty.call(node.consts, port.name);
    const val = set ? node.consts[port.name] : port.default;
    const f = `const:${port.name}`;
    if (port.type === "bool") {
      return `<input type="checkbox" data-f="${esc(f)}" ${val ? "checked" : ""} title="${t("Konstant verdi")}">`;
    }
    if (port.type === "num") {
      return `<input type="number" step="any" data-f="${esc(f)}" value="${esc(val ?? 0)}" title="${t("Konstant verdi")}">`;
    }
    return `<input type="text" data-f="${esc(f)}" value="${esc(val ?? "")}" title="${t("Konstant verdi")}">`;
  }

  _renderProps() {
    if (!this.$props) return;
    if (!this._prog) {
      this.$props.innerHTML = `<div class="loading">${t("Laster…")}</div>`;
      return;
    }
    if (this._selLink) {
      const l = this._prog.links.find((x) => x.id === this._selLink);
      if (l) {
        const a = this._node(l.from);
        const b = this._node(l.to);
        const an = a ? this._blocks[a.type]?.symbol || a.type : "?";
        const bn = b ? this._blocks[b.type]?.symbol || b.type : "?";
        const sig = `${this._fullId(l.from)}|${l.from_port}`;
        const canTrend = this._livePid && this._kind === "program" && !this._trend.signals.includes(sig);
        this.$props.innerHTML = `<h3>${t("Tråd")}</h3>
          <div class="desc">${esc(a?.label || an)}.<b>${esc(l.from_port)}</b> → ${esc(b?.label || bn)}.<b>${esc(l.to_port)}</b></div>
          <div class="row">${t("Verdi:")} <span class="live" data-live="${esc(l.from)}|o|${esc(l.from_port)}">–</span></div>
          <div class="btns"><button class="danger" data-act="del-link">${t("Slett tråd")}</button>${canTrend ? `<button data-act="trend-add" data-sig="${esc(sig)}">📈 ${t("Legg i trend")}</button>` : ""}</div>`;
        this._applySnapshot();
        return;
      }
    }
    if (this._sel.size > 1) {
      this.$props.innerHTML = `<h3>${t("{n} blokker valgt", { n: this._sel.size })}</h3>
        <div class="desc">${t("Dra for å flytte. Ctrl+C / Ctrl+V for å kopiere, Delete for å slette.")}</div>
        ${this._movePageField()}
        <div class="btns"><button data-act="dup-node">${t("Dupliser")}</button><button class="danger" data-act="del-node">${t("Slett")}</button></div>
        <div class="btns"><button data-act="make-macro" title="${t("Erstatt utvalget med en ny makroblokk")}">${t("▣ Lag makro av utvalget")}</button></div>
        <div class="hint">${t("Tråder inn til og ut av utvalget blir inn- og utganger på makroen.")}</div>`;
      return;
    }
    if (this._sel.size === 1) {
      const node = this._node([...this._sel][0]);
      if (node) {
        this._renderNodeProps(node);
        return;
      }
    }
    this._renderProgramProps();
  }

  _renderNodeProps(node) {
    const def = this._blocks[node.type];
    if (!def) {
      this.$props.innerHTML = `<h3>${t("Ukjent blokk")}</h3><div class="err">${t("Blokktypen «{type}» finnes ikke i denne versjonen.", { type: esc(node.type) })}</div>
        <div class="btns"><button class="danger" data-act="del-node">${t("Slett")}</button></div>`;
      return;
    }
    const h = [];
    const nid = node.id;
    h.push(`<h3>${esc(def.title)}</h3><div class="desc">${esc(def.description)}</div>`);
    h.push(`<div class="err" data-live="${esc(nid)}|e|"></div>`);
    if (node.type !== "comment") {
      h.push(`<div class="field"><span>${t("Navn på tegningen (valgfritt)")}</span><input type="text" data-f="label" value="${esc(node.label || "")}"></div>`);
    }
    if (def.params.length) {
      h.push(`<h4>${t("Innstillinger")}</h4>`);
      for (const p of def.params) {
        if (p.show_if) {
          const cur = node.params[p.show_if.param] !== undefined ? node.params[p.show_if.param] : def.params.find((x) => x.name === p.show_if.param)?.default;
          if (!p.show_if.in.includes(cur)) continue;
        }
        h.push(this._paramField(node, p));
      }
    }
    const ins = this._inputPorts(def, node.params);
    if (ins.length) {
      h.push(`<h4>${t("Innganger")}</h4>`);
      for (const p of ins) {
        const l = this._linkTo(nid, p.name);
        if (l) {
          const src = this._node(l.from);
          const sname = src ? src.label || this._blocks[src.type]?.symbol || src.type : "?";
          h.push(
            `<div class="row"><span class="pn">${esc(p.label)}</span><span class="linked">← ${esc(sname)}.${esc(l.from_port)}</span><span class="live" data-live="${esc(nid)}|src|${esc(l.from)}:${esc(l.from_port)}">–</span></div>`
          );
        } else {
          h.push(`<div class="row"><span class="pn">${esc(p.label)}</span>${this._constField(node, p)}</div>`);
        }
      }
    }
    if (def.outputs.length) {
      const live = this._online && !!this._livePid && !this._dirtyNode(nid);
      h.push(`<h4>${t("Utganger")}${this._online ? " (live)" : ""}</h4>`);
      const sn = this._snap && this._snap.nodes && this._snap.nodes[nid];
      for (const p of def.outputs) {
        const forced = !!(sn && sn.f && Object.prototype.hasOwnProperty.call(sn.f, p.name));
        const sig = `${this._fullId(nid)}|${p.name}`;
        let extra = "";
        if (live) {
          if (forced) {
            extra = `<button class="small" data-act="force-release" data-node="${esc(nid)}" data-port="${esc(p.name)}" title="${t("Frigi tvangsstyringen")}">${t("Frigi")}</button>`;
          } else {
            const inp =
              p.type === "bool"
                ? `<input type="checkbox" class="fzin" data-fzin="${esc(p.name)}" title="${t("Verdi å tvinge til")}" style="flex:none;width:auto">`
                : `<input type="text" class="fzin" data-fzin="${esc(p.name)}" placeholder="${t("verdi")}" title="${t("Verdi å tvinge til")}">`;
            extra = `${inp}<button class="small" data-act="force-set" data-node="${esc(nid)}" data-port="${esc(p.name)}" title="${t("Tving utgangen til verdien")}">${t("Tving")}</button>`;
          }
          if (this._kind === "program" && !this._trend.signals.includes(sig) && p.type !== "str") {
            extra += `<button class="small" data-act="trend-add" data-sig="${esc(sig)}" title="${t("Legg i trend")}">📈</button>`;
          }
        }
        h.push(
          `<div class="row"><span class="pn">${esc(p.label)}</span><span class="live" data-live="${esc(nid)}|o|${esc(p.name)}">–</span>${extra}</div>`
        );
      }
      if (live) h.push(`<div class="hint">${t("Tving overstyrer utgangen i det kjørende programmet (som i en PLS) til du frigir den. Gjelder til den frigis, også etter omstart.")}</div>`);
    }
    if (node.type.startsWith(MACRO_PREFIX)) {
      h.push(`<h4>${t("Makro")}</h4><div class="btns" style="margin-top:0"><button data-act="open-macro" data-node="${esc(nid)}">${t("▣ Åpne makro")}</button>`);
      if (this._livePid && !this._isNew) h.push(`<button data-act="open-macro-live" data-node="${esc(nid)}">${t("● Vis live innhold")}</button>`);
      h.push(`</div><div class="hint">${t("Endringer i makroen gjelder alle steder den brukes.")}</div>`);
    }
    h.push(this._movePageField());
    if ((def.ha === "setpoint" || def.ha === "toggle") && !this._isNew && this._kind === "program") {
      h.push(`<h4>${t("Verdi i HA")}</h4>`);
      const cur = this._snap && this._snap.nodes && this._snap.nodes[nid] ? this._snap.nodes[nid].v : undefined;
      if (def.ha === "toggle") {
        h.push(`<div class="row"><input type="checkbox" data-liveinput="${esc(nid)}" ${cur ? "checked" : ""}> ${t("På")} <button class="small" data-act="set-live" data-node="${esc(nid)}">${t("Sett")}</button></div>`);
      } else {
        h.push(
          `<div class="row"><input type="number" step="any" data-liveinput="${esc(nid)}" value="${esc(cur ?? "")}"><button class="small" data-act="set-live" data-node="${esc(nid)}">${t("Sett")}</button></div>`
        );
      }
      h.push(`<div class="hint">${t("Nå:")} <span class="live" data-live="${esc(nid)}|v|">–</span>. ${t("Kan også endres fra dashboard (entiteten opprettes ved lagring).")}</div>`);
    }
    if (def.ha === "entity_out") {
      h.push(`<div class="hint" style="margin-top:8px">${t("Skriver bare ved endring. Handling «Automatisk» velger tjeneste ut fra domenet: lys (av/på eller lysstyrke %), cover/valve (posisjon), climate (temperatur), number (sett verdi), select (alternativ), knapp/script/scene (trykk).")}</div>`);
    }
    h.push(`<div class="btns"><button data-act="dup-node">${t("Dupliser")}</button><button class="danger" data-act="del-node">${t("Slett blokk")}</button></div>`);
    h.push(`<div class="hint" style="margin-top:10px">ID: <code>${esc(nid)}</code> · type <code>${esc(node.type)}</code></div>`);
    if (def.params.some((p) => p.type === "entity")) h.push(this._entityDatalist());
    this.$props.innerHTML = h.join("");
    this._applySnapshot();
  }

  _movePageField() {
    if (!this._prog || this._prog.pages.length < 2) return "";
    const opts = this._prog.pages
      .map((pg) => `<option value="${esc(pg.id)}" ${pg.id === this._page ? "selected" : ""}>${esc(pg.name)}</option>`)
      .join("");
    return `<div class="field" style="margin-top:12px"><span>${t("Flytt til side")}</span><select data-f="move-page">${opts}</select></div>`;
  }

  /* A node added since the last save has no runtime counterpart yet. */
  _dirtyNode(nid) {
    return !!(this._snap && this._snap.nodes && !this._snap.nodes[nid]);
  }

  _renderMacroProps() {
    const p = this._prog;
    const pins = (kind) =>
      p.nodes
        .filter((n) => n.type === kind)
        .sort((a, b) => a.y - b.y || a.x - b.x)
        .map((n) => esc(n.params?.name || "?"))
        .join(", ") || "–";
    const used = (p.used_by || []).length ? p.used_by.map(esc).join(", ") : t("ingen ennå");
    this.$props.innerHTML = `
      <h3>${t("Makro")}</h3>
      <div class="field"><span>${t("Navn")}</span><input type="text" data-f="prog:name" value="${esc(p.name)}"></div>
      <div class="field"><span>${t("Symbol (vises i blokkhodet)")}</span><input type="text" maxlength="10" data-f="prog:symbol" value="${esc(p.symbol || "M")}"></div>
      <div class="field"><span>${t("Beskrivelse")}</span><textarea data-f="prog:description">${esc(p.description || "")}</textarea></div>
      <h4>${t("Pinner")}</h4>
      <div class="row">${t("Innganger:")} ${pins("macro_in")}</div>
      <div class="row">${t("Utganger:")} ${pins("macro_out")}</div>
      <div class="hint">${t("Legg til «Makro-inngang» og «Makro-utgang» fra paletten. Rekkefølgen følger høyden på tegningen.")}</div>
      <h4>${t("Bruk")}</h4>
      <div class="hint">${t("Brukt i:")} ${used}</div>
      ${this._isNew ? `<div class="hint" style="margin-top:8px">${t("Makroen er ikke lagret. Trykk <b>Lagre</b> – da dukker den opp under «Makroer» i paletten.")}</div>` : ""}
      <h4>${t("Om")}</h4>
      <div class="hint">${t("En makro er en egen blokk satt sammen av andre blokker. Hver instans har sin egen tilstand (timere, låser, PID).")}</div>`;
  }

  _renderProgramProps() {
    if (this._kind === "macro") return this._renderMacroProps();
    const p = this._prog;
    const s = this._snap;
    const warnings = (s && s.warnings) || [];
    this.$props.innerHTML = `
      <h3>Program</h3>
      <div class="field"><span>${t("Navn")}</span><input type="text" data-f="prog:name" value="${esc(p.name)}"></div>
      <div class="field"><span>${t("Syklustid (sekunder)")}</span><input type="number" data-f="prog:interval" min="0.1" max="3600" step="0.1" value="${esc(p.interval)}"></div>
      <label class="row"><input type="checkbox" data-f="prog:event_scan" ${p.event_scan !== false ? "checked" : ""}> ${t("Skann straks når en inngang endres")}</label>
      <div class="hint">${t("Gjelder Les entitet, KNX lytt, Settpunkt og Bryter. Gir rask respons uten kort syklustid. Det faste skannet går fortsatt, blant annet for timerne.")}</div>
      <label class="row"><input type="checkbox" data-f="prog:enabled" ${p.enabled ? "checked" : ""}> ${t("Aktiv (kjører)")}</label>
      <div class="field"><span>${t("Beskrivelse")}</span><textarea data-f="prog:description">${esc(p.description || "")}</textarea></div>
      ${
        this._isNew
          ? `<div class="hint">${t("Programmet er ikke lagret ennå. Trykk <b>Lagre</b> for å opprette og starte det.")}</div>`
          : `<h4>Status</h4>
        <div class="row">${t("Tilstand:")} <span class="live" data-live="prog|running|">–</span></div>
        <div class="row">${t("Skann:")} <span class="live" data-live="prog|scan|">–</span> · <span class="live" data-live="prog|ms|">–</span> ms</div>
        <div class="row">${t("Skann ved endring:")} <span class="live" data-live="prog|events|">–</span></div>
        <div class="row">${t("Tvangsstyrt:")} <span class="live" data-live="prog|forced|">–</span>
          <button class="small" data-act="force-clear" style="margin-left:auto" title="${t("Frigi alle tvangsstyringer")}">${t("Frigi alle")}</button></div>
        ${warnings.length ? `<div class="err">${warnings.map(esc).join("\n")}</div>` : ""}`
      }
      <h4>${t("Hurtigtaster")}</h4>
      <div class="kbd">
        ${t("Dra fra utgang til inngang for å koble.")}<br>
        ${t("Dra en tilkoblet inngang for å flytte tråden.")}<br>
        ${t("Shift/Ctrl + dra på lerretet: velg flere.")}<br>
        ${t("Delete: slett · Ctrl+Z/Y: angre/gjør om")}<br>
        ${t("Ctrl+C/V/D: kopier/lim inn/dupliser")}<br>
        ${t("Ctrl+S: lagre · Piltaster: flytt · Hjul: zoom")}<br>
        ${t("Dobbeltklikk på blokk: egenskaper")}<br>
        ${t("Dobbeltklikk på sidefane: gi nytt navn")}
      </div>
      <h4>${t("Om")}</h4>
      <div class="hint">FBD Logic ${FBD_VERSION}. ${t("Programmet kjøres syklisk i Home Assistant, og straks en inngang endres hvis det er slått på. Lagring laster det inn på nytt uten å nullstille timere og låser som ikke er endret.")}</div>`;
    this._applySnapshot();
  }

  _parseAny(raw) {
    const s = String(raw).trim();
    if (s === "") return "";
    if (/^(true|på|on)$/i.test(s)) return true;
    if (/^(false|av|off)$/i.test(s)) return false;
    const n = Number(s.replace(",", "."));
    return isFinite(n) ? n : s;
  }

  _onPropsChange(e) {
    const el = e.target;
    const f = el.dataset && el.dataset.f;
    if (!f || !this._prog) return;
    if (f.startsWith("prog:")) {
      const key = f.slice(5);
      let v;
      if (key === "enabled" || key === "event_scan") v = el.checked;
      else if (key === "interval") {
        v = parseFloat(el.value);
        if (!isFinite(v)) return;
        v = clamp(v, 0.1, 3600);
      } else if (key === "symbol") v = el.value.trim().slice(0, 10) || "M";
      else v = key === "name" ? el.value.trim() || t("Uten navn") : el.value;
      this._setProgField(key, v);
      this._syncToolbar();
      return;
    }
    if (f === "move-page") {
      this._moveSelectionToPage(el.value);
      return;
    }
    const node = this._sel.size === 1 ? this._node([...this._sel][0]) : null;
    if (!node) return;
    const def = this._blocks[node.type];
    if (f.startsWith("sched:")) {
      const [, idx, which] = f.split(":");
      const periods = clone(Array.isArray(node.params.periods) ? node.params.periods : []);
      if (!periods[+idx] || !/^\d{1,2}:\d{2}$/.test(el.value)) return;
      this._pushUndo();
      periods[+idx][which] = el.value;
      node.params.periods = periods;
      this._markDirty();
      return;
    }
    this._pushUndo();
    if (f === "label") {
      node.label = el.value.trim();
    } else if (f.startsWith("param:")) {
      const name = f.slice(6);
      const pdef = def.params.find((p) => p.name === name);
      if (!pdef) return;
      let v;
      if (pdef.type === "bool") v = el.checked;
      else if (pdef.type === "number") {
        v = parseFloat(String(el.value).replace(",", "."));
        if (!isFinite(v)) v = pdef.default;
      } else v = el.value;
      if (pdef.type === "entity") v = String(v).trim();
      node.params[name] = v;
      if (def.dynamic && def.dynamic.param === name) {
        this._pruneLinks(node);
        this._renderProps();
      } else if (def.params.some((p) => p.show_if && p.show_if.param === name)) {
        this._renderProps();
      } else if (pdef.type === "entity") {
        const hint = el.parentElement.querySelector("[data-enthint]");
        if (hint) {
          hint.dataset.enthint = v;
          hint.innerHTML = this._entityHint(v);
        }
      }
    } else if (f.startsWith("const:")) {
      const name = f.slice(6);
      const port = this._inputPorts(def, node.params).find((p) => p.name === name);
      if (!port) return;
      let v;
      if (port.type === "bool") v = el.checked;
      else if (port.type === "num") {
        v = parseFloat(String(el.value).replace(",", "."));
        if (!isFinite(v)) v = port.default ?? 0;
      } else if (port.type === "str") v = el.value;
      else v = this._parseAny(el.value);
      node.consts[name] = v;
    }
    this._markDirty();
  }

  _onHassUpdate() {
    if (!this.$props) return;
    const now = Date.now();
    if (now - (this._lastHassUpd || 0) < 1000) return;
    this._lastHassUpd = now;
    for (const el of this.$props.querySelectorAll("[data-enthint]")) {
      el.innerHTML = this._entityHint(el.dataset.enthint);
    }
  }

  // ------------------------------------------------------------------ forcing
  async _force(nid, port, value) {
    const pid = this._livePid;
    if (!pid) return;
    try {
      await this._ws({ type: "fbd_logic/force", program_id: pid, node_id: this._fullId(nid), port, value });
      this._propsRefresh = true;
      const node = this._node(nid);
      const out = node && this._blocks[node.type] && this._blocks[node.type].outputs.find((p) => p.name === port);
      const lbl = out ? out.label : port;
      this._toast(value === null ? t("Tvangsstyringen av «{port}» er frigitt", { port: lbl }) : t("Utgangen «{port}» er tvunget til {value}", { port: lbl, value: fmt(value) }));
    } catch (err) {
      this._toast(t("Tvangsstyring feilet: {err}", { err: err.message || err }), true);
    }
  }

  // ------------------------------------------------------------------ trend
  _isDark() {
    return !!(this._hass && this._hass.themes && this._hass.themes.darkMode);
  }

  async _loadTrend() {
    const pid = this._livePid;
    if (!pid || this._kind !== "program") return;
    try {
      const res = await this._ws({ type: "fbd_logic/trend/get", program_id: pid });
      if (this._livePid !== pid) return;
      this._applyTrendResult(res, true);
    } catch (_e) {
      /* trend is optional */
    }
  }

  _applyTrendResult(res, replace) {
    const data = replace ? {} : this._trend.data;
    const signals = res.signals || [];
    for (const k of Object.keys(data)) if (!signals.includes(k)) delete data[k];
    for (const [k, arr] of Object.entries(res.data || {})) {
      if (replace || !data[k] || !data[k].length) data[k] = arr.map(([t, v]) => [t * 1000, v]);
    }
    let last = this._trendNow || 0;
    for (const arr of Object.values(data)) if (arr.length) last = Math.max(last, arr[arr.length - 1][0]);
    this._trendNow = last || Date.now();
    this._trend = { signals, data };
    const used = new Set();
    for (const s of Object.keys(this._trendSlots)) if (!signals.includes(s)) delete this._trendSlots[s];
    for (const s of signals) if (this._trendSlots[s] !== undefined) used.add(this._trendSlots[s]);
    for (const s of signals) {
      if (this._trendSlots[s] !== undefined) continue;
      let i = 0;
      while (used.has(i)) i++;
      this._trendSlots[s] = i;
      used.add(i);
    }
    this._renderTrend();
  }

  async _trendSet(signals) {
    const pid = this._livePid;
    if (!pid) return;
    try {
      const res = await this._ws({ type: "fbd_logic/trend/set", program_id: pid, signals });
      this._applyTrendResult(res, false);
      if (this._sel.size === 1 || this._selLink) this._renderProps();
    } catch (err) {
      this._toast(t("Kunne ikke endre trend: {err}", { err: err.message || err }), true);
    }
  }

  async _trendAdd(sig) {
    if (!sig || this._trend.signals.includes(sig)) return;
    if (this._trend.signals.length >= 8) {
      this._toast(t("Maks 8 signaler i trenden – fjern ett først"), true);
      return;
    }
    await this._trendSet([...this._trend.signals, sig]);
    if (!this._showTrend) {
      this._showTrend = true;
      this._applyLayout();
      this._renderTrend();
    }
  }

  _trendFromSnapshot() {
    const sigs = this._trend.signals;
    if (!sigs.length || this._kind !== "program" || !this._snap) return;
    const t = this._snap.t ? this._snap.t * 1000 : Date.now();
    if (t - (this._trendLastT || 0) < 1000) return;
    this._trendLastT = t;
    this._trendNow = t;
    const nodes = this._snap.nodes || {};
    for (const sig of sigs) {
      const [nid, port] = sig.split("|");
      const o = nodes[nid] && nodes[nid].o;
      const v = o ? o[port] : undefined;
      if (typeof v !== "boolean" && typeof v !== "number") continue;
      const arr = this._trend.data[sig] || (this._trend.data[sig] = []);
      if (arr.length && arr[arr.length - 1][0] >= t) continue;
      arr.push([t, v]);
      if (arr.length > 4000) arr.splice(0, arr.length - 3600);
    }
    if (this._showTrend) this._renderTrend();
  }

  _sigLabel(sig) {
    const [nid, port] = sig.split("|");
    const node = this._node(nid);
    if (!node) return t("{sig} (slettet)", { sig: `${nid}.${port}` });
    const def = this._blocks[node.type];
    const out = def && def.outputs.find((p) => p.name === port);
    const nlabel = node.label || this._info(node, def || {}) || def?.title || node.type;
    return `${nlabel}.${out ? out.label : port}`;
  }

  // Short label for a trend lane: the port name is always kept, so two outputs of one block stay apart.
  _sigLabelShort(sig, max) {
    const full = this._sigLabel(sig);
    if (full.length <= max) return full;
    const [nid, port] = sig.split("|");
    const node = this._node(nid);
    if (!node) return trunc(full, max);
    const def = this._blocks[node.type];
    const out = def && def.outputs.find((p) => p.name === port);
    const plabel = out ? out.label : port;
    const named = node.label || this._info(node, def || {});
    const head = named || def?.symbol || def?.title || node.type;
    return `${trunc(head, Math.max(3, max - plabel.length - 1))}.${plabel}`;
  }

  _renderTrend() {
    if (!this._showTrend || !this.$trend || !this._prog) return;
    const sigs = this._trend.signals;
    if (!this.$trend.querySelector(".thead")) {
      const opts = TREND_WINDOWS.map(([s, l]) => `<option value="${s}" ${s === this._trendWin ? "selected" : ""}>${l}</option>`).join("");
      this.$trend.innerHTML = `<div class="thead"><b>Trend</b><span class="tcount"></span><span style="flex:1"></span>
        <select class="twin" title="${t("Tidsvindu")}">${opts}</select>
        <button data-act="trend-csv" title="${t("Last ned verdiene som CSV (tabell)")}">⤓ CSV</button></div><div class="tbody"></div><div class="tip hidden"></div>`;
    }
    this.$trend.style.setProperty("--fbd-grid", this._isDark() ? "#2c2c2a" : "#e1e0d9");
    this.$trend.querySelector(".tcount").textContent = `· ${t("{n} av 8 signaler", { n: sigs.length })}`;
    const body = this.$trend.querySelector(".tbody");
    if (this._kind !== "program" || this._isNew) {
      body.innerHTML = `<div class="tempty">${t("Trend er tilgjengelig for lagrede programmer.")}</div>`;
      return;
    }
    if (!sigs.length) {
      body.innerHTML = `<div class="tempty">${t("Velg en blokk og trykk 📈 ved en utgang (eller velg en tråd og «Legg i trend»). Verdiene samples hvert sekund (eller hver syklus) og de siste 60 minuttene huskes så lenge HA kjører.")}</div>`;
      return;
    }
    body.innerHTML = this._trendSvg(body.clientWidth || 600);
    if (this._lastHover) this._trendHover(this._lastHover);
  }

  _trendLayout(width) {
    // Narrow pane: the label goes on its own row above each lane so the plot keeps the full width.
    const compact = width < 480;
    const X0 = compact ? 40 : 190;
    const X1 = Math.max(X0 + 60, width - (compact ? 8 : 14));
    const tEnd = this._trendNow || Date.now();
    const tStart = tEnd - this._trendWin * 1000;
    const lanes = [];
    const head = compact ? 18 : 0;
    let y = 6;
    for (const sig of this._trend.signals) {
      const pts = (this._trend.data[sig] || []).filter((p) => p[0] >= tStart - 2000);
      const isBool = pts.length ? typeof pts[pts.length - 1][1] === "boolean" : false;
      const h = isBool ? 30 : 58;
      lanes.push({ sig, pts, isBool, top: y, y: y + head, h });
      y += head + h + 8;
    }
    return { X0, X1, tStart, tEnd, lanes, H: y + 18, compact, width };
  }

  _trendSvg(width) {
    const L = this._trendLayout(width);
    this._trendL = L;
    const pal = this._isDark() ? TREND_DARK : TREND_LIGHT;
    const tx = (t) => L.X0 + ((t - L.tStart) / (L.tEnd - L.tStart)) * (L.X1 - L.X0);
    const parts = [];
    for (const lane of L.lanes) {
      const color = pal[this._trendSlots[lane.sig] ?? 0];
      const { y, h, pts } = lane;
      const last = pts.length ? pts[pts.length - 1][1] : undefined;
      const lastTxt = last === undefined ? "–" : esc(fmt(last));
      const rm = (rx, ry) =>
        `<g class="rm" data-act="trend-rm" data-sig="${esc(lane.sig)}"><title>${t("Fjern fra trend")}</title><rect x="${rx}" y="${ry}" width="20" height="18" fill="transparent"></rect><text x="${rx + 10}" y="${ry + 13}" text-anchor="middle">✕</text></g>`;
      parts.push(`<line class="grid" x1="${L.X0}" x2="${L.X1}" y1="${y + h}" y2="${y + h}"></line>`);
      if (L.compact) {
        const t = lane.top;
        const chars = Math.max(6, Math.floor((L.X1 - 24 - 90) / 7));
        parts.push(`<line x1="8" x2="20" y1="${t + 9}" y2="${t + 9}" stroke="${color}" stroke-width="2" stroke-linecap="round"></line>`);
        parts.push(`<text class="lname" x="24" y="${t + 13}">${esc(this._sigLabelShort(lane.sig, chars))}</text>`);
        parts.push(`<text class="lval" x="${L.X1 - 24}" y="${t + 13}" text-anchor="end">${lastTxt}</text>`);
        parts.push(rm(L.X1 - 20, t));
      } else {
        parts.push(`<line x1="8" x2="20" y1="${y + 10}" y2="${y + 10}" stroke="${color}" stroke-width="2" stroke-linecap="round"></line>`);
        parts.push(`<text class="lname" x="24" y="${y + 14}">${esc(this._sigLabelShort(lane.sig, 22))}</text>`);
        parts.push(`<text class="lval" x="24" y="${y + 28}">${lastTxt}</text>`);
        parts.push(rm(4, y + 16));
      }
      if (!pts.length) continue;
      let d = "";
      if (lane.isBool) {
        const yv = (v) => (v ? y + 4 : y + h - 4);
        pts.forEach((p, i) => {
          const x = Math.max(L.X0, tx(p[0])).toFixed(1);
          d += i === 0 ? `M${x},${yv(p[1])}` : `H${x}V${yv(p[1])}`;
        });
        d += `H${Math.min(L.X1, tx(pts[pts.length - 1][0])).toFixed(1)}`;
        parts.push(`<text class="axis" x="${L.X0 - 4}" y="${y + 8}" text-anchor="end">1</text><text class="axis" x="${L.X0 - 4}" y="${y + h - 1}" text-anchor="end">0</text>`);
      } else {
        let lo = Infinity;
        let hi = -Infinity;
        for (const p of pts) {
          lo = Math.min(lo, p[1]);
          hi = Math.max(hi, p[1]);
        }
        if (hi - lo < 1e-9) {
          lo -= 1;
          hi += 1;
        } else {
          const pad = (hi - lo) * 0.08;
          lo -= pad;
          hi += pad;
        }
        lane.lo = lo;
        lane.hi = hi;
        const yv = (v) => y + 4 + (1 - (v - lo) / (hi - lo)) * (h - 8);
        pts.forEach((p, i) => {
          d += `${i === 0 ? "M" : "L"}${Math.max(L.X0, tx(p[0])).toFixed(1)},${yv(p[1]).toFixed(1)}`;
        });
        parts.push(`<line class="grid" x1="${L.X0}" x2="${L.X1}" y1="${y + 4}" y2="${y + 4}"></line>`);
        parts.push(`<text class="axis" x="${L.X0 - 4}" y="${y + 10}" text-anchor="end">${esc(fmt(hi))}</text><text class="axis" x="${L.X0 - 4}" y="${y + h - 1}" text-anchor="end">${esc(fmt(lo))}</text>`);
      }
      parts.push(`<path class="line" stroke="${color}" d="${d}"></path>`);
    }
    // time axis
    const ticks = Math.max(1, Math.min(5, Math.floor((L.X1 - L.X0) / 70)));
    for (let i = 0; i <= ticks; i++) {
      const t = L.tStart + ((L.tEnd - L.tStart) * i) / ticks;
      const x = tx(t);
      const d = new Date(t);
      const lbl = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
      parts.push(`<text class="axis" x="${x}" y="${L.H - 4}" text-anchor="${i === 0 ? "start" : i === ticks ? "end" : "middle"}">${lbl}</text>`);
    }
    parts.push(`<line class="xh hidden" x1="0" x2="0" y1="2" y2="${L.H - 16}"></line>`);
    return `<svg height="${L.H}" viewBox="0 0 ${width} ${L.H}">${parts.join("")}</svg>`;
  }

  _trendHover(e) {
    this._lastHover = e ? { clientX: e.clientX, clientY: e.clientY } : null;
    const tip = this.$trend.querySelector(".tip");
    const xh = this.$trend.querySelector(".xh");
    const svg = this.$trend.querySelector("svg");
    const L = this._trendL;
    if (!tip || !xh || !svg || !L) return;
    const r = svg.getBoundingClientRect();
    const x = e ? e.clientX - r.left : -1;
    if (!e || x < L.X0 || x > L.X1 || e.clientY > r.bottom) {
      tip.classList.add("hidden");
      xh.classList.add("hidden");
      return;
    }
    const t = L.tStart + ((x - L.X0) / (L.X1 - L.X0)) * (L.tEnd - L.tStart);
    const pal = this._isDark() ? TREND_DARK : TREND_LIGHT;
    tip.textContent = "";
    const d = new Date(t);
    const head = document.createElement("div");
    head.className = "n";
    head.textContent = d.toLocaleTimeString();
    tip.appendChild(head);
    for (const lane of L.lanes) {
      let val;
      for (const p of lane.pts) {
        if (p[0] > t) break;
        val = p[1];
      }
      const row = document.createElement("div");
      row.className = "tr";
      const k = document.createElement("span");
      k.className = "k";
      k.style.background = pal[this._trendSlots[lane.sig] ?? 0];
      const v = document.createElement("span");
      v.className = "v";
      v.textContent = val === undefined ? "–" : fmt(val);
      const n = document.createElement("span");
      n.className = "n";
      n.textContent = this._sigLabel(lane.sig);
      row.append(k, v, n);
      tip.appendChild(row);
    }
    xh.setAttribute("x1", x);
    xh.setAttribute("x2", x);
    xh.classList.remove("hidden");
    tip.classList.remove("hidden");
    const tr = this.$trend.getBoundingClientRect();
    const left = e.clientX - tr.left + 14;
    tip.style.left = `${Math.min(left, tr.width - tip.offsetWidth - 6)}px`;
    tip.style.top = `30px`;
  }

  _trendCsv() {
    const sigs = this._trend.signals;
    if (!sigs.length) return;
    const times = new Set();
    for (const s of sigs) for (const p of this._trend.data[s] || []) times.add(p[0]);
    const maps = sigs.map((s) => new Map((this._trend.data[s] || []).map((p) => [p[0], p[1]])));
    const q = (s) => `"${String(s).replace(/"/g, '""')}"`;
    const sep = LANG === "en" ? "," : ";";
    const lines = [[t("tid"), ...sigs.map((s) => this._sigLabel(s))].map(q).join(sep)];
    for (const t of [...times].sort((a, b) => a - b)) {
      const row = [new Date(t).toISOString()];
      for (const m of maps) {
        const v = m.get(t);
        row.push(v === undefined ? "" : typeof v === "boolean" ? (v ? 1 : 0) : LANG === "en" ? String(v) : String(v).replace(".", ","));
      }
      lines.push(row.join(sep));
    }
    const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = (this._prog.name || "trend").replace(/[^\wæøåÆØÅ\- ]+/g, "_") + "_trend.csv";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(a.href);
      a.remove();
    }, 500);
  }

  // ------------------------------------------------------------------ macro from selection
  async _makeMacroFromSelection() {
    const ids = new Set(this._sel);
    const nodes = this._prog.nodes.filter((n) => ids.has(n.id));
    if (nodes.length < 1) return;
    if (nodes.some((n) => n.type === "macro_in" || n.type === "macro_out")) {
      this._toast(t("Utvalget kan ikke inneholde makro-pinner"), true);
      return;
    }
    const name = await this._prompt(t("Navn på den nye makroen"), t("Ny makro"));
    if (!name) return;
    const outType = (nid, port) => {
      const n = this._node(nid);
      const def = n && this._blocks[n.type];
      const p = def && def.outputs.find((x) => x.name === port);
      return p ? p.type : "any";
    };
    const internal = this._prog.links.filter((l) => ids.has(l.from) && ids.has(l.to));
    const incoming = this._prog.links.filter((l) => !ids.has(l.from) && ids.has(l.to));
    const outgoing = this._prog.links.filter((l) => ids.has(l.from) && !ids.has(l.to));
    const group = (links) => {
      const m = new Map();
      for (const l of links) {
        const k = `${l.from}|${l.from_port}`;
        if (!m.has(k)) m.set(k, []);
        m.get(k).push(l);
      }
      return [...m.entries()];
    };
    const inGroups = group(incoming);
    const outGroups = group(outgoing);
    const minX = Math.min(...nodes.map((n) => n.x));
    const minY = Math.min(...nodes.map((n) => n.y));
    const maxX = Math.max(...nodes.map((n) => this._geom(n).x + this._geom(n).w));
    const dx = 220 - minX;
    const dy = 40 - minY;
    const used = new Set();
    const uniq = (base) => {
      let s = String(base || "x").replace(/[^\wæøåÆØÅ]+/g, "_").slice(0, 12) || "x";
      let k = s;
      let i = 2;
      while (used.has(k)) k = `${s}${i++}`;
      used.add(k);
      return k;
    };
    const mNodes = nodes.map((n) => {
      const c = clone(n);
      delete c.page;
      c.x += dx;
      c.y += dy;
      return c;
    });
    const mLinks = internal.map((l) => ({ ...clone(l), id: uid("l") }));
    const pinIn = [];
    inGroups.forEach(([key, links], i) => {
      const [src, sport] = key.split("|");
      const pname = uniq(links[0].to_port);
      const id = uid("n");
      mNodes.push({ id, type: "macro_in", x: 20, y: 40 + i * 80, params: { name: pname, type: outType(src, sport), default: "0" }, consts: {}, label: "" });
      for (const l of links) mLinks.push({ id: uid("l"), from: id, from_port: "value", to: l.to, to_port: l.to_port });
      pinIn.push({ pname, src, sport });
    });
    used.clear();
    const pinOut = [];
    outGroups.forEach(([key, links], i) => {
      const [src, sport] = key.split("|");
      const pname = uniq(sport);
      const id = uid("n");
      mNodes.push({ id, type: "macro_out", x: maxX + dx + 120, y: 40 + i * 80, params: { name: pname, type: outType(src, sport) }, consts: {}, label: "" });
      mLinks.push({ id: uid("l"), from: src, from_port: sport, to: id, to_port: "value" });
      pinOut.push({ pname, links });
    });
    let mid;
    try {
      const res = await this._ws({ type: "fbd_logic/macro/save", macro: { name, symbol: "M", description: "", nodes: mNodes, links: mLinks } });
      mid = res.macro.id;
      await this._loadLibrary();
      await this._loadPrograms();
    } catch (err) {
      this._toast(t("Kunne ikke lage makro: {err}", { err: err.message || err }), true);
      return;
    }
    this._pushUndo();
    const inst = { id: uid("n"), type: MACRO_PREFIX + mid, x: snapG(minX), y: snapG(minY), params: {}, consts: {}, label: "", page: this._page };
    this._prog.nodes = this._prog.nodes.filter((n) => !ids.has(n.id));
    this._prog.links = this._prog.links.filter((l) => !ids.has(l.from) && !ids.has(l.to));
    this._prog.nodes.push(inst);
    for (const p of pinIn) this._prog.links.push({ id: uid("l"), from: p.src, from_port: p.sport, to: inst.id, to_port: p.pname });
    for (const p of pinOut)
      for (const l of p.links) this._prog.links.push({ id: uid("l"), from: inst.id, from_port: p.pname, to: l.to, to_port: l.to_port });
    this._sel = new Set([inst.id]);
    this._selLink = null;
    this._markDirty();
    this._renderProps();
    this._toast(t("Makroen «{name}» er laget. Trykk Lagre for å ta den i bruk her.", { name }));
  }

  // ------------------------------------------------------------------ small UI helpers
  _prompt(label, value) {
    return new Promise((resolve) => {
      const m = document.createElement("div");
      m.className = "modal";
      m.innerHTML = `<div class="box"><p>${esc(label)}</p><input type="text" class="pin" style="width:100%;padding:6px 8px;margin:-6px 0 14px;font:inherit;border:1px solid var(--divider-color,#ccc);border-radius:4px;background:var(--primary-background-color,#fff);color:inherit">
        <div class="acts"><button class="cancel">${t("Avbryt")}</button><button class="ok">OK</button></div></div>`;
      const inp = m.querySelector(".pin");
      inp.value = value || "";
      const done = (v) => {
        m.remove();
        resolve(v);
      };
      m.querySelector(".cancel").addEventListener("click", () => done(null));
      m.querySelector(".ok").addEventListener("click", () => done(inp.value.trim() || null));
      inp.addEventListener("keydown", (e) => {
        if (e.key === "Enter") done(inp.value.trim() || null);
        if (e.key === "Escape") done(null);
        e.stopPropagation();
      });
      this.shadowRoot.querySelector(".app").appendChild(m);
      inp.focus();
      inp.select();
    });
  }

  _toast(msg, error) {
    const old = this.shadowRoot.querySelector(".toast");
    if (old) old.remove();
    const t = document.createElement("div");
    t.className = "toast" + (error ? " error" : "");
    t.textContent = msg;
    this.shadowRoot.querySelector(".main").appendChild(t);
    setTimeout(() => t.remove(), error ? 6000 : 2500);
  }

  _confirm(html, okText) {
    return new Promise((resolve) => {
      const m = document.createElement("div");
      m.className = "modal";
      m.innerHTML = `<div class="box"><p>${html}</p><div class="acts"><button class="cancel">${t("Avbryt")}</button><button class="ok">${esc(okText || "OK")}</button></div></div>`;
      const done = (v) => {
        m.remove();
        resolve(v);
      };
      m.querySelector(".cancel").addEventListener("click", () => done(false));
      m.querySelector(".ok").addEventListener("click", () => done(true));
      m.addEventListener("click", (e) => {
        if (e.target === m) done(false);
      });
      this.shadowRoot.querySelector(".app").appendChild(m);
      m.querySelector(".ok").focus();
    });
  }
}

if (!customElements.get("fbd-logic-panel")) {
  customElements.define("fbd-logic-panel", FbdLogicPanel);
}
