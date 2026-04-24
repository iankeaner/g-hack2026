**Program intent:**  
`core/inputs.py` is the input/translation layer for room sensor data. It collects readings from manual entry, CSV, or an Inkbird device, normalizes them into a standard schema, removes impossible values, and adds building time/context metadata.

## Inputs
Depending on function:

- **`read_manual()`**
  - User-entered values from console:
    - `co2_ppm`
    - `pm25_ugm3`
    - `temperature_f`
    - `humidity_pct`
    - `voc_index`

- **`read_from_csv(filepath)`**
  - `filepath: str`
  - CSV file with columns:
    - `timestamp`
    - `co2_ppm`
    - `pm25_ugm3`
    - `temperature_f`
    - `humidity_pct`
    - `voc_index`

- **`read_from_inkbird()`**
  - No direct input
  - Reads from external `inkbird.py` / BLE device

- **`validate_readings(readings)`**
  - `readings: dict` in the standard sensor schema

- **`add_context(readings, dt=None)`**
  - `readings: dict`
  - optional `dt: datetime`
  - uses built-in weekly library schedule

## Outputs
Main schema returned/used:

```python
{
  "co2_ppm": float | None,
  "pm25_ugm3": float | None,
  "temperature_f": float | None,
  "humidity_pct": float | None,
  "voc_index": float | None,
}
```

Additional outputs by function:

- **`read_manual()`**
  - Returns readings dict in standard schema

- **`read_from_csv(filepath)`**
  - Returns readings dict from the **last CSV row**
  - May also include:
    - `timestamp`
  - Returns `None` if file missing or empty

- **`read_from_inkbird()`**
  - Returns device reading dict
  - Returns `None` if driver/device unavailable

- **`validate_readings(readings)`**
  - Returns cleaned dict where out-of-range or invalid values are replaced with `None`

- **`add_context(readings, dt=None)`**
  - Returns readings dict plus:
    - `building_status`: `"open" | "offices_only" | "closed"`
    - `timestamp`: existing or generated ISO timestamp
    - `after_hours_flag`: `str | None`

## Key behavior
- Rejects physically impossible sensor values using fixed valid ranges
- Fills missing/invalid values with `None`
- Determines if building is open, offices-only, or closed based on schedule
- Flags high CO2 when the building should be empty