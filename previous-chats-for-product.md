# TerminalRide — Agent Pack (All‑in‑One, Shareable to IDE Agents)

> Purpose: Give Claude Code / GPT‑5 Thinking / Copilot everything needed to build a terminal‑first indoor cycling app (Zwift‑lite) **without** reading a long chat history.

---

## 0) TL;DR for Agents

* **Goal:** Minimal, stable TUI app that connects to a Wahoo KICKR via **BLE FTMS**, displays live metrics, supports **Free / ERG / SIM** modes, and saves sessions to CSV/JSONL.
* **Done when (MVP):**

  * Connects and shows **Power/Cadence/Speed/HR**; ERG target changes react on trainer in \~2 s.
  * SIM mode changes resistance by grade and computes virtual speed/dist.
  * Sessions saved locally; CSV export; Stats view.
* **Constraints:** Python 3.11; deps = `bleak`, `rich` (or `textual`), `numpy`, `pydantic`, `pytest`; no new deps without approval.
* **Guardrails:** Tests first; deterministic (temperature 0.1); no invented UUIDs/opcodes; JSONL logs; docstrings w/ units.

---

## 1) North Star & Success Metrics

* **North Star:** Active training minutes per user per week.
* Activation: first ride started in **< 60 s** from app start.
* ERG responsiveness: **< 2 s** to setpoint change.
* Stability: disconnects auto‑recover; **no data loss** for outages **< 10 s**.

---

## 2) Repository Map (proposed)

```
terminalride/
  docs/
    MRD.md  PRD.md  TECH_SPEC.md  SETUP.md  ADR-0001.md
  terminalride/
    __init__.py
    app.py                  # main state machine + router
    config.py               # load/save settings (pydantic)
    logging.py              # JSONL logger
    ui/
      views.py              # Connect, Home, Live, Stats, Settings
      widgets.py            # common terminal components
    devices/
      base.py               # protocols for TrainerDevice/HrDevice
      ftms_client.py        # bleak BLE wrapper (scan/connect/notify/write)
      ftms_parse.py         # pure parser for Indoor Bike Data frames
    modes/
      free.py
      erg.py                # PI controller (no BLE here)
      sim.py                # grade scheduler + power→speed physics
    store/
      models.py             # pydantic models
      repo.py               # JSONL/SQLite persistence
      export.py             # CSV export; FIT later
    analytics/
      metrics.py            # avg, NP/IF/TSS
  tests/
    test_ftms_parse.py  test_erg.py  test_sim_physics.py  test_store.py
  .github/workflows/ci.yml
  .pre-commit-config.yaml
  pyproject.toml (or requirements*.txt)
  README.md  CHANGELOG.md  CONTRIBUTING.md
  .vscode/settings.json  .vscode/extensions.json  PULL_REQUEST_TEMPLATE.md
```

---

## 3) Setup Guide (short)

```bash
# Python env
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install bleak rich numpy pydantic pytest mypy ruff black

# Pre-commit
pip install pre-commit && pre-commit install

# Run tests
pytest -q
```

* **CI:** GitHub Actions runs ruff → black --check → mypy → pytest.
* **VS Code:** enable Black, Mypy, Ruff; format on save; recommend Copilot optional.

---

## 4) MRD (1‑pager)

**Problem:** Power‑focused riders want a fast, offline, terminal‑first trainer app without 3D frills.
**Users:** Triathletes/engineers; Mac‑first; Linux/Windows possible.
**JTBD:** Start ride < 60 s; hold ERG targets; log clean data.
**Competitors:** Zwift, TrainerRoad, Rouvy, Wahoo SYSTM.
**Differentiator:** protocol‑true, test‑first, open TUI with robust logs.
**Outcomes:** activation < 60 s; ERG response < 2 s; session drop‑rate < 0.5 %.

---

## 5) PRD (MVP)

**Devices:** Wahoo KICKR/KICKR Core (BLE FTMS); optional BLE HR.
**Modes:** Free Ride; **ERG** (constant target, +/-); **SIM** (grade‑based).
**Live View:** time, power (actual/target), cadence, speed (real/virt), distance, HR, mode; help overlay `?`.
**Data:** session persist (JSONL/SQLite), **CSV export**.
**Settings:** units, mass, FTP, CdA, Crr, keybindings.
**Out of Scope:** 3D, multiplayer, cloud sync, ANT+ (later), FIT/TCX (later).
**NFRs:** startup < 3 s; UI 10 Hz; input < 100 ms; reconnect < 10 s outage; CPU < 20 % on M‑series Mac.

**User Flows**

```
Start → Connect (scan/select) → Home
  ├ Start Training → {Free | ERG | SIM}
  ├ Devices
  ├ Stats
  └ Settings
Live → pause/resume → End → Save → Home
```

**Keybindings:** `1` Free, `2` ERG, `3` SIM, `+/-` target W, `space` pause, `l` lap, `s` save, `q` quit, `?` help.

---

## 6) TECH SPEC (v0.1)

**Language:** Python 3.11
**Deps:** `bleak`, `rich` or `textual`, `numpy`, `pydantic`, `pytest`
**Design:** TUI views + pure logic modules (parser, controller, physics) + BLE I/O wrapper

### 6.1 Interfaces (contracts)

```python
# devices/base.py
from typing import Protocol, Callable, Optional, TypedDict

class BikeSample(TypedDict):
    ts: float
    power_w: Optional[int]
    cadence_rpm: Optional[int]
    speed_mps: Optional[float]

class TrainerDevice(Protocol):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def subscribe(self, cb: Callable[[BikeSample], None]) -> None: ...
    async def request_control(self) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def set_target_power(self, watts: int) -> None: ...
    async def set_simulation(self, grade_pct: float) -> None: ...
```

### 6.2 FTMS over BLE (essentials)

* **Service:** `0x1826` (FTMS).
* **Notify:** Indoor Bike Data → live Power/Cadence/Speed via bit‑flagged fields, little‑endian.
* **Write:** Fitness Machine Control Point → request control, start/stop, set target power, set simulation params.
* **Status:** Fitness Machine Status (optional notify).
* **Rule:** **Do not guess** opcodes/field scales; leave `TODO(FTMS: confirm)` markers in code + tests.

### 6.3 SIM Physics (quasi‑steady)

Power balance (no accel term):
$P = 0.5\,\rho\,C_dA\,v^3 + m g C_r v + m g \sin(\theta) v + P_0$
Numerically solve for **v** (m/s) with Newton/fixed‑point; clamp to \[0, 20] m/s.
Defaults: $\rho=1.2\,\mathrm{kg/m^3}, C_dA=0.33, C_r=0.0045, P_0\approx5\,\mathrm{W}$.
Settings: mass (rider+bike), CdA, Crr editable.

### 6.4 ERG PI Controller

* Inputs: `current_hr`, `target_hr`, `current_power`.
* Output: `new_target_power`.
* Bounds: \[100, 400] W; rate limit: ±10 W per 5 s; anti‑windup (clamp integrator).
* Sampling: 1 Hz.

---

## 7) Data Model & Event Taxonomy

**Session**

```
{ id, start_ts, end_ts, mode, device:{model,fw}, user:{ftp,mass,cda,crr,units} }
```

**Sample row (CSV)**

```
ts_iso,power_w,cadence_rpm,speed_mps,hr_bpm,mode,erg_target_w,grade_pct
```

**JSONL Events**

```
session_started {session_id, mode, device_model, fw, ftp, mass}
device_connected {device_id, type:'trainer'|'hr', transport:'BLE', rssi}
mode_changed {from,to}
erg_target_set {watts, source:'key'}
sample {ts, power_w, cadence_rpm, speed_mps, hr_bpm, grade_pct, erg_target_w}
session_saved {session_id, duration_s, avg_power_w, np_w, tss}
error {code, message, context}
```

---

## 8) Test Plan (TDD first)

**Unit**

* `test_ftms_parse.py` — three hex fixtures: (all fields), (missing speed), (invalid length).
* `test_erg.py` — bounds respected; rate limit; step response within spec.
* `test_sim_physics.py` — 250 W @ 0 % grade, m=100 kg, CdA=0.33, Crr=0.0045 → v in \[9.0, 11.5] m/s.
* `test_store.py` — save/load + CSV header schema.

**Integration (mock BLE)**

* Subscribe → stream 100 samples → UI doesn’t crash.
* ERG setpoint change → single command send; no spam.

**Manual (hardware)**

* KICKR connect; ERG response < 2 s; disconnect mid‑ride recovers without data loss.

---

## 9) CI, Tooling & Policies

**CI (`.github/workflows/ci.yml`)** runs: `ruff` → `black --check` → `mypy --strict` → `pytest -q`.
**Pre‑commit:** trailing whitespace, end‑of‑file, black, isort/ruff, mypy.
**Commits:** Conventional Commits; PR template required; Tests must pass.
**Versioning:** SemVer; tag `v0.1.0` for MVP.

---

## 10) Prioritization & Roadmap

**RICE (MVP)**: 1) stable BLE + Free Ride; 2) ERG (+/−); 3) SIM + physics; 4) Persist+CSV; 5) Stats view.
**Weeks**

* **W1:** Repo+CI+TUI skeleton; tests for parser/erg/physics.
* **W2:** BLE subscribe + ERG write; keybindings; tests green.
* **W3:** SIM grade + power→speed; distance/HM; persistence+CSV.
* **W4:** Hardening (disconnects, perf), packaging, release `0.1.0`.

---

## 11) Agent Operating Procedure (AOP)

**Global Constraints**

* Temperature **0.1**; no new deps; tests first; no invented FTMS details; add `TODO(FTMS: …)` where gaps.
* Public APIs require docstrings with **Args/Returns/Raises**; all numbers have **units**.
* Logs are **JSONL**, one event per line.

**Prompts Library**

1. **Create tests only**

```
Create unit tests only for TerminalRide:
- tests/test_ftms_parse.py (FTMS frames → fields, hex fixtures)
- tests/test_erg.py (PI: bounds [100,400] W, rate limit ±10 W/5 s)
- tests/test_sim_physics.py (250 W flat → v in [9.0, 11.5] m/s)
No BLE I/O. Use pytest. Output only test files.
```

2. **Implement FTMS parser**

```
Implement devices/ftms_parse.py: parse_indoor_bike_data(frame: bytes) -> ParsedBikeData.
Little-endian flags; optional fields; NamedTuple(power_w|None, cadence_rpm|None, speed_mps|None, flags:int).
Raise ValueError on invalid length. Add docstring with units and example hex. Make tests pass.
```

3. **ERG controller**

```
Implement modes/erg.py PI controller with saturation and rate limit ±10 W/5 s, bounds [100,400] W, 1 Hz.
Add unit tests in tests/test_erg.py (step response, anti-windup). No BLE calls.
```

4. **SIM physics**

```
Implement modes/sim.py with grade scheduler and power→speed solver (Newton/fixed-point), clamp [0,20] m/s.
Parameters from config (mass, CdA, Crr, rho). Tests must pass.
```

5. **TUI skeleton**

```
Build Rich/Textual TUI with views: Connect, Home, Live, Stats, Settings; AppState; keybindings 1/2/3, +/- , space, l, s, q, ?.
No hardware yet; display placeholder data.
```

6. **BLE client**

```
Implement devices/ftms_client.py with bleak: scan/connect/subscribe Indoor Bike Data; request control; start; set target power; set simulation grade.
Reconnect with exponential backoff (1,2,4,8 s; max 30 s). Use ftms_parse.parse_indoor_bike_data for decoding.
```

7. **Persistence & Export**

```
Implement store/repo.py (JSONL sessions+samples) and store/export.py (CSV with fixed header).
Add analytics/metrics.py (avg, NP, IF, TSS). Add Stats view using repo.
```

8. **Stability & Release**

```
Add tests for disconnect/reconnect; ensure UI 10 Hz; package via pyinstaller/pipx; write CHANGELOG.md and tag v0.1.0.
```

---

## 12) Guardrails & Security

* **Do‑Not‑Hallucinate:** If FTMS doc missing → add `TODO(FTMS: confirm field scaling/opcode)` and an `xfail` test.
* **No PII in logs.** Do not log BLE pairing secrets.
* **Error Codes:** prefix with `FTMS_E_*`, `BLE_E_*`, `SIM_E_*` for greppable logs.

---

## 13) ADR Example

```
ADR-0001: Choose BLE FTMS via bleak
Date: 2025‑09‑01
Context: Mac-first; avoid ANT+ dongles.
Decision: Implement BLE FTMS first; abstract with TrainerDevice.
Consequences: Faster MVP; later add ANT+ FE-C behind same interface.
```

---

## 14) Open Questions / TODOs

* Confirm FTMS Control Point opcodes & scaling for: request control, start/stop, set target power, set simulation parameters.
* Decide JSONL vs SQLite as primary store (start JSONL, migrate later).
* Tuning PI gains for HR‑adaptive mode (avoid oscillation).
* Minimum terminal size & condensed layout definition.

---

## 15) Mini Smoke App (optional dopamine)

```python
# main.py — fake live table for quick win
import time, math, random
from rich.live import Live
from rich.table import Table

def snapshot(t, base=200):
    power = base + 25*math.sin(t/3.0) + random.uniform(-5,5)
    cadence = 85 + 5*math.sin(t/2.0)
    speed = 9.8 + 0.6*math.sin(t/4.0)
    return max(0,int(power)), int(cadence), speed

def render(mode, t, power, cadence, speed):
    tbl = Table(title=f"TerminalRide — Mode: {mode}")
    tbl.add_column("Metric"); tbl.add_column("Value")
    tbl.add_row("Time", f"{t:5.1f} s")
    tbl.add_row("Power", f"{power:4d} W")
    tbl.add_row("Cadence", f"{cadence:3d} rpm")
    tbl.add_row("Speed", f"{speed*3.6:4.1f} km/h")
    tbl.add_row("Keys", "q=Quit, 1=Free, 2=ERG, 3=SIM")
    return tbl

def main():
    mode = "free"; t0 = time.time()
    with Live(refresh_per_second=10) as live:
        while True:
            t = time.time() - t0
            p,c,s = snapshot(t)
            live.update(render(mode, t, p, c, s))
            time.sleep(0.1)

if __name__ == "__main__":
    main()
```

---

## 16) Release Checklist (MVP v0.1.0)

* CI green; unit + mock‑integration tests pass.
* KICKR ERG reacts to `+/-` in \~2 s (manual check).
* SIM shows plausible speed/dist/HM.
* End‑of‑ride → CSV + JSONL saved; Stats lists sessions.
* Reconnect works; no crash on mid‑ride disconnect < 10 s.
* PyInstaller bundle launches; README Quick Start updated; CHANGELOG tagged.

---

## 17) Context & Origin (for Agents)

**Why this exists:** Fynn cancelled Zwift and wants a **minimal, terminal‑first** alternative that controls a **Wahoo KICKR/KICKR Core** via BLE FTMS, shows core metrics, and supports Free/ERG/SIM — **no 3D world**, **no cloud**, fast startup, reliable logs. 95% of code will be written by AI agents; hence strong guardrails (tests first, protocol‑true, deterministic settings).

**Initial conversations covered:**

* Desired **user flow** like Zwift but simplified: **Connect → Home → Start Training (Free/ERG/SIM) → Live → End/Save → Stats**; ability to manage devices anytime; simple keyboard navigation in a TUI.
* **Live view** essentials: time, power (actual/target), cadence, (virtual) speed, distance, HR; laps; pause/resume; finish → save; then review in stats.
* The need for **professional artifacts** (MRD/PRD, IA, Service Blueprint idea, Tech Spec, ADRs, Test Plan, CI) so agents don’t drift.
* Decision to build **protocol‑true FTMS** support with **parser as pure logic**, **BLE I/O isolated**, **ERG PI controller** with rate‑limit & saturation, and **SIM physics** with configurable parameters (mass, CdA, Crr).
* Fynn’s stack/environment: **Mac‑first**, Wahoo trainer (\~€500–600 KICKR/Core), offline‑first preference, triathlon training; simple **terminal ergonomics** over UI flash.

**Overwhelm management:** we created a **mini dopamine app** (fake live table) and a **minimal three‑test TDD start** (FTMS parse, ERG PI, SIM physics) so progress is visible quickly before tackling BLE.

**Comparison & merge with Claude’s plan:**

* **Our docs**: stronger on FTMS/PI/physics, data/events, NFRs, CI, prioritization (RICE), recovery.
* **Claude’s**: stronger on setup ergonomics (Poetry, VS Code, Git workflow, packaging) and PRD tables.
* **Merged approach**: keep our *technical spine*, adopt Claude’s *developer ergonomics*. This doc already reflects that (see v0.2 notes).

---

## 18) What This App Is (and Isn’t)

**Is:**

* A **terminal‑first indoor cycling controller & logger**. Connects to FTMS trainer; runs **Free**, **ERG**, **SIM**; shows core metrics; logs to JSONL/CSV; fast and reliable.
* **Protocol‑true**, **test‑first**, **offline‑first**, designed for **extendability** (ANT+/FIT later behind stable interfaces).

**Is not (MVP):**

* 3D rendering, multiplayer, social features.
* Cloud sync, coaching library, web dashboards (may come later).

**Why terminal:** speed, low overhead, predictability under load, reproducibility, focus on training signal, robust logging for later analysis (NP/IF/TSS).

---

## 19) Prior Topics in One Glance (condensed)

* **User Flow & Navigation:** Connect device list; show connection success; Home hub; start/stop sessions; device management; Stats & Settings; help overlay `?` and consistent keybindings.
* **Modes:** Free (no control), ERG (target watts with `+/-`), SIM (grade schedule; resistance changes; virtual speed/dist/HM). Optional adaptive PI based on HR zones later.
* **Data & Exports:** Fixed CSV schema; JSONL event logs; later FIT/TCX roadmap; Stats view sourcing from local store.
* **Recovery:** Auto‑reconnect with exponential backoff; no data loss for short outages; clear error codes (`FTMS_E_*`, `BLE_E_*`, `SIM_E_*`).
* **Testing & CI:** Tests first, BLE mocked, parser/PI/physics pure; CI runs ruff/black/mypy/pytest; coverage focus on protocol/controls.
* **Agent Ops:** Deterministic generation (temperature 0.1); don’t invent opcodes/UUIDs; insert `TODO(FTMS: confirm ...)` and `xfail` where spec gaps exist; respect folder edit guards.

---

## 20) Assumptions & Personas (why decisions make sense)

* **Primary user:** performance‑oriented cyclist/triathlete who values **structured training** and **data fidelity** over visuals.
* **Hardware:** Wahoo KICKR/KICKR Core via **BLE FTMS** (Mac‑first works well); optional BLE HR strap.
* **Environment:** Offline‑first; single local user; terminal width ≥100 cols preferred (condensed layout below that).
* **Training philosophy:** ERG for intervals; SIM to simulate terrain load; metrics: AVG, NP, IF, TSS.

---

## 21) How to Use This Document (for Agents)

1. Read **TL;DR** (Section 0) and **Repo Map** (Section 2).
2. Start with **Setup Guide** (Section 3) and make CI green.
3. Implement **tests only** (Section 8 prompts), then satisfy them in **parser/erg/sim**.
4. Build **TUI skeleton**, then wire **BLE client**; keep **SIM physics** independent.
5. Add **persistence & export**, then **hardening & release** as per **Release Checklist**.

---

## 22) Glossary (quick reference)

* **FTMS**: Fitness Machine Service (BLE GATT profile) — provides **Indoor Bike Data**, **Control Point**, **Status**.
* **ERG**: Ergometer mode — trainer enforces a target power.
* **SIM**: Simulation mode — trainer simulates grade/wind/rolling resistance; app sends grade.
* **JSONL**: JSON Lines — one JSON object per line, easy to stream/append.
* **NP/IF/TSS**: Normalized Power / Intensity Factor / Training Stress Score.

---

## 23) Roadmap Context (why the sequence)

* **Week 1** front‑loads test scaffolding and UI skeleton → agent productivity and tight feedback.
* **Week 2** focuses on **BLE + ERG** (highest training impact).
* **Week 3** adds **SIM physics + persistence** to complete the solo training loop.
* **Week 4** hardens reconnect/perf/packaging → a shippable `v0.1.0`.

*This context block lets any agent understand the origin, scope, and decisions without digging through chat logs.*


# Claude-Supplement Lite für TerminalRide

> **Purpose:** Ergänzt ChatGPT's "TerminalRide — Agent Pack" mit KI-Agent Workflows für Cursor/Claude Code/Codex/Gemini CLI. Keine neuen Dependencies. Fokus: Rollen, Prompts, Setup, Handoffs.

---

## 11) Allgemeine Agent-Verhaltensleitlinien

### Chirurgische Präzision statt Broad Strokes
- ✅ **Schreibe nur den Code der explizit angefragt wurde**
- ✅ **Kleine, fokussierte Änderungen** statt große Rewrites
- ✅ **Ein Problem nach dem anderen** lösen
- ❌ Nicht "gleich noch schnell XYZ mitfixen" ohne Nachfrage
- ❌ Keine anticipatory features ("könnte später nützlich sein")

### Bei Unsicherheit: Fragen statt Raten
- 🤔 **"Soll ich auch [verwandtes Problem] mit angehen?"**  
- 🤔 **"Ich sehe zwei Ansätze: A oder B. Welcher ist gewünscht?"**
- 🤔 **"Die Spec sagt X, aber Y würde mehr Sinn ergeben - was denkst du?"**
- ✅ Lieber einmal zu viel gefragt als falsche Annahmen gemacht

### Nichts ist in Stein gemeißelt!
- 🗣️ **"Diese Vorgabe verhindert eine sinnvolle Lösung, weil..."**
- 🗣️ **"Ich sehe einen Widerspruch zwischen Spec A und Requirement B"**  
- 🗣️ **"Das führt zu einem Design-Problem. Alternativer Ansatz wäre..."**
- ✅ **Hinterfrage aktiv** wenn etwas nicht stimmt oder besser geht

### Transparente Arbeitsweise
- 📝 **Erkläre dein Vorgehen:** "Ich implementiere zuerst X, dann Y, weil..."
- 📝 **Zeige Alternativen auf:** "Könnte auch mit Z lösen, aber X ist einfacher"
- 📝 **Nenne Limitations:** "Das funktioniert, aber hat Einschränkung Y"
- 📝 **Dokumentiere Entscheidungen:** "Wähle Ansatz A wegen Performance"

### Proaktive Problem-Erkennung
- 🚨 **"Das könnte später Probleme verursachen, weil..."**
- 🚨 **"Ich sehe ein Race Condition Risiko in..."**
- 🚨 **"Diese Abhängigkeit macht Testing schwierig"**
- 🚨 **"Performance könnte bei großen Datenmengen leiden"**

### Collaborative Mindset
- 🤝 **Baue auf bestehender Arbeit auf** statt alles neu zu schreiben
- 🤝 **Respektiere Architektur-Entscheidungen** (aber hinterfrage sie wenn nötig)
- 🤝 **Hinterlasse Code sauberer** als du ihn vorgefunden hast
- 🤝 **Denke an den nächsten Entwickler** (auch an dich selbst in 6 Monaten)

### Practical Engineering
- ⚙️ **MVP first:** Funktionsfähig > Perfekt
- ⚙️ **Tests als Dokumentation:** Zeigen wie Code verwendet werden soll
- ⚙️ **Fail fast:** Lieber früh crashen als silent corruption  
- ⚙️ **Measure before optimize:** Vermutungen über Performance sind oft falsch

### Communication Excellence
- 💬 **Status Updates:** "Bin bei X angelangt, Y ist noch offen"
- 💬 **Blockers melden:** "Kann nicht weitermachen wegen Z"  
- 💬 **Erfolge teilen:** "X funktioniert jetzt, Tests sind grün"
- 💬 **Handoff vorbereiten:** "Für nächsten Schritt braucht Agent B Info Y"

**Golden Rule:** Du bist ein **Collaborative Partner**, nicht nur ein Code-Generator. Think along, question assumptions, suggest improvements, aber implementiere nur was gewünscht ist.

---

## 1) Abstrakte Agent-Rollen (Tool-agnostisch)

### Agent A: Architecture & Complex Logic
- Interface Design (`devices/base.py` Protocols)
- Komplexe Algorithmen (ERG PI controller, SIM physics solver)  
- FTMS Protocol Parser (bit-level parsing)
- Module Integration & Refactoring
- Error Handling Patterns

### Agent B: Feature Implementation
- TUI Views & Components (`ui/views.py`, `ui/widgets.py`)
- BLE Client Implementation (`devices/ftms_client.py`)
- Data Persistence (`store/repo.py`, `store/export.py`)
- Test Implementation (unit & integration)
- Bug Fixes & Debugging

### Agent C: Utilities & Boilerplate
- Configuration Management (`config.py`)
- Data Models (Pydantic classes)
- CLI Argument Parsing
- Logging Utilities (simple JSONL)

### Agent D: Review & Analysis
- Code Quality Review
- Architecture Compliance Check
- Performance Analysis
- Documentation Gaps

**Note:** Du kannst diese Rollen auf deine verfügbaren KI-Tools (Claude Code, Cursor Agent, Codex, Gemini CLI) verteilen wie es für dich am besten funktioniert.

---

## 2) Standard Kontext Template (für alle Agents)

```
PROJECT: TerminalRide v0.1 - Terminal-first FTMS cycling trainer
STACK: Python 3.11, bleak (BLE), rich/textual (TUI), numpy, pydantic, pytest
ARCHITECTURE: Protocol-first, pure functions separated from I/O
CONSTRAINTS: 
- Temperature 0.1 (deterministic)
- Tests-first approach (TDD)  
- No invented FTMS details (add TODO markers)
- No new dependencies beyond: bleak, rich, numpy, pydantic, pytest
- JSONL logging via stdlib logging only

CURRENT TASK: [specific module/feature]
CONTEXT: [what's already implemented]
GOAL: [specific deliverable]
```

---

## 3) Prompt Templates

### 3.1 Tests-First Implementation
```
Create unit tests only for TerminalRide:

For [MODULE]:
- tests/test_ftms_parse.py (3 hex fixtures: all fields, missing speed, invalid length)
- tests/test_erg.py (PI controller: bounds [100,400]W, rate limit ±10W/5s, step response)  
- tests/test_sim_physics.py (250W @ 0% grade, m=100kg → speed in [9.0,11.5] m/s)

Use pytest. No BLE I/O in tests. Output only test files.
Make tests fail initially (red phase of TDD).
```

### 3.2 Pure Function Implementation
```
Implement [MODULE] following TerminalRide patterns:

REQUIREMENTS: [from ChatGPT's spec]
INTERFACES: Follow devices/base.py Protocol exactly
CONSTRAINTS: Pure function, no I/O side effects, comprehensive docstrings

EXAMPLE:
```python
def parse_indoor_bike_data(frame: bytes) -> ParsedBikeData:
    """Parse FTMS Indoor Bike Data frame.
    
    Args:
        frame: Raw BLE notification bytes
        
    Returns:
        ParsedBikeData with power_w, cadence_rpm, speed_mps (None if absent)
        
    Raises:
        ValueError: If frame length invalid
        
    Example:
        >>> data = parse_indoor_bike_data(b'\x16\x2A\x63\x01\x00\xF4\x01')
        >>> data.power_w
        500
    """
```

Make the failing tests pass.
```

### 3.3 UI Component Implementation  
```
Implement TUI component for TerminalRide using Rich/Textual:

COMPONENT: [LiveView/MenuSystem/StatsView]
REQUIREMENTS: [from ChatGPT's PRD]
EXISTING PATTERNS: Follow ui/ structure exactly

Must include:
- Keyboard navigation (1/2/3, +/-, space, q, ?)
- Real-time updates at 10Hz
- Clear visual hierarchy
- Error state handling

No new dependencies. Use only rich/textual primitives.
```

---

## 4) Development Environment Setup

### 4.1 Cursor IDE Configuration
```json
// .cursor/settings.json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "editor.formatOnSave": true,
    "python.analysis.typeCheckingMode": "basic",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true,
        "source.fixAll.ruff": true
    },
    "files.associations": {
        "*.jsonl": "jsonlines"
    }
}
```

### 4.2 Simple Project Setup
```bash
# Virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install core dependencies only
pip install bleak rich numpy pydantic pytest mypy ruff black

# Development setup
git init
echo ".venv/" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
```

### 4.3 requirements.txt (keep it simple)
```
# Core dependencies
bleak>=0.21.1
rich>=13.7.0
numpy>=1.24.0
pydantic>=2.5.0

# Dev dependencies
pytest>=7.4.0
pytest-asyncio>=0.21.0
mypy>=1.8.0
ruff>=0.1.0
black>=23.12.0
```

---

## 5) Code Quality Checklist (minimal)

### Before Commit:
- [ ] Tests pass (`pytest`)
- [ ] Type checking passes (`mypy --strict terminalride`)
- [ ] Linting passes (`ruff check terminalride`)
- [ ] Formatting applied (`black terminalride`)
- [ ] No debug prints or untracked TODOs

### Architecture Compliance:
- [ ] Pure functions separated from I/O operations
- [ ] Follows Protocol interfaces from `devices/base.py`
- [ ] Type hints and docstrings with units (W, rpm, m/s, %)
- [ ] JSONL logging for significant events only
- [ ] No blocking operations in async functions

---

## 6) Simple Logging Pattern

```python
# Simple JSONL logging (no new dependencies)
import json
import logging
from datetime import datetime

# Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler('terminalride.jsonl'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('terminalride')

# Usage
def log_event(event_type: str, **kwargs):
    """Log structured event to JSONL."""
    event = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        **kwargs
    }
    logger.info(json.dumps(event, separators=(',', ':')))

# Examples  
log_event('session_started', session_id='abc123', mode='erg', ftp=250)
log_event('sample', power_w=245, cadence_rpm=85, speed_mps=9.2)
log_event('error', code='BLE_E_CONNECTION_FAILED', message='Device not found')
```

---

## 7) Agent Handoff Process

### Agent A → Agent B:
```markdown
## Handoff: Architecture → Implementation

**Status:** ✅ Complete
- [ ] Interfaces defined in `devices/base.py`
- [ ] Algorithm implemented and tested
- [ ] Error handling patterns established  
- [ ] Integration points documented

**Next Steps for Implementation:**
- Implement UI components using established patterns
- Wire BLE client to interface
- Add persistence layer
- Integration testing

**Notes:** ERG controller uses PI with anti-windup, bounds [100,400]W
```

### Agent B → Agent A:
```markdown
## Handoff: Implementation → Optimization

**Status:** ✅ Feature complete, ⚠️ Performance review needed
- [x] Feature working end-to-end
- [x] Tests passing  
- [ ] Memory usage optimization needed
- [ ] BLE reconnection timing improvement

**Issues Found:**
- Memory grows during long sessions (data pipeline)
- UI occasionally drops frames during high data rate

**Next Steps:** Performance optimization and refactoring
```

---

## 8) Simple Mock Trainer (for testing, no new deps)

```python
# tests/fixtures/mock_trainer.py
import time
import random
import asyncio
from typing import Dict, Any

class MockWahooTrainer:
    """Simple mock trainer for testing."""
    
    def __init__(self):
        self.connected = False
        self.control_granted = False
        self.target_power = 150
        self.current_power = 150.0
        self.cadence = 80
        
    async def connect(self) -> None:
        """Simulate connection delay."""
        await asyncio.sleep(0.1)
        self.connected = True
        
    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self.connected = False
        self.control_granted = False
        
    async def request_control(self) -> None:
        """Grant trainer control."""
        if not self.connected:
            raise RuntimeError("Trainer not connected")
        self.control_granted = True
        
    async def set_target_power(self, watts: int) -> None:
        """Set ERG target power."""
        if not self.control_granted:
            raise RuntimeError("Control not granted")
        self.target_power = max(100, min(400, watts))
        
    def get_current_sample(self) -> Dict[str, Any]:
        """Generate realistic sample data."""
        # Simple power following with lag
        power_diff = self.target_power - self.current_power
        self.current_power += power_diff * 0.3  # 30% per sample
        
        # Realistic cadence based on power
        self.cadence = max(0, 70 + (self.current_power - 150) * 0.1)
        
        # Speed from power approximation
        speed_mps = max(0, 8.0 + (self.current_power - 150) * 0.01)
        
        return {
            'ts': time.time(),
            'power_w': int(self.current_power + random.uniform(-5, 5)),
            'cadence_rpm': int(self.cadence + random.uniform(-3, 3)),
            'speed_mps': speed_mps + random.uniform(-0.2, 0.2)
        }

# Usage in tests
@pytest.mark.asyncio
async def test_erg_session():
    """Test ERG session with mock trainer."""
    trainer = MockWahooTrainer()
    await trainer.connect()
    await trainer.request_control()
    
    # Set target and verify response
    await trainer.set_target_power(200)
    
    # Simulate 10 samples
    samples = []
    for _ in range(10):
        sample = trainer.get_current_sample()
        samples.append(sample)
        await asyncio.sleep(0.1)
    
    # Verify power converges to target
    final_power = samples[-1]['power_w']
    assert abs(final_power - 200) < 20  # Within 20W of target
```

---

## 9) What NOT to Add (keep it simple)

❌ **Don't add these (save for later):**
- Additional logging libraries (`structlog`, `loguru`)
- Performance monitoring tools (`psutil`, `memory_profiler`)  
- Security scanners (`bandit`, `safety`)
- Complex CI/CD pipelines 
- Cross-platform build scripts
- Recovery/emergency procedures
- Advanced configuration management
- Database migrations or complex persistence

✅ **Keep it minimal:**
- Core 5 dependencies only
- Simple JSONL logging with stdlib
- Basic file persistence (JSONL → CSV export)
- Essential error handling
- Standard git workflow

---

## 10) Success Criteria Reminder

**MVP v0.1.0 is done when:**
- ✅ KICKR connects via BLE in <5 seconds
- ✅ ERG mode responds to +/- keys in <2 seconds  
- ✅ Live metrics display at 10Hz
- ✅ Session saves to JSONL and exports CSV
- ✅ UI navigation works intuitively
- ✅ Reconnects after brief disconnection
- ✅ All tests pass

**That's it.** No more, no less.

---

**This supplement focuses only on what ChatGPT's excellent technical foundation was missing: KI-agent workflows and basic development ergonomics. Everything else can wait for v0.2+.**