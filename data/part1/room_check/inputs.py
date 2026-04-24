#!/usr/bin/env python3
"""
TEAM 1 — THE TRANSLATOR (inputs.py)

The sensor speaks numbers. The rest of the code speaks context.
This module cleans raw sensor readings, catches impossible values,
and adds time-of-day context.

Public API (called by main.py):
    read_manual() -> dict
    read_from_csv(filepath) -> dict
    read_from_inkbird() -> dict   # optional, delegates to inkbird.py
    validate_readings(readings) -> dict
    add_context(readings, dt=None) -> dict

This file MUST return the standard Room Check schema:
    {
      "co2_ppm": float | None,
      "pm25_ugm3": float | None,
      "temperature_f": float | None,
      "humidity_pct": float | None,
      "voc_index": float | None,
    }
"""

from __future__ import annotations

import csv
from datetime import datetime
from typing import Optional

# Physically possible ranges — anything outside means the sensor is broken
# or the value is nonsense. Set those to None so later stages mark UNKNOWN.
VALID_RANGES = {
    "co2_ppm":        (300, 5000),
    "pm25_ugm3":      (0, 500),
    "temperature_f":  (20, 130),
    "humidity_pct":   (0, 100),
    "voc_index":      (0, 500),
}

# This specific library's schedule. Used by add_context().
LIBRARY_SCHEDULE = {
    # weekday: (library_open, library_close, offices_open, offices_close)
    0: ((10, 20), (8.5, 17)),   # Mon
    1: ((10, 20), (8.5, 17)),   # Tue
    2: ((10, 20), (8.5, 17)),   # Wed
    3: ((10, 20), (8.5, 17)),   # Thu
    4: ((10, 18), (8.5, 17)),   # Fri
    5: ((10, 18), None),        # Sat
    6: (None, None),            # Sun
}

EMPTY_READINGS = {k: None for k in VALID_RANGES}


def _prompt_float(label: str) -> Optional[float]:
    raw = input(f"  {label} (blank = skip): ").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        print(f"    ! couldn't parse '{raw}' — marking as unknown")
        return None


def read_manual() -> dict:
    """Prompt a user for each sensor value. Returns the standard schema."""
    print("\n  Enter sensor readings (press Enter to skip a value):")
    return {
        "co2_ppm":       _prompt_float("CO2 (ppm)"),
        "pm25_ugm3":     _prompt_float("PM2.5 (µg/m³)"),
        "temperature_f": _prompt_float("Temperature (°F)"),
        "humidity_pct":  _prompt_float("Humidity (%RH)"),
        "voc_index":     _prompt_float("VOC index"),
    }


def read_from_csv(filepath: str) -> Optional[dict]:
    """Read the LAST row of a CSV and return readings.

    Expected columns: timestamp, co2_ppm, pm25_ugm3, temperature_f,
    humidity_pct, voc_index.
    """
    try:
        with open(filepath, "r", newline="") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        print(f"  ! CSV not found: {filepath}")
        return None

    if not rows:
        print(f"  ! CSV is empty: {filepath}")
        return None

    last = rows[-1]
    out = dict(EMPTY_READINGS)
    for key in VALID_RANGES:
        raw = last.get(key)
        if raw in (None, ""):
            continue
        try:
            out[key] = float(raw)
        except ValueError:
            out[key] = None
    out["timestamp"] = last.get("timestamp")
    return out


def read_from_inkbird() -> Optional[dict]:
    """Pull a fresh reading from an Inkbird BLE monitor.

    Delegates to inkbird.py so Team 1 doesn't have to own the BLE stack.
    Returns None if the device can't be reached — main.py should fall
    back to CSV or manual entry.
    """
    try:
        from inkbird import read_once
    except Exception as exc:
        print(f"  ! Inkbird driver unavailable: {exc}")
        return None
    return read_once()


def validate_readings(readings: dict) -> dict:
    """Replace impossible values with None so nothing downstream crashes."""
    cleaned = dict(readings)
    for key, (lo, hi) in VALID_RANGES.items():
        val = cleaned.get(key)
        if val is None:
            continue
        if not isinstance(val, (int, float)) or val < lo or val > hi:
            cleaned[key] = None
    return cleaned


def add_context(readings: dict, dt: Optional[datetime] = None) -> dict:
    """Tag readings with building open/closed context and flag oddities.

    Adds two keys:
      building_status: "open" | "offices_only" | "closed"
      after_hours_flag: str | None   # populated if CO2 is elevated when closed
    """
    if dt is None:
        dt = datetime.now()

    weekday = dt.weekday()
    hour = dt.hour + dt.minute / 60
    library, offices = LIBRARY_SCHEDULE.get(weekday, (None, None))

    def _in_window(window):
        if window is None:
            return False
        start, end = window
        return start <= hour < end

    if _in_window(library):
        status = "open"
    elif _in_window(offices):
        status = "offices_only"
    else:
        status = "closed"

    out = dict(readings)
    out["building_status"] = status
    out["timestamp"] = out.get("timestamp") or dt.isoformat(timespec="seconds")

    flag = None
    co2 = out.get("co2_ppm")
    if status == "closed" and co2 is not None and co2 > 500:
        flag = (
            f"Elevated CO2 ({co2:.0f} ppm) while building should be empty — "
            "possible AHU weekend-drift (BAS-1 fix not holding)."
        )
    out["after_hours_flag"] = flag
    return out
