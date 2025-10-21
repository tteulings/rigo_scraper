#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Map visualization functionality
"""

import logging
import os
from typing import List, Optional

import folium
import geopandas as gpd
import pandas as pd

logger = logging.getLogger(__name__)

# Kleurenschema voor property types
PROPERTY_COLORS = {
    "Entire home": "#3498db",  # Blauw
    "Private room": "#e67e22",  # Oranje
    "Shared room": "#e91e63",  # Pink/Magenta
    "Guesthouse": "#27ae60",  # Groen
    "Hotel": "#f39c12",  # Goud
    "Unique stay": "#9b59b6",  # Paars
    "Unknown": "#95a5a6",  # Grijs (fallback)
}


def create_map(
    df_map: pd.DataFrame,
    gdf_gemeenten: gpd.GeoDataFrame,
    gemeenten: List[str],
    output_dir: Optional[str] = None,
) -> folium.Map:
    # Filter gemeentegrenzen
    gdf_sel = gdf_gemeenten[gdf_gemeenten["naam"].isin(gemeenten)]

    # Bepaal center
    center_lat = df_map["latitude"].mean()
    center_lon = df_map["longitude"].mean()

    # Maak kaart met moderne styling
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles="CartoDB positron",  # Modern, clean look
        zoom_control=True,
        scrollWheelZoom=True,
        dragging=True,
    )

    # Voeg gemeentegrenzen toe
    folium.GeoJson(
        gdf_sel,
        style_function=lambda x: {
            "fillColor": "#E8F4F8",
            "color": "#2E86AB",
            "weight": 2.5,
            "fillOpacity": 0.15,
            "dashArray": "5, 5",
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["naam"],
            aliases=["Gemeente:"],
            style="background-color: white; color: #333; font-family: Arial; font-size: 14px; padding: 10px;",
        ),
    ).add_to(m)

    for idx in df_map.index:
        row = df_map.loc[idx]
        prop_type = row.get("property_type_airbnb", "Unknown")
        color = PROPERTY_COLORS.get(prop_type, "#95a5a6")

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=7,
            popup=folium.Popup(_create_popup_html(row, color), max_width=350),
            tooltip=folium.Tooltip(_create_tooltip_html(row, color)),
            color="white",
            fill=True,
            fillColor=color,
            fillOpacity=0.9,
            weight=2.5,
        ).add_to(m)

    # Voeg legende toe (alleen voor types die in data voorkomen)
    present_types = df_map["property_type_airbnb"].unique().tolist()
    legend_html = _create_legend_html(present_types)
    m.get_root().html.add_child(folium.Element(legend_html))

    if output_dir:
        _save_map(m, output_dir)

    return m


def _create_popup_html(row: pd.Series, color: str) -> str:
    """Genereer HTML voor popup met kalender als hoofdfocus"""
    # Maak een simpele kalender grid
    total_days = int(row.get("total_days", 30))
    available_days = int(row.get("days_available", 0))

    # Only show calendar if we have reasonable data
    show_calendar = total_days <= 60 and total_days > 0

    if show_calendar:
        # Genereer kalender blokjes (max 7 per rij)
        calendar_html = '<div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin: 15px 0;">'
        for day in range(min(total_days, 60)):  # Cap at 60 days for display
            # Aanname: de eerste N dagen zijn beschikbaar (je zou dit kunnen verbeteren met echte data)
            is_available = day < available_days
            bg_color = color if is_available else "#e0e0e0"
            calendar_html += f'<div style="width: 24px; height: 24px; background: {bg_color}; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 10px; color: white; font-weight: bold;" title="Dag {day + 1}">{day + 1}</div>'
        calendar_html += "</div>"
    else:
        # Simple text display for long periods or point-in-time
        calendar_html = f'<div style="margin: 15px 0; text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px;"><div style="font-size: 24px; font-weight: bold; color: {color};">{available_days} / {total_days}</div><div style="font-size: 12px; color: #666; margin-top: 5px;">days available</div></div>'

    return f'''
    <div style="font-family: Arial, sans-serif; min-width: 280px; max-width: 320px;">
        <div style="background: linear-gradient(135deg, {color} 0%, {color}cc 100%); 
                    color: white; padding: 10px; margin: -10px -10px 8px -10px; 
                    border-radius: 4px 4px 0 0;">
            <div style="font-size: 14px; font-weight: bold; margin-bottom: 3px;">
                {row["listing_title"][:50]}
            </div>
            <div style="font-size: 11px; opacity: 0.9;">
                {row["property_type_airbnb"]} | EUR {row["price"]:.0f}/nacht
                {" | Rating: " + str(row["rating"]) if pd.notna(row["rating"]) else ""}
            </div>
        </div>
        
        <div style="padding: 10px; background: white; border-radius: 0 0 4px 4px;">
            <div style="font-weight: bold; color: {color}; font-size: 16px; margin-bottom: 10px; text-align: center;">
                {row["availability_rate"]:.0f}% Beschikbaar
            </div>
            
            {calendar_html}
            
            <div style="font-size: 10px; color: #666; margin-top: 8px; display: flex; justify-content: center; gap: 12px;">
                <span>
                    <span style="display: inline-block; width: 10px; height: 10px; background: {color}; border-radius: 2px; margin-right: 4px;"></span>
                    Beschikbaar
                </span>
                <span>
                    <span style="display: inline-block; width: 10px; height: 10px; background: #e0e0e0; border-radius: 2px; margin-right: 4px;"></span>
                    Bezet
                </span>
            </div>
            
            <div style="margin-top: 10px; text-align: center;">
                <a href="{row["listing_url"]}" target="_blank" 
                   style="display: inline-block; background-color: {color}; color: white; 
                          padding: 6px 14px; text-decoration: none; border-radius: 4px;
                          font-weight: bold; font-size: 11px;">
                    Bekijk op Airbnb &rarr;
                </a>
            </div>
        </div>
    </div>
    '''


def _create_tooltip_html(row: pd.Series, color: str) -> str:
    """Genereer HTML voor tooltip"""
    return f"""
    <div style="font-family: Arial; font-size: 12px;">
        <b style="color: {color};">{row["listing_title"][:45]}</b><br>
        <span style="color: #666;">{row["property_type_airbnb"]}</span> | 
        <b>EUR {row["price"]:.0f}</b><br>
        Beschikbaar: <b style="color: {color};">{row["availability_rate"]:.0f}%</b>
    </div>
    """


def _create_legend_html(present_types: List[str]) -> str:
    """Genereer HTML voor legende - alleen voor types die in data voorkomen"""
    # Filter colors to only show present types
    filtered_colors = {
        prop_type: color
        for prop_type, color in PROPERTY_COLORS.items()
        if prop_type in present_types or prop_type == "Unknown"
    }

    # Check if there are any types not in standard list
    unknown_types = [t for t in present_types if t not in PROPERTY_COLORS]
    if unknown_types and "Unknown" not in filtered_colors:
        filtered_colors["Unknown"] = PROPERTY_COLORS["Unknown"]

    legend_items = "".join(
        [
            f'<div style="margin: 8px 0; display: flex; align-items: center;">'
            f'<span style="display: inline-block; width: 16px; height: 16px; '
            f"background-color: {color}; border-radius: 50%; margin-right: 10px; "
            f'border: 2px solid white; box-shadow: 0 1px 3px rgba(0,0,0,0.3);"></span>'
            f'<span style="font-weight: 500;">{prop_type}</span></div>'
            for prop_type, color in filtered_colors.items()
        ]
    )

    return f"""
    <div style="position: fixed; 
                top: 80px; right: 20px; 
                width: 180px;
                background-color: white;
                border: 3px solid #2c3e50;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.25);
                z-index: 9999;
                padding: 16px;
                font-family: Arial, sans-serif;
                font-size: 13px;">
        <div style="font-weight: bold; margin-bottom: 12px; color: #2c3e50; font-size: 15px; 
                    border-bottom: 2px solid #ecf0f1; padding-bottom: 8px;">
            🏠 Accommodatietypen
        </div>
        {legend_items}
        <div style="margin-top: 12px; padding-top: 8px; border-top: 1px solid #ecf0f1; 
                    font-size: 11px; color: #7f8c8d; text-align: center;">
            Klik op marker voor details
        </div>
    </div>
    """


def _save_map(m: folium.Map, output_dir: str) -> None:
    """Sla kaart op als HTML (beste formaat voor interactieve kaarten)"""
    map_html_path = os.path.join(output_dir, "map.html")
    m.save(map_html_path)
    print(f"✓ Kaart opgeslagen: {map_html_path}")
