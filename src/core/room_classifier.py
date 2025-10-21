#!/usr/bin/env python3
"""
Room type classification logic
"""

import logging

logger = logging.getLogger(__name__)


def extract_room_type(rec: dict) -> str:
    """
    Extraheer kamertype met verbeterde classificatie

    Args:
        rec: Airbnb API record

    Returns:
        String met gedetecteerd room type
    """
    # Probeer eerst category
    category = rec.get("category", "")
    if category:
        return category.lower().replace(" ", "_")

    # Probeer type field
    room_type = rec.get("type", "")
    if room_type:
        return room_type.lower().replace(" ", "_")

    # Parse uit titel
    title = rec.get("title", "").lower()
    name = rec.get("name", "").lower()
    combined = f"{title} {name}"

    # Speciale/unieke types EERST (meest specifiek)
    if "camper" in combined or "caravan" in combined or "rv" in combined:
        return "camper_rv"
    elif (
        "bed and breakfast" in combined
        or "bed & breakfast" in combined
        or "b&b" in combined
    ):
        return "bed_and_breakfast"
    elif (
        "boetiekhotel" in combined
        or "boutique hotel" in combined
        or "boutique-hotel" in combined
    ):
        return "boutique_hotel"
    elif (
        "hotel" in combined
        or "hotelkamer" in combined
        or "hotel kamer" in combined
        or "hotel room" in combined
    ):
        return "hotel"
    elif (
        "woonboot" in combined
        or "houseboat" in combined
        or "boat" in combined
        or "boot " in combined
    ):
        return "houseboat"
    elif "schuur" in combined or "barn" in combined or "schuur" in title:
        return "barn"
    elif (
        "yurt" in combined
        or "joert" in combined
        or " tent " in combined
        or "tent in " in combined
        or "camping" in combined
    ):
        return "tent"
    elif (
        "gastenverblijf" in combined
        or "gastsuite" in combined
        or "gastensuite" in combined
        or "guesthouse" in combined
        or "guest house" in combined
        or "guest suite" in combined
    ):
        return "guesthouse"
    elif (
        "tiny home" in combined or "tiny house" in combined or "tiny-house" in combined
    ):
        return "tiny_home"
    elif "loft" in combined:
        return "loft"
    elif "appartement" in combined or "apartment" in combined or "flat" in combined:
        return "apartment"
    elif "villa" in combined:
        return "villa"
    elif "bungalow" in combined:
        return "bungalow"
    elif "chalet" in combined:
        return "chalet"
    elif "cottage" in combined or "huisje" in combined:
        return "cottage"
    elif "cabin" in combined or "hut" in combined:
        return "cabin"
    elif (
        "home in" in combined
        or "vacation home" in combined
        or "holiday home" in combined
    ):
        return "home"
    elif "gedeelde kamer" in combined or "shared room" in combined:
        return "shared_room"
    elif (
        "privékamer" in combined
        or "private room" in combined
        or "room in" in combined
        or "kamer in" in combined
    ):
        return "private_room"
    elif "accommodatie" in combined or "accommodation" in combined:
        return "accommodation"
    elif "huis" in combined or "house" in combined or "woning" in combined:
        return "house"
    elif "entire" in combined or "geheel" in combined:
        return "entire_home"

    return "unknown"
