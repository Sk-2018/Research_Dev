"""
Plotly Dash dashboard for Laptop Health Guardian.
Binds to localhost and auto-refreshes every 3 seconds.
"""
from __future__ import annotations

from datetime import datetime
import logging

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html, dash_table


logger = logging.getLogger(__name__)

TIER_COLOR = {"INFO": "#2ECC71", "WARN": "#F39C12", "CRITICAL": "#E74C3C"}
DARK_BG = "#0d1117"
CARD_BG = "#161b22"
TEXT_COLOR = "#c9d1d9"


def _card(title: str, element_id: str, color: str = TEXT_COLOR) -> html.Div:
    return html.Div(
        [
            html.P(title, style={"margin": "0", "fontSize": "11px", "color": "#8b949e"}),
            html.H3(
                id=element_id,
                children="-",
                style={"margin": "4px 0 0", "color": color, "fontSize": "22px"},
            ),
        ],
        style={"background": CARD_BG, "borderRadius": "8px", "padding": "14px 18px", "minWidth": "140px", "flex": "1"},
    )


def _empty_figure(title: str) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        title=title,
        template="plotly_dark",
        paper_bgcolor=DARK_BG,
        plot_bgcolor=CARD_BG,
        margin=dict(t=40, b=30),
    )
    return figure


def create_dashboard(db, cfg: dict):
    from app.agent.jarvis import propose
    from app.watchdog.actions import (
        lower_process_priority,
        request_process_termination,
        run_maintenance_script,
        switch_to_power_saver,
    )
    from app.watchdog.scheduler import get_latest, get_latest_ats

    app = dash.Dash(
        __name__,
        title="Laptop Health Guardian",
        update_title=None,
        suppress_callback_exceptions=True,
    )

    chart_minutes = cfg.get("dashboard", {}).get("chart_window_minutes", 30)
    dry_run = cfg.get("general", {}).get("dry_run", False)

    def serialize_ats_result(ats_result) -> dict:
        if not ats_result:
            return {}
        return {
            "maintenance_score": ats_result.maintenance_score,
            "verdict": ats_result.verdict,
            "top_reasons": list(ats_result.top_reasons),
            "last_evaluated": ats_result.last_evaluated,
            "fresh_scan": ats_result.fresh_scan,
        }

    app.layout = html.Div(
        style={"background": DARK_BG, "minHeight": "100vh", "fontFamily": "Segoe UI, sans-serif", "color": TEXT_COLOR},
        children=[
            dcc.Interval(id="interval", interval=3000, n_intervals=0),
            dcc.Store(id="store-telemetry"),
            dcc.Store(id="store-proposal"),
            html.Div(
                [
                    html.H1("Laptop Health Guardian", style={"margin": "0", "fontSize": "20px", "color": "#58a6ff"}),
                    html.Span(id="header-status", style={"fontSize": "13px", "marginLeft": "12px"}),
                ],
                style={"padding": "16px 24px", "borderBottom": "1px solid #30363d", "display": "flex", "alignItems": "center"},
            ),
            html.Div(
                [
                    _card("CPU Usage", "tile-cpu"),
                    _card("CPU Temp", "tile-temp"),
                    _card("RAM Usage", "tile-ram"),
                    _card("Disk Read", "tile-disk-r"),
                    _card("Disk Write", "tile-disk-w"),
                    _card("Power Plan", "tile-power"),
                    _card("Risk Score", "tile-risk"),
                ],
                style={"display": "flex", "gap": "12px", "padding": "18px 24px", "flexWrap": "wrap"},
            ),
            html.Div(
                [
                    dcc.Graph(id="chart-cpu-temp", style={"flex": "1", "minWidth": "300px"}),
                    dcc.Graph(id="chart-ram-disk", style={"flex": "1", "minWidth": "300px"}),
                ],
                style={"display": "flex", "gap": "12px", "padding": "0 24px 18px"},
            ),
            dcc.Graph(id="chart-risk", style={"padding": "0 24px 18px"}),
            html.Div(
                [
                    html.H3("Top Processes", style={"color": "#58a6ff", "marginBottom": "8px"}),
                    dash_table.DataTable(
                        id="table-procs",
                        columns=[
                            {"name": "PID", "id": "pid"},
                            {"name": "Process", "id": "name"},
                            {"name": "CPU %", "id": "cpu_pct"},
                            {"name": "RAM %", "id": "mem_pct"},
                            {"name": "Read MB", "id": "io_read_mb"},
                            {"name": "Write MB", "id": "io_write_mb"},
                            {"name": "Heat", "id": "heat_flag"},
                        ],
                        data=[],
                        style_table={"overflowX": "auto"},
                        style_header={
                            "backgroundColor": "#21262d",
                            "color": "#58a6ff",
                            "fontWeight": "bold",
                            "border": "1px solid #30363d",
                        },
                        style_cell={
                            "backgroundColor": CARD_BG,
                            "color": TEXT_COLOR,
                            "border": "1px solid #21262d",
                            "padding": "6px 10px",
                        },
                        style_data_conditional=[
                            {"if": {"filter_query": '{heat_flag} = "HOT"'}, "backgroundColor": "#3d1a1a", "color": "#ff7b72"}
                        ],
                        page_size=10,
                    ),
                ],
                style={"padding": "0 24px 18px"},
            ),
            html.Div(
                [
                    html.H3("Alerts (Last 24h)", style={"color": "#58a6ff", "marginBottom": "8px"}),
                    html.Div(id="alerts-panel"),
                ],
                style={"padding": "0 24px 18px"},
            ),
            html.Div(
                [
                    html.H3("Jarvis Recommendation", style={"color": "#58a6ff", "marginBottom": "8px"}),
                    html.Div(id="jarvis-panel"),
                    html.Button(
                        "Apply Action",
                        id="btn-apply-action",
                        n_clicks=0,
                        style={
                            "marginTop": "10px",
                            "background": "#1f6feb",
                            "color": "white",
                            "border": "none",
                            "padding": "8px 16px",
                            "borderRadius": "6px",
                            "cursor": "pointer",
                        },
                    ),
                    html.Div(id="action-result", style={"marginTop": "8px", "color": "#3fb950"}),
                ],
                style={"padding": "0 24px 18px", "background": CARD_BG, "borderRadius": "8px", "margin": "0 24px 18px"},
            ),
            html.Div(
                [
                    html.Button(
                        "Export CSV (30 min)",
                        id="btn-export",
                        n_clicks=0,
                        style={
                            "background": "#238636",
                            "color": "white",
                            "border": "none",
                            "padding": "8px 16px",
                            "borderRadius": "6px",
                            "cursor": "pointer",
                        },
                    ),
                    dcc.Download(id="download-csv"),
                ],
                style={"padding": "0 24px 24px"},
            ),
        ],
    )

    @app.callback(Output("store-telemetry", "data"), Input("interval", "n_intervals"))
    def refresh_store(_):
        telemetry, risk = get_latest()
        ats_result = get_latest_ats()
        if not telemetry:
            return {}
        return {
            "telemetry": telemetry,
            "risk": risk.__dict__ if risk else {},
            "ats": serialize_ats_result(ats_result),
        }

    @app.callback(
        Output("tile-cpu", "children"),
        Output("tile-temp", "children"),
        Output("tile-ram", "children"),
        Output("tile-disk-r", "children"),
        Output("tile-disk-w", "children"),
        Output("tile-power", "children"),
        Output("tile-risk", "children"),
        Output("header-status", "children"),
        Output("header-status", "style"),
        Input("store-telemetry", "data"),
    )
    def update_tiles(data):
        if not data:
            return ("-", "-", "-", "-", "-", "-", "-", "No data", {"color": "gray", "marginLeft": "12px"})

        telemetry = data.get("telemetry", {})
        risk = data.get("risk", {})
        cpu = telemetry.get("cpu", {})
        memory = telemetry.get("memory", {})
        disk = telemetry.get("disk", {})
        power = telemetry.get("power", {})
        score = risk.get("score", 0)
        tier = risk.get("tier", "INFO")
        temp = cpu.get("temp_celsius")
        temp_str = f"{temp:.1f} C" if temp is not None else "N/A"
        color = TIER_COLOR.get(tier, TEXT_COLOR)

        return (
            f"{cpu.get('total_pct', 0):.1f}%",
            temp_str,
            f"{memory.get('ram_pct', 0):.1f}%",
            f"{disk.get('read_mb_s', 0):.1f} MB/s",
            f"{disk.get('write_mb_s', 0):.1f} MB/s",
            power.get("plan_name", "-")[:16],
            f"{score:.0f}/100",
            f"{tier} | {risk.get('reason', '')}",
            {"color": color, "fontSize": "13px", "marginLeft": "12px", "fontWeight": "bold"},
        )

    @app.callback(
        Output("chart-cpu-temp", "figure"),
        Output("chart-ram-disk", "figure"),
        Output("chart-risk", "figure"),
        Input("interval", "n_intervals"),
    )
    def update_charts(_):
        rows = db.get_metrics(chart_minutes)
        if not rows:
            return (
                _empty_figure("CPU and Temperature"),
                _empty_figure("RAM and Disk I/O"),
                _empty_figure("Thermal Risk Score"),
            )

        frame = pd.DataFrame(rows)
        frame["time"] = pd.to_datetime(frame["ts"], unit="s")

        fig_cpu = go.Figure()
        fig_cpu.add_trace(go.Scatter(x=frame["time"], y=frame["cpu_pct"], name="CPU %", line=dict(color="#58a6ff")))
        fig_cpu.add_trace(go.Scatter(x=frame["time"], y=frame["temp_c"], name="Temp C", line=dict(color="#ff7b72")))
        fig_cpu.update_layout(
            title="CPU and Temperature",
            template="plotly_dark",
            paper_bgcolor=DARK_BG,
            plot_bgcolor=CARD_BG,
            legend=dict(bgcolor=CARD_BG),
            margin=dict(t=40, b=30),
        )

        fig_ram = go.Figure()
        fig_ram.add_trace(go.Scatter(x=frame["time"], y=frame["ram_pct"], name="RAM %", line=dict(color="#3fb950")))
        fig_ram.add_trace(go.Scatter(x=frame["time"], y=frame["disk_read"], name="Disk Read", line=dict(color="#d2a8ff")))
        fig_ram.add_trace(go.Scatter(x=frame["time"], y=frame["disk_write"], name="Disk Write", line=dict(color="#ffa657")))
        fig_ram.update_layout(
            title="RAM and Disk I/O",
            template="plotly_dark",
            paper_bgcolor=DARK_BG,
            plot_bgcolor=CARD_BG,
            legend=dict(bgcolor=CARD_BG),
            margin=dict(t=40, b=30),
        )

        fig_risk = go.Figure()
        fig_risk.add_trace(
            go.Scatter(x=frame["time"], y=frame["risk_score"], name="Risk Score", fill="tozeroy", line=dict(color="#f85149"))
        )
        fig_risk.add_hline(y=40, line_dash="dash", line_color="#F39C12", annotation_text="WARN")
        fig_risk.add_hline(y=70, line_dash="dash", line_color="#E74C3C", annotation_text="CRITICAL")
        fig_risk.update_layout(
            title="Thermal Risk Score",
            template="plotly_dark",
            paper_bgcolor=DARK_BG,
            plot_bgcolor=CARD_BG,
            yaxis=dict(range=[0, 105]),
            margin=dict(t=40, b=30),
        )

        return fig_cpu, fig_ram, fig_risk

    @app.callback(Output("table-procs", "data"), Input("store-telemetry", "data"))
    def update_table(data):
        if not data:
            return []

        rows = []
        for process in data.get("telemetry", {}).get("cpu", {}).get("top_processes", []):
            rows.append(
                {
                    "pid": process["pid"],
                    "name": process["name"],
                    "cpu_pct": process["cpu_pct"],
                    "mem_pct": process["mem_pct"],
                    "io_read_mb": process["io_read_mb"],
                    "io_write_mb": process["io_write_mb"],
                    "heat_flag": "HOT" if process["cpu_pct"] > 20 else "",
                }
            )
        return rows

    @app.callback(Output("alerts-panel", "children"), Input("interval", "n_intervals"))
    def update_alerts(_):
        alerts = db.get_alerts(24)
        if not alerts:
            return html.P("No alerts in the last 24 hours.", style={"color": "#3fb950"})

        items = []
        for alert in alerts[:15]:
            timestamp = datetime.fromtimestamp(alert["ts"]).strftime("%H:%M:%S")
            color = TIER_COLOR.get(alert["tier"], TEXT_COLOR)
            items.append(
                html.Div(
                    f"[{timestamp}] {alert['tier']} - {alert['message']}",
                    style={"padding": "4px 0", "color": color, "fontSize": "13px"},
                )
            )
        return items

    @app.callback(
        Output("jarvis-panel", "children"),
        Output("store-proposal", "data"),
        Input("store-telemetry", "data"),
    )
    def update_jarvis(data):
        if not data:
            return html.P("Waiting for data..."), {}

        telemetry = data.get("telemetry", {})
        ats_result = data.get("ats", {})
        proposal = propose(telemetry, cfg, ats_result=ats_result)
        color = "#3fb950" if proposal["action"] == "no_action" else "#f0883e"
        ats_line = "ATS: waiting for evaluation."
        if ats_result:
            ats_line = (
                f"ATS: {ats_result.get('maintenance_score', 0):.1f}/100 | "
                f"{ats_result.get('verdict', 'CLEAN')}"
            )

        return (
            html.Div(
                [
                    html.P(
                        f"Action: {proposal['action']} | Target: {proposal['target']}",
                        style={"fontWeight": "bold", "color": color},
                    ),
                    html.P(f"Reason: {proposal['reason']}", style={"fontSize": "13px"}),
                    html.P(
                        f"Confidence: {proposal['confidence'] * 100:.0f}% | "
                        f"Requires confirmation: {proposal['safety']['requires_confirmation']}",
                        style={"fontSize": "12px", "color": "#8b949e"},
                    ),
                    html.P(ats_line, style={"fontSize": "12px", "color": "#8b949e"}),
                ]
            ),
            proposal,
        )

    @app.callback(
        Output("action-result", "children"),
        Input("btn-apply-action", "n_clicks"),
        State("store-proposal", "data"),
        prevent_initial_call=True,
    )
    def apply_jarvis_action(_n_clicks, proposal):
        if not proposal or proposal.get("action") == "no_action":
            return "Nothing to apply."

        action = proposal.get("action")
        target = proposal.get("target", "")
        requires_confirmation = proposal.get("safety", {}).get("requires_confirmation", True)
        destructive = proposal.get("safety", {}).get("is_destructive", False)

        if destructive and requires_confirmation:
            return f"Action '{action}' on '{target}' requires confirmation."

        telemetry, _risk = get_latest()
        processes = telemetry.get("cpu", {}).get("top_processes", [])

        if action == "switch_power_saver":
            return "Switched to Power Saver." if switch_to_power_saver(dry_run) else "Failed to switch power plan."

        if action == "lower_priority":
            allowlist = cfg.get("process_allowlist", {}).get("priority_lower", [])
            for process in processes[:3]:
                if process["name"].lower() == target.lower():
                    lower_process_priority(process["pid"], process["name"], allowlist, dry_run)
                    return f"Priority lowered for {target}."
            return f"{target} not found or not in the allowlist."

        if action == "propose_terminate":
            allowlist = cfg.get("process_allowlist", {}).get("kill_candidates", [])
            for process in processes[:3]:
                if process["name"].lower() == target.lower():
                    request_process_termination(process["pid"], process["name"], allowlist, dry_run)
                    return f"Termination request issued for {target}."
            return f"{target} not found or not in the allowlist."

        if action == "run_maintenance_script":
            script_path = cfg.get("ats", {}).get("script_path", "")
            if run_maintenance_script(script_path, dry_run):
                return "ATS maintenance script started."
            return f"Failed to start ATS maintenance script: {script_path}"

        return f"Action '{action}' is noted but no executor is defined."

    @app.callback(Output("download-csv", "data"), Input("btn-export", "n_clicks"), prevent_initial_call=True)
    def export_csv(_n_clicks):
        csv_data = db.export_csv(30)
        return {"content": csv_data, "filename": "guardian_export.csv"}

    return app
