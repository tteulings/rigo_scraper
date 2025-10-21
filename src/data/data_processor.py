#!/usr/bin/env python3
"""
Data processing and analysis functionality
"""

import logging
from datetime import date, timedelta
from typing import List

import pandas as pd

logger = logging.getLogger(__name__)


def calculate_availability(
    df_all: pd.DataFrame, period_start: str, period_end: str
) -> pd.DataFrame:
    start_date = date.fromisoformat(period_start)
    end_date = date.fromisoformat(period_end)
    total_days = (end_date - start_date).days + 1

    df_calc = df_all.copy()
    df_calc["check_in_date"] = pd.to_datetime(df_calc["scan_checkin"]).dt.date

    availability_rows = []
    for room_id in df_calc["room_id"].unique():
        room_data = df_calc[df_calc["room_id"] == room_id]

        available_days = set()
        for _, row_data in room_data.iterrows():
            check_in = row_data["check_in_date"]
            nights = int(row_data["scan_nights"])

            for day_offset in range(nights):
                current_day = check_in + timedelta(days=day_offset)
                if start_date <= current_day <= end_date:
                    available_days.add(current_day)

        days_available = len(available_days)
        availability_rate = (days_available / total_days * 100) if total_days > 0 else 0

        first_row = room_data.iloc[0]
        availability_rows.append(
            {
                "room_id": room_id,
                "listing_title": first_row["listing_title"],
                "property_type_airbnb": first_row["property_type_airbnb"],
                "gemeente": first_row["gemeente"],
                "days_available": days_available,
                "total_days": total_days,
                "availability_rate": round(availability_rate, 1),
            }
        )

    availability_data = pd.DataFrame(availability_rows).sort_values(
        "days_available", ascending=False
    )
    return availability_data


def calculate_availability_timeline(
    df_all: pd.DataFrame, property_types: List[str]
) -> pd.DataFrame:
    df_all["check_in_date"] = pd.to_datetime(df_all["scan_checkin"])

    availability_rows = []
    for nights in df_all["scan_nights"].unique():
        df_subset = df_all[df_all["scan_nights"] == nights].copy()
        if len(df_subset) == 0:
            continue

        for day_offset in range(int(nights)):
            df_day = df_subset[
                ["room_id", "property_type_airbnb", "check_in_date"]
            ].copy()
            df_day["datum"] = df_day["check_in_date"] + pd.Timedelta(days=day_offset)
            availability_rows.append(
                df_day[["datum", "room_id", "property_type_airbnb"]]
            )

    if not availability_rows:
        return pd.DataFrame(index=[], columns=property_types).fillna(0).astype(int)

    avail_days_df = pd.concat(availability_rows, ignore_index=True)
    avail_days_df["datum"] = avail_days_df["datum"].dt.date.astype(str)

    avail_timeline = (
        avail_days_df.groupby(["datum", "property_type_airbnb"])
        .agg({"room_id": "nunique"})
        .reset_index()
    )
    avail_timeline.columns = ["datum", "accommodatietype", "aantal_beschikbaar"]

    avail_timeline_pivot = avail_timeline.pivot(
        index="datum", columns="accommodatietype", values="aantal_beschikbaar"
    )

    for prop_type in property_types:
        if prop_type not in avail_timeline_pivot.columns:
            avail_timeline_pivot[prop_type] = 0

    return avail_timeline_pivot.fillna(0).astype(int)


def prepare_export_data(df_all: pd.DataFrame) -> pd.DataFrame:
    df_export = df_all.copy()
    df_export = df_export.sort_values(["scan_checkin", "listing_title"])
    return df_export


def print_summary_stats(df_all: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("📊 SAMENVATTING")
    print("=" * 80)
    print(f"Totaal aantal records: {len(df_all):,}")
    print(f"Unieke listings: {df_all['room_id'].nunique():,}")
    print("\nVerdeling per accommodatietype:")

    type_counts = df_all.groupby("property_type_airbnb")["room_id"].nunique()
    for prop_type, count in type_counts.items():
        print(f"  • {prop_type}: {count}")

    print(f"\nGemiddelde prijs: €{df_all['price'].mean():.2f}")
    print(f"Prijs range: €{df_all['price'].min():.0f} - €{df_all['price'].max():.0f}")
    print("=" * 80)
