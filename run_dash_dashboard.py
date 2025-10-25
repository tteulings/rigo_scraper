#!/usr/bin/env python3
"""
Launch script for the Dash dashboard
"""

import subprocess
import sys


def ensure_dash():
    try:
        import dash  # type: ignore  # noqa: F401
    except Exception:
        print("Installing Dash (dash>=2.17.0)...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "dash>=2.17.0"], check=False
        )


def main():
    print("Dash dashboard starten op http://localhost:8050 ...")
    ensure_dash()
    subprocess.run([sys.executable, "dash_dashboard_nl.py"])  # no-interactive


if __name__ == "__main__":
    main()
