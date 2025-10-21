"""
Run Status Tracking System
Tracks scraping runs, their status, and logs
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import threading


class RunStatus(Enum):
    """Run status enum"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunTracker:
    """Tracks status and progress of scraping runs"""

    def __init__(self, run_dir: str):
        """
        Initialize run tracker

        Args:
            run_dir: Directory where run data will be stored
        """
        self.run_dir = run_dir
        self.status_file = os.path.join(run_dir, "run_status.json")
        self.log_file = os.path.join(run_dir, "run.log")
        self._lock = threading.Lock()

        # Ensure directory exists
        os.makedirs(run_dir, exist_ok=True)

        # Initialize status if not exists
        if not os.path.exists(self.status_file):
            self._save_status(
                {
                    "status": RunStatus.PENDING.value,
                    "created_at": datetime.now().isoformat(),
                    "started_at": None,
                    "completed_at": None,
                    "progress": {
                        "total_scans": 0,
                        "completed_scans": 0,
                        "failed_scans": 0,
                        "total_listings": 0,
                    },
                    "error": None,
                }
            )

    def _save_status(self, status_data: Dict[str, Any]):
        """Save status to JSON file"""
        with self._lock:
            with open(self.status_file, "w") as f:
                json.dump(status_data, f, indent=2)

    def _load_status(self) -> Dict[str, Any]:
        """Load status from JSON file"""
        with self._lock:
            if os.path.exists(self.status_file):
                with open(self.status_file, "r") as f:
                    return json.load(f)
        return {}

    def start(self, total_scans: int = 0):
        """Mark run as started"""
        status = self._load_status()
        status["status"] = RunStatus.RUNNING.value
        status["started_at"] = datetime.now().isoformat()
        status["progress"]["total_scans"] = total_scans
        self._save_status(status)
        self.log("🚀 Run started")

    def complete(self, total_listings: int = 0):
        """Mark run as completed"""
        status = self._load_status()
        status["status"] = RunStatus.COMPLETED.value
        status["completed_at"] = datetime.now().isoformat()
        status["progress"]["total_listings"] = total_listings
        self._save_status(status)
        self.log(f"✅ Run completed successfully - {total_listings} listings found")

    def fail(self, error: str):
        """Mark run as failed"""
        status = self._load_status()
        status["status"] = RunStatus.FAILED.value
        status["completed_at"] = datetime.now().isoformat()
        status["error"] = error
        self._save_status(status)
        self.log(f"❌ Run failed: {error}")

    def cancel(self):
        """Mark run as cancelled"""
        status = self._load_status()
        status["status"] = RunStatus.CANCELLED.value
        status["completed_at"] = datetime.now().isoformat()
        self._save_status(status)
        self.log("⚠️ Run cancelled")

    def update_progress(self, completed_scans: int = None, failed_scans: int = None):
        """Update progress counters"""
        status = self._load_status()
        if completed_scans is not None:
            status["progress"]["completed_scans"] = completed_scans
        if failed_scans is not None:
            status["progress"]["failed_scans"] = failed_scans
        self._save_status(status)

    def log(self, message: str):
        """Append message to log file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"

        with self._lock:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_line)

    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return self._load_status()

    def get_logs(self, tail: Optional[int] = None) -> str:
        """
        Get log content

        Args:
            tail: If specified, return only last N lines

        Returns:
            Log content as string
        """
        if not os.path.exists(self.log_file):
            return ""

        with open(self.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if tail and len(lines) > tail:
            lines = lines[-tail:]

        return "".join(lines)


def get_all_runs(data_dir: str = "data") -> list[Dict[str, Any]]:
    """
    Get all runs with their status

    Args:
        data_dir: Base data directory

    Returns:
        List of run info dictionaries
    """
    runs = []

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
                # If can't read status, mark as unknown
                runs.append(
                    {"run_name": run_name, "run_path": run_path, "status": "unknown"}
                )
        else:
            # Legacy run without status tracking - mark as completed
            # Try to infer if it's actually completed by checking for output files
            excel_files = []
            try:
                excel_files = [
                    f
                    for f in os.listdir(run_path)
                    if f.endswith(".xlsx") and not f.startswith("~$")
                ]
            except:
                pass

            if excel_files:
                # Has data files, so it's completed
                runs.append(
                    {
                        "run_name": run_name,
                        "run_path": run_path,
                        "status": "completed",
                        "created_at": run_name.split("_")[-2]
                        + " "
                        + run_name.split("_")[-1]
                        if "_" in run_name
                        else "",
                    }
                )
            else:
                # No data files, mark as legacy/unknown
                runs.append(
                    {"run_name": run_name, "run_path": run_path, "status": "legacy"}
                )

    # Sort by created_at (newest first)
    runs.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return runs
