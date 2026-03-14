from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
from typing import Any

ATS_COLORS = {
    "CLEAN": "#22c55e",
    "ADVISORY": "#38bdf8",
    "MAINTENANCE_NEEDED": "#f59e0b",
    "CRITICAL_MAINTENANCE": "#ef4444",
}


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _series_with_gap_breaks(
    history: list[dict[str, Any]],
    value_key: str,
    gap_seconds: float,
) -> tuple[list[Any], list[Any]]:
    xs: list[Any] = []
    ys: list[Any] = []
    previous: datetime | None = None

    for row in history:
        dt = row.get("_dt")
        if not isinstance(dt, datetime):
            continue
        if previous is not None and (dt - previous).total_seconds() > gap_seconds:
            xs.append(None)
            ys.append(None)
        xs.append(dt)
        ys.append(row.get(value_key))
        previous = dt

    return xs, ys


def _make_plot(history: list[dict[str, Any]], sample_interval_seconds: int) -> Any:
    import plotly.graph_objs as go

    gap_seconds = max(10, sample_interval_seconds * 4)
    cpu_x, cpu_y = _series_with_gap_breaks(history, "cpu_percent", gap_seconds)
    ram_x, ram_y = _series_with_gap_breaks(history, "ram_percent", gap_seconds)
    risk_x, risk_y = _series_with_gap_breaks(history, "risk_score", gap_seconds)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cpu_x, y=cpu_y, name="CPU %"))
    fig.add_trace(go.Scatter(x=ram_x, y=ram_y, name="RAM %"))

    has_temp = any(float(row.get("temp_c", -1.0)) > 0 for row in history)
    if has_temp:
        temp_x, temp_y = _series_with_gap_breaks(history, "temp_c", gap_seconds)
        fig.add_trace(
            go.Scatter(
                x=temp_x,
                y=temp_y,
                name="Temp C",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=risk_x,
            y=risk_y,
            name="Risk Score",
            line={"dash": "dot"},
        )
    )

    fig.update_layout(
        template="plotly_dark",
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        legend={"orientation": "h"},
        yaxis={"range": [0, 100]},
    )
    return fig


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_ats_script_path(config: dict[str, Any]) -> Path:
    raw_path = str(config.get("ats", {}).get("script_path", "ATS_Maintenance_Aspire.bat")).strip()
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return _project_root() / path


def _launch_ats_script_elevated(script_path: Path) -> tuple[bool, str]:
    escaped_path = str(script_path).replace("'", "''")
    escaped_workdir = str(script_path.parent).replace("'", "''")
    command = (
        f"Start-Process -FilePath '{escaped_path}' "
        f"-WorkingDirectory '{escaped_workdir}' "
        "-Verb RunAs"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        return False, str(exc)

    if result.returncode == 0:
        return True, ""
    error = (result.stderr or result.stdout or "UAC launch failed").strip()
    return False, error


def _agent_status_text(config: dict[str, Any]) -> str:
    agent_cfg = config.get("agent", {})
    enabled = bool(agent_cfg.get("enabled", False))
    use_llm = bool(agent_cfg.get("use_llm", False))
    model = str(agent_cfg.get("ollama_model", "unknown")).strip() or "unknown"
    if enabled and use_llm:
        return f"Agent mode: LLM ({model})"
    if enabled:
        return "Agent mode: rule-based (LLM disabled)"
    return "Agent mode: disabled (rule-based safety fallback active)"


def _health_status_text(latest: dict[str, Any], actions: list[dict[str, Any]]) -> str:
    temp = float(latest.get("temp_c", -1.0))
    battery = latest.get("battery_percent")
    gpu_percent = latest.get("gpu_percent")
    risk_flags = latest.get("risk_flags", [])

    checks: list[str] = []
    checks.append("Temp sensor OK" if temp > 0 else "Temp sensor unavailable (WMI)")
    checks.append("Battery telemetry OK" if battery is not None else "Battery telemetry unavailable")
    checks.append("GPU telemetry OK" if gpu_percent is not None else "GPU telemetry unavailable")
    if isinstance(risk_flags, list) and risk_flags:
        checks.append(f"Risk flags: {','.join(risk_flags)}")
    else:
        checks.append("Risk flags: none")

    if actions:
        last = actions[0]
        checks.append(
            "Last action: "
            f"{last.get('action', 'NONE')} -> {last.get('outcome', 'n/a')}"
        )
    else:
        checks.append("Last action: none")
    return " | ".join(checks)


def _normalize_actions(actions_raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in actions_raw:
        details = row.get("details", {})
        if not isinstance(details, dict):
            details = {}
        risk_flags = details.get("risk_flags", [])
        reason = str(row.get("reason", ""))
        if isinstance(risk_flags, list) and risk_flags:
            reason = f"{reason} | flags={','.join(str(flag) for flag in risk_flags)}"
        rows.append(
            {
                "timestamp": row.get("timestamp", ""),
                "risk_score": row.get("risk_score", ""),
                "risk_level": row.get("risk_level", ""),
                "action": row.get("action", ""),
                "target": row.get("target", ""),
                "outcome": row.get("outcome", ""),
                "agent_mode": details.get("agent_mode", ""),
                "source": details.get("decision_source", ""),
                "policy_version": details.get("policy_version", ""),
                "reason": reason,
            }
        )
    return rows


def _build_dashboard_payload(
    db: Any,
    points: int,
    chart_minutes: int,
    sample_interval_seconds: int,
    config: dict[str, Any],
) -> tuple[str, Any, str, list[dict[str, Any]], str, str, str, str]:
    history_all = db.get_recent_metrics(max(points * 4, 400))
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max(1, chart_minutes))
    history: list[dict[str, Any]] = []
    for row in history_all:
        parsed = _parse_timestamp(row.get("timestamp"))
        if parsed is None:
            continue
        enriched = dict(row)
        enriched["_dt"] = parsed
        if parsed >= cutoff:
            history.append(enriched)

    if not history:
        fallback: list[dict[str, Any]] = []
        for row in history_all[-points:]:
            parsed = _parse_timestamp(row.get("timestamp"))
            if parsed is None:
                continue
            enriched = dict(row)
            enriched["_dt"] = parsed
            fallback.append(enriched)
        history = fallback

    history = sorted(history, key=lambda row: row["_dt"])[-points:]
    if not history:
        import plotly.graph_objs as go

        fig = go.Figure()
        fig.update_layout(template="plotly_dark")
        return (
            "Waiting for telemetry data...",
            fig,
            "No processes yet",
            [],
            "No alerts yet",
            "No diagnosis yet",
            _agent_status_text(config),
            "Health checks pending...",
        )

    latest = history[-1]
    temp = float(latest.get("temp_c", -1.0))
    temp_text = f"{temp:.1f} C" if temp > 0 else "Unavailable"
    status = (
        f"CPU: {float(latest.get('cpu_percent', 0.0)):.1f}% | "
        f"RAM: {float(latest.get('ram_percent', 0.0)):.1f}% | "
        f"Temp: {temp_text} | "
        f"Risk: {int(latest.get('risk_score', 0))} ({latest.get('risk_level', 'normal')})"
    )

    top = latest.get("top_processes", [])
    if top:
        process_lines = [f"- {row.get('name', '?')}: {float(row.get('cpu', 0.0)):.1f}% CPU" for row in top]
        top_text = "\n".join(process_lines)
    else:
        top_text = "No process data"

    actions_raw = db.get_recent_actions(20)
    actions = _normalize_actions(actions_raw)
    level = str(latest.get("risk_level", "normal")).lower()
    flags = latest.get("risk_flags", [])
    flags_text = ",".join(flags) if isinstance(flags, list) and flags else "none"
    alerts_text = f"Risk level: {level}; flags: {flags_text}"
    diagnosis_text = f"Recent actions: {len(actions)}"
    fig = _make_plot(history, sample_interval_seconds)
    return (
        status,
        fig,
        top_text,
        actions,
        alerts_text,
        diagnosis_text,
        _agent_status_text(config),
        _health_status_text(latest, actions),
    )


def create_dashboard(db: Any, config: dict[str, Any]) -> Any:
    try:
        import dash
        from dash import dash_table, dcc, html
        from dash.dependencies import Input, Output, State
    except Exception as exc:
        raise RuntimeError("Dashboard dependencies missing. Install requirements.txt.") from exc

    app = dash.Dash(__name__)
    chart_minutes = max(1, int(config["dashboard"].get("chart_window_minutes", 30)))
    sample_interval = max(1, int(float(config["general"].get("sample_interval_seconds", 3))))
    points = max(20, int((chart_minutes * 60) / sample_interval))
    refresh_ms = max(1000, sample_interval * 1000)
    ats_script_path = _resolve_ats_script_path(config)

    def _latest_snapshot_from_db() -> dict[str, Any]:
        latest = db.get_latest_metric()
        if latest is None:
            return {}
        return latest

    def _render_ats_panel(latest_ats: dict[str, Any]) -> tuple[Any, Any, Any, str, dict[str, Any], bool]:
        if not latest_ats:
            empty_style = {
                "backgroundColor": "#111827",
                "borderRadius": "10px",
                "padding": "16px",
                "border": "1px solid #1f2937",
            }
            return (
                html.Div(
                    [
                        html.Div("ATS Maintenance", style={"fontSize": "14px", "color": "#93c5fd"}),
                        html.Div("Waiting", style={"fontSize": "34px", "fontWeight": "bold"}),
                        html.Div("No ATS evaluation recorded yet", style={"fontSize": "13px", "color": "#94a3b8"}),
                    ],
                    style=empty_style,
                ),
                html.Div("ATS reasons will appear after the first evaluation.", style={"color": "#94a3b8", "fontSize": "13px"}),
                html.Div("No ATS signal data yet.", style={"color": "#94a3b8", "fontSize": "13px"}),
                f"Script: {ats_script_path} (missing)",
                {
                    "backgroundColor": "#7f1d1d",
                    "color": "#f8fafc",
                    "border": "none",
                    "padding": "10px 16px",
                    "borderRadius": "8px",
                    "fontWeight": "bold",
                    "cursor": "not-allowed",
                },
                True,
            )

        verdict = str(latest_ats.get("verdict", "CLEAN"))
        score = float(latest_ats.get("maintenance_score", 0.0))
        reasons = list(latest_ats.get("top_reasons", []))
        signals = list(latest_ats.get("signals", []))
        fresh_scan = bool(latest_ats.get("fresh_scan", False))
        timestamp = _parse_timestamp(latest_ats.get("timestamp"))
        timestamp_text = timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S") if timestamp else "Unknown"
        color = ATS_COLORS.get(verdict, "#94a3b8")
        bar_width = f"{max(0.0, min(score, 100.0)):.0f}%"

        summary = html.Div(
            [
                html.Div("ATS Maintenance", style={"fontSize": "14px", "color": "#93c5fd"}),
                html.Div(
                    [
                        html.Span(f"{score:.0f}", style={"fontSize": "40px", "fontWeight": "bold", "color": color}),
                        html.Span("/100", style={"fontSize": "18px", "color": "#94a3b8", "marginLeft": "4px"}),
                    ]
                ),
                html.Div(
                    style={"height": "10px", "backgroundColor": "#1f2937", "borderRadius": "999px", "overflow": "hidden", "margin": "10px 0"},
                    children=[
                        html.Div(style={"width": bar_width, "height": "100%", "backgroundColor": color})
                    ],
                ),
                html.Div(verdict.replace("_", " "), style={"fontSize": "16px", "fontWeight": "bold", "color": color}),
                html.Div(
                    f"Last scan: {timestamp_text} | {'fresh scan' if fresh_scan else 'cached heavy scan'}",
                    style={"fontSize": "12px", "color": "#94a3b8", "marginTop": "6px"},
                ),
            ],
            style={
                "backgroundColor": "#111827",
                "borderRadius": "10px",
                "padding": "16px",
                "border": f"1px solid {color}",
            },
        )

        if reasons:
            reasons_block = html.Ul(
                [html.Li(reason, style={"marginBottom": "4px"}) for reason in reasons[:5]],
                style={"paddingLeft": "18px", "margin": 0, "fontSize": "13px", "color": "#e2e8f0"},
            )
        else:
            reasons_block = html.Div("System is clean.", style={"fontSize": "13px", "color": "#22c55e"})

        signal_rows = []
        for signal in signals:
            status = str(signal.get("status", "OK"))
            signal_rows.append(
                html.Tr(
                    [
                        html.Td(str(signal.get("name", "")), style={"padding": "6px 8px"}),
                        html.Td(f"{signal.get('value', 0)} {signal.get('unit', '')}".strip(), style={"padding": "6px 8px", "color": "#cbd5e1"}),
                        html.Td(status, style={"padding": "6px 8px", "color": ATS_COLORS.get('CRITICAL_MAINTENANCE' if status == 'CRITICAL' else 'MAINTENANCE_NEEDED' if status == 'WARN' else 'CLEAN', '#e2e8f0')}),
                    ]
                )
            )
        signals_table = html.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Signal", style={"textAlign": "left", "padding": "6px 8px"}),
                            html.Th("Value", style={"textAlign": "left", "padding": "6px 8px"}),
                            html.Th("Status", style={"textAlign": "left", "padding": "6px 8px"}),
                        ]
                    )
                ),
                html.Tbody(signal_rows),
            ],
            style={"width": "100%", "fontSize": "13px", "borderCollapse": "collapse"},
        )

        script_exists = ats_script_path.exists()
        if script_exists:
            script_status = f"Script: {ats_script_path}"
        else:
            script_status = f"Script missing: {ats_script_path}"

        button_style = {
            "backgroundColor": color if score >= 40 else "#2563eb",
            "color": "#f8fafc",
            "border": "none",
            "padding": "10px 16px",
            "borderRadius": "8px",
            "fontWeight": "bold",
            "cursor": "pointer" if script_exists else "not-allowed",
            "opacity": 1.0 if script_exists else 0.55,
        }
        return summary, reasons_block, signals_table, script_status, button_style, (not script_exists)

    app.layout = html.Div(
        style={"fontFamily": "Segoe UI", "padding": "20px", "backgroundColor": "#0f172a", "color": "#e2e8f0"},
        children=[
            html.H1("Laptop Health Guardian"),
            html.Div(id="status-line", style={"fontSize": "18px", "marginBottom": "10px"}),
            html.Div(id="agent-line", style={"fontSize": "15px", "marginBottom": "6px", "color": "#93c5fd"}),
            html.Div(id="health-line", style={"fontSize": "14px", "marginBottom": "10px", "color": "#cbd5e1"}),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "1fr 1.4fr", "gap": "12px", "marginBottom": "14px"},
                children=[
                    html.Div(id="ats-summary"),
                    html.Div(
                        style={"backgroundColor": "#111827", "borderRadius": "10px", "padding": "16px", "border": "1px solid #1f2937"},
                        children=[
                            html.Div("ATS Signals", style={"fontSize": "15px", "fontWeight": "bold", "marginBottom": "8px", "color": "#93c5fd"}),
                            html.Div(id="ats-signals"),
                        ],
                    ),
                ],
            ),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "1fr auto", "gap": "12px", "alignItems": "center", "marginBottom": "14px"},
                children=[
                    html.Div(
                        style={"backgroundColor": "#111827", "borderRadius": "10px", "padding": "16px", "border": "1px solid #1f2937"},
                        children=[
                            html.Div("ATS Reasons", style={"fontSize": "15px", "fontWeight": "bold", "marginBottom": "8px", "color": "#93c5fd"}),
                            html.Div(id="ats-reasons"),
                            html.Div(id="ats-script-status", style={"fontSize": "12px", "color": "#94a3b8", "marginTop": "10px"}),
                            html.Div(id="ats-action-result", style={"fontSize": "13px", "marginTop": "8px", "color": "#22c55e"}),
                        ],
                    ),
                    html.Div(
                        style={"display": "flex", "flexDirection": "column", "gap": "10px"},
                        children=[
                            html.Button("Run ATS Now", id="ats-run-button", n_clicks=0),
                            html.Button(
                                "Re-evaluate ATS",
                                id="ats-reevaluate-button",
                                n_clicks=0,
                                style={
                                    "backgroundColor": "#1d4ed8",
                                    "color": "#f8fafc",
                                    "border": "none",
                                    "padding": "10px 16px",
                                    "borderRadius": "8px",
                                    "fontWeight": "bold",
                                    "cursor": "pointer",
                                },
                            ),
                        ],
                    ),
                ],
            ),
            dcc.Graph(id="metrics-graph"),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"},
                children=[
                    html.Div(
                        style={"backgroundColor": "#111827", "borderRadius": "8px", "padding": "12px"},
                        children=[html.H3("Top Processes"), html.Pre(id="top-processes", style={"whiteSpace": "pre-wrap", "margin": 0})],
                    ),
                    html.Div(
                        style={"backgroundColor": "#111827", "borderRadius": "8px", "padding": "12px"},
                        children=[
                            html.H3("Recent Actions"),
                            dash_table.DataTable(
                                id="actions-table",
                                columns=[
                                    {"name": "Timestamp", "id": "timestamp"},
                                    {"name": "Risk", "id": "risk_score"},
                                    {"name": "Level", "id": "risk_level"},
                                    {"name": "Action", "id": "action"},
                                    {"name": "Target", "id": "target"},
                                    {"name": "Outcome", "id": "outcome"},
                                    {"name": "Agent", "id": "agent_mode"},
                                    {"name": "Source", "id": "source"},
                                    {"name": "Policy", "id": "policy_version"},
                                    {"name": "Reason", "id": "reason"},
                                ],
                                data=[],
                                style_table={"overflowX": "auto"},
                                style_cell={
                                    "backgroundColor": "#0b1220",
                                    "color": "#e2e8f0",
                                    "fontSize": "12px",
                                    "textAlign": "left",
                                    "whiteSpace": "normal",
                                    "maxWidth": "320px",
                                },
                                style_header={"backgroundColor": "#1f2937", "fontWeight": "bold"},
                            ),
                        ],
                    ),
                ],
            ),
            dcc.Interval(id="interval", interval=refresh_ms, n_intervals=0),
            dcc.Interval(id="ats-interval", interval=15000, n_intervals=0),
            # Legacy IDs kept to avoid 500s from stale browser tabs after dashboard updates.
            dcc.Interval(id="interval-component", interval=refresh_ms, n_intervals=0),
            html.Div(id="live-metrics", style={"display": "none"}),
            dcc.Graph(id="live-graph", style={"display": "none"}),
            html.Div(id="alert-feed", style={"display": "none"}),
            html.Div(id="process-feed", style={"display": "none"}),
            html.Div(id="disk-writer-feed", style={"display": "none"}),
            html.Div(id="diagnosis-feed", style={"display": "none"}),
        ],
    )

    @app.callback(
        [
            Output("status-line", "children"),
            Output("agent-line", "children"),
            Output("health-line", "children"),
            Output("metrics-graph", "figure"),
            Output("top-processes", "children"),
            Output("actions-table", "data"),
        ],
        [Input("interval", "n_intervals")],
    )
    def update(_: int) -> tuple[str, str, str, Any, str, list[dict[str, Any]]]:
        status, fig, top_text, actions, _, _, agent_line, health_line = _build_dashboard_payload(
            db,
            points,
            chart_minutes,
            sample_interval,
            config,
        )
        return status, agent_line, health_line, fig, top_text, actions

    @app.callback(
        [
            Output("ats-summary", "children"),
            Output("ats-signals", "children"),
            Output("ats-reasons", "children"),
            Output("ats-script-status", "children"),
            Output("ats-run-button", "style"),
            Output("ats-run-button", "disabled"),
            Output("ats-action-result", "children"),
        ],
        [
            Input("ats-interval", "n_intervals"),
            Input("ats-reevaluate-button", "n_clicks"),
            Input("ats-run-button", "n_clicks"),
        ],
        [State("ats-action-result", "children")],
    )
    def update_ats_panel(_: int, reeval_clicks: int, run_clicks: int, current_message: str) -> tuple[Any, Any, Any, str, dict[str, Any], bool, str]:
        from app.watchdog.ats_evaluator import evaluate as evaluate_ats

        message = current_message or ""
        triggered = dash.ctx.triggered_id
        if triggered == "ats-reevaluate-button":
            latest_snapshot = _latest_snapshot_from_db()
            if latest_snapshot:
                result = evaluate_ats(latest_snapshot, config, force=True)
                db.insert_ats_evaluation(result)
                db.insert_action(
                    risk_score=int(round(result.maintenance_score)),
                    risk_level=result.verdict.lower(),
                    action="ATS_REEVALUATE",
                    target="maintenance_evaluator",
                    reason="Manual ATS re-evaluation requested from dashboard",
                    outcome="success",
                    details={
                        "decision_source": "dashboard_manual_reevaluate",
                        "policy_version": str(config.get("accountability", {}).get("policy_version", "unknown")),
                        "maintenance_score": result.maintenance_score,
                        "verdict": result.verdict,
                    },
                )
                message = f"ATS re-evaluated. Verdict: {result.verdict.replace('_', ' ')} ({result.maintenance_score:.0f}/100)."
            else:
                message = "ATS re-evaluation skipped: no telemetry has been recorded yet."
        elif triggered == "ats-run-button":
            if ats_script_path.exists():
                try:
                    launched, error = _launch_ats_script_elevated(ats_script_path)
                    if launched:
                        db.insert_action(
                            risk_score=0,
                            risk_level="info",
                            action="ATS_RUN_SCRIPT",
                            target=str(ats_script_path),
                            reason="Dashboard launched ATS maintenance script with elevation",
                            outcome="launched_elevated",
                            details={"decision_source": "dashboard_manual_launch"},
                        )
                        message = "ATS maintenance launched. Approve the UAC prompt if Windows asks."
                    else:
                        db.insert_action(
                            risk_score=0,
                            risk_level="error",
                            action="ATS_RUN_SCRIPT",
                            target=str(ats_script_path),
                            reason="Dashboard failed to launch ATS maintenance script with elevation",
                            outcome="failed",
                            details={"decision_source": "dashboard_manual_launch", "error": error},
                        )
                        message = f"ATS maintenance launch failed: {error}"
                except Exception as exc:
                    db.insert_action(
                        risk_score=0,
                        risk_level="error",
                        action="ATS_RUN_SCRIPT",
                        target=str(ats_script_path),
                        reason="Dashboard failed to launch ATS maintenance script",
                        outcome="failed",
                        details={"decision_source": "dashboard_manual_launch", "error": str(exc)},
                    )
                    message = f"ATS maintenance launch failed: {exc}"
            else:
                message = f"ATS script not found: {ats_script_path}"

        latest_ats = db.get_latest_ats_evaluation()
        summary, reasons_block, signals_table, script_status, button_style, button_disabled = _render_ats_panel(latest_ats or {})
        return summary, signals_table, reasons_block, script_status, button_style, button_disabled, message

    @app.callback(
        [
            Output("live-metrics", "children"),
            Output("live-graph", "figure"),
            Output("alert-feed", "children"),
            Output("process-feed", "children"),
        ],
        [Input("interval-component", "n_intervals")],
    )
    def update_legacy_live(_: int) -> tuple[str, Any, str, str]:
        status, fig, top_text, _, alerts_text, _, _, _ = _build_dashboard_payload(
            db,
            points,
            chart_minutes,
            sample_interval,
            config,
        )
        return status, fig, alerts_text, top_text

    @app.callback(
        [
            Output("disk-writer-feed", "children"),
            Output("diagnosis-feed", "children"),
        ],
        [Input("interval-component", "n_intervals")],
    )
    def update_legacy_diagnosis(_: int) -> tuple[str, str]:
        _, _, _, _, alerts_text, diagnosis_text, _, _ = _build_dashboard_payload(
            db,
            points,
            chart_minutes,
            sample_interval,
            config,
        )
        return alerts_text, diagnosis_text

    return app
