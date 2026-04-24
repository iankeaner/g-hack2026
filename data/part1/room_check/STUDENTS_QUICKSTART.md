# GridHack 2026 — Student Quickstart

Everything you need to run Room Check tomorrow on your own laptop, whether you brought an **Inkbird IAM-O2** or a **Dyson Pure Cool / Hot+Cool**, or neither.

If you forget anything, there's **one command** that walks you through it all:

```
python student_quickstart.py
```

---

## 1. Laptop setup (10 minutes, do this once)

### Install Python
1. Go to https://www.python.org/downloads/
2. Download **Python 3.11 or newer** for your OS.
3. **Windows users — check the box "Add python.exe to PATH"** during install. This is the #1 mistake people make.
4. Close and reopen your terminal/PowerShell.
5. Test: `python --version` should print a version number.

### Get the project
1. Download the project zip (your instructor will share a link).
2. Unzip to a folder you'll remember, e.g. `Documents/Orivia/room_check`.
3. Open a terminal and navigate into it:
   - **Windows:** `cd $env:USERPROFILE\Documents\Orivia\room_check`
   - **macOS / Linux:** `cd ~/Documents/Orivia/room_check`

### Install dependencies (only if you have a Dyson)
Skip this section if you have an Inkbird or no sensor.

```
pip install libdyson-neon
python dyson_pull.py --login
```

The `--login` flow walks you through MyDyson email → password → OTP from email → pick your device. It stores a `.dyson-auth.json` file so you don't need to log in again. **Make sure your laptop is on the same WiFi as your Dyson.**

---

## 2. Running Room Check

The easiest path — one command, menu-driven:

```
python student_quickstart.py
```

You'll see:

```
Which sensor are you using?
  [1] Inkbird IAM-O2        — I'll read values off the screen
  [2] Dyson Pure Cool/Hot+Cool — live cloud pull
  [3] No sensor              — play a canned scenario
  [4] Simulator              — deterministic fake data
```

Pick the one that matches your setup. That's it — Room Check runs and appends to `alerts.csv`.

---

## 3. The five output files

After each run, three files get updated in your project folder:

| File | What's in it | Why |
|---|---|---|
| Terminal output | GREEN/YELLOW/RED panel + alert + resilience | Watch this live during the demo. |
| `alerts.csv` | **Full** alert text + drift summary + resilience band, per run | Audit trail judges can review. Open in Excel. |
| `local_backup.csv` | All sensor values + status, per run | WiFi-down-proof data log for Team 5. |
| `dyson_live.csv` | Latest Dyson reading (Dyson only) | Bridge between `dyson_pull.py` and `main.py`. |
| `sample_data/sensor_log.csv` | Pre-canned CSV readings | For CSV-mode testing. |

Open `alerts.csv` in Excel when your demo is done. Every urgent situation you triggered will be there with a full-text explanation of what a librarian should do.

---

## 4. Inkbird IAM-O2 workflow (manual)

Your Inkbird's BLE pairing doesn't work reliably — we tried. The good news: every other part of Room Check works fine with manual entry.

```
python student_quickstart.py
# pick [1]
```

You'll be asked for three values that appear on the Inkbird display:

- **CO₂** — largest number, in ppm
- **Temperature** — type the number; if the Inkbird shows °C you can type e.g. `22c` and it auto-converts to °F
- **Humidity** — the % next to the water-drop icon

The Inkbird doesn't measure PM2.5 or VOCs, so those two will show as UNKNOWN. That's accurate — Room Check tells a librarian exactly what's measured and what isn't.

### Run continuously
When asked "Run once or continuously?" pick **w** (watch). You'll be re-prompted every 30 seconds. Useful during judging — walk the monitor around the room and re-enter numbers to show alerts flip in real time.

---

## 5. Dyson Pure Cool / Hot+Cool workflow (live)

One-time setup (see section 1 above):

```
pip install libdyson-neon
python dyson_pull.py --login
```

Then run it through the quickstart:

```
python student_quickstart.py
# pick [2]
```

The script will:
1. Pull a fresh reading from your Dyson (via Dyson's cloud, discovered on LAN).
2. Write it to `sample_data/dyson_live.csv`.
3. Run Room Check on that CSV.

For **continuous live data during your demo**, open two terminal windows:

```
# Terminal 1 — pulls fresh readings every 30s
python dyson_pull.py --watch --interval 30
```

```
# Terminal 2 — re-runs Room Check every 30s
python main.py --source csv --file sample_data/dyson_live.csv --watch --interval 30
```

### Dyson caveats to know
- Dyson Pure Cool does **not** measure CO₂. It'll show UNKNOWN for CO₂.
- PM2.5, temperature, humidity, and VOC all come through.
- VOC on the Dyson display is 0–9 (whole numbers). Room Check multiplies by 50 to map onto the international Sensirion 0–500 scale the thresholds use. Dyson 0 → 0, Dyson 3 → 150 (still green), Dyson 8+ → 400+ (red).

---

## 6. No sensor? Use a scenario.

```
python student_quickstart.py
# pick [3]
```

Nine pre-built scenarios, each based on a real risk for Montgomery County Library:

- Normal day — baseline
- Stuffy meeting room — elevated CO₂
- Ventilation failure
- Heat wave — with the building's aging R-22 chillers
- Wildfire smoke — tests the "do NOT open windows" alert
- Power outage — no backup generator
- Combined emergency — worst-case, resilience drops to 0
- Weekend AHU drift — the $37/day BAS-1 waste the auditor flagged

These are great demo beats. Pick 2–3, run them back-to-back, and show the judges how the same tool produces three completely different librarian actions.

---

## 7. Running in Replit instead of a laptop

If you didn't bring a laptop, use the Replit project:

1. Open the Replit URL your instructor shared. Sign in.
2. Click **Run** — the web UI starts.
3. In the Replit **Shell** tab, run:
   ```
   cd room_check
   python student_quickstart.py
   ```
4. Pick [1] Inkbird manual or [3] Scenario. (Dyson cloud works too but requires extra Replit secret config.)

BLE doesn't work in Replit (no hardware), so Inkbird is manual-only there — same as on a laptop.

---

## 8. Demo scripting — what to say

A crisp 3-minute demo that wins judges:

**Beat 1 (30 sec).** "This is Room Check. One librarian, one room, one question: is it safe for occupants right now?"
Run: `python student_quickstart.py` → pick Inkbird or Dyson → show the GREEN panel.

**Beat 2 (45 sec).** "Now imagine there's wildfire smoke outside."
Run: pick [3] scenario → `smoke_event`. Point at the RED banner and read the alert verbatim: *"Do NOT open windows — this may be a smoke event."*

**Beat 3 (45 sec).** "This is the library's actual vulnerability profile — no backup generator, R-22 chillers, 1994 AHUs. Watch what happens in the worst case."
Run: pick [3] scenario → `combined_emergency`. Point at resilience score crashing to 0/100.

**Beat 4 (30 sec).** "Every alert is logged. A manager can review what happened, when, and what was decided."
Open `alerts.csv` in Excel. Point at the `alert_full` column.

**Beat 5 (30 sec).** "Five teams built this. One file each. They plug into one runnable script. No gatekeeper — anyone can read the thresholds, anyone can improve the logic."
Close deck.

---

## 9. Troubleshooting cheatsheet

**`pip` is not recognized** → Python wasn't added to PATH. Reinstall Python with the checkbox on.

**`python` is not recognized** → Same as above. Close and reopen terminal after install.

**Dyson `--login` fails at OTP** → The code expired (10-minute window). Retype and go faster, or request a new one.

**`libdyson-neon` installed but import fails** → `pip` and `python` might point at different Pythons. Force-install: `python -m pip install --upgrade libdyson-neon`.

**Dyson discovery says "Could not discover"** → Laptop and Dyson must be on the same WiFi. 5GHz vs 2.4GHz split networks sometimes block this. Switch to the same band.

**Temperature shows `-407.1`** → Old version of `dyson_pull.py` — grab the latest from the project zip. This was fixed.

**`alerts.csv` won't open in Excel** → Open Excel first → Data → From Text/CSV → pick the file. Double-click sometimes opens it in a weird way.

**Anything else** → Fall back to `python main.py --source manual` and type numbers. It always works. Your demo doesn't depend on the transport layer.

Good luck tomorrow. Ship something a librarian could actually use.
