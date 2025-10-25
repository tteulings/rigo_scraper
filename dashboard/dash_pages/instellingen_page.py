"""Settings/Instellingen Page"""
from pathlib import Path
from dash import html, dcc
import dash_bootstrap_components as dbc
from dashboard.dash_components import create_sidebar

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
GPKG_PATH = str(PROJECT_ROOT / "assets" / "BestuurlijkeGebieden_2025.gpkg")


def create_instellingen_page(data_dir: str):
    """Create the settings page
    
    Args:
        data_dir: Path to the data directory
    """
    DATA_DIR = data_dir
    
    return html.Div(
                    [
                        create_sidebar("/instellingen"),
                        html.Div(
                            [
                                html.H2("Instellingen", style={"marginBottom": "20px"}),
                                html.Div(
                                    [
                                        html.H4(
                                            "Data Directory", style={"marginBottom": "12px"}
                                        ),
                                        html.P(
                                            f"📁 {DATA_DIR}",
                                            style={
                                                "fontSize": "14px",
                                                "color": "#616161",
                                                "fontFamily": "monospace",
                                            },
                                        ),
                                        html.Hr(style={"margin": "20px 0"}),
                                        html.H4(
                                            "Geopackage", style={"marginBottom": "12px"}
                                        ),
                                        html.P(
                                            f"📁 {GPKG_PATH}",
                                            style={
                                                "fontSize": "14px",
                                                "color": "#616161",
                                                "fontFamily": "monospace",
                                            },
                                        ),
                                    ],
                                    style={
                                        "background": "white",
                                        "padding": "32px",
                                        "borderRadius": "8px",
                                        "border": "1px solid #e0e0e0",
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
    
