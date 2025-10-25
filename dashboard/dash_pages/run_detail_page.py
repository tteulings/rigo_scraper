"""Run Detail Page"""

import os
import json
from typing import Dict, Any
from dash import html, dcc
import dash_bootstrap_components as dbc
from dashboard.dash_helpers import add_source_to_run
from dashboard.dash_components import create_sidebar, source_chip


def create_run_detail_page(run: Dict[str, Any]):
    # Add source information to run
    run = add_source_to_run(run)

    # Load config (fast)
    config = {}
    config_path = os.path.join(run["run_path"], "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass
    gemeenten = ", ".join(config.get("gemeenten", [])) or "Onbekend"

    # Get summary metrics from run_status.json and config
    status_path = os.path.join(run["run_path"], "run_status.json")
    total_records = "-"
    unique_listings = "-"
    period_str = "-"

    if os.path.exists(status_path):
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                status_data = json.load(f)
                progress = status_data.get("progress", {})
                total_records = progress.get("total_scans", "-")
                unique_listings = progress.get("total_listings", "-")
        except Exception:
            pass

    # Get period from config
    if config:
        period_start = config.get("period_start", "")
        period_end = config.get("period_end", "")
        if period_start and period_end:
            period_str = f"{period_start} tot {period_end}"

    # Check if run is still active (running/failed) for auto-refresh
    run_status = run.get("status", "completed")
    is_active = run_status in ["running", "failed", "pending"]

    # Check if data files exist
    run_path = run.get("run_path")
    has_data = False
    if run_path and os.path.exists(run_path):
        excel_files = [
            f
            for f in os.listdir(run_path)
            if f.endswith(".xlsx") and not f.startswith("~$")
        ]
        parquet_path = os.path.join(run_path, "data.parquet")
        has_data = bool(excel_files) or os.path.exists(parquet_path)

    return html.Div(
        [
            create_sidebar("/dashboard"),
            html.Div(
                [
                    dcc.Store(
                        id="current-run",
                        data={
                            "run_path": run.get("run_path"),
                            "gemeenten": config.get("gemeenten", []),
                            "status": run_status,
                        },
                    ),
                    # Auto-refresh interval for running/failed runs
                    dcc.Interval(
                        id="log-refresh-interval",
                        interval=3000,  # 3 seconds
                        n_intervals=0,
                        disabled=not is_active,  # Only active for running/failed runs
                    ),
                    # Header with back button
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Button(
                                        [
                                            html.I(
                                                "arrow_back",
                                                className="material-icons",
                                                style={
                                                    "marginRight": "8px",
                                                    "fontSize": "18px",
                                                },
                                            ),
                                            html.Span("Terug naar Overzicht"),
                                        ],
                                        id="back-btn",
                                        n_clicks=0,
                                        style={
                                            "background": "#10357e",
                                            "color": "white",
                                            "border": "none",
                                            "padding": "12px 20px",
                                            "borderRadius": "6px",
                                            "cursor": "pointer",
                                            "display": "flex",
                                            "alignItems": "center",
                                            "fontSize": "14px",
                                            "fontWeight": "500",
                                        },
                                    ),
                                ],
                                style={"marginBottom": "20px"},
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.H1(
                                                        gemeenten,
                                                        style={
                                                            "margin": 0,
                                                            "color": "#10357e",
                                                            "fontSize": "32px",
                                                            "fontWeight": "bold",
                                                        },
                                                    ),
                                                    source_chip(
                                                        run.get("source", "airbnb"),
                                                        show_label=True,
                                                    ),
                                                ],
                                                style={
                                                    "display": "flex",
                                                    "alignItems": "center",
                                                    "gap": "16px",
                                                    "marginBottom": "8px",
                                                },
                                            ),
                                            html.Div(
                                                run.get("run_name", ""),
                                                style={
                                                    "color": "#888",
                                                    "fontSize": "14px",
                                                    "marginTop": "8px",
                                                },
                                            ),
                                        ],
                                        style={"flex": "1"},
                                    ),
                                    dbc.DropdownMenu(
                                        [
                                            dbc.DropdownMenuItem(
                                                [
                                                    html.I(
                                                        "folder_zip",
                                                        className="material-icons",
                                                        style={
                                                            "marginRight": "8px",
                                                            "fontSize": "18px",
                                                            "verticalAlign": "middle",
                                                        },
                                                    ),
                                                    "Alles (ZIP)",
                                                ],
                                                href=f"/download_zip/{run.get('run_name', '')}",
                                                external_link=True,
                                            ),
                                            dbc.DropdownMenuItem(divider=True),
                                            dbc.DropdownMenuItem(
                                                "Data Bestanden",
                                                header=True,
                                                style={
                                                    "fontWeight": "600",
                                                    "color": "#10357e",
                                                    "fontSize": "12px",
                                                },
                                            ),
                                            dbc.DropdownMenuItem(
                                                [
                                                    html.I(
                                                        "table_chart",
                                                        className="material-icons",
                                                        style={
                                                            "marginRight": "8px",
                                                            "fontSize": "18px",
                                                            "verticalAlign": "middle",
                                                        },
                                                    ),
                                                    "Excel (.xlsx)",
                                                ],
                                                href=f"/download/excel?run={run.get('run_name', '')}",
                                                external_link=True,
                                            ),
                                            dbc.DropdownMenuItem(
                                                [
                                                    html.I(
                                                        "storage",
                                                        className="material-icons",
                                                        style={
                                                            "marginRight": "8px",
                                                            "fontSize": "18px",
                                                            "verticalAlign": "middle",
                                                        },
                                                    ),
                                                    "Parquet (.parquet)",
                                                ],
                                                href=f"/download/parquet?run={run.get('run_name', '')}",
                                                external_link=True,
                                            ),
                                            dbc.DropdownMenuItem(
                                                [
                                                    html.I(
                                                        "insert_drive_file",
                                                        className="material-icons",
                                                        style={
                                                            "marginRight": "8px",
                                                            "fontSize": "18px",
                                                            "verticalAlign": "middle",
                                                        },
                                                    ),
                                                    "CSV (.csv)",
                                                ],
                                                href=f"/download/csv?run={run.get('run_name', '')}",
                                                external_link=True,
                                            ),
                                            dbc.DropdownMenuItem(divider=True),
                                            dbc.DropdownMenuItem(
                                                "Visualisaties & Logs",
                                                header=True,
                                                style={
                                                    "fontWeight": "600",
                                                    "color": "#10357e",
                                                    "fontSize": "12px",
                                                },
                                            ),
                                            dbc.DropdownMenuItem(
                                                [
                                                    html.I(
                                                        "map",
                                                        className="material-icons",
                                                        style={
                                                            "marginRight": "8px",
                                                            "fontSize": "18px",
                                                            "verticalAlign": "middle",
                                                        },
                                                    ),
                                                    "Kaart (HTML)",
                                                ],
                                                href=f"/download_file/{run.get('run_name', '')}/map.html",
                                                external_link=True,
                                            ),
                                            dbc.DropdownMenuItem(
                                                [
                                                    html.I(
                                                        "show_chart",
                                                        className="material-icons",
                                                        style={
                                                            "marginRight": "8px",
                                                            "fontSize": "18px",
                                                            "verticalAlign": "middle",
                                                        },
                                                    ),
                                                    "Grafiek (PNG)",
                                                ],
                                                href=f"/download_file/{run.get('run_name', '')}/timeline_availability.png",
                                                external_link=True,
                                            ),
                                            dbc.DropdownMenuItem(
                                                [
                                                    html.I(
                                                        "settings",
                                                        className="material-icons",
                                                        style={
                                                            "marginRight": "8px",
                                                            "fontSize": "18px",
                                                            "verticalAlign": "middle",
                                                        },
                                                    ),
                                                    "Configuratie (JSON)",
                                                ],
                                                href=f"/download_file/{run.get('run_name', '')}/config.json",
                                                external_link=True,
                                            ),
                                            dbc.DropdownMenuItem(
                                                [
                                                    html.I(
                                                        "description",
                                                        className="material-icons",
                                                        style={
                                                            "marginRight": "8px",
                                                            "fontSize": "18px",
                                                            "verticalAlign": "middle",
                                                        },
                                                    ),
                                                    "Log (TXT)",
                                                ],
                                                href=f"/download_file/{run.get('run_name', '')}/run.log",
                                                external_link=True,
                                            ),
                                        ],
                                        label=[
                                            html.I(
                                                "download",
                                                className="material-icons",
                                                style={
                                                    "marginRight": "8px",
                                                    "fontSize": "20px",
                                                },
                                            ),
                                            "Download",
                                        ],
                                        color="warning",
                                        size="sm",
                                        style={
                                            "fontSize": "13px",
                                            "fontWeight": "500",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "20px",
                                },
                            ),
                        ],
                        style={"marginBottom": "32px"},
                    ),
                    # Summary metrics
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        "Totaal Metingen",
                                        style={
                                            "color": "#888",
                                            "fontSize": "13px",
                                            "marginBottom": "4px",
                                        },
                                    ),
                                    html.H3(
                                        f"{total_records:,}"
                                        if isinstance(total_records, int)
                                        else str(total_records),
                                        style={"margin": 0, "color": "#10357e"},
                                    ),
                                ],
                                style={
                                    "background": "white",
                                    "border": "1px solid #e0e0e0",
                                    "borderRadius": "8px",
                                    "padding": "20px",
                                },
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        "Unieke Listings",
                                        style={
                                            "color": "#888",
                                            "fontSize": "13px",
                                            "marginBottom": "4px",
                                        },
                                    ),
                                    html.H3(
                                        f"{unique_listings:,}"
                                        if isinstance(unique_listings, int)
                                        else str(unique_listings),
                                        style={"margin": 0, "color": "#0288d1"},
                                    ),
                                ],
                                style={
                                    "background": "white",
                                    "border": "1px solid #e0e0e0",
                                    "borderRadius": "8px",
                                    "padding": "20px",
                                },
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Div(
                                                        "Meetperiode",
                                                        style={
                                                            "color": "#888",
                                                            "fontSize": "13px",
                                                            "marginBottom": "4px",
                                                        },
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.H3(
                                                                period_str,
                                                                style={
                                                                    "margin": 0,
                                                                    "color": "#2e7d32",
                                                                    "fontSize": "17px",
                                                                    "display": "inline-block",
                                                                },
                                                            ),
                                                            html.I(
                                                                "expand_more",
                                                                id="period-expand-icon",
                                                                className="material-icons",
                                                                style={
                                                                    "marginLeft": "8px",
                                                                    "fontSize": "24px",
                                                                    "color": "#2e7d32",
                                                                    "verticalAlign": "middle",
                                                                    "transition": "transform 0.2s ease",
                                                                    "transform": "rotate(0deg)",
                                                                },
                                                            ),
                                                        ],
                                                        style={
                                                            "display": "flex",
                                                            "alignItems": "center",
                                                            "justifyContent": "space-between",
                                                        },
                                                    ),
                                                ],
                                                id="period-toggle",
                                                n_clicks=0,
                                                style={
                                                    "cursor": "pointer",
                                                    "userSelect": "none",
                                                },
                                            ),
                                        ],
                                    ),
                                ],
                                style={
                                    "background": "white",
                                    "border": "1px solid #e0e0e0",
                                    "borderRadius": "8px",
                                    "padding": "20px",
                                    "gridColumn": "span 2",
                                    "transition": "all 0.2s ease",
                                    "boxShadow": "0 1px 3px rgba(0,0,0,0.05)",
                                },
                            ),
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "repeat(4, 1fr)",
                            "gap": "16px",
                            "marginBottom": "24px",
                        },
                    ),
                    # Meetmomenten collapsible section - appears as dropdown from card
                    dbc.Collapse(
                        html.Div(
                            [
                                dcc.Loading(
                                    id="loading-meetmomenten",
                                    type="default",
                                    children=html.Div(id="meetmomenten-content"),
                                ),
                            ],
                            style={
                                "padding": "20px",
                                "background": "#f8f9fa",
                                "borderRadius": "0 0 8px 8px",
                                "border": "1px solid #e0e0e0",
                                "borderTop": "1px dashed #d0d0d0",
                            },
                        ),
                        id="meetmomenten-collapse",
                        is_open=False,
                        style={
                            "marginTop": "-8px",
                            "marginBottom": "24px",
                        },
                    ),
                    # Tabs (default to Log tab for running jobs, Overview when completed with data)
                    dcc.Tabs(
                        id="detail-tabs",
                        value="tab-log"
                        if (run_status in ["running", "pending"] or not has_data)
                        else "tab-overview",
                        children=[
                            dcc.Tab(
                                label="Overzicht",
                                value="tab-overview",
                                disabled=not has_data,
                                style={
                                    "padding": "12px 24px",
                                    "opacity": 0.5 if not has_data else 1,
                                    "cursor": "not-allowed"
                                    if not has_data
                                    else "pointer",
                                },
                                selected_style={
                                    "padding": "12px 24px",
                                    "borderTop": "3px solid #10357e",
                                    "fontWeight": "bold",
                                },
                            ),
                            dcc.Tab(
                                label="Data",
                                value="tab-data",
                                disabled=not has_data,
                                style={
                                    "padding": "12px 24px",
                                    "opacity": 0.5 if not has_data else 1,
                                    "cursor": "not-allowed"
                                    if not has_data
                                    else "pointer",
                                },
                                selected_style={
                                    "padding": "12px 24px",
                                    "borderTop": "3px solid #10357e",
                                    "fontWeight": "bold",
                                },
                            ),
                            dcc.Tab(
                                label="Logs",
                                value="tab-log",
                                style={"padding": "12px 24px"},
                                selected_style={
                                    "padding": "12px 24px",
                                    "borderTop": "3px solid #10357e",
                                    "fontWeight": "bold",
                                },
                            ),
                            dcc.Tab(
                                label="Configuratie",
                                value="tab-config",
                                style={"padding": "12px 24px"},
                                selected_style={
                                    "padding": "12px 24px",
                                    "borderTop": "3px solid #10357e",
                                    "fontWeight": "bold",
                                },
                            ),
                        ],
                        style={"marginBottom": "24px"},
                    ),
                    # Tab content (loaded dynamically by callback)
                    html.Div(id="tab-content"),
                ],
                style={
                    "marginLeft": "280px",
                    "padding": "32px",
                    "minHeight": "100vh",
                    "background": "#f5f5f5",
                },
            ),
        ]
    )
