#!/usr/bin/env python3
"""
Dash Dashboard voor Airbnb Scraper (Nederlandse versie)
"""

import os
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd  # type: ignore
from dash import (
    Dash,
    html,
    dcc,
    Input,
    Output,
    State,
)  # type: ignore
from dash.exceptions import PreventUpdate  # type: ignore
import dash_bootstrap_components as dbc  # type: ignore
import geopandas as gpd  # type: ignore
from src.core.scraper_core import (
    scrape_all,
    generate_scan_combinations,
)
from src.core.run_tracker import RunTracker
from src.data.data_processor import calculate_availability, prepare_export_data
from src.data.exporter import export_to_excel

try:
    from src.visualization.map_creator import create_map  # type: ignore
except Exception:
    create_map = None  # type: ignore

# Import modular components
from dashboard.dash_helpers import (
    load_run_data,
    load_run_preview,
    get_all_runs,
)
from dashboard.dash_components import create_sidebar, status_badge
from dashboard.dash_pages import (
    create_login_page,
    create_nieuwe_run_page,
    create_mapping_page,
    create_instellingen_page,
    create_resultaten_page,
)
from dashboard.dash_callbacks import (
    register_auth_callbacks,
    register_nieuwe_run_callbacks,
    register_run_callbacks,
    register_mapping_callbacks,
)

# Project paths
PROJECT_ROOT = Path(__file__).parent
LOGO_PATH = PROJECT_ROOT / "assets" / "rigo-logo.svg"
GPKG_PATH = str(PROJECT_ROOT / "assets" / "BestuurlijkeGebieden_2025.gpkg")
DATA_DIR = str(PROJECT_ROOT / "outputs" / "data")
LOGIN_PASSWORD = "Ruijterkade"


# Note: Helper functions moved to dash_helpers/ module
# - load_gemeenten_list() -> dash_helpers/data_helpers.py
# - create_gemeente_selection_map_html() -> dash_helpers/map_helpers.py
# - load_run_data() -> dash_helpers/data_helpers.py
# - create_timeline_figure() -> dash_helpers/visualization_helpers.py
# - load_run_preview() -> dash_helpers/data_helpers.py
# - get_all_runs() -> dash_helpers/data_helpers.py
# - create_sidebar() -> dash_components/sidebar.py
# - status_badge() -> dash_components/ui_elements.py


# OLD HELPER FUNCTION - NOW IMPORTED FROM dash_helpers


def load_run_details(run: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Use Parquet-first loading
        df_all = load_run_data(run["run_path"])
    except Exception as e:
        print(f"Error loading run data: {e}")
        return {"df_all": pd.DataFrame(), "config": {}}

    config = {}
    config_path = os.path.join(run["run_path"], "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass

    # Find Excel path for download link
    excel_files = (
        [
            f
            for f in os.listdir(run["run_path"])
            if f.endswith(".xlsx") and not f.startswith("~$")
        ]
        if os.path.exists(run["run_path"])
        else []
    )
    excel_path = os.path.join(run["run_path"], excel_files[0]) if excel_files else None

    return {"df_all": df_all, "config": config, "excel_path": excel_path}


def make_app() -> Dash:
    # Check if favicon exists
    favicon_path = PROJECT_ROOT / "favicon.png"

    app = Dash(
        __name__,
        title="Airbnb Scraper Dashboard",
        suppress_callback_exceptions=True,
        assets_folder=str(PROJECT_ROOT / "assets")
        if (PROJECT_ROOT / "assets").exists()
        else None,
        external_stylesheets=[
            # Bootstrap CSS is required for dash_bootstrap_components Collapse to work properly
            "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
            "https://fonts.googleapis.com/icon?family=Material+Icons",
        ],
    )

    # Set favicon if it exists
    if favicon_path.exists():
        app._favicon = "favicon.png"

    # Add custom CSS for animations and dropdown styling
    app.index_string = """
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
            <style>
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                
                .download-dropdown:hover {
                    display: block !important;
                }
                
                .download-dropdown a:hover {
                    background-color: #f5f5f5 !important;
                }
                
                /* Smooth scrolling for log content */
                pre {
                    scroll-behavior: smooth;
                }
                
                /* Better hover states for cards */
                .run-card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
                }
                
                /* ===== ALL DROPDOWN STYLING ===== */
                
                /* Improve multiselect dropdown styling */
                .Select-multi-value-wrapper {
                    max-height: 100px;
                    overflow-y: auto;
                }
                
                /* Default styling for all selected items - dark blue with good contrast */
                .Select-value {
                    background-color: #10357e !important;
                    border: 1px solid #0a2456 !important;
                    color: white !important;
                    border-radius: 4px !important;
                    padding: 3px 10px !important;
                    margin: 3px !important;
                    font-weight: 500 !important;
                    font-size: 13px !important;
                }
                
                .Select-value-icon {
                    border-right: 1px solid rgba(255,255,255,0.3) !important;
                    padding: 2px 5px !important;
                }
                
                .Select-value-icon:hover {
                    background-color: rgba(0,0,0,0.3) !important;
                    color: white !important;
                }
                
                .Select-value-label {
                    color: white !important;
                    padding-left: 5px !important;
                }
                
                /* Universal dropdown control styling */
                .Select-control {
                    border: 1px solid #d1d5db !important;
                    border-radius: 8px !important;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
                    background-color: white !important;
                    min-height: 42px !important;
                    transition: all 0.2s ease !important;
                }
                
                .Select-control:hover {
                    border-color: #10357e !important;
                    box-shadow: 0 2px 4px rgba(16,53,126,0.1) !important;
                }
                
                .Select.is-focused > .Select-control {
                    border-color: #10357e !important;
                    box-shadow: 0 0 0 3px rgba(16,53,126,0.1) !important;
                }
                
                /* Dropdown placeholder */
                .Select-placeholder {
                    color: #9ca3af !important;
                    font-size: 14px !important;
                    padding-left: 4px !important;
                }
                
                /* Dropdown input */
                .Select-input {
                    padding-left: 4px !important;
                }
                
                .Select-input > input {
                    padding: 8px 0 !important;
                    font-size: 14px !important;
                }
                
                /* Dropdown arrow */
                .Select-arrow-zone {
                    padding-right: 8px !important;
                }
                
                .Select-arrow {
                    border-color: #6b7280 transparent transparent !important;
                    border-width: 5px 5px 2.5px !important;
                }
                
                /* Dropdown menu */
                .Select-menu-outer {
                    border: 1px solid #e5e7eb !important;
                    border-radius: 8px !important;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.15) !important;
                    margin-top: 4px !important;
                    z-index: 9999 !important;
                }
                
                .Select-menu {
                    max-height: 300px !important;
                    border-radius: 8px !important;
                }
                
                /* Dropdown options */
                .Select-option {
                    padding: 10px 14px !important;
                    font-size: 14px !important;
                    cursor: pointer !important;
                    transition: all 0.15s ease !important;
                }
                
                .Select-option:hover {
                    background-color: #eff6ff !important;
                    color: #10357e !important;
                }
                
                .Select-option.is-selected {
                    background-color: #10357e !important;
                    color: white !important;
                    font-weight: 500 !important;
                }
                
                .Select-option.is-focused {
                    background-color: #e3f2fd !important;
                    color: #10357e !important;
                }
                
                /* Disabled options */
                .Select-option.is-disabled {
                    color: #d1d5db !important;
                    cursor: not-allowed !important;
                    background-color: #f9fafb !important;
                }
                
                .Select-option.is-disabled:hover {
                    background-color: #f9fafb !important;
                }
                
                /* Single value (selected in single-select) */
                .Select--single > .Select-control .Select-value {
                    background-color: transparent !important;
                    border: none !important;
                    color: #111827 !important;
                    padding: 0 !important;
                    margin: 0 !important;
                    line-height: 42px !important;
                    display: flex !important;
                    align-items: center !important;
                }
                
                .Select--single > .Select-control .Select-value-label {
                    color: #111827 !important;
                    font-size: 14px !important;
                    padding-left: 4px !important;
                    line-height: 1.5 !important;
                }
                
                /* Clear button */
                .Select-clear-zone {
                    padding-right: 4px !important;
                }
                
                .Select-clear {
                    font-size: 20px !important;
                    color: #9ca3af !important;
                }
                
                .Select-clear:hover {
                    color: #ef4444 !important;
                }
                
                /* Loading indicator */
                .Select-loading {
                    border-color: #10357e transparent transparent !important;
                }
                
                /* No results */
                .Select-noresults {
                    padding: 12px 14px !important;
                    color: #6b7280 !important;
                    font-size: 14px !important;
                }
            </style>
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    """

    server = app.server  # Flask server for routes

    # Load and cache runs at startup (much faster than loading per request)
    print("Loading runs at startup...")
    try:
        app.cached_runs = get_all_runs(DATA_DIR)
        print(f"Cached {len(app.cached_runs)} runs")
    except Exception as e:
        print(f"Error loading runs: {e}")
        app.cached_runs = []

    # Initialize data cache for Excel/Parquet files
    app.run_data_cache = {}

    app.layout = html.Div(
        [
            dcc.Location(id="url"),
            dcc.Store(id="auth", storage_type="session"),
            dcc.Store(id="runs-store"),
            dcc.Store(id="df-store"),
            html.Div(
                id="page",
                children=html.Div(
                    "Laden...", style={"padding": "24px", "color": "#616161"}
                ),
            ),
        ],
        style={"fontFamily": "Inter, Arial, sans-serif"},
    )

    # Login view
    login_view = create_login_page()

    # Dashboard view skeleton
    def dashboard_view(runs: List[Dict[str, Any]]):
        # Prepare table data
        table_data = []
        total_listings = 0

        for run in runs:
            try:
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
                    }
                )
            except Exception:
                pass

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
                                            style={"fontSize": "14px"},
                                        ),
                                    ],
                                    style={"flex": "0 0 250px"},
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
                                            style={"fontSize": "14px"},
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
                                                        html.H4(
                                                            row["gemeenten"],
                                                            style={
                                                                "margin": 0,
                                                                "fontSize": "18px",
                                                                "color": "#10357e",
                                                                "fontWeight": "600",
                                                            },
                                                        ),
                                                        html.Div(
                                                            row["moment"],
                                                            style={
                                                                "fontSize": "13px",
                                                                "color": "#888",
                                                                "marginTop": "4px",
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
                                                        dbc.DropdownMenuItem(
                                                            divider=True
                                                        ),
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
                                                        dbc.DropdownMenuItem(
                                                            divider=True
                                                        ),
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

    # Run details view with tabs
    def details_view(run: Dict[str, Any]):
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

        # Pre-load Excel data in background to cache it
        run_path = run.get("run_path")
        data_cache_key = f"{run_path}_data"
        if data_cache_key not in app.run_data_cache:
            import threading

            def load_data_async():
                try:
                    df = load_run_data(run_path)
                    app.run_data_cache[data_cache_key] = df
                except Exception:
                    pass

            # Start loading in background thread
            thread = threading.Thread(target=load_data_async, daemon=True)
            thread.start()

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
                                                html.H1(
                                                    gemeenten,
                                                    style={
                                                        "margin": 0,
                                                        "color": "#10357e",
                                                        "fontSize": "32px",
                                                        "fontWeight": "bold",
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

    # Routes and callbacks
    @app.server.route("/download")
    def download_excel():
        """Download Excel file (legacy route)"""
        from flask import request, send_file, abort  # type: ignore

        run_name = request.args.get("run")
        if not run_name:
            return abort(400)
        run_path = os.path.join(DATA_DIR, run_name)
        if not os.path.exists(run_path):
            return abort(404)
        excel_files = [
            f
            for f in os.listdir(run_path)
            if f.endswith(".xlsx") and not f.startswith("~$")
        ]
        if not excel_files:
            return abort(404)
        excel_path = os.path.join(run_path, excel_files[0])
        return send_file(excel_path, as_attachment=True)

    @app.server.route("/download/<format_type>")
    def download_format(format_type):
        """Download file in specified format (excel, parquet, csv)"""
        from flask import request, send_file, abort  # type: ignore

        run_name = request.args.get("run")
        if not run_name:
            return abort(400)
        run_path = os.path.join(DATA_DIR, run_name)
        if not os.path.exists(run_path):
            return abort(404)

        if format_type == "excel":
            excel_files = [
                f
                for f in os.listdir(run_path)
                if f.endswith(".xlsx") and not f.startswith("~$")
            ]
            if not excel_files:
                return abort(404)
            file_path = os.path.join(run_path, excel_files[0])
            return send_file(file_path, as_attachment=True)

        elif format_type == "parquet":
            parquet_path = os.path.join(run_path, "data.parquet")
            if os.path.exists(parquet_path):
                return send_file(
                    parquet_path,
                    as_attachment=True,
                    download_name=f"{run_name}.parquet",
                )
            # Create parquet from Excel if doesn't exist
            try:
                df = load_run_data(run_path)
                parquet_path = os.path.join(run_path, "data.parquet")
                df.to_parquet(parquet_path, index=False)
                return send_file(
                    parquet_path,
                    as_attachment=True,
                    download_name=f"{run_name}.parquet",
                )
            except Exception:
                return abort(404)

        elif format_type == "csv":
            # Create CSV from data
            try:
                df = load_run_data(run_path)
                import io

                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                return send_file(
                    io.BytesIO(csv_buffer.getvalue().encode()),
                    mimetype="text/csv",
                    as_attachment=True,
                    download_name=f"{run_name}.csv",
                )
            except Exception:
                return abort(404)

        return abort(404)

    @app.server.route("/download_file/<run_name>/<filename>")
    def download_file(run_name, filename):
        from flask import send_file, abort  # type: ignore

        run_path = os.path.join(DATA_DIR, run_name)
        if not os.path.exists(run_path):
            return abort(404)

        file_path = os.path.join(run_path, filename)
        if not os.path.exists(file_path):
            return abort(404)

        # Security: Prevent directory traversal
        if not os.path.abspath(file_path).startswith(os.path.abspath(run_path)):
            return abort(403)

        return send_file(file_path, as_attachment=True)

    @app.server.route("/download_zip/<run_name>")
    def download_zip(run_name):
        from flask import send_file, abort  # type: ignore
        import zipfile
        import tempfile
        import shutil

        run_path = os.path.join(DATA_DIR, run_name)
        if not os.path.exists(run_path):
            return abort(404)

        # Create temporary ZIP file
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, f"{run_name}.zip")

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Add Excel file
                excel_files = [
                    f
                    for f in os.listdir(run_path)
                    if f.endswith(".xlsx") and not f.startswith("~$")
                ]
                if excel_files:
                    excel_path = os.path.join(run_path, excel_files[0])
                    zipf.write(excel_path, excel_files[0])

                # Add map.html if exists
                map_path = os.path.join(run_path, "map.html")
                if os.path.exists(map_path):
                    zipf.write(map_path, "map.html")

                # Add config.json if exists
                config_path = os.path.join(run_path, "config.json")
                if os.path.exists(config_path):
                    zipf.write(config_path, "config.json")

                # Add run_status.json if exists
                status_path = os.path.join(run_path, "run_status.json")
                if os.path.exists(status_path):
                    zipf.write(status_path, "run_status.json")

                # Add run.log if exists
                log_path = os.path.join(run_path, "run.log")
                if os.path.exists(log_path):
                    zipf.write(log_path, "run.log")

                # Add timeline graph if exists
                timeline_path = os.path.join(run_path, "timeline_availability.png")
                if os.path.exists(timeline_path):
                    zipf.write(timeline_path, "timeline_availability.png")

            return send_file(
                zip_path,
                as_attachment=True,
                download_name=f"{run_name}.zip",
                mimetype="application/zip",
            )
        except Exception as e:
            print(f"Error creating ZIP: {e}")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return abort(500)

    @app.callback(
        Output("page", "children"),
        [Input("url", "pathname"), Input("auth", "data")],
        prevent_initial_call=False,
    )
    def route(pathname, auth):
        # DEBUG: Simple routing

        # Route: Login page
        if pathname == "/" or pathname is None:
            if not auth or not auth.get("ok"):
                return login_view
            # If logged in at root, show dashboard directly (no redirect)
            pathname = "/dashboard"  # Fall through to dashboard handling

        # All other routes require auth
        if not auth or not auth.get("ok"):
            return dcc.Location(pathname="/", id="redirect")

        # Route: Dashboard overview
        if pathname == "/dashboard":
            # Reload runs from disk to get latest status (don't use cache)
            runs = get_all_runs(DATA_DIR) if os.path.exists(DATA_DIR) else []
            # Update cache for sidebar
            app.cached_runs = runs
            return create_resultaten_page(runs)

        # Route: Run details
        if pathname and pathname.startswith("/run/"):
            run_name = pathname.split("/run/")[-1]
            # Reload runs from disk to get latest status
            runs = get_all_runs(DATA_DIR) if os.path.exists(DATA_DIR) else []
            app.cached_runs = runs  # Update cache
            sel = [r for r in runs if r.get("run_name") == run_name]
            if sel:
                return details_view(sel[0])
            return create_resultaten_page(runs)

        # Route: Nieuwe Run
        if pathname == "/nieuwe_run":
            return create_nieuwe_run_page()

        # Route: Mapping Config
        if pathname == "/mapping":
            return create_mapping_page()

        # Route: Instellingen
        if pathname == "/instellingen":
            return create_instellingen_page(DATA_DIR)

        # Default: redirect to dashboard
        return dcc.Location(pathname="/dashboard", id="redirect")

    # Schedule mode UI visibility

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        [Input("start-run-btn", "n_clicks")],
        [
            State("source-dropdown", "value"),
            State("gemeenten-dropdown", "value"),
            State("period-start", "date"),
            State("period-end", "date"),
            State("nights-input", "value"),
            State("guests-input", "value"),
            State("schedule-mode", "value"),
            State("measurement-interval", "value"),
            State("days-of-week", "value"),
            State("num-repeat-calls", "value"),
            State("zoom-value", "value"),
            State("price-min", "value"),
            State("price-max", "value"),
            State("currency", "value"),
            State("language", "value"),
            State("max-workers", "value"),
            State("delay-between-scans", "value"),
            State("delay-between-calls", "value"),
        ],
        prevent_initial_call=True,
    )
    def start_run(
        n_clicks,
        source,
        gemeenten,
        start_date,
        end_date,
        nights_str,
        guests_str,
        mode,
        interval,
        days_of_week,
        num_repeat_calls,
        zoom_value,
        price_min,
        price_max,
        currency,
        language,
        max_workers,
        delay_between_scans,
        delay_between_calls,
    ):
        if not n_clicks:
            raise PreventUpdate
        if not gemeenten:
            raise PreventUpdate
        if not start_date or not end_date or start_date >= end_date:
            raise PreventUpdate

        # Parse lists
        try:
            nights_list = [
                int(n.strip()) for n in (nights_str or "").split(",") if n.strip()
            ]
            guests_list = [
                int(g.strip()) for g in (guests_str or "").split(",") if g.strip()
            ]
        except Exception:
            nights_list = [3, 7]
            guests_list = [2]

        # Build output dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        gemeente_name = (
            "_".join(gemeenten) if len(gemeenten) <= 3 else f"{gemeenten[0]}_etc"
        )
        output_dir = os.path.join(DATA_DIR, f"run_{gemeente_name}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)

        tracker = RunTracker(output_dir)
        config = {
            "gemeenten": gemeenten,
            "period_start": start_date,
            "period_end": end_date,
            "nights_list": nights_list,
            "guests_list": guests_list,
            "measurement_interval": int(interval or 7),
            "num_repeat_calls": int(num_repeat_calls or 2),
            "zoom_value": int(zoom_value or 12),
            "price_min": int(price_min or 0),
            "price_max": int(price_max or 0),
            "currency": currency or "EUR",
            "language": language or "nl",
            "days_of_week": (days_of_week or [])
            if mode in ("weekdays", "monthly")
            else None,
            "weeks_interval": 1,
            "monthly_interval": mode == "monthly",
            "max_workers": int(max_workers or 1),
            "delay_between_scans": float(delay_between_scans or 1.0),
            "delay_between_calls": float(delay_between_calls or 0.5),
            "measurement_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": source or "airbnb",  # Data source for this run
        }
        with open(os.path.join(output_dir, "config.json"), "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        def _background_scrape():
            try:
                # Configure logging to write to run.log
                import logging

                log_file = os.path.join(output_dir, "run.log")

                # Get the root logger and scraper logger
                root_logger = logging.getLogger()
                scraper_logger = logging.getLogger("src.core.scraper_core")

                # Create file handler
                file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
                file_handler.setLevel(logging.INFO)
                formatter = logging.Formatter(
                    "[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
                )
                file_handler.setFormatter(formatter)

                # Add handler to both loggers if not already present
                if not any(
                    isinstance(h, logging.FileHandler) and h.baseFilename == log_file
                    for h in scraper_logger.handlers
                ):
                    scraper_logger.addHandler(file_handler)
                    scraper_logger.setLevel(logging.INFO)

                # Generate combinations
                combos, _ = generate_scan_combinations(
                    config["period_start"],
                    config["period_end"],
                    config["nights_list"],
                    config["guests_list"],
                    config["measurement_interval"],
                    config.get("days_of_week"),
                    config.get("weeks_interval", 1),
                    config.get("monthly_interval", False),
                )
                total_scans = len(combos) * len(config["gemeenten"])
                tracker.start(total_scans=total_scans)

                df_all = scrape_all(
                    gemeenten=config["gemeenten"],
                    scan_combinations=combos,
                    gpkg_path=GPKG_PATH,
                    num_repeat_calls=config["num_repeat_calls"],
                    zoom_value=config["zoom_value"],
                    price_min=config["price_min"],
                    price_max=config["price_max"],
                    amenities=[],
                    currency=config["currency"],
                    language=config["language"],
                    proxy_url="",
                    measurement_date=config["measurement_date"],
                    show_progress=False,
                    max_workers=config["max_workers"],
                    checkpoint_dir=output_dir,
                    delay_between_scans=config["delay_between_scans"],
                    delay_between_calls=config["delay_between_calls"],
                    tracker=tracker,
                )

                if df_all.empty:
                    tracker.fail("Geen resultaten gevonden")
                    return

                # Export
                df_avail = calculate_availability(
                    df_all, config["period_start"], config["period_end"]
                )
                df_map = df_all.drop_duplicates("room_id").merge(
                    df_avail[
                        ["room_id", "days_available", "availability_rate", "total_days"]
                    ],
                    on="room_id",
                    how="left",
                )
                df_export = prepare_export_data(df_all)
                excel_filename = (
                    f"airbnb_scrape_{'_'.join(config['gemeenten'])}_{timestamp}.xlsx"
                )
                excel_path = os.path.join(output_dir, excel_filename)
                export_to_excel(df_export, excel_path, df_avail, df_all)

                # Map output (best-effort)
                try:
                    gdf_gemeenten = (
                        gpd.read_file(GPKG_PATH, layer="gemeentegebied")
                        .set_crs("EPSG:28992")
                        .to_crs("EPSG:4326")
                    )
                    create_map(df_map, gdf_gemeenten, config["gemeenten"], output_dir)
                except Exception:
                    pass

                tracker.complete(total_listings=int(df_all["room_id"].nunique()))
            except Exception as e:
                tracker.fail(str(e))

        threading.Thread(target=_background_scrape, daemon=True).start()

        # Update cached runs so details page can find it immediately
        try:
            run_name = f"run_{gemeente_name}_{timestamp}"
            new_run = {
                "run_name": run_name,
                "run_path": output_dir,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "progress": {
                    "total_scans": 0,
                    "completed_scans": 0,
                    "failed_scans": 0,
                    "total_listings": 0,
                },
            }
            if hasattr(app, "cached_runs"):
                app.cached_runs = [new_run] + list(app.cached_runs)
        except Exception:
            pass

        # Redirect to run details
        return f"/run/run_{gemeente_name}_{timestamp}"

    # Register all callbacks from modules
    register_auth_callbacks(app, LOGIN_PASSWORD)
    register_nieuwe_run_callbacks(app)
    register_run_callbacks(app, DATA_DIR)
    register_mapping_callbacks(app)

    return app


def main():
    app = make_app()
    app.run(host="0.0.0.0", port=8050, debug=False)


if __name__ == "__main__":
    main()
