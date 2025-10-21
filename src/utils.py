#!/usr/bin/env python3
"""
Utility functions for Airbnb scraper
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def extract_guest_capacity(rec: dict) -> Optional[int]:
    """
    Extraheer guest capacity uit API record

    Args:
        rec: Airbnb API record

    Returns:
        Guest capacity as int or None
    """
    # Try direct person capacity field
    person_capacity = rec.get("personCapacity") or rec.get("person_capacity")
    if person_capacity:
        try:
            return int(person_capacity)
        except (ValueError, TypeError):
            pass

    # Try from structuredContent
    structured = rec.get("structuredContent", {})
    primary_line = structured.get("primaryLine", [])

    for item in primary_line:
        body = item.get("body", "").lower()

        # Look for "X gast" or "X gasten" patterns
        if "gast" in body:
            try:
                # Extract first number
                parts = body.split()
                for i, part in enumerate(parts):
                    if "gast" in part and i > 0:
                        return int(parts[i - 1])
            except (ValueError, IndexError):
                pass

    return None


def extract_beds_info(rec: dict) -> Tuple[Optional[int], Optional[int]]:
    """
    Extraheer slaapkamer en bed informatie uit structuredContent

    Args:
        rec: Airbnb API record

    Returns:
        Tuple van (bedrooms, beds)
    """
    structured = rec.get("structuredContent", {})
    primary_line = structured.get("primaryLine", [])

    bedrooms = None
    beds = None

    for item in primary_line:
        body = item.get("body", "").lower()
        item_type = item.get("type", "")

        if item_type == "BEDINFO":
            # Parse slaapkamer info
            if "slaapkamer" in body:
                try:
                    bedrooms = int(body.split()[0])
                except (ValueError, IndexError):
                    pass

            # Parse bed info
            if "bed" in body or "slaapbank" in body:
                try:
                    count = int(body.split()[0])
                    if beds is None:
                        beds = count
                    else:
                        beds += count
                except (ValueError, IndexError):
                    pass

    return bedrooms, beds


def extract_price(rec: dict) -> float:
    """
    Extraheer prijs uit API record

    Args:
        rec: Airbnb API record

    Returns:
        Prijs als float (0 als niet gevonden)
    """
    price_data = rec.get("price", {})
    price_unit = price_data.get("unit", {})
    return price_unit.get("amount", 0) if price_unit else 0


def extract_rating(rec: dict) -> Tuple[Optional[float], Optional[int]]:
    """
    Extraheer rating en reviews count uit API record

    Args:
        rec: Airbnb API record

    Returns:
        Tuple van (rating, reviews_count)
    """
    rating_data = rec.get("rating", {})
    rating = rating_data.get("value", None) if rating_data else None
    reviews_count = rating_data.get("reviewCount", None) if rating_data else None

    if reviews_count:
        try:
            reviews_count = int(reviews_count)
        except (ValueError, TypeError):
            reviews_count = None

    return rating, reviews_count


def extract_coordinates(rec: dict) -> Tuple[Optional[float], Optional[float]]:
    """
    Extraheer coördinaten uit API record

    Args:
        rec: Airbnb API record

    Returns:
        Tuple van (latitude, longitude)
    """
    coords = rec.get("coordinates", {})
    lat = coords.get("latitude")
    lon = coords.get("longitud") or coords.get("longitude")
    return lat, lon


def generate_listing_url(room_id: Optional[str]) -> Optional[str]:
    """
    Genereer Airbnb listing URL

    Args:
        room_id: Room ID

    Returns:
        URL string of None
    """
    return f"https://www.airbnb.nl/rooms/{room_id}" if room_id else None


def setup_logging(verbose: bool = False, log_file: str = None) -> None:
    """
    Setup logging configuratie

    Args:
        verbose: If True, set level to INFO. If False, set to WARNING (default)
        log_file: Optional log file path. If None, logs to console.
    """
    level = logging.INFO if verbose else logging.WARNING
    handlers = []

    if log_file:
        # Log to file
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        handlers.append(file_handler)
    else:
        # Log to console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        handlers.append(console_handler)

    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True,  # Override any existing config
    )
