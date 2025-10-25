"""Nieuwe Run Form Callbacks"""

from dash import Input, Output, html
from dash.exceptions import PreventUpdate
from dashboard.dash_helpers import create_gemeente_selection_map_html
from src.core.scraper_core import generate_scan_combinations


def register_nieuwe_run_callbacks(app):
    """Register callbacks for the nieuwe run form"""

    @app.callback(
        [
            Output("interval-config", "style"),
            Output("weekday-config", "style"),
            Output("monthly-config", "style"),
        ],
        [Input("schedule-mode", "value")],
        prevent_initial_call=False,
    )
    def toggle_schedule_ui(mode):
        if mode == "interval":
            return {"display": "block"}, {"display": "none"}, {"display": "none"}
        if mode == "weekdays":
            return (
                {"display": "none"},
                {"display": "block", "marginTop": "8px"},
                {"display": "none"},
            )
        if mode == "monthly":
            return (
                {"display": "none"},
                {"display": "block", "marginTop": "8px"},
                {
                    "display": "block",
                    "marginTop": "8px",
                    "fontSize": "12px",
                    "color": "#666",
                },
            )
        raise PreventUpdate

    @app.callback(
        Output("preview-container", "children"),
        [
            Input("period-start", "date"),
            Input("period-end", "date"),
            Input("schedule-mode", "value"),
            Input("measurement-interval", "value"),
            Input("days-of-week", "value"),
        ],
        prevent_initial_call=False,
    )
    def update_preview(start_date, end_date, mode, interval, days_of_week):
        try:
            if not start_date or not end_date:
                return ""
            if start_date >= end_date:
                return html.Div(
                    "⚠️ Einddatum moet na startdatum zijn", style={"color": "#c62828"}
                )

            monthly = mode == "monthly"
            if mode == "interval":
                days = None
                weeks_interval = 1
            else:
                days = days_of_week or []
                weeks_interval = 1

            scan_combinations, _ = generate_scan_combinations(
                period_start=start_date,
                period_end=end_date,
                nights_list=[1],
                guests_list=[2],
                measurement_interval=int(interval or 7),
                days_of_week=days,
                weeks_interval=weeks_interval,
                monthly_interval=monthly,
            )

            checkins = sorted({c[0] for c in scan_combinations})
            days_count = (
                datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)
            ).days
            return html.Div(
                [
                    html.Div(
                        [
                            html.I(
                                "calendar_today",
                                className="material-icons",
                                style={
                                    "fontSize": "16px",
                                    "marginRight": "6px",
                                    "verticalAlign": "middle",
                                    "color": "#2e7d32",
                                },
                            ),
                            html.Span(
                                f"{len(checkins)} metingen",
                                style={
                                    "fontWeight": "600",
                                    "color": "#2e7d32",
                                    "fontSize": "14px",
                                },
                            ),
                            html.Span(
                                f" over {days_count} dagen",
                                style={
                                    "color": "#616161",
                                    "fontSize": "13px",
                                    "marginLeft": "4px",
                                },
                            ),
                        ],
                        style={
                            "padding": "10px 14px",
                            "background": "#e8f5e9",
                            "borderRadius": "8px",
                            "border": "1px solid #c8e6c9",
                            "display": "inline-flex",
                            "alignItems": "center",
                        },
                    ),
                ]
            )
        except Exception:
            return ""

    @app.callback(
        Output("map-container", "children"),
        [Input("gemeenten-dropdown", "value")],
        prevent_initial_call=False,
    )
    def update_map(selected):
        selected = selected or []
        map_html = create_gemeente_selection_map_html(selected)
        return html.Iframe(
            srcDoc=map_html,
            style={
                "width": "100%",
                "height": "520px",
                "border": "none",
                "borderRadius": "8px",
            },
        )
