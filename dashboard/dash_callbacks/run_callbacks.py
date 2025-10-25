"""Run Management Callbacks"""

import os
import json
import pandas as pd
from dash import Input, Output, State, html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from dashboard.dash_helpers import (
    load_run_data,
    create_timeline_figure,
    get_all_runs,
    load_run_preview,
)
from dashboard.dash_components import status_badge


def register_run_callbacks(app, DATA_DIR):
    """Register run management callbacks"""

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        [Input("back-btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def navigate_back(n_clicks):
        if n_clicks:
            return "/dashboard"
        raise PreventUpdate

    @app.callback(
        [
            Output("meetmomenten-collapse", "is_open"),
            Output("period-expand-icon", "style"),
        ],
        [Input("period-toggle", "n_clicks")],
        [State("meetmomenten-collapse", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_meetmomenten(n_clicks, is_open):
        if not n_clicks:
            raise PreventUpdate

        new_state = not is_open
        icon_style = {
            "marginLeft": "8px",
            "fontSize": "24px",
            "color": "#2e7d32",
            "verticalAlign": "middle",
            "transition": "transform 0.2s ease",
            "transform": "rotate(180deg)" if new_state else "rotate(0deg)",
        }
        print(
            f"DEBUG toggle_meetmomenten: is_open={is_open} -> new_state={new_state}, icon rotation={icon_style['transform']}"
        )
        return new_state, icon_style

    @app.callback(
        Output("meetmomenten-content", "children"),
        [Input("meetmomenten-collapse", "is_open"), Input("current-run", "data")],
        prevent_initial_call=True,
    )
    def load_meetmomenten(is_open, current_run_data):
        import time

        start_time = time.time()

        print(f"\n{'=' * 60}")

        if not is_open:
            raise PreventUpdate

        if not current_run_data:
            raise PreventUpdate

        run_path = current_run_data.get("run_path")
        if not run_path:
            raise PreventUpdate

        try:
            scan_dates = []  # type: list
            cache_key = f"{run_path}_data"

            print(
                f"DEBUG MEETMOMENTEN: Cache contains key: {cache_key in app.run_data_cache}"
            )

            if cache_key in app.run_data_cache:
                print(
                    f"DEBUG MEETMOMENTEN: Using cached Excel - Time: {time.time() - start_time:.2f}s"
                )
                df_all = app.run_data_cache[cache_key]
                print(
                    f"DEBUG MEETMOMENTEN: Got cached df with {len(df_all)} rows - Time: {time.time() - start_time:.2f}s"
                )
                if "scan_checkin" in df_all.columns:
                    print(
                        f"DEBUG MEETMOMENTEN: Starting date conversion - Time: {time.time() - start_time:.2f}s"
                    )
                    scan_dates = sorted(
                        pd.to_datetime(df_all["scan_checkin"]).dt.date.unique()
                    )
                    print(
                        f"DEBUG MEETMOMENTEN: Found {len(scan_dates)} scan dates from cache - Time: {time.time() - start_time:.2f}s"
                    )

            if not scan_dates:
                print(
                    f"DEBUG MEETMOMENTEN: Checking config.json - Time: {time.time() - start_time:.2f}s"
                )
                config_path = os.path.join(run_path, "config.json")

                if os.path.exists(config_path):
                    try:
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                            scan_dates_str = config.get("scan_dates", [])
                            if scan_dates_str:
                                from datetime import datetime

                                scan_dates = sorted(
                                    [
                                        datetime.fromisoformat(d[:10]).date()
                                        for d in scan_dates_str
                                    ]
                                )
                    except Exception:
                        pass

            if not scan_dates:
                excel_files = [
                    f
                    for f in os.listdir(run_path)
                    if f.endswith(".xlsx") and not f.startswith("~$")
                ]
                if not excel_files:
                    return html.Div(
                        "Geen Excel bestand gevonden",
                        style={
                            "padding": "20px",
                            "textAlign": "center",
                            "color": "#888",
                        },
                    )

                print(
                    f"DEBUG MEETMOMENTEN: Loading data from {run_path} - Time: {time.time() - start_time:.2f}s"
                )

                df_all = load_run_data(run_path)
                print(
                    f"DEBUG MEETMOMENTEN: Data loaded ({len(df_all)} rows) - Time: {time.time() - start_time:.2f}s"
                )

                app.run_data_cache[cache_key] = df_all
                print(
                    f"DEBUG MEETMOMENTEN: Cached data - Time: {time.time() - start_time:.2f}s"
                )

                if "scan_checkin" in df_all.columns:
                    print(
                        f"DEBUG MEETMOMENTEN: Extracting scan dates - Time: {time.time() - start_time:.2f}s"
                    )
                    scan_dates = sorted(
                        pd.to_datetime(df_all["scan_checkin"]).dt.date.unique()
                    )
                    print(
                        f"DEBUG MEETMOMENTEN: Found {len(scan_dates)} scan dates from Excel - Time: {time.time() - start_time:.2f}s"
                    )

            if not scan_dates:
                return html.Div(
                    "Geen meetmomenten gevonden",
                    style={
                        "padding": "20px",
                        "textAlign": "center",
                        "color": "#888",
                    },
                )

            from collections import defaultdict

            month_names_dutch = {
                "January": "januari",
                "February": "februari",
                "March": "maart",
                "April": "april",
                "May": "mei",
                "June": "juni",
                "July": "juli",
                "August": "augustus",
                "September": "september",
                "October": "oktober",
                "November": "november",
                "December": "december",
            }

            months = defaultdict(list)
            for d in scan_dates:
                month_key_en = d.strftime("%B %Y")
                month_en = d.strftime("%B")
                month_nl = month_names_dutch.get(month_en, month_en)
                month_key = f"{month_nl} {d.strftime('%Y')}"
                months[month_key].append(d)

            weekday_dutch = {
                "Mon": "ma",
                "Tue": "di",
                "Wed": "wo",
                "Thu": "do",
                "Fri": "vr",
                "Sat": "za",
                "Sun": "zo",
            }

            month_sections = []
            for month_name, dates in months.items():
                date_cards = []
                for date in dates:
                    day_str = date.strftime("%d")
                    weekday_en = date.strftime("%a")
                    weekday = weekday_dutch.get(weekday_en, weekday_en)
                    date_cards.append(
                        html.Div(
                            [
                                html.Div(
                                    weekday,
                                    style={
                                        "fontSize": "10px",
                                        "opacity": "0.8",
                                        "marginBottom": "4px",
                                    },
                                ),
                                html.Div(
                                    day_str,
                                    style={
                                        "fontSize": "16px",
                                        "fontWeight": "bold",
                                    },
                                ),
                            ],
                            style={
                                "display": "inline-block",
                                "margin": "4px",
                                "padding": "8px 12px",
                                "background": "#27ae60",
                                "color": "white",
                                "borderRadius": "6px",
                                "textAlign": "center",
                                "minWidth": "60px",
                            },
                        )
                    )

                month_sections.append(
                    html.Div(
                        [
                            html.H4(
                                month_name,
                                style={"marginTop": "16px", "marginBottom": "12px"},
                            ),
                            html.Div(date_cards),
                        ]
                    )
                )

            print(
                f"DEBUG MEETMOMENTEN: Building HTML - Time: {time.time() - start_time:.2f}s"
            )
            result = html.Div(
                [
                    html.H3(
                        "Meetmomenten",
                        style={
                            "marginBottom": "16px",
                            "color": "#10357e",
                            "marginTop": "8px",
                        },
                    ),
                    html.Div(
                        f"{len(scan_dates)} meetmomenten",
                        style={
                            "padding": "12px",
                            "background": "#e3f2fd",
                            "borderRadius": "6px",
                            "marginBottom": "16px",
                            "color": "#1976d2",
                            "fontWeight": "500",
                        },
                    ),
                    html.Div(month_sections),
                ]
            )
            print(
                f"DEBUG MEETMOMENTEN: Returning result - Total time: {time.time() - start_time:.2f}s"
            )
            print(f"{'=' * 60}\n")
            return result

        except Exception as e:
            print(
                f"DEBUG MEETMOMENTEN: ERROR - {str(e)} - Time: {time.time() - start_time:.2f}s"
            )
            print(f"{'=' * 60}\n")
            return html.Div(
                f"Fout bij laden meetmomenten: {str(e)}",
                style={
                    "padding": "20px",
                    "textAlign": "center",
                    "color": "#d32f2f",
                },
            )

    if not hasattr(app, "run_data_cache"):
        app.run_data_cache = {}

    @app.callback(
        Output("tab-content", "children"),
        [
            Input("detail-tabs", "value"),
            Input("current-run", "data"),
            Input("log-refresh-interval", "n_intervals"),
        ],
        prevent_initial_call=False,
    )
    def render_tab_content(active_tab, current_run_data, n_intervals):
        if not current_run_data:
            return html.Div(
                "Geen run geselecteerd", style={"padding": "20px", "color": "#888"}
            )

        run_path = current_run_data.get("run_path")
        if not run_path or not os.path.exists(run_path):
            return html.Div(
                "Run pad niet gevonden", style={"padding": "20px", "color": "#888"}
            )

        if active_tab == "tab-overview":
            try:
                status_path = os.path.join(run_path, "run_status.json")
                run_status = "unknown"
                if os.path.exists(status_path):
                    try:
                        with open(status_path, "r") as f:
                            status_data = json.load(f)
                            run_status = status_data.get("status", "unknown")
                    except Exception:
                        pass

                excel_files = (
                    [
                        f
                        for f in os.listdir(run_path)
                        if f.endswith(".xlsx") and not f.startswith("~$")
                    ]
                    if os.path.exists(run_path)
                    else []
                )
                parquet_path = os.path.join(run_path, "data.parquet")
                has_data = excel_files or os.path.exists(parquet_path)

                if run_status == "running" and not has_data:
                    return html.Div(
                        [
                            html.Div(
                                [
                                    html.I(
                                        "hourglass_empty",
                                        className="material-icons",
                                        style={
                                            "fontSize": "64px",
                                            "color": "#fb8c00",
                                            "marginBottom": "16px",
                                        },
                                    ),
                                    html.H3(
                                        "Run is Bezig...",
                                        style={
                                            "color": "#424242",
                                            "marginBottom": "8px",
                                        },
                                    ),
                                    html.P(
                                        "De scraper is actief maar heeft nog geen resultaten.",
                                        style={
                                            "color": "#757575",
                                            "marginBottom": "16px",
                                        },
                                    ),
                                    html.P(
                                        "Ga naar de Logs tab om de voortgang te volgen.",
                                        style={"color": "#757575"},
                                    ),
                                ],
                                style={
                                    "textAlign": "center",
                                    "padding": "60px 40px",
                                    "background": "white",
                                    "borderRadius": "12px",
                                    "border": "1px solid #e0e0e0",
                                },
                            )
                        ],
                        style={"padding": "20px"},
                    )

                map_html_path = os.path.join(run_path, "map.html")
                map_content = None
                if os.path.exists(map_html_path):
                    with open(map_html_path, "r", encoding="utf-8") as f:
                        map_content = f.read()

                timeline_figure = None
                data_cache_key = f"{run_path}_data"

                try:
                    df = None
                    if data_cache_key in app.run_data_cache:
                        df = app.run_data_cache[data_cache_key]
                    else:
                        df = load_run_data(run_path)

                        app.run_data_cache[data_cache_key] = df

                    if df is not None:
                        config_path = os.path.join(run_path, "config.json")
                        config = {}
                        if os.path.exists(config_path):
                            with open(config_path, "r") as f:
                                config = json.load(f)

                        timeline_figure = create_timeline_figure(df, config)
                except Exception as e:
                    print(f"Error creating timeline: {e}")
                    import traceback

                    traceback.print_exc()

                if not map_content and not timeline_figure:
                    return html.Div(
                        "Geen visualisaties gevonden voor deze run",
                        style={"padding": "20px", "color": "#888"},
                    )

                # Get available scan dates for the time slider
                scan_dates = []
                if df is not None and "scan_checkin" in df.columns:
                    scan_dates = sorted(
                        pd.to_datetime(df["scan_checkin"]).dt.date.unique()
                    )

                # Create time slider marks
                slider_marks = {}
                if scan_dates:
                    for i, date in enumerate(scan_dates):
                        slider_marks[i] = {
                            "label": date.strftime("%d-%m"),
                            "style": {"writingMode": "vertical-rl", "fontSize": "11px"},
                        }

                return html.Div(
                    [
                        html.Div(
                            [
                                html.H3("Kaart", style={"marginBottom": "16px"}),
                                html.Iframe(
                                    id="map-iframe",
                                    srcDoc=map_content,
                                    style={
                                        "width": "100%",
                                        "height": "600px",
                                        "border": "none",
                                        "borderRadius": "8px",
                                    },
                                )
                                if map_content
                                else html.Div(
                                    "Kaart niet beschikbaar",
                                    style={
                                        "padding": "40px",
                                        "background": "#f5f5f5",
                                        "textAlign": "center",
                                        "color": "#888",
                                    },
                                ),
                                # Time slider section
                                html.Div(
                                    [
                                        html.Label(
                                            "Tijdsperiode:",
                                            style={
                                                "fontWeight": "600",
                                                "marginBottom": "8px",
                                                "display": "block",
                                                "color": "#10357e",
                                            },
                                        ),
                                        dcc.RangeSlider(
                                            id="time-range-slider",
                                            min=0,
                                            max=len(scan_dates) - 1
                                            if scan_dates
                                            else 0,
                                            value=[0, len(scan_dates) - 1]
                                            if scan_dates
                                            else [0, 0],
                                            marks=slider_marks,
                                            step=1,
                                            tooltip={
                                                "placement": "bottom",
                                                "always_visible": False,
                                            },
                                            disabled=not scan_dates,
                                        ),
                                        html.Div(
                                            id="time-range-display",
                                            style={
                                                "marginTop": "12px",
                                                "textAlign": "center",
                                                "color": "#666",
                                                "fontSize": "14px",
                                                "fontWeight": "500",
                                            },
                                            children=f"Alle metingen ({len(scan_dates)} datums)"
                                            if scan_dates
                                            else "Geen metingen beschikbaar",
                                        ),
                                    ],
                                    style={
                                        "marginTop": "24px",
                                        "padding": "16px",
                                        "background": "#f8f9fa",
                                        "borderRadius": "8px",
                                    },
                                )
                                if scan_dates
                                else None,
                                # Store scan dates for callback
                                dcc.Store(
                                    id="scan-dates-store",
                                    data=[str(d) for d in scan_dates],
                                ),
                            ],
                            style={
                                "background": "white",
                                "padding": "20px",
                                "borderRadius": "8px",
                                "border": "1px solid #e0e0e0",
                                "marginBottom": "20px",
                            },
                        ),
                        html.Div(
                            [
                                html.H3(
                                    "Beschikbaarheid over Tijd",
                                    style={"marginBottom": "16px"},
                                ),
                                dcc.Graph(
                                    figure=timeline_figure,
                                    config={
                                        "displayModeBar": True,
                                        "displaylogo": False,
                                    },
                                )
                                if timeline_figure
                                else html.Div(
                                    "Tijdlijn grafiek niet beschikbaar",
                                    style={
                                        "padding": "40px",
                                        "background": "#f5f5f5",
                                        "textAlign": "center",
                                        "color": "#888",
                                    },
                                ),
                            ],
                            style={
                                "background": "white",
                                "padding": "20px",
                                "borderRadius": "8px",
                                "border": "1px solid #e0e0e0",
                            },
                        ),
                    ]
                )
            except Exception as e:
                print(f"Error loading overview: {e}")
                import traceback

                traceback.print_exc()
                return html.Div(
                    f"Fout bij laden overzicht: {str(e)}",
                    style={"padding": "20px", "color": "#ef5350"},
                )

        elif active_tab == "tab-data":
            try:
                data_cache_key = f"{run_path}_data"
                df = None

                if data_cache_key in app.run_data_cache:
                    df = app.run_data_cache[data_cache_key]
                else:
                    df = load_run_data(run_path)

                    app.run_data_cache[data_cache_key] = df

                if df is None:
                    return html.Div(
                        "Geen data gevonden",
                        style={"padding": "20px", "color": "#888"},
                    )

                return html.Div(
                    [
                        html.H3("Data Tabel", style={"marginBottom": "16px"}),
                        dash_table.DataTable(
                            data=df.head(1000).to_dict(
                                "records"
                            ),  # Limit to first 1000 for performance
                            columns=[{"name": i, "id": i} for i in df.columns],
                            page_size=20,
                            page_action="native",
                            sort_action="native",
                            filter_action="native",
                            style_table={"overflowX": "auto"},
                            style_cell={
                                "textAlign": "left",
                                "padding": "10px",
                                "fontSize": "13px",
                            },
                            style_header={
                                "backgroundColor": "#f5f5f5",
                                "fontWeight": "bold",
                            },
                        ),
                        html.Div(
                            f"Toont eerste 1000 van {len(df)} records"
                            if len(df) > 1000
                            else f"Toont alle {len(df)} records",
                            style={
                                "marginTop": "16px",
                                "color": "#888",
                                "fontSize": "14px",
                            },
                        ),
                    ],
                    style={
                        "background": "white",
                        "padding": "20px",
                        "borderRadius": "8px",
                        "border": "1px solid #e0e0e0",
                    },
                )
            except Exception as e:
                print(f"Error loading data: {e}")
                import traceback

                traceback.print_exc()
                return html.Div(
                    f"Fout bij laden data: {str(e)}",
                    style={"padding": "20px", "color": "#ef5350"},
                )

        elif active_tab == "tab-data":
            try:
                excel_files = [
                    f
                    for f in os.listdir(run_path)
                    if f.endswith(".xlsx") and not f.startswith("~$")
                ]
                if not excel_files:
                    return html.Div(
                        "Geen Excel bestand gevonden",
                        style={"padding": "20px", "color": "#888"},
                    )

                df = load_run_data(run_path)

                display_cols = [
                    c
                    for c in [
                        "name",
                        "price",
                        "room_type",
                        "bedrooms",
                        "beds",
                        "property_type_airbnb",
                        "host_name",
                    ]
                    if c in df.columns
                ]

                return html.Div(
                    [
                        html.H3(
                            f"Data Tabel ({len(df):,} records)",
                            style={"marginBottom": "16px"},
                        ),
                        dash_table.DataTable(
                            id="details-table",
                            columns=[
                                {"name": c.replace("_", " ").title(), "id": c}
                                for c in display_cols
                            ],
                            data=df[display_cols].head(100).to_dict("records"),
                            page_size=20,
                            page_action="native",
                            sort_action="native",
                            filter_action="native",
                            style_table={
                                "overflowX": "auto",
                                "background": "white",
                                "borderRadius": "8px",
                            },
                            style_header={
                                "backgroundColor": "#10357e",
                                "color": "white",
                                "fontWeight": "bold",
                                "textAlign": "left",
                                "padding": "12px",
                            },
                            style_cell={
                                "textAlign": "left",
                                "padding": "12px",
                                "fontSize": "14px",
                            },
                            style_data={
                                "backgroundColor": "white",
                            },
                            style_data_conditional=[
                                {
                                    "if": {"row_index": "odd"},
                                    "backgroundColor": "#f9f9f9",
                                },
                            ],
                        ),
                    ]
                )
            except Exception as e:
                return html.Div(
                    f"Fout bij laden data: {str(e)}",
                    style={"padding": "20px", "color": "#ef5350"},
                )

        elif active_tab == "tab-log":
            try:
                log_path = os.path.join(run_path, "run.log")
                status_path = os.path.join(run_path, "run_status.json")

                status_data = {}
                if os.path.exists(status_path):
                    with open(status_path, "r") as f:
                        status_data = json.load(f)

                log_content = ""
                if os.path.exists(log_path):
                    with open(log_path, "r", encoding="utf-8") as f:
                        log_content = f.read()

                run_status = status_data.get("status", "unknown")
                progress_data = status_data.get("progress", {})
                total_scans = progress_data.get("total_scans", 0)
                completed_scans = progress_data.get("completed_scans", 0)
                total_listings = progress_data.get("total_listings", 0)

                status_colors = {
                    "running": {
                        "bg": "#e3f2fd",
                        "color": "#1976d2",
                        "icon": "autorenew",
                    },
                    "completed": {
                        "bg": "#e8f5e9",
                        "color": "#2e7d32",
                        "icon": "check_circle",
                    },
                    "failed": {"bg": "#ffebee", "color": "#c62828", "icon": "cancel"},
                    "pending": {
                        "bg": "#fff3e0",
                        "color": "#f57c00",
                        "icon": "schedule",
                    },
                }
                status_style = status_colors.get(
                    run_status, {"bg": "#f5f5f5", "color": "#616161", "icon": "help"}
                )

                return html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.I(
                                            status_style["icon"],
                                            className="material-icons",
                                            style={
                                                "fontSize": "32px",
                                                "marginRight": "12px",
                                                "color": status_style["color"],
                                            },
                                        ),
                                        html.Span(
                                            run_status.title(),
                                            style={
                                                "fontSize": "20px",
                                                "fontWeight": "600",
                                            },
                                        ),
                                    ],
                                    style={"display": "flex", "alignItems": "center"},
                                ),
                                html.Div(
                                    [
                                        html.I(
                                            "refresh",
                                            className="material-icons",
                                            style={
                                                "fontSize": "16px",
                                                "marginRight": "6px",
                                                "animation": "spin 2s linear infinite"
                                                if run_status == "running"
                                                else "none",
                                            },
                                        ),
                                        html.Span(
                                            "Auto-refreshing elke 3s",
                                            style={"fontSize": "13px"},
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "color": "#616161",
                                    },
                                )
                                if run_status == "running"
                                else None,
                            ],
                            style={
                                "background": status_style["bg"],
                                "padding": "20px 24px",
                                "borderRadius": "12px",
                                "marginBottom": "20px",
                                "display": "flex",
                                "justifyContent": "space-between",
                                "alignItems": "center",
                                "border": f"2px solid {status_style['color']}",
                            },
                        ),
                        html.Div(
                            [
                                html.H4(
                                    "Voortgang",
                                    style={"marginBottom": "16px", "color": "#10357e"},
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Div(
                                                    f"{completed_scans} / {total_scans}",
                                                    style={
                                                        "fontSize": "24px",
                                                        "fontWeight": "600",
                                                        "color": "#10357e",
                                                        "marginBottom": "8px",
                                                    },
                                                ),
                                                html.Div(
                                                    "Scans voltooid",
                                                    style={
                                                        "fontSize": "13px",
                                                        "color": "#757575",
                                                    },
                                                ),
                                            ],
                                            style={"flex": 1},
                                        ),
                                        html.Div(
                                            [
                                                html.Div(
                                                    f"{total_listings:,}",
                                                    style={
                                                        "fontSize": "24px",
                                                        "fontWeight": "600",
                                                        "color": "#0288d1",
                                                        "marginBottom": "8px",
                                                    },
                                                ),
                                                html.Div(
                                                    "Listings gevonden",
                                                    style={
                                                        "fontSize": "13px",
                                                        "color": "#757575",
                                                    },
                                                ),
                                            ],
                                            style={"flex": 1},
                                        ),
                                        html.Div(
                                            [
                                                html.Div(
                                                    f"{(completed_scans / total_scans * 100):.1f}%"
                                                    if total_scans > 0
                                                    else "0%",
                                                    style={
                                                        "fontSize": "24px",
                                                        "fontWeight": "600",
                                                        "color": "#2e7d32",
                                                        "marginBottom": "8px",
                                                    },
                                                ),
                                                html.Div(
                                                    "Voltooid",
                                                    style={
                                                        "fontSize": "13px",
                                                        "color": "#757575",
                                                    },
                                                ),
                                            ],
                                            style={"flex": 1},
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "gap": "24px",
                                        "marginBottom": "16px",
                                    },
                                ),
                                dbc.Progress(
                                    value=(completed_scans / total_scans * 100)
                                    if total_scans > 0
                                    else 0,
                                    style={"height": "12px", "borderRadius": "6px"},
                                    color="success"
                                    if run_status == "completed"
                                    else "info",
                                    striped=run_status == "running",
                                    animated=run_status == "running",
                                ),
                            ],
                            style={
                                "background": "white",
                                "padding": "24px",
                                "borderRadius": "12px",
                                "border": "1px solid #e0e0e0",
                                "marginBottom": "20px",
                            },
                        )
                        if total_scans > 0 or run_status == "running"
                        else None,
                        html.Div(
                            [
                                html.H4(
                                    "Run Informatie",
                                    style={"marginBottom": "16px", "color": "#10357e"},
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.I(
                                                    "schedule",
                                                    className="material-icons",
                                                    style={
                                                        "fontSize": "18px",
                                                        "marginRight": "8px",
                                                        "color": "#616161",
                                                        "verticalAlign": "middle",
                                                    },
                                                ),
                                                html.Strong(
                                                    "Gestart: ",
                                                    style={"verticalAlign": "middle"},
                                                ),
                                                html.Span(
                                                    status_data.get("started_at", "-")[
                                                        :19
                                                    ]
                                                    if status_data.get("started_at")
                                                    else "-",
                                                    style={"verticalAlign": "middle"},
                                                ),
                                            ],
                                            style={"marginBottom": "12px"},
                                        ),
                                        html.Div(
                                            [
                                                html.I(
                                                    "check_circle",
                                                    className="material-icons",
                                                    style={
                                                        "fontSize": "18px",
                                                        "marginRight": "8px",
                                                        "color": "#616161",
                                                        "verticalAlign": "middle",
                                                    },
                                                ),
                                                html.Strong(
                                                    "Voltooid: ",
                                                    style={"verticalAlign": "middle"},
                                                ),
                                                html.Span(
                                                    status_data.get(
                                                        "completed_at", "-"
                                                    )[:19]
                                                    if status_data.get("completed_at")
                                                    else "-",
                                                    style={"verticalAlign": "middle"},
                                                ),
                                            ],
                                            style={"marginBottom": "12px"},
                                        ),
                                        html.Div(
                                            [
                                                html.Strong("Totaal Scans: "),
                                                html.Span(
                                                    str(
                                                        status_data.get(
                                                            "progress", {}
                                                        ).get("total_scans", "-")
                                                    )
                                                ),
                                            ],
                                            style={"marginBottom": "8px"},
                                        ),
                                    ],
                                    style={"fontSize": "14px"},
                                ),
                            ],
                            style={
                                "background": "white",
                                "padding": "20px",
                                "borderRadius": "12px",
                                "border": "1px solid #e0e0e0",
                                "marginBottom": "20px",
                            },
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.I(
                                            "description",
                                            className="material-icons",
                                            style={
                                                "fontSize": "24px",
                                                "marginRight": "12px",
                                                "color": "#10357e",
                                                "verticalAlign": "middle",
                                            },
                                        ),
                                        html.H4(
                                            "Log Output",
                                            style={
                                                "margin": 0,
                                                "color": "#10357e",
                                                "display": "inline-block",
                                                "verticalAlign": "middle",
                                            },
                                        ),
                                    ],
                                    style={
                                        "marginBottom": "16px",
                                        "display": "flex",
                                        "alignItems": "center",
                                    },
                                ),
                                html.Pre(
                                    log_content
                                    if log_content
                                    else "Geen log bestand gevonden",
                                    style={
                                        "background": "#1e1e1e",
                                        "color": "#d4d4d4",
                                        "padding": "20px",
                                        "borderRadius": "8px",
                                        "fontSize": "13px",
                                        "fontFamily": "'Consolas', 'Monaco', 'Courier New', monospace",
                                        "maxHeight": "600px",
                                        "overflow": "auto",
                                        "whiteSpace": "pre-wrap",
                                        "wordWrap": "break-word",
                                        "lineHeight": "1.6",
                                        "border": "1px solid #333",
                                    },
                                ),
                            ],
                            style={
                                "background": "white",
                                "padding": "24px",
                                "borderRadius": "12px",
                                "border": "1px solid #e0e0e0",
                            },
                        ),
                    ]
                )
            except Exception as e:
                print(f"Error loading log: {e}")
                import traceback

                traceback.print_exc()
                return html.Div(
                    f"Fout bij laden log: {str(e)}",
                    style={"padding": "20px", "color": "#ef5350"},
                )

        elif active_tab == "tab-config":
            try:
                config_path = os.path.join(run_path, "config.json")
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        config = json.load(f)

                    return html.Div(
                        [
                            html.H3("Run Configuratie", style={"marginBottom": "16px"}),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H4(
                                                "Gemeenten",
                                                style={
                                                    "color": "#10357e",
                                                    "marginBottom": "8px",
                                                },
                                            ),
                                            html.P(
                                                ", ".join(config.get("gemeenten", []))
                                                or "Niet gespecificeerd"
                                            ),
                                        ],
                                        style={"marginBottom": "20px"},
                                    ),
                                    html.Div(
                                        [
                                            html.H4(
                                                "Check-in / Check-out",
                                                style={
                                                    "color": "#10357e",
                                                    "marginBottom": "8px",
                                                },
                                            ),
                                            html.P(
                                                f"Check-in: {config.get('check_in', 'N/A')}"
                                            ),
                                            html.P(
                                                f"Check-out: {config.get('check_out', 'N/A')}"
                                            ),
                                        ],
                                        style={"marginBottom": "20px"},
                                    ),
                                    html.Div(
                                        [
                                            html.H4(
                                                "Gasten",
                                                style={
                                                    "color": "#10357e",
                                                    "marginBottom": "8px",
                                                },
                                            ),
                                            html.P(
                                                f"Aantal: {config.get('guests', 'N/A')}"
                                            ),
                                        ],
                                        style={"marginBottom": "20px"},
                                    ),
                                    html.Div(
                                        [
                                            html.H4(
                                                "Volledige Configuratie (JSON)",
                                                style={
                                                    "color": "#10357e",
                                                    "marginBottom": "8px",
                                                },
                                            ),
                                            html.Pre(
                                                json.dumps(
                                                    config, indent=2, ensure_ascii=False
                                                ),
                                                style={
                                                    "background": "#f5f5f5",
                                                    "padding": "16px",
                                                    "borderRadius": "8px",
                                                    "overflow": "auto",
                                                    "fontSize": "13px",
                                                    "fontFamily": "monospace",
                                                },
                                            ),
                                        ]
                                    ),
                                ],
                                style={
                                    "background": "white",
                                    "padding": "24px",
                                    "borderRadius": "8px",
                                    "border": "1px solid #e0e0e0",
                                },
                            ),
                        ]
                    )
                else:
                    return html.Div(
                        "Geen configuratie bestand gevonden",
                        style={"padding": "20px", "color": "#888"},
                    )
            except Exception as e:
                return html.Div(
                    f"Fout bij laden configuratie: {str(e)}",
                    style={"padding": "20px", "color": "#ef5350"},
                )

        return html.Div("Onbekende tab", style={"padding": "20px", "color": "#888"})

    @app.callback(
        Output("runs-container", "children"),
        [
            Input("status-filter", "value"),
            Input("source-filter", "value"),
            Input("search-input", "value"),
            Input("sort-dropdown", "value"),
        ],
        prevent_initial_call=True,
    )
    def filter_runs(status_value, source_value, search_value, sort_value):
        from dashboard.dash_helpers import add_source_to_run, get_runs_by_source
        from dashboard.dash_components import source_chip

        runs = get_all_runs(DATA_DIR) if os.path.exists(DATA_DIR) else []
        app.cached_runs = runs  # Update cache

        # Add source information to all runs
        runs = [add_source_to_run(run) for run in runs]
        filtered = runs

        # Filter by status
        if status_value and len(status_value) > 0:
            allowed_statuses = []
            for status in status_value:
                if status == "completed":
                    allowed_statuses.extend(["completed", "legacy"])
                else:
                    allowed_statuses.append(status)
            filtered = [r for r in filtered if r.get("status") in allowed_statuses]

        # Filter by data source
        filtered = get_runs_by_source(filtered, source_value)

        # Filter by search text
        if search_value:
            s = str(search_value).lower()
            filtered = [
                r
                for r in filtered
                if s in r.get("run_name", "").lower()
                or s in str(r.get("params", {}).get("gemeenten", "")).lower()
            ]

        runs_with_preview = []
        for run in filtered:
            preview = load_run_preview(run)
            runs_with_preview.append(
                {
                    "run": run,
                    "preview": preview,
                }
            )

        if sort_value == "date_desc":
            runs_with_preview.sort(
                key=lambda x: x["preview"]["timestamp"], reverse=True
            )
        elif sort_value == "date_asc":
            runs_with_preview.sort(
                key=lambda x: x["preview"]["timestamp"], reverse=False
            )
        elif sort_value == "listings_desc":
            runs_with_preview.sort(
                key=lambda x: x["preview"]["listings"]
                if isinstance(x["preview"]["listings"], int)
                else 0,
                reverse=True,
            )
        elif sort_value == "listings_asc":
            runs_with_preview.sort(
                key=lambda x: x["preview"]["listings"]
                if isinstance(x["preview"]["listings"], int)
                else 0,
                reverse=False,
            )
        elif sort_value == "name_asc":
            runs_with_preview.sort(key=lambda x: x["preview"]["gemeenten"].lower())
        elif sort_value == "name_desc":
            runs_with_preview.sort(
                key=lambda x: x["preview"]["gemeenten"].lower(), reverse=True
            )

        cards = []
        for item in runs_with_preview:
            run = item["run"]
            preview = item["preview"]
            row = {
                "gemeenten": preview["gemeenten"],
                "moment": preview["timestamp"],
                "status": preview["status"],
                "listings": preview["listings"],
                "periode": preview["period"],
                "run_name": run["run_name"],
                "has_excel": preview["excel_path"] is not None,
            }

            cards.append(
                html.Div(
                    [
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
                                                    },
                                                ),
                                                source_chip(
                                                    run.get("source", "airbnb"),
                                                    show_label=False,
                                                ),
                                            ],
                                            style={
                                                "display": "flex",
                                                "alignItems": "center",
                                                "gap": "8px",
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
                                    style={"flex": "1", "textAlign": "right"},
                                ),
                            ],
                            style={
                                "display": "flex",
                                "justifyContent": "space-between",
                                "marginBottom": "16px",
                            },
                        ),
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
                                (
                                    html.A(
                                        "Download Excel",
                                        href=f"/download?run={row['run_name']}",
                                        style={
                                            "color": "#da9a36",
                                            "textDecoration": "none",
                                            "fontSize": "14px",
                                            "fontWeight": "500",
                                            "padding": "10px 20px",
                                            "display": "inline-block",
                                        },
                                    )
                                    if row["has_excel"]
                                    else None
                                ),
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
                )
            )

        return cards

    # Update time range display text when slider changes
    @app.callback(
        Output("time-range-display", "children"),
        [Input("time-range-slider", "value")],
        [State("scan-dates-store", "data")],
        prevent_initial_call=True,
    )
    def update_time_range_display(slider_value, scan_dates_str):
        if not scan_dates_str or not slider_value:
            return "Geen metingen beschikbaar"

        from datetime import datetime

        # Convert string dates back to date objects
        scan_dates = [datetime.fromisoformat(d).date() for d in scan_dates_str]

        start_idx, end_idx = slider_value
        start_date = scan_dates[start_idx]
        end_date = scan_dates[end_idx]

        if start_date == end_date:
            return f"Metingen van: {start_date.strftime('%d-%m-%Y')}"
        else:
            num_dates = end_idx - start_idx + 1
            return f"Metingen van {start_date.strftime('%d-%m-%Y')} tot {end_date.strftime('%d-%m-%Y')} ({num_dates} datums)"

    # Update map based on time range slider
    @app.callback(
        Output("map-iframe", "srcDoc"),
        [Input("time-range-slider", "value")],
        [State("scan-dates-store", "data"), State("current-run", "data")],
        prevent_initial_call=True,
    )
    def update_map_by_time_range(slider_value, scan_dates_str, current_run_data):
        if not scan_dates_str or not slider_value or not current_run_data:
            raise PreventUpdate

        from datetime import datetime
        import pandas as pd

        run_path = current_run_data.get("run_path")
        if not run_path:
            raise PreventUpdate

        # Load the data
        data_cache_key = f"{run_path}_data"
        if data_cache_key in app.run_data_cache:
            df = app.run_data_cache[data_cache_key]
        else:
            df = load_run_data(run_path)
            app.run_data_cache[data_cache_key] = df

        if df is None or df.empty:
            raise PreventUpdate

        # Convert string dates back to date objects
        scan_dates = [datetime.fromisoformat(d).date() for d in scan_dates_str]

        # Get selected date range
        start_idx, end_idx = slider_value
        selected_dates = scan_dates[start_idx : end_idx + 1]

        # Filter data by selected dates
        df["scan_checkin_date"] = pd.to_datetime(df["scan_checkin"]).dt.date
        df_filtered = df[df["scan_checkin_date"].isin(selected_dates)]

        # Prepare map data (unique listings with availability metrics)
        if not df_filtered.empty:
            df_map = df_filtered.drop_duplicates("room_id").copy()
            
            # Add required columns if missing
            for col, default in [
                ("availability_rate", 100.0),
                ("days_available", 1),
                ("total_days", 1),
            ]:
                if col not in df_map.columns:
                    df_map[col] = default
        else:
            df_map = df_filtered

        # Generate new map with filtered data
        try:
            from src.visualization.map_creator import create_map
            import geopandas as gpd
            from pathlib import Path

            if create_map and not df_map.empty:
                # Load config
                config_path = os.path.join(run_path, "config.json")
                config = {}
                gemeenten = []
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        config = json.load(f)
                        gemeenten = config.get("gemeenten", [])

                # Load gemeente boundaries
                PROJECT_ROOT = Path(__file__).parent.parent.parent
                GPKG_PATH = str(
                    PROJECT_ROOT / "assets" / "BestuurlijkeGebieden_2025.gpkg"
                )
                gdf_gemeenten = gpd.read_file(GPKG_PATH, layer="gemeentegebied")

                # Create the map with filtered data (use df_map with required columns)
                map_obj = create_map(df_map, gdf_gemeenten, gemeenten)
                if map_obj:
                    return map_obj.get_root().render()
        except Exception as e:
            print(f"Error creating filtered map: {e}")

        # If map creation fails, return original map
        map_html_path = os.path.join(run_path, "map.html")
        if os.path.exists(map_html_path):
            with open(map_html_path, "r", encoding="utf-8") as f:
                return f.read()

        raise PreventUpdate

    # Details: update map based on filters - TEMPORARILY DISABLED FOR DEBUG
