#!/usr/bin/env python3
"""
Room type configuration and mapping logic
"""

# Mappings van gedetecteerde room types naar gestandaardiseerde Airbnb types
# Gebaseerd op Airbnb's hiërarchie: Space Type (Entire/Private/Shared) + Property Type
ROOM_TYPE_MAPPING = {
    # === ENTIRE HOMES & APARTMENTS (Hele woningen voor gasten) ===
    # Houses
    "Entire home": "Entire home",
    "Entire house": "Entire home",
    "Entire cabin": "Entire home",
    "Entire chalet": "Entire home",
    "Entire cottage": "Entire home",
    "Entire bungalow": "Entire home",
    "Entire villa": "Entire home",
    "Entire vacation home": "Entire home",
    "Entire townhouse": "Entire home",
    "Entire place": "Entire home",
    # Apartments
    "Entire rental unit": "Entire home",
    "Entire apartment": "Entire home",
    "Entire condo": "Entire home",
    "Entire serviced apartment": "Entire home",
    "Entire loft": "Entire home",
    # === PRIVATE ROOMS (Privékamer in een woning) ===
    "Room in home": "Private room",
    "Private room in home": "Private room",
    "Room in rental unit": "Private room",
    "Private room in rental unit": "Private room",
    "Private room in apartment": "Private room",
    "Room in apartment": "Private room",
    # === SHARED ROOMS (Gedeelde kamer) ===
    "Shared room": "Shared room",
    "Shared room in home": "Shared room",
    "Shared room in apartment": "Shared room",
    # === GUESTHOUSE / BED & BREAKFAST (Gastenverblijf, vaak bij eigenaar) ===
    "Entire guesthouse": "Guesthouse",
    "Entire guest suite": "Guesthouse",
    "Room in bed and breakfast": "Guesthouse",
    "Entire bed and breakfast": "Guesthouse",
    "Private room in bed and breakfast": "Guesthouse",
    "Shared room in bed and breakfast": "Guesthouse",
    "Entire bed & breakfast": "Guesthouse",
    # === HOTELS (Commerciële accommodaties) ===
    "Room in boutique hotel": "Hotel",
    "Room in hotel": "Hotel",
    "Hotel room": "Hotel",
    "Boutique hotel": "Hotel",
    "Room in serviced apartment": "Hotel",
    # === UNIQUE STAYS (Bijzondere accommodaties) ===
    "Unique space": "Unique stay",  # Old category name
    "Boat": "Unique stay",
    "Entire boat": "Unique stay",
    "Houseboat": "Unique stay",
    "Camper/RV": "Unique stay",
    "Campsite": "Unique stay",
    "Tent": "Unique stay",
    "Tiny home": "Unique stay",
    "Treehouse": "Unique stay",
    "Farm stay": "Unique stay",
    "Nature lodge": "Unique stay",
    "Earth home": "Unique stay",
    "Yurt": "Unique stay",
    "Barn": "Unique stay",
    # === Van classifier (detected types) ===
    "bed_and_breakfast": "Guesthouse",
    "boutique_hotel": "Hotel",
    "hotel": "Hotel",
    "hotel_room": "Hotel",
    "guesthouse": "Guesthouse",
    "barn": "Unique stay",
    "tent": "Unique stay",
    "yurt_tent": "Unique stay",
    "camper_rv": "Unique stay",
    "houseboat": "Unique stay",
    "tiny_home": "Unique stay",
    "apartment": "Entire home",
    "loft": "Entire home",
    "house": "Entire home",
    "villa": "Entire home",
    "bungalow": "Entire home",
    "chalet": "Entire home",
    "cottage": "Entire home",
    "cabin": "Entire home",
    "home": "Entire home",
    "entire_home": "Entire home",
    "private_room": "Private room",
    "shared_room": "Shared room",
    "accommodation": "Entire home",
}

# Standaard Airbnb categorieën voor analyse
# Gebaseerd op Airbnb's eigen indeling die je in hun filters ziet
STANDARD_PROPERTY_TYPES = [
    "Entire home",  # Hele woning/appartement (houses, apartments, condos, villas, etc.)
    "Private room",  # Privékamer in een woning/appartement
    "Shared room",  # Gedeelde kamer
    "Guesthouse",  # Gastenverblijf / B&B (persoonlijke hospitality)
    "Hotel",  # Hotels en boutique hotels (commercieel)
    "Unique stay",  # Bijzondere accommodaties (boats, tents, treehouses, etc.)
]


def get_mapped_property_type(detected_type: str, auto_learn: bool = True) -> str:
    """
    Map een gedetecteerd room type naar een gestandaardiseerd Airbnb type

    Args:
        detected_type: Het gedetecteerde room type string
        auto_learn: Of nieuwe types automatisch geleerd moeten worden

    Returns:
        Gestandaardiseerd Airbnb property type
    """
    # Direct match
    if detected_type in ROOM_TYPE_MAPPING:
        return ROOM_TYPE_MAPPING[detected_type]

    # Case-insensitive match
    for key, value in ROOM_TYPE_MAPPING.items():
        if detected_type.lower() == key.lower():
            return value

    # Als auto-learning enabled, gebruik de learner
    if auto_learn:
        try:
            from src.config.room_type_auto_learner import auto_learn_room_type
            return auto_learn_room_type(detected_type, ROOM_TYPE_MAPPING)
        except Exception as e:
            import logging
            logging.warning(f"Auto-learning failed: {e}, falling back to manual mapping")

    # Partial match op lowercase
    detected_lower = detected_type.lower()

    # Check eerst op Hotels (commercieel)
    if "boetiekhotel" in detected_lower or "boutique" in detected_lower:
        return "Hotel"
    elif "hotel" in detected_lower:
        return "Hotel"

    # Check op Guesthouse / B&B (persoonlijke hospitality)
    elif (
        "bed & breakfast" in detected_lower
        or "bed and breakfast" in detected_lower
        or "b&b" in detected_lower
    ):
        return "Guesthouse"
    elif "gastsuite" in detected_lower or "gastenverblijf" in detected_lower:
        return "Guesthouse"
    elif "guesthouse" in detected_lower or "guest suite" in detected_lower:
        return "Guesthouse"

    # Check op Unique stays
    elif "schuur" in detected_lower or "barn" in detected_lower:
        return "Unique stay"
    elif (
        "boat" in detected_lower
        or "houseboat" in detected_lower
        or "woonboot" in detected_lower
    ):
        return "Unique stay"
    elif (
        "tent" in detected_lower
        or "camper" in detected_lower
        or "rv" in detected_lower
        or "tiny" in detected_lower
        or "tree" in detected_lower
        or "yurt" in detected_lower
        or "farm" in detected_lower
    ) and "apartment" not in detected_lower:
        return "Unique stay"

    # Check op Shared room (moet voor Private room check)
    elif "shared" in detected_lower and "room" in detected_lower:
        return "Shared room"

    # Check op Private room (privékamer in woning/appartement)
    elif (
        "private" in detected_lower and "room" in detected_lower
    ) or "room in" in detected_lower:
        return "Private room"

    # Check op Entire home (hele woningen/appartementen)
    elif "entire" in detected_lower or (
        "apartment" in detected_lower
        or "condo" in detected_lower
        or "loft" in detected_lower
        or "flat" in detected_lower
        or "home" in detected_lower
        or "house" in detected_lower
        or "huis" in detected_lower
        or "woning" in detected_lower
        or "cabin" in detected_lower
        or "cottage" in detected_lower
        or "villa" in detected_lower
        or "bungalow" in detected_lower
        or "chalet" in detected_lower
    ):
        return "Entire home"

    elif "accommodatie" in detected_lower or "accommodation" in detected_lower:
        # Generic accommodation - default to Entire home
        return "Entire home"

    # Ultimate fallback
    return "Unknown"
