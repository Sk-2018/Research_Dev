# Laptop Health Guardian

Windows-oriented watchdog that samples device health, computes a thermal/performance risk score, and can apply guarded mitigation actions.

## Features

- Periodic system telemetry collection (CPU, RAM, disk, battery, temperature, top processes)
- Weighted risk scoring with trend awareness (temperature slope)
- Rule-based or optional LLM-backed action suggestions
- Safe watchdog actions (power plan switch, process priority reduction, optional process suspend)
- ATS maintenance scoring with dashboard launch button for `ATS_Maintenance_Aspire.bat`
- SQLite persistence for metrics and actions
- Optional Dash dashboard

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run once for a smoke test:

```powershell
python -m app.main --once --headless
```

4. Run continuously:

```powershell
python -m app.main --headless
```

5. Run with dashboard:

```powershell
python -m app.main
```

Dashboard default URL: `http://127.0.0.1:8050`.

## Config

Main runtime options live in `config.yaml`:

- `general`: sampling interval, DB/log paths, dry-run mode
- `thresholds`: warning/critical thresholds for risk inputs
- `risk_weights`: weighted contribution to total risk score
- `actions`: mitigation toggles
- `process_allowlist`: guarded process names for priority lowering/kill candidates
- `agent`: Jarvis decision mode (rule-based vs LLM fallback)
- `ats`: ATS maintenance evaluation interval, toast cooldown, and batch-script path

## Scripts

- `scripts/run.ps1`: bootstrap + run app
- `scripts/install_service.ps1`: register a Windows Scheduled Task for background startup

## Notes

- Temperature via WMI may be unavailable on some systems/BIOS setups.
- Actions are intentionally conservative; set `general.dry_run: true` to verify behavior before enabling real changes.
- The current config points to `..\ATS_Maintenance_Aspire.bat`; change `ats.script_path` if your BAT lives elsewhere.
