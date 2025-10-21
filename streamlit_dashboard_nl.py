#!/usr/bin/env python3
"""
Streamlit Dashboard voor Airbnb Scraper (Nederlandse versie)
"""

import os
import sys
import logging
import json
from datetime import datetime, date, timedelta
from typing import List
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Define paths
LOGO_PATH = project_root / "assets" / "rigo-logo.svg"
GPKG_PATH_ABS = project_root / "assets" / "BestuurlijkeGebieden_2025.gpkg"
DATA_DIR_ABS = project_root / "outputs" / "data"

import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import folium
from streamlit_folium import st_folium

# Import scraper modules
from src.core.scraper_core import scrape_all, generate_scan_combinations
from src.core.run_tracker import RunTracker
from src.data.data_processor import calculate_availability, prepare_export_data
from src.data.exporter import export_to_excel
from src.visualization.map_creator import create_map
from src.visualization.graph_creator import create_availability_timeline_graph

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Airbnb Scraper Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Add logo to sidebar
st.logo(str(LOGO_PATH), size="large")

# Custom CSS to make logo larger
st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] img {
        width: 300% !important;
        max-width: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Constants (using absolute paths for reliability)
GPKG_PATH = str(GPKG_PATH_ABS)
DATA_DIR = str(DATA_DIR_ABS)
LOGIN_PASSWORD = "Ruijterkade"


# Authentication
def check_login():
    """Check if user is logged in, show login form if not"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        # Custom CSS for login page
        st.markdown(
            """
            <style>
            .stForm {
                background-color: #f5f5f5;
                padding: 30px;
                border-radius: 10px;
                border: 2px solid #10357e;
            }
            .stTextInput input {
                border: 2px solid #10357e;
            }
            .stButton button {
                background-color: #da9a36;
                color: white;
                border: none;
                width: 100%;
                padding: 10px;
                font-weight: bold;
            }
            .stButton button:hover {
                background-color: #c68a2e;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Center the login form
        col1, col2, col3 = st.columns([1, 1, 1])

        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)

            # Logo
            st.image(str(LOGO_PATH), width=200)

            # Login form
            with st.form("login_form"):
                password = st.text_input("Wachtwoord", type="password")
                submit = st.form_submit_button("Inloggen")

                if submit:
                    if password == LOGIN_PASSWORD:
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("Onjuist wachtwoord")

        st.stop()

    return True


# Custom CSS
def load_custom_css():
    st.markdown(
        """
        <style>
        /* RIGO Brand Colors */
        :root {
            --rigo-blue: #10357e;
            --rigo-gold: #da9a36;
        }
        
        .stMetric {
            background-color: #f0f2f6;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #10357e;
        }
        .success-box {
            padding: 20px;
            border-radius: 10px;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            margin: 10px 0;
        }
        .info-box {
            padding: 15px;
            border-radius: 10px;
            background-color: #e8f0ff;
            border: 2px solid #10357e;
            color: #10357e;
            margin: 10px 0;
        }
        h1 {
            color: #10357e;
        }
        h2 {
            color: #10357e;
        }
        h3 {
            color: #484848;
        }
        
        /* Logo styling with blue background */
        [data-testid="stLogo"] {
            background-color: #10357e !important;
            padding: 20px !important;
            border-radius: 10px !important;
            margin-bottom: 20px !important;
        }
        [data-testid="stLogo"] img {
            display: block !important;
            margin: 0 auto !important;
        }
        
        /* Button styling */
        .stButton button {
            border: 1px solid #10357e;
        }
        .stButton button[kind="primary"] {
            background-color: #10357e;
            color: white;
        }
        .stButton button[kind="primary"]:hover {
            background-color: #da9a36;
            border-color: #da9a36;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 4px;
            color: #10357e;
            border: 1px solid #10357e;
        }
        .stTabs [aria-selected="true"] {
            background-color: #10357e;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# Initialize session state
def init_session_state():
    if "selected_run" not in st.session_state:
        st.session_state.selected_run = None
    if "gemeenten_list" not in st.session_state:
        st.session_state.gemeenten_list = load_gemeenten_list()
    if "current_results" not in st.session_state:
        st.session_state.current_results = None


def load_gemeenten_list() -> List[str]:
    """Load available gemeenten from GeoPackage"""
    try:
        if not os.path.exists(GPKG_PATH):
            return []
        gdf = gpd.read_file(GPKG_PATH, layer="gemeentegebied")
        return sorted(gdf["naam"].unique().tolist())
    except Exception as e:
        logger.error(f"Error loading gemeenten: {e}")
        return []


def get_historical_runs() -> List[dict]:
    """Get list of historical runs from data directory"""
    runs: List[dict] = []

    if not os.path.exists(DATA_DIR):
        return runs

    # Get all run directories
    for item in os.listdir(DATA_DIR):
        item_path = os.path.join(DATA_DIR, item)
        if os.path.isdir(item_path) and item.startswith("run_"):
            # Extract metadata from directory name
            parts = item.replace("run_", "").split("_")
            if len(parts) >= 2:
                gemeente = parts[0]
                timestamp = "_".join(parts[1:])

                # Parse timestamp
                try:
                    dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                    timestamp_display = dt.strftime("%d-%m-%Y %H:%M")
                except:
                    timestamp_display = timestamp

                runs.append(
                    {
                        "gemeente": gemeente,
                        "timestamp": timestamp,
                        "timestamp_display": timestamp_display,
                        "path": item_path,
                        "name": item,
                    }
                )

    # Sort by timestamp descending
    runs.sort(key=lambda x: x["timestamp"], reverse=True)
    return runs


def load_run_data(run_path: str):
    """Load data from a historical run"""
    try:
        # Find Excel file
        excel_files = [
            f
            for f in os.listdir(run_path)
            if f.endswith(".xlsx") and not f.startswith("~$")
        ]

        if not excel_files:
            return None

        excel_path = os.path.join(run_path, excel_files[0])

        # Load data - try different sheet names (old and new formats)
        # New format: "All Data", "Availability Summary"
        # Old format: "Alle Data", "Beschikbaarheid"
        try:
            df_all = pd.read_excel(excel_path, sheet_name="All Data")
        except:
            try:
                df_all = pd.read_excel(excel_path, sheet_name="Alle Data")
            except:
                # Try first sheet
                df_all = pd.read_excel(excel_path, sheet_name=0)

        try:
            df_availability = pd.read_excel(
                excel_path, sheet_name="Availability Summary"
            )
        except:
            try:
                df_availability = pd.read_excel(
                    excel_path, sheet_name="Beschikbaarheid"
                )
            except:
                # If availability sheet doesn't exist, calculate it
                # Get period from data
                if (
                    "scan_checkin" in df_all.columns
                    and "scan_checkout" in df_all.columns
                ):
                    period_start = df_all["scan_checkin"].min()
                    period_end = df_all["scan_checkout"].max()
                    df_availability = calculate_availability(
                        df_all, str(period_start)[:10], str(period_end)[:10]
                    )
                else:
                    # Fallback: create minimal availability data
                    df_availability = pd.DataFrame(
                        {
                            "room_id": df_all["room_id"].unique(),
                            "days_available": 1,
                            "total_days": 1,
                            "availability_rate": 100.0,
                        }
                    )

        # Ensure required columns exist
        if "availability_rate" not in df_availability.columns:
            df_availability["availability_rate"] = 100.0
        if "days_available" not in df_availability.columns:
            df_availability["days_available"] = 1
        if "total_days" not in df_availability.columns:
            df_availability["total_days"] = 1

        # Create df_map
        df_map = df_all.drop_duplicates("room_id").merge(
            df_availability[
                ["room_id", "days_available", "availability_rate", "total_days"]
            ],
            on="room_id",
            how="left",
        )

        # Fill missing values (avoid FutureWarning)
        df_map = df_map.fillna(
            {"availability_rate": 100.0, "days_available": 1, "total_days": 1}
        )

        # Load config
        config_path = os.path.join(run_path, "config.json")
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)

        return {
            "df_all": df_all,
            "df_availability": df_availability,
            "df_map": df_map,
            "config": config,
            "path": run_path,
        }
    except Exception as e:
        logger.error(f"Error loading run: {e}")
        logger.exception("Detailed error:")
        return None


def create_gemeente_selection_map(selected_gemeenten=None):
    """Create a map showing only selected gemeente boundaries

    Args:
        selected_gemeenten: List of gemeente names to show. If None or empty, shows placeholder.
    """
    try:
        # Only load selected gemeenten, not all 342+
        if selected_gemeenten:
            # Load only the selected gemeenten from GeoPackage
            gdf = gpd.read_file(GPKG_PATH, layer="gemeentegebied")
            gdf = gdf[gdf["naam"].isin(selected_gemeenten)]

            if gdf.empty:
                logger.warning(f"No gemeenten found for: {selected_gemeenten}")
                # Fallback to Netherlands center
                center_lat, center_lon = 52.1326, 5.2913
                zoom = 7
            else:
                gdf = gdf.set_crs("EPSG:28992").to_crs("EPSG:4326")
                # Calculate center based on selected gemeenten
                bounds = gdf.total_bounds
                center_lat = (bounds[1] + bounds[3]) / 2
                center_lon = (bounds[0] + bounds[2]) / 2
                zoom = 10  # Closer zoom for selected gemeenten
        else:
            # No gemeenten selected - show empty map centered on Netherlands
            gdf = None
            center_lat, center_lon = 52.1326, 5.2913
            zoom = 7

        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom,
            tiles="CartoDB positron",
        )

        # Add gemeente boundaries if we have any
        if gdf is not None and not gdf.empty:
            folium.GeoJson(
                gdf,
                style_function=lambda x: {
                    "fillColor": "#27ae60",  # Green for selected
                    "color": "#229954",
                    "weight": 3,
                    "fillOpacity": 0.4,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=["naam"],
                    aliases=["Gemeente:"],
                    style="background-color: white; color: #333; font-family: Arial; font-size: 14px; padding: 10px; font-weight: bold;",
                ),
            ).add_to(m)

        return m
    except Exception as e:
        logger.error(f"Error creating gemeente map: {e}")
        return None


@st.cache_data(ttl=3600)  # Cache for 1 hour
def create_interactive_timeline(df_all: pd.DataFrame, config: dict):
    """Create interactive Plotly timeline graph"""
    from datetime import date, timedelta
    import plotly.graph_objects as go

    # Get period from config or data
    period_start = config.get("period_start")
    period_end = config.get("period_end")

    if not period_start or not period_end:
        period_start = df_all["scan_checkin"].min()
        period_end = df_all["scan_checkout"].max()

    # Calculate timeline data
    start_date = date.fromisoformat(str(period_start)[:10])
    end_date = date.fromisoformat(str(period_end)[:10])
    all_dates = [
        start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)
    ]

    # Color mapping (same as graph_creator.py)
    COLORS = {
        "Entire home": "#3498db",
        "Private room": "#e67e22",
        "Shared room": "#e91e63",
        "Guesthouse": "#27ae60",
        "Hotel": "#f39c12",
        "Unique stay": "#9b59b6",
        "Unknown": "#95a5a6",
    }

    # OPTIMIZED: Vectorized calculation
    # Convert dates once
    df_calc = df_all[
        ["room_id", "property_type_airbnb", "scan_checkin", "scan_checkout"]
    ].copy()
    df_calc["check_in"] = pd.to_datetime(df_calc["scan_checkin"]).dt.date
    df_calc["check_out"] = pd.to_datetime(df_calc["scan_checkout"]).dt.date

    # Calculate availability per day per type
    availability_timeline = []

    # Group by property type for efficiency
    for prop_type in df_calc["property_type_airbnb"].unique():
        type_data = df_calc[df_calc["property_type_airbnb"] == prop_type]

        for current_date in all_dates:
            # Vectorized check: which listings are available on this date?
            mask = (type_data["check_in"] <= current_date) & (
                current_date < type_data["check_out"]
            )
            available_count = type_data[mask]["room_id"].nunique()

            availability_timeline.append(
                {
                    "datum": current_date,
                    "property_type": prop_type,
                    "available_count": available_count,
                }
            )

    df_timeline = pd.DataFrame(availability_timeline)

    # Create Plotly figure
    fig = go.Figure()

    # Add a line for each property type
    for prop_type in sorted(df_timeline["property_type"].unique()):
        data = df_timeline[df_timeline["property_type"] == prop_type].sort_values(
            "datum"
        )

        fig.add_trace(
            go.Scatter(
                x=data["datum"],
                y=data["available_count"],
                name=prop_type,
                mode="lines+markers",
                line=dict(color=COLORS.get(prop_type, "#95a5a6"), width=3),
                marker=dict(
                    size=8,
                    color=COLORS.get(prop_type, "#95a5a6"),
                ),
                hovertemplate="<b>%{fullData.name}</b><br>"
                + "Datum: %{x|%d %b %Y}<br>"
                + "Beschikbaar: %{y} listings<br>"
                + "<extra></extra>",
            )
        )

    # Update layout
    fig.update_layout(
        title="",
        xaxis_title="Datum",
        yaxis_title="Aantal Beschikbare Listings",
        hovermode="x unified",
        height=500,
        legend=dict(
            title="Accommodatietype",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        plot_bgcolor="white",
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.1)",
            showline=True,
            linecolor="rgba(0,0,0,0.2)",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.1)",
            showline=True,
            linecolor="rgba(0,0,0,0.2)",
        ),
    )

    return fig


def page_resultaten():
    """Main results page with table view"""
    from src.core.run_tracker import get_all_runs

    # Check if restart requested
    if st.session_state.get("restart_run_now"):
        st.session_state.restart_run_now = False
        config = st.session_state.get("restart_run_config")
        if config:
            st.info("🔄 Restarting run met dezelfde configuratie...")

            # Extract config parameters with defaults
            gemeenten = config.get("gemeenten", [])
            period_start = config.get("period_start")
            period_end = config.get("period_end")

            # Ensure nights_list and guests_list are lists (handle old configs that stored as int)
            nights_list = config.get("nights_list", [3, 7])
            if isinstance(nights_list, int):
                nights_list = [nights_list]
            guests_list = config.get("guests_list", [2])
            if isinstance(guests_list, int):
                guests_list = [guests_list]

            measurement_interval = config.get("measurement_interval", 7)
            num_repeat_calls = config.get("num_repeat_calls", 2)
            zoom_value = config.get("zoom_value", 12)
            price_min = config.get("price_min", 0)
            price_max = config.get("price_max", 0)
            currency = config.get("currency", "EUR")
            language = config.get("language", "nl")
            max_workers = config.get("max_workers", 1)
            days_of_week = config.get("days_of_week", None)
            weeks_interval = config.get("weeks_interval", 1)
            monthly_interval = config.get("monthly_interval", False)
            # Older configs might not have these
            delay_between_scans = config.get("delay_between_scans", 1.0)
            delay_between_calls = config.get("delay_between_calls", 0.5)

            # Start new run
            run_scraping_job(
                gemeenten=gemeenten,
                period_start=period_start,
                period_end=period_end,
                nights_list=nights_list,
                guests_list=guests_list,
                measurement_interval=measurement_interval,
                num_repeat_calls=num_repeat_calls,
                zoom_value=zoom_value,
                price_min=price_min,
                price_max=price_max,
                currency=currency,
                language=language,
                max_workers=max_workers,
                days_of_week=days_of_week,
                weeks_interval=weeks_interval,
                monthly_interval=monthly_interval,
                delay_between_scans=delay_between_scans,
                delay_between_calls=delay_between_calls,
            )
            return

    # Check if viewing a specific run detail
    if st.session_state.get("viewing_run_detail"):
        display_run_detail_page(st.session_state.viewing_run_detail)
        return

    # Check if viewing completed run results
    if st.session_state.current_results:
        display_selected_run(st.session_state.current_results, get_historical_runs())
        return

    st.title("📊 Runs Overzicht")

    # Get all runs with status
    runs_with_status = get_all_runs(data_dir=DATA_DIR)

    if not runs_with_status:
        st.info("Geen runs gevonden. Maak een nieuwe run om te beginnen!")
        if st.button("➕ Nieuwe Run Maken", type="primary", width="stretch"):
            st.session_state.page = "➕ Nieuwe Run"
            st.rerun()
        return

    # Filters and search
    col1, col2, col3 = st.columns([2, 3, 1])

    with col1:
        status_filter = st.multiselect(
            "Status",
            ["Voltooid", "Bezig", "Mislukt", "Wachtend", "Geannuleerd"],
            default=["Voltooid", "Bezig"],
            help="Filter op run status",
        )

    with col2:
        search_term = st.text_input(
            "Zoeken",
            placeholder="Gemeente naam...",
        )

    with col3:
        st.write("")
        st.write("")
        if st.button("🔄", width="stretch"):
            st.rerun()

    # Build table data
    table_data = []
    for run in runs_with_status:
        # Get config for gemeente info
        config_path = os.path.join(run["run_path"], "config.json")
        gemeenten_str = "Onbekend"
        period = "-"
        nachten = "-"
        gasten = "-"
        listings_count = "-"

        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                gemeenten = config.get("gemeenten", [])
                gemeenten_str = ", ".join(gemeenten) if gemeenten else "Onbekend"
                period_start = config.get("period_start", "")
                period_end = config.get("period_end", "")
                if period_start and period_end:
                    period = f"{period_start} - {period_end}"
                nachten = str(config.get("nights_list", "-"))
                gasten = str(config.get("guests_list", "-"))
            except:
                pass

        # Try to get listings count
        if run.get("status") in ["completed", "legacy"]:
            try:
                excel_files = [
                    f
                    for f in os.listdir(run["run_path"])
                    if f.endswith(".xlsx") and not f.startswith("~$")
                ]
                if excel_files:
                    excel_path = os.path.join(run["run_path"], excel_files[0])
                    # Try both Dutch and English sheet names
                    try:
                        df = pd.read_excel(
                            excel_path, sheet_name="Alle Data", usecols=["room_id"]
                        )
                    except ValueError:
                        df = pd.read_excel(
                            excel_path, sheet_name="All_Data", usecols=["room_id"]
                        )
                    listings_count = int(df["room_id"].nunique())
            except Exception:
                # Silent fail but keep as dash
                pass
        elif "progress" in run and run["progress"].get("total_listings", 0) > 0:
            listings_count = int(run["progress"]["total_listings"])

        # Get timestamp
        timestamp = run.get("created_at", "")[:16] if run.get("created_at") else "-"

        # Translate status to Dutch
        status_map = {
            "running": "Bezig",
            "completed": "Voltooid",
            "failed": "Mislukt",
            "pending": "Wachtend",
            "cancelled": "Geannuleerd",
            "legacy": "Voltooid",  # Show legacy as completed
            "unknown": "Onbekend",
        }
        status_nl = status_map.get(run.get("status", "unknown"), "Onbekend")

        table_data.append(
            {
                "Timestamp": timestamp,
                "Gemeente(n)": gemeenten_str,
                "Status": status_nl,
                "Periode": period,
                "Listings": listings_count,
                "run_path": run["run_path"],
                "run_name": run["run_name"],
                "status_raw": run.get("status", "unknown"),
            }
        )

    # Apply status filter (convert Dutch to English)
    status_nl_to_en = {
        "Voltooid": ["completed", "legacy"],  # Include legacy as completed
        "Bezig": ["running"],
        "Mislukt": ["failed"],
        "Wachtend": ["pending"],
        "Geannuleerd": ["cancelled"],
    }

    allowed_statuses = []
    for status_nl in status_filter:
        allowed_statuses.extend(status_nl_to_en.get(status_nl, []))

    if allowed_statuses:
        table_data = [r for r in table_data if r["status_raw"] in allowed_statuses]

    # Apply search filter
    if search_term:
        search_lower = search_term.lower()
        table_data = [r for r in table_data if search_lower in r["Gemeente(n)"].lower()]

    if not table_data:
        st.info("Geen runs gevonden met deze filters")
        return

    st.caption(f"{len(table_data)} runs")

    # Check if there are running jobs
    running_count = len([r for r in table_data if r["status_raw"] == "running"])
    if running_count > 0 and "Bezig" in status_filter:
        st.info(
            f"🔵 {running_count} actieve run(s) - Gebruik refresh knop voor updates"
        )
        # Auto-refresh disabled - manual refresh only

    # Table header
    col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 3, 1.5, 3, 1.5, 1, 1])
    with col1:
        st.markdown("**Datum**")
    with col2:
        st.markdown("**Gemeente(n)**")
    with col3:
        st.markdown("**Status**")
    with col4:
        st.markdown("**Periode**")
    with col5:
        st.markdown("**Listings**")
    with col6:
        st.markdown("**Bekijk**")
    with col7:
        st.markdown("**📥**")

    st.markdown("---")

    # Display table rows
    for idx, row in enumerate(table_data):
        col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 3, 1.5, 3, 1.5, 1, 1])

        # Color based on status
        if row["status_raw"] == "completed":
            status_color = "🟢"
        elif row["status_raw"] == "running":
            status_color = "🔵"
        elif row["status_raw"] == "failed":
            status_color = "🔴"
        elif row["status_raw"] == "pending":
            status_color = "🟡"
        else:
            status_color = "⚪"

        with col1:
            st.write(row["Timestamp"])
        with col2:
            st.write(
                row["Gemeente(n)"][:30]
                + ("..." if len(row["Gemeente(n)"]) > 30 else "")
            )
        with col3:
            st.write(f"{status_color} {row['Status']}")
        with col4:
            st.caption(row["Periode"])
        with col5:
            # Show progress for running/pending jobs
            if row["status_raw"] in ["running", "pending"]:
                # Get progress from original run data
                run_data = next(
                    (r for r in runs_with_status if r["run_path"] == row["run_path"]),
                    None,
                )
                if run_data and "progress" in run_data:
                    progress = run_data["progress"]
                    total = progress.get("total_scans", 0)
                    completed = progress.get("completed_scans", 0)
                    listings = progress.get("total_listings", 0)

                    if total > 0:
                        progress_pct = (completed / total) * 100
                        st.progress(progress_pct / 100)
                        st.caption(f"{completed}/{total} ({progress_pct:.0f}%)")
                    elif listings > 0:
                        st.write(str(listings))
                    else:
                        st.caption("-")
                else:
                    st.caption("-")
            else:
                # For completed runs, show listings count or dash
                if row["Listings"] != "-":
                    st.write(f"{row['Listings']:,}")
                else:
                    st.write("-")
        with col6:
            # Click to view logs (always available)
            if st.button("📋", key=f"log_{idx}", help="Bekijk logs"):
                st.session_state.viewing_run_detail = row["run_path"]
                st.rerun()
            # Analysis button for completed runs
            if row["status_raw"] in ["completed", "legacy"]:
                if st.button("📊", key=f"view_{idx}", help="Bekijk analyse"):
                    load_run_results(row["run_path"])
        with col7:
            # Excel download button
            if row["status_raw"] in ["completed", "legacy"]:
                try:
                    excel_files = [
                        f
                        for f in os.listdir(row["run_path"])
                        if f.endswith(".xlsx") and not f.startswith("~$")
                    ]
                    if excel_files:
                        excel_path = os.path.join(row["run_path"], excel_files[0])
                        with open(excel_path, "rb") as f:
                            st.download_button(
                                label="📥",
                                data=f,
                                file_name=excel_files[0],
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"dl_{idx}",
                                help="Downloads Excel",
                            )
                except:
                    pass

        if idx < len(table_data) - 1:
            st.markdown("---")


def display_run_detail_page(run_path):
    """Display detail page for a run (logs for active, or redirect to results for completed)"""
    from src.core.run_tracker import RunTracker, get_all_runs
    import time

    # Get run info
    all_runs = get_all_runs(data_dir=DATA_DIR)
    run_info = next((r for r in all_runs if r["run_path"] == run_path), None)

    if not run_info:
        st.error("Run niet gevonden")
        return

    status = run_info.get("status", "unknown")
    run_name = run_info["run_name"]

    # Load config
    config_path = os.path.join(run_path, "config.json")
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)

    # Parse gemeente and timestamp from run_name
    gemeente = (
        config.get("gemeenten", ["Onbekend"])[0]
        if config.get("gemeenten")
        else "Onbekend"
    )

    # Try to extract date from run_name (format: gemeente_YYYYMMDD_HHMMSS)
    run_date_str = ""
    try:
        parts = run_name.split("_")
        if len(parts) >= 2:
            timestamp = "_".join(parts[1:])
            dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
            run_date_str = dt.strftime("%d-%m-%Y %H:%M")
    except (ValueError, IndexError):
        run_date_str = ""

    # Status icons
    status_map = {
        "running": "🔵",
        "completed": "✅",
        "failed": "❌",
        "pending": "⏳",
    }
    status_text = {
        "running": "Bezig",
        "completed": "Voltooid",
        "failed": "Mislukt",
        "pending": "Wachtend",
    }

    # Title with gemeente prominently and run info below
    col_title, col_back = st.columns([4, 1])
    with col_title:
        st.title(f"{status_map.get(status, '❓')} {gemeente}")
        st.caption(f"Status: {status_text.get(status, 'Onbekend')}")
        st.caption(f"📁 {run_name}")
        if run_date_str:
            st.caption(f"📅 {run_date_str}")

    with col_back:
        st.markdown("")  # Add spacing
        st.markdown("")  # Add spacing
        if st.button("← Terug", width="stretch"):
            st.session_state.viewing_run_detail = None
            st.rerun()

    # Action buttons
    col_action1, col_action2, col_action3 = st.columns([1, 1, 4])

    with col_action1:
        if st.button(
            "🔄 Restart Run",
            width="stretch",
            help="Start nieuwe run met dezelfde configuratie",
        ):
            if config:
                # Cancel current run if it's running
                if status in ["running", "pending"]:
                    tracker = RunTracker(run_path)
                    tracker.cancel()
                    tracker.log("⚠️ Run geannuleerd voor restart")

                # Start new run with same config
                st.session_state.restart_run_config = config
                st.session_state.restart_run_now = True
                st.rerun()

    with col_action2:
        if st.button(
            "🗑️ Verwijder",
            width="stretch",
            type="secondary",
            help="Verwijder deze run",
        ):
            # Show confirmation dialog
            st.session_state.confirm_delete_run = run_path

    # Show delete confirmation dialog if requested
    if st.session_state.get("confirm_delete_run") == run_path:
        st.warning(f"⚠️ Weet je zeker dat je run **{run_name}** wilt verwijderen?")
        col_confirm1, col_confirm2, col_confirm3 = st.columns([1, 1, 4])

        with col_confirm1:
            if st.button("✅ Ja, verwijder", width="stretch", type="primary"):
                import shutil

                try:
                    shutil.rmtree(run_path)
                    st.success(f"Run {run_name} verwijderd")
                    st.session_state.confirm_delete_run = None
                    st.session_state.viewing_run_detail = None
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Fout bij verwijderen: {e}")

        with col_confirm2:
            if st.button("❌ Annuleer", width="stretch"):
                st.session_state.confirm_delete_run = None
                st.rerun()

    st.markdown("---")

    # Configuration in expander (collapsed by default)
    with st.expander("⚙️ Run Configuratie"):
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            st.markdown("**📍 Gemeenten**")
            gemeenten = config.get("gemeenten", [])
            if gemeenten:
                for g in gemeenten:
                    st.caption(f"  • {g}")
            else:
                st.caption("Onbekend")

            st.markdown("**📅 Periode**")
            st.caption(f"Start: {config.get('period_start', '-')}")
            st.caption(f"Eind: {config.get('period_end', '-')}")

            st.markdown("**🛏️ Nachten**")
            st.caption(f"{config.get('nights_list', [])}")

            st.markdown("**👥 Gasten**")
            st.caption(f"{config.get('guests_list', [])}")

        with col_c2:
            st.markdown("**💰 Prijs**")
            price_min = config.get("price_min", 0)
            price_max = config.get("price_max", 0)
            if price_min > 0 or price_max > 0:
                st.caption(f"€{price_min} - €{price_max}")
            else:
                st.caption("Geen limiet")

            st.markdown("**🔧 API Instellingen**")
            st.caption(f"Herhalingen: {config.get('num_repeat_calls', 2)}")
            st.caption(f"Zoom: {config.get('zoom_value', 12)}")
            st.caption(f"Workers: {config.get('max_workers', 1)}")

        # Show planned scan moments
        st.markdown("---")
        st.markdown("**📅 Geplande Scan Momenten**")

        try:
            from src.core.scraper_core import generate_scan_combinations

            # Generate scan combinations based on config
            period_start = config.get("period_start")
            period_end = config.get("period_end")
            nights_list = config.get("nights_list", [3, 7])
            guests_list = config.get("guests_list", [2])
            measurement_interval = config.get("measurement_interval", 7)
            days_of_week = config.get("days_of_week")
            weeks_interval = config.get("weeks_interval", 1)
            monthly_interval = config.get("monthly_interval", False)

            # Safety check: ensure nights_list and guests_list are lists
            if isinstance(nights_list, int):
                nights_list = [nights_list]
            if isinstance(guests_list, int):
                guests_list = [guests_list]

            if period_start and period_end:
                scan_combinations, _ = generate_scan_combinations(
                    period_start=period_start,
                    period_end=period_end,
                    nights_list=nights_list,
                    guests_list=guests_list,
                    measurement_interval=measurement_interval,
                    days_of_week=days_of_week,
                    weeks_interval=weeks_interval,
                    monthly_interval=monthly_interval,
                )

                # Extract unique check-in dates
                measurement_dates = sorted(
                    list(
                        set(
                            [
                                datetime.fromisoformat(combo[0]).date()
                                for combo in scan_combinations
                            ]
                        )
                    )
                )

                if measurement_dates:
                    st.info(f"**{len(measurement_dates)} metingen** gepland")

                    # Group by month
                    from collections import defaultdict

                    months = defaultdict(list)
                    for d in measurement_dates:
                        month_key = d.strftime("%B %Y")
                        months[month_key].append(d)

                    # Display each month
                    for month_name, dates in months.items():
                        st.markdown(f"**{month_name}**")

                        # Create calendar grid
                        dates_str = ""
                        for i, d in enumerate(dates):
                            day_str = d.strftime("%d")
                            weekday = d.strftime("%a")
                            dates_str += f"<div style='display: inline-block; margin: 4px; padding: 8px 12px; background: #27ae60; color: white; border-radius: 6px; text-align: center; min-width: 60px;'><div style='font-size: 10px; opacity: 0.8;'>{weekday}</div><div style='font-size: 16px; font-weight: bold;'>{day_str}</div></div>"

                            # Add line break after every 3 dates
                            if (i + 1) % 3 == 0:
                                dates_str += "<br>"

                        st.markdown(dates_str, unsafe_allow_html=True)
                        st.markdown("")
            else:
                st.caption("Nog geen scan momenten gepland")
        except Exception as e:
            import traceback

            st.caption("Scan momenten niet beschikbaar")
            with st.expander("Debug Info"):
                st.code(f"Error: {str(e)}\n\n{traceback.format_exc()}")

    st.markdown("---")

    # Show live info for active runs
    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("📊 Status")

        st.markdown("---")

        # Progress
        if "progress" in run_info:
            progress = run_info["progress"]
            total = progress.get("total_scans", 0)
            completed = progress.get("completed_scans", 0)
            failed = progress.get("failed_scans", 0)
            listings = progress.get("total_listings", 0)

            st.markdown("**Voortgang:**")
            if total > 0:
                progress_pct = (completed / total) * 100
                st.progress(progress_pct / 100)
                st.caption(f"{completed}/{total} scans ({progress_pct:.0f}%)")

            col_m1, col_m2 = st.columns(2)
            if completed > 0:
                col_m1.metric("Scans", f"{completed:,}")
            if listings > 0:
                col_m2.metric("Listings", f"{listings:,}")
            if failed > 0:
                st.metric("Failed", f"{failed:,}", delta_color="inverse")

        # Timestamps
        st.markdown("---")
        st.markdown("**Tijden:**")
        if "created_at" in run_info:
            st.caption(f"🕐 {run_info['created_at'][:19]}")
        if "started_at" in run_info and run_info["started_at"]:
            st.caption(f"▶️ {run_info['started_at'][:19]}")

    with col2:
        st.subheader("📋 Logs")

        # Auto-refresh toggle for running jobs
        auto_refresh = False
        if status == "running":
            auto_refresh = st.checkbox("🔄 Auto-refresh (elke 3s)", value=False)

        # Show logs
        tracker = RunTracker(run_path)
        logs = tracker.get_logs(tail=100)

        if logs:
            st.code(logs, language=None, line_numbers=False)

            col_dl, col_analyze = st.columns(2)
            with col_dl:
                # Download button
                full_logs = tracker.get_logs()
                st.download_button(
                    label="⬇️ Download Logs",
                    data=full_logs,
                    file_name=f"{run_name}.log",
                    mime="text/plain",
                    width="stretch",
                )
            with col_analyze:
                # For completed runs, add button to view full analysis
                if status in ["completed", "legacy"]:
                    if st.button("📊 Bekijk Analyse", width="stretch"):
                        load_run_results(run_path)
                        st.session_state.viewing_run_detail = None
                        st.rerun()
        else:
            st.info("Nog geen logs beschikbaar...")

    # Auto-refresh for running jobs (only if explicitly enabled)
    if status == "running" and auto_refresh:
        time.sleep(3)
        st.rerun()


def load_run_results(run_path):
    """Load a run's results into session state"""
    try:
        excel_files = [
            f
            for f in os.listdir(run_path)
            if f.endswith(".xlsx") and not f.startswith("~$")
        ]
        if not excel_files:
            st.error("Geen data bestanden gevonden")
            return

        excel_path = os.path.join(run_path, excel_files[0])

        # Load config first
        config_path = os.path.join(run_path, "config.json")
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)

        # Try to read Excel file - handle both English and Dutch sheet names
        try:
            xl = pd.ExcelFile(excel_path)
            sheet_names = xl.sheet_names

            # Try to find data sheet (support both English and Dutch)
            data_sheet = None
            if "All_Data" in sheet_names:
                data_sheet = "All_Data"
            elif "Alle Data" in sheet_names:
                data_sheet = "Alle Data"
            else:
                data_sheet = 0  # First sheet

            df_all = pd.read_excel(excel_path, sheet_name=data_sheet)
        except Exception as e:
            st.error(f"Kan data niet laden uit Excel bestand: {e}")
            return

        # Try to read availability sheet (support both English and Dutch)
        try:
            xl = pd.ExcelFile(excel_path)
            sheet_names = xl.sheet_names

            avail_sheet = None
            if "Availability" in sheet_names:
                avail_sheet = "Availability"
            elif "Beschikbaarheid" in sheet_names:
                avail_sheet = "Beschikbaarheid"

            if avail_sheet:
                df_availability = pd.read_excel(excel_path, sheet_name=avail_sheet)
            else:
                raise ValueError("No availability sheet found")
        except (ValueError, Exception):
            # Calculate availability if sheet doesn't exist
            period_start = config.get("period_start")
            period_end = config.get("period_end")

            try:
                df_availability = calculate_availability(
                    df_all, period_start, period_end
                )
            except:
                df_availability = pd.DataFrame()

        # Create df_map with availability data merged
        df_map = df_all.drop_duplicates("room_id")

        # Merge availability data if it exists
        if not df_availability.empty and "room_id" in df_availability.columns:
            df_map = df_map.merge(
                df_availability[
                    ["room_id", "days_available", "availability_rate", "total_days"]
                ],
                on="room_id",
                how="left",
            )

        st.session_state.current_results = {
            "df_all": df_all,
            "df_availability": df_availability,
            "df_map": df_map,
            "config": config,
            "path": run_path,
        }
        st.rerun()
    except Exception as e:
        st.error(f"Error bij laden data: {e}")
        import traceback

        st.code(traceback.format_exc())


def display_run_card(run):
    """Display a single run card with status, logs, and results"""
    from src.core.run_tracker import RunTracker

    status = run.get("status", "unknown")
    run_name = run["run_name"]
    run_path = run["run_path"]

    # Status icon
    if status == "running":
        icon = "🔄"
    elif status == "completed":
        icon = "✅"
    elif status == "failed":
        icon = "❌"
    elif status == "pending":
        icon = "⏳"
    elif status == "legacy":
        icon = "📦"
    else:
        icon = "❓"

    # Run card
    with st.expander(
        f"{icon} {run_name} - {status.upper()}", expanded=(status == "running")
    ):
        # Two column layout
        col_left, col_right = st.columns([3, 2])

        with col_left:
            # Config info
            config_path = os.path.join(run_path, "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)

                st.markdown("**📋 Configuratie**")
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    gemeenten = config.get("gemeenten", [])
                    st.caption(
                        f"📍 {', '.join(gemeenten[:3])}"
                        + ("..." if len(gemeenten) > 3 else "")
                    )
                    st.caption(
                        f"📅 {config.get('period_start')} → {config.get('period_end')}"
                    )
                with col_c2:
                    st.caption(f"🛏️ Nachten: {config.get('nights_list', [])}")
                    st.caption(f"👥 Gasten: {config.get('guests_list', [])}")

            st.markdown("---")

            # Results if completed
            if status == "completed" or status == "legacy":
                st.markdown("**📊 Resultaten**")

                # Try to load data
                try:
                    excel_files = [
                        f
                        for f in os.listdir(run_path)
                        if f.endswith(".xlsx") and not f.startswith("~$")
                    ]
                    if excel_files:
                        excel_path = os.path.join(run_path, excel_files[0])
                        df = pd.read_excel(excel_path, sheet_name="All_Data")

                        col_r1, col_r2, col_r3 = st.columns(3)
                        col_r1.metric("Listings", f"{df['room_id'].nunique():,}")
                        col_r2.metric("Records", f"{len(df):,}")
                        col_r3.metric("Prijs", f"€{df['price'].mean():.0f}")

                        # View button
                        if st.button("📊 Bekijk Data", key=f"view_{run_name}"):
                            # Load full results
                            try:
                                df_availability = pd.read_excel(
                                    excel_path, sheet_name="Availability"
                                )
                                df_map = df.drop_duplicates("room_id")

                                st.session_state.current_results = {
                                    "df_all": df,
                                    "df_availability": df_availability,
                                    "df_map": df_map,
                                    "config": config,
                                    "path": run_path,
                                }
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error loading data: {e}")

                    # Show map thumbnail if exists
                    map_path = os.path.join(run_path, "map_availability.html")
                    if os.path.exists(map_path):
                        st.caption("🗺️ Kaart beschikbaar")

                except Exception:
                    st.caption("Geen data beschikbaar")

        with col_right:
            st.markdown("**📡 Status**")

            # Timestamps
            if "created_at" in run:
                st.caption(f"🕐 Created: {run['created_at'][:16]}")
            if "started_at" in run and run["started_at"]:
                st.caption(f"▶️ Started: {run['started_at'][:16]}")
            if "completed_at" in run and run["completed_at"]:
                st.caption(f"✓ Completed: {run['completed_at'][:16]}")

            # Progress for running/pending
            if status in ["running", "pending"] and "progress" in run:
                progress = run["progress"]
                total = progress.get("total_scans", 0)
                completed = progress.get("completed_scans", 0)
                listings = progress.get("total_listings", 0)

                if total > 0:
                    progress_pct = (completed / total) * 100
                    st.progress(progress_pct / 100)
                    st.caption(f"{completed}/{total} scans ({progress_pct:.0f}%)")

                if listings > 0:
                    st.metric("Listings", f"{listings:,}")

            # Error message
            if "error" in run and run["error"]:
                st.error(f"Error: {run['error']}")

            st.markdown("---")

            # Logs
            st.markdown("**📋 Logs**")
            tracker = RunTracker(run_path)
            logs = tracker.get_logs(tail=20)

            if logs:
                st.code(logs, language=None, line_numbers=False)

                # Download button
                full_logs = tracker.get_logs()
                st.download_button(
                    label="⬇️ Download",
                    data=full_logs,
                    file_name=f"{run_name}.log",
                    mime="text/plain",
                    key=f"download_{run_name}",
                )
            else:
                st.caption("Geen logs beschikbaar")


def display_run_selection(runs):
    """Display run selection view with search and filters"""

    # Search and filters
    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        search_term = st.text_input(
            "🔍 Zoeken",
            placeholder="Zoek op gemeente of datum...",
            label_visibility="collapsed",
        )

    with col2:
        all_gemeenten = sorted(set(run["gemeente"] for run in runs))
        filter_gemeente = st.selectbox(
            "Gemeente",
            ["Alle gemeenten"] + all_gemeenten,
            key="filter_gemeente",
            label_visibility="collapsed",
        )

    with col3:
        if st.button("➕ Nieuwe Run", width="stretch"):
            st.session_state.page = "➕ Nieuwe Run"
            st.rerun()

    st.markdown("---")

    # Filter runs
    filtered_runs = runs

    # Apply gemeente filter
    if filter_gemeente != "Alle gemeenten":
        filtered_runs = [r for r in filtered_runs if r["gemeente"] == filter_gemeente]

    # Apply search filter
    if search_term:
        search_lower = search_term.lower()
        filtered_runs = [
            r
            for r in filtered_runs
            if search_lower in r["gemeente"].lower()
            or search_lower in r["timestamp_display"].lower()
        ]

    st.caption(f"{len(filtered_runs)} van {len(runs)} runs")
    st.markdown("")

    # Display runs in compact cards
    for i, run in enumerate(filtered_runs):
        col_info, col_stats, col_actions = st.columns([4, 2, 2])

        with col_info:
            st.markdown(f"**{run['gemeente']}** · {run['timestamp_display']}")

            # Load and show config info
            config_path = os.path.join(run["path"], "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)

                # Compact config display
                period_start = config.get("period_start", "")
                period_end = config.get("period_end", "")
                interval = config.get("measurement_interval", "N/A")
                st.caption(f"{period_start} → {period_end} • {interval}d interval")

        with col_stats:
            # Try to load quick stats - count unique listings
            try:
                excel_files = [
                    f
                    for f in os.listdir(run["path"])
                    if f.endswith(".xlsx") and not f.startswith("~$")
                ]
                if excel_files:
                    excel_path = os.path.join(run["path"], excel_files[0])
                    # Read room_id column to count unique listings
                    try:
                        df_rooms = pd.read_excel(
                            excel_path, sheet_name=0, usecols=["room_id"]
                        )
                        listings_count = df_rooms["room_id"].nunique()
                        st.caption(f"{listings_count:,} accommodaties")
                    except:
                        # Fallback: just count rows if room_id column doesn't exist
                        df_count = pd.read_excel(excel_path, sheet_name=0, usecols=[0])
                        listings_count = len(df_count)
                        st.caption(f"{listings_count:,} records")
            except:
                st.caption("")

        with col_actions:
            btn_col1, btn_col2 = st.columns(2)

            with btn_col1:
                if st.button(
                    "Bekijk",
                    key=f"load_{i}",
                    width="stretch",
                    type="primary",
                ):
                    with st.spinner("Laden..."):
                        data = load_run_data(run["path"])
                        if data:
                            st.session_state.current_results = data
                            st.rerun()
                        else:
                            st.error("Fout bij laden")

            with btn_col2:
                # Download button
                excel_files = [
                    f
                    for f in os.listdir(run["path"])
                    if f.endswith(".xlsx") and not f.startswith("~$")
                ]
                if excel_files:
                    excel_path = os.path.join(run["path"], excel_files[0])
                    with open(excel_path, "rb") as f:
                        st.download_button(
                            label="Excel",
                            data=f,
                            file_name=excel_files[0],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            width="stretch",
                            key=f"download_{i}",
                        )

        st.divider()


def display_selected_run(results, runs):
    """Display selected run with gemeente as title"""
    df_all = results["df_all"]
    df_availability = results["df_availability"]
    df_map = results["df_map"]
    config = results.get("config", {})
    output_dir = results["path"]

    # Extract run info from path
    run_name = os.path.basename(output_dir)

    # Parse gemeente and timestamp from run_name
    gemeente = (
        config.get("gemeenten", ["Onbekend"])[0]
        if config.get("gemeenten")
        else "Onbekend"
    )

    # Try to extract date from run_name (format: gemeente_YYYYMMDD_HHMMSS)
    run_date_str = ""
    try:
        parts = run_name.split("_")
        if len(parts) >= 2:
            timestamp = "_".join(parts[1:])
            dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
            run_date_str = dt.strftime("%d-%m-%Y %H:%M")
    except (ValueError, IndexError):
        run_date_str = ""

    # Title with gemeente prominently and run info below
    col_title, col_back = st.columns([4, 1])
    with col_title:
        st.title(f"🏙️ {gemeente}")
        st.caption(f"📁 {run_name}")
        if run_date_str:
            st.caption(f"📅 {run_date_str}")

    with col_back:
        st.markdown("")
        st.markdown("")
        if st.button("← Terug", width="stretch"):
            st.session_state.current_results = None
            st.rerun()

    # Configuration in expander (collapsed by default)
    with st.expander("⚙️ Run Configuratie"):
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            st.markdown("**📍 Gemeenten**")
            gemeenten = config.get("gemeenten", [])
            if gemeenten:
                for g in gemeenten:
                    st.caption(f"  • {g}")
            else:
                st.caption("Onbekend")

            st.markdown("**📅 Periode**")
            st.caption(f"Start: {config.get('period_start', '-')}")
            st.caption(f"Eind: {config.get('period_end', '-')}")

            st.markdown("**🛏️ Nachten**")
            st.caption(f"{config.get('nights_list', [])}")

            st.markdown("**👥 Gasten**")
            st.caption(f"{config.get('guests_list', [])}")

        with col_c2:
            st.markdown("**💰 Prijs**")
            price_min = config.get("price_min", 0)
            price_max = config.get("price_max", 0)
            if price_min > 0 or price_max > 0:
                st.caption(f"€{price_min} - €{price_max}")
            else:
                st.caption("Geen limiet")

            st.markdown("**🔧 API Instellingen**")
            st.caption(f"Herhalingen: {config.get('num_repeat_calls', 2)}")
            st.caption(f"Zoom: {config.get('zoom_value', 12)}")
            st.caption(f"Workers: {config.get('max_workers', 1)}")

        # Show scan moments like in new run page
        st.markdown("---")
        st.markdown("**📅 Scan Momenten**")

        # Get unique scan dates from data
        try:
            scan_dates = sorted(pd.to_datetime(df_all["scan_checkin"]).dt.date.unique())
            if scan_dates:
                st.info(f"**{len(scan_dates)} metingen** uitgevoerd")

                # Group by month
                from collections import defaultdict

                months = defaultdict(list)
                for d in scan_dates:
                    month_key = d.strftime("%B %Y")
                    months[month_key].append(d)

                # Display each month
                for month_name, dates in months.items():
                    st.markdown(f"**{month_name}**")

                    # Create calendar grid
                    dates_str = ""
                    for i, d in enumerate(dates):
                        day_str = d.strftime("%d")
                        weekday = d.strftime("%a")
                        dates_str += f"<div style='display: inline-block; margin: 4px; padding: 8px 12px; background: #27ae60; color: white; border-radius: 6px; text-align: center; min-width: 60px;'><div style='font-size: 10px; opacity: 0.8;'>{weekday}</div><div style='font-size: 16px; font-weight: bold;'>{day_str}</div></div>"

                        # Add line break after every 3 dates
                        if (i + 1) % 3 == 0:
                            dates_str += "<br>"

                    st.markdown(dates_str, unsafe_allow_html=True)
                    st.markdown("")
        except Exception:
            st.caption("Scan momenten niet beschikbaar")

    st.markdown("---")

    # Map and metrics side by side
    col_map, col_metrics = st.columns([3, 1])

    # Get available dates for timeline
    all_dates = sorted(pd.to_datetime(df_all["scan_checkin"]).dt.date.unique())

    # Determine filtered data based on selection
    filtered_df_all = df_all
    filtered_df_availability = df_availability
    filtered_df_map = df_map
    map_display_mode = "total"
    selected_date = None
    date_range = None

    with col_metrics:
        # Downloads dropdown at top
        with st.expander("📥 Downloads", expanded=False):
            excel_files = [
                f
                for f in os.listdir(output_dir)
                if f.endswith(".xlsx") and not f.startswith("~$")
            ]
            if excel_files:
                excel_path = os.path.join(output_dir, excel_files[0])
                with open(excel_path, "rb") as f:
                    st.download_button(
                        "📊 Excel",
                        data=f.read(),
                        file_name=excel_files[0],
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width="stretch",
                    )

            csv_data = df_all.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📄 CSV (Alle Data)",
                data=csv_data,
                file_name=f"{gemeente}_data.csv",
                mime="text/csv",
                width="stretch",
            )

            map_file = os.path.join(output_dir, "map.html")
            if os.path.exists(map_file):
                with open(map_file, "r", encoding="utf-8") as f:
                    st.download_button(
                        "🗺️ Map (HTML)",
                        data=f.read(),
                        file_name=f"{gemeente}_map.html",
                        mime="text/html",
                        width="stretch",
                    )

        # Metrics vertically stacked (will be updated based on selection)
        metric_records = st.empty()
        metric_listings = st.empty()
        metric_price = st.empty()
        metric_avail = st.empty()

        # Initial metrics
        metric_records.metric("Records", f"{len(filtered_df_all):,}")
        metric_listings.metric("Listings", f"{filtered_df_all['room_id'].nunique():,}")
        metric_price.metric("Gem. Prijs", f"€{filtered_df_all['price'].mean():.2f}")

        # Availability metric - check if column exists
        if (
            not filtered_df_availability.empty
            and "availability_rate" in filtered_df_availability.columns
        ):
            metric_avail.metric(
                "Beschikbaarheid",
                f"{filtered_df_availability['availability_rate'].mean():.1f}%",
            )
        else:
            metric_avail.metric("Beschikbaarheid", "N/A")

    with col_map:
        # Timeline-based date selector BEFORE map

        # Initialize variables
        map_display_mode = "total"
        filtered_df_map = df_map
        is_full_range = True
        date_range = None
        selected_date = None

        if len(all_dates) > 1:
            # Always show timeline slider
            # Range selection
            date_range = st.select_slider(
                "📅 Selecteer datumbereik op tijdlijn",
                options=all_dates,
                value=(all_dates[0], all_dates[-1]),
                key="range_slider",
            )

            # Check if default range (all dates)
            is_full_range = (
                date_range[0] == all_dates[0] and date_range[1] == all_dates[-1]
            )

            if is_full_range:
                # Use original map data for full range
                map_display_mode = "total"
                filtered_df_map = df_map
            else:
                # Filter data for range
                start_date, end_date = date_range
                filtered_df_all = df_all[
                    (pd.to_datetime(df_all["scan_checkin"]).dt.date >= start_date)
                    & (pd.to_datetime(df_all["scan_checkin"]).dt.date <= end_date)
                ]

                if not filtered_df_all.empty:
                    map_display_mode = "range"
                    filtered_df_availability = calculate_availability(
                        filtered_df_all,
                        start_date.isoformat(),
                        end_date.isoformat(),
                    )
                    filtered_df_map = filtered_df_all.drop_duplicates("room_id").merge(
                        filtered_df_availability[
                            [
                                "room_id",
                                "days_available",
                                "availability_rate",
                                "total_days",
                            ]
                        ],
                        on="room_id",
                        how="left",
                    )

                    # Update metrics
                    metric_records.metric("Records", f"{len(filtered_df_all):,}")
                    metric_listings.metric(
                        "Listings", f"{filtered_df_all['room_id'].nunique():,}"
                    )
                    metric_price.metric(
                        "Gem. Prijs", f"€{filtered_df_all['price'].mean():.2f}"
                    )
                    metric_avail.metric(
                        "Beschikbaarheid",
                        f"{filtered_df_availability['availability_rate'].mean():.1f}%",
                    )

        else:
            st.caption("Onvoldoende meetmomenten voor selectie")
            map_display_mode = "total"
            filtered_df_map = df_map

        # Display info message
        if map_display_mode == "point" and selected_date:
            st.caption(f"📍 Listings beschikbaar op {selected_date}")
        elif map_display_mode == "range" and date_range and not is_full_range:
            st.caption(f"📅 Listings van {date_range[0]} tot {date_range[1]}")

        # Single dynamic map - generate when needed
        try:
            gdf_gemeenten = (
                gpd.read_file(GPKG_PATH, layer="gemeentegebied")
                .set_crs("EPSG:28992")
                .to_crs("EPSG:4326")
            )
            gemeenten = config.get(
                "gemeenten", filtered_df_map["gemeente"].unique().tolist()
            )

            # Create the map
            map_obj = create_map(
                filtered_df_map,
                gdf_gemeenten,
                gemeenten,
                output_dir=None,
            )

            # Display with stable key - disable returned objects to prevent rerun on interaction
            st_folium(
                map_obj, width=None, height=600, key="result_map", returned_objects=[]
            )

        except Exception as e:
            st.error(f"Fout bij maken kaart: {str(e)}")
            logger.error(f"Map creation error: {e}")

    st.markdown("---")

    # Timeline graph - Dynamic Plotly version
    st.subheader("Beschikbaarheid over Tijd")

    try:
        # Create interactive timeline
        fig_timeline = create_interactive_timeline(df_all, config)
        st.plotly_chart(fig_timeline, use_container_width=True)
    except Exception as e:
        logger.error(f"Error creating timeline: {e}")
        # Fallback to static image if available
        timeline_img_path = os.path.join(output_dir, "timeline_availability.png")
        if os.path.exists(timeline_img_path):
            st.image(timeline_img_path, width="stretch")
        else:
            st.info("Tijdlijn grafiek niet beschikbaar")

    # Additional data in expander
    with st.expander("📊 Meer Details"):
        tab1, tab2 = st.tabs(["Data Tabel", "Analyses"])

        with tab1:
            display_data_table(df_all, df_map)

        with tab2:
            display_analytics(df_all, df_availability, config, output_dir)


def display_results_map_only(results):
    """Display results with map as main focus"""
    df_all = results["df_all"]
    df_availability = results["df_availability"]
    df_map = results["df_map"]
    config = results.get("config", {})
    output_dir = results["path"]

    # Summary metrics - compact
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Records", f"{len(df_all):,}")
    with col2:
        st.metric("Listings", f"{df_all['room_id'].nunique():,}")
    with col3:
        st.metric("Gem. Prijs", f"€{df_all['price'].mean():.2f}")
    with col4:
        st.metric(
            "Beschikbaarheid", f"{df_availability['availability_rate'].mean():.1f}%"
        )

    st.markdown("---")

    # Map viewing controls
    col_mode, col_filter = st.columns([2, 2])

    with col_mode:
        map_mode = st.radio(
            "🗺️ Weergave",
            ["Totaal", "Per Datum", "Bereik"],
            horizontal=True,
        )

    with col_filter:
        if map_mode == "Per Datum":
            all_dates = sorted(pd.to_datetime(df_all["scan_checkin"]).dt.date.unique())
            if all_dates:
                selected_date = st.selectbox("Datum", all_dates)
            else:
                st.warning("Geen datums")
                selected_date = None
        elif map_mode == "Bereik":
            all_dates = sorted(pd.to_datetime(df_all["scan_checkin"]).dt.date.unique())
            if all_dates and len(all_dates) > 1:
                date_range = st.slider(
                    "Bereik",
                    min_value=min(all_dates),
                    max_value=max(all_dates),
                    value=(min(all_dates), max(all_dates)),
                )
            else:
                st.warning("Onvoldoende datums")
                date_range = None

    # Display map
    if map_mode == "Per Datum" and "selected_date" in locals() and selected_date:
        display_point_in_time_map(df_all, selected_date, config)
    elif map_mode == "Bereik" and "date_range" in locals() and date_range:
        display_date_range_map(df_all, date_range, config)
    else:
        display_total_availability_map(df_map, output_dir, config)

    # Additional info in expander
    with st.expander("📈 Data & Analyses"):
        tab1, tab2, tab3 = st.tabs(["📊 Data Tabel", "📈 Analyses", "💾 Export"])

        with tab1:
            display_data_table(df_all, df_map)

        with tab2:
            display_analytics(df_all, df_availability, config, output_dir)

        with tab3:
            display_export_options(output_dir)


def display_results(results):
    """Display results for a loaded run (legacy - with tabs)"""
    df_all = results["df_all"]
    df_availability = results["df_availability"]
    df_map = results["df_map"]
    config = results.get("config", {})
    output_dir = results["path"]

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Totaal Records", f"{len(df_all):,}")
    with col2:
        st.metric("Unieke Listings", f"{df_all['room_id'].nunique():,}")
    with col3:
        st.metric("Gem. Prijs", f"€{df_all['price'].mean():.2f}")
    with col4:
        st.metric(
            "Gem. Beschikbaarheid",
            f"{df_availability['availability_rate'].mean():.1f}%",
        )

    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Kaart", "📊 Data", "📈 Analyses", "💾 Export"])

    with tab1:
        display_map_view(df_all, df_map, config, output_dir)

    with tab2:
        display_data_table(df_all, df_map)

    with tab3:
        display_analytics(df_all, df_availability, config, output_dir)

    with tab4:
        display_export_options(output_dir)


def display_map_view(df_all, df_map, config, output_dir):
    """Display map with viewing options"""
    st.subheader("Interactieve Kaart")

    # Viewing mode selector
    col1, col2 = st.columns([2, 3])

    with col1:
        map_mode = st.radio(
            "Weergave Modus",
            ["Totale Beschikbaarheid", "Op Datum", "Datumbereik"],
            help="Kies hoe je beschikbaarheid wilt bekijken",
        )

    with col2:
        if map_mode == "Op Datum":
            all_dates = sorted(pd.to_datetime(df_all["scan_checkin"]).dt.date.unique())
            if all_dates:
                selected_date = st.selectbox("Selecteer Datum", all_dates)
            else:
                st.warning("Geen datums beschikbaar")
                return

        elif map_mode == "Datumbereik":
            all_dates = sorted(pd.to_datetime(df_all["scan_checkin"]).dt.date.unique())
            if all_dates:
                date_range = st.slider(
                    "Selecteer Bereik",
                    min_value=min(all_dates),
                    max_value=max(all_dates),
                    value=(min(all_dates), max(all_dates)),
                )
            else:
                st.warning("Geen datums beschikbaar")
                return

    # Display map based on mode
    if map_mode == "Op Datum":
        display_point_in_time_map(df_all, selected_date, config)
    elif map_mode == "Datumbereik":
        display_date_range_map(df_all, date_range, config)
    else:
        display_total_availability_map(df_map, output_dir, config)


def display_point_in_time_map(df_all, selected_date, config):
    """Display map for a specific date"""
    st.markdown(f"Listings beschikbaar op: **{selected_date}**")

    df_filtered = df_all[
        pd.to_datetime(df_all["scan_checkin"]).dt.date == selected_date
    ].copy()

    if df_filtered.empty:
        st.warning("Geen listings gevonden voor deze datum")
        return

    df_map_filtered = df_filtered.drop_duplicates("room_id").copy()
    df_map_filtered["availability_rate"] = 100.0
    df_map_filtered["days_available"] = df_filtered.groupby("room_id")[
        "scan_nights"
    ].first()
    df_map_filtered["total_days"] = 1

    # Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Beschikbare Listings", len(df_map_filtered))
    with col2:
        st.metric("Gem. Prijs", f"€{df_map_filtered['price'].mean():.2f}")
    with col3:
        st.metric(
            "Accommodatietypes", df_map_filtered["property_type_airbnb"].nunique()
        )

    # Create and display map
    try:
        gdf_gemeenten = (
            gpd.read_file(GPKG_PATH, layer="gemeentegebied")
            .set_crs("EPSG:28992")
            .to_crs("EPSG:4326")
        )

        gemeenten = config.get(
            "gemeenten", df_map_filtered["gemeente"].unique().tolist()
        )
        map_obj = create_map(df_map_filtered, gdf_gemeenten, gemeenten, output_dir=None)
        st_folium(map_obj, width=None, height=600, returned_objects=[])
    except Exception as e:
        st.error(f"Fout bij maken kaart: {str(e)}")


def display_date_range_map(df_all, date_range, config):
    """Display map for a date range"""
    start_date, end_date = date_range
    st.markdown(f"Listings beschikbaar: **{start_date}** tot **{end_date}**")

    df_filtered = df_all[
        (pd.to_datetime(df_all["scan_checkin"]).dt.date >= start_date)
        & (pd.to_datetime(df_all["scan_checkin"]).dt.date <= end_date)
    ].copy()

    if df_filtered.empty:
        st.warning("Geen listings gevonden voor dit bereik")
        return

    df_avail_range = calculate_availability(
        df_filtered, start_date.isoformat(), end_date.isoformat()
    )

    df_map_range = df_filtered.drop_duplicates("room_id").merge(
        df_avail_range[
            ["room_id", "days_available", "availability_rate", "total_days"]
        ],
        on="room_id",
        how="left",
    )

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Unieke Listings", len(df_map_range))
    with col2:
        st.metric(
            "Gem. Beschikbaarheid", f"{df_avail_range['availability_rate'].mean():.1f}%"
        )
    with col3:
        st.metric("Gem. Prijs", f"€{df_map_range['price'].mean():.2f}")
    with col4:
        st.metric("Dagen in Bereik", (end_date - start_date).days + 1)

    # Create and display map
    try:
        gdf_gemeenten = (
            gpd.read_file(GPKG_PATH, layer="gemeentegebied")
            .set_crs("EPSG:28992")
            .to_crs("EPSG:4326")
        )

        gemeenten = config.get("gemeenten", df_map_range["gemeente"].unique().tolist())
        map_obj = create_map(df_map_range, gdf_gemeenten, gemeenten, output_dir=None)
        st_folium(map_obj, width=None, height=600, returned_objects=[])
    except Exception as e:
        st.error(f"Fout bij maken kaart: {str(e)}")


def display_total_availability_map(df_map, output_dir, config):
    """Display total availability map"""
    st.markdown("**Totale beschikbaarheid over alle meetmomenten**")

    map_html_path = os.path.join(output_dir, "map.html")
    if os.path.exists(map_html_path):
        with open(map_html_path, "r", encoding="utf-8") as f:
            map_html = f.read()
        st.components.v1.html(map_html, height=600, scrolling=True)
    else:
        st.info("Kaart niet gevonden. Probeer een andere weergave modus.")


def display_data_table(df_all, df_map):
    """Display filterable data table"""
    st.subheader("Listings Data")

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        property_types = ["Alle"] + sorted(
            df_all["property_type_airbnb"].unique().tolist()
        )
        selected_type = st.selectbox("Accommodatietype", property_types)

    with col2:
        gemeenten_filter = ["Alle"] + sorted(df_all["gemeente"].unique().tolist())
        selected_gemeente = st.selectbox("Gemeente", gemeenten_filter)

    with col3:
        min_availability = st.slider("Min Beschikbaarheid %", 0, 100, 0)

    with col4:
        all_dates = sorted(pd.to_datetime(df_all["scan_checkin"]).dt.date.unique())
        date_filter_mode = st.selectbox(
            "Datum Filter", ["Alle Datums", "Specifieke Datum"]
        )

    # Apply filters
    df_filtered = df_map.copy()

    if date_filter_mode == "Specifieke Datum" and len(all_dates) > 0:
        selected_date = st.selectbox("Selecteer Check-in Datum", all_dates)
        df_all_filtered = df_all[
            pd.to_datetime(df_all["scan_checkin"]).dt.date == selected_date
        ]
        df_filtered = df_all_filtered.drop_duplicates("room_id")

    if selected_type != "Alle":
        df_filtered = df_filtered[df_filtered["property_type_airbnb"] == selected_type]
    if selected_gemeente != "Alle":
        df_filtered = df_filtered[df_filtered["gemeente"] == selected_gemeente]
    if "availability_rate" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["availability_rate"] >= min_availability]

    # Display columns
    display_columns = ["listing_title", "property_type_airbnb", "gemeente", "price"]

    for col in ["availability_rate", "rating", "reviews_count", "bedrooms", "beds"]:
        if col in df_filtered.columns:
            display_columns.append(col)

    sort_by = (
        "availability_rate" if "availability_rate" in df_filtered.columns else "price"
    )

    st.dataframe(
        df_filtered[display_columns].sort_values(sort_by, ascending=False),
        width="stretch",
        height=500,
    )

    st.caption(f"Weergave van {len(df_filtered)} listings")


def display_analytics(df_all, df_availability, config, output_dir):
    """Display analytics charts"""
    st.subheader("Analyses & Inzichten")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Verdeling per Accommodatietype**")
        type_counts = df_all.groupby("property_type_airbnb")["room_id"].nunique()
        fig_pie = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.markdown("**Gemiddelde Prijs per Type**")
        avg_price = df_all.groupby("property_type_airbnb")["price"].mean().sort_values()
        fig_bar = px.bar(
            x=avg_price.values,
            y=avg_price.index,
            orientation="h",
            labels={"x": "Gemiddelde Prijs (€)", "y": "Accommodatietype"},
            color=avg_price.values,
            color_continuous_scale="Blues",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Availability distribution
    st.markdown("**Beschikbaarheid Verdeling**")
    fig_hist = px.histogram(
        df_availability,
        x="availability_rate",
        nbins=20,
        labels={"availability_rate": "Beschikbaarheid (%)"},
        color_discrete_sequence=["#FF5A5F"],
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    # Timeline
    st.markdown("**Beschikbaarheid Tijdlijn**")
    timeline_img_path = os.path.join(output_dir, "timeline_availability.png")
    if os.path.exists(timeline_img_path):
        st.image(timeline_img_path, width="stretch")
    else:
        st.info("Tijdlijn grafiek niet gevonden")


def display_export_options(output_dir):
    """Display export options"""
    st.subheader("Export Opties")

    st.markdown(f"**Output Map:** `{output_dir}`")

    if os.path.exists(output_dir):
        files = os.listdir(output_dir)
        st.markdown("**Gegenereerde Bestanden:**")
        for file in files:
            file_path = os.path.join(output_dir, file)
            file_size = os.path.getsize(file_path) / 1024
            st.markdown(f"- `{file}` ({file_size:.1f} KB)")

        # Download Excel
        excel_files = [
            f for f in files if f.endswith(".xlsx") and not f.startswith("~$")
        ]
        if excel_files:
            excel_path = os.path.join(output_dir, excel_files[0])
            with open(excel_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Excel Bestand",
                    data=f,
                    file_name=excel_files[0],
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )


def page_nieuwe_run():
    """Page for creating a new run with gemeente map"""
    st.title("Nieuwe Run Maken")

    # Initialize selected gemeenten in session state
    if "selected_gemeenten" not in st.session_state:
        st.session_state.selected_gemeenten = []

    col_config, col_map = st.columns([1, 2])

    with col_config:
        # Gemeente selection with search
        available_gemeenten = st.session_state.gemeenten_list
        if not available_gemeenten:
            st.error("Geen gemeenten beschikbaar")
            return

        # Multi-select dropdown for gemeente selection
        gemeenten = st.multiselect(
            "Selecteer Gemeenten",
            available_gemeenten,
            default=st.session_state.selected_gemeenten
            if st.session_state.selected_gemeenten
            else [],
            help="Zoek en selecteer één of meerdere gemeenten",
        )

        # Update session state
        st.session_state.selected_gemeenten = gemeenten

        st.markdown("---")

        # Date range configuration
        today = date.today()
        period_start = st.date_input("Start Datum", value=today)
        period_end = st.date_input("Eind Datum", value=today + timedelta(days=30))

        schedule_mode = st.radio(
            "Planning",
            ["📆 Interval", "📅 Weekdagen", "🗓️ Maandelijks"],
            horizontal=True,
        )

        # Initialize variables
        measurement_interval = 7
        days_of_week = None
        weeks_interval = 1
        monthly_interval = False

        if schedule_mode == "📆 Interval":
            measurement_interval = st.number_input(
                "Interval (dagen)", min_value=1, max_value=30, value=7
            )

        elif schedule_mode == "📅 Weekdagen":
            # Direct multiselect
            day_options = {
                "Maandag": 0,
                "Dinsdag": 1,
                "Woensdag": 2,
                "Donderdag": 3,
                "Vrijdag": 4,
                "Zaterdag": 5,
                "Zondag": 6,
            }

            selected_days = st.multiselect(
                "Dagen",
                options=list(day_options.keys()),
                default=["Vrijdag"],
            )

            if selected_days:
                days_of_week = [day_options[day] for day in selected_days]
            else:
                st.warning("⚠️ Selecteer minimaal één dag")
                days_of_week = None

            weeks_interval = 1  # Always every week

        elif schedule_mode == "🗓️ Maandelijks":
            monthly_interval = True

            # Direct multiselect
            day_options = {
                "Maandag": 0,
                "Dinsdag": 1,
                "Woensdag": 2,
                "Donderdag": 3,
                "Vrijdag": 4,
                "Zaterdag": 5,
                "Zondag": 6,
            }

            selected_days = st.multiselect(
                "Dagen (eerste per maand)",
                options=list(day_options.keys()),
                default=["Vrijdag"],
            )

            if selected_days:
                days_of_week = [day_options[day] for day in selected_days]
            else:
                st.warning("⚠️ Selecteer minimaal één dag")
                days_of_week = None

        # Show measurement moments in expandable section
        with st.expander("📅 Preview", expanded=True):
            if period_start >= period_end:
                st.warning("⚠️ Einddatum moet na startdatum zijn")
            else:
                # Generate scan combinations to get actual measurement dates
                scan_combinations, _ = generate_scan_combinations(
                    period_start=period_start.isoformat(),
                    period_end=period_end.isoformat(),
                    nights_list=[1],  # Dummy for preview
                    guests_list=[2],  # Dummy for preview
                    measurement_interval=measurement_interval,
                    days_of_week=days_of_week,
                    weeks_interval=weeks_interval,
                    monthly_interval=monthly_interval,
                )

                # Extract unique check-in dates
                measurement_dates = sorted(
                    list(
                        set(
                            [
                                datetime.fromisoformat(combo[0]).date()
                                for combo in scan_combinations
                            ]
                        )
                    )
                )

                if measurement_dates:
                    st.info(
                        f"**{len(measurement_dates)} metingen** over {(period_end - period_start).days} dagen"
                    )

                    # Group by month for better visualization
                    from collections import defaultdict

                    months = defaultdict(list)
                    for d in measurement_dates:
                        month_key = d.strftime("%B %Y")
                        months[month_key].append(d)

                    # Display each month
                    for month_name, dates in months.items():
                        st.markdown(f"**{month_name}**")

                        # Create calendar grid (7 days per row)
                        dates_str = ""
                        for i, d in enumerate(dates):
                            day_str = d.strftime("%d")
                            weekday = d.strftime("%a")
                            dates_str += f"<div style='display: inline-block; margin: 4px; padding: 8px 12px; background: #27ae60; color: white; border-radius: 6px; text-align: center; min-width: 60px;'><div style='font-size: 10px; opacity: 0.8;'>{weekday}</div><div style='font-size: 16px; font-weight: bold;'>{day_str}</div></div>"

                            # Add line break after every 3 dates for better mobile view
                            if (i + 1) % 3 == 0:
                                dates_str += "<br>"

                        st.markdown(dates_str, unsafe_allow_html=True)
                        st.markdown("")

    with col_map:
        # Map updates based on selected gemeenten - only loads selected geometries!
        if not st.session_state.selected_gemeenten:
            st.caption("📍 Voeg gemeenten toe om de kaart te zien")

        gemeente_map = create_gemeente_selection_map(
            st.session_state.selected_gemeenten
        )
        if gemeente_map:
            st_folium(
                gemeente_map,
                width=None,
                height=500,
                key=f"map_{len(st.session_state.selected_gemeenten)}",
                returned_objects=[],
            )
        else:
            st.error("Kon gemeente kaart niet laden")

    # Additional configuration in expander
    with st.expander("⚙️ Instellingen"):
        col1, col2 = st.columns(2)

        with col1:
            nights_input = st.text_input("Nachten (komma-gescheiden)", value="3,7")
            guests_input = st.text_input("Gasten (komma-gescheiden)", value="2")
            price_min = st.number_input("Min Prijs (€)", min_value=0, value=0)
            price_max = st.number_input("Max Prijs (€)", min_value=0, value=0)

        with col2:
            num_repeat_calls = st.number_input(
                "API Herhalingen",
                min_value=1,
                max_value=5,
                value=2,
                help="2-3 is aanbevolen. Meer = betere coverage maar meer API calls.",
            )
            zoom_value = st.number_input(
                "Zoom Level", min_value=1, max_value=20, value=12
            )
            max_workers = st.number_input(
                "Workers",
                min_value=1,
                max_value=10,
                value=1,
                help="1-2 is veilig, 3 is normaal, 5+ is risicovol",
            )
            currency = st.selectbox("Valuta", ["EUR", "USD", "GBP"], index=0)
            language = st.selectbox("Taal", ["nl", "en", "de"], index=0)

        # Rate Limit Protection
        with st.expander("⏱️ Rate Limits"):
            col_delay1, col_delay2 = st.columns(2)

            with col_delay1:
                delay_between_scans = st.number_input(
                    "Scan delay (sec)",
                    min_value=0.0,
                    max_value=10.0,
                    value=3.0,
                    step=0.5,
                )

            with col_delay2:
                delay_between_calls = st.number_input(
                    "Call delay (sec)",
                    min_value=0.0,
                    max_value=5.0,
                    value=1.5,
                    step=0.1,
                )

            # Recommendations
            if max_workers >= 5 and delay_between_scans < 1.0:
                st.warning("⚠️ Rate limit risico")
            elif max_workers <= 2 and delay_between_scans >= 1.5:
                st.success("✅ Veilig")

    # Start button
    st.markdown("---")

    if st.button("🚀 Start Scraping", type="primary", width="stretch"):
        if not gemeenten:
            st.error("Selecteer minimaal één gemeente")
            return

        if period_start >= period_end:
            st.error("Einddatum moet na startdatum zijn")
            return

        try:
            nights_list = [int(n.strip()) for n in nights_input.split(",")]
            guests_list = [int(g.strip()) for g in guests_input.split(",")]
        except ValueError:
            st.error("Ongeldig formaat voor nachten of gasten")
            return

        run_scraping_job(
            gemeenten=gemeenten,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            nights_list=nights_list,
            guests_list=guests_list,
            measurement_interval=measurement_interval,
            num_repeat_calls=num_repeat_calls,
            zoom_value=zoom_value,
            price_min=price_min,
            price_max=price_max,
            currency=currency,
            language=language,
            max_workers=max_workers,
            days_of_week=days_of_week,
            weeks_interval=weeks_interval,
            monthly_interval=monthly_interval,
            delay_between_scans=delay_between_scans,
            delay_between_calls=delay_between_calls,
        )


def run_scraping_job(
    gemeenten,
    period_start,
    period_end,
    nights_list,
    guests_list,
    measurement_interval,
    num_repeat_calls,
    zoom_value,
    price_min,
    price_max,
    currency,
    language,
    max_workers,
    days_of_week=None,
    weeks_interval=1,
    monthly_interval=False,
    delay_between_scans=1.0,
    delay_between_calls=0.5,
):
    """Execute the scraping job"""
    import time

    # Safety check: ensure nights_list and guests_list are lists
    if isinstance(nights_list, int):
        nights_list = [nights_list]
    if isinstance(guests_list, int):
        guests_list = [guests_list]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    gemeente_name = (
        "_".join(gemeenten) if len(gemeenten) <= 3 else f"{gemeenten[0]}_etc"
    )
    output_dir = os.path.join(DATA_DIR, f"run_{gemeente_name}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    measurement_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Terminal logging
    print("\n" + "=" * 80)
    print(f"🚀 NEW RUN STARTED: {gemeente_name}_{timestamp}")
    print("=" * 80)
    print(f"📍 Gemeenten: {', '.join(gemeenten)}")
    print(f"📅 Periode: {period_start} → {period_end}")
    print(f"🛏️  Nachten: {nights_list}")
    print(f"👥 Gasten: {guests_list}")
    print(f"⚙️  Workers: {max_workers}")
    print(f"📁 Output: {output_dir}")
    print("=" * 80 + "\n")

    # Initialize run tracker
    tracker = RunTracker(output_dir)

    # Save config
    config = {
        "gemeenten": gemeenten,
        "period_start": period_start,
        "period_end": period_end,
        "nights_list": nights_list,
        "guests_list": guests_list,
        "measurement_interval": measurement_interval,
        "num_repeat_calls": num_repeat_calls,
        "zoom_value": zoom_value,
        "price_min": price_min,
        "price_max": price_max,
        "currency": currency,
        "language": language,
        "measurement_date": measurement_date,
        "days_of_week": days_of_week,
        "weeks_interval": weeks_interval,
        "monthly_interval": monthly_interval,
        "max_workers": max_workers,
        "delay_between_scans": delay_between_scans,
        "delay_between_calls": delay_between_calls,
    }

    with open(os.path.join(output_dir, "config.json"), "w") as f:
        json.dump(config, f, indent=2)

    # Start background scraping job using threading
    import threading

    def run_scraping_in_background():
        """Run the actual scraping in a background thread"""
        try:
            _execute_scraping(
                gemeenten,
                period_start,
                period_end,
                nights_list,
                guests_list,
                measurement_interval,
                num_repeat_calls,
                zoom_value,
                price_min,
                price_max,
                currency,
                language,
                max_workers,
                output_dir,
                days_of_week,
                weeks_interval,
                monthly_interval,
                delay_between_scans,
                delay_between_calls,
                config,
            )
        except Exception as e:
            tracker.fail(str(e))

    # Start thread
    thread = threading.Thread(target=run_scraping_in_background, daemon=True)
    thread.start()

    # Redirect to run detail page to see live logs
    st.success("✅ Run gestart in background! Redirecting naar live logs...")
    st.session_state.viewing_run_detail = output_dir
    st.session_state.page = "📊 Resultaten"
    time.sleep(0.5)
    st.rerun()


def _execute_scraping(
    gemeenten,
    period_start,
    period_end,
    nights_list,
    guests_list,
    measurement_interval,
    num_repeat_calls,
    zoom_value,
    price_min,
    price_max,
    currency,
    language,
    max_workers,
    output_dir,
    days_of_week,
    weeks_interval,
    monthly_interval,
    delay_between_scans,
    delay_between_calls,
    config,
):
    """Execute the actual scraping (to be run in background thread)"""

    # Safety check: ensure nights_list and guests_list are lists
    if isinstance(nights_list, int):
        nights_list = [nights_list]
    if isinstance(guests_list, int):
        guests_list = [guests_list]

    tracker = RunTracker(output_dir)
    measurement_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Set up logging handler to redirect Python logger to RunTracker
    import logging

    class TrackerLogHandler(logging.Handler):
        """Custom logging handler that writes to RunTracker"""

        def __init__(self, tracker):
            super().__init__()
            self.tracker = tracker
            self.last_checkpoint = 0

        def emit(self, record):
            try:
                # Skip all verbose logging - we only want clean progress bar updates
                # which are generated by the monitoring thread
                pass
            except Exception:
                # Don't let logging errors crash the scraper
                pass

    # Add custom handler to capture logs from scraper modules
    handler = TrackerLogHandler(tracker)
    handler.setLevel(logging.INFO)

    # Add to relevant loggers (but handler will suppress all messages)
    for logger_name in [
        "src.core.scraper_core",
        "src.data.data_processor",
        "src.data.exporter",
        "src.core.scraper_utils",  # Suppress generate_scan_combinations messages
    ]:
        logger_obj = logging.getLogger(logger_name)
        logger_obj.addHandler(handler)
        logger_obj.setLevel(
            logging.CRITICAL
        )  # Set to CRITICAL to suppress INFO messages

    try:
        # Generate scan combinations (suppressing verbose output)
        scan_combinations, _ = generate_scan_combinations(
            period_start,
            period_end,
            nights_list,
            guests_list,
            measurement_interval,
            days_of_week,
            weeks_interval,
            monthly_interval,
        )

        total_scans = len(scan_combinations) * len(gemeenten)
        tracker.start(total_scans=total_scans)

        # Initial progress bar
        tracker.log(f"⚡ 🔴 0/{total_scans} (0%) │ 🏠 0 listings │ ⏱️ 0.0m / ~0m")

        import time
        import threading

        start_time = time.time()

        # Monitor checkpoints for progress tracking
        stop_monitoring = threading.Event()
        last_checkpoint_count = [0]  # Track last count to avoid duplicate logs

        def monitor_checkpoints():
            """Monitor status and log progress after each scan completion"""
            last_reported_progress = [-1]
            last_checkpoint_count = [0]

            while not stop_monitoring.is_set():
                time.sleep(0.5)  # Check every 0.5 seconds for real-time updates
                try:
                    current_time = time.time()
                    elapsed = current_time - start_time

                    # Read actual progress from run_status.json
                    status_file = os.path.join(output_dir, "run_status.json")
                    actual_completed = 0
                    total_listings = 0

                    if os.path.exists(status_file):
                        try:
                            with open(status_file, "r") as f:
                                status_data = json.load(f)
                                actual_completed = status_data.get("progress", {}).get(
                                    "completed_scans", 0
                                )
                                total_listings = status_data.get("progress", {}).get(
                                    "total_listings", 0
                                )
                        except:
                            pass

                    # If no progress from status file, estimate from checkpoint files
                    if actual_completed == 0:
                        import glob

                        checkpoint_files = glob.glob(
                            os.path.join(output_dir, "checkpoint_*.xlsx")
                        )
                        num_checkpoints = len(checkpoint_files)

                        # Each checkpoint ≈ 10 scans, but check for new checkpoints
                        if num_checkpoints > last_checkpoint_count[0]:
                            last_checkpoint_count[0] = num_checkpoints
                            actual_completed = num_checkpoints * 10

                    # Only log when progress changes (new scan completed)
                    if actual_completed > last_reported_progress[0]:
                        last_reported_progress[0] = actual_completed

                        progress_pct = (actual_completed / total_scans) * 100
                        avg_time = (
                            elapsed / actual_completed if actual_completed > 0 else 0
                        )
                        remaining = (
                            avg_time * (total_scans - actual_completed)
                            if actual_completed > 0
                            else 0
                        )

                        # Status emoji based on progress
                        if progress_pct >= 75:
                            status_emoji = "🟢"
                        elif progress_pct >= 25:
                            status_emoji = "🟡"
                        else:
                            status_emoji = "🔴"

                        # Show update for this scan
                        tracker.log(
                            f"⚡ {status_emoji} {actual_completed}/{total_scans} ({progress_pct:.0f}%) │ "
                            f"🏠 {total_listings:,} listings │ "
                            f"⏱️ {elapsed / 60:.1f}m / ~{remaining / 60:.0f}m"
                        )
                        tracker.update_progress(completed_scans=actual_completed)

                except Exception:
                    pass

        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_checkpoints, daemon=True)
        monitor_thread.start()

        df_all = scrape_all(
            gemeenten=gemeenten,
            scan_combinations=scan_combinations,
            gpkg_path=GPKG_PATH,
            num_repeat_calls=num_repeat_calls,
            zoom_value=zoom_value,
            price_min=price_min,
            price_max=price_max,
            amenities=[],
            currency=currency,
            language=language,
            proxy_url="",
            measurement_date=measurement_date,
            show_progress=False,  # Disable tqdm progress bar
            max_workers=max_workers,  # ⚡ Parallel scraping (configureerbaar)
            checkpoint_dir=output_dir,  # 💾 Tussentijds opslaan
            delay_between_scans=delay_between_scans,  # ⏱️ Rate limit protection
            delay_between_calls=delay_between_calls,  # ⏱️ Rate limit protection
            tracker=tracker,  # Pass tracker for real-time progress updates
        )

        # Stop monitoring
        stop_monitoring.set()

        elapsed_time = time.time() - start_time

        # Update final scanning stats
        if df_all.empty:
            tracker.fail("Geen resultaten gevonden")
            return

        total_listings = df_all["room_id"].nunique()

        # Final progress bar update
        tracker.log(
            f"⚡ 🟢 {total_scans}/{total_scans} (100%) │ "
            f"🏠 {total_listings:,} listings │ ⏱️ {elapsed_time / 60:.1f}m"
        )
        tracker.update_progress(completed_scans=total_scans)

        # Process data silently
        df_availability = calculate_availability(df_all, period_start, period_end)
        df_map = df_all.drop_duplicates("room_id").merge(
            df_availability[
                ["room_id", "days_available", "availability_rate", "total_days"]
            ],
            on="room_id",
            how="left",
        )

        df_export = prepare_export_data(df_all)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"airbnb_scrape_{'_'.join(gemeenten)}_{timestamp}.xlsx"
        excel_path = os.path.join(output_dir, excel_filename)
        export_to_excel(df_export, excel_path, df_availability, df_all)

        # Create visualizations (non-critical - don't fail run if these error)
        try:
            gdf_gemeenten = (
                gpd.read_file(GPKG_PATH, layer="gemeentegebied")
                .set_crs("EPSG:28992")
                .to_crs("EPSG:4326")
            )
            create_map(df_map, gdf_gemeenten, gemeenten, output_dir)
        except Exception as e:
            tracker.log(f"⚠️ Map creation failed: {str(e)[:100]}")

        try:
            create_availability_timeline_graph(
                df_all, period_start, period_end, output_dir
            )
        except Exception as e:
            tracker.log(f"⚠️ Timeline graph creation failed: {str(e)[:100]}")

        # Mark as complete AFTER data is saved
        tracker.complete(total_listings=total_listings)
        # Final summary message
        tracker.log(
            f"✅ Voltooid │ {len(df_all):,} records │ {total_listings:,} listings │ "
            f"€{df_all['price'].mean():.0f} avg │ {df_availability['availability_rate'].mean():.0f}% beschikbaar"
        )

        # Terminal logging for completion
        print("\n" + "=" * 80)
        print(f"✅ RUN COMPLETED: {os.path.basename(output_dir)}")
        print("=" * 80)
        print(f"📊 Records: {len(df_all):,}")
        print(f"🏠 Unique Listings: {total_listings:,}")
        print(f"💰 Avg Price: €{df_all['price'].mean():.2f}")
        print(
            f"📈 Avg Availability: {df_availability['availability_rate'].mean():.1f}%"
        )
        print(f"⏱️  Duration: {elapsed_time / 60:.1f}m")
        print(f"📁 Output: {output_dir}")
        print("=" * 80 + "\n")

    except Exception as e:
        tracker.fail(str(e))
        logger.exception("Scraping error")

        # Terminal logging for failure
        print("\n" + "=" * 80)
        print(f"❌ RUN FAILED: {os.path.basename(output_dir)}")
        print("=" * 80)
        print(f"Error: {str(e)[:200]}")
        print(f"📁 Output: {output_dir}")
        print("=" * 80 + "\n")


def display_monitoring_tab():
    """Display monitoring view as tab"""
    from src.core.run_tracker import get_all_runs, RunTracker

    # Refresh button
    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        if st.button("🔄 Refresh", width="stretch"):
            st.rerun()

    # Get all runs
    runs = get_all_runs(data_dir=DATA_DIR)

    if not runs:
        st.info("Geen runs gevonden.")
        return

    # Summary stats at top
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        running_count = len([r for r in runs if r.get("status") == "running"])
        st.metric("🔄 Running", running_count)

    with col2:
        completed_count = len([r for r in runs if r.get("status") == "completed"])
        st.metric("✅ Completed", completed_count)

    with col3:
        failed_count = len([r for r in runs if r.get("status") == "failed"])
        st.metric("❌ Failed", failed_count)

    with col4:
        pending_count = len([r for r in runs if r.get("status") == "pending"])
        st.metric("⏳ Pending", pending_count)

    st.markdown("---")

    # Filter by status
    status_filter = st.multiselect(
        "Filter op status",
        ["running", "completed", "failed", "pending", "cancelled"],
        default=["running", "pending"],
    )

    # Filter runs
    filtered_runs = [r for r in runs if r.get("status") in status_filter]

    if not filtered_runs:
        st.info(f"Geen runs met status: {', '.join(status_filter)}")
        return

    # Show runs
    for run in filtered_runs:
        status = run.get("status", "unknown")
        run_name = run["run_name"]
        run_path = run["run_path"]

        # Status icon
        if status == "running":
            icon = "🔄"
        elif status == "completed":
            icon = "✅"
        elif status == "failed":
            icon = "❌"
        elif status == "pending":
            icon = "⏳"
        else:
            icon = "❓"

        # Load config for this run
        config_path = os.path.join(run_path, "config.json")
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)

        # Parse gemeente from config
        gemeente = (
            config.get("gemeenten", ["Onbekend"])[0]
            if config.get("gemeenten")
            else "Onbekend"
        )

        # Run card - show gemeente prominently
        with st.expander(
            f"{icon} {gemeente} - {status.upper()}", expanded=(status == "running")
        ):
            # Show run name and date
            st.caption(f"📁 {run_name}")

            col_info, col_logs = st.columns([1, 2])

            with col_info:
                st.markdown(f"**Status:** `{status}`")

                if "created_at" in run:
                    st.caption(f"🕐 {run['created_at']}")
                if "started_at" in run and run["started_at"]:
                    st.caption(f"▶️ {run['started_at']}")
                if "completed_at" in run and run["completed_at"]:
                    st.caption(f"✓ {run['completed_at']}")

                # Progress
                if "progress" in run:
                    progress = run["progress"]
                    total = progress.get("total_scans", 0)
                    completed = progress.get("completed_scans", 0)
                    failed = progress.get("failed_scans", 0)
                    listings = progress.get("total_listings", 0)

                    if total > 0:
                        progress_pct = (completed / total) * 100
                        st.progress(progress_pct / 100)
                        st.caption(f"{completed}/{total} scans ({progress_pct:.1f}%)")

                    col_m1, col_m2 = st.columns(2)
                    if completed > 0:
                        col_m1.metric("Scans", f"{completed:,}")
                    if listings > 0:
                        col_m2.metric("Listings", f"{listings:,}")
                    if failed > 0:
                        st.metric("Failed", f"{failed:,}", delta_color="inverse")

                # Error message
                if "error" in run and run["error"]:
                    st.error(f"Error: {run['error']}")

                # Config in nested expander
                with st.expander("⚙️ Configuratie", expanded=False):
                    st.markdown("**📍 Gemeenten**")
                    gemeenten = config.get("gemeenten", [])
                    if gemeenten:
                        for g in gemeenten:
                            st.caption(f"  • {g}")
                    else:
                        st.caption("Onbekend")

                    st.markdown("**📅 Periode**")
                    st.caption(f"Start: {config.get('period_start', '-')}")
                    st.caption(f"Eind: {config.get('period_end', '-')}")

                    st.markdown("**🛏️ Nachten**")
                    st.caption(f"{config.get('nights_list', [])}")

                    st.markdown("**👥 Gasten**")
                    st.caption(f"{config.get('guests_list', [])}")

            with col_logs:
                st.markdown("**📋 Logs**")

                # Show logs
                tracker = RunTracker(run_path)
                logs = tracker.get_logs(tail=100)

                if logs:
                    # Log viewer with scroll
                    st.code(logs, language=None, line_numbers=False)

                    # Download logs button
                    st.download_button(
                        label="⬇️ Download Logs",
                        data=logs,
                        file_name=f"{run_name}.log",
                        mime="text/plain",
                    )
                else:
                    st.caption("Nog geen logs beschikbaar")

    # Auto-refresh disabled - use manual refresh button instead


def page_monitoring():
    """Legacy monitoring page - redirects to results tab"""
    st.info("Monitoring is nu geïntegreerd in Resultaten → Status & Logs")
    if st.button("Ga naar Resultaten"):
        st.session_state.page = "📊 Resultaten"
        st.rerun()


def page_instellingen():
    """Settings page"""
    st.title("Instellingen")

    st.subheader("Data Beheer")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Beschikbare Gemeenten", len(st.session_state.gemeenten_list))
        st.metric("Historische Runs", len(get_historical_runs()))

    with col2:
        if os.path.exists(DATA_DIR):
            total_size = sum(
                os.path.getsize(os.path.join(dirpath, f))
                for dirpath, _, filenames in os.walk(DATA_DIR)
                for f in filenames
            )
            st.metric("Data Map Grootte", f"{total_size / 1024 / 1024:.1f} MB")

    st.markdown("---")

    st.subheader("GeoPackage Status")
    if os.path.exists(GPKG_PATH):
        st.success(f"✅ GeoPackage gevonden: `{GPKG_PATH}`")
        try:
            gdf = gpd.read_file(GPKG_PATH, layer="gemeentegebied")
            st.info(f"Bevat {len(gdf)} gemeenten")
        except Exception as e:
            st.error(f"Fout bij lezen GeoPackage: {e}")
    else:
        st.error(f"❌ GeoPackage niet gevonden: `{GPKG_PATH}`")

    st.markdown("---")

    st.subheader("Acties")

    if st.button("🔄 Ververs Gemeenten Lijst"):
        st.session_state.gemeenten_list = load_gemeenten_list()
        st.success("✅ Gemeenten lijst ververst")
        st.rerun()

    if st.button("🗑️ Wis Sessie Cache"):
        st.session_state.current_results = None
        st.success("✅ Sessie cache gewist")
        st.rerun()


def page_mapping_configuratie():
    """Room type mapping configuration page"""
    st.title("🏷️ Room Type Mapping Configuratie")

    st.markdown("""
    Configureer hoe gedetecteerde room types worden gemapped naar gestandaardiseerde categorieën.
    Deze mappings worden gebruikt tijdens het scrapen om listings te classificeren.
    """)

    # Load current mappings
    from src.config.room_type_config import ROOM_TYPE_MAPPING, STANDARD_PROPERTY_TYPES

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(
        ["📋 Bekijk Mappings", "➕ Toevoegen/Bewerken", "📊 Statistieken"]
    )

    with tab1:
        st.subheader("Huidige Mappings")

        # Filter options
        col_filter1, col_filter2 = st.columns([2, 1])

        with col_filter1:
            search_term = st.text_input(
                "🔍 Zoeken in mappings",
                placeholder="Zoek op naam...",
                key="mapping_search",
            )

        with col_filter2:
            filter_category = st.selectbox(
                "Filter op categorie",
                ["Alle"] + STANDARD_PROPERTY_TYPES,
                key="filter_category",
            )

        # Filter mappings
        filtered_mappings = {}
        for key, value in sorted(ROOM_TYPE_MAPPING.items()):
            # Apply filters
            if filter_category != "Alle" and value != filter_category:
                continue
            if search_term and search_term.lower() not in key.lower():
                continue
            filtered_mappings[key] = value

        st.caption(
            f"Weergave van {len(filtered_mappings)} van {len(ROOM_TYPE_MAPPING)} mappings"
        )

        # Group by category for better display
        for category in STANDARD_PROPERTY_TYPES:
            category_mappings = {
                k: v for k, v in filtered_mappings.items() if v == category
            }

            if category_mappings:
                with st.expander(
                    f"**{category}** ({len(category_mappings)} mappings)",
                    expanded=(filter_category == category or filter_category == "Alle"),
                ):
                    # Create a dataframe for display
                    mapping_data = []
                    for detected, mapped in sorted(category_mappings.items()):
                        mapping_data.append(
                            {"Gedetecteerd Type": detected, "Gemapped naar": mapped}
                        )

                    if mapping_data:
                        df_display = pd.DataFrame(mapping_data)
                        st.dataframe(df_display, width="stretch", hide_index=True)

    with tab2:
        st.subheader("Mapping Toevoegen of Bewerken")

        st.info(
            "ℹ️ **Let op:** Wijzigingen vereisen aanpassing van `src/config/room_type_config.py`"
        )

        col_input1, col_input2 = st.columns(2)

        with col_input1:
            detected_type = st.text_input(
                "Gedetecteerd Type",
                placeholder="Bijv: Entire vacation home",
                help="Het type zoals het door Airbnb wordt geretourneerd",
            )

        with col_input2:
            mapped_category = st.selectbox(
                "Map naar Categorie",
                STANDARD_PROPERTY_TYPES,
                help="De gestandaardiseerde categorie",
            )

        if st.button("➕ Toevoegen aan Configuratie", type="primary", width="stretch"):
            if detected_type:
                # Import the updater
                from src.config.room_type_updater import add_mapping_to_config

                # Add directly to config file
                success, message = add_mapping_to_config(detected_type, mapped_category)

                if success:
                    st.success(message)
                    st.info(
                        "🔄 Herlaad de pagina om de nieuwe mapping te zien in de lijst"
                    )
                    # Show what was added
                    st.code(
                        f'"{detected_type}": "{mapped_category}"', language="python"
                    )
                else:
                    st.error(message)
            else:
                st.warning("⚠️ Vul een gedetecteerd type in")

        st.markdown("---")

        # Bulk add section
        with st.expander("📝 Bulk Toevoegen (Meerdere Mappings)"):
            st.markdown(
                "Voeg meerdere mappings toe, één per regel in het formaat: `detected_type -> category`"
            )

            bulk_input = st.text_area(
                "Bulk Mappings",
                placeholder="Entire beach house -> Entire home\nPrivate room in villa -> Private room\nRoom in hostel -> Hotel",
                height=150,
            )

            selected_category_bulk = st.selectbox(
                "Standaard categorie (indien niet gespecificeerd)",
                STANDARD_PROPERTY_TYPES,
                key="bulk_category",
            )

            if st.button("➕ Bulk Toevoegen", type="primary"):
                if bulk_input:
                    from src.config.room_type_updater import add_bulk_mappings

                    lines = bulk_input.strip().split("\n")
                    mappings = []

                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue

                        if "->" in line:
                            parts = line.split("->")
                            detected = parts[0].strip()
                            category = (
                                parts[1].strip()
                                if len(parts) > 1
                                else selected_category_bulk
                            )
                        else:
                            detected = line
                            category = selected_category_bulk

                        mappings.append((detected, category))

                    if mappings:
                        # Add all mappings
                        success_count, skip_count, messages = add_bulk_mappings(
                            mappings
                        )

                        # Show results
                        if success_count > 0:
                            st.success(f"✅ {success_count} mappings toegevoegd!")
                        if skip_count > 0:
                            st.warning(
                                f"⚠️ {skip_count} mappings overgeslagen (bestaan al)"
                            )

                        # Show details in expander
                        with st.expander("📋 Details"):
                            for msg in messages:
                                st.caption(msg)

                        if success_count > 0:
                            st.info(
                                "🔄 Herlaad de pagina om de nieuwe mappings te zien"
                            )
                else:
                    st.warning("⚠️ Voer mappings in")

    with tab3:
        st.subheader("📊 Mapping Statistieken")

        # Count by category
        category_counts = {}
        for value in ROOM_TYPE_MAPPING.values():
            category_counts[value] = category_counts.get(value, 0) + 1

        col_stats1, col_stats2 = st.columns(2)

        with col_stats1:
            st.metric("Totaal Mappings", len(ROOM_TYPE_MAPPING))
            st.metric("Categorieën", len(STANDARD_PROPERTY_TYPES))

        with col_stats2:
            most_common = max(category_counts, key=category_counts.get)
            st.metric("Meest Voorkomend", most_common)
            st.metric("Aantal", category_counts[most_common])

        st.markdown("---")

        # Distribution chart
        st.markdown("**Verdeling per Categorie**")

        import plotly.express as px

        df_stats = pd.DataFrame(
            [
                {"Categorie": cat, "Aantal Mappings": count}
                for cat, count in sorted(
                    category_counts.items(), key=lambda x: x[1], reverse=True
                )
            ]
        )

        fig = px.bar(
            df_stats,
            x="Categorie",
            y="Aantal Mappings",
            color="Aantal Mappings",
            color_continuous_scale="Viridis",
            text="Aantal Mappings",
        )

        fig.update_traces(textposition="outside")
        fig.update_layout(
            showlegend=False, height=400, xaxis_title="", yaxis_title="Aantal Mappings"
        )

        st.plotly_chart(fig, use_container_width=True)

        # Detailed breakdown
        st.markdown("**Details per Categorie**")

        for category in sorted(
            category_counts.keys(), key=lambda x: category_counts[x], reverse=True
        ):
            count = category_counts[category]
            percentage = (count / len(ROOM_TYPE_MAPPING)) * 100

            st.markdown(
                f"""
            <div style='background: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                <strong style='font-size: 1.1em;'>{category}</strong><br>
                <span style='color: #666;'>{count} mappings ({percentage:.1f}%)</span>
            </div>
            """,
                unsafe_allow_html=True,
            )


def sidebar_navigation():
    """Sidebar navigation"""
    # Add RIGO logo using st.logo
    st.logo(str(LOGO_PATH), size="large")

    st.sidebar.title("Airbnb Scraper")
    st.sidebar.markdown("---")

    # Use buttons instead of radio for cleaner look
    if st.sidebar.button(
        "📊 Resultaten",
        width="stretch",
        type="primary"
        if st.session_state.get("page") == "📊 Resultaten"
        else "secondary",
    ):
        st.session_state.page = "📊 Resultaten"
        st.rerun()

    if st.sidebar.button(
        "➕ Nieuwe Run",
        width="stretch",
        type="primary"
        if st.session_state.get("page") == "➕ Nieuwe Run"
        else "secondary",
    ):
        st.session_state.page = "➕ Nieuwe Run"
        st.rerun()

    if st.sidebar.button(
        "🏷️ Mapping Configuratie",
        width="stretch",
        type="primary" if st.session_state.get("page") == "🏷️ Mapping" else "secondary",
    ):
        st.session_state.page = "🏷️ Mapping"
        st.rerun()

    if st.sidebar.button(
        "⚙️ Instellingen",
        width="stretch",
        type="primary"
        if st.session_state.get("page") == "⚙️ Instellingen"
        else "secondary",
    ):
        st.session_state.page = "⚙️ Instellingen"
        st.rerun()

    st.sidebar.markdown("---")

    # Stats
    st.sidebar.markdown("### 📊 Overzicht")
    runs = get_historical_runs()
    runs_count = len(runs)

    # Count unique gemeenten across all runs
    unique_gemeenten = set()
    if runs:
        for run in runs:
            gemeente = run.get("gemeente", "")
            if gemeente:
                unique_gemeenten.add(gemeente)

    st.sidebar.metric("Beschikbare Runs", runs_count)
    if unique_gemeenten:
        st.sidebar.metric("Gemeenten Gescand", len(unique_gemeenten))

    return st.session_state.get("page", "📊 Resultaten")


def main():
    """Main application"""
    check_login()
    load_custom_css()
    init_session_state()

    # Navigation
    if "page" not in st.session_state:
        st.session_state.page = "📊 Resultaten"

    page = sidebar_navigation()
    st.session_state.page = page

    # Route to pages
    if page == "📊 Resultaten":
        page_resultaten()
    elif page == "➕ Nieuwe Run":
        page_nieuwe_run()
    elif page == "📡 Monitoring":
        page_monitoring()
    elif page == "🏷️ Mapping":
        page_mapping_configuratie()
    elif page == "⚙️ Instellingen":
        page_instellingen()


if __name__ == "__main__":
    main()
