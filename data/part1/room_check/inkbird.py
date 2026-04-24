#!/usr/bin/env python3
"""
INKBIRD BLE CONNECTOR (bonus)
=============================

Talks to Inkbird air-quality monitors over Bluetooth Low Energy and returns
readings in the Room Check standard schema:

    {
      "co2_ppm": float,
      "pm25_ugm3": float,
      "temperature_f": float,
      "humidity_pct": float,
      "voc_index": float,
      "timestamp": "2026-04-24T13:30:00",
      "device": "IAM-T1:AA:BB:CC:DD:EE:FF",
    }

Supports:
  * IAM-T1  — CO2 + temp + humidity (Inkbird's indoor air-quality monitor)
  * ITH-11P / ITH-13B — temp + humidity (falls back, PM2.5/CO2/VOC left None)

Requirements:
    pip install bleak

Usage:
    from inkbird import read_once, stream, scan
    data = read_once()                     # first device found, one reading
    for data in stream(address, every=30): # continuous polling
        ...

NOTE ON PROTOCOL
----------------
Inkbird publishes sensor values inside the BLE manufacturer-specific
advertisement payload (company ID 0x0001 / 0x09C7 depending on firmware).
No bonding, no notify subscription required — you just listen for the
advertisement and parse 16 bytes of payload. This module implements the
community-reverse-engineered format as also used by the Home Assistant
inkbird_ble integration. If your device ships a newer firmware with a
different layout, set INKBIRD_DEBUG=1 to dump raw bytes.

If `bleak` is not installed or no adapter is present, the module falls
back to a *simulated* device so main.py still runs — this is useful for
demo laptops without Bluetooth. Set INKBIRD_SIMULATE=0 to disable.
"""

from __future__ import annotations

import asyncio
import os
import struct
import sys
import time
from datetime import datetime
from typing import Iterator, Optional

try:
    from bleak import BleakScanner  # type: ignore
    HAS_BLEAK = True
except Exception:
    HAS_BLEAK = False


INKBIRD_COMPANY_IDS = (0x0001, 0x09C7)
SCAN_SECONDS = 6
DEBUG = os.environ.get("INKBIRD_DEBUG") == "1"


# ─────────────────────── parsing ─────────────────────────────────────────
def _c_to_f(c: float) -> float:
    return c * 9 / 5 + 32


def _parse_iam_t1(data: bytes) -> Optional[dict]:
    """
    IAM-T1 advertisement payload layout (little-endian, 16 bytes).
    Bytes:
       0-1   int16  temperature * 100 (°C)
       2-3   uint16 humidity * 100 (%RH)
       4-5   uint16 CO2 (ppm)
       6-7   uint16 PM2.5 (µg/m³ * 10)
       8-9   uint16 VOC index
       10    uint8  battery percent
       11-15 reserved
    """
    if len(data) < 10:
        return None
    temp_c, hum, co2, pm25_x10, voc = struct.unpack_from("<hHHHH", data, 0)
    return {
        "co2_ppm": float(co2),
        "pm25_ugm3": pm25_x10 / 10.0,
        "temperature_f": round(_c_to_f(temp_c / 100.0), 2),
        "humidity_pct": hum / 100.0,
        "voc_index": float(voc),
    }


def _parse_ith(data: bytes) -> Optional[dict]:
    """Fallback parser for ITH-11P / ITH-13B (temp+humidity only)."""
    if len(data) < 4:
        return None
    temp_c, hum = struct.unpack_from("<hH", data, 0)
    return {
        "co2_ppm": None,
        "pm25_ugm3": None,
        "temperature_f": round(_c_to_f(temp_c / 100.0), 2),
        "humidity_pct": hum / 100.0,
        "voc_index": None,
    }


def _parse_manufacturer_data(name: str, payload: bytes) -> Optional[dict]:
    if name and "IAM" in name.upper():
        return _parse_iam_t1(payload)
    if name and "ITH" in name.upper():
        return _parse_ith(payload)
    # Last resort: try IAM parser; if numbers are obviously wrong, skip.
    parsed = _parse_iam_t1(payload)
    if parsed and 300 <= (parsed["co2_ppm"] or 0) <= 5000:
        return parsed
    return None


# ─────────────────────── BLE scanning ────────────────────────────────────
async def _scan_once(address: Optional[str] = None, timeout: float = SCAN_SECONDS) -> Optional[dict]:
    if not HAS_BLEAK:
        raise RuntimeError("bleak not installed — run `pip install bleak`")

    found: dict = {}

    def _cb(device, advertisement_data):
        if address and device.address.upper() != address.upper():
            return
        md = advertisement_data.manufacturer_data or {}
        for cid, payload in md.items():
            if cid not in INKBIRD_COMPANY_IDS and "Inkbird" not in (device.name or ""):
                continue
            if DEBUG:
                print(f"  [inkbird] {device.address} {device.name!r} cid=0x{cid:04x} data={payload.hex()}", file=sys.stderr)
            parsed = _parse_manufacturer_data(device.name or "", payload)
            if parsed:
                parsed["device"] = f"{device.name or 'Inkbird'}:{device.address}"
                found.update(parsed)

    scanner = BleakScanner(detection_callback=_cb)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()
    return found or None


async def _scan_all(timeout: float = SCAN_SECONDS) -> list:
    """Return every Inkbird device seen during the scan window."""
    if not HAS_BLEAK:
        raise RuntimeError("bleak not installed")
    devices: dict = {}

    def _cb(device, advertisement_data):
        md = advertisement_data.manufacturer_data or {}
        for cid in md:
            if cid in INKBIRD_COMPANY_IDS or "Inkbird" in (device.name or ""):
                devices[device.address] = device.name or "Inkbird"

    scanner = BleakScanner(detection_callback=_cb)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()
    return [{"address": a, "name": n} for a, n in devices.items()]


# ─────────────────────── simulation fallback ─────────────────────────────
def _simulated_reading() -> dict:
    """Deterministic-ish sim so demos don't require hardware."""
    now = time.time()
    drift = (now % 60) / 60.0
    return {
        "co2_ppm": round(600 + 200 * drift, 1),
        "pm25_ugm3": round(7 + 5 * drift, 2),
        "temperature_f": round(71 + 3 * drift, 2),
        "humidity_pct": round(42 + 8 * drift, 2),
        "voc_index": round(95 + 30 * drift, 1),
        "device": "SIMULATED:no-bluetooth",
    }


def _should_simulate() -> bool:
    if os.environ.get("INKBIRD_SIMULATE") == "0":
        return False
    if os.environ.get("INKBIRD_SIMULATE") == "1":
        return True
    return not HAS_BLEAK


# ─────────────────────── public API ──────────────────────────────────────
def scan(timeout: float = SCAN_SECONDS) -> list:
    """List Inkbird devices visible right now."""
    if _should_simulate():
        return [{"address": "SIMULATED", "name": "Inkbird (simulated)"}]
    return asyncio.run(_scan_all(timeout))


def read_once(address: Optional[str] = None, timeout: float = SCAN_SECONDS) -> Optional[dict]:
    """One reading from the first (or specified) Inkbird device.

    Returns None if no device is reachable — caller (main.py) decides
    whether to fall back to CSV or manual entry.
    """
    if _should_simulate():
        data = _simulated_reading()
        data["timestamp"] = datetime.now().isoformat(timespec="seconds")
        return data

    try:
        data = asyncio.run(_scan_once(address=address, timeout=timeout))
    except Exception as exc:
        if DEBUG:
            print(f"  [inkbird] error: {exc}", file=sys.stderr)
        return None
    if data is None:
        return None
    data["timestamp"] = datetime.now().isoformat(timespec="seconds")
    return data


def stream(address: Optional[str] = None, every: float = 30.0) -> Iterator[dict]:
    """Yield a fresh reading every `every` seconds."""
    while True:
        reading = read_once(address=address)
        if reading is not None:
            yield reading
        time.sleep(every)


if __name__ == "__main__":
    import argparse, json
    p = argparse.ArgumentParser()
    p.add_argument("--scan", action="store_true")
    p.add_argument("--address", default=None)
    args = p.parse_args()
    if args.scan:
        print(json.dumps(scan(), indent=2))
    else:
        print(json.dumps(read_once(args.address), indent=2))
