**Program:** `core/room_check.py`

**Intent:**  
Evaluates room/environment sensor readings against threshold rules to determine per-metric and overall room status, and detects operational drift conditions that suggest systems are not behaving as expected.

## Inputs

### `evaluate_room(readings, thresholds)`
- **`readings`**: `dict` of measured values, such as:
  - `co2_ppm`
  - `pm25_ugm3`
  - `temperature_f`
  - `humidity_pct`
  - `voc_index`
- **`thresholds`**: `dict` of threshold specs for each metric.
  - For ceiling-based metrics: expects keys like `green_max`, `yellow_max`
  - For range-based metrics: expects keys like `green_min`, `green_max`, `yellow_min`, `yellow_max`

### `check_drift(readings, drift_rules, dt=None)`
- **`readings`**: `dict` of current values, including:
  - `building_status`
  - `co2_ppm`
  - `temperature_f`
- **`drift_rules`**: `dict` of drift detection rules, including:
  - `BAS-1_weekend_co2`
  - `BAS-2_setback`
- **`dt`**: optional `datetime` used for time-based checks; defaults to current time

## Outputs

### `evaluate_room(...) -> dict`
Returns a dictionary with status for each parameter and the worst overall status:
- `<metric>_status`: `"GREEN"`, `"YELLOW"`, `"RED"`, or `"UNKNOWN"`
- `overall_status`: worst status among all metrics

Example output:
```python
{
  "co2_ppm_status": "GREEN",
  "pm25_ugm3_status": "GREEN",
  "temperature_f_status": "YELLOW",
  "humidity_pct_status": "GREEN",
  "voc_index_status": "GREEN",
  "overall_status": "YELLOW",
}
```

### `check_drift(...) -> list`
Returns a list of drift findings. Each finding is a `dict` containing:
- `rule`
- `fix_id`
- `description`
- `observed`
- `expected_max`
- `daily_waste_usd`

Example output:
```python
[
  {
    "rule": "BAS-1_weekend_co2",
    "fix_id": "BAS-1",
    "description": "...",
    "observed": 530,
    "expected_max": 450,
    "daily_waste_usd": 37.26,
  }
]
```

## Main behaviors
- Uses **ceiling checks** for CO2, PM2.5, and VOC
- Uses **range checks** for temperature and humidity
- Missing values or missing thresholds produce `"UNKNOWN"`
- Overall room status is the **worst** individual status
- Drift detection flags:
  - high CO2 when building is marked `"closed"`
  - high after-hours temperature during nighttime setback window