#!/usr/bin/env python3
"""
Airbnb Scraper - Python Script Versie
Scraped Airbnb verhuurobjecten per gemeente met meerdere API calls voor maximale dekking

BELANGRIJKSTE INZICHT: De Airbnb API retourneert willekeurige subsets (~250-280 verhuurobjecten) per call.
Door meerdere calls te maken met dezelfde parameters en te dedupliceren,
krijgen we ~98% dekking met 3 calls.

NOTE: Dit is een standalone script voor quick runs. Voor uitgebreide functionaliteit,
gebruik het Streamlit dashboard (run_dashboard.py) of het Jupyter notebook (bnb_scraper.ipynb).
Dit script hergebruikt functies uit de src/ modules om code duplicatie te vermijden.
"""

import pyairbnb
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from datetime import date, timedelta, datetime
from src.config.room_type_config import get_mapped_property_type
from src.core.scraper_core import generate_scan_combinations
from src.core.room_classifier import extract_room_type
from src.utils import extract_beds_info
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# ═══════════════════════════════════════════════════════════════════════════════
# 📋 CONFIGURATIE
# ═══════════════════════════════════════════════════════════════════════════════

# ── Doelgemeenten ──────────────────────────────────────────────────────────────
gemeenten = ["Schagen"]

# ── PERIODE CONFIGURATIE ───────────────────────────────────────────────────────
PERIOD_START = "2025-12-01"
PERIOD_END = "2025-12-05"
MEASUREMENT_INTERVAL = 1  # dagen (wekelijkse snapshots)

# ── VARIATIES ──────────────────────────────────────────────────────────────────
# Minimale set om alle verhuurobjecten te vangen (1n, 3n, 7n dekken meeste use cases)
nights_variations = [1, 3, 7]
guests_variations = [1, 3, 6]  # Solo, klein gezin, grotere groep

# ── API CALL STRATEGIE ────────────────────────────────────────────────────────
# ONTDEKKING: De Airbnb API retourneert willekeurige subsets van verhuurobjecten bij elke call (~250-280)
# Door MEERDERE calls te maken met dezelfde parameters, vangen we verschillende willekeurige subsets
# Tests toonden aan: 1 call = ~250 verhuurobjecten, 3 calls = ~290 verhuurobjecten (~98% dekking)
# Strategie: Maak 3 API calls per zoekopdracht en dedupliceer voor maximale dekking
NUM_REPEAT_CALLS = 3  # Optimale balans tussen dekking en API-gebruik

# ── Extra Configuratie ────────────────────────────────────────────────────────
gpkg_path = "assets/BestuurlijkeGebieden_2025.gpkg"  # Gemeentegrenzen
currency = "EUR"
language = "nl"

# API parameters (standaard - meestal niet nodig om aan te passen)
price_min = 0  # 0 = geen minimum
price_max = 0  # 0 = geen maximum
amenities = []  # Lege lijst = geen filter
zoom_value = 10  # Lagere zoom presteert beter (testen toonden 10 als optimaal)
proxy_url = ""  # Leeg = geen proxy

# ── Meetmoment ─────────────────────────────────────────────────────────────────
MEASUREMENT_DATE = datetime.now().isoformat()

print("=" * 80)
print("🚀 AIRBNB SCRAPER - PYTHON SCRIPT")
print("=" * 80)
print(f"Meetmoment: {MEASUREMENT_DATE}")
print(f"Periode: {PERIOD_START} → {PERIOD_END}")
print(f"Meet-interval: Elke {MEASUREMENT_INTERVAL} dagen")
print(f"Gemeenten: {', '.join(gemeenten)}")
print("=" * 80)

# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 HULPFUNCTIES
# ═══════════════════════════════════════════════════════════════════════════════
# Note: extract_beds_info, extract_room_type, en generate_scan_combinations
# worden nu geïmporteerd uit src/ modules om code duplicatie te vermijden


def make_api_call(call_num, check_in, check_out, maxy, maxx, miny, minx):
    """Hulpfunctie om één API call te maken (voor parallellisatie)"""
    try:
        raw = pyairbnb.search_all(
            check_in,
            check_out,
            ne_lat=maxy,
            ne_long=maxx,
            sw_lat=miny,
            sw_long=minx,
            zoom_value=zoom_value,
            price_min=price_min,
            price_max=price_max,
            # Geen place_type parameter - weggelaten voor beste resultaten
            amenities=amenities,
            currency=currency,
            language=language,
            proxy_url=proxy_url,
        )
        return (call_num, raw, None)
    except Exception as e:
        return (call_num, None, e)


def scrape_one(gm, check_in, check_out, nights, guests, scan_id):
    """Scrape één gemeente met parallelle API calls voor maximale dekking"""
    print(f" {gm:12s} {check_in}→{check_out} {nights}n/{guests}g", end="")

    # Laad gemeentegrenzen
    gdf_all = (
        gpd.read_file(gpkg_path, layer="gemeentegebied")
        .set_crs("EPSG:28992")
        .to_crs("EPSG:4326")
    )
    sel = gdf_all[gdf_all["naam"] == gm]
    if sel.empty:
        print(" ⚠️  Geen grens")
        return pd.DataFrame()

    # Haal bounding box op
    minx, miny, maxx, maxy = sel.total_bounds

    # ✨ PARALLELLE API CALLS - elk retourneert verschillende willekeurige subset
    all_raw_results = []
    all_room_ids = set()

    # Voer API calls parallel uit
    with ThreadPoolExecutor(max_workers=NUM_REPEAT_CALLS) as executor:
        # Dien alle calls tegelijk in
        futures = [
            executor.submit(
                make_api_call, i, check_in, check_out, maxy, maxx, miny, minx
            )
            for i in range(1, NUM_REPEAT_CALLS + 1)
        ]

        # Verzamel resultaten zodra ze klaar zijn
        for future in as_completed(futures):
            call_num, raw, error = future.result()

            if error:
                continue

            if raw:
                # Houd room IDs bij en verzamel resultaten
                new_ids = {rec.get("room_id") for rec in raw if rec.get("room_id")}
                all_room_ids.update(new_ids)
                all_raw_results.extend(raw)

    if not all_raw_results:
        print(" → 0 verhuurobjecten")
        return pd.DataFrame()

    # Toon resultaten (eenvoudige output met opmaak)
    print(f" → {len(all_room_ids):3d} verhuurobjecten")

    # Verwerk alle resultaten
    if not all_raw_results:
        return pd.DataFrame()

    rows = []
    for rec in all_raw_results:
        coords = rec.get("coordinates", {})
        lat = coords.get("latitude")
        lon = coords.get("longitud") or coords.get("longitude")

        if not lat or not lon:
            continue

        # Haal prijs op
        price_data = rec.get("price", {})
        price_unit = price_data.get("unit", {})
        price = price_unit.get("amount", 0) if price_unit else 0

        # Haal beoordeling op
        rating_data = rec.get("rating", {})
        rating = rating_data.get("value", None) if rating_data else None
        reviews_count = rating_data.get("reviewCount", None) if rating_data else None

        # Converteer reviews_count naar int als het een string is
        if reviews_count:
            try:
                reviews_count = int(reviews_count)
            except (ValueError, TypeError):
                reviews_count = None

        # Extraheer bed/slaapkamer info
        bedrooms, beds = extract_beds_info(rec)

        # Genereer verhuurobject URL
        room_id = rec.get("room_id")
        listing_url = f"https://www.airbnb.nl/rooms/{room_id}" if room_id else None

        # Detecteer type en koppel aan Airbnb standaard
        detected_type = extract_room_type(rec)
        airbnb_property_type = get_mapped_property_type(detected_type)
        airbnb_room_type = detected_type  # Behoud originele detected type

        rows.append(
            {
                "gemeente": gm,
                "room_id": rec.get("room_id"),
                "listing_url": listing_url,
                "listing_title": rec.get("title", "") or rec.get("name", ""),
                "room_type_detected": detected_type,  # Specifiek type
                "room_type_airbnb": airbnb_room_type,  # Airbnb standaard
                "property_type_airbnb": airbnb_property_type,  # Accommodatie subtype
                "bedrooms": bedrooms,
                "beds": beds,
                "price": price,
                "rating": rating,
                "reviews_count": reviews_count,
                "latitude": lat,
                "longitude": lon,
                "scan_checkin": check_in,
                "scan_checkout": check_out,
                "scan_nights": nights,
                "scan_guests": guests,
                "scan_id": scan_id,
                "measurement_date": MEASUREMENT_DATE,
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # DEDUPLICEER op room_id
    df_dedup = df.drop_duplicates("room_id")

    # Ruimtelijk filter
    gdf_pts = gpd.GeoDataFrame(
        df_dedup,
        geometry=[Point(xy) for xy in zip(df_dedup.longitude, df_dedup.latitude)],
        crs="EPSG:4326",
    )
    inside = gdf_pts[gdf_pts.within(sel.geometry.union_all())].copy()

    return inside


# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 HOOFDUITVOERING
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Genereer scan combinaties
    scan_combinations, valid_nights = generate_scan_combinations(
        PERIOD_START,
        PERIOD_END,
        nights_variations,
        guests_variations,
        MEASUREMENT_INTERVAL,
    )

    print(f"\n📊 Totaal Scan Combinaties: {len(scan_combinations)}")
    print(f"🛏️  Nachten Variaties: {valid_nights}")
    print(f"👥 Gasten Variaties: {guests_variations}")

    # Tijdsduur schatting
    total_scans = len(scan_combinations) * len(gemeenten)
    total_api_calls = total_scans * NUM_REPEAT_CALLS
    est_time_per_call = 2  # seconden (conservatieve schatting)
    est_parallel_time = (
        total_scans * est_time_per_call
    ) / 60  # minuten (calls lopen parallel)

    print("\n⏱️  Geschatte tijd:")
    print(
        f"   • Totaal: {total_scans} zoekopdrachten × {NUM_REPEAT_CALLS} calls = {total_api_calls} API calls"
    )
    print(f"   • Geschatte duur: ~{est_parallel_time:.1f} minuten")

    # Scrape alle combinaties
    print("\n" + "=" * 80)
    print("🚀 START SCRAPEN")
    print("=" * 80)

    all_runs = []
    current_scan = 0
    start_time = time.time()

    for ci, co, nights, guests, scan_id in scan_combinations:
        for gm in gemeenten:
            current_scan += 1

            # Toon voortgang met geschatte resterende tijd
            if current_scan > 1:
                elapsed = time.time() - start_time
                avg_time_per_scan = elapsed / (current_scan - 1)
                remaining_scans = total_scans - current_scan
                eta_seconds = remaining_scans * avg_time_per_scan
                eta_minutes = eta_seconds / 60
                progress_pct = (current_scan / total_scans) * 100
                print(
                    f"\n[{current_scan:3d}/{total_scans} {progress_pct:5.1f}% | ETA {eta_minutes:4.1f}m]",
                    end="",
                )
            else:
                print(f"\n[{current_scan:3d}/{total_scans}]", end="")

            df_run = scrape_one(gm, ci, co, nights, guests, scan_id)
            all_runs.append(df_run)

    # Combineer alle runs
    total_duration = time.time() - start_time
    print("\n\n" + "=" * 80)
    print("📊 RESULTATEN VERWERKEN")
    print("=" * 80)

    df_all = pd.concat(all_runs, ignore_index=True)
    print(f"\n✓ Totaal records:         {len(df_all):,}")
    print(f"✓ Unieke verhuurobjecten: {df_all['room_id'].nunique():,}")
    print(
        f"✓ Scrape tijd:            {total_duration / 60:.1f} minuten ({total_duration:.0f} seconden)"
    )
    print(f"✓ Gemiddeld per zoekopdracht: {total_duration / total_scans:.1f} seconden")

    # Kamertype verdeling
    print("\n🏠 Airbnb Standaard Categorieën:")
    room_type_counts = df_all["room_type_airbnb"].value_counts()
    for rt, count in room_type_counts.items():
        print(f"   • {rt}: {count}")

    print("\n🏘️  Accommodatietypes:")
    property_type_counts = df_all["property_type_airbnb"].value_counts()
    for pt, count in property_type_counts.items():
        print(f"   • {pt}: {count}")

    print("\n🔍 Gedetecteerde Types (top 10):")
    detected_counts = df_all["room_type_detected"].value_counts()
    for dt, count in detected_counts.head(10).items():
        print(f"   • {dt}: {count}")

    # ═══════════════════════════════════════════════════════════════════════════════
    # AVAILABILITY ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════════

    print("\n📅 Beschikbaarheidsanalyse:")

    # Tel unieke check-in datums per verhuurobject
    availability_data = (
        df_all.groupby("room_id")
        .agg(
            {
                "scan_checkin": "nunique",  # Aantal unieke datums beschikbaar
                "listing_title": "first",
                "property_type_airbnb": "first",
                "gemeente": "first",
            }
        )
        .reset_index()
    )

    # Bereken totaal mogelijke check-in datums in de periode
    total_scans_per_listing = len(scan_combinations)

    # Voeg beschikbaarheidsmetrics toe
    availability_data["total_scans"] = total_scans_per_listing
    availability_data["availability_rate"] = (
        availability_data["scan_checkin"] / total_scans_per_listing * 100
    ).round(1)

    # Hernoem voor duidelijkheid
    availability_data = availability_data.rename(
        columns={"scan_checkin": "times_available"}
    )

    # Sorteer op beschikbaarheid
    availability_data = availability_data.sort_values(
        "times_available", ascending=False
    )

    # Toon samenvatting
    avg_availability = availability_data["availability_rate"].mean()
    print(f"   • Gemiddelde beschikbaarheid: {avg_availability:.1f}%")
    print(
        f"   • Altijd beschikbaar ({total_scans_per_listing}× gevonden): {(availability_data['times_available'] == total_scans_per_listing).sum()} verhuurobjecten"
    )
    print(
        f"   • Soms beschikbaar (1-{total_scans_per_listing - 1}× gevonden): {((availability_data['times_available'] > 0) & (availability_data['times_available'] < total_scans_per_listing)).sum()} verhuurobjecten"
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
            f"   • {prop_type:20s}: {row['gem_beschikbaarheid_%']:5.1f}% ({int(row['aantal_listings'])} verhuurobjecten)"
        )

    # Exporteer naar Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    gm_string = "-".join(gemeenten)
    filename = f"airbnb_scrape_{gm_string}_{timestamp}.xlsx"

    # Bereid data voor export - alleen essentiële kolommen
    export_columns = [
        "gemeente",
        "room_id",
        "listing_url",
        "listing_title",
        "property_type_airbnb",
        "bedrooms",
        "beds",
        "price",
        "rating",
        "reviews_count",
        "latitude",
        "longitude",
        "scan_checkin",
        "scan_checkout",
        "scan_nights",
        "scan_guests",
        "measurement_date",
    ]
    df_export = df_all[export_columns].copy()

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        df_export.to_excel(writer, sheet_name="Alle Data", index=False)

        # Availability Analysis sheet
        availability_export = availability_data[
            [
                "room_id",
                "listing_title",
                "gemeente",
                "property_type_airbnb",
                "times_available",
                "total_scans",
                "availability_rate",
            ]
        ].copy()
        availability_export.to_excel(writer, sheet_name="Beschikbaarheid", index=False)

        # Beschikbaarheid over tijd - inclusief alle dagen van het verblijf
        # Als iemand 3 nachten boekt (1-4 dec), tel als beschikbaar op 1, 2, 3 dec
        availability_rows = []
        for _, row in df_all.iterrows():
            check_in = date.fromisoformat(row["scan_checkin"])
            check_out = date.fromisoformat(row["scan_checkout"])
            nights = row["scan_nights"]

            # Genereer alle dagen van het verblijf
            for day_offset in range(nights):
                current_day = check_in + timedelta(days=day_offset)
                availability_rows.append(
                    {
                        "datum": current_day.isoformat(),
                        "room_id": row["room_id"],
                        "property_type_airbnb": row["property_type_airbnb"],
                    }
                )

        # Maak DataFrame van alle dagen
        avail_days_df = pd.DataFrame(availability_rows)

        # Tel unieke verhuurobjecten per dag en type
        avail_timeline = (
            avail_days_df.groupby(["datum", "property_type_airbnb"])
            .agg({"room_id": "nunique"})
            .reset_index()
        )
        avail_timeline.columns = ["datum", "accommodatietype", "aantal_beschikbaar"]

        # Get all unique property types to ensure consistent columns
        all_property_types = sorted(df_all["property_type_airbnb"].unique())

        # Pivot en vul ontbrekende waarden met 0
        avail_timeline_pivot = avail_timeline.pivot(
            index="datum", columns="accommodatietype", values="aantal_beschikbaar"
        )

        # Ensure all property types are present as columns
        for prop_type in all_property_types:
            if prop_type not in avail_timeline_pivot.columns:
                avail_timeline_pivot[prop_type] = 0

        # Sort columns and fill NaN
        avail_timeline_pivot = (
            avail_timeline_pivot[all_property_types].fillna(0).astype(int)
        )

        avail_timeline_pivot.to_excel(writer, sheet_name="Beschikbaarheid over tijd")

    print(f"\n✅ Opgeslagen: {filename}")
    print("=" * 80)
