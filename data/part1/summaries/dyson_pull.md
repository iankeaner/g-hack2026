**Program:** `core/dyson_pull.py`

**Intent:**  
Logs air-quality readings from a Dyson Pure Cool / Hot+Cool device and appends them to a CSV file in the Room Check schema. It also supports a one-time login flow to save Dyson device credentials locally.

## Inputs
### Login mode (`--login`)
- MyDyson email
- MyDyson password
- Region (default `US`)
- 6-digit OTP sent by email
- Device selection if multiple Dyson devices exist

### Pull mode
- Saved auth file: `.dyson-auth.json`
- Optional Dyson host/IP via `--host`
- Live sensor data from the Dyson device:
  - PM2.5
  - VOC
  - Humidity
  - Temperature

## Outputs
### Login mode
- Creates `.dyson-auth.json` containing:
  - email
  - region
  - serial
  - credential
  - product_type
  - device name

### Pull mode
- Connects to the Dyson over the local network
- Converts/formats readings for Room Check:
  - VOC scaled from Dyson’s 0–9 index to Room Check’s range
  - Temperature converted to °F
  - CO2 left blank
- Appends a row to `sample_data/dyson_live.csv` (or configured output file)

## Main functions
- `_require_libdyson()` — loads required Dyson library components
- `_k10_to_f()` — converts Dyson temperature formats to Fahrenheit
- `_num()` — safely parses numbers
- `cmd_login()` — performs cloud login and saves auth info
- `_discover_host()` — finds device IP via mDNS
- `_connect()` — connects to the Dyson on the local network
- `_pluck_env()` — extracts environmental readings across library versions
- `cmd_pull()` — reads current values and writes them to CSV
