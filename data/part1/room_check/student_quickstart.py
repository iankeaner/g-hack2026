#!/usr/bin/env python3
"""
Student Quickstart for Room Check
=================================

One script that walks a student through running Room Check with whatever
hardware they brought to GridHack. No command-line flags to remember.

    python student_quickstart.py

You'll be asked:
  1. Which sensor you have (Inkbird / Dyson / none)
  2. Whether to run once or continuously
And then Room Check runs and appends to alerts.csv.

If you need flags later:  python main.py --help
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"


BANNER = """
============================================================
 ROOM CHECK — Student Quickstart
 GridHack 2026 · Open-source air-quality tool for MoCo Library
============================================================
"""

MENU = """
Which sensor are you using?

  [1] Inkbird IAM-O2        — I'll read values off the screen (recommended)
  [2] Dyson Pure Cool/Hot+Cool — live cloud pull (requires --login done once)
  [3] No sensor              — play a canned scenario (smoke event, heat wave...)
  [4] Simulator              — deterministic fake data for UI demos
  [q] Quit

"""

SCENARIOS = [
    ("normal",              "Normal library day"),
    ("stuffy_room",         "Stuffy meeting room (elevated CO2)"),
    ("ventilation_failure", "Ventilation failure"),
    ("heat_wave",           "Heat wave, no backup generator"),
    ("smoke_event",         "Wildfire smoke event"),
    ("power_outage",        "Power outage"),
    ("combined_emergency",  "Combined emergency (worst case)"),
    ("bas1_drift",          "Weekend AHU drift ($37/day waste)"),
    ("library_baseline",    "Library baseline (pre-audit)"),
]


def _ask(prompt: str, allowed: tuple, default: str | None = None) -> str:
    while True:
        raw = input(prompt).strip().lower()
        if not raw and default:
            return default
        if raw in allowed:
            return raw
        print(f"  Please enter one of: {', '.join(allowed)}")


def _ask_watch() -> bool:
    ans = _ask("Run once or continuously? [o]nce / [w]atch [o]: ", ("o", "w"), "o")
    return ans == "w"


def _ask_interval() -> int:
    raw = input("How many seconds between checks? [30]: ").strip()
    try:
        return max(5, int(raw)) if raw else 30
    except ValueError:
        return 30


def _run(cmd: list[str]) -> int:
    """Run main.py with the given args, streaming output."""
    print(f"\n  → python {' '.join(cmd)}\n")
    return subprocess.call([sys.executable, str(MAIN)] + cmd)


def _pick_scenario() -> str | None:
    print("\nPick a scenario:")
    for i, (sid, label) in enumerate(SCENARIOS, 1):
        print(f"  [{i}] {label}")
    print("  [b] back")
    while True:
        raw = input("Select: ").strip().lower()
        if raw == "b":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(SCENARIOS):
            return SCENARIOS[int(raw) - 1][0]


def route_inkbird():
    """Inkbird IAM-O2 — manual entry. Watch mode re-prompts each interval."""
    if _ask_watch():
        interval = _ask_interval()
        print(f"  (Room Check will re-prompt you every {interval}s. Ctrl-C to stop.)")
        _run(["--source", "inkbird-manual", "--watch", "--interval", str(interval)])
    else:
        _run(["--source", "inkbird-manual"])


def route_dyson():
    """Dyson — check auth file, offer to run --login, then pull via CSV bridge."""
    auth = HERE / ".dyson-auth.json"
    if not auth.exists():
        print("\n  ! No Dyson auth yet. Run this first (one-time):")
        print("      python dyson_pull.py --login")
        print("  Then come back here.")
        return

    live_csv = HERE / "sample_data" / "dyson_live.csv"

    if _ask_watch():
        interval = _ask_interval()
        print("\n  Two terminals needed:")
        print(f"    1) python dyson_pull.py --watch --interval {interval}")
        print(f"    2) python main.py --source csv --file sample_data/dyson_live.csv --watch --interval {interval}")
        print("\n  Start terminal 1 now, then run terminal 2. Ctrl-C to stop both.")
        ans = _ask("Start terminal 2 (main.py reader) now? [y/n] [y]: ", ("y","n"), "y")
        if ans == "y":
            _run(["--source", "csv", "--file", str(live_csv), "--watch", "--interval", str(interval)])
    else:
        print("\n  Pulling one Dyson reading...\n")
        rc = subprocess.call([sys.executable, str(HERE / "dyson_pull.py")])
        if rc != 0:
            print("  (dyson_pull.py failed — you can still fall back to Inkbird or a scenario.)")
            return
        _run(["--source", "csv", "--file", str(live_csv)])


def route_scenario():
    sid = _pick_scenario()
    if sid is None:
        return
    _run(["--scenario", sid])


def route_simulator():
    import os
    os.environ["INKBIRD_SIMULATE"] = "1"
    if _ask_watch():
        interval = _ask_interval()
        _run(["--source", "inkbird", "--watch", "--interval", str(interval)])
    else:
        _run(["--source", "inkbird"])


def main():
    print(BANNER)
    while True:
        print(MENU)
        choice = _ask("Select [1-4] or q: ", ("1","2","3","4","q"))
        if choice == "q":
            print("Goodbye.")
            return
        if choice == "1": route_inkbird()
        elif choice == "2": route_dyson()
        elif choice == "3": route_scenario()
        elif choice == "4": route_simulator()

        print()
        again = _ask("Do another run? [y/n] [y]: ", ("y","n"), "y")
        if again == "n":
            return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
