**Program intent:**  
`core/inkbird.py` reads air-quality/environment data from Inkbird BLE devices, parses their Bluetooth advertisement payloads, and returns normalized sensor readings. If BLE is unavailable, it can simulate readings.

## Inputs
- **BLE advertisements** from nearby Inkbird devices
- Optional function/CLI inputs:
  - `address`: specific BLE MAC address to target
  - `timeout`: scan duration
  - `every`: polling interval for streaming
  - CLI flags:
    - `--scan`
    - `--address`
- Optional environment variables:
  - `INKBIRD_DEBUG`
  - `INKBIRD_SIMULATE`

## Outputs
- **`scan()`** → list of visible Inkbird devices  
  Example:
  ```python
  [{"address": "AA:BB:CC:DD:EE:FF", "name": "IAM-T1"}]
  ```

- **`read_once()`** → one standardized reading dictionary, or `None` if no device found  
  Example:
  ```python
  {
    "co2_ppm": 800.0,
    "pm25_ugm3": 12.3,
    "temperature_f": 72.5,
    "humidity_pct": 45.2,
    "voc_index": 110.0,
    "timestamp": "2026-04-24T13:30:00",
    "device": "IAM-T1:AA:BB:CC:DD:EE:FF"
  }
  ```

- **`stream()`** → iterator yielding repeated reading dictionaries over time

- **CLI output**
  - `python core/inkbird.py --scan` → JSON list of devices
  - `python core/inkbird.py --address <addr>` → JSON reading for that device

## Device support
- **IAM-T1**: CO2, PM2.5, temperature, humidity, VOC
- **ITH-11P / ITH-13B**: temperature and humidity only (`co2_ppm`, `pm25_ugm3`, `voc_index` become `None`)