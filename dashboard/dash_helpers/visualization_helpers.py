"""Visualization helpers for Dash dashboard"""

import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta


def create_timeline_figure(df: pd.DataFrame, config: dict):
    """Create interactive Plotly timeline graph showing availability over time"""
    # Get period from config or data
    period_start = config.get("period_start")
    period_end = config.get("period_end")

    if not period_start or not period_end:
        period_start = df["scan_checkin"].min()
        period_end = df["scan_checkout"].max()

    # Calculate timeline data
    start_date = date.fromisoformat(str(period_start)[:10])
    end_date = date.fromisoformat(str(period_end)[:10])
    all_dates = [
        start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)
    ]

    # Color mapping
    COLORS = {
        "Entire home": "#3498db",
        "Private room": "#e67e22",
        "Shared room": "#e91e63",
        "Guesthouse": "#27ae60",
        "Hotel": "#f39c12",
        "Unique stay": "#9b59b6",
        "Unknown": "#95a5a6",
    }

    # Prepare data for calculation
    df_calc = df[
        ["room_id", "property_type_airbnb", "scan_checkin", "scan_checkout"]
    ].copy()
    df_calc["check_in"] = pd.to_datetime(df_calc["scan_checkin"]).dt.date
    df_calc["check_out"] = pd.to_datetime(df_calc["scan_checkout"]).dt.date

    # Calculate availability per day per type
    availability_timeline = []

    for prop_type in df_calc["property_type_airbnb"].unique():
        type_data = df_calc[df_calc["property_type_airbnb"] == prop_type]

        for current_date in all_dates:
            # Which listings are available on this date?
            mask = (type_data["check_in"] <= current_date) & (
                current_date < type_data["check_out"]
            )
            available_count = type_data[mask]["room_id"].nunique()

            availability_timeline.append(
                {
                    "datum": current_date,
                    "property_type": prop_type,
                    "available_count": available_count,
                }
            )

    df_timeline = pd.DataFrame(availability_timeline)

    # Create Plotly figure
    fig = go.Figure()

    # Add a line for each property type
    for prop_type in sorted(df_timeline["property_type"].unique()):
        data = df_timeline[df_timeline["property_type"] == prop_type].sort_values(
            "datum"
        )

        fig.add_trace(
            go.Scatter(
                x=data["datum"],
                y=data["available_count"],
                name=prop_type,
                mode="lines+markers",
                line=dict(color=COLORS.get(prop_type, "#95a5a6"), width=3),
                marker=dict(
                    size=6,
                    color=COLORS.get(prop_type, "#95a5a6"),
                ),
                hovertemplate="<b>%{fullData.name}</b><br>"
                + "Datum: %{x|%d %b %Y}<br>"
                + "Beschikbaar: %{y} listings<br>"
                + "<extra></extra>",
            )
        )

    # Update layout
    fig.update_layout(
        xaxis_title="Datum",
        yaxis_title="Aantal Beschikbare Listings",
        hovermode="x unified",
        height=500,
        legend=dict(
            title="Accommodatietype",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        plot_bgcolor="white",
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.1)",
            showline=True,
            linecolor="rgba(0,0,0,0.2)",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.1)",
            showline=True,
            linecolor="rgba(0,0,0,0.2)",
        ),
        margin=dict(l=50, r=20, t=40, b=50),
    )

    return fig

