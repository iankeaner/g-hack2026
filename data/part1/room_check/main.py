#!/usr/bin/env python3
"""
ROOM CHECK — Integrated Runnable Script
========================================

This is where all five teams' work meets.

    Team 1 (inputs.py)      → reads + cleans + adds context to sensor data
    Team 2 (thresholds.json)→ safety limits + BEPS + drift rules + vulnerabilities
    Team 3 (room_check.py)  → GREEN/YELLOW/RED decision + drift detection
    Team 4 (alerts.py)      → human message + Community Resilience Index
    Team 5 (README / docs)  → this script's structure + local CSV backup

Usage:
    python main.py --source manual
    python main.py --source csv --file sample_data/sensor_log.csv
    python main.py --source inkbird
    python main.py --source inkbird --fallback csv --file sample_data/sensor_log.csv
    python main.py --scenario ventilation_failure   # run a canned scenario
    python main.py --watch --interval 30            # continuously poll

Exit codes:
    0 GREEN, 1 YELLOW, 2 RED, 3 UNKNOWN  (useful for CI / dashboards)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Make sibling modules importable when run from anywhere.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import inputs        # Team 1
import room_check    # Team 3
import alerts        # Team 4


EXIT_BY_STATUS = {"GREEN": 0, "YELLOW": 1, "RED": 2, "UNKNOWN": 3}
BACKUP_LOG = HERE / "local_backup.csv"
ALERTS_LOG = HERE / "alerts.csv"


def load_config(path: Path) -> dict:
    """Team 2 output."""
    with open(path, "r") as f:
        return json.load(f)


def gather_readings(args) -> dict:
    """Pull readings from the requested source, with graceful fallback."""
    readings = None

    if args.scenario:
        readings = load_scenario(args.scenario)
        if readings is None:
            sys.exit(f"Unknown scenario: {args.scenario}")

    elif args.source == "manual":
        readings = inputs.read_manual()

    elif args.source == "inkbird-manual":
        import inkbird_manual
        readings = inkbird_manual.read_inkbird_guided()

    elif args.source == "csv":
        readings = inputs.read_from_csv(args.file)

    elif args.source == "inkbird":
        readings = inputs.read_from_inkbird()
        if readings is None and args.fallback == "csv" and args.file:
            print("  ! Falling back to CSV")
            readings = inputs.read_from_csv(args.file)
        if readings is None and args.fallback == "manual":
            print("  ! Falling back to manual entry")
            readings = inputs.read_manual()

    if readings is None:
        sys.exit("No readings available. Check source and try again.")

    readings = inputs.validate_readings(readings)
    readings = inputs.add_context(readings)
    return readings


def load_scenario(name: str) -> dict | None:
    """Canned scenarios matching the web simulator — useful for judging."""
    scenarios = {
        "normal":              {"co2_ppm": 620, "pm25_ugm3": 8.2,  "temperature_f": 72.4, "humidity_pct": 44, "voc_index": 95},
        "library_baseline":    {"co2_ppm": 680, "pm25_ugm3": 9.0,  "temperature_f": 74.8, "humidity_pct": 48, "voc_index": 110},
        "bas1_drift":          {"co2_ppm": 530, "pm25_ugm3": 7.8,  "temperature_f": 71.0, "humidity_pct": 42, "voc_index": 88},
        "stuffy_room":         {"co2_ppm": 1050,"pm25_ugm3": 10.1, "temperature_f": 76.8, "humidity_pct": 52, "voc_index": 130},
        "ventilation_failure": {"co2_ppm": 1480,"pm25_ugm3": 14.3, "temperature_f": 79.2, "humidity_pct": 58, "voc_index": 180},
        "heat_wave":           {"co2_ppm": 720, "pm25_ugm3": 9.0,  "temperature_f": 87.3, "humidity_pct": 72, "voc_index": 110},
        "smoke_event":         {"co2_ppm": 690, "pm25_ugm3": 89.4, "temperature_f": 73.1, "humidity_pct": 38, "voc_index": 280},
        "power_outage":        {"co2_ppm": 1320,"pm25_ugm3": 18.5, "temperature_f": 84.1, "humidity_pct": 63, "voc_index": 210},
        "combined_emergency":  {"co2_ppm": 1850,"pm25_ugm3": 156.2,"temperature_f": 96.4, "humidity_pct": 78, "voc_index": 420},
    }
    return scenarios.get(name)


def run_once(config: dict, args) -> dict:
    readings = gather_readings(args)

    thresholds = config["air_quality_thresholds"]
    drift_rules = config["drift_rules"]
    vulnerabilities = config["resilience_vulnerabilities"]

    statuses = room_check.evaluate_room(readings, thresholds)
    drift = room_check.check_drift(readings, drift_rules)
    message = alerts.get_alert_message(statuses["overall_status"], readings, statuses)
    resilience = alerts.get_resilience_index(statuses, readings, vulnerabilities)

    payload = {
        "timestamp": readings.get("timestamp") or datetime.now().isoformat(timespec="seconds"),
        "building_status": readings.get("building_status"),
        "readings": {k: readings.get(k) for k in (
            "co2_ppm", "pm25_ugm3", "temperature_f", "humidity_pct", "voc_index")},
        "statuses": statuses,
        "drift": drift,
        "alert": message,
        "resilience": resilience,
        "after_hours_flag": readings.get("after_hours_flag"),
    }
    return payload


def render(payload: dict) -> None:
    s = payload["statuses"]["overall_status"]
    banner = {"GREEN":"[  SAFE  ]","YELLOW":"[ CAUTION ]","RED":"[ UNSAFE ]","UNKNOWN":"[ UNKNOWN ]"}[s]
    print()
    print("=" * 60)
    print(f" ROOM CHECK  {banner}   {payload['timestamp']}")
    print(f" Building: {payload['building_status']}")
    print("=" * 60)
    for k, v in payload["readings"].items():
        st = payload["statuses"].get(f"{k}_status", "?")
        vs = f"{v:>7.1f}" if isinstance(v, (int, float)) else f"{'--':>7}"
        print(f"  {k:<16} {vs}    [{st}]")
    print("-" * 60)
    print(f"  ALERT: {payload['alert']}")
    if payload["drift"]:
        print("  DRIFT FINDINGS:")
        for d in payload["drift"]:
            print(f"    - {d['fix_id']}: observed {d['observed']}, expected ≤ {d['expected_max']} "
                  f"(${d['daily_waste_usd']:.2f}/day wasted)")
    r = payload["resilience"]
    print(f"  RESILIENCE: {r['score']}/100 ({r['band']})")
    print("=" * 60)


def append_backup(payload: dict) -> None:
    """Team 5's job: when WiFi dies, the CSV keeps recording."""
    new_file = not BACKUP_LOG.exists()
    cols = ["timestamp", "building_status",
            "co2_ppm", "pm25_ugm3", "temperature_f", "humidity_pct", "voc_index",
            "overall_status", "alert", "resilience_score"]
    with open(BACKUP_LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(cols)
        w.writerow([
            payload["timestamp"],
            payload["building_status"],
            payload["readings"].get("co2_ppm"),
            payload["readings"].get("pm25_ugm3"),
            payload["readings"].get("temperature_f"),
            payload["readings"].get("humidity_pct"),
            payload["readings"].get("voc_index"),
            payload["statuses"]["overall_status"],
            payload["alert"][:200],
            payload["resilience"]["score"],
        ])


def append_alerts(payload: dict, source: str) -> None:
    """Dedicated alert log with FULL alert text + drift findings + resilience band.

    Separate from local_backup.csv (which is the full-fidelity reading log) so
    a librarian or judge can skim just the actionable alerts and their context.
    """
    new_file = not ALERTS_LOG.exists()
    cols = [
        "timestamp", "source", "building_status",
        "overall_status", "alert_full",
        "co2_ppm", "pm25_ugm3", "temperature_f", "humidity_pct", "voc_index",
        "drift_count", "drift_summary",
        "resilience_score", "resilience_band",
    ]
    drift = payload.get("drift") or []
    drift_summary = "; ".join(
        f"{d['fix_id']}: observed {d['observed']} (exp ≤ {d['expected_max']}, ${d['daily_waste_usd']:.2f}/day)"
        for d in drift
    )
    with open(ALERTS_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(cols)
        w.writerow([
            payload["timestamp"],
            source,
            payload["building_status"],
            payload["statuses"]["overall_status"],
            payload["alert"],  # FULL text — not truncated
            payload["readings"].get("co2_ppm"),
            payload["readings"].get("pm25_ugm3"),
            payload["readings"].get("temperature_f"),
            payload["readings"].get("humidity_pct"),
            payload["readings"].get("voc_index"),
            len(drift),
            drift_summary,
            payload["resilience"]["score"],
            payload["resilience"]["band"],
        ])


def post_to_cloud(payload: dict, url: str) -> None:
    """Team 5's other job: push to the EcoGuard dashboard when possible."""
    try:
        import urllib.request, urllib.error
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as exc:
        print(f"  (cloud sync failed: {exc} — kept local backup only)")


def main():
    p = argparse.ArgumentParser(description="Room Check — integrated runnable.")
    p.add_argument("--source", choices=["manual", "inkbird-manual", "csv", "inkbird"], default="manual")
    p.add_argument("--file", default=str(HERE / "sample_data" / "sensor_log.csv"))
    p.add_argument("--fallback", choices=["none", "csv", "manual"], default="none")
    p.add_argument("--scenario", default=None, help="Skip sources; use a canned scenario (e.g. 'smoke_event').")
    p.add_argument("--config", default=str(HERE / "thresholds.json"))
    p.add_argument("--watch", action="store_true", help="Run continuously.")
    p.add_argument("--interval", type=int, default=30, help="Seconds between polls in --watch mode.")
    p.add_argument("--cloud", default=os.environ.get("ROOMCHECK_CLOUD_URL"),
                   help="POST results to this URL (defaults to $ROOMCHECK_CLOUD_URL).")
    p.add_argument("--json", action="store_true", help="Emit JSON only (no pretty output).")
    args = p.parse_args()

    config = load_config(Path(args.config))

    def one():
        payload = run_once(config, args)
        if args.json:
            print(json.dumps(payload, default=str))
        else:
            render(payload)
        append_backup(payload)
        source_label = args.scenario if args.scenario else args.source
        append_alerts(payload, source_label)
        if args.cloud:
            post_to_cloud(payload, args.cloud)
        return payload

    if not args.watch:
        payload = one()
        sys.exit(EXIT_BY_STATUS.get(payload["statuses"]["overall_status"], 3))

    print(f"Watching every {args.interval}s. Ctrl-C to stop.")
    while True:
        try:
            one()
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped.")
            break


if __name__ == "__main__":
    main()
