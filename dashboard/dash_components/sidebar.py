"""Sidebar component for Dash dashboard"""

import os
from dash import html, dcc
from pathlib import Path

# Import project paths
PROJECT_ROOT = Path(
    __file__
).parent.parent.parent  # Go up to airbnb/ from dashboard/dash_components/
LOGO_PATH = PROJECT_ROOT / "assets" / "rigo-logo.svg"
DATA_DIR = str(PROJECT_ROOT / "outputs" / "data")


def create_sidebar(current_page="/dashboard"):
    """Create sidebar with navigation"""
    # Get runs count for stats
    runs = []
    try:
        from dashboard.dash_helpers import get_all_runs

        runs = get_all_runs(DATA_DIR) if os.path.exists(DATA_DIR) else []
    except Exception:
        pass

    nav_items = [
        {"label": "Resultaten", "path": "/dashboard", "icon": "dashboard"},
        {"label": "Nieuwe Run", "path": "/nieuwe_run", "icon": "add_circle"},
        {
            "label": "Mapping Config",
            "path": "/mapping",
            "icon": "settings_applications",
        },
        {"label": "Instellingen", "path": "/instellingen", "icon": "settings"},
    ]

    # Logo section
    logo_section = html.Div(
        [
            (
                html.Img(
                    src="/assets/rigo-logo.svg",
                    style={
                        "width": "100%",
                        "maxWidth": "180px",
                        "height": "auto",
                        "padding": "8px",
                    },
                )
                if LOGO_PATH.exists()
                else html.H3(
                    "Airbnb Scraper",
                    style={"margin": "0", "color": "white", "textAlign": "center"},
                )
            ),
        ],
        style={
            "padding": "20px",
            "borderBottom": "1px solid rgba(255,255,255,0.1)",
            "display": "flex",
            "justifyContent": "center",
            "alignItems": "center",
        },
    )

    return html.Div(
        [
            logo_section,
            # Navigation
            html.Div(
                [
                    dcc.Link(
                        html.Div(
                            [
                                html.I(
                                    item["icon"],
                                    className="material-icons",
                                    style={
                                        "fontSize": "20px",
                                        "marginRight": "12px",
                                    },
                                ),
                                html.Span(item["label"]),
                            ],
                            style={
                                "padding": "12px 20px",
                                "cursor": "pointer",
                                "display": "flex",
                                "alignItems": "center",
                                "background": (
                                    "rgba(255,255,255,0.15)"
                                    if item["path"] == current_page
                                    else "transparent"
                                ),
                                "borderLeft": (
                                    "3px solid #da9a36"
                                    if item["path"] == current_page
                                    else "3px solid transparent"
                                ),
                                "transition": "all 0.2s",
                                "fontWeight": "500"
                                if item["path"] == current_page
                                else "normal",
                            },
                        ),
                        href=item["path"],
                        style={
                            "textDecoration": "none",
                            "color": "white",
                            "fontSize": "15px",
                        },
                    )
                    for item in nav_items
                ],
                style={"marginTop": "20px"},
            ),
            html.Div(
                [
                    html.Div(
                        "Overzicht",
                        style={
                            "fontSize": "14px",
                            "fontWeight": "bold",
                            "marginBottom": "12px",
                            "color": "rgba(255,255,255,0.7)",
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                str(len(runs)),
                                style={
                                    "fontSize": "32px",
                                    "fontWeight": "bold",
                                    "color": "#da9a36",
                                },
                            ),
                            html.Div(
                                "Beschikbare Runs",
                                style={
                                    "fontSize": "12px",
                                    "color": "rgba(255,255,255,0.6)",
                                },
                            ),
                        ],
                        style={
                            "background": "rgba(255,255,255,0.05)",
                            "padding": "16px",
                            "borderRadius": "8px",
                        },
                    ),
                ],
                style={"padding": "20px", "marginTop": "auto"},
            ),
            html.Div(
                dcc.Link(
                    html.Div(
                        [
                            html.I(
                                "logout",
                                className="material-icons",
                                style={
                                    "fontSize": "20px",
                                    "marginRight": "8px",
                                },
                            ),
                            html.Span("Uitloggen"),
                        ],
                        style={
                            "padding": "12px 20px",
                            "cursor": "pointer",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "background": "rgba(244,67,54,0.15)",
                            "transition": "all 0.2s",
                            "fontWeight": "500",
                        },
                    ),
                    href="/",
                    id="logout-link",
                    style={
                        "textDecoration": "none",
                        "color": "#ef5350",
                        "fontSize": "15px",
                    },
                ),
                style={
                    "borderTop": "1px solid rgba(255,255,255,0.1)",
                    "padding": "10px 0",
                },
            ),
        ],
        style={
            "width": "280px",
            "height": "100vh",
            "background": "linear-gradient(180deg, #10357e 0%, #0a2456 100%)",
            "position": "fixed",
            "left": "0",
            "top": "0",
            "display": "flex",
            "flexDirection": "column",
            "boxShadow": "2px 0 10px rgba(0,0,0,0.1)",
            "zIndex": "1000",
        },
    )
