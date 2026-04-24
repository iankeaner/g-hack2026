# GridHack 2026 — Student User Guide

**Welcome to Room Check.** You're building an open-source air-quality safety tool for Montgomery County Library — a real 104,634 sq ft building with 436 daily visitors, no backup generator, and 1994-era HVAC. What you ship today could actually get deployed.

This guide walks you through the environment, how to submit, how scoring works, and what to do when things go sideways.

---

## 1. The day at a glance

| Time | What |
|---|---|
| 12:30 | Doors + lunch. Sign in. Find your team table. |
| 1:00  | Welcome from Michelle — the building, the challenge, EcoGuard. Ask questions now. |
| 1:15  | **Phase 1 (audit challenge):** 4 timed challenges — BEPS score, audit comparison, retrofit roadmap, grant narrative. |
| 2:30  | Phase 1 presentations, 3 min per team. |
| 2:55  | **Phase 2 (build Room Check):** 60 minutes. Each team writes one file. |
| 4:00  | **Integration (15 min):** plug all 5 files together. Run it end-to-end. |
| 4:15  | Demo Room Check against the library's real data. |
| 4:45  | Awards. Grand Prize = fellowship slots in Cohort 1, July 2026. |

## 2. The test environment (web app)

Open the Replit URL on your laptop. You'll see a dark-green sidebar with seven pages.

| Page | What it's for |
|---|---|
| **Mission Hub** (`/`) | The story. Start here. |
| **Simulator** (`/room-check`) | Drag sliders for CO2 / PM2.5 / temp / humidity / VOC. Get GREEN/YELLOW/RED instantly. Use this to sanity-check your logic before you commit code. |
| **Teams** (`/teams`) | Your team's page is here. Click your team card to open your workspace. |
| **Leaderboard** (`/leaderboard`) | Live standings. Your score updates automatically every time you submit. |
| **Submit Ideas** (`/submit`) | Non-technical teammates can submit ideas, scenarios, edge cases, and user stories — with an "AI Writing Helper" (Gemini / Claude / GPT) to polish rough thoughts. |
| **Dictionary** (`/dictionary`) | 32 terms. Search, filter, cross-reference. Any word underlined with dots has a definition — hover it. |
| **Field Guide** (`/guide`) | The full event playbook. |

### Accessibility

Bottom-right floating widget: high contrast, large text, font-size +/−, focus highlight, link underline, reduced motion. Settings persist — toggle once and they stick.

## 3. Your team's job (Phase 2)

Each team owns **one file**. All five files import each other through `main.py`, so yours has to match the contract below or integration at 4pm breaks.

| Team | File | Role | Max Pts |
|---|---|---|---|
| 1 | `inputs.py` | The Translator — read/validate/contextualize sensor data | 30 |
| 2 | `thresholds.json` | The Rule Book — safety standards + BEPS math | 30 |
| 3 | `room_check.py` | The Detective — GREEN/YELLOW/RED + drift detection | 30 |
| 4 | `alerts.py` | The First Responder — plain alerts + Resilience Index | 30 |
| 5 | `README.md` | The Messenger — docs + local backup system | 30 |

Open your team page (`/teams/<your-number>`) — it has:
- **Mission** — what this file must do
- **Step-by-step guide** — checkable boxes with hints and bonus challenges (your progress is saved locally)
- **Starter code** — copy from here; any dotted-underline term has a definition tooltip; **highlight any code text to look it up in the dictionary**
- **Submit** — paste your finished code, click Submit

## 4. How scoring works (and why retrying is free)

Every submission runs against a **dynamic auto-grader**. No waiting for a judge.

- Each test in the rubric is worth between 5 and 10 points (see your team page).
- After you submit, you see immediately: pass/fail per test + the reason failing tests failed.
- Your team's score on the leaderboard is the **best** grade you've achieved. Resubmitting a worse attempt never lowers your score.
- Some tests are partial credit (e.g., correct GREEN/RED decision = 5 pts even if drift detection is still broken = 10 more pts).

**Tip:** submit *early and often*. The first submission is usually worth 5–10 pts just from the easy tests. Use that as a foothold.

### Auto-prompt-on-low-score

If a submission scores **below 30%** of the max, the system automatically files a prompt in `/submit` describing which tests failed and inviting your non-technical teammates to help define the next target. Check `/submit` when you're stuck — there may be a hint waiting for you from five minutes ago.

## 5. Connecting an Inkbird IAM-T1 monitor (bonus)

If your team has an Inkbird plugged into the demo laptop:

```bash
# From the Replit shell
python room_check/inkbird.py --scan        # confirms the device is visible
python room_check/main.py --source inkbird --watch --interval 30
```

Without an Inkbird in range, the driver falls back to a deterministic simulator — your code will still run.

Want live data in the web UI? Hit `GET /api/roomcheck/live` — it returns the freshest Inkbird reading in the standard schema. The Simulator page can be extended with a "Pull from Inkbird" button if you add one.

## 6. Running the integrated script yourself

Anytime during Phase 2 or integration, open the shell and test end-to-end:

```bash
# Canned scenarios (no hardware needed)
python room_check/main.py --scenario normal
python room_check/main.py --scenario smoke_event
python room_check/main.py --scenario combined_emergency

# Real CSV of sensor readings
python room_check/main.py --source csv --file room_check/sample_data/sensor_log.csv

# Prompt me at the terminal for readings
python room_check/main.py --source manual

# Run every 30s, ship results to the EcoGuard dashboard
python room_check/main.py --source inkbird --watch --interval 30 \
    --cloud https://YOUR-REPL.repl.co/api/roomcheck/ingest
```

**Exit codes** — useful for CI or dashboards:
- `0` = GREEN
- `1` = YELLOW
- `2` = RED
- `3` = UNKNOWN (sensors missing)

Every run appends one row to `room_check/local_backup.csv`. That file is the "WiFi-down insurance" — if the building loses power, a laptop on battery + USB Inkbird keeps logging until power is back.

## 7. Non-technical teammates — you are not optional

Coders will get stuck on what to *build*. You already know the answer because you understand people.

Open `/submit` and contribute:

- **Feature Idea** — "The alert should also list the nearest cooling center."
- **Real-World Scenario** — "What if the fire alarm is going off and CO2 is also elevated?"
- **Edge Case** — "What if the sensor is unplugged for 30 minutes?"
- **User Story** — "As a librarian, I need to know if the building is safe to open without checking 5 screens."
- **Question** — "Does CO2 climb faster in the kids' section than the reading room?"
- **Design Idea** — "The alert should say what to DO, not just what's wrong."

The **AI Writing Helper** (Gemini / Claude / GPT toggle) turns a rough thought into something your coders can pick up and implement in 10 minutes. Use it.

## 8. Common problems

### "My submission got a 0."
Open the submission detail — the failing tests will include a one-line reason. Common ones:
- `valid_json` for Team 2 → you broke the JSON (missing comma, trailing comma). Paste into a JSON validator.
- `cannot import` → a syntax error in your file. The trace is in the `log` field.

### "The simulator says my numbers are RED but my code says GREEN."
Your thresholds file or decision engine disagrees with the server's canonical thresholds. Open `/dictionary` and look up the sensor — it links to the real standard.

### "I can't find my Inkbird."
- On Replit, the BLE adapter usually isn't available — you'll see the simulated device. That's fine for submissions.
- On a local laptop, make sure bluetooth is on, then `python room_check/inkbird.py --scan`.
- Set `INKBIRD_DEBUG=1` to dump raw BLE payloads.

### "My team's leaderboard score went down."
It didn't — leaderboard shows the best score your team has achieved. Check the Submissions page; there may be a newer submission with more points that hasn't loaded.

### "The AI Helper is rate-limited."
10 requests per minute per IP. Switch providers (Gemini ↔ Claude ↔ GPT) or wait 60 seconds.

## 9. What makes a winning team

From last year's judges:

1. **You chose a real librarian scenario and stuck with it.** Vague specs lose.
2. **Your alert told the user what to DO, not just what's wrong.** "Unsafe" is not useful. "Close windows, move elderly occupants to the reading room, call building ops" is.
3. **You cited a real source.** "ASHRAE 62.1 says..." beats "we think 1000 ppm is bad."
4. **You accounted for one thing that could fail.** Power outage. WiFi outage. Sensor offline. Smoke. Extreme heat. Pick one; plan for it.
5. **You finished.** A complete weaker solution beats a flawless 40% solution every time.

## 10. When in doubt

- Ask Michelle or any mentor.
- Check the **Field Guide** (`/guide`) — it has the same content as this document, but hyperlinked.
- Re-read your **team page's starter code** — the TODO comments literally tell you what to build.
- Talk to your **non-technical teammates**. They are closer to the library user than you are.

Now go ship it.
