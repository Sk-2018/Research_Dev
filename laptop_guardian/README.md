# Laptop Health Guardian

Full-feature Windows thermal watchdog with:
- Continuous telemetry collection (CPU, RAM, WMI temperature, top CPU processes)
- Stateful risk scoring
- Rule-based or LLM-assisted remediation decisions
- Safe action execution with cooldowns and allowlists
- SQLite persistence for metrics and action audit history
- Live Dash dashboard for monitoring and incident review

## Architecture
- `app/collector/sensors.py`: system telemetry sampling
- `app/watchdog/risk.py`: stateful risk engine
- `app/agent/jarvis.py`: decision engine (rules + optional Ollama LLM)
- `app/watchdog/daemon.py`: orchestrates monitoring and mitigations
- `app/storage/db.py`: telemetry + action storage
- `app/ui/dashboard.py`: real-time dashboard
- `app/configuration.py`: defaults, merge, and validation
- `app/logging_utils.py`: rotating logs

## Safety Controls
- `actions.never_kill`: hard-protected process list (cannot be terminated)
- `actions.allowlist_kill`: only these process names can be terminated
- `actions.max_kill_per_cycle`: bounds termination blast radius
- `actions.action_cooldown_sec`: prevents repeated aggressive actions
- `actions.dry_run`: simulate decisions without applying system changes

## Installation
```powershell
pip install -r requirements.txt
```

## Run Modes
- Normal mode (watchdog + dashboard):
```powershell
python -m app.main
```

- Headless mode (watchdog only):
```powershell
python -m app.main --headless
```

- Force dry-run for a session:
```powershell
python -m app.main --dry-run
```

- Custom config path:
```powershell
python -m app.main --config .\config.yaml
```

Dashboard URL is configured under `dashboard.host` and `dashboard.port`.

## Operational Notes
- Run elevated PowerShell for best WMI and `powercfg` behavior.
- If WMI temperature is unavailable, risk engine automatically falls back to CPU-based proxy logic.
- `guardian.log` is rotated automatically (2 MB x 3 backups).
- SQLite DB stores:
  - `metrics`: sampled telemetry
  - `actions`: all critical decisions and outcomes

## Tuning Guidance
- Start in `dry_run: true` for calibration.
- Lower thresholds temporarily to test notifications and action paths.
- Keep `use_llm: false` until local Ollama connectivity is verified.
- Add your IDE, terminals, and critical developer services to `never_kill`.
- Keep `allowlist_kill` narrow and explicit.
