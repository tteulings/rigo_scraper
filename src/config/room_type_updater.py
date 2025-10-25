#!/usr/bin/env python3
"""
Simple Room Type Config Updater
Schrijft nieuwe mappings direct naar room_type_config.py
"""

import re
from pathlib import Path
from datetime import datetime


def add_mapping_to_config(
    detected_type: str, mapped_category: str, config_file: str = "src/config/room_type_config.py"
) -> tuple[bool, str]:
    """
    Voeg een nieuwe mapping toe aan room_type_config.py
    
    Args:
        detected_type: Het nieuwe room type
        mapped_category: De categorie waar het naar moet mappen
        config_file: Pad naar config bestand
        
    Returns:
        (success, message)
    """
    config_path = Path(config_file)
    
    if not config_path.exists():
        return False, f"❌ Config bestand niet gevonden: {config_file}"
    
    # Lees het bestand
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check of deze mapping al bestaat
    if f'"{detected_type}"' in content or f"'{detected_type}'" in content:
        return False, f"⚠️ Type '{detected_type}' bestaat al in configuratie"
    
    # Vind de ROOM_TYPE_MAPPING dictionary
    if "ROOM_TYPE_MAPPING = {" not in content:
        return False, "❌ Kon ROOM_TYPE_MAPPING niet vinden in config"
    
    # Vind de laatste regel voor de sluitende }
    lines = content.split("\n")
    insert_index = None
    
    for i, line in enumerate(lines):
        # Zoek de laatste regel voor de } van ROOM_TYPE_MAPPING
        if line.strip() == "}" and i > 0:
            # Check of dit de } van ROOM_TYPE_MAPPING is
            # Door terug te kijken of er mapping entries zijn
            if any('"' in lines[j] and ":" in lines[j] for j in range(max(0, i-5), i)):
                insert_index = i
                break
    
    if insert_index is None:
        return False, "❌ Kon einde van ROOM_TYPE_MAPPING niet vinden"
    
    # Maak de nieuwe entry
    new_entry = f'    "{detected_type}": "{mapped_category}",'
    
    # Voeg toe
    lines.insert(insert_index, new_entry)
    
    # Schrijf terug
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return True, f"✅ Mapping toegevoegd: '{detected_type}' → '{mapped_category}'"
    except Exception as e:
        return False, f"❌ Fout bij schrijven: {e}"


def add_bulk_mappings(
    mappings: list[tuple[str, str]], config_file: str = "src/config/room_type_config.py"
) -> tuple[int, int, list[str]]:
    """
    Voeg meerdere mappings toe
    
    Args:
        mappings: Lijst van (detected_type, mapped_category) tuples
        config_file: Pad naar config bestand
        
    Returns:
        (success_count, skip_count, messages)
    """
    success_count = 0
    skip_count = 0
    messages = []
    
    for detected_type, mapped_category in mappings:
        success, message = add_mapping_to_config(detected_type, mapped_category, config_file)
        messages.append(message)
        if success:
            success_count += 1
        else:
            skip_count += 1
    
    return success_count, skip_count, messages


def get_current_mappings(config_file: str = "src/config/room_type_config.py") -> dict:
    """
    Lees de huidige mappings uit het config bestand
    
    Returns:
        Dictionary met mappings
    """
    try:
        # Import the mapping from the file
        import sys
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("room_type_config", config_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return dict(module.ROOM_TYPE_MAPPING)
    except Exception:
        return {}






