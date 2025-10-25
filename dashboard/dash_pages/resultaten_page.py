"""Resultaten (Dashboard Overview) Page"""

from datetime import datetime
from typing import List, Dict, Any
from dash import html, dcc
import dash_bootstrap_components as dbc
from dashboard.dash_helpers import load_run_preview, add_source_to_run
from dashboard.dash_components import create_sidebar, status_badge, source_chip


def create_resultaten_page(runs: List[Dict[str, Any]]):
    print(f"DEBUG dashboard_view: Building view for {len(runs)} runs")

    # Prepare table data
    table_data = []
    total_listings = 0

    for run in runs:
        try:
            # Add source information to run
            run = add_source_to_run(run)

            preview = load_run_preview(run)
            if isinstance(preview["listings"], int):
                total_listings += preview["listings"]

            table_data.append(
                {
                    "gemeenten": preview["gemeenten"],
                    "moment": preview["timestamp"],
                    "status": preview["status"],
                    "listings": preview["listings"],
                    "periode": preview["period"],
                    "run_name": run["run_name"],
                    "has_excel": preview["excel_path"] is not None,
                    "source": run.get("source", "airbnb"),  # Add source to row data
                }
            )
        except Exception as e:
            print(f"DEBUG: Error loading preview for {run.get('run_name')}: {e}")

    print(f"DEBUG: Created {len(table_data)} table rows")

    return html.Div(
        [
            create_sidebar("/dashboard"),
            html.Div(
                [
                    # Header with gradient
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H2(
                                        [
                                            html.I(
                                                "dashboard",
                                                className="material-icons",
                                                style={
                                                    "fontSize": "32px",
                                                    "marginRight": "12px",
                                                    "verticalAlign": "middle",
                                                },
                                            ),
                                            html.Span(
                                                "Resultaten",
                                                style={"verticalAlign": "middle"},
                                            ),
                                        ],
                                        style={
                                            "margin": 0,
                                            "color": "white",
                                            "display": "flex",
                                            "alignItems": "center",
                                            "fontSize": "28px",
                                            "fontWeight": "600",
                                        },
                                    ),
                                    html.Div(
                                        "Beheer en bekijk alle scraping runs",
                                        style={
                                            "color": "rgba(255,255,255,0.9)",
                                            "fontSize": "14px",
                                            "marginTop": "8px",
                                        },
                                    ),
                                ],
                            ),
                            html.Div(
                                datetime.now().strftime("%d-%m-%Y %H:%M"),
                                style={
                                    "color": "rgba(255,255,255,0.8)",
                                    "fontSize": "13px",
                                    "fontWeight": "500",
                                },
                            ),
                        ],
                        style={
                            "background": "linear-gradient(135deg, #1565c0 0%, #10357e 100%)",
                            "padding": "32px",
                            "borderRadius": "12px",
                            "marginBottom": "24px",
                            "boxShadow": "0 4px 6px rgba(0,0,0,0.1)",
                            "display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "center",
                        },
                    ),
                    # Filters Card
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label(
                                        [
                                            html.I(
                                                "search",
                                                className="material-icons",
                                                style={
                                                    "fontSize": "18px",
                                                    "marginRight": "8px",
                                                    "color": "#616161",
                                                    "verticalAlign": "middle",
                                                },
                                            ),
                                            html.Span(
                                                "Zoeken",
                                                style={"verticalAlign": "middle"},
                                            ),
                                        ],
                                        style={
                                            "fontSize": "14px",
                                            "fontWeight": "600",
                                            "color": "#424242",
                                            "marginBottom": "8px",
                                            "display": "flex",
                                            "alignItems": "center",
                                        },
                                    ),
                                    dcc.Input(
                                        id="search-input",
                                        type="text",
                                        placeholder="Zoek op gemeente naam...",
                                        style={
                                            "width": "100%",
                                            "padding": "12px",
                                            "border": "1px solid #e0e0e0",
                                            "borderRadius": "8px",
                                            "fontSize": "14px",
                                        },
                                    ),
                                ],
                                style={"flex": "1"},
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        [
                                            html.I(
                                                "filter_list",
                                                className="material-icons",
                                                style={
                                                    "fontSize": "18px",
                                                    "marginRight": "8px",
                                                    "color": "#616161",
                                                    "verticalAlign": "middle",
                                                },
                                            ),
                                            html.Span(
                                                "Status",
                                                style={"verticalAlign": "middle"},
                                            ),
                                        ],
                                        style={
                                            "fontSize": "14px",
                                            "fontWeight": "600",
                                            "color": "#424242",
                                            "marginBottom": "8px",
                                            "display": "flex",
                                            "alignItems": "center",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="status-filter",
                                        options=[
                                            {
                                                "label": "Voltooid",
                                                "value": "completed",
                                            },
                                            {
                                                "label": "Bezig",
                                                "value": "running",
                                            },
                                            {
                                                "label": "Gepauzeerd",
                                                "value": "paused",
                                            },
                                            {"label": "Fout", "value": "failed"},
                                            {
                                                "label": "Legacy",
                                                "value": "legacy",
                                            },
                                        ],
                                        value=["completed", "running"],
                                        multi=True,
                                        placeholder="Selecteer statussen...",
                                    ),
                                ],
                                style={"flex": "0 0 250px"},
                            ),
                            # Data Source Filter
                            html.Div(
                                [
                                    html.Label(
                                        [
                                            html.I(
                                                "source",
                                                className="material-icons",
                                                style={
                                                    "fontSize": "18px",
                                                    "marginRight": "8px",
                                                    "color": "#616161",
                                                    "verticalAlign": "middle",
                                                },
                                            ),
                                            html.Span(
                                                "Bron",
                                                style={"verticalAlign": "middle"},
                                            ),
                                        ],
                                        style={
                                            "fontSize": "14px",
                                            "fontWeight": "600",
                                            "color": "#424242",
                                            "marginBottom": "8px",
                                            "display": "flex",
                                            "alignItems": "center",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="source-filter",
                                        options=[
                                            {"label": "● Alle bronnen", "value": "all"},
                                            {"label": "● Airbnb", "value": "airbnb"},
                                            {"label": "● Funda", "value": "funda"},
                                        ],
                                        value="all",
                                        clearable=False,
                                        placeholder="Selecteer bron...",
                                    ),
                                ],
                                style={"flex": "0 0 200px"},
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        [
                                            html.I(
                                                "sort",
                                                className="material-icons",
                                                style={
                                                    "fontSize": "18px",
                                                    "marginRight": "8px",
                                                    "color": "#616161",
                                                    "verticalAlign": "middle",
                                                },
                                            ),
                                            html.Span(
                                                "Sorteren",
                                                style={"verticalAlign": "middle"},
                                            ),
                                        ],
                                        style={
                                            "fontSize": "14px",
                                            "fontWeight": "600",
                                            "color": "#424242",
                                            "marginBottom": "8px",
                                            "display": "flex",
                                            "alignItems": "center",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="sort-dropdown",
                                        options=[
                                            {
                                                "label": "↓ Nieuwste eerst",
                                                "value": "date_desc",
                                            },
                                            {
                                                "label": "↑ Oudste eerst",
                                                "value": "date_asc",
                                            },
                                            {
                                                "label": "↓ Meeste listings",
                                                "value": "listings_desc",
                                            },
                                            {
                                                "label": "↑ Minste listings",
                                                "value": "listings_asc",
                                            },
                                            {
                                                "label": "A-Z Gemeenten",
                                                "value": "name_asc",
                                            },
                                            {
                                                "label": "Z-A Gemeenten",
                                                "value": "name_desc",
                                            },
                                        ],
                                        value="date_desc",
                                        clearable=False,
                                    ),
                                ],
                                style={"flex": "0 0 220px"},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "flex-start",
                            "gap": "16px",
                            "marginBottom": "28px",
                            "padding": "24px",
                            "background": "white",
                            "borderRadius": "12px",
                            "border": "1px solid #e0e0e0",
                            "boxShadow": "0 2px 4px rgba(0,0,0,0.05)",
                        },
                    ),
                    # Runs Cards Grid
                    html.Div(
                        [
                            html.Div(
                                [
                                    # Card header with run info
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.H4(
                                                                row["gemeenten"],
                                                                style={
                                                                    "margin": 0,
                                                                    "fontSize": "18px",
                                                                    "color": "#10357e",
                                                                    "fontWeight": "600",
                                                                    "marginRight": "8px",
                                                                },
                                                            ),
                                                            source_chip(
                                                                row.get(
                                                                    "source", "airbnb"
                                                                ),
                                                                show_label=False,
                                                            ),
                                                        ],
                                                        style={
                                                            "display": "flex",
                                                            "alignItems": "center",
                                                            "marginBottom": "6px",
                                                        },
                                                    ),
                                                    html.Div(
                                                        row["moment"],
                                                        style={
                                                            "fontSize": "13px",
                                                            "color": "#888",
                                                        },
                                                    ),
                                                ],
                                                style={"flex": "1"},
                                            ),
                                            status_badge(row["status"]),
                                        ],
                                        style={
                                            "display": "flex",
                                            "justifyContent": "space-between",
                                            "alignItems": "flex-start",
                                            "marginBottom": "16px",
                                            "paddingBottom": "12px",
                                            "borderBottom": "1px solid #e0e0e0",
                                        },
                                    ),
                                    # Card metrics
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Div(
                                                        "Listings",
                                                        style={
                                                            "fontSize": "12px",
                                                            "color": "#888",
                                                            "marginBottom": "4px",
                                                        },
                                                    ),
                                                    html.Div(
                                                        str(row["listings"]),
                                                        style={
                                                            "fontSize": "20px",
                                                            "fontWeight": "600",
                                                            "color": "#0288d1",
                                                        },
                                                    ),
                                                ],
                                                style={"flex": "1"},
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        "Periode",
                                                        style={
                                                            "fontSize": "12px",
                                                            "color": "#888",
                                                            "marginBottom": "4px",
                                                        },
                                                    ),
                                                    html.Div(
                                                        row["periode"],
                                                        style={
                                                            "fontSize": "14px",
                                                            "color": "#333",
                                                        },
                                                    ),
                                                ],
                                                style={
                                                    "flex": "1",
                                                    "textAlign": "right",
                                                },
                                            ),
                                        ],
                                        style={
                                            "display": "flex",
                                            "justifyContent": "space-between",
                                            "marginBottom": "16px",
                                        },
                                    ),
                                    # Card actions
                                    html.Div(
                                        [
                                            dcc.Link(
                                                html.Button(
                                                    "Bekijken",
                                                    style={
                                                        "background": "#10357e",
                                                        "color": "white",
                                                        "border": "none",
                                                        "padding": "10px 20px",
                                                        "borderRadius": "6px",
                                                        "cursor": "pointer",
                                                        "fontSize": "14px",
                                                        "fontWeight": "500",
                                                        "transition": "all 0.2s",
                                                    },
                                                ),
                                                href=f"/run/{row['run_name']}",
                                                style={"textDecoration": "none"},
                                            ),
                                            dbc.DropdownMenu(
                                                [
                                                    dbc.DropdownMenuItem(
                                                        "Alle bestanden",
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
                                                        href=f"/download_zip/{row['run_name']}",
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
                                                        href=f"/download/excel?run={row['run_name']}",
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
                                                        href=f"/download/parquet?run={row['run_name']}",
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
                                                        href=f"/download/csv?run={row['run_name']}",
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
                                                        href=f"/download_file/{row['run_name']}/map.html",
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
                                                        href=f"/download_file/{row['run_name']}/timeline_availability.png",
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
                                                        href=f"/download_file/{row['run_name']}/config.json",
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
                                                        href=f"/download_file/{row['run_name']}/run.log",
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
                                            )
                                            if row["has_excel"]
                                            else None,
                                        ],
                                        style={
                                            "display": "flex",
                                            "justifyContent": "space-between",
                                            "alignItems": "center",
                                            "gap": "12px",
                                        },
                                    ),
                                ],
                                style={
                                    "background": "white",
                                    "border": "1px solid #e0e0e0",
                                    "borderRadius": "8px",
                                    "padding": "20px",
                                    "transition": "all 0.2s",
                                    "boxShadow": "0 1px 3px rgba(0,0,0,0.05)",
                                },
                                className="run-card",
                            )
                            for row in table_data
                        ],
                        id="runs-container",
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "repeat(2, 1fr)",
                            "gap": "20px",
                            "marginTop": "20px",
                        },
                    ),
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
