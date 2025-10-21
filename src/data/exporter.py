#!/usr/bin/env python3
"""
Export functionality for Airbnb scrape results
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd

from src.data.data_processor import (
    calculate_availability,
    calculate_availability_timeline,
    prepare_export_data,
)

logger = logging.getLogger(__name__)


def auto_export_results(
    df_all: pd.DataFrame,
    period_start: str,
    period_end: str,
    gemeenten: List[str],
    data_dir: str = "data",
    config: Dict = None,
) -> Tuple[str, pd.DataFrame, str]:
    """
    Automatisch exporteren van scrape resultaten naar Excel in georganiseerde folder

    Args:
        df_all: DataFrame met alle scrape resultaten
        period_start: Start datum van periode
        period_end: Eind datum van periode
        gemeenten: List van gemeente namen
        data_dir: Output directory
        config: Optional dictionary met alle config parameters

    Returns:
        Tuple van (filename, availability_data, output_dir)
    """
    logger.info("Starting automatic export...")

    # Maak data directory als het niet bestaat
    os.makedirs(data_dir, exist_ok=True)

    # Bereken beschikbaarheid (day-based)
    availability_data = calculate_availability(df_all, period_start, period_end)

    # Bereken timeline
    property_types = sorted(df_all["property_type_airbnb"].unique())
    avail_timeline_pivot = calculate_availability_timeline(df_all, property_types)

    # Prepareer export data
    df_export = prepare_export_data(df_all)

    # Maak output directory voor deze run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    gm_string = "_".join(gemeenten)
    output_dir = os.path.join(data_dir, f"run_{gm_string}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    filename = os.path.join(output_dir, f"airbnb_scrape_{gm_string}_{timestamp}.xlsx")

    # Sla config op als JSON
    if config:
        config_file = os.path.join(output_dir, "config.json")
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Config saved: {config_file}")

    # Export naar Excel
    logger.info(f"Exporting to: {filename}")

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        df_export.to_excel(writer, sheet_name="Alle Data", index=False)

        availability_export = availability_data[
            [
                "room_id",
                "listing_title",
                "gemeente",
                "property_type_airbnb",
                "days_available",
                "total_days",
                "availability_rate",
            ]
        ].copy()
        availability_export.to_excel(writer, sheet_name="Beschikbaarheid", index=False)

        avail_timeline_pivot.to_excel(writer, sheet_name="Beschikbaarheid over tijd")

    logger.info(f"Export complete: {filename}")

    # Print export summary
    print("\n" + "=" * 80)
    print("📦 EXPORT COMPLEET")
    print("=" * 80)
    print(f"📁 Output folder: {output_dir}")
    print(f"📊 Excel bestand: {os.path.basename(filename)}")
    print(f"   • {len(df_all):,} totale records")
    print(f"   • {df_all['room_id'].nunique():,} unieke listings")
    if config:
        print("⚙️  Config opgeslagen: config.json")
    print("=" * 80)

    # Print beschikbaarheid statistieken
    print("\n📅 Beschikbaarheidsanalyse:")
    avg_availability = availability_data["availability_rate"].mean()
    total_days = availability_data.iloc[0]["total_days"]

    print(f"   • Gemiddelde beschikbaarheid: {avg_availability:.1f}%")
    print(f"   • Periode: {total_days} dagen")
    print(
        f"   • Altijd beschikbaar (alle {total_days} dagen): "
        + f"{(availability_data['days_available'] == total_days).sum()} verhuurobjecten"
    )

    # Beschikbaarheid per accommodatietype
    print("\n📊 Beschikbaarheid per accommodatietype:")
    avail_by_type = (
        availability_data.groupby("property_type_airbnb")
        .agg({"availability_rate": "mean", "room_id": "count"})
        .round(1)
    )
    avail_by_type.columns = ["gem_beschikbaarheid_%", "aantal_listings"]
    avail_by_type = avail_by_type.sort_values("gem_beschikbaarheid_%", ascending=False)

    for prop_type, row in avail_by_type.iterrows():
        print(
            f"   • {prop_type:20s}: {row['gem_beschikbaarheid_%']:5.1f}% "
            + f"({int(row['aantal_listings'])} verhuurobjecten)"
        )

    return filename, availability_data, output_dir


def export_to_excel(
    df_export: pd.DataFrame,
    output_path: str,
    df_availability: pd.DataFrame,
    df_all: pd.DataFrame,
) -> None:
    """
    Export scrape data to Excel file with multiple sheets

    Args:
        df_export: Prepared export data
        output_path: Path to output Excel file
        df_availability: Availability summary data
        df_all: All raw scrape data
    """
    logger.info(f"Exporting to Excel: {output_path}")

    # Get property types for timeline
    property_types = sorted(df_all["property_type_airbnb"].unique())

    # Calculate timeline
    avail_timeline_pivot = calculate_availability_timeline(df_all, property_types)

    # Export to Excel with multiple sheets
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Main data
        df_export.to_excel(writer, sheet_name="Alle Data", index=False)

        # Availability summary
        availability_export = df_availability[
            [
                "room_id",
                "listing_title",
                "gemeente",
                "property_type_airbnb",
                "days_available",
                "total_days",
                "availability_rate",
            ]
        ].copy()
        availability_export.to_excel(writer, sheet_name="Beschikbaarheid", index=False)

        # Timeline
        avail_timeline_pivot.to_excel(writer, sheet_name="Beschikbaarheid over tijd")

    logger.info(f"Export complete: {output_path}")
    print(f"✓ Excel file saved: {output_path}")
