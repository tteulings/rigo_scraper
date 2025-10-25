"""Nieuwe Run Page"""

from datetime import date, timedelta
from dash import html, dcc
from dashboard.dash_helpers import (
    load_gemeenten_list,
    create_gemeente_selection_map_html,
)
from dashboard.dash_components import create_sidebar


def create_nieuwe_run_page():
    """Create the nieuwe run (new scraping job) page"""
    gemeenten_options = load_gemeenten_list()

    return html.Div(
        [
            create_sidebar("/nieuwe_run"),
            html.Div(
                [
                    # Header with gradient
                    html.Div(
                        [
                            html.H2(
                                [
                                    html.I(
                                        "add_circle",
                                        className="material-icons",
                                        style={
                                            "fontSize": "32px",
                                            "marginRight": "12px",
                                            "verticalAlign": "middle",
                                        },
                                    ),
                                    html.Span(
                                        "Nieuwe Run",
                                        style={"verticalAlign": "middle"},
                                    ),
                                ],
                                style={
                                    "margin": 0,
                                    "display": "flex",
                                    "alignItems": "center",
                                    "color": "white",
                                    "fontSize": "28px",
                                    "fontWeight": "600",
                                },
                            ),
                            html.Div(
                                "Configureer en start een nieuwe scraping run",
                                style={
                                    "color": "rgba(255,255,255,0.9)",
                                    "fontSize": "14px",
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
                    # Configuration and map columns
                    html.Div(
                        [
                            # Left column - Configuration
                            html.Div(
                                [
                                    # Data Source Selection Card
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.I(
                                                        "source",
                                                        className="material-icons",
                                                        style={
                                                            "fontSize": "20px",
                                                            "marginRight": "8px",
                                                            "color": "#10357e",
                                                        },
                                                    ),
                                                    html.Span(
                                                        "Data Bron",
                                                        style={
                                                            "fontSize": "16px",
                                                            "fontWeight": "600",
                                                            "color": "#10357e",
                                                        },
                                                    ),
                                                ],
                                                style={
                                                    "display": "flex",
                                                    "alignItems": "center",
                                                    "marginBottom": "16px",
                                                },
                                            ),
                                            dcc.Dropdown(
                                                id="source-dropdown",
                                                options=[
                                                    {
                                                        "label": "Airbnb",
                                                        "value": "airbnb",
                                                    },
                                                    {
                                                        "label": "Funda (Binnenkort)",
                                                        "value": "funda",
                                                        "disabled": True,
                                                    },
                                                ],
                                                value="airbnb",
                                                clearable=False,
                                                searchable=False,
                                            ),
                                            html.Div(
                                                "Selecteer de databron voor deze scraping run",
                                                style={
                                                    "fontSize": "13px",
                                                    "color": "#666",
                                                    "marginTop": "8px",
                                                },
                                            ),
                                        ],
                                        style={
                                            "background": "white",
                                            "padding": "20px",
                                            "borderRadius": "8px",
                                            "border": "1px solid #e0e0e0",
                                            "marginBottom": "20px",
                                            "boxShadow": "0 1px 3px rgba(0,0,0,0.05)",
                                        },
                                    ),
                                    # Gemeente Selection Card
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.I(
                                                        "location_on",
                                                        className="material-icons",
                                                        style={
                                                            "fontSize": "20px",
                                                            "marginRight": "8px",
                                                            "color": "#10357e",
                                                        },
                                                    ),
                                                    html.Span(
                                                        "Gemeenten",
                                                        style={
                                                            "fontSize": "16px",
                                                            "fontWeight": "600",
                                                            "color": "#10357e",
                                                        },
                                                    ),
                                                ],
                                                style={
                                                    "display": "flex",
                                                    "alignItems": "center",
                                                    "marginBottom": "16px",
                                                },
                                            ),
                                            dcc.Dropdown(
                                                id="gemeenten-dropdown",
                                                options=[
                                                    {"label": g, "value": g}
                                                    for g in gemeenten_options
                                                ],
                                                multi=True,
                                                placeholder="🔍 Zoek en selecteer gemeenten...",
                                            ),
                                        ],
                                        style={
                                            "background": "white",
                                            "padding": "24px",
                                            "borderRadius": "12px",
                                            "border": "1px solid #e0e0e0",
                                            "marginBottom": "16px",
                                            "boxShadow": "0 2px 4px rgba(0,0,0,0.05)",
                                        },
                                    ),
                                    # Period Configuration Card
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.I(
                                                        "date_range",
                                                        className="material-icons",
                                                        style={
                                                            "fontSize": "20px",
                                                            "marginRight": "8px",
                                                            "color": "#10357e",
                                                        },
                                                    ),
                                                    html.Span(
                                                        "Periode & Planning",
                                                        style={
                                                            "fontSize": "16px",
                                                            "fontWeight": "600",
                                                            "color": "#10357e",
                                                        },
                                                    ),
                                                ],
                                                style={
                                                    "display": "flex",
                                                    "alignItems": "center",
                                                    "marginBottom": "16px",
                                                },
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Start Datum",
                                                                style={
                                                                    "fontSize": "13px",
                                                                    "fontWeight": "500",
                                                                    "color": "#616161",
                                                                    "display": "block",
                                                                    "marginBottom": "6px",
                                                                },
                                                            ),
                                                            dcc.DatePickerSingle(
                                                                id="period-start",
                                                                date=date.today(),
                                                                style={"width": "100%"},
                                                            ),
                                                        ],
                                                        style={
                                                            "flex": 1,
                                                            "marginRight": "8px",
                                                        },
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Eind Datum",
                                                                style={
                                                                    "fontSize": "13px",
                                                                    "fontWeight": "500",
                                                                    "color": "#616161",
                                                                    "display": "block",
                                                                    "marginBottom": "6px",
                                                                },
                                                            ),
                                                            dcc.DatePickerSingle(
                                                                id="period-end",
                                                                date=(
                                                                    date.today()
                                                                    + timedelta(days=30)
                                                                ),
                                                                style={"width": "100%"},
                                                            ),
                                                        ],
                                                        style={
                                                            "flex": 1,
                                                            "marginLeft": "8px",
                                                        },
                                                    ),
                                                ],
                                                style={
                                                    "display": "flex",
                                                    "gap": "16px",
                                                    "marginBottom": "16px",
                                                },
                                            ),
                                            html.Label(
                                                "Planning Mode",
                                                style={
                                                    "fontSize": "13px",
                                                    "fontWeight": "500",
                                                    "color": "#616161",
                                                    "display": "block",
                                                    "marginBottom": "8px",
                                                },
                                            ),
                                            dcc.RadioItems(
                                                id="schedule-mode",
                                                options=[
                                                    {
                                                        "label": "📆 Interval",
                                                        "value": "interval",
                                                    },
                                                    {
                                                        "label": "📅 Weekdagen",
                                                        "value": "weekdays",
                                                    },
                                                    {
                                                        "label": "🗓️ Maandelijks",
                                                        "value": "monthly",
                                                    },
                                                ],
                                                value="interval",
                                                inline=True,
                                                style={"marginBottom": "12px"},
                                                inputStyle={"marginRight": "6px"},
                                                labelStyle={
                                                    "marginRight": "16px",
                                                    "fontSize": "14px",
                                                },
                                            ),
                                            # Schedule-specific config
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Interval (dagen)",
                                                        style={
                                                            "fontSize": "13px",
                                                            "fontWeight": "500",
                                                            "color": "#616161",
                                                            "display": "block",
                                                            "marginBottom": "6px",
                                                        },
                                                    ),
                                                    dcc.Input(
                                                        id="measurement-interval",
                                                        type="number",
                                                        min=1,
                                                        max=30,
                                                        value=7,
                                                        style={
                                                            "width": "100%",
                                                            "padding": "8px",
                                                            "border": "1px solid #e0e0e0",
                                                            "borderRadius": "6px",
                                                            "fontSize": "14px",
                                                        },
                                                    ),
                                                ],
                                                id="interval-config",
                                                style={"display": "block"},
                                            ),
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Selecteer Dagen",
                                                        style={
                                                            "fontSize": "13px",
                                                            "fontWeight": "500",
                                                            "color": "#616161",
                                                            "display": "block",
                                                            "marginBottom": "6px",
                                                        },
                                                    ),
                                                    dcc.Dropdown(
                                                        id="days-of-week",
                                                        options=[
                                                            {
                                                                "label": l,
                                                                "value": v,
                                                            }
                                                            for l, v in [
                                                                ("Maandag", 0),
                                                                ("Dinsdag", 1),
                                                                ("Woensdag", 2),
                                                                (
                                                                    "Donderdag",
                                                                    3,
                                                                ),
                                                                ("Vrijdag", 4),
                                                                ("Zaterdag", 5),
                                                                ("Zondag", 6),
                                                            ]
                                                        ],
                                                        value=[4],
                                                        multi=True,
                                                        style={"fontSize": "14px"},
                                                    ),
                                                ],
                                                id="weekday-config",
                                                style={"display": "none"},
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        "ℹ️ Eerste voorkomen van geselecteerde dag(en) per maand",
                                                        style={
                                                            "fontSize": "12px",
                                                            "color": "#616161",
                                                            "padding": "8px 12px",
                                                            "background": "#f5f5f5",
                                                            "borderRadius": "6px",
                                                            "marginTop": "8px",
                                                        },
                                                    ),
                                                ],
                                                id="monthly-config",
                                                style={"display": "none"},
                                            ),
                                            html.Div(
                                                id="preview-container",
                                                style={"marginTop": "16px"},
                                            ),
                                        ],
                                        style={
                                            "background": "white",
                                            "padding": "24px",
                                            "borderRadius": "12px",
                                            "border": "1px solid #e0e0e0",
                                            "marginBottom": "16px",
                                            "boxShadow": "0 2px 4px rgba(0,0,0,0.05)",
                                        },
                                    ),
                                    # Advanced Settings (collapsed by default)
                                    html.Details(
                                        [
                                            html.Summary(
                                                [
                                                    html.I(
                                                        "settings",
                                                        className="material-icons",
                                                        style={
                                                            "fontSize": "18px",
                                                            "marginRight": "8px",
                                                            "verticalAlign": "middle",
                                                        },
                                                    ),
                                                    html.Span(
                                                        "Geavanceerde Instellingen",
                                                        style={
                                                            "fontSize": "15px",
                                                            "fontWeight": "500",
                                                        },
                                                    ),
                                                ],
                                                style={
                                                    "cursor": "pointer",
                                                    "color": "#10357e",
                                                    "padding": "16px",
                                                    "background": "white",
                                                    "borderRadius": "12px",
                                                    "border": "1px solid #e0e0e0",
                                                    "marginBottom": "16px",
                                                    "boxShadow": "0 2px 4px rgba(0,0,0,0.05)",
                                                },
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Nachten (komma-gescheiden)"
                                                            ),
                                                            dcc.Input(
                                                                id="nights-input",
                                                                type="text",
                                                                value="3,7",
                                                                style={"width": "100%"},
                                                            ),
                                                            html.Label(
                                                                "Gasten (komma-gescheiden)",
                                                                style={
                                                                    "marginTop": "8px"
                                                                },
                                                            ),
                                                            dcc.Input(
                                                                id="guests-input",
                                                                type="text",
                                                                value="2",
                                                                style={"width": "100%"},
                                                            ),
                                                            html.Label(
                                                                "Min Prijs (€)",
                                                                style={
                                                                    "marginTop": "8px"
                                                                },
                                                            ),
                                                            dcc.Input(
                                                                id="price-min",
                                                                type="number",
                                                                value=0,
                                                                style={"width": "100%"},
                                                            ),
                                                            html.Label(
                                                                "Max Prijs (€)",
                                                                style={
                                                                    "marginTop": "8px"
                                                                },
                                                            ),
                                                            dcc.Input(
                                                                id="price-max",
                                                                type="number",
                                                                value=0,
                                                                style={"width": "100%"},
                                                            ),
                                                        ],
                                                        style={
                                                            "flex": 1,
                                                            "marginRight": "10px",
                                                        },
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "API Herhalingen"
                                                            ),
                                                            dcc.Input(
                                                                id="num-repeat-calls",
                                                                type="number",
                                                                min=1,
                                                                max=5,
                                                                value=2,
                                                                style={"width": "100%"},
                                                            ),
                                                            html.Label(
                                                                "Zoom Level",
                                                                style={
                                                                    "marginTop": "8px"
                                                                },
                                                            ),
                                                            dcc.Input(
                                                                id="zoom-value",
                                                                type="number",
                                                                min=1,
                                                                max=20,
                                                                value=12,
                                                                style={"width": "100%"},
                                                            ),
                                                            html.Label(
                                                                "Workers",
                                                                style={
                                                                    "marginTop": "8px"
                                                                },
                                                            ),
                                                            dcc.Input(
                                                                id="max-workers",
                                                                type="number",
                                                                min=1,
                                                                max=10,
                                                                value=1,
                                                                style={"width": "100%"},
                                                            ),
                                                            html.Label(
                                                                "Valuta",
                                                                style={
                                                                    "marginTop": "8px"
                                                                },
                                                            ),
                                                            dcc.Dropdown(
                                                                id="currency",
                                                                options=[
                                                                    {
                                                                        "label": c,
                                                                        "value": c,
                                                                    }
                                                                    for c in [
                                                                        "EUR",
                                                                        "USD",
                                                                        "GBP",
                                                                    ]
                                                                ],
                                                                value="EUR",
                                                            ),
                                                            html.Label(
                                                                "Taal",
                                                                style={
                                                                    "marginTop": "8px"
                                                                },
                                                            ),
                                                            dcc.Dropdown(
                                                                id="language",
                                                                options=[
                                                                    {
                                                                        "label": l,
                                                                        "value": l,
                                                                    }
                                                                    for l in [
                                                                        "nl",
                                                                        "en",
                                                                        "de",
                                                                    ]
                                                                ],
                                                                value="nl",
                                                            ),
                                                        ],
                                                        style={
                                                            "flex": 1,
                                                            "marginLeft": "10px",
                                                        },
                                                    ),
                                                ],
                                                style={
                                                    "display": "flex",
                                                    "gap": "20px",
                                                    "marginTop": "10px",
                                                },
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Scan delay (sec)"
                                                            ),
                                                            dcc.Input(
                                                                id="delay-between-scans",
                                                                type="number",
                                                                min=0,
                                                                max=10,
                                                                step=0.5,
                                                                value=3.0,
                                                                style={"width": "100%"},
                                                            ),
                                                        ],
                                                        style={
                                                            "flex": 1,
                                                            "marginRight": "10px",
                                                        },
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Call delay (sec)"
                                                            ),
                                                            dcc.Input(
                                                                id="delay-between-calls",
                                                                type="number",
                                                                min=0,
                                                                max=5,
                                                                step=0.1,
                                                                value=1.5,
                                                                style={"width": "100%"},
                                                            ),
                                                        ],
                                                        style={
                                                            "flex": 1,
                                                            "marginLeft": "10px",
                                                        },
                                                    ),
                                                ],
                                                style={
                                                    "display": "flex",
                                                    "gap": "20px",
                                                    "marginTop": "10px",
                                                },
                                            ),
                                        ],
                                        open=False,
                                        style={"marginTop": "8px"},
                                    ),
                                    # Start Button
                                    html.Button(
                                        [
                                            html.I(
                                                "rocket_launch",
                                                className="material-icons",
                                                style={
                                                    "fontSize": "20px",
                                                    "marginRight": "8px",
                                                    "verticalAlign": "middle",
                                                },
                                            ),
                                            html.Span(
                                                "Start Scraping",
                                                style={"verticalAlign": "middle"},
                                            ),
                                        ],
                                        id="start-run-btn",
                                        n_clicks=0,
                                        style={
                                            "width": "100%",
                                            "marginTop": "16px",
                                            "background": "linear-gradient(135deg, #da9a36 0%, #c88a2e 100%)",
                                            "color": "white",
                                            "padding": "16px",
                                            "border": "none",
                                            "borderRadius": "12px",
                                            "fontSize": "16px",
                                            "fontWeight": "600",
                                            "cursor": "pointer",
                                            "boxShadow": "0 4px 6px rgba(218, 154, 54, 0.3)",
                                            "transition": "all 0.2s",
                                        },
                                    ),
                                    html.Div(
                                        id="start-run-error",
                                        style={
                                            "color": "#c62828",
                                            "marginTop": "8px",
                                            "fontSize": "13px",
                                        },
                                    ),
                                ],
                                style={"flex": 1},
                            ),
                            # Right column - Map Preview
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.I(
                                                "map",
                                                className="material-icons",
                                                style={
                                                    "fontSize": "20px",
                                                    "marginRight": "8px",
                                                    "color": "#10357e",
                                                },
                                            ),
                                            html.Span(
                                                "Kaart Preview",
                                                style={
                                                    "fontSize": "16px",
                                                    "fontWeight": "600",
                                                    "color": "#10357e",
                                                },
                                            ),
                                        ],
                                        style={
                                            "display": "flex",
                                            "alignItems": "center",
                                            "marginBottom": "16px",
                                        },
                                    ),
                                    html.Div(
                                        id="map-container",
                                        children=html.Iframe(
                                            srcDoc=create_gemeente_selection_map_html(
                                                []
                                            ),
                                            style={
                                                "width": "100%",
                                                "height": "520px",
                                                "border": "none",
                                                "borderRadius": "8px",
                                            },
                                        ),
                                        style={
                                            "background": "white",
                                            "borderRadius": "12px",
                                            "border": "1px solid #e0e0e0",
                                            "overflow": "hidden",
                                            "boxShadow": "0 2px 4px rgba(0,0,0,0.05)",
                                        },
                                    ),
                                ],
                                style={"flex": 2, "marginLeft": "24px"},
                            ),
                        ],
                        style={"display": "flex", "gap": "24px"},
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
