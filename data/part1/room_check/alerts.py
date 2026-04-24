#!/usr/bin/env python3
"""
TEAM 4 — THE FIRST RESPONDER (alerts.py)

Plain-language alerts a librarian can act on, plus a Community
Resilience Index (0-100) that accounts for the building's known
vulnerabilities.

Public API (called by main.py):
    get_alert_message(overall_status, readings, statuses) -> str
    get_resilience_index(statuses, readings, vulnerabilities) -> dict
"""

from __future__ import annotations

from typing import Iterable

# Smoke and heat danger thresholds — slightly above "RED" because these
# unlock specific librarian instructions (don't open windows, etc.).
SMOKE_PM25 = 35.4
HEAT_TEMP_F = 88
HIGH_CO2 = 1200


def _red_params(statuses: dict) -> list:
    return [k.replace("_status", "") for k, v in statuses.items() if v == "RED"]


def _yellow_params(statuses: dict) -> list:
    return [k.replace("_status", "") for k, v in statuses.items() if v == "YELLOW"]


def get_alert_message(overall_status: str, readings: dict, statuses: dict) -> str:
    """Return the message to show the person standing in the building."""
    pm25 = readings.get("pm25_ugm3")
    temp = readings.get("temperature_f")
    co2 = readings.get("co2_ppm")

    smoke = pm25 is not None and pm25 > SMOKE_PM25
    heat  = temp is not None and temp > HEAT_TEMP_F
    stuffy = co2 is not None and co2 > HIGH_CO2

    if overall_status == "GREEN":
        return "Air quality is good. The room is safe for all occupants. No action needed."

    if overall_status == "UNKNOWN":
        return "Some sensor readings are unavailable. Cannot fully assess room safety. Check sensor connections."

    if overall_status == "RED":
        if smoke and heat:
            return ("URGENT: Dangerous air quality AND extreme heat. "
                    "Do NOT open windows — outdoor air may contain smoke. "
                    "Move occupants to an interior room with filtered air. "
                    "Contact building management immediately.")
        if smoke:
            return ("URGENT: Air particulate levels are dangerous. "
                    "Do NOT open windows — this may be a smoke event. "
                    "Keep doors closed. Run any available air purifiers. "
                    "Contact building management now.")
        if heat:
            return ("URGENT: Temperature is dangerously high. "
                    "Move vulnerable occupants (elderly, children) to the coolest area. "
                    "Provide water. Contact building management. "
                    "If no cooling available, consider evacuation.")
        if stuffy:
            return ("URGENT: Carbon dioxide levels are very high — poor ventilation. "
                    "Open windows and doors if outdoor air is clean. "
                    "This may indicate HVAC failure — alert building staff.")
        params = ", ".join(_red_params(statuses))
        return (f"URGENT: Unsafe conditions detected ({params}). "
                "Take action immediately and contact building management.")

    # YELLOW
    params = " and ".join(_yellow_params(statuses)) or "some readings"
    return (f"Caution: {params} readings are outside the ideal range. "
            "Monitor closely and consider improving ventilation or adjusting temperature. "
            "Alert staff if conditions worsen.")


def get_resilience_index(statuses: dict, readings: dict, vulnerabilities: dict) -> dict:
    """Compute a 0-100 Community Resilience Index.

    Starts at 100, deducts for:
      - known building vulnerabilities (no generator, R-22 chillers, etc.)
      - current YELLOW/RED sensor statuses
      - after-hours drift flags
    """
    score = 100.0
    breakdown = []

    for vuln_id, spec in vulnerabilities.items():
        deduction = spec.get("points_deducted", 0)
        score -= deduction
        breakdown.append({
            "cause": vuln_id,
            "note": spec.get("note", ""),
            "points": -deduction,
        })

    for key, value in statuses.items():
        if key == "overall_status":
            continue
        if value == "RED":
            score -= 10
            breakdown.append({"cause": f"{key}=RED", "note": "Current unsafe reading", "points": -10})
        elif value == "YELLOW":
            score -= 4
            breakdown.append({"cause": f"{key}=YELLOW", "note": "Current caution reading", "points": -4})

    if readings.get("after_hours_flag"):
        score -= 5
        breakdown.append({
            "cause": "after_hours_flag",
            "note": readings["after_hours_flag"],
            "points": -5,
        })

    score = max(0.0, min(100.0, score))

    if score >= 80:
        band = "RESILIENT"
    elif score >= 60:
        band = "FRAGILE"
    elif score >= 40:
        band = "AT RISK"
    else:
        band = "CRITICAL"

    return {
        "score": round(score, 1),
        "band": band,
        "breakdown": breakdown,
    }
