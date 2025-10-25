"""Utilities for run management"""

import os
from typing import Dict, Any, Optional
from dashboard.constants import DataSource


def detect_run_source(run: Dict[str, Any]) -> str:
    """
    Detect the data source of a run based on its metadata

    Args:
        run: Run dictionary with metadata

    Returns:
        Data source type (airbnb, funda, etc.)
    """
    # ONLY check config.json for explicit source field
    # This prevents misdetection based on gemeente names
    run_path = run.get("run_path")
    if run_path:
        config_path = os.path.join(run_path, "config.json")
        if os.path.exists(config_path):
            import json

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if "source" in config:
                        return config["source"]
            except Exception:
                pass

    # Default to airbnb for all existing runs
    # (new runs will have source in config.json)
    return DataSource.AIRBNB.value


def add_source_to_run(run: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add source field to run metadata if not present

    Args:
        run: Run dictionary

    Returns:
        Run dictionary with source field added
    """
    if "source" not in run:
        run["source"] = detect_run_source(run)
    return run


def get_runs_by_source(runs: list, source: Optional[str] = None) -> list:
    """
    Filter runs by data source

    Args:
        runs: List of run dictionaries
        source: Source to filter by (None = all runs)

    Returns:
        Filtered list of runs
    """
    if not source or source == "all":
        return runs

    return [run for run in runs if run.get("source", detect_run_source(run)) == source]
