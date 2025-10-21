#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Graph creation functionality
"""

import logging
import os
from datetime import date, timedelta
from typing import Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)

# Consistent kleurenschema met map
GRAPH_COLORS = {
    "Entire home": "#3498db",
    "Private room": "#e67e22",
    "Shared room": "#e91e63",
    "Guesthouse": "#27ae60",
    "Hotel": "#f39c12",
    "Unique stay": "#9b59b6",
}


def create_availability_timeline_graph(
    df_all: pd.DataFrame,
    period_start: str,
    period_end: str,
    output_dir: Optional[str] = None,
) -> None:
    # Bereken beschikbaarheid per dag per type
    df_timeline = _calculate_timeline_data(df_all, period_start, period_end)

    # Maak grafiek
    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot lijn per property type
    for prop_type in sorted(df_timeline["property_type"].unique()):
        data = df_timeline[df_timeline["property_type"] == prop_type].sort_values(
            "datum"
        )
        ax.plot(
            data["datum"],
            data["available_count"],
            marker="o",
            linewidth=2.5,
            markersize=5,
            label=prop_type,
            color=GRAPH_COLORS.get(prop_type, "#95a5a6"),
        )

    # Styling
    ax.set_xlabel("Datum", fontsize=13, fontweight="bold")
    ax.set_ylabel("Aantal Beschikbare Listings", fontsize=13, fontweight="bold")
    ax.set_title(
        "Beschikbaarheid Over Tijd per Accommodatietype",
        fontsize=15,
        fontweight="bold",
        pad=20,
    )
    ax.legend(title="Accommodatietype", loc="best", fontsize=11, title_fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Datum formatting
    start_date = date.fromisoformat(period_start)
    end_date = date.fromisoformat(period_end)
    num_days = (end_date - start_date).days + 1

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, num_days // 10)))
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()

    if output_dir:
        timeline_path = os.path.join(output_dir, "timeline_availability.png")
        plt.savefig(timeline_path, dpi=300, bbox_inches="tight")
        print(f"✓ Timeline grafiek opgeslagen: {timeline_path}")

    plt.show()
    _print_timeline_stats(df_timeline)


def _calculate_timeline_data(
    df_all: pd.DataFrame, period_start: str, period_end: str
) -> pd.DataFrame:
    availability_timeline = []

    start_date = date.fromisoformat(period_start)
    end_date = date.fromisoformat(period_end)
    all_dates = [
        start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)
    ]

    df_calc = df_all[
        ["room_id", "property_type_airbnb", "scan_checkin", "scan_checkout"]
    ].copy()
    df_calc["check_in"] = pd.to_datetime(df_calc["scan_checkin"]).dt.date
    df_calc["check_out"] = pd.to_datetime(df_calc["scan_checkout"]).dt.date

    for prop_type in df_calc["property_type_airbnb"].unique():
        type_data = df_calc[df_calc["property_type_airbnb"] == prop_type]

        for current_date in all_dates:
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

    return pd.DataFrame(availability_timeline)


def _print_timeline_stats(df_timeline: pd.DataFrame) -> None:
    print("\n📊 Beschikbaarheid Statistieken per Type:")
    for prop_type in sorted(df_timeline["property_type"].unique()):
        data = df_timeline[df_timeline["property_type"] == prop_type]
        print(f"\n{prop_type}:")
        print(f"  • Gemiddeld: {data['available_count'].mean():.1f} listings/dag")
        print(f"  • Min: {data['available_count'].min()} listings")
        print(f"  • Max: {data['available_count'].max()} listings")
