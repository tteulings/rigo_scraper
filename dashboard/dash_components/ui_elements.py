"""Reusable UI elements for Dash dashboard"""

from dash import html
from dashboard.constants import get_status_config, get_source_config


def status_badge(status: str) -> html.Span:
    """Create a colored status badge using centralized configuration"""
    config = get_status_config(status)

    return html.Span(
        config["label"],
        style={
            "background": config["color"],
            "color": "white",
            "padding": "2px 8px",
            "borderRadius": "12px",
            "fontSize": "12px",
            "fontWeight": "500",
        },
    )


def source_chip(source: str, show_label: bool = True) -> html.Div:
    """Create a data source chip/badge with logo"""
    config = get_source_config(source)

    # Map source to logo filename
    logo_map = {
        "airbnb": "airbnb-logo.jpg",
        "funda": "funda-logo.svg",
        "booking": "booking-logo.png",  # In case you add it later
    }

    logo_file = logo_map.get(source.lower(), None)

    return html.Div(
        [
            html.Img(
                src=f"/assets/{logo_file}" if logo_file else "",
                style={
                    "height": "16px",
                    "width": "auto",
                    "marginRight": "6px" if show_label else "0",
                    "verticalAlign": "middle",
                    "objectFit": "contain",
                },
            )
            if logo_file
            else html.I(
                config["icon"],
                className="material-icons",
                style={
                    "fontSize": "16px",
                    "marginRight": "4px" if show_label else "0",
                    "verticalAlign": "middle",
                },
            ),
            html.Span(
                config["name"],
                style={
                    "verticalAlign": "middle",
                    "fontSize": "12px",
                    "fontWeight": "500",
                },
            )
            if show_label
            else None,
        ],
        style={
            "display": "inline-flex",
            "alignItems": "center",
            "background": config["color_light"],
            "color": config["color"],
            "padding": "4px 10px",
            "borderRadius": "16px",
            "border": f"1px solid {config['color']}",
        },
    )
