#!/usr/bin/env python3
"""
dyson_pull.py — Pull readings from a Dyson Pure Cool / Hot+Cool
and append a row to dyson_live.csv in Room Check's schema.

ONE-TIME SETUP
--------------
  pip install libdyson-neon
  python dyson_pull.py --login

The --login flow asks for your MyDyson email + password, sends you a
6-digit OTP by email, saves auth tokens locally in .dyson-auth.json
(no passwords stored in plaintext — only the cloud credential for
your device).

NORMAL USE
----------
  python dyson_pull.py                             # one row now
  python dyson_pull.py --watch --interval 30       # continuous

Then in a second terminal:
  python main.py --source csv --file sample_data/dyson_live.csv --watch --interval 30

NOTES
-----
 * Dyson Pure Cool / Hot+Cool does NOT measure CO2. co2_ppm is always blank.
 * Dyson's VOC comes back on a 0-9 "index" scale; we rescale it to Room Check's
   0-500 range by multiplying by 50 so the thresholds still apply.
 * Temperature is reported in Kelvin × 10 (e.g. 2950 = 295 K). We convert to °F.
 * Humidity and PM2.5 pass through directly.

If libdyson-neon's API has changed since this was written and login fails,
fall back to `python main.py --source manual` and type values off the
MyDyson app display. Demo still works.
"""
from __future__ import annotations
import argparse
import csv
import getpass
import json
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUTH = HERE / ".dyson-auth.json"
OUT_DEFAULT = HERE / "sample_data" / "dyson_live.csv"


def _require_libdyson():
    try:
        import libdyson  # noqa: F401
        from libdyson import get_device
    except ImportError as exc:
        sys.exit(f"libdyson base import failed: {exc}\n"
                 f"    pip install --upgrade libdyson-neon")

    # DysonAccount moved between versions; try the known locations.
    DysonAccount = None
    last_err = None
    for path in ("libdyson.cloud.account",
                 "libdyson.cloud",
                 "libdyson.dyson_account",
                 "libdyson"):
        try:
            mod = __import__(path, fromlist=["DysonAccount"])
            DysonAccount = getattr(mod, "DysonAccount", None)
            if DysonAccount:
                break
        except ImportError as exc:
            last_err = exc

    if DysonAccount is None:
        sys.exit(f"Could not find DysonAccount in libdyson. "
                 f"Last import error: {last_err}. "
                 f"Your installed libdyson version may have moved it — "
                 f"run: python -c \"import libdyson, pkgutil; "
                 f"print([m.name for m in pkgutil.walk_packages(libdyson.__path__, prefix='libdyson.')])\"")

    return DysonAccount, get_device

def _k10_to_f(k10) -> float | None:
    """Dyson returns temperature in several formats. Auto-detect by magnitude:
        > 1000  → Kelvin × 10  (legacy, e.g., 2950 = 295.0 K)
        > 100   → Kelvin       (e.g., 291.5 K)
        else    → Celsius      (e.g., 18.4 °C)
    Normal room temperature is 270-310 K, so the split points are unambiguous.
    """
    try:
        raw = float(k10)
    except (TypeError, ValueError):
        return None
    if raw > 1000:
        k = raw / 10.0
    elif raw > 100:
        k = raw
    else:
        k = raw + 273.15
    return round((k - 273.15) * 9 / 5 + 32, 2)


def _num(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ─────────────────────── auth ─────────────────────────────────────────
def cmd_login(args):
    DysonAccount, _ = _require_libdyson()

    email = input("MyDyson email: ").strip()
    password = getpass.getpass("MyDyson password: ")
    region = (input("Region [US]: ").strip() or "US").upper()

    account = DysonAccount()
    print("\nRequesting OTP — check your email inbox...")
    try:
        verify_fn = account.login_email_otp(email, region)
    except Exception as exc:
        sys.exit(f"Login request failed: {exc}")

    if not callable(verify_fn):
        sys.exit(f"Unexpected login_email_otp return: {verify_fn!r}")

    otp = input("Enter the 6-digit OTP: ").strip()
    try:
        verify_fn(otp, password)
    except Exception as exc:
        sys.exit(f"OTP verification failed: {exc}")

    try:
        devices = account.devices()
    except Exception as exc:
        sys.exit(f"Could not list devices: {exc}")

    if not devices:
        sys.exit("No Dyson devices found on this account.")

    print("\nDevices on your account:")
    for i, d in enumerate(devices):
        name = getattr(d, "name", "(unnamed)")
        serial = getattr(d, "serial", "?")
        ptype = getattr(d, "product_type", "?")
        print(f"  [{i}] {name}  serial={serial}  product_type={ptype}")

    idx_raw = input(f"Select device [0-{len(devices)-1}] (default 0): ").strip()
    idx = int(idx_raw) if idx_raw else 0
    chosen = devices[idx]

    payload = {
        "email": email,
        "region": region,
        "serial": getattr(chosen, "serial", None),
        "credential": getattr(chosen, "credential", None),
        "product_type": getattr(chosen, "product_type", None),
        "name": getattr(chosen, "name", None),
    }

    if not payload["credential"]:
        sys.exit("Could not extract device credential from the account response.")

    AUTH.write_text(json.dumps(payload, indent=2))
    AUTH.chmod(0o600)
    print(f"\nSaved {AUTH.name}. You can now run:\n    python dyson_pull.py")


# ─────────────────────── pull ─────────────────────────────────────────
def _discover_host(device, timeout=10):
    """Find the Dyson's IP on the local network via mDNS."""
    try:
        from libdyson.discovery import DysonDiscovery
    except ImportError:
        return None
    found = {}
    def _cb(address):
        if address and "host" not in found:
            found["host"] = address
    discovery = DysonDiscovery()
    discovery.start_discovery()
    try:
        discovery.register_device(device, _cb)
        start = time.time()
        while time.time() - start < timeout:
            if "host" in found:
                break
            time.sleep(0.2)
    finally:
        try: discovery.stop_discovery()
        except Exception: pass
    return found.get("host")


def _connect(device, host: str | None):
    """Connect to the Dyson on the local network. Auto-discovers via mDNS if host not given."""
    if not host:
        print("  Discovering Dyson on local network via mDNS...")
        host = _discover_host(device, timeout=10)
        if host:
            print(f"  Found device at {host}")
        else:
            raise RuntimeError(
                "Could not discover Dyson on the local network. "
                "Make sure your laptop is on the same WiFi as the Dyson. "
                "Alternatively, find the Dyson's IP in your router's admin page "
                "and pass it with --host. Example: python dyson_pull.py --host 192.168.1.42"
            )
    try:
        device.connect(host)
        return host
    except Exception as exc:
        raise RuntimeError(f"Could not connect to {host}: {exc}")


def _pluck_env(device) -> dict:
    """libdyson-neon has used a few different attribute names; try them all."""
    env = getattr(device, "environmental_data", None)
    if env:
        return env
    # Older versions
    out = {}
    for key, attrs in {
        "particulate_matter_2_5": ("particulate_matter_2_5", "pm2_5", "pm25"),
        "volatile_organic_compounds": ("volatile_organic_compounds", "voc", "va10"),
        "humidity": ("humidity", "hact"),
        "temperature": ("temperature", "tact"),
    }.items():
        for a in attrs:
            v = getattr(device, a, None)
            if v is not None:
                out[key] = v
                break
    return out


def cmd_pull(args):
    if not AUTH.exists():
        sys.exit("No auth file. Run: python dyson_pull.py --login")

    auth = json.loads(AUTH.read_text())
    _, get_device = _require_libdyson()

    device = get_device(auth["serial"], auth["credential"], auth["product_type"])
    _connect(device, args.host)

    env = _pluck_env(device)

    # Dyson's VOC scale is 0-9 (integer). The API may return fractional values
    # (e.g., 0.5) but the display floors to 0-9. Match the display so values
    # look consistent, t
if __name__ == "__main__":
    cmd_login(None)
