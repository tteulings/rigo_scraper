# Multi-Source Dashboard Guide

This dashboard is designed to easily support multiple data sources (Airbnb, Funda, Booking.com, etc.)

## Architecture Overview

The dashboard uses a modular architecture with:
- **Centralized constants** for data source configuration
- **Automatic source detection** from run metadata
- **Filtering system** to view runs by source
- **Visual indicators** (chips/badges) showing data source

## Files Structure

```
dashboard/
├── constants.py                 # Central configuration for all sources
├── dash_helpers/
│   └── run_utils.py             # Source detection and filtering utilities
├── dash_components/
│   └── ui_elements.py           # Source chips and badges
└── dash_callbacks/
    └── run_callbacks.py         # Filtering logic with source support
```

## Adding a New Data Source

### Step 1: Add Source to Constants

Edit `dashboard/constants.py`:

```python
class DataSource(str, Enum):
    AIRBNB = "airbnb"
    FUNDA = "funda"
    BOOKING = "booking"
    YOUR_NEW_SOURCE = "your_source"  # Add here

DATA_SOURCE_CONFIG: Dict[str, Dict[str, Any]] = {
    DataSource.YOUR_NEW_SOURCE: {
        "name": "Your Source Name",
        "icon": "store",  # Material Icons name
        "color": "#FF5A5F",  # Primary color
        "color_light": "#FFE5E7",  # Light background color
        "enabled": True,
        "description": "Description of your source",
    },
}
```

###2: Update Source Detection

Edit `dashboard/dash_helpers/run_utils.py` in the `detect_run_source()` function:

```python
def detect_run_source(run: Dict[str, Any]) -> str:
    run_name = run.get("run_name", "").lower()
    
    if "your_source" in run_name:
        return DataSource.YOUR_NEW_SOURCE
    # ... existing detection logic
```

### Step 3: Add to Filter Dropdown

Edit `dashboard/dash_pages/resultaten_page.py`:

```python
dcc.Dropdown(
    id="source-filter",
    options=[
        {"label": "Alle bronnen", "value": "all"},
        {"label": "🏠 Airbnb", "value": "airbnb"},
        {"label": "🏢 Funda", "value": "funda"},
        {"label": "🏪 Your Source", "value": "your_source"},  # Add here
    ],
    # ...
)
```

### Step 4: Save Source in Run Config

When creating a new run, save the source in `config.json`:

```python
config = {
    "source": "your_source",
    "gemeenten": [...],
    # ... other config
}
```

## Features

### 1. Source Chips
Display data source with icon on each run card:

```python
from dashboard.dash_components import source_chip

# With label
source_chip("airbnb", show_label=True)

# Icon only
source_chip("airbnb", show_label=False)
```

### 2. Source Filtering
Filter runs by source in the overview page using the "Bron" dropdown.

### 3. Automatic Detection
If a run doesn't have a `source` field, it's automatically detected from:
1. Run name (e.g., "funda_amsterdam_...")
2. Config.json file
3. Defaults to Airbnb if unclear

### 4. Source-Specific Styling
Each source has:
- **Icon**: Material Icons identifier
- **Primary color**: Used for borders and text
- **Light color**: Used for backgrounds
- **Name**: Display name in UI

## Configuration Constants

### Available Constants

From `dashboard.constants`:

```python
from dashboard.constants import (
    DataSource,          # Enum of all sources
    RunStatus,           # Enum of run statuses
    DATA_SOURCE_CONFIG,  # Source configurations
    STATUS_CONFIG,       # Status configurations
    PageRoutes,          # Page route constants
    UIConstants,         # UI colors, spacing, etc.
)

# Helper functions
from dashboard.constants import (
    get_enabled_sources,   # List of enabled sources
    get_source_config,     # Get config for a source
    get_status_config,     # Get config for a status
)
```

### UI Constants

```python
from dashboard.constants import UIConstants

# Colors
UIConstants.PRIMARY_COLOR    # "#10357e"
UIConstants.ACCENT_COLOR      # "#da9a36"
UIConstants.SUCCESS_COLOR     # "#2e7d32"

# Spacing
UIConstants.SPACING_SM        # "8px"
UIConstants.SPACING_MD        # "16px"
UIConstants.SPACING_LG        # "24px"

# Border radius
UIConstants.BORDER_RADIUS_MD  # "8px"
```

## Utilities

### Run Utils

```python
from dashboard.dash_helpers import (
    detect_run_source,      # Detect source from run metadata
    add_source_to_run,      # Add source field to run dict
    get_runs_by_source,     # Filter runs by source
)

# Example usage
runs = get_all_runs(DATA_DIR)
runs = [add_source_to_run(run) for run in runs]
airbnb_runs = get_runs_by_source(runs, "airbnb")
```

## Example: Adding Funda Support

1. **Already configured** in `constants.py` ✅
2. **Detection** works for runs with "funda" in the name ✅
3. **Filter** available in dropdown ✅
4. **UI** shows Funda icon and colors ✅

To activate:
- Create a run with "funda" in the name, OR
- Add `"source": "funda"` to config.json
- The dashboard will automatically show it with the 🏢 icon

## Scraper Integration

When creating a new scraper for a different source:

1. Add source to config when starting run:
   ```python
   config = {
       "source": DataSource.FUNDA,
       "search_params": {...},
   }
   ```

2. Use the same output structure:
   - Create `run_NAME_TIMESTAMP/` directory
   - Save `config.json` with source field
   - Save data to Excel/Parquet
   - Create `run_status.json`

3. The dashboard will automatically:
   - Detect the source
   - Apply correct styling
   - Enable filtering
   - Show appropriate icon

## Best Practices

1. **Always set source in config.json** when creating runs
2. **Use constants** instead of hardcoded values
3. **Test filtering** after adding a new source
4. **Update detection logic** if source names change
5. **Keep icons consistent** with Material Icons library

## Future Extensions

Easy to add:
- Source-specific metrics
- Source-specific export formats
- Source-specific validation rules
- Per-source rate limiting display
- Source comparison views

The modular architecture makes these additions straightforward!

