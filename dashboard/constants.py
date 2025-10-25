"""Constants and configuration for the dashboard"""

from enum import Enum
from typing import Dict, Any


class DataSource(str, Enum):
    """Data source types"""

    AIRBNB = "airbnb"
    FUNDA = "funda"
    BOOKING = "booking"


class RunStatus(str, Enum):
    """Run status types"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    LEGACY = "legacy"


# Data source configuration
DATA_SOURCE_CONFIG: Dict[str, Dict[str, Any]] = {
    DataSource.AIRBNB: {
        "name": "Airbnb",
        "icon": "home",
        "color": "#FF5A5F",
        "color_light": "#FFE5E7",
        "enabled": True,
        "description": "Vacation rentals",
    },
    DataSource.FUNDA: {
        "name": "Funda",
        "icon": "apartment",
        "color": "#F7A100",
        "color_light": "#FFF4E5",
        "enabled": True,
        "description": "Real estate listings",
    },
    DataSource.BOOKING: {
        "name": "Booking.com",
        "icon": "hotel",
        "color": "#003580",
        "color_light": "#E5F0FF",
        "enabled": False,
        "description": "Hotel bookings",
    },
}

# Status configuration
STATUS_CONFIG: Dict[str, Dict[str, str]] = {
    RunStatus.PENDING: {
        "label": "In Wachtrij",
        "color": "#f57c00",
        "bg": "#fff3e0",
        "icon": "schedule",
    },
    RunStatus.RUNNING: {
        "label": "Bezig",
        "color": "#1976d2",
        "bg": "#e3f2fd",
        "icon": "autorenew",
    },
    RunStatus.COMPLETED: {
        "label": "Voltooid",
        "color": "#2e7d32",
        "bg": "#e8f5e9",
        "icon": "check_circle",
    },
    RunStatus.FAILED: {
        "label": "Mislukt",
        "color": "#c62828",
        "bg": "#ffebee",
        "icon": "cancel",
    },
    RunStatus.LEGACY: {
        "label": "Oud",
        "color": "#616161",
        "bg": "#f5f5f5",
        "icon": "archive",
    },
}


# Page routes
class PageRoutes:
    """Dashboard page routes"""

    LOGIN = "/"
    DASHBOARD = "/dashboard"
    NEW_RUN = "/nieuwe_run"
    RUN_DETAIL = "/run"
    MAPPING = "/mapping"
    SETTINGS = "/instellingen"


# UI Constants
class UIConstants:
    """UI-related constants"""

    # Colors
    PRIMARY_COLOR = "#10357e"
    PRIMARY_DARK = "#0a2454"
    ACCENT_COLOR = "#da9a36"
    SUCCESS_COLOR = "#2e7d32"
    WARNING_COLOR = "#f57c00"
    ERROR_COLOR = "#c62828"

    # Spacing
    SPACING_XS = "4px"
    SPACING_SM = "8px"
    SPACING_MD = "16px"
    SPACING_LG = "24px"
    SPACING_XL = "32px"

    # Font sizes
    FONT_SIZE_SM = "12px"
    FONT_SIZE_MD = "14px"
    FONT_SIZE_LG = "16px"
    FONT_SIZE_XL = "20px"

    # Border radius
    BORDER_RADIUS_SM = "4px"
    BORDER_RADIUS_MD = "8px"
    BORDER_RADIUS_LG = "12px"


# Helper functions
def get_enabled_sources():
    """Get list of enabled data sources"""
    return [
        source for source, config in DATA_SOURCE_CONFIG.items() if config["enabled"]
    ]


def get_source_config(source: str) -> Dict[str, Any]:
    """Get configuration for a specific data source"""
    return DATA_SOURCE_CONFIG.get(source, DATA_SOURCE_CONFIG[DataSource.AIRBNB])


def get_status_config(status: str) -> Dict[str, str]:
    """Get configuration for a specific status"""
    return STATUS_CONFIG.get(status, STATUS_CONFIG[RunStatus.COMPLETED])
