#!/usr/bin/env python3
"""
TEAM 3 — THE DETECTIVE (room_check.py)

Takes validated readings from Team 1 and thresholds from Team 2.
Produces GREEN/YELLOW/RED status + drift detection.

Public API (called by main.py):
    evaluate_room(readings, thresholds) -> dict
    check_drift(readings, drift_rules) -> list[dict]
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

Status = str  # "GREEN" | "YELLOW" | "RED" | "UNKNOWN"

# Ordering is important: worse statuses win.
STATUS_ORDER = {"GREEN": 0, "UNKNOWN": 1, "YELLOW": 2, "RED": 3}


def _eval_ceiling(value: Optional[float], spec: dict) -> Status:
    if value is None:
        return "UNKNOWN"
    if value <= spec["green_max"]:
        return "GREEN"
    if value <= spec["yellow_max"]:
        return "YELLOW"
    return "RED"


def _eval_range(value: Optional[float], spec: dict) -> Status:
    if value is None:
        return "UNKNOWN"
    if spec["green_min"] <= value <= spec["green_max"]:
        return "GREEN"
    if spec["yellow_min"] <= value <= spec["yellow_max"]:
        return "YELLOW"
    return "RED"


def evaluate_room(readings: dict, thresholds: dict) -> dict:
    """Return status per parameter + overall_status (worst of the lot).

    Returns:
        {
          "co2_ppm_status": "GREEN",
          "pm25_ugm3_status": "GREEN",
          "temperature_f_status": "YELLOW",
          "humidity_pct_status": "GREEN",
          "voc_index_status": "GREEN",
          "overall_status": "YELLOW",
        }
    """
    result = {}
    params = {
        "co2_ppm":       _eval_ceiling,
        "pm25_ugm3":     _eval_ceiling,
        "voc_index":     _eval_ceiling,
        "temperature_f": _eval_range,
        "humidity_pct":  _eval_range,
    }
    for key, fn in params.items():
        spec = thresholds.get(key, {})
        if not spec:
            result[f"{key}_status"] = "UNKNOWN"
            continue
        result[f"{key}_status"] = fn(readings.get(key), spec)

    worst = "GREEN"
    for key in params:
        s = result[f"{key}_status"]
        if STATUS_ORDER[s] > STATUS_ORDER[worst]:
            worst = s
    result["overall_status"] = worst
    return result


def check_drift(readings: dict, drift_rules: dict, dt: Optional[datetime] = None) -> list:
    """Detect when reality diverges from what the auditor promised.

    Returns a list of findings, each:
        {
          "rule": "BAS-1_weekend_co2",
          "fix_id": "BAS-1",
          "description": "...",
          "observed": 530,
          "expected_max": 450,
          "daily_waste_usd": 37.26,
        }
    """
    if dt is None:
        dt = datetime.now()
    findings = []

    status = readings.get("building_status")
    hour = dt.hour

    rule = drift_rules.get("BAS-1_weekend_co2")
    if rule and status == "closed":
        co2 = readings.get("co2_ppm")
        if co2 is not None and co2 > rule["expected_max_co2"]:
            findings.append({
                "rule": "BAS-1_weekend_co2",
                "fix_id": rule["fix_id"],
                "description": rule["description"],
                "observed": co2,
                "expected_max": rule["expected_max_co2"],
                "daily_waste_usd": rule["daily_waste_if_broken_usd"],
            })

    rule = drift_rules.get("BAS-2_setback")
    if rule and (hour >= 21 or hour <= 5):
        temp = readings.get("temperature_f")
        if temp is not None and temp > rule["expected_max_temp_after_hours_f"]:
            findings.append({
                "rule": "BAS-2_setback",
                "fix_id": rule["fix_id"],
                "description": rule["description"],
                "observed": temp,
                "expected_max": rule["expected_max_temp_after_hours_f"],
                "daily_waste_usd": rule["daily_waste_if_broken_usd"],
            })

    return findings
