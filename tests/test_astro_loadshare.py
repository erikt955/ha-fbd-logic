"""Astro clock and load balancing blocks (0.6.0)."""

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.fbd_logic.blocks import LIBRARY, share_current, sun_events, sun_position
from custom_components.fbd_logic.engine import Program

CEST = timezone(timedelta(hours=2))
CET = timezone(timedelta(hours=1))
OSLO = {"lat": "59.9139", "lon": "10.7522"}
TROMSO = {"lat": "69.6492", "lon": "18.9553"}


class IO:
    def __init__(self, location=None):
        self._loc = location

    def location(self):
        return self._loc


def astro(params=None, io=None):
    node = {"id": "a", "type": "astro", "params": params or {}, "consts": {}}
    return Program({"id": "p", "name": "t", "nodes": [node], "links": []}, io=io or IO())


def hm(minutes):
    return f"{int(minutes // 60):02d}:{int(round(minutes % 60)):02d}"


# ---------------------------------------------------------------- astro clock
@pytest.mark.parametrize(
    ("day", "tz", "rise", "set_"),
    [
        (datetime(2024, 6, 21, 12, 0, tzinfo=CEST), CEST, 3 * 60 + 54, 22 * 60 + 44),
        (datetime(2024, 12, 21, 12, 0, tzinfo=CET), CET, 9 * 60 + 18, 15 * 60 + 12),
        (datetime(2024, 3, 20, 12, 0, tzinfo=CET), CET, 6 * 60 + 17, 18 * 60 + 32),
    ],
)
def test_astro_sunrise_sunset_oslo(day, tz, rise, set_):
    p = astro(OSLO)
    p.step(0, day)
    out = p.nodes["a"].outputs
    assert abs(out["rise"] - rise) <= 3, hm(out["rise"])
    assert abs(out["set"] - set_) <= 3, hm(out["set"])
    assert out["day"] is True


def test_astro_elevation_and_azimuth_at_noon():
    # Solar noon in Oslo on midsummer is about 13:19 CEST: sun due south, ~53.5° high
    elev, azi = sun_position(datetime(2024, 6, 21, 11, 19), 59.9139, 10.7522)
    assert abs(elev - 53.5) < 0.5
    assert abs(azi - 180) < 2
    # 06:00 CEST: low in the north-east (reference: astral 10.98° / 61.59°)
    elev, azi = sun_position(datetime(2024, 6, 21, 4, 0), 59.9139, 10.7522)
    assert abs(azi - 61.59) < 0.5 and abs(elev - 10.98) < 0.3


def test_astro_late_sunset_crossing_midnight():
    # Tromsø 15 May: a short night around solar midnight (about 00:40 CEST): the sun sets
    # just before midnight and rises after it, so 'opp' is a small number of minutes.
    p = astro(TROMSO)
    p.step(0, datetime(2024, 5, 15, 12, 0, tzinfo=CEST))
    out = p.nodes["a"].outputs
    assert 23 * 60 + 30 < out["set"] < 24 * 60 and 60 < out["rise"] < 120, (hm(out["rise"]), hm(out["set"]))
    p.step(1, datetime(2024, 5, 15, 0, 40, tzinfo=CEST))
    assert p.nodes["a"].outputs["day"] is False


def test_astro_night_and_twilight():
    p = astro(OSLO)
    p.step(0, datetime(2024, 12, 21, 16, 0, tzinfo=CET))  # 48 min after sunset
    assert p.nodes["a"].outputs["day"] is False
    civil = astro({**OSLO, "horizon": "civil"})
    civil.step(0, datetime(2024, 12, 21, 15, 40, tzinfo=CET))  # still civil twilight
    assert civil.nodes["a"].outputs["day"] is True
    custom = astro({**OSLO, "horizon": "custom", "elev": 10})
    custom.step(0, datetime(2024, 12, 21, 12, 0, tzinfo=CET))  # sun only ~6.7° high
    assert custom.nodes["a"].outputs["day"] is False


def test_astro_midnight_sun_and_polar_night():
    p = astro(TROMSO)
    p.step(0, datetime(2024, 6, 21, 0, 30, tzinfo=CEST))
    out = p.nodes["a"].outputs
    assert out["day"] is True and out["rise"] == -1 and out["set"] == -1
    p = astro(TROMSO)
    p.step(0, datetime(2024, 12, 21, 12, 0, tzinfo=CET))
    out = p.nodes["a"].outputs
    assert out["day"] is False and out["rise"] == -1 and out["set"] == -1
    assert out["elev"] < -0.833
    civil = astro({**TROMSO, "horizon": "civil"})
    civil.step(0, datetime(2024, 12, 21, 12, 0, tzinfo=CET))
    assert civil.nodes["a"].outputs["day"] is True  # blue light at noon in the polar night


def test_astro_uses_ha_location_and_reports_missing():
    p = astro(io=IO((59.9139, 10.7522)))
    p.step(0, datetime(2024, 6, 21, 12, 0, tzinfo=CEST))
    assert p.nodes["a"].error is None and p.nodes["a"].outputs["day"] is True
    p = astro(io=IO(None))
    p.step(0, datetime(2024, 6, 21, 12, 0, tzinfo=CEST))
    assert "posisjon" in (p.nodes["a"].error or "")


def test_sun_events_none_in_polar_night():
    assert sun_events(2024, 12, 21, 69.6492, 18.9553, -0.833) == (None, None)


# ---------------------------------------------------------------- load balancing
def test_share_even_and_capped():
    assert share_current(20, [(True, 1, 32), (True, 1, 32)], 6, True) == ([10, 10], 0)
    # a charger with a lower max leaves the rest to the other
    assert share_current(40, [(True, 1, 16), (True, 1, 32)], 6, True) == ([16, 24], 0)
    # everything at max: the rest is reported
    assert share_current(80, [(True, 1, 16), (True, 1, 32)], 6, True) == ([16, 32], 32)


def test_share_priority_when_tight():
    # both get the minimum, the rest to the higher priority
    assert share_current(20, [(True, 2, 32), (True, 1, 32)], 6, True) == ([14, 6], 0)
    # room for only one minimum: the higher priority charges, the other pauses
    assert share_current(10, [(True, 1, 32), (True, 2, 32)], 6, True) == ([0, 10], 0)
    # not even one minimum: all paused
    assert share_current(5, [(True, 1, 32), (True, 1, 32)], 6, True) == ([0, 0], 5)


def test_share_inactive_whole_and_fractional():
    assert share_current(20, [(False, 1, 32), (True, 1, 32)], 6, True) == ([0, 20], 0)
    alloc, rest = share_current(21, [(True, 1, 32), (True, 1, 32)], 6, True)
    assert sorted(alloc) == [10, 11] and rest == 0
    assert share_current(21, [(True, 1, 32), (True, 1, 32)], 6, False) == ([10.5, 10.5], 0)
    # three with equal priority, one capped low
    assert share_current(30, [(True, 1, 32), (True, 1, 6), (True, 1, 32)], 6, True) == ([12, 6, 12], 0)


def test_loadshare_block_outputs_follow_charger_count():
    bdef = LIBRARY["loadshare"]
    assert [p.name for p in bdef.output_ports({"n": 3})] == ["out1", "out2", "out3", "rest", "lim"]
    node = {
        "id": "lb",
        "type": "loadshare",
        "params": {"n": 3},
        "consts": {"avail": 25, "prio1": 1, "prio2": 3, "prio3": 1, "en3": False, "max2": 16},
    }
    p = Program({"id": "p", "name": "t", "nodes": [node], "links": []}, io=IO())
    p.step(0)
    out = p.nodes["lb"].outputs
    assert out["out2"] == 16 and out["out1"] == 9 and out["out3"] == 0
    assert out["rest"] == 0 and out["lim"] is True
    # a wire from a dynamic output is accepted
    data = {
        "id": "p",
        "name": "t",
        "nodes": [node, {"id": "k", "type": "abs", "consts": {}}],
        "links": [{"id": "l", "from": "lb", "from_port": "out3", "to": "k", "to_port": "in"}],
    }
    p2 = Program(data, io=IO())
    assert not p2.warnings
