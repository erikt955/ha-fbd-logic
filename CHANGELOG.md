# Changelog

## 0.6.0

- New block **Astro clock** (`ASTRO`, Time): sun elevation and azimuth, `day` while the sun is above the horizon and `night` as its opposite, civil or nautical twilight or a custom elevation, and today's sunrise and sunset (minutes after midnight). Offsets in minutes move when `day` starts and ends, e.g. −30 on `set ±min` for outdoor lights on `night` 30 minutes before sunset. Uses the location in Home Assistant, or your own latitude/longitude. Works with midnight sun and polar night; the times agree with the `astral` library within a minute.
- New block **Load balancing** (`LB`, Control): divides the available current between 1–8 chargers. Every active charger first gets the minimum (6 A by default), highest priority first, and a charger that cannot get it is paused (0 A). The rest goes to the highest priority first and is shared evenly within a priority, up to each charger's max. Outputs per charger, plus unused current and a `limited` flag.
- Blocks can have a variable number of outputs that follows a setting (used by Load balancing). Wires from outputs that disappear are removed.

## 0.5.0

- New block **Sample & hold** (`S&H`, Control): holds the value and lets the newest value through at most once per interval, without a ramp – for example a PID output that should reach an actuator at most every 10 s. A change after a quiet period passes at once, the output always catches up with an input that has stopped changing, and changes smaller than the deadband are held. Works for numbers, on/off and text, has an `updated` pulse and is kept over a restart.
- **Wire bends can be moved.** Select a wire and drag its bend (the vertical segment, or the lower one for a wire going backwards). The bend snaps to the grid, is saved with the program and moves along when both blocks are moved together. Double-click the wire, or press “Automatic routing”, to reset it.
- **Pins lie on the grid.** Header, info line and pin rows are 20 px, so every pin is on the grid and an output and an input can always be put level for a straight wire. Blocks become slightly taller.
- **Icon.** The integration ships its own icon (`brand/`), shown in HA 2026.3 and later.

## 0.4.1

- New block **Rate limiter** (`RATE`, Control): limits how fast a value may change, with separate rates up and down (0 = unlimited in that direction), an enable input that bypasses it, and a `limiting` output. The output is kept over a restart.

## 0.4.0

- **English.** The panel and the blocks follow the language of the HA user: Norwegian for nb/nn, English for every other language. Warnings, block errors and entity names follow HA's system language.
- The program switch is named from the translation files (`Running` / `Kjører`), so a new program in English gets `switch.<program>_running`. Existing entities keep their ids.
- English README, `README.nb.md` in Norwegian, an English example program, MIT license, GitHub Actions (hassfest, HACS, tests) and links in `manifest.json` for HACS.
- The trend CSV uses `,` and a decimal point in English, `;` and a decimal comma in Norwegian.

## 0.3.1

- PID controller: manual mode with a manual value, bumpless transfer back to automatic (the integrator follows the output while off or in manual), a bias input, a continuous deadband and an `auto` output.
- A lowered output limit now takes effect at once.
- Fixed: the PID integrator and the low-pass filter value were reset on the first scan after saving the program or restarting HA.

## 0.3.0

- **Scan on change**: a program is scanned at once when an input changes (Read entity, KNX listen, Setpoint, Switch). Bursts give one scan, and scans come at least 20 ms apart. On by default.
- Publish value sends only on change, with deadband and minimum interval.
- The PID derivative is filtered (Td/10), so short scans right after a PV step give no large kick.
- The live view gets a trailing update when a scan falls inside its update throttle.

## 0.2.3

- The device class of Publish value is case-insensitive (`Temperature` works). The field suggests common classes, and saving warns about an unknown class, a unit that does not fit, or a class that cannot be a measurement.

## 0.2.2

- Removed a deprecation warning from HA 2026.11 about device registry lookups. Short trend names keep the port name.

## 0.2.1

- Fixed the panel height in HA, and a narrow layout for the trend.

## 0.2.0

- Weekly schedule, several pages per program with connectors, macros, forcing, trend in the panel, MUX, priority select, get bit, KNX send/listen and Modbus write.

## 0.1.0

- First version: the runtime, 49 blocks, the editor and the entities.
