#!/usr/bin/env python3
"""
API client for Airbnb with retry logic
"""

import logging
import time
from typing import Optional

from pyairbnb import search_all

logger = logging.getLogger(__name__)


def make_api_call(
    check_in: str,
    check_out: str,
    ne_lat: float,
    ne_long: float,
    sw_lat: float,
    sw_long: float,
    zoom_value: int,
    price_min: int,
    price_max: int,
    amenities: list,
    currency: str,
    language: str,
    proxy_url: Optional[str],
) -> list:
    """
    Voer een enkele Airbnb API call uit

    Args:
        check_in: Check-in datum (YYYY-MM-DD)
        check_out: Check-out datum (YYYY-MM-DD)
        ne_lat: Noordoost latitude
        ne_long: Noordoost longitude
        sw_lat: Zuidwest latitude
        sw_long: Zuidwest longitude
        zoom_value: Zoom level
        price_min: Minimum prijs
        price_max: Maximum prijs
        amenities: Lijst van amenities
        currency: Valuta code
        language: Taal code
        proxy_url: Proxy URL (optioneel)

    Returns:
        List van listings
    """
    results = search_all(
        check_in=check_in,
        check_out=check_out,
        ne_lat=ne_lat,
        ne_long=ne_long,
        sw_lat=sw_lat,
        sw_long=sw_long,
        zoom_value=zoom_value,
        currency=currency,
        language=language,
        price_min=price_min,
        price_max=price_max,
        amenities=amenities,
        proxy_url=proxy_url if proxy_url else "",
    )

    # search_all returns a list of results
    return results if results else []


def make_api_call_with_retry(
    check_in: str,
    check_out: str,
    ne_lat: float,
    ne_long: float,
    sw_lat: float,
    sw_long: float,
    zoom_value: int,
    price_min: int,
    price_max: int,
    amenities: list,
    currency: str,
    language: str,
    proxy_url: Optional[str],
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> list:
    """
    API call met exponential backoff retry logic

    Args:
        (same as make_api_call)
        max_retries: Maximum aantal retry pogingen
        retry_delay: Initiële delay tussen retries in seconden

    Returns:
        List van listings

    Raises:
        Exception: Als alle retries falen
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            return make_api_call(
                check_in,
                check_out,
                ne_lat,
                ne_long,
                sw_lat,
                sw_long,
                zoom_value,
                price_min,
                price_max,
                amenities,
                currency,
                language,
                proxy_url,
            )
        except Exception as e:
            last_error = e

            # Compact error message (niet de hele HTML body printen)
            error_str = str(e)
            if len(error_str) > 150:
                error_str = error_str[:150] + "..."

            # Detecteer rate limiting (405, 429) en gebruik langere delays
            is_rate_limit = (
                "405" in error_str or "429" in error_str or "Not Allowed" in error_str
            )

            if attempt < max_retries - 1:
                # Langere delays voor rate limiting
                wait_time = (
                    retry_delay * (2**attempt)
                    if not is_rate_limit
                    else retry_delay * (3**attempt)
                )

                if is_rate_limit:
                    logger.warning(
                        f"⚠️ Rate limit hit (attempt {attempt + 1}/{max_retries}). "
                        f"Waiting {wait_time:.1f}s..."
                    )
                else:
                    logger.warning(
                        f"API call failed (attempt {attempt + 1}/{max_retries}): {error_str}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                time.sleep(wait_time)
            else:
                if is_rate_limit:
                    logger.error(
                        "❌ Rate limit: Too many requests. Reduce workers or increase delays."
                    )
                else:
                    logger.error(
                        f"API call failed after {max_retries} attempts: {error_str}"
                    )

    raise Exception(f"API call failed after {max_retries} attempts") from last_error


def make_parallel_api_calls(
    check_in: str,
    check_out: str,
    ne_lat: float,
    ne_long: float,
    sw_lat: float,
    sw_long: float,
    num_repeat_calls: int,
    zoom_value: int,
    price_min: int,
    price_max: int,
    amenities: list,
    currency: str,
    language: str,
    proxy_url: Optional[str],
    delay_between_calls: float = 0.5,
) -> tuple:
    """
    Maak meerdere parallelle API calls

    Args:
        delay_between_calls: Delay in seconden tussen API calls (default 0.5s)

    Returns:
        Tuple van (all_raw_results, unique_count)
    """
    all_raw_results = []
    unique_ids = set()

    for i in range(num_repeat_calls):
        try:
            # Add delay between repeat calls (but not before first call)
            if i > 0 and delay_between_calls > 0:
                time.sleep(delay_between_calls)
            
            res = make_api_call_with_retry(
                check_in,
                check_out,
                ne_lat,
                ne_long,
                sw_lat,
                sw_long,
                zoom_value,
                price_min,
                price_max,
                amenities,
                currency,
                language,
                proxy_url,
            )
            all_raw_results.extend(res)
            unique_ids.update(
                [
                    r.get("room_id") or r.get("id")
                    for r in res
                    if r.get("room_id") or r.get("id")
                ]
            )
        except Exception as e:
            logger.error(f"Failed to make API call: {e}")

    return all_raw_results, len(unique_ids)
