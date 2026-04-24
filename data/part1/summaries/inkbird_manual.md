**Program intent:**  
Provides a **guided manual data-entry flow** for an Inkbird IAM-O2 air-quality monitor when BLE sync is unreliable. It asks the user to type values shown on the device and returns them in the app’s **standard readings schema** so the rest of the pipeline can use them like any other data source.

**Inputs:**  
Interactive keyboard input from the user:
- `co2_ppm` (CO2 in ppm)
- `temperature_f` (temperature in °F; also accepts values entered in °C like `22c` and converts to °F)
- `humidity_pct` (relative humidity %)

Possible skipped input:
- Blank entry twice returns `None` for that field

**Outputs:**  
A Python `dict` with this structure:
- `co2_ppm`: `float | None`
- `pm25_ugm3`: `None`
- `temperature_f`: `float | None`
- `humidity_pct`: `float | None`
- `voc_index`: `None`

Example output:
```python
{
    "co2_ppm": 650.0,
    "pm25_ugm3": None,
    "temperature_f": 72.0,
    "humidity_pct": 45.0,
    "voc_index": None,
}
```

**Main public function:**  
- `read_inkbird_guided() -> dict`

**Helper function:**  
- `_prompt_float(field: dict) -> Optional[float]`  
  Prompts for one value, validates numeric input, supports °C-to-°F conversion for temperature, or returns `None` if skipped.