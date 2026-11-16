"""Entities created by FBD programs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .blocks import to_bool, to_num, to_str
from .const import DOMAIN, MANUFACTURER, MODEL, VERSION
from .device_class import publish_class
from .i18n import tr

if TYPE_CHECKING:
    from .manager import FbdManager


class FbdEntity(Entity):
    """Base class for all FBD entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: FbdManager, spec: dict[str, Any]) -> None:
        self.manager = manager
        self.program_id: str = spec["program_id"]
        self.node_id: str = spec["node_id"]
        self.spec: dict[str, Any] = {}
        self._attr_unique_id = f"{self.program_id}_{self.node_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.program_id)},
            name=manager.program_name(self.program_id),
            manufacturer=MANUFACTURER,
            model=tr(MODEL),
            sw_version=VERSION,
        )
        self._apply_spec(spec)

    _added = False

    @property
    def _vkey(self) -> str:
        return f"{self.program_id}:{self.node_id}"

    async def async_added_to_hass(self) -> None:
        self._added = True

    async def async_will_remove_from_hass(self) -> None:
        self._added = False
        key = (self.platform.domain if self.platform else "", self._attr_unique_id)
        if self.manager.entities.get(key) is self:
            self.manager.entities.pop(key, None)

    def write_state(self) -> None:
        """Write state if the entity is live in HA."""
        if self._added and self.hass is not None:
            self.async_write_ha_state()

    def _apply_spec(self, spec: dict[str, Any]) -> None:
        self.spec = spec
        self._attr_name = spec.get("name") or self.node_id

    def update_spec(self, spec: dict[str, Any]) -> None:
        if spec == self.spec:
            return
        self._apply_spec(spec)
        self.write_state()


# ---------------------------------------------------------------------- number
class FbdNumber(FbdEntity, NumberEntity):
    """Setpoint block → adjustable number entity."""

    def _apply_spec(self, spec: dict[str, Any]) -> None:
        super()._apply_spec(spec)
        lo, hi = float(spec.get("min", 0)), float(spec.get("max", 100))
        if hi <= lo:
            hi = lo + 1
        self._attr_native_min_value = lo
        self._attr_native_max_value = hi
        self._attr_native_step = float(spec.get("step") or 0.5)
        self._attr_native_unit_of_measurement = spec.get("unit")
        mode = spec.get("mode", "box")
        self._attr_mode = {"slider": NumberMode.SLIDER, "auto": NumberMode.AUTO}.get(
            mode, NumberMode.BOX
        )

    @property
    def native_value(self) -> float | None:
        value = self.manager.values.get(self._vkey)
        return None if value is None else to_num(value)

    async def async_set_native_value(self, value: float) -> None:
        self.manager.set_value(self.program_id, self.node_id, float(value))


# ---------------------------------------------------------------------- switches
class FbdToggle(FbdEntity, SwitchEntity):
    """Toggle block → switch entity."""

    @property
    def is_on(self) -> bool:
        return to_bool(self.manager.values.get(self._vkey, False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.manager.set_value(self.program_id, self.node_id, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.manager.set_value(self.program_id, self.node_id, False)


class FbdProgramSwitch(FbdEntity, SwitchEntity):
    """Enables/disables a whole program."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:play-pause"
    _attr_translation_key = "program_running"  # name from translations/<language>.json

    def _apply_spec(self, spec: dict[str, Any]) -> None:
        self.spec = spec

    @property
    def is_on(self) -> bool:
        data = self.manager.programs.get(self.program_id)
        return bool(data and data.get("enabled", True))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.manager.async_set_enabled(self.program_id, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.manager.async_set_enabled(self.program_id, False)


# ---------------------------------------------------------------------- published values
class FbdSensor(FbdEntity, SensorEntity):
    """Publish block (numeric/text) → sensor."""

    _value: Any = None

    def _apply_spec(self, spec: dict[str, Any]) -> None:
        super()._apply_spec(spec)
        kind = spec.get("kind", "num")
        self._kind = kind
        self._decimals = int(spec.get("decimals", 2))
        if kind == "num":
            classes = publish_class(spec)
            self._attr_native_unit_of_measurement = spec.get("unit")
            self._attr_state_class = classes.state_class
            self._attr_suggested_display_precision = self._decimals
            self._attr_device_class = classes.device_class
        else:
            self._attr_native_unit_of_measurement = None
            self._attr_state_class = None
            self._attr_device_class = None
            self._attr_suggested_display_precision = None
        value = self.manager.published.get(self._vkey)
        if value is not None:
            self._value = self._convert(value)

    def _convert(self, value: Any) -> Any:
        if self._kind == "num":
            return round(to_num(value), self._decimals)
        return to_str(value)[:255]

    @property
    def native_value(self) -> Any:
        return self._value

    def set_published(self, value: Any) -> None:
        new = self._convert(value)
        if new != self._value:
            self._value = new
            self.write_state()


class FbdBinarySensor(FbdEntity, BinarySensorEntity):
    """Publish block (boolean) → binary_sensor."""

    _value: bool | None = None

    def _apply_spec(self, spec: dict[str, Any]) -> None:
        super()._apply_spec(spec)
        self._attr_device_class = publish_class(spec).device_class
        value = self.manager.published.get(self._vkey)
        if value is not None:
            self._value = to_bool(value)

    @property
    def is_on(self) -> bool | None:
        return self._value

    def set_published(self, value: Any) -> None:
        new = to_bool(value)
        if new != self._value:
            self._value = new
            self.write_state()


def create_entity(manager: FbdManager, spec: dict[str, Any]) -> FbdEntity:
    platform = spec["platform"]
    if platform == "number":
        return FbdNumber(manager, spec)
    if platform == "switch":
        if spec.get("kind") == "program_enabled":
            return FbdProgramSwitch(manager, spec)
        return FbdToggle(manager, spec)
    if platform == "binary_sensor":
        return FbdBinarySensor(manager, spec)
    return FbdSensor(manager, spec)
