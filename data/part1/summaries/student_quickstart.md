**Program intent:**  
Interactive “quickstart” launcher for students to run the Room Check system without remembering CLI flags. It asks what sensor/source they have, whether to run once or continuously, and then invokes `main.py` (and sometimes `dyson_pull.py`) with the right arguments.

**Inputs:**  
- User keyboard input via prompts:
  - Sensor choice:
    - Inkbird manual entry
    - Dyson
    - No sensor / canned scenario
    - Simulator
    - Quit
  - Run mode: once or watch
  - Watch interval (seconds)
  - Scenario selection
  - Whether to start another run
  - For Dyson watch mode, whether to start terminal 2 now
- File existence check:
  - `.dyson-auth.json` to verify Dyson login is already set up
- Environment variable set internally for simulator:
  - `INKBIRD_SIMULATE=1`

**Outputs:**  
- Printed menu, instructions, status messages, and error/help text to the console
- Launches subprocesses:
  - `main.py` with appropriate flags
  - `dyson_pull.py` for Dyson one-time pull / login guidance
- Indirectly causes Room Check to append results to `alerts.csv` through `main.py`
- Exit status code from subprocess calls is returned internally by `_run`

**Main behaviors by option:**  
- **Inkbird:** runs `main.py --source inkbird-manual` (optionally watch mode)
- **Dyson:** checks auth, optionally runs `dyson_pull.py`, then runs `main.py` against `sample_data/dyson_live.csv`
- **Scenario:** runs `main.py --scenario <scenario_id>`
- **Simulator:** sets simulation env var and runs `main.py --source inkbird` (optionally watch mode)