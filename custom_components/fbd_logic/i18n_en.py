"""English texts for the block library and the backend messages, keyed by the Norwegian original.

Add the English version here when a Norwegian text is added or changed: tests/test_i18n.py fails
for every text in the library or in a tr() call that has no entry (or is not listed in SAME).
"""

# Texts that are the same in both languages (identifiers, units, technical names).
SAME: set[str] = {
    "Home Assistant", "KNX / Modbus", "XOR", "A", "B", "q", "s", "r", "g", "k", "in", "out", "in0", "in1",
    "err", "min", "Min", "PV", "SP", "Kp", "Ti s", "Td s", "auto", "Auto", "idx", "bit", "cu", "count",
    "reset", "rate/s", "tau s", "Type", "Coil", "int16", "uint16", "DPT / type", "9.004 Lux",
    "VOC (tall)",
}

EN: dict[str, str] = {
    # ------------------------------------------------------------------ categories
    "Logikk": "Logic",
    "Sammenligning": "Compare",
    "Matematikk": "Math",
    "Tid": "Time",
    "Regulering": "Control",
    "Annet": "Other",
    "Makroer": "Macros",
    "Makro-tilkoblinger": "Macro pins",
    # ------------------------------------------------------------------ common port and field names
    "verdi": "value",
    "på": "on",
    "tekst": "text",
    "gyldig": "valid",
    "aktiv": "enable",
    "høy": "high",
    "lav": "low",
    "maks": "max",
    "tid s": "time s",
    "gått s": "elapsed s",
    "på s": "on s",
    "av s": "off s",
    "time": "hour",
    "dagmin": "daymin",
    "ukedag": "weekday",
    "helg": "weekend",
    "timer": "hours",
    "ellers": "else",
    "neste min": "next min",
    "ny": "new",
    "inn lav": "in low",
    "inn høy": "in high",
    "ut lav": "out low",
    "ut høy": "out high",
    "manuell": "manual",
    "man. verdi": "man. value",
    "arb.punkt": "bias",
    "avvik": "error",
    "Entitet": "Entity",
    "Navn": "Name",
    "Verdi": "Value",
    "Tekst": "Text",
    "Maks": "Max",
    "Steg": "Step",
    "Enhet": "Unit",
    "Visning": "Display",
    "Handling": "Action",
    "Tjeneste": "Service",
    "Automatisk": "Automatic",
    "Dødbånd": "Deadband",
    "Minste intervall (s)": "Minimum interval (s)",
    "Desimaler": "Decimals",
    "Antall innganger": "Number of inputs",
    "Datatype": "Data type",
    "Datatype (DPT)": "Data type (DPT)",
    "Gruppeadresse": "Group address",
    "f.eks. 1/2/3": "e.g. 1/2/3",
    "Skala": "Scale",
    "Tall": "Number",
    "Av/på": "On/off",
    "Valgfri": "Any",
    "Temperatur": "Temperature",
    # ------------------------------------------------------------------ Home Assistant blocks
    "Les entitet": "Read entity",
    "Leser tilstanden (eller et attributt) til en HA-entitet.": "Reads the state (or an attribute) of an HA entity.",
    "Attributt (valgfritt)": "Attribute (optional)",
    "Ved utilgjengelig": "When unavailable",
    "Hold siste verdi": "Hold last value",
    "Bruk reserveverdi": "Use fallback value",
    "Reserveverdi": "Fallback value",
    "Skriv entitet": "Write entity",
    "Skriver verdien til en HA-entitet via riktig tjeneste. Skriver bare når verdien endres (med valgfritt dødbånd og minste intervall).": (
        "Writes the value to an HA entity with the matching service. Writes only when the value changes "
        "(with optional deadband and minimum interval)."
    ),
    "Automatisk (etter domene)": "Automatic (by domain)",
    "Sett verdi": "Set value",
    "Lysstyrke %": "Brightness %",
    "Posisjon %": "Position %",
    "Velg alternativ": "Select option",
    "Trykk (på stigende flanke)": "Press (on rising edge)",
    "Egendefinert tjeneste": "Custom service",
    "f.eks. light.turn_on": "e.g. light.turn_on",
    "Datafelt for verdien": "Data field for the value",
    "f.eks. brightness (tomt = ingen verdi sendes)": "e.g. brightness (empty = no value is sent)",
    "Skriv ved oppstart": "Write on start",
    "Settpunkt (HA)": "Setpoint (HA)",
    "Lager en number-entitet i HA som kan justeres fra dashboard, og gir verdien ut i programmet.": (
        "Creates a number entity in HA that can be adjusted from a dashboard, and outputs its value in the program."
    ),
    "Settpunkt": "Setpoint",
    "Startverdi": "Initial value",
    "Tallfelt": "Box",
    "Glidebryter": "Slider",
    "Bryter (HA)": "Switch (HA)",
    "Lager en switch-entitet i HA (f.eks. manuell overstyring) og gir tilstanden ut.": (
        "Creates a switch entity in HA (e.g. a manual override) and outputs its state."
    ),
    "Bryter": "Switch",
    "Publiser verdi": "Publish value",
    "Gjør et internt signal tilgjengelig som sensor/binary_sensor i HA (til dashboard, historikk og automasjoner).": (
        "Makes an internal signal available as a sensor/binary_sensor in HA (for dashboards, history and automations)."
    ),
    "Tall (sensor)": "Number (sensor)",
    "Av/på (binary_sensor)": "On/off (binary_sensor)",
    "Tekst (sensor)": "Text (sensor)",
    "Device class (valgfritt)": "Device class (optional)",
    "HA-navnet med små bokstaver, f.eks. temperature. Velg fra listen eller skriv selv.": (
        "The HA name in lower case, e.g. temperature. Pick from the list or type it."
    ),
    "Temperatur (tall)": "Temperature (number)",
    "Temperaturdifferanse (tall)": "Temperature difference (number)",
    "Relativ fuktighet (tall)": "Relative humidity (number)",
    "CO₂ (tall)": "CO₂ (number)",
    "Svevestøv PM2.5 (tall)": "Particulate matter PM2.5 (number)",
    "Trykk (tall)": "Pressure (number)",
    "Volumstrøm (tall)": "Volume flow rate (number)",
    "Effekt (tall)": "Power (number)",
    "Energi (tall)": "Energy (number)",
    "Spenning (tall)": "Voltage (number)",
    "Strøm (tall)": "Current (number)",
    "Effektfaktor (tall)": "Power factor (number)",
    "Frekvens (tall)": "Frequency (number)",
    "Belysningsstyrke (tall)": "Illuminance (number)",
    "Vindhastighet (tall)": "Wind speed (number)",
    "Varighet (tall)": "Duration (number)",
    "Batteri (tall eller av/på)": "Battery (number or on/off)",
    "I drift (av/på)": "Running (on/off)",
    "Feil/alarm (av/på)": "Problem/alarm (on/off)",
    "Varme (av/på)": "Heat (on/off)",
    "Kulde (av/på)": "Cold (on/off)",
    "Dør (av/på)": "Door (on/off)",
    "Vindu (av/på)": "Window (on/off)",
    "Åpen/lukket (av/på)": "Opening (on/off)",
    "Bevegelse (av/på)": "Motion (on/off)",
    "Tilstedeværelse (av/på)": "Occupancy (on/off)",
    "Fukt/lekkasje (av/på)": "Moisture/leak (on/off)",
    "Røyk (av/på)": "Smoke (on/off)",
    "Tall sendes til HA først når de har endret seg minst så mye. 0 = hver endring.": (
        "Numbers are sent to HA only when they have changed at least this much. 0 = every change."
    ),
    "Høyst én ny verdi så ofte. Siste verdi kommer alltid fram.": (
        "At most one new value this often. The latest value always gets through."
    ),
    # ------------------------------------------------------------------ other
    "Konstant (tall)": "Constant (number)",
    "Fast tallverdi.": "Fixed number.",
    "Konstant (av/på)": "Constant (on/off)",
    "Fast av/på-verdi.": "Fixed on/off value.",
    "Kommentar": "Comment",
    "Fritekst på tegningen. Påvirker ikke logikken.": "Free text on the drawing. Does not affect the logic.",
    "Koblingspunkt (sender)": "Connector (sender)",
    "Sender et signal under et navn. Hentes med «Koblingspunkt (mottaker)» med samme navn, på samme eller en annen side.": (
        "Sends a signal under a name. Picked up by a “Connector (receiver)” with the same name, on the same page "
        "or another one."
    ),
    "Koblingspunkt (mottaker)": "Connector (receiver)",
    "Henter signalet fra koblingspunktet (sender) med samme navn.": (
        "Gets the signal from the connector (sender) with the same name."
    ),
    # ------------------------------------------------------------------ logic
    "OG (AND)": "AND",
    "Utgangen er på når alle innganger er på.": "The output is on when all inputs are on.",
    "ELLER (OR)": "OR",
    "Utgangen er på når minst én inngang er på.": "The output is on when at least one input is on.",
    "Utgangen er på når et odde antall innganger er på.": "The output is on when an odd number of inputs are on.",
    "IKKE (NOT)": "NOT",
    "Inverterer inngangen.": "Inverts the input.",
    "SR-lås (sett dominant)": "SR latch (set dominant)",
    "Sett/tilbakestill-lås. Sett vinner hvis begge er på. Huskes over omstart.": (
        "Set/reset latch. Set wins when both are on. Kept over a restart."
    ),
    "RS-lås (tilbakestill dominant)": "RS latch (reset dominant)",
    "Sett/tilbakestill-lås. Tilbakestill vinner hvis begge er på. Huskes over omstart.": (
        "Set/reset latch. Reset wins when both are on. Kept over a restart."
    ),
    "Stigende flanke": "Rising edge",
    "Gir én puls (ett skann) når inngangen går fra av til på.": "Gives one pulse (one scan) when the input goes from off to on.",
    "Fallende flanke": "Falling edge",
    "Gir én puls (ett skann) når inngangen går fra på til av.": "Gives one pulse (one scan) when the input goes from on to off.",
    "Impulsrelé (toggle)": "Toggle (impulse relay)",
    "Hver stigende flanke på inngangen veksler utgangen. Huskes over omstart.": (
        "Every rising edge on the input toggles the output. Kept over a restart."
    ),
    # ------------------------------------------------------------------ compare
    "Større enn": "Greater than",
    "Utgangen er på når A > B.": "The output is on when A > B.",
    "Større eller lik": "Greater or equal",
    "Utgangen er på når A ≥ B.": "The output is on when A ≥ B.",
    "Mindre enn": "Less than",
    "Utgangen er på når A < B.": "The output is on when A < B.",
    "Mindre eller lik": "Less or equal",
    "Utgangen er på når A ≤ B.": "The output is on when A ≤ B.",
    "Lik": "Equal",
    "Utgangen er på når A = B.": "The output is on when A = B.",
    "Ulik": "Not equal",
    "Utgangen er på når A ≠ B.": "The output is on when A ≠ B.",
    "Hysterese": "Hysteresis",
    "På når inngang ≥ høy, av når inngang ≤ lav, ellers uendret.": "On when input ≥ high, off when input ≤ low, otherwise unchanged.",
    "Innenfor område": "In range",
    "På når lav ≤ inngang ≤ høy.": "On when low ≤ input ≤ high.",
    "Velger (SEL)": "Select (SEL)",
    "Gir ut in1 når g er på, ellers in0.": "Outputs in1 when g is on, otherwise in0.",
    "Tekst lik": "Text equals",
    "På når teksten er lik oppgitt verdi (f.eks. hvac-modus 'heat').": "On when the text equals the given value (e.g. hvac mode 'heat').",
    "Ignorer store/små bokstaver": "Ignore case",
    "Multiplekser (MUX)": "Multiplexer (MUX)",
    "Gir ut inngangen som indeksen k peker på (in0, in1, …). Ugyldig indeks begrenses til nærmeste inngang og setter err.": (
        "Outputs the input that index k points to (in0, in1, …). An invalid index is limited to the nearest input "
        "and sets err."
    ),
    "Prioritetsvelger": "Priority select",
    "Gir ut verdien til første aktive prioritet (g1 høyest), ellers 'ellers'. Typisk: manuell > alarm > tidsprogram > auto. idx = aktiv prioritet (0 = ingen).": (
        "Outputs the value of the first active priority (g1 highest), otherwise 'else'. Typical: manual > alarm > "
        "schedule > auto. idx = active priority (0 = none)."
    ),
    "Antall prioriteter": "Number of priorities",
    # ------------------------------------------------------------------ math
    "Addisjon": "Add",
    "Summerer inngangene.": "Sums the inputs.",
    "Subtraksjon": "Subtract",
    "out = A − B": "out = A − B",
    "Multiplikasjon": "Multiply",
    "Multipliserer inngangene.": "Multiplies the inputs.",
    "Divisjon": "Divide",
    "out = A ÷ B. Ved deling på null blir out 0 og err på.": "out = A ÷ B. Division by zero gives out 0 and err on.",
    "Minimum": "Minimum",
    "Laveste av inngangene.": "Lowest of the inputs.",
    "Maksimum": "Maximum",
    "Høyeste av inngangene.": "Highest of the inputs.",
    "Gjennomsnitt": "Average",
    "Gjennomsnitt av inngangene.": "Average of the inputs.",
    "Absoluttverdi": "Absolute value",
    "out = |in|": "out = |in|",
    "Begrensning": "Limit",
    "Begrenser inngangen til [min, maks].": "Limits the input to [min, max].",
    "Skalering (lineær)": "Scale (linear)",
    "Lineær skalering fra [inn lav, inn høy] til [ut lav, ut høy].": "Linear scaling from [in low, in high] to [out low, out high].",
    "Begrens til utområdet": "Limit to the output range",
    "Avrunding": "Round",
    "Runder av til valgt antall desimaler.": "Rounds to the chosen number of decimals.",
    "Formel": "Formula",
    "Fritt uttrykk med innganger a…h, f.eks. 'a*0.5 + b' eller 'sel(a > 20, b, c)'. Funksjoner: abs, min, max, round, sqrt, clamp, sel, floor, ceil, sin, cos, log, exp.": (
        "Free expression with inputs a…h, e.g. 'a*0.5 + b' or 'sel(a > 20, b, c)'. Functions: abs, min, max, round, "
        "sqrt, clamp, sel, floor, ceil, sin, cos, log, exp."
    ),
    "Uttrykk": "Expression",
    "Hent bit": "Get bit",
    "Henter én bit (0 = minst signifikant) ut av et heltall, f.eks. et Modbus statusord.": (
        "Gets one bit (0 = least significant) out of an integer, e.g. a Modbus status word."
    ),
    # ------------------------------------------------------------------ time
    "Innkoblingsforsinkelse": "On delay",
    "Utgangen går på når inngangen har vært på i 'tid' sekunder.": "The output goes on when the input has been on for 'time' seconds.",
    "Utkoblingsforsinkelse": "Off delay",
    "Utgangen går av 'tid' sekunder etter at inngangen gikk av.": "The output goes off 'time' seconds after the input went off.",
    "Puls": "Pulse",
    "Stigende flanke gir en puls med fast lengde ('tid' sekunder).": "A rising edge gives a pulse of fixed length ('time' seconds).",
    "Pulsgenerator": "Pulse generator",
    "Blinker med valgt på- og av-tid mens aktiv.": "Blinks with the chosen on and off time while enabled.",
    "Klokke": "Clock",
    "Lokal tid: time, minutt, minutter siden midnatt, ukedag (1=man) og helg.": (
        "Local time: hour, minute, minutes since midnight, weekday (1=Mon) and weekend."
    ),
    "Driftstid": "Run time",
    "Teller driftstimer mens inngangen er på. Huskes over omstart.": "Counts running hours while the input is on. Kept over a restart.",
    "Teller": "Counter",
    "Teller stigende flanker. Huskes over omstart.": "Counts rising edges. Kept over a restart.",
    "Ukeplan": "Weekly schedule",
    "Tidsprogram med perioder per ukedag. q er på i periodene, value gir verdi for på/av (f.eks. 21/18 °C), next er minutter til neste skift. En periode der av er før på, går over midnatt. aktiv = av gir q av (f.eks. helligdag).": (
        "Time schedule with periods per weekday. q is on in the periods, value gives a value for on/off (e.g. "
        "21/18 °C), next is minutes to the next change. A period whose off time is before its on time runs past "
        "midnight. enable = off turns q off (e.g. on a holiday)."
    ),
    "Perioder": "Periods",
    "Verdi i periode": "Value in period",
    "Verdi utenfor periode": "Value outside period",
    # ------------------------------------------------------------------ control
    "PID-regulator": "PID controller",
    "Generell PID-regulator med anti-windup, for alle slags prosesser (temperatur, trykk, fukt, CO₂, nivå, lys). Revers: utgangen øker når PV er under SP (f.eks. varme, befukting). Direkte: utgangen øker når PV er over SP (f.eks. kjøling, CO₂ til ventilasjon). Ti = integraltid i sekunder (0 = av), Td = derivattid i sekunder (derivatet virker på PV og er filtrert med Td/10). Aktiv av gir min ut, manuell gir den manuelle verdien ut. Overgangen tilbake til automatikk er støtfri: utgangen fortsetter der den var. Arbeidspunktet legges til utgangen (nyttig for ren P-regulering eller foroverkobling).": (
        "General PID controller with anti-windup, for all kinds of processes (temperature, pressure, humidity, "
        "CO₂, level, light). Reverse: the output rises when PV is below SP (e.g. heating, humidifying). Direct: "
        "the output rises when PV is above SP (e.g. cooling, CO₂ to ventilation). Ti = integral time in seconds "
        "(0 = off), Td = derivative time in seconds (the derivative acts on PV and is filtered with Td/10). Enable "
        "off gives min out, manual gives the manual value out. The return to automatic is bumpless: the output "
        "continues where it was. The bias is added to the output (useful for P-only control or feedforward)."
    ),
    "Virkning": "Action",
    "Revers: øker når PV < SP (f.eks. varme)": "Reverse: rises when PV < SP (e.g. heating)",
    "Direkte: øker når PV > SP (f.eks. kjøling)": "Direct: rises when PV > SP (e.g. cooling)",
    "Avvik innenfor ± dødbåndet regnes som 0, så pådraget står stille nær SP (sparer spjeld- og ventilmotorer). Samme enhet som PV. 0 = av.": (
        "An error within ± the deadband counts as 0, so the output stays still near SP (saves damper and valve "
        "actuators). Same unit as PV. 0 = off."
    ),
    "Rampe": "Ramp",
    "Utgangen følger inngangen med maks endring 'rate' per sekund.": "The output follows the input with at most 'rate' change per second.",
    "Endringsbegrenser": "Rate limiter",
    "Begrenser hvor fort utgangen kan endre seg: maks 'opp' enheter per sekund oppover og 'ned' per sekund nedover (0 = ubegrenset i den retningen). Når aktiv er av, følger utgangen inngangen direkte. 'begrenser' er på mens utgangen henger etter. Huskes over omstart.": (
        "Limits how fast the output can change: at most 'up' units per second upwards and 'down' "
        "per second downwards (0 = unlimited in that direction). When enable is off, the output "
        "follows the input directly. 'limiting' is on while the output lags behind. Kept over a restart."
    ),
    "opp/s": "up/s",
    "ned/s": "down/s",
    "begrenser": "limiting",
    "Lavpassfilter": "Low-pass filter",
    "Førsteordens filter med tidskonstant tau (sekunder).": "First-order filter with time constant tau (seconds).",
    # ------------------------------------------------------------------ macros
    "Makro-inngang": "Macro input",
    "En inngang på makroblokken. Rekkefølgen på blokken følger høyden på tegningen.": (
        "An input on the macro block. The order on the block follows the height on the drawing."
    ),
    "Navn på pinnen": "Pin name",
    "inn1": "in1",
    "Standardverdi (når pinnen ikke er koblet)": "Default value (when the pin is not connected)",
    "Makro-utgang": "Macro output",
    "En utgang på makroblokken. Rekkefølgen følger høyden på tegningen.": (
        "An output on the macro block. The order follows the height on the drawing."
    ),
    "ut1": "out1",
    "Makro": "Macro",
    "Egendefinert makroblokk.": "Custom macro block.",
    # ------------------------------------------------------------------ KNX / Modbus
    "KNX send": "KNX send",
    "Sender verdien til en KNX-gruppeadresse (knx.send) med valgt DPT. Sender bare ved endring, med dødbånd, minste intervall og valgfri syklisk sending.": (
        "Sends the value to a KNX group address (knx.send) with the chosen DPT. Sends only on change, with "
        "deadband, minimum interval and optional cyclic sending."
    ),
    "1.001 Av/på": "1.001 On/off",
    "1.008 Opp/ned": "1.008 Up/down",
    "1.009 Åpne/lukk": "1.009 Open/close",
    "5.001 Prosent 0–100 %": "5.001 Percent 0–100 %",
    "5.010 Heltall 0–255": "5.010 Integer 0–255",
    "7.001 Heltall 0–65535": "7.001 Integer 0–65535",
    "9.001 Temperatur °C": "9.001 Temperature °C",
    "9.007 Fuktighet %": "9.007 Humidity %",
    "9.008 CO₂ ppm": "9.008 CO₂ ppm",
    "13.001 Heltall 32 bit": "13.001 Integer 32 bit",
    "14.056 Effekt W (float)": "14.056 Power W (float)",
    "17.001 Scene 0–63": "17.001 Scene 0–63",
    "Annen DPT…": "Other DPT…",
    "f.eks. 9.005 eller percent": "e.g. 9.005 or percent",
    "Send syklisk hvert (s, 0 = av)": "Send cyclically every (s, 0 = off)",
    "Send ved oppstart": "Send on start",
    "KNX lytt": "KNX listen",
    "Lytter på telegrammer til en KNX-gruppeadresse (knx_event) og gir ut siste verdi. 'ny' er en puls når et telegram kommer. Kan sende leseforespørsel ved oppstart.": (
        "Listens for telegrams to a KNX group address (knx_event) and outputs the latest value. 'new' is a pulse "
        "when a telegram arrives. Can send a read request on start."
    ),
    "Send leseforespørsel ved oppstart": "Send a read request on start",
    "Modbus skriv": "Modbus write",
    "Skriver til et holding-register eller en coil via HAs Modbus-integrasjon (modbus.write_register / write_coil). Råverdi = verdi × skala. Les Modbus-verdier med «Les entitet» mot en Modbus-sensor.": (
        "Writes to a holding register or a coil through HA's Modbus integration (modbus.write_register / "
        "write_coil). Raw value = value × scale. Read Modbus values with “Read entity” on a Modbus sensor."
    ),
    "Hub (navn i modbus-oppsettet)": "Hub (name in the modbus configuration)",
    "Enhetsadresse (slave)": "Device address (slave)",
    "Registeradresse": "Register address",
    "Holding-register": "Holding register",
    "int32 (2 reg.)": "int32 (2 reg.)",
    "uint32 (2 reg.)": "uint32 (2 reg.)",
    "float32 (2 reg.)": "float32 (2 reg.)",
    "Ordrekkefølge (32 bit)": "Word order (32 bit)",
    "Høy først (big)": "High first (big)",
    "Lav først (swap)": "Low first (swap)",
    # ------------------------------------------------------------------ engine warnings and errors
    "Ukjent makro '{mid}' ({full}) ignorert": "Unknown macro '{mid}' ({full}) ignored",
    "Makroen «{name}» brukes i seg selv ({full}) – ignorert": "The macro “{name}” is used inside itself ({full}) – ignored",
    "Ukjent makroutgang {pin} ignorert": "Unknown macro output {pin} ignored",
    "Ukjent makroinngang {pin} ignorert": "Unknown macro input {pin} ignored",
    "Ukjent blokktype '{btype}' ({node_id}) ignorert": "Unknown block type '{btype}' ({node_id}) ignored",
    "Duplisert node-id {node_id} ignorert": "Duplicate node id {node_id} ignored",
    "Tråd til ukjent blokk ignorert": "Wire to an unknown block ignored",
    "Ukjent utgang {port} ignorert": "Unknown output {port} ignored",
    "Ukjent inngang {port} ignorert": "Unknown input {port} ignored",
    "Inngang {port} har flere tråder – siste brukes": "Input {port} has several wires – the last one is used",
    "Koblingspunktet «{name}» finnes flere ganger – første brukes": "The connector “{name}” exists more than once – the first one is used",
    "Koblingspunktet «{name}» har ingen sender": "The connector “{name}” has no sender",
    "Ingen sender med navnet «{name}»": "No sender with the name “{name}”",
    "Ugyldig uttrykk": "Invalid expression",
    "KNX-integrasjonen er ikke lastet i Home Assistant": "The KNX integration is not loaded in Home Assistant",
    # expressions (Formula block)
    "Potens utenfor gyldig område": "Power out of range",
    "Tomt uttrykk": "Empty expression",
    "Uttrykket er for langt": "The expression is too long",
    "Syntaksfeil: {msg}": "Syntax error: {msg}",
    "Bare tall er tillatt som konstanter": "Only numbers are allowed as constants",
    "Ukjent navn: {name}": "Unknown name: {name}",
    "Operator ikke tillatt": "Operator not allowed",
    "Sammenligning ikke tillatt": "Comparison not allowed",
    "Ukjent funksjon": "Unknown function",
    "Navngitte argumenter er ikke tillatt": "Named arguments are not allowed",
    "Ikke tillatt i uttrykk: {kind}": "Not allowed in an expression: {kind}",
    # writing to HA
    "Tjenesten {service} finnes ikke": "The service {service} does not exist",
    "Ugyldig entitet: {entity_id}": "Invalid entity: {entity_id}",
    "Egendefinert tjeneste må være på formen domene.tjeneste": "A custom service must have the form domain.service",
    "Ukjent handling: {action}": "Unknown action: {action}",
    "Makroen kan ikke inneholde seg selv (direkte eller via andre makroer)": (
        "The macro cannot contain itself (directly or through other macros)"
    ),
    # device class (Publish value)
    "«{name}»: device class «{dc}» finnes ikke for av/på-signaler og brukes ikke": (
        "“{name}”: device class “{dc}” does not exist for on/off signals and is not used"
    ),
    "«{name}»: device class brukes bare på tall og av/på-signaler": (
        "“{name}”: a device class is only used for numbers and on/off signals"
    ),
    "«{name}»: device class «{dc}» finnes ikke for tallsensorer og brukes ikke": (
        "“{name}”: device class “{dc}” does not exist for number sensors and is not used"
    ),
    "«{name}»: device class «{dc}» er ikke for tall og brukes ikke": (
        "“{name}”: device class “{dc}” is not for numbers and is not used"
    ),
    "«{name}»: «{dc}» kan ikke være en måling, så sensoren får ikke langtidsstatistikk": (
        "“{name}”: “{dc}” cannot be a measurement, so the sensor gets no long-term statistics"
    ),
    "«{name}»: enheten «{unit}» passer ikke til «{dc}» (gyldige: {valid})": (
        "“{name}”: the unit “{unit}” does not fit “{dc}” (valid: {valid})"
    ),
    "ingen enhet": "no unit",
    # websocket
    "FBD Logic er ikke lastet": "FBD Logic is not loaded",
    "Programmet finnes ikke": "The program does not exist",
    "Ugyldig program: {err}": "Invalid program: {err}",
    "Fant ikke settpunkt/bryter": "Setpoint/switch not found",
    "Makroen finnes ikke": "The macro does not exist",
    "Ugyldig makro: {err}": "Invalid macro: {err}",
    "Makroen er i bruk i: {users}": "The macro is used in: {users}",
    # HA texts
    "Funksjonsblokker": "Function blocks",
    "Funksjonsblokkprogram": "Function block program",
}
