import json

import dash
import plotly.graph_objs as go
from dash import dash_table, dcc, html
from dash.dependencies import Input, Output


def _safe_json(value, fallback):
    try:
        return json.loads(value) if isinstance(value, str) else value
    except Exception:
        return fallback


def _status_text(latest):
    temp_value = float(latest["temp_c"])
    cpu_value = float(latest["cpu_percent"])
    ram_value = float(latest["ram_percent"])
    risk_value = float(latest["risk_score"])
    temp_str = f"{temp_value:.1f} C" if temp_value > 0 else "Unavailable (WMI blocked/unexposed)"
    return f"Temp: {temp_str} | CPU: {cpu_value:.1f}% | RAM: {ram_value:.1f}% | Risk: {risk_value:.0f}"


def create_dashboard(db, config):
    app = dash.Dash(__name__)
    history_points = int(config["system"]["history_points"])
    refresh_ms = int(config["dashboard"]["refresh_ms"])
    risk_critical = int(config["thresholds"]["risk_score_critical"])
    temp_warn = float(config["thresholds"]["temp_warn"])
    temp_critical = float(config["thresholds"]["temp_critical"])

    app.layout = html.Div(
        style={"backgroundColor": "#0e1117", "color": "white", "fontFamily": "Segoe UI", "padding": "20px"},
        children=[
            html.H1("Laptop Health Guardian"),
            html.Div(id="live-status", style={"fontSize": "20px", "marginBottom": "12px"}),
            dcc.Graph(id="metrics-graph"),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"},
                children=[
                    html.Div(
                        style={"backgroundColor": "#161b22", "padding": "12px", "borderRadius": "8px"},
                        children=[
                            html.H3("Top CPU Processes"),
                            html.Pre(id="top-processes", style={"whiteSpace": "pre-wrap", "margin": 0}),
                        ],
                    ),
                    html.Div(
                        style={"backgroundColor": "#161b22", "padding": "12px", "borderRadius": "8px"},
                        children=[
                            html.H3("Recent Actions"),
                            dash_table.DataTable(
                                id="actions-table",
                                columns=[
                                    {"name": "Timestamp", "id": "timestamp"},
                                    {"name": "Risk", "id": "risk_score"},
                                    {"name": "Action", "id": "action"},
                                    {"name": "Target", "id": "target"},
                                    {"name": "Outcome", "id": "outcome"},
                                    {"name": "Reason", "id": "reason"},
                                ],
                                data=[],
                                style_table={"overflowX": "auto"},
                                style_cell={
                                    "backgroundColor": "#0e1117",
                                    "color": "white",
                                    "fontSize": "12px",
                                    "textAlign": "left",
                                    "maxWidth": "280px",
                                    "whiteSpace": "normal",
                                },
                                style_header={
                                    "backgroundColor": "#1f2937",
                                    "fontWeight": "bold",
                                },
                            ),
                        ],
                    ),
                ],
            ),
            dcc.Interval(id="interval-component", interval=refresh_ms, n_intervals=0),
        ],
    )

    @app.callback(
        [
            Output("live-status", "children"),
            Output("metrics-graph", "figure"),
            Output("top-processes", "children"),
            Output("actions-table", "data"),
        ],
        [Input("interval-component", "n_intervals")],
    )
    def update_dash(_):
        df = db.get_recent(history_points)
        if df.empty:
            fig = go.Figure()
            fig.update_layout(template="plotly_dark")
            return "Awaiting telemetry data...", fig, "No process data yet.", []

        df = df.iloc[::-1]
        latest = df.iloc[-1]
        status = _status_text(latest)

        top_processes = _safe_json(latest["top_processes"], [])
        if top_processes:
            process_lines = []
            for proc in top_processes:
                name = str(proc.get("name", "unknown"))
                cpu = float(proc.get("cpu", 0.0))
                process_lines.append(f"- {name}: {cpu:.1f}% CPU")
            top_process_text = "\n".join(process_lines)
        else:
            top_process_text = "No process data available."

        fig = go.Figure()
        fig.add_trace(go.Scatter(y=df["cpu_percent"], name="CPU %", line={"color": "#00BFFF"}))
        fig.add_trace(go.Scatter(y=df["ram_percent"], name="RAM %", line={"color": "#8A2BE2"}))
        if float(latest["temp_c"]) > 0:
            fig.add_trace(go.Scatter(y=df["temp_c"], name="Temp C", line={"color": "#FF4500"}))
            fig.add_hline(y=temp_warn, line_dash="dash", line_color="#FFA500", annotation_text="Temp Warn")
            fig.add_hline(y=temp_critical, line_dash="dot", line_color="#FF0000", annotation_text="Temp Critical")
        fig.add_trace(go.Scatter(y=df["risk_score"], name="Risk Score", line={"color": "#FFD700", "dash": "dot"}))
        fig.add_hline(y=risk_critical, line_dash="dash", line_color="#F87171", annotation_text="Risk Critical")
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            margin={"l": 20, "r": 20, "t": 30, "b": 20},
            legend={"orientation": "h"},
            yaxis={"range": [0, 100]},
        )

        actions_df = db.get_recent_actions(20)
        if actions_df.empty:
            action_rows = []
        else:
            actions_df = actions_df.fillna("")
            rows = []
            for _, row in actions_df.iterrows():
                details = _safe_json(row.get("details", "{}"), {})
                reason = str(row.get("reason", ""))
                if details.get("reasons"):
                    reason = f"{reason} | flags={','.join(details['reasons'])}"
                rows.append(
                    {
                        "timestamp": str(row.get("timestamp", "")),
                        "risk_score": f"{float(row.get('risk_score', 0.0)):.0f}",
                        "action": str(row.get("action", "")),
                        "target": str(row.get("target", "")),
                        "outcome": str(row.get("outcome", "")),
                        "reason": reason,
                    }
                )
            action_rows = rows

        return status, fig, top_process_text, action_rows

    return app

