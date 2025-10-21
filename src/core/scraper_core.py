#!/usr/bin/env python3
"""
Core Airbnb scraping functions
"""

import logging
import time
from datetime import date, timedelta
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from tqdm import tqdm

from src.config.room_type_config import get_mapped_property_type
from src.core.room_classifier import extract_room_type
from src.utils import (
    extract_beds_info,
    extract_guest_capacity,
    extract_price,
    extract_rating,
    extract_coordinates,
    generate_listing_url,
)
from src.core.api_client import make_parallel_api_calls

logger = logging.getLogger(__name__)


def generate_scan_combinations(
    period_start: str,
    period_end: str,
    nights_list: List[int],
    guests_list: List[int],
    measurement_interval: int,
    days_of_week: Optional[List[int]] = None,
    weeks_interval: int = 1,
    monthly_interval: bool = False,
) -> Tuple[List[Tuple[str, str, int, int, int]], List[int]]:
    """
    Genereer scan combinaties voor de opgegeven periode

    Args:
        period_start: Start datum (YYYY-MM-DD)
        period_end: Eind datum (YYYY-MM-DD)
        nights_list: Lijst van nachten variaties
        guests_list: Lijst van gasten variaties
        measurement_interval: Interval in dagen tussen metingen (gebruikt als days_of_week=None)
        days_of_week: Lijst van weekdagen (0=Monday, 6=Sunday) of None voor alle dagen
                      Bijv: [4] = alleen vrijdag, [5,6] = alleen weekend
        weeks_interval: Interval in weken bij gebruik van days_of_week (ignored als monthly_interval=True)
                        Bijv: 2 = elke 2e week, 3 = elke 3e week
        monthly_interval: Als True, pak de eerste occurrence van elke dag per maand
                          Bijv: [4] met monthly_interval=True = eerste vrijdag van elke maand

    Returns:
        Tuple van (scan_combinations, valid_nights)
    """
    # Safety check: ensure nights_list and guests_list are lists
    if isinstance(nights_list, int):
        nights_list = [nights_list]
    if isinstance(guests_list, int):
        guests_list = [guests_list]

    start_date = date.fromisoformat(period_start)
    end_date = date.fromisoformat(period_end)
    max_nights = (end_date - start_date).days

    valid_nights = [n for n in nights_list if n <= max_nights]
    if not valid_nights:
        valid_nights = [1]
        logger.warning(
            f"No valid nights in range, using 1 night. Max nights: {max_nights}"
        )

    combinations = []
    scan_id = 0

    # If days_of_week is specified, scan ALL days and filter by day-of-week
    if days_of_week is not None:
        if monthly_interval:
            logger.info("Using monthly day-of-week filter: first occurrence per month")
            # Group by month and find first occurrence of each day_of_week
            matching_dates = []
            current_year_month = (start_date.year, start_date.month)
            end_year_month = (end_date.year, end_date.month)

            # Iterate through each month
            year, month = current_year_month
            while (year, month) <= end_year_month:
                # For each day_of_week, find first occurrence in this month
                for target_day in days_of_week:
                    # Start from 1st of month
                    first_day = date(year, month, 1)

                    # Find first occurrence of target_day in this month
                    for day_offset in range(31):  # Max days in a month
                        try:
                            check_date = first_day + timedelta(days=day_offset)
                            # Stop if we've gone into next month
                            if check_date.month != month:
                                break
                            # Check if this is our target day and within range
                            if (
                                check_date.weekday() == target_day
                                and start_date <= check_date <= end_date
                            ):
                                matching_dates.append(check_date)
                                break
                        except:
                            break

                # Move to next month
                if month == 12:
                    year += 1
                    month = 1
                else:
                    month += 1

            matching_dates = sorted(matching_dates)
        else:
            logger.info(
                f"Using day-of-week filter: scanning all days in period for matches "
                f"(every {weeks_interval} week(s))"
            )

            # First, collect all matching dates
            matching_dates = []
            current_date = start_date
            while current_date <= end_date:
                if current_date.weekday() in days_of_week:
                    matching_dates.append(current_date)
                current_date += timedelta(days=1)

            # Now apply weeks_interval filter
            # Group by day-of-week, then take every Nth occurrence
            if weeks_interval > 1:
                filtered_dates = []
                for target_day in days_of_week:
                    # Get all dates for this specific day of week
                    day_dates = [d for d in matching_dates if d.weekday() == target_day]
                    # Take every Nth occurrence
                    filtered_dates.extend(day_dates[::weeks_interval])
                matching_dates = sorted(filtered_dates)

        # Create combinations for all matching dates
        for scan_date in matching_dates:
            for nights in valid_nights:
                check_out = scan_date + timedelta(days=nights)
                if check_out <= end_date + timedelta(days=1):
                    for guests in guests_list:
                        scan_id += 1
                        combinations.append(
                            (
                                scan_date.isoformat(),
                                check_out.isoformat(),
                                nights,
                                guests,
                                scan_id,
                            )
                        )

    # Otherwise, use measurement_interval
    else:
        current_date = start_date
        while current_date <= end_date:
            for nights in valid_nights:
                check_out = current_date + timedelta(days=nights)
                if check_out <= end_date + timedelta(days=1):
                    for guests in guests_list:
                        scan_id += 1
                        combinations.append(
                            (
                                current_date.isoformat(),
                                check_out.isoformat(),
                                nights,
                                guests,
                                scan_id,
                            )
                        )
            current_date += timedelta(days=measurement_interval)

    day_filter_str = f", days: {days_of_week}" if days_of_week else ""
    logger.info(
        f"Generated {len(combinations)} scan combinations "
        f"(nights: {valid_nights}, guests: {guests_list}{day_filter_str})"
    )
    return combinations, valid_nights


def process_raw_results(
    raw_results: List[dict],
    gemeente: str,
    check_in: str,
    check_out: str,
    nights: int,
    scan_id: int,
    measurement_date: str,
) -> List[dict]:
    """
    Verwerk ruwe API resultaten naar gestructureerde rows

    Args:
        raw_results: Lijst van ruwe API records
        gemeente: Gemeente naam
        check_in: Check-in datum
        check_out: Check-out datum
        nights: Aantal nachten
        scan_id: Scan ID
        measurement_date: Meetmoment timestamp

    Returns:
        Lijst van gestructureerde data dictionaries
    """
    rows = []

    for rec in raw_results:
        lat, lon = extract_coordinates(rec)
        if not lat or not lon:
            continue

        price = extract_price(rec)
        rating, reviews_count = extract_rating(rec)
        bedrooms, beds = extract_beds_info(rec)
        max_guests = extract_guest_capacity(rec)
        room_id = rec.get("room_id")
        listing_url = generate_listing_url(room_id)

        # Detecteer type en map naar Airbnb standaard
        detected_type = extract_room_type(rec)
        airbnb_property_type = get_mapped_property_type(detected_type)
        airbnb_room_type = detected_type  # Behoud originele detected type

        rows.append(
            {
                "gemeente": gemeente,
                "room_id": room_id,
                "listing_url": listing_url,
                "listing_title": rec.get("title", "") or rec.get("name", ""),
                "room_type_detected": detected_type,
                "room_type_airbnb": airbnb_room_type,
                "property_type_airbnb": airbnb_property_type,
                "bedrooms": bedrooms,
                "beds": beds,
                "max_guests": max_guests,
                "price": price,
                "rating": rating,
                "reviews_count": reviews_count,
                "latitude": lat,
                "longitude": lon,
                "scan_checkin": check_in,
                "scan_checkout": check_out,
                "scan_nights": nights,
                "scan_id": scan_id,
                "measurement_date": measurement_date,
            }
        )

    return rows


def apply_spatial_filter(
    df: pd.DataFrame, gemeente: str, gpkg_path: str
) -> pd.DataFrame:
    """
    Filter listings binnen gemeentegrenzen

    Args:
        df: DataFrame met listings
        gemeente: Gemeente naam
        gpkg_path: Pad naar GeoPackage bestand

    Returns:
        GeoDataFrame met gefilterde listings
    """
    # Laad gemeentegrenzen
    gdf_all = (
        gpd.read_file(gpkg_path, layer="gemeentegebied")
        .set_crs("EPSG:28992")
        .to_crs("EPSG:4326")
    )
    sel = gdf_all[gdf_all["naam"] == gemeente]

    if sel.empty:
        logger.error(f"No boundary found for gemeente: {gemeente}")
        return pd.DataFrame()

    # Maak GeoDataFrame
    gdf_pts = gpd.GeoDataFrame(
        df,
        geometry=[Point(xy) for xy in zip(df.longitude, df.latitude)],
        crs="EPSG:4326",
    )

    # Filter op gemeentegrenzen
    inside = gdf_pts[gdf_pts.within(sel.geometry.union_all())].copy()

    filtered_count = len(df) - len(inside)
    if filtered_count > 0:
        logger.debug(f"Filtered out {filtered_count} listings outside {gemeente}")

    return inside


def scrape_gemeente(
    gemeente: str,
    check_in: str,
    check_out: str,
    nights: int,
    guests: int,
    scan_id: int,
    gpkg_path: str,
    num_repeat_calls: int,
    zoom_value: int,
    price_min: int,
    price_max: int,
    amenities: List[str],
    currency: str,
    language: str,
    proxy_url: str,
    measurement_date: str,
) -> pd.DataFrame:
    """
    Scrape Airbnb verhuurobjecten voor één gemeente met parallelle API calls

    Args:
        gemeente: Gemeente naam
        check_in: Check-in datum (YYYY-MM-DD)
        check_out: Check-out datum (YYYY-MM-DD)
        nights: Aantal nachten
        guests: (Deprecated) Heeft geen effect op API resultaten
        scan_id: Unieke scan ID
        gpkg_path: Pad naar gemeentegrenzen GeoPackage
        num_repeat_calls: Aantal herhaalde API calls
        zoom_value: Zoom level voor API
        price_min: Minimum prijs filter
        price_max: Maximum prijs filter
        amenities: Lijst van amenity filters
        currency: Valuta code
        language: Taal code
        proxy_url: Proxy URL (optioneel)
        measurement_date: Meetmoment timestamp

    Returns:
        GeoDataFrame met scrape resultaten
    """
    logger.info(f"Scraping {gemeente}: {check_in}→{check_out} ({nights}n)")

    # Laad gemeentegrenzen voor bounding box
    gdf_all = (
        gpd.read_file(gpkg_path, layer="gemeentegebied")
        .set_crs("EPSG:28992")
        .to_crs("EPSG:4326")
    )
    sel = gdf_all[gdf_all["naam"] == gemeente]

    if sel.empty:
        logger.error(f"No boundary found for gemeente: {gemeente}")
        return pd.DataFrame()

    minx, miny, maxx, maxy = sel.total_bounds

    # Maak parallelle API calls
    all_raw_results, unique_count = make_parallel_api_calls(
        check_in,
        check_out,
        maxy,
        maxx,
        miny,
        minx,
        num_repeat_calls,
        zoom_value,
        price_min,
        price_max,
        amenities,
        currency,
        language,
        proxy_url,
        delay_between_calls=0.5,
    )

    if not all_raw_results:
        logger.warning(f"No results for {gemeente}")
        return pd.DataFrame()

    logger.info(f"{gemeente}: {unique_count} unique listings")

    # Verwerk resultaten
    rows = process_raw_results(
        all_raw_results,
        gemeente,
        check_in,
        check_out,
        nights,
        scan_id,
        measurement_date,
    )

    if not rows:
        logger.warning(f"No valid rows after processing for {gemeente}")
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Dedupliceer op room_id
    df_dedup = df.drop_duplicates("room_id")
    logger.debug(f"Deduplicated: {len(df)} → {len(df_dedup)} rows")

    # Ruimtelijk filter
    inside = apply_spatial_filter(df_dedup, gemeente, gpkg_path)

    return inside


def scrape_all(
    gemeenten: List[str],
    scan_combinations: List[Tuple[str, str, int, int, int]],
    gpkg_path: str,
    num_repeat_calls: int,
    zoom_value: int,
    price_min: int,
    price_max: int,
    amenities: List[str],
    currency: str,
    language: str,
    proxy_url: str,
    measurement_date: str,
    show_progress: bool = True,
    max_workers: int = 5,
    checkpoint_dir: Optional[str] = None,
    delay_between_scans: float = 1.0,
    delay_between_calls: float = 0.5,
    tracker=None,
) -> pd.DataFrame:
    """
    Scrape alle gemeenten en scan combinaties met parallelisatie en timing

    Args:
        gemeenten: Lijst van gemeente namen
        scan_combinations: Lijst van scan combinaties
        gpkg_path: Pad naar gemeentegrenzen GeoPackage
        num_repeat_calls: Aantal herhaalde API calls
        zoom_value: Zoom level voor API
        price_min: Minimum prijs filter
        price_max: Maximum prijs filter
        amenities: Lijst van amenity filters
        currency: Valuta code
        language: Taal code
        proxy_url: Proxy URL (optioneel)
        measurement_date: Meetmoment timestamp
        show_progress: Toon progress bar
        max_workers: Aantal parallel workers (default 5)
        checkpoint_dir: Directory voor tussentijds opslaan (None = disabled)
        delay_between_scans: Delay tussen scans in seconden (default 1.0s)
        delay_between_calls: Delay tussen API repeat calls in seconden (default 0.5s)

    Returns:
        DataFrame met alle scrape resultaten
    """
    start_time = time.time()
    all_runs = []
    total_scans = len(scan_combinations) * len(gemeenten)
    total_records = 0
    unique_listings = set()

    # Timing statistics
    timing_stats = {
        "api_calls": 0.0,
        "processing": 0.0,
        "spatial_filter": 0.0,
        "checkpoints": 0.0,
    }

    logger.info(
        f"Starting parallel scrape: {total_scans} total scans with {max_workers} workers"
    )

    # Print nice scanning header
    if show_progress:
        print("\n" + "═" * 80)
        print("  🚀 AIRBNB SCANNER GESTART")
        print("═" * 80)
        print(f"  📊 Totaal scans:      {total_scans}")
        print(f"  🏘️  Gemeenten:         {', '.join(gemeenten)}")
        print(f"  👷 Workers:           {max_workers}")
        print(f"  ⏱️  Scan delay:        {delay_between_scans}s")
        print(f"  🔄 API repeat calls:  {num_repeat_calls}")
        print("═" * 80 + "\n")

    # Create progress bar
    pbar = tqdm(
        total=total_scans,
        desc="⚡ Scanning",
        disable=not show_progress,
        unit="scan",
        bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}",
    )

    # Build task list
    tasks = []
    for ci, co, nights, guests, scan_id in scan_combinations:
        for gemeente in gemeenten:
            tasks.append((gemeente, ci, co, nights, guests, scan_id))

    # Parallel execution
    completed_scans = 0
    failed_scans = 0
    rate_limit_hits = 0  # Track rate limiting

    # Detailed timing per gemeente and phase
    gemeente_timings = {}  # Track time per gemeente
    phase_timings = {
        "api_individual": [],  # Individual API call times
        "processing_individual": [],  # Individual processing times
        "spatial_individual": [],  # Individual spatial filter times
    }

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks with delay between submissions
        future_to_task = {}
        for idx, (gemeente, ci, co, nights, guests, scan_id) in enumerate(tasks):
            # Add delay between task submissions (but not before first task)
            if idx > 0 and delay_between_scans > 0:
                time.sleep(delay_between_scans)

            future = executor.submit(
                _scrape_with_timing,
                gemeente,
                ci,
                co,
                nights,
                guests,
                scan_id,
                gpkg_path,
                num_repeat_calls,
                zoom_value,
                price_min,
                price_max,
                amenities,
                currency,
                language,
                proxy_url,
                measurement_date,
                delay_between_calls,
            )
            future_to_task[future] = (gemeente, ci, co, nights, scan_id)

        # Process completed tasks
        for future in as_completed(future_to_task):
            gemeente_name, ci, co, nights, scan_id = future_to_task[future]
            try:
                df_run, timings = future.result()
                all_runs.append(df_run)
                completed_scans += 1

                # Update tracker after each scan if provided
                if tracker is not None:
                    # Get current unique listings count
                    df_combined = pd.concat(all_runs, ignore_index=True)
                    unique_listings = (
                        df_combined["room_id"].nunique() if not df_combined.empty else 0
                    )
                    tracker.update_progress(completed_scans=completed_scans)
                    # Also update total_listings in status
                    status = tracker._load_status()
                    status["progress"]["total_listings"] = unique_listings
                    tracker._save_status(status)

                # Aggregate timings
                for key in timings:
                    if key in timing_stats:
                        timing_stats[key] += timings[key]

                # Track per-gemeente timing
                if gemeente_name not in gemeente_timings:
                    gemeente_timings[gemeente_name] = {
                        "total": 0.0,
                        "api": 0.0,
                        "processing": 0.0,
                        "spatial": 0.0,
                        "scans": 0,
                    }
                gemeente_timings[gemeente_name]["total"] += sum(timings.values())
                gemeente_timings[gemeente_name]["api"] += timings.get("api_calls", 0)
                gemeente_timings[gemeente_name]["processing"] += timings.get(
                    "processing", 0
                )
                gemeente_timings[gemeente_name]["spatial"] += timings.get(
                    "spatial_filter", 0
                )
                gemeente_timings[gemeente_name]["scans"] += 1

                # Track individual phase times
                phase_timings["api_individual"].append(timings.get("api_calls", 0))
                phase_timings["processing_individual"].append(
                    timings.get("processing", 0)
                )
                phase_timings["spatial_individual"].append(
                    timings.get("spatial_filter", 0)
                )

                # Update statistics
                new_listings = 0
                if not df_run.empty:
                    records_in_run = len(df_run)
                    total_records += records_in_run
                    before_count = len(unique_listings)
                    unique_listings.update(df_run["room_id"].unique())
                    new_listings = len(unique_listings) - before_count
                else:
                    records_in_run = 0

                # Calculate rates
                elapsed = time.time() - start_time
                avg_time_per_scan = elapsed / (pbar.n + 1)

                # This scan timing
                this_scan_time = sum(timings.values())

                # Success rate
                success_rate = (
                    (completed_scans / (completed_scans + failed_scans) * 100)
                    if (completed_scans + failed_scans) > 0
                    else 100
                )

                # Update progress bar with detailed stats
                # Status emoji based on success rate
                if success_rate >= 95:
                    status_emoji = "🟢"
                elif success_rate >= 80:
                    status_emoji = "🟡"
                else:
                    status_emoji = "🔴"

                # New listings indicator
                new_indicator = f"✨+{new_listings}" if new_listings > 0 else ""

                pbar.set_description(
                    f"⚡ {status_emoji} {gemeente_name[:10]:10s} │ {ci} ({nights}n)"
                )
                pbar.set_postfix_str(
                    f"✅{completed_scans} ❌{failed_scans} │ "
                    f"🏠{len(unique_listings):,} {new_indicator} │ "
                    f"📊{total_records:,} │ "
                    f"⏱️{this_scan_time:.1f}s (Ø{avg_time_per_scan:.1f}s)"
                )

                # Checkpoint save every 10 tasks
                if checkpoint_dir and len(all_runs) % 10 == 0:
                    checkpoint_start = time.time()
                    _save_checkpoint(all_runs, checkpoint_dir, len(all_runs))
                    timing_stats["checkpoints"] += time.time() - checkpoint_start
                    pbar.write(
                        f"  💾 Checkpoint #{len(all_runs) // 10} → {len(unique_listings):,} listings opgeslagen"
                    )

            except Exception as e:
                failed_scans += 1
                error_msg = str(e)

                # Detect rate limiting
                is_rate_limit = (
                    "405" in error_msg
                    or "429" in error_msg
                    or "Not Allowed" in error_msg
                    or "Rate limit" in error_msg
                )
                if is_rate_limit:
                    rate_limit_hits += 1
                    pbar.write(
                        f"  🚫 RATE LIMIT │ {gemeente_name} {ci} │ Verlaag workers!"
                    )
                    # Auto-adjust: als we te veel rate limits krijgen, voeg delay toe
                    if rate_limit_hits > 3:
                        time.sleep(2.0)  # Extra pauze
                        pbar.write("  ⏸️  Extra pauze (2s) na meerdere rate limits...")
                else:
                    logger.error(
                        f"Error in task {gemeente_name} {ci}: {error_msg[:100]}"
                    )
                    pbar.write(f"  ❌ FOUT │ {gemeente_name} {ci} │ {error_msg[:50]}")

            pbar.update(1)

    pbar.close()

    # Print nice completion header
    if show_progress:
        print("\n" + "═" * 80)
        print("  ✅ SCANNING VOLTOOID!")
        print("═" * 80)

    # Combineer alle runs
    combine_start = time.time()
    df_all = pd.concat(all_runs, ignore_index=True) if all_runs else pd.DataFrame()
    combine_time = time.time() - combine_start

    # Total time
    total_time = time.time() - start_time

    # Print quick summary
    if show_progress:
        unique_count = df_all["room_id"].nunique() if not df_all.empty else 0
        success_rate = (completed_scans / total_scans * 100) if total_scans > 0 else 0

        # Success rate emoji
        if success_rate >= 95:
            rate_emoji = "🟢"
        elif success_rate >= 80:
            rate_emoji = "🟡"
        else:
            rate_emoji = "🔴"

        print(f"  ⏱️  Totale tijd:       {total_time:.1f}s ({total_time / 60:.1f}m)")
        print(
            f"  {rate_emoji} Succes rate:      {completed_scans}/{total_scans} ({success_rate:.1f}%)"
        )
        print(f"  🏠 Unieke listings:   {unique_count:,}")
        print(f"  📊 Totaal records:    {len(df_all):,}")
        print(
            f"  ⚡ Gem. per scan:     {total_time / completed_scans:.1f}s"
            if completed_scans > 0
            else ""
        )

        if failed_scans > 0:
            print(f"  ⚠️  Gefaald:           {failed_scans}")
        if rate_limit_hits > 0:
            print(f"  🚫 Rate limits:       {rate_limit_hits}")

        print("═" * 80 + "\n")

    # Print detailed timing summary
    logger.info("=" * 80)
    logger.info("⏱️  DETAILED TIMING BREAKDOWN")
    logger.info("=" * 80)
    logger.info(f"Total time:           {total_time:.2f}s ({total_time / 60:.1f}m)")
    logger.info(
        f"Successful scans:     {completed_scans}/{total_scans} ({completed_scans / total_scans * 100:.1f}%)"
    )
    logger.info(f"Failed scans:         {failed_scans}")
    if rate_limit_hits > 0:
        logger.warning(
            f"⚠️ Rate limit hits:   {rate_limit_hits} (reduce workers from {max_workers} to {max(1, max_workers - 2)})"
        )
    logger.info("")

    # Overall phase breakdown
    logger.info("📊 PHASE BREAKDOWN (Total)")
    logger.info(
        f"API calls:            {timing_stats['api_calls']:.2f}s ({timing_stats['api_calls'] / total_time * 100:.1f}%)"
    )
    logger.info(
        f"Processing:           {timing_stats['processing']:.2f}s ({timing_stats['processing'] / total_time * 100:.1f}%)"
    )
    logger.info(
        f"Spatial filtering:    {timing_stats['spatial_filter']:.2f}s ({timing_stats['spatial_filter'] / total_time * 100:.1f}%)"
    )
    logger.info(
        f"Checkpoints:          {timing_stats['checkpoints']:.2f}s ({timing_stats['checkpoints'] / total_time * 100:.1f}%)"
    )
    logger.info(
        f"DataFrame combine:    {combine_time:.2f}s ({combine_time / total_time * 100:.1f}%)"
    )
    logger.info("")

    # Per-scan averages
    if completed_scans > 0:
        logger.info("📈 PER-SCAN AVERAGES")
        logger.info(f"Avg total per scan:   {total_time / completed_scans:.2f}s")
        logger.info(
            f"Avg API time:         {timing_stats['api_calls'] / completed_scans:.2f}s"
        )
        logger.info(
            f"Avg processing:       {timing_stats['processing'] / completed_scans:.2f}s"
        )
        logger.info(
            f"Avg spatial filter:   {timing_stats['spatial_filter'] / completed_scans:.2f}s"
        )
        logger.info("")

        # Min/Max/Median for phases
        import statistics

        logger.info("📉 PHASE STATISTICS (min/median/max)")

        if phase_timings["api_individual"]:
            api_times = phase_timings["api_individual"]
            logger.info(
                f"API calls:            {min(api_times):.2f}s / {statistics.median(api_times):.2f}s / {max(api_times):.2f}s"
            )

        if phase_timings["processing_individual"]:
            proc_times = phase_timings["processing_individual"]
            logger.info(
                f"Processing:           {min(proc_times):.2f}s / {statistics.median(proc_times):.2f}s / {max(proc_times):.2f}s"
            )

        if phase_timings["spatial_individual"]:
            spatial_times = phase_timings["spatial_individual"]
            logger.info(
                f"Spatial filtering:    {min(spatial_times):.2f}s / {statistics.median(spatial_times):.2f}s / {max(spatial_times):.2f}s"
            )
        logger.info("")

    # Per-gemeente breakdown
    if gemeente_timings:
        logger.info("🏘️  PER-GEMEENTE TIMING")
        logger.info(
            f"{'Gemeente':<20} {'Scans':>6} {'Total':>8} {'API':>8} {'Process':>8} {'Spatial':>8} {'Avg/scan':>9}"
        )
        logger.info("-" * 80)
        for gemeente, times in sorted(
            gemeente_timings.items(), key=lambda x: x[1]["total"], reverse=True
        ):
            avg_per_scan = times["total"] / times["scans"] if times["scans"] > 0 else 0
            logger.info(
                f"{gemeente:<20} {times['scans']:>6} "
                f"{times['total']:>7.1f}s {times['api']:>7.1f}s "
                f"{times['processing']:>7.1f}s {times['spatial']:>7.1f}s "
                f"{avg_per_scan:>8.2f}s"
            )

    logger.info("=" * 80)

    logger.info(
        f"Scraping complete: {len(df_all)} total records, "
        f"{df_all['room_id'].nunique() if not df_all.empty else 0} unique listings"
    )

    return df_all


def _scrape_with_timing(
    gemeente: str,
    check_in: str,
    check_out: str,
    nights: int,
    guests: int,
    scan_id: int,
    gpkg_path: str,
    num_repeat_calls: int,
    zoom_value: int,
    price_min: int,
    price_max: int,
    amenities: List[str],
    currency: str,
    language: str,
    proxy_url: str,
    measurement_date: str,
    delay_between_calls: float = 0.5,
) -> tuple:
    """
    Scrape with timing measurements

    Args:
        delay_between_calls: Delay tussen API repeat calls in seconden

    Returns:
        Tuple of (DataFrame, timing_dict)
    """
    timings = {
        "api_calls": 0.0,
        "processing": 0.0,
        "spatial_filter": 0.0,
    }

    api_start = time.time()

    # Load gemeente boundaries for bounding box
    gdf_all = (
        gpd.read_file(gpkg_path, layer="gemeentegebied")
        .set_crs("EPSG:28992")
        .to_crs("EPSG:4326")
    )
    sel = gdf_all[gdf_all["naam"] == gemeente]

    if sel.empty:
        logger.error(f"No boundary found for gemeente: {gemeente}")
        return pd.DataFrame(), timings

    minx, miny, maxx, maxy = sel.total_bounds

    # Make parallel API calls
    all_raw_results, unique_count = make_parallel_api_calls(
        check_in,
        check_out,
        maxy,
        maxx,
        miny,
        minx,
        num_repeat_calls,
        zoom_value,
        price_min,
        price_max,
        amenities,
        currency,
        language,
        proxy_url,
        delay_between_calls,
    )

    timings["api_calls"] = time.time() - api_start

    if not all_raw_results:
        return pd.DataFrame(), timings

    # Process results
    process_start = time.time()
    rows = process_raw_results(
        all_raw_results,
        gemeente,
        check_in,
        check_out,
        nights,
        scan_id,
        measurement_date,
    )

    if not rows:
        return pd.DataFrame(), timings

    df = pd.DataFrame(rows)
    df_dedup = df.drop_duplicates("room_id")
    timings["processing"] = time.time() - process_start

    # Spatial filter
    spatial_start = time.time()
    inside = apply_spatial_filter(df_dedup, gemeente, gpkg_path)
    timings["spatial_filter"] = time.time() - spatial_start

    return inside, timings


def _save_checkpoint(all_runs: List[pd.DataFrame], checkpoint_dir: str, batch_num: int):
    """Save intermediate checkpoint als parquet EN Excel"""
    import os
    from src.data.data_processor import calculate_availability, prepare_export_data

    os.makedirs(checkpoint_dir, exist_ok=True)

    df_checkpoint = pd.concat(all_runs, ignore_index=True)

    # Save parquet (snel, voor recovery)
    checkpoint_parquet = os.path.join(
        checkpoint_dir, f"checkpoint_batch_{batch_num}.parquet"
    )
    df_checkpoint.to_parquet(checkpoint_parquet, index=False)

    # Save Excel (bekijkbaar, voor tussentijdse analyse)
    try:
        # Get period from data
        period_start = df_checkpoint["scan_checkin"].min()
        period_end = df_checkpoint["scan_checkout"].max()

        # Calculate availability
        df_availability = calculate_availability(
            df_checkpoint, str(period_start)[:10], str(period_end)[:10]
        )

        # Prepare export
        df_export = prepare_export_data(df_checkpoint)

        # Write Excel with basic sheets
        checkpoint_excel = os.path.join(
            checkpoint_dir, f"checkpoint_batch_{batch_num}.xlsx"
        )
        with pd.ExcelWriter(checkpoint_excel, engine="openpyxl") as writer:
            df_export.to_excel(writer, sheet_name="All Data", index=False)

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
            availability_export.to_excel(
                writer, sheet_name="Availability Summary", index=False
            )

        logger.info(
            f"💾 Checkpoint saved: batch {batch_num}, "
            f"{len(df_checkpoint)} records, "
            f"{df_checkpoint['room_id'].nunique()} unique listings"
        )
    except Exception as e:
        logger.warning(
            f"Failed to save Excel checkpoint: {e}. Parquet saved successfully."
        )
        logger.info(
            f"💾 Checkpoint saved (parquet only): {batch_num} batches, {len(df_checkpoint)} records"
        )
