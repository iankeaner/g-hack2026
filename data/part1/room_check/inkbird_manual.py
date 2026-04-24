#!/usr/bin/env python3
"""
Inkbird IAM-O2 manual entry flow.

The Inkbird IAM-O2's BLE protocol is proprietary and the companion app is
flaky enough that BLE sync is not reliable on demo day. This module walks
the student through reading values off the Inkbird's screen and typing
them in. The output format matches exactly what live sources (Dyson,
scenarios, CSV) produce, so main.py's pipeline doesn't care.

Public API:
    read_inkbird_guided() -> dict   # returns a readings dict in the
                                    # standard Room Check schema
"""
from __future__ import annotations

from typing import Optional


# What the IAM-O2 actually measures on its display.
# Other fields (pm25_ugm3, voc_index) are left None so the pipeline
# marks them UNKNOWN — which is accurate, the Inkbird doesn't have
# those sensors.
INKBIRD_FIELDS = [
    {
        "key":     "co2_ppm",
        "label":   "CO2",
        "unit":    "ppm",
        "hint":    "Largest number on the display. Outdoor baseline ~420 ppm; "
                   "occupied room 600-1000 ppm; stuffy > 1200 ppm.",
        "typical": "650",
    },
    {
        "key":     "temperature_f",
        "label":   "Temperature",
        "unit":    "°F",
        "hint":    "If the Inkbird shows °C, press the unit button or multiply by 9/5 + 32. "
                   "Example: 22°C × 9/5 + 32 = 71.6°F.",
        "typical": "72",
    },
    {
        "key":     "humidity_pct",
        "label":   "Humidity",
        "unit":    "%RH",
        "hint":    "Shown with a water-drop icon. Comfortable range 30-60%.",
        "typical": "45",
    },
]


def _prompt_float(field: dict) -> Optional[float]:
    """Prompt for one value, with hint + typical range. Tolerates °C too."""
    prompt = f"  {field['label']} ({field['unit']}) [{field['typical']}]: "
    hint_shown = False
    while True:
        raw = input(prompt).strip()
        if not raw and not hint_shown:
            print(f"    hint: {field['hint']}")
            hint_shown = True
            continue
        if not raw:
            return None
        raw_lower = raw.lower()

        # Tolerate inputs like "22c" or "22 C" — convert °C → °F automatically
        if field["key"] == "temperature_f" and raw_lower.endswith(("c", "°c")):
            try:
                c = float(raw_lower.rstrip("c").rstrip("°").strip())
                f = round(c * 9 / 5 + 32, 2)
                print(f"    converted {c}°C → {f}°F")
                return f
            except ValueError:
                pass

        try:
            return float(raw)
        except ValueError:
            print(f"    couldn't parse {raw!r} — try just the number (or blank to skip).")


def read_inkbird_guided() -> dict:
    """Guided interactive entry for an Inkbird IAM-O2 monitor."""
    print()
    print("=" * 60)
    print(" INKBIRD IAM-O2 — Manual Entry")
    print("=" * 60)
    print(" Read the three numbers off your Inkbird's screen and type")
    print(" each one here. Press Enter twice to skip a value.")
    print(" The Inkbird does not measure PM2.5 or VOCs — those will")
    print(" show as UNKNOWN, which is correct.")
    print("-" * 60)

    out = {
        "co2_ppm":       None,
        "pm25_ugm3":     None,
        "temperature_f": None,
        "humidity_pct":  None,
        "voc_index":     None,
    }
    for field in INKBIRD_FIELDS:
        out[field["key"]] = _prompt_float(field)

    print("-" * 60)
    print(" Captured:")
    for k, v in out.items():
        display = f"{v}" if v is not None else "—"
        print(f"   {k:<16} {display}")
    print("=" * 60)
    return out


if __name__ == "__main__":
    from pprint import pprint
    pprint(read_inkbird_guided())
