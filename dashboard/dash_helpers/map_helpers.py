"""Map creation helpers for Dash dashboard"""

import geopandas as gpd
import folium
from typing import List
from pathlib import Path

# Import project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent  # dashboard/dash_helpers -> dashboard -> project_root
GPKG_PATH = str(PROJECT_ROOT / "assets" / "BestuurlijkeGebieden_2025.gpkg")


def create_gemeente_selection_map_html(selected_gemeenten: List[str]) -> str:
    """
    Create a folium map with selected gemeente boundaries.
    Always returns a basemap, with geometries only if gemeenten are selected.
    """
    try:
        # Default center (Netherlands)
        center_lat, center_lon, zoom = 52.1326, 5.2913, 7

        # Create basemap
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom,
            tiles="CartoDB positron",
        )

        # If gemeenten selected, add geometries
        if selected_gemeenten:
            gdf = gpd.read_file(GPKG_PATH, layer="gemeentegebied")
            gdf = gdf[gdf["naam"].isin(selected_gemeenten)]

            if not gdf.empty:
                gdf = gdf.set_crs("EPSG:28992").to_crs("EPSG:4326")
                bounds = gdf.total_bounds
                center_lat = (bounds[1] + bounds[3]) / 2
                center_lon = (bounds[0] + bounds[2]) / 2

                # Recenter map on selected gemeenten
                m = folium.Map(
                    location=[center_lat, center_lon],
                    zoom_start=10,
                    tiles="CartoDB positron",
                )

                # Add gemeente geometries
                folium.GeoJson(
                    gdf,
                    style_function=lambda x: {
                        "fillColor": "#27ae60",
                        "color": "#229954",
                        "weight": 3,
                        "fillOpacity": 0.35,
                    },
                    tooltip=folium.GeoJsonTooltip(
                        fields=["naam"], aliases=["Gemeente:"]
                    ),
                ).add_to(m)

        return m.get_root().render()

    except Exception:
        # Fallback empty map
        m = folium.Map(
            location=[52.1326, 5.2913], zoom_start=7, tiles="CartoDB positron"
        )
        return m.get_root().render()

