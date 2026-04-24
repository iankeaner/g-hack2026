**Program intent: `core/alerts.py`**

Generates:
1. **Human-readable safety alerts** for building staff/librarians based on sensor conditions.
2. A **Community Resilience Index** (0–100) showing how prepared or vulnerable the building is, combining current conditions with known building weaknesses.

---

## Inputs and outputs

### `get_alert_message(overall_status, readings, statuses) -> str`
**Purpose:**  
Creates a plain-language alert message describing current room safety and recommended action.

**Inputs:**
- `overall_status` (`str`): overall safety level, such as `"GREEN"`, `"YELLOW"`, `"RED"`, or `"UNKNOWN"`.
- `readings` (`dict`): sensor values, including possible keys:
  - `"pm25_ugm3"`: particulate/smoke level
  - `"temperature_f"`: temperature in Fahrenheit
  - `"co2_ppm"`: carbon dioxide level
- `statuses` (`dict`): per-sensor status values like `"RED"` or `"YELLOW"` (for example, `temperature_status`, `pm25_status`).

**Output:**
- `str`: a message telling staff what conditions mean and what action to take.

---

### `get_resilience_index(statuses, readings, vulnerabilities) -> dict`
**Purpose:**  
Calculates a resilience score starting from 100 and subtracting points for vulnerabilities, bad sensor conditions, and after-hours issues.

**Inputs:**
- `statuses` (`dict`): sensor status values such as `"RED"` or `"YELLOW"`.
- `readings` (`dict`): current readings; may include `"after_hours_flag"`.
- `vulnerabilities` (`dict`): known building weaknesses, where each item may include:
  - `"points_deducted"`
  - `"note"`

**Output:**
- `dict` containing:
  - `"score"` (`float`): resilience score from 0 to 100
  - `"band"` (`str`): category such as `"RESILIENT"`, `"FRAGILE"`, `"AT RISK"`, or `"CRITICAL"`
  - `"breakdown"` (`list`): list of deductions and reasons

---

## Helper functions

### `_red_params(statuses) -> list`
**Purpose:**  
Returns the names of parameters marked `"RED"`.

**Input:** `statuses` (`dict`)  
**Output:** `list` of parameter names

### `_yellow_params(statuses) -> list`
**Purpose:**  
Returns the names of parameters marked `"YELLOW"`.

**Input:** `statuses` (`dict`)  
**Output:** `list` of parameter names

---

## Overall summary
This file turns sensor and vulnerability data into:
- **actionable safety messages**, and
- a **numerical resilience assessment** for the building.
