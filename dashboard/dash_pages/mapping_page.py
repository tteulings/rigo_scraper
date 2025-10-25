"""Mapping Configuration Page"""
from dash import html, dcc
import dash_bootstrap_components as dbc
from dashboard.dash_components import create_sidebar


def create_mapping_page():
    """Create the room type mapping configuration page"""
    # Load room type mappings
    try:
        from src.config.room_type_config import (
            ROOM_TYPE_MAPPING,
            STANDARD_PROPERTY_TYPES,
        )
    except ImportError:
        ROOM_TYPE_MAPPING = {}
        STANDARD_PROPERTY_TYPES = []
    
    return html.Div(
                    [
                        create_sidebar("/mapping"),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H2(
                                            [
                                                html.I(
                                                    "settings_applications",
                                                    className="material-icons",
                                                    style={
                                                        "fontSize": "32px",
                                                        "marginRight": "12px",
                                                        "verticalAlign": "middle",
                                                    },
                                                ),
                                                html.Span(
                                                    "Mapping Config",
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
                                            f"{len(ROOM_TYPE_MAPPING)} mappings → {len(STANDARD_PROPERTY_TYPES)} categorieën",
                                            style={
                                                "color": "rgba(255,255,255,0.8)",
                                                "fontSize": "13px",
                                                "fontWeight": "500",
                                                "marginTop": "8px",
                                            },
                                        ),
                                    ],
                                    style={
                                        "background": "linear-gradient(135deg, #1565c0 0%, #10357e 100%)",
                                        "padding": "32px",
                                        "borderRadius": "12px",
                                        "marginBottom": "24px",
                                        "boxShadow": "0 4px 6px rgba(0,0,0,0.1)",
                                    },
                                ),
                                # Info card
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.I(
                                                    "info",
                                                    className="material-icons",
                                                    style={
                                                        "fontSize": "20px",
                                                        "marginRight": "12px",
                                                        "color": "#0288d1",
                                                        "verticalAlign": "middle",
                                                    },
                                                ),
                                                html.Strong(
                                                    "Room Type Classificatie",
                                                    style={"verticalAlign": "middle"},
                                                ),
                                            ],
                                            style={
                                                "marginBottom": "12px",
                                                "display": "flex",
                                                "alignItems": "center",
                                            },
                                        ),
                                        html.P(
                                            "De scraper classificeert accommodaties automatisch naar gestandaardiseerde Airbnb categorieën. "
                                            "Dit maakt analyses consistent en vergelijkbaar over tijd.",
                                            style={
                                                "fontSize": "14px",
                                                "color": "#616161",
                                                "margin": 0,
                                            },
                                        ),
                                    ],
                                    style={
                                        "background": "#e3f2fd",
                                        "padding": "20px",
                                        "borderRadius": "8px",
                                        "border": "1px solid #90caf9",
                                        "marginBottom": "24px",
                                    },
                                ),
                                # Tabs for View and Add/Edit
                                dcc.Tabs(
                                    id="mapping-tabs",
                                    value="tab-view",
                                    children=[
                                        dcc.Tab(
                                            label="Bekijk Mappings",
                                            value="tab-view",
                                            style={
                                                "padding": "12px 24px",
                                                "fontWeight": "500",
                                            },
                                            selected_style={
                                                "padding": "12px 24px",
                                                "fontWeight": "600",
                                                "borderTop": "3px solid #1565c0",
                                            },
                                        ),
                                        dcc.Tab(
                                            label="Toevoegen/Bewerken",
                                            value="tab-edit",
                                            style={
                                                "padding": "12px 24px",
                                                "fontWeight": "500",
                                            },
                                            selected_style={
                                                "padding": "12px 24px",
                                                "fontWeight": "600",
                                                "borderTop": "3px solid #1565c0",
                                            },
                                        ),
                                    ],
                                    style={"marginBottom": "24px"},
                                ),
                                # Tab content container
                                html.Div(id="mapping-tab-content"),
                                # Hidden stores for state
                                dcc.Store(id="mapping-filter-search", data=""),
                                dcc.Store(id="mapping-filter-category", data="Alle"),
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
    
