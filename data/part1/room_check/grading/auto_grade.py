#!/usr/bin/env python3
"""
DYNAMIC AUTO-GRADER
===================

Drops a student's submission into a sandbox directory, imports it,
runs a suite of test cases, and returns:

    {
      "team_id": 3,
      "filename": "room_check.py",
      "score": 24,
      "max_score": 30,
      "passed": ["evaluate_room_green", "evaluate_room_red", ...],
      "failed": [{"test": "check_drift_bas1", "reason": "..."}],
      "log": "...",
    }

Usage:
    python auto_grade.py --team 3 --file path/to/room_check.py
    # or programmatically:
    from auto_grade import grade_submission
    result = grade_submission(team_id=3, code=source_string,
                              filename="room_check.py")

Integration with the API:
    The Express /api/submissions POST handler invokes this script with
    --json so the TypeScript side can parse the result and call
    UPDATE teams SET score = score + <new_points>.

No external deps. Uses only the stdlib.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import sys
import tempfile
import traceback
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Callable, Optional


# ───────────────────────── sandboxing ─────────────────────────────────
def _load_module(source_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, source_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load spec for {source_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_test(fn: Callable, label: str, passed: list, failed: list, log: io.StringIO):
    try:
        with redirect_stdout(log), redirect_stderr(log):
            fn()
        passed.append(label)
    except AssertionError as exc:
        failed.append({"test": label, "reason": str(exc) or "assertion failed"})
    except Exception as exc:
        tb = traceback.format_exc(limit=3)
        failed.append({"test": label, "reason": f"{type(exc).__name__}: {exc}", "trace": tb})


# ───────────────────────── team graders ───────────────────────────────
def _grade_team1(mod) -> list:
    """Team 1 (inputs.py) — 30 pts total."""
    tests = []

    def test_validate_replaces_bad_values():
        out = mod.validate_readings({
            "co2_ppm": -50, "pm25_ugm3": 9999, "temperature_f": 72,
            "humidity_pct": 45, "voc_index": 100,
        })
        assert out["co2_ppm"] is None, "negative CO2 should be None"
        assert out["pm25_ugm3"] is None, "out-of-range PM2.5 should be None"
        assert out["temperature_f"] == 72
    tests.append(("validate_replaces_bad_values", test_validate_replaces_bad_values, 10))

    def test_csv_reads_last_row():
        tmp = Path(tempfile.mkstemp(suffix=".csv")[1])
        tmp.write_text(
            "timestamp,co2_ppm,pm25_ugm3,temperature_f,humidity_pct,voc_index\n"
            "2026-04-24T10:00:00,500,5.0,70,40,80\n"
            "2026-04-24T10:05:00,1234,12.3,74.5,48,150\n",
            encoding="utf-8",
        )
        try:
            out = mod.read_from_csv(str(tmp))
            assert out is not None, "read_from_csv returned None"
            assert abs(out["co2_ppm"] - 1234) < 0.1, "should read the LAST row"
            assert abs(out["temperature_f"] - 74.5) < 0.1
        finally:
            tmp.unlink(missing_ok=True)
    tests.append(("csv_reads_last_row", test_csv_reads_last_row, 10))

    def test_context_flags_after_hours_co2():
        from datetime import datetime
        # Sunday 2am — library closed.
        dt = datetime(2026, 4, 26, 2, 0)
        out = mod.add_context({"co2_ppm": 620, "pm25_ugm3": 5, "temperature_f": 70,
                               "humidity_pct": 40, "voc_index": 80}, dt=dt)
        assert out.get("building_status") == "closed", "Sunday 2am should be closed"
        assert out.get("after_hours_flag"), "elevated CO2 while closed should set after_hours_flag"
    tests.append(("context_flags_after_hours_co2", test_context_flags_after_hours_co2, 10))

    return tests


def _grade_team2(cfg: dict) -> list:
    """Team 2 (thresholds.json) — 30 pts total."""
    tests = []

    def test_co2_limits_match_ashrae():
        spec = cfg["air_quality_thresholds"]["co2_ppm"]
        assert 700 <= spec["green_max"] <= 1000, "CO2 green_max should be 700-1000 (ASHRAE 62.1)"
        assert 1000 <= spec["yellow_max"] <= 1500, "CO2 yellow_max should be 1000-1500"
        assert spec.get("source"), "must cite a source"
    tests.append(("co2_limits_match_ashrae", test_co2_limits_match_ashrae, 5))

    def test_pm25_limits_match_epa():
        spec = cfg["air_quality_thresholds"]["pm25_ugm3"]
        assert abs(spec["green_max"] - 12) < 0.5, "PM2.5 green_max should be 12 (EPA AQI)"
        assert abs(spec["yellow_max"] - 35.4) < 0.5, "PM2.5 yellow_max should be 35.4 (EPA AQI)"
    tests.append(("pm25_limits_match_epa", test_pm25_limits_match_epa, 5))

    def test_temp_and_humidity_sane():
        t = cfg["air_quality_thresholds"]["temperature_f"]
        h = cfg["air_quality_thresholds"]["humidity_pct"]
        assert 60 <= t["green_min"] <= 70 and 75 <= t["green_max"] <= 82
        assert 25 <= h["green_min"] <= 35 and 55 <= h["green_max"] <= 65
    tests.append(("temp_and_humidity_sane", test_temp_and_humidity_sane, 5))

    def test_beps_math_correct():
        ep = cfg["beps_compliance"]["energy_performance"]
        gap = ep["latest_eui"] - ep["target_eui"]
        assert abs(gap - ep["gap"]) < 0.1, f"gap should equal latest-target (= {gap})"
        penalty = cfg["beps_compliance"]["penalty"]
        assert penalty["fine_per_year"] == 500 * 365, "fine_per_year = $500 * 365"
    tests.append(("beps_math_correct", test_beps_math_correct, 10))

    def test_phase1_combined_savings():
        p = cfg["beps_compliance"]["phase1_fixes"]
        expected = p["BAS-1"]["annual_savings"] + p["BAS-2"]["annual_savings"] + p["MECH-1"]["annual_savings"]
        assert abs(p["combined_savings"] - expected) < 1, "combined_savings must equal sum of three ECMs"
    tests.append(("phase1_combined_savings", test_phase1_combined_savings, 5))

    return tests


def _grade_team3(mod, cfg) -> list:
    """Team 3 (room_check.py) — 30 pts total."""
    thresholds = cfg["air_quality_thresholds"]
    drift_rules = cfg["drift_rules"]
    tests = []

    def test_green_when_all_good():
        r = {"co2_ppm": 500, "pm25_ugm3": 5, "temperature_f": 72,
             "humidity_pct": 45, "voc_index": 80}
        out = mod.evaluate_room(r, thresholds)
        assert out["overall_status"] == "GREEN"
    tests.append(("green_when_all_good", test_green_when_all_good, 5))

    def test_red_on_smoke():
        r = {"co2_ppm": 500, "pm25_ugm3": 89, "temperature_f": 72,
             "humidity_pct": 45, "voc_index": 80}
        out = mod.evaluate_room(r, thresholds)
        assert out["overall_status"] == "RED"
        assert out["pm25_ugm3_status"] == "RED"
    tests.append(("red_on_smoke", test_red_on_smoke, 5))

    def test_worst_status_wins():
        r = {"co2_ppm": 900, "pm25_ugm3": 5, "temperature_f": 95,
             "humidity_pct": 45, "voc_index": 80}
        out = mod.evaluate_room(r, thresholds)
        assert out["overall_status"] == "RED", "one RED parameter should drive overall RED"
    tests.append(("worst_status_wins", test_worst_status_wins, 5))

    def test_unknown_on_missing():
        r = {"co2_ppm": None, "pm25_ugm3": 5, "temperature_f": 72,
             "humidity_pct": 45, "voc_index": 80}
        out = mod.evaluate_room(r, thresholds)
        assert out["co2_ppm_status"] == "UNKNOWN"
        # Missing CO2 alone shouldn't make overall RED.
        assert out["overall_status"] in ("GREEN", "UNKNOWN", "YELLOW")
    tests.append(("unknown_on_missing", test_unknown_on_missing, 5))

    def test_drift_catches_bas1():
        r = {"co2_ppm": 530, "building_status": "closed"}
        findings = mod.check_drift(r, drift_rules)
        assert any(f["fix_id"] == "BAS-1" for f in findings), "BAS-1 drift should fire"
        assert any(abs(f["daily_waste_usd"] - 37.26) < 0.01 for f in findings)
    tests.append(("drift_catches_bas1", test_drift_catches_bas1, 10))

    return tests


def _grade_team4(mod, cfg) -> list:
    """Team 4 (alerts.py) — 30 pts total."""
    vulns = cfg["resilience_vulnerabilities"]
    tests = []

    def test_green_alert_is_calm():
        msg = mod.get_alert_message("GREEN", {"co2_ppm": 500}, {"overall_status": "GREEN"})
        assert "safe" in msg.lower() or "good" in msg.lower()
    tests.append(("green_alert_is_calm", test_green_alert_is_calm, 5))

    def test_smoke_alert_says_no_windows():
        msg = mod.get_alert_message("RED",
            {"co2_ppm": 500, "pm25_ugm3": 89, "temperature_f": 73},
            {"pm25_ugm3_status": "RED"})
        assert "not open" in msg.lower() or "do not open" in msg.lower() or "keep doors closed" in msg.lower()
        assert "window" in msg.lower()
    tests.append(("smoke_alert_says_no_windows", test_smoke_alert_says_no_windows, 10))

    def test_heat_alert_calls_out_vulnerable():
        msg = mod.get_alert_message("RED",
            {"co2_ppm": 500, "pm25_ugm3": 5, "temperature_f": 95},
            {"temperature_f_status": "RED"})
        assert "elder" in msg.lower() or "vulnerable" in msg.lower() or "children" in msg.lower()
    tests.append(("heat_alert_calls_out_vulnerable", test_heat_alert_calls_out_vulnerable, 5))

    def test_resilience_deducts_for_vulnerabilities():
        statuses = {"co2_ppm_status":"GREEN","pm25_ugm3_status":"GREEN",
                    "temperature_f_status":"GREEN","humidity_pct_status":"GREEN",
                    "voc_index_status":"GREEN","overall_status":"GREEN"}
        r = mod.get_resilience_index(statuses, {"co2_ppm": 500}, vulns)
        assert 0 <= r["score"] <= 100
        assert r["score"] < 100, "known vulnerabilities should reduce score below 100"
        assert r["band"] in ("RESILIENT", "FRAGILE", "AT RISK", "CRITICAL")
    tests.append(("resilience_deducts_for_vulnerabilities", test_resilience_deducts_for_vulnerabilities, 10))

    return tests


def _grade_team5(doc: str) -> list:
    """Team 5 (README.md) — 30 pts total. Lightweight content checks."""
    tests = []
    text = doc.lower() if doc else ""

    def test_mentions_all_teams():
        for t in ("team 1", "team 2", "team 3", "team 4", "team 5"):
            assert t in text, f"README should mention {t}"
    tests.append(("mentions_all_teams", test_mentions_all_teams, 5))

    def test_explains_data_flow():
        assert ("data flow" in text or "dataflow" in text or "architecture" in text), \
            "README should include a data-flow / architecture section"
    tests.append(("explains_data_flow", test_explains_data_flow, 5))

    def test_mentions_local_backup():
        assert "csv" in text and ("backup" in text or "offline" in text), \
            "README must describe the local CSV backup (works during outages)"
    tests.append(("mentions_local_backup", test_mentions_local_backup, 10))

    def test_explains_library_context():
        assert ("library" in text and "montgomery" in text), \
            "README should ground the project in the real building (Montgomery County Library)"
    tests.append(("explains_library_context", test_explains_library_context, 5))

    def test_includes_install_instructions():
        assert ("install" in text or "getting started" in text or "pip install" in text or "run" in text), \
            "README should have install / run instructions"
    tests.append(("includes_install_instructions", test_includes_install_instructions, 5))

    return tests


# ───────────────────────── top-level ──────────────────────────────────
def _load_config(config_path: Optional[Path]) -> dict:
    path = config_path or (Path(__file__).resolve().parent.parent / "thresholds.json")
    with open(path) as f:
        return json.load(f)


def grade_submission(team_id: int, code: Optional[str] = None,
                     filename: Optional[str] = None,
                     file_path: Optional[str] = None,
                     config_path: Optional[str] = None) -> dict:
    """Grade a submission. Returns the result dict."""
    cfg = _load_config(Path(config_path) if config_path else None)

    # Materialize code to a file if given inline.
    tmp_dir = Path(tempfile.mkdtemp(prefix="grade_"))
    if file_path and not code:
        src = Path(file_path).read_text()
    elif code:
        src = code
    else:
        raise ValueError("Provide either code or file_path")

    passed, failed = [], []
    log = io.StringIO()
    max_score = 0
    earned = 0

    try:
        if team_id == 1:
            target = tmp_dir / "inputs.py"
            target.write_text(src)
            mod = _load_module(target, f"student_inputs_{id(target)}")
            tests = _grade_team1(mod)

        elif team_id == 2:
            try:
                cfg_student = json.loads(src)
            except json.JSONDecodeError as exc:
                return {"team_id": 2, "filename": filename or "thresholds.json",
                        "score": 0, "max_score": 30, "passed": [],
                        "failed": [{"test": "valid_json", "reason": str(exc)}], "log": ""}
            tests = _grade_team2(cfg_student)
            mod = None  # no module to run

        elif team_id == 3:
            target = tmp_dir / "room_check.py"
            target.write_text(src)
            mod = _load_module(target, f"student_roomcheck_{id(target)}")
            tests = _grade_team3(mod, cfg)

        elif team_id == 4:
            target = tmp_dir / "alerts.py"
            target.write_text(src)
            mod = _load_module(target, f"student_alerts_{id(target)}")
            tests = _grade_team4(mod, cfg)

        elif team_id == 5:
            tests = _grade_team5(src)

        else:
            raise ValueError(f"Unknown team_id: {team_id}")

        for label, fn, weight in tests:
            max_score += weight
            before_fails = len(failed)
            _run_test(fn, label, passed, failed, log)
            if len(failed) == before_fails:
                earned += weight

    except Exception as exc:
        tb = traceback.format_exc(limit=5)
        failed.append({"test": "load", "reason": f"{type(exc).__name__}: {exc}", "trace": tb})
        max_score = max_score or 30

    return {
        "team_id": team_id,
        "filename": filename,
        "score": earned,
        "max_score": max_score,
        "passed": passed,
        "failed": failed,
        "log": log.getvalue(),
    }


def main():
    p = argparse.ArgumentParser(description="Dynamic Room Check auto-grader.")
    p.add_argument("--team", type=int, required=True, choices=[1,2,3,4,5])
    p.add_argument("--file", required=True, help="Path to the submitted file.")
    p.add_argument("--config", default=None, help="Path to thresholds.json (for teams 3/4).")
    p.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = p.parse_args()

    result = grade_submission(team_id=args.team, file_path=args.file, config_path=args.config,
                              filename=Path(args.file).name)

    if args.json:
        print(json.dumps(result, default=str))
        sys.exit(0 if result["score"] == result["max_score"] else 1)

    print(f"Team {result['team_id']}  {result['filename']}")
    print(f"  Score: {result['score']} / {result['max_score']}")
    print(f"  Passed ({len(result['passed'])}): {', '.join(result['passed']) or '—'}")
    if result["failed"]:
        print(f"  Failed ({len(result['failed'])}):")
        for f in result["failed"]:
            print(f"    - {f['test']}: {f['reason']}")
    sys.exit(0 if result["score"] == result["max_score"] else 1)


if __name__ == "__main__":
    main()
