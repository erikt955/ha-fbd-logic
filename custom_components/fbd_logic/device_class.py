"""Device class and state class for the entities made by Publish blocks.

Checked in one place, so saving a program can show the user what HA would otherwise only log or
ignore silently: an unknown device class, a unit that does not fit it, or a device class that
cannot be a measurement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import (
    DEVICE_CLASS_STATE_CLASSES,
    DEVICE_CLASS_UNITS,
    SensorDeviceClass,
    SensorStateClass,
)

from .i18n import tr

# Sensor device classes whose state is not a number.
_NOT_NUMERIC = {SensorDeviceClass.DATE, SensorDeviceClass.ENUM, SensorDeviceClass.TIMESTAMP}


@dataclass
class PublishClass:
    device_class: SensorDeviceClass | BinarySensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    problems: list[str] = field(default_factory=list)


def normalize(value: Any) -> str | None:
    """'Temperature' and ' Wind speed ' become 'temperature' and 'wind_speed'."""
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return text or None


def publish_class(spec: dict[str, Any]) -> PublishClass:
    """Device class and state class for a publish spec, with problems in HA's system language."""
    platform = spec.get("platform")
    kind = spec.get("kind", "num")
    name = spec.get("name") or spec.get("node_id", "")
    dc = normalize(spec.get("device_class"))
    measurement = SensorStateClass.MEASUREMENT if platform == "sensor" and kind == "num" else None
    if not dc:
        return PublishClass(state_class=measurement)

    if platform == "binary_sensor":
        try:
            return PublishClass(BinarySensorDeviceClass(dc))
        except ValueError:
            return PublishClass(problems=[tr("«{name}»: device class «{dc}» finnes ikke for av/på-signaler og brukes ikke", name=name, dc=dc)])

    if kind != "num":
        return PublishClass(problems=[tr("«{name}»: device class brukes bare på tall og av/på-signaler", name=name)])
    try:
        cls = SensorDeviceClass(dc)
    except ValueError:
        return PublishClass(
            state_class=measurement,
            problems=[tr("«{name}»: device class «{dc}» finnes ikke for tallsensorer og brukes ikke", name=name, dc=dc)],
        )
    if cls in _NOT_NUMERIC:
        return PublishClass(
            state_class=measurement,
            problems=[tr("«{name}»: device class «{dc}» er ikke for tall og brukes ikke", name=name, dc=dc)],
        )

    result = PublishClass(cls, measurement)
    allowed = DEVICE_CLASS_STATE_CLASSES.get(cls)
    if allowed is not None and SensorStateClass.MEASUREMENT not in allowed:
        # energy, gas, water …: HA rejects 'measurement'; without a state class there is no long-term statistics.
        result.state_class = None
        result.problems.append(
            tr("«{name}»: «{dc}» kan ikke være en måling, så sensoren får ikke langtidsstatistikk", name=name, dc=dc)
        )
    units = DEVICE_CLASS_UNITS.get(cls)
    unit = spec.get("unit") or None
    if units is not None and unit not in units:
        valid = ", ".join(sorted(str(u) for u in units if u is not None)) or tr("ingen enhet")
        result.problems.append(
            tr("«{name}»: enheten «{unit}» passer ikke til «{dc}» (gyldige: {valid})", name=name, unit=unit or "", dc=dc, valid=valid)
        )
    return result
