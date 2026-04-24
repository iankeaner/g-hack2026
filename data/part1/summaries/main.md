### Program: `core/main.py`

**Intent:**  
Main entry point for the “Room Check” system. It collects room air-quality readings, evaluates safety status, detects drift/problems, generates alerts and resilience scores, displays results, logs them locally, and optionally sends them to a cloud endpoint.

---

### Inputs
- **Command-line arguments**
  - `--source`: reading source (`manual`, `inkbird-manual`, `csv`, `inkbird`)
  - `--file`: CSV file path
  - `--fallback`: fallback source if primary fails
  - `--scenario`: canned scenario name
  - `--config`: path to JSON config
  - `--watch`: continuous polling mode
  - `--interval`: polling interval in seconds
  - `--cloud`: cloud URL for POST
  - `--json`: output raw JSON only
- **Configuration file**
  - `thresholds.json`
- **Sensor/input data**
  - manual entry, Inkbird device, CSV file, or built-in scenarios
- **Environment variable**
  - `ROOMCHECK_CLOUD_URL` (optional)

---

### Outputs
- **Console output**
  - pretty formatted room status report, or JSON payload
- **Exit code**
  - `0` = GREEN
  - `1` = YELLOW
  - `2` = RED
  - `3` = UNKNOWN
- **Local files**
  - `local_backup.csv`: backup log of readings/results
  - `alerts.csv`: alert-focused log with full alert text and drift summary
- **Optional network output**
  - HTTP POST of JSON payload to cloud URL

---

### Key functions

- **`load_config(path)`**  
  Reads JSON configuration.  
  **Input:** config file path  
  **Output:** config dictionary

- **`gather_readings(args)`**  
  Gets readings from selected source and applies validation/context.  
  **Input:** parsed CLI args  
  **Output:** cleaned readings dictionary

- **`load_scenario(name)`**  
  Returns predefined test scenario values.  
  **Input:** scenario name  
  **Output:** readings dictionary or `None`

- **`run_once(config, args)`**  
  Runs one full cycle: collect readings, evaluate room, detect drift, create alert/resilience payload.  
  **Input:** config dict, CLI args  
  **Output:** payload dictionary

- **`render(payload)`**  
  Prints a human-readable report.  
  **Input:** payload dict  
  **Output:** console display

- **`append_backup(payload)`**  
  Appends summary results to local CSV backup.  
  **Input:** payload dict  
  **Output:** writes to `local_backup.csv`

- **`append_alerts(payload, source)`**  
  Appends alert details to alert log.  
  **Input:** payload dict, source label  
  **Output:** writes to `alerts.csv`

- **`post_to_cloud(payload, url)`**  
  Sends payload to remote dashboard.  
  **Input:** payload dict, URL  
  **Output:** HTTP POST attempt

- **`main()`**  
  Parses arguments and runs once or continuously.  
  **Input:** CLI/environment  
  **Output:** orchestrates full program flow and exits with status code

---

If you want, I can also summarize the imported modules (`inputs`, `room_check`, `alerts`) based on how `main.py` uses them.