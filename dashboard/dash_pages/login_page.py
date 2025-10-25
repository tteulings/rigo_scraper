"""Login Page"""

from pathlib import Path
from dash import html, dcc

# Project paths
PROJECT_ROOT = Path(
    __file__
).parent.parent.parent  # Go up to airbnb/ from dashboard/dash_pages/
LOGO_PATH = PROJECT_ROOT / "assets" / "rigo-logo.svg"


def create_login_page():
    """Create the login page layout"""
    return html.Div(
        [
            html.Div(
                [
                    html.Img(
                        src=f"/assets/{LOGO_PATH.name}",
                        style={"width": "220px", "marginBottom": "20px"},
                    )
                    if LOGO_PATH.exists()
                    else None,
                    html.H2("Airbnb Scraper Dashboard", style={"color": "#10357e"}),
                    html.Div(
                        [
                            dcc.Input(
                                id="password",
                                type="password",
                                placeholder="Wachtwoord",
                                style={
                                    "width": "100%",
                                    "padding": "10px",
                                    "border": "2px solid #10357e",
                                    "borderRadius": "8px",
                                },
                            ),
                            html.Button(
                                "Inloggen",
                                id="login-btn",
                                n_clicks=0,
                                style={
                                    "width": "100%",
                                    "marginTop": "10px",
                                    "background": "#da9a36",
                                    "color": "white",
                                    "padding": "10px",
                                    "border": "none",
                                    "borderRadius": "8px",
                                    "fontWeight": "bold",
                                },
                            ),
                            html.Div(
                                id="login-error",
                                style={"color": "#c62828", "marginTop": "8px"},
                            ),
                        ],
                        style={"width": "320px"},
                    ),
                ],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "minHeight": "90vh",
                },
            )
        ]
    )
