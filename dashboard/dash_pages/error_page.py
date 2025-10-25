"""Error and 404 Pages"""

from dash import html
import dash_bootstrap_components as dbc
from dashboard.dash_components import create_sidebar


def create_404_page():
    """Create a 404 not found page"""
    return html.Div(
        [
            create_sidebar(""),
            html.Div(
                [
                    html.Div(
                        [
                            html.I(
                                className="material-icons",
                                children="error_outline",
                                style={
                                    "fontSize": "72px",
                                    "color": "#c62828",
                                    "marginBottom": "20px",
                                },
                            ),
                            html.H1(
                                "404 - Pagina Niet Gevonden", style={"color": "#2b3e50"}
                            ),
                            html.P(
                                "De pagina die u zoekt bestaat niet.",
                                style={
                                    "fontSize": "18px",
                                    "color": "#666",
                                    "marginBottom": "30px",
                                },
                            ),
                            dbc.Button(
                                "Terug naar Dashboard",
                                href="/dashboard",
                                color="primary",
                                size="lg",
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "minHeight": "80vh",
                            "textAlign": "center",
                        },
                    )
                ],
                style={"marginLeft": "250px", "padding": "20px"},
            ),
        ]
    )


def create_error_page(error_message: str):
    """Create a generic error page

    Args:
        error_message: The error message to display
    """
    return html.Div(
        [
            create_sidebar(""),
            html.Div(
                [
                    html.Div(
                        [
                            html.I(
                                className="material-icons",
                                children="error",
                                style={
                                    "fontSize": "72px",
                                    "color": "#c62828",
                                    "marginBottom": "20px",
                                },
                            ),
                            html.H1(
                                "Er is een fout opgetreden", style={"color": "#2b3e50"}
                            ),
                            html.P(
                                error_message,
                                style={
                                    "fontSize": "16px",
                                    "color": "#666",
                                    "marginBottom": "30px",
                                    "maxWidth": "600px",
                                    "backgroundColor": "#f5f5f5",
                                    "padding": "20px",
                                    "borderRadius": "8px",
                                    "border": "1px solid #ddd",
                                },
                            ),
                            dbc.Button(
                                "Terug naar Dashboard",
                                href="/dashboard",
                                color="primary",
                                size="lg",
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "minHeight": "80vh",
                            "textAlign": "center",
                        },
                    )
                ],
                style={"marginLeft": "250px", "padding": "20px"},
            ),
        ]
    )
