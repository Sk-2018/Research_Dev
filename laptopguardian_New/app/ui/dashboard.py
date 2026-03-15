@'
"""
Plotly Dash dashboard for Laptop Health Guardian.
Binds to localhost:8050. Auto-refreshes every 3 seconds.
"""
import dash, json, time, logging
from dash import dcc, html, dash_table, Input, Output, State, ctx
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

TIER_COLOR = {"INFO": "#2ECC71", "WARN": "#F39C12", "CRITICAL": "#E74C3C"}
DARK_BG    = "#0d1117"
CARD_BG    = "#161b22"
TEXT_COLOR = "#c9d1d9"


def _card(title: str, id_val: str, color: str = TEXT_COLOR) -> html.Div:
    return html.Div([
        html.P(title, style={"margin": "0", "fontSize": "11px", "color": "#8b949e"}),
        html.H3(id=id_val, children="—", style={"margin": "4px 0 0", "color": color, "fontSize": "22px"}),
    ], style={"background": CARD_BG, "borderRadius": "8px", "padding": "14px 18px",
              "minWidth": "140px", "flex": "1"})


def create_dashboard(db, cfg: dict):
    from app.watchdog.scheduler import get_latest
    from app.agent.jarvis import propose
    from app.watchdog.actions import (
        switch_to_power_saver, lower_process_priority,
        request_process_termination
    )

    app = dash.Dash(
        __name__,
        title="🛡️ Laptop Health Guardian",
        update_title=None,
        suppress_callback_exceptions=True,
    )

    chart_minutes = cfg.get("dashboard", {}).get("chart_window_minutes", 30)
    dry_run       = cfg.get("general", {}).get("dry_run", False)

    app.layout = html.Div(style={"background": DARK_BG, "minHeight": "100vh",
                                  "fontFamily": "Segoe UI, sans-serif", "color": TEXT_COLOR}, children=[
        dcc.Interval(id="interval", interval=3000, n_intervals=0),
        dcc.Store(id="store-telemetry"),
        dcc.Store(id="store-confirm-pid"),

        # Header
        html.Div([
            html.H1("🛡️ Laptop Health Guardian",
                    style={"margin": "0", "fontSize": "20px", "color": "#58a6ff"}),
            html.Span(id="header-status", style={"fontSize": "13px", "marginLeft": "12px"}),
        ], style={"padding": "16px 24px", "borderBottom": "1px solid #30363d",
                   "display": "flex", "alignItems": "center"}),

        # Live tiles
        html.Div([
            _card("CPU Usage", "tile-cpu"),
            _card("CPU Temp", "tile-temp"),
            _card("RAM Usage", "tile-ram"),
            _card("Disk Read", "tile-disk-r"),
            _card("Disk Write", "tile-disk-w"),
            _card("Power Plan", "tile-power"),
            _card("Risk Score", "tile-risk"),
        ], style={"display": "flex", "gap": "12px", "padding": "18px 24px",
                   "flexWrap": "wrap"}),

        # Charts
        html.Div([
            dcc.Graph(id="chart-cpu-temp", style={"flex": "1", "minWidth": "300px"}),
            dcc.Graph(id="chart-ram-disk", style={"flex": "1", "minWidth": "300px"}),
        ], style={"display": "flex", "gap": "12px", "padding": "0 24px 18px"}),

        dcc.Graph(id="chart-risk", style={"padding": "0 24px 18px"}),

        # Top processes table
        html.Div([
            html.H3("🔥 Top Processes", style={"color": "#58a6ff", "marginBottom": "8px"}),
            dash_table.DataTable(
                id="table-procs",
                columns=[
                    {"name": "PID",     "id": "pid"},
                    {"name": "Process", "id": "name"},
                    {"name": "CPU %",   "id": "cpu_pct"},
                    {"name": "RAM %",   "id": "mem_pct"},
                    {"name": "Read MB", "id": "io_read_mb"},
                    {"name": "Write MB","id": "io_write_mb"},
                    {"name": "⚠️ Heat",  "id": "heat_flag"},
                ],
                data=[],
                style_table={"overflowX": "auto"},
                style_header={"backgroundColor": "#21262d", "color": "#58a6ff",
                               "fontWeight": "bold", "border": "1px solid #30363d"},
                style_cell={"backgroundColor": CARD_BG, "color": TEXT_COLOR,
                             "border": "1px solid #21262d", "padding": "6px 10px"},
                style_data_conditional=[
                    {"if": {"filter_query": '{heat_flag} = "🔥"'},
                     "backgroundColor": "#3d1a1a", "color": "#ff7b72"},
                ],
                page_size=10,
            ),
        ], style={"padding": "0 24px 18px"}),

        # Alerts panel
        html.Div([
            html.H3("🚨 Alerts (Last 24h)", style={"color": "#58a6ff", "marginBottom": "8px"}),
            html.Div(id="alerts-panel"),
        ], style={"padding": "0 24px 18px"}),

        # Jarvis panel
        html.Div([
            html.H3("🤖 Jarvis Recommendation", style={"color": "#58a6ff", "marginBottom": "8px"}),
            html.Div(id="jarvis-panel"),
            html.Button("▶ Apply Action", id="btn-apply-action", n_clicks=0,
                        style={"marginTop": "10px", "background": "#1f6feb",
                               "color": "white", "border": "none",
                               "padding": "8px 16px", "borderRadius": "6px",
                               "cursor": "pointer"}),
            html.Div(id="action-result", style={"marginTop": "8px", "color": "#3fb950"}),
        ], style={"padding": "0 24px 18px", "background": CARD_BG,
                   "borderRadius": "8px", "margin": "0 24px 18px"}),

        # Export
        html.Div([
            html.Button("📥 Export CSV (30 min)", id="btn-export", n_clicks=0,
                        style={"background": "#238636", "color": "white",
                               "border": "none", "padding": "8px 16px",
                               "borderRadius": "6px", "cursor": "pointer"}),
            dcc.Download(id="download-csv"),
        ], style={"padding": "0 24px 24px"}),
    ])

    # ───────────────────────────── CALLBACKS ─────────────────────────────

    @app.callback(
        Output("store-telemetry", "data"),
        Input("interval", "n_intervals"),
    )
    def refresh_store(_):
        tel, risk = get_latest()
        if not tel:
            return {}
        return {"telemetry": tel, "risk": risk.__dict__ if risk else {}}

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
            return ("—",) * 7 + ("No data", {"color": "gray", "marginLeft": "12px"})
        t  = data.get("telemetry", {})
        r  = data.get("risk", {})
        cpu   = t.get("cpu", {})
        mem   = t.get("memory", {})
        disk  = t.get("disk", {})
        pwr   = t.get("power", {})
        score = r.get("score", 0)
        tier  = r.get("tier", "INFO")
        temp  = cpu.get("temp_celsius")
        temp_str = f"{temp:.1f}°C" if temp else "N/A"
        color = TIER_COLOR.get(tier, TEXT_COLOR)
        return (
            f"{cpu.get('total_pct', 0):.1f}%",
            temp_str,
            f"{mem.get('ram_pct', 0):.1f}%",
            f"{disk.get('read_mb_s', 0):.1f} MB/s",
            f"{disk.get('write_mb_s', 0):.1f} MB/s",
            pwr.get("plan_name", "—")[:16],
            f"{score:.0f}/100",
            f"● {tier}  |  {r.get('reason', '')}",
            {"color": color, "fontSize": "13px", "marginLeft": "12px", "fontWeight": "bold"},
        )

    @app.callback(
        Output("chart-cpu-temp", "figure"),
        Output("chart-ram-disk", "figure"),
        Output("chart-risk",     "figure"),
        Input("interval", "n_intervals"),
    )
    def update_charts(_):
        rows = db.get_metrics(chart_minutes)
        empty_layout = dict(template="plotly_dark", paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG)
        if not rows:
            fig1 = go.Figure(layout={**empty_layout, "title": "CPU & Temperature"})
            fig2 = go.Figure(layout={**empty_layout, "title": "RAM & Disk IO"})
            fig3 = go.Figure(layout={**empty_layout, "title": "Thermal Risk Score"})
            return fig1, fig2, fig3

        df = pd.DataFrame(rows)
        df["time"] = pd.to_datetime(df["ts"], unit="s")

        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df["time"], y=df["cpu_pct"],  name="CPU %",   line=dict(color="#58a6ff")))
        fig1.add_trace(go.Scatter(x=df["time"], y=df["temp_c"],   name="Temp °C", line=dict(color="#ff7b72")))
        fig1.update_layout(title="CPU % & Temperature", template="plotly_dark",
                           paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
                           legend=dict(bgcolor=CARD_BG), margin=dict(t=40, b=30))

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df["time"], y=df["ram_pct"],    name="RAM %",      line=dict(color="#3fb950")))
        fig2.add_trace(go.Scatter(x=df["time"], y=df["disk_read"],  name="Disk Read",  line=dict(color="#d2a8ff")))
        fig2.add_trace(go.Scatter(x=df["time"], y=df["disk_write"], name="Disk Write", line=dict(color="#ffa657")))
        fig2.update_layout(title="RAM & Disk IO (MB/s)", template="plotly_dark",
                           paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
                           legend=dict(bgcolor=CARD_BG), margin=dict(t=40, b=30))

        tier_map = {"INFO": 0, "WARN": 1, "CRITICAL": 2}
        df["tier_num"] = df["risk_tier"].map(tier_map).fillna(0)
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=df["time"], y=df["risk_score"], name="Risk Score",
                                  fill="tozeroy", line=dict(color="#f85149")))
        fig3.add_hline(y=40, line_dash="dash", line_color="#F39C12", annotation_text="WARN")
        fig3.add_hline(y=70, line_dash="dash", line_color="#E74C3C", annotation_text="CRITICAL")
        fig3.update_layout(title="Thermal Risk Score (0–100)", template="plotly_dark",
                           paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
                           yaxis=dict(range=[0, 105]), margin=dict(t=40, b=30))
        return fig1, fig2, fig3

    @app.callback(
        Output("table-procs", "data"),
        Input("store-telemetry", "data"),
    )
    def update_table(data):
        if not data:
            return []
        procs = data.get("telemetry", {}).get("cpu", {}).get("top_processes", [])
        rows = []
        for p in procs:
            rows.append({
                "pid":       p["pid"],
                "name":      p["name"],
                "cpu_pct":   p["cpu_pct"],
                "mem_pct":   p["mem_pct"],
                "io_read_mb": p["io_read_mb"],
                "io_write_mb": p["io_write_mb"],
                "heat_flag": "🔥" if p["cpu_pct"] > 20 else "",
            })
        return rows

    @app.callback(
        Output("alerts-panel", "children"),
        Input("interval", "n_intervals"),
    )
    def update_alerts(_):
        alerts = db.get_alerts(24)
        if not alerts:
            return html.P("No alerts in last 24h. System nominal. ✅",
                          style={"color": "#3fb950"})
        items = []
        for a in alerts[:15]:
            ts = datetime.fromtimestamp(a["ts"]).strftime("%H:%M:%S")
            color = TIER_COLOR.get(a["tier"], TEXT_COLOR)
            items.append(html.Div(
                f"[{ts}] {a['tier']} — {a['message']}",
                style={"padding": "4px 0", "color": color, "fontSize": "13px"}
            ))
        return items

    @app.callback(
        Output("jarvis-panel",  "children"),
        Output("store-confirm-pid", "data"),
        Input("store-telemetry", "data"),
    )
    def update_jarvis(data):
        if not data:
            return html.P("Waiting for data..."), {}
        t = data.get("telemetry", {})
        proposal = propose(t, cfg)
        color = "#3fb950" if proposal["action"] == "no_action" else "#f0883e"
        return (
            html.Div([
                html.P(f"Action: {proposal['action']}   Target: {proposal['target']}",
                       style={"fontWeight": "bold", "color": color}),
                html.P(f"Reason: {proposal['reason']}",      style={"fontSize": "13px"}),
                html.P(f"Confidence: {proposal['confidence']*100:.0f}%  |  "
                       f"Requires confirmation: {proposal['safety']['requires_confirmation']}",
                       style={"fontSize": "12px", "color": "#8b949e"}),
            ]),
            proposal,
        )

    @app.callback(
        Output("action-result", "children"),
        Input("btn-apply-action", "n_clicks"),
        State("store-confirm-pid", "data"),
        prevent_initial_call=True,
    )
    def apply_jarvis_action(n_clicks, proposal):
        if not proposal or proposal.get("action") == "no_action":
            return "Nothing to apply."
        action = proposal.get("action")
        target = proposal.get("target", "")
        requires_conf = proposal.get("safety", {}).get("requires_confirmation", True)
        destructive   = proposal.get("safety", {}).get("is_destructive", False)
        if destructive and requires_conf:
            return f"⚠️ Action '{action}' on '{target}' requires admin confirmation. Logged for review."
        if action == "switch_power_saver":
            ok = switch_to_power_saver(dry_run)
            return "✅ Switched to Power Saver." if ok else "❌ Failed to switch power plan."
        if action == "lower_priority":
            allowlist = cfg.get("process_allowlist", {}).get("priority_lower", [])
            _, risk = get_latest()
            tel, _ = get_latest()
            procs = tel.get("cpu", {}).get("top_processes", [])
            ok_any = False
            for p in procs[:3]:
                if p["name"].lower() == target.lower():
                    lower_process_priority(p["pid"], p["name"], allowlist, dry_run)
                    ok_any = True
            return f"✅ Priority lowered for {target}." if ok_any else f"⚠️ {target} not found or not in allowlist."
        return f"ℹ️ Action '{action}' noted but no executor matched."

    @app.callback(
        Output("download-csv", "data"),
        Input("btn-export", "n_clicks"),
        prevent_initial_call=True,
    )
    def export_csv(n_clicks):
        csv_str = db.export_csv(30)
        return dict(content=csv_str, filename="guardian_export.csv")

    return app
'@ | Out-File -FilePath "app\ui\dashboard.py" -Encoding utf8
