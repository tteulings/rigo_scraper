"""Data loading and processing helpers for Dash dashboard"""

import os
import json
import time
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Union

# Import project paths from parent
PROJECT_ROOT = Path(
    __file__
).parent.parent.parent  # dashboard/dash_helpers -> dashboard -> project_root
GPKG_PATH = str(PROJECT_ROOT / "assets" / "BestuurlijkeGebieden_2025.gpkg")
DATA_DIR = str(PROJECT_ROOT / "outputs" / "data")


def load_gemeenten_list() -> List[str]:
    """Load list of gemeenten from GPKG file"""
    import geopandas as gpd

    try:
        if not os.path.exists(GPKG_PATH):
            return []
        gdf = gpd.read_file(GPKG_PATH, layer="gemeentegebied")
        return sorted(gdf["naam"].unique().tolist())
    except Exception:
        return []


def load_run_data(run_path: str, sheet_name: str = "Alle Data") -> pd.DataFrame:
    """
    Load run data with Parquet-first strategy for 10-100x speedup.
    Falls back to Excel if Parquet doesn't exist.

    Args:
        run_path: Path to the run directory
        sheet_name: Excel sheet name to load (if Excel fallback is needed)

    Returns:
        DataFrame with the run data
    """
    start = time.time()

    # Try Parquet first (10-100x faster!)
    parquet_path = os.path.join(run_path, "data.parquet")
    if os.path.exists(parquet_path):
        print(f"DEBUG: Loading Parquet from {parquet_path}")
        df = pd.read_parquet(parquet_path)
        load_time = time.time() - start
        print(f"DEBUG: Parquet loaded {len(df)} rows in {load_time:.2f}s")
        return df

    # Fallback to Excel (slower)
    excel_files = [
        f
        for f in os.listdir(run_path)
        if f.endswith(".xlsx") and not f.startswith("~$")
    ]

    if not excel_files:
        raise FileNotFoundError(f"No data files found in {run_path}")

    excel_path = os.path.join(run_path, excel_files[0])
    print(
        f"DEBUG: Excel fallback {excel_path} (Run convert_excel_to_parquet.py for 10x speedup!)"
    )

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, engine="openpyxl")
    except Exception:
        # Try alternate sheet names
        try:
            alt_sheet = "All Data" if sheet_name == "Alle Data" else "Alle Data"
            df = pd.read_excel(excel_path, sheet_name=alt_sheet, engine="openpyxl")
        except Exception:
            # Last resort: load first sheet
            df = pd.read_excel(excel_path, sheet_name=0, engine="openpyxl")

    load_time = time.time() - start
    print(f"DEBUG: Excel loaded {len(df)} rows in {load_time:.2f}s")
    return df


def load_run_preview(run: Dict[str, Any]) -> Dict[str, Any]:
    """Load preview information for a run (for cards in overview)"""
    # Try to get listings count from run metadata (fast)
    listings_count: Union[int, str] = "-"
    if "progress" in run and "total_listings" in run.get("progress", {}):
        listings_count = run["progress"]["total_listings"]

    # If not in metadata, check if Excel exists
    if listings_count == "-":
        excel_files = (
            [
                f
                for f in os.listdir(run["run_path"])
                if f.endswith(".xlsx") and not f.startswith("~$")
            ]
            if os.path.exists(run["run_path"])
            else []
        )
        excel_path = (
            os.path.join(run["run_path"], excel_files[0]) if excel_files else None
        )

        # Try Parquet first (faster), then Excel
        parquet_path = os.path.join(run["run_path"], "data.parquet")
        if os.path.exists(parquet_path):
            try:
                df = pd.read_parquet(parquet_path, columns=["room_id"])
                listings_count = int(df["room_id"].nunique())
            except Exception:
                listings_count = "-"
        elif excel_path:
            # Fallback to Excel (slower)
            try:
                try:
                    df = pd.read_excel(
                        excel_path, sheet_name="Alle Data", usecols=["room_id"]
                    )
                except Exception:
                    df = pd.read_excel(
                        excel_path, sheet_name="All Data", usecols=["room_id"]
                    )
                listings_count = int(df["room_id"].nunique())
            except Exception:
                listings_count = "-"
    else:
        # Still need to check if Excel exists for download link
        excel_files = (
            [
                f
                for f in os.listdir(run["run_path"])
                if f.endswith(".xlsx") and not f.startswith("~$")
            ]
            if os.path.exists(run["run_path"])
            else []
        )
        excel_path = (
            os.path.join(run["run_path"], excel_files[0]) if excel_files else None
        )

    # Config info
    gemeenten_str, period = "Onbekend", "-"
    config_path = os.path.join(run["run_path"], "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            gemeenten = config.get("gemeenten", [])
            gemeenten_str = ", ".join(gemeenten) if gemeenten else "Onbekend"
            ps, pe = config.get("period_start", ""), config.get("period_end", "")
            period = f"{ps} - {pe}" if ps and pe else "-"
        except Exception:
            pass

    timestamp = run.get("created_at", "")[:16] if run.get("created_at") else "-"
    status = run.get("status", "unknown")

    return {
        "gemeenten": gemeenten_str,
        "period": period,
        "listings": listings_count,
        "timestamp": timestamp,
        "status": status,
        "excel_path": excel_path,
    }


# Import get_all_runs from run_tracker or provide fallback
try:
    from src.core.run_tracker import get_all_runs
except Exception:

    def get_all_runs(data_dir: str = "data") -> List[Dict[str, Any]]:
        """Fallback implementation to get all runs"""
        runs: List[Dict[str, Any]] = []
        if not os.path.exists(data_dir):
            return runs
        for run_name in os.listdir(data_dir):
            run_path = os.path.join(data_dir, run_name)
            if not os.path.isdir(run_path) or not run_name.startswith("run_"):
                continue
            status_file = os.path.join(run_path, "run_status.json")
            if os.path.exists(status_file):
                try:
                    with open(status_file, "r") as f:
                        status = json.load(f)
                    runs.append({"run_name": run_name, "run_path": run_path, **status})
                except Exception:
                    runs.append(
                        {
                            "run_name": run_name,
                            "run_path": run_path,
                            "status": "unknown",
                        }
                    )
            else:
                # Legacy: infer completed if excel exists
                excel_files = [
                    f
                    for f in os.listdir(run_path)
                    if f.endswith(".xlsx") and not f.startswith("~$")
                ]
                if excel_files:
                    runs.append(
                        {
                            "run_name": run_name,
                            "run_path": run_path,
                            "status": "completed",
                        }
                    )
                else:
                    runs.append(
                        {"run_name": run_name, "run_path": run_path, "status": "legacy"}
                    )
        runs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return runs
