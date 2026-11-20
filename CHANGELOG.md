# Changelog

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
