#!/usr/bin/env python3
"""
Launch script for the Streamlit dashboard
"""

import subprocess
import sys
import os


def check_dependencies():
    """Check if required packages are installed, and install if missing"""
    missing_packages = []

    try:
        import streamlit
    except ImportError:
        missing_packages.append("streamlit>=1.28.0")

    try:
        import plotly
    except ImportError:
        missing_packages.append("plotly>=5.17.0")

    try:
        import streamlit_folium
    except ImportError:
        missing_packages.append("streamlit-folium>=0.15.0")

    if missing_packages:
        print(f"❌ Missing dependencies: {', '.join(missing_packages)}")
        print("\n📦 Attempting to install missing packages...")

        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install"] + missing_packages,
                check=True,
                capture_output=False,
            )
            print("\n✅ Dependencies installed successfully!")
            print("🔄 Please restart the script to use the newly installed packages.\n")
            return False
        except subprocess.CalledProcessError:
            print("\n❌ Failed to install dependencies automatically.")
            print("📦 Please install manually using:")
            print("   pip install -r requirements.txt")
            return False

    return True


def main():
    """Launch the Streamlit dashboard"""
    print("🚀 Airbnb Scraper Dashboard starten...")
    print("=" * 60)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Check if GeoPackage exists
    gpkg_path = "assets/BestuurlijkeGebieden_2025.gpkg"
    if not os.path.exists(gpkg_path):
        print(f"\n⚠️  Waarschuwing: {gpkg_path} niet gevonden")
        print("   Dashboard werkt maar gemeente selectie niet beschikbaar")
        print()

    # Launch Streamlit (Dutch version)
    print("\n✓ Dashboard starten...")
    print("✓ Browser opent op http://localhost:8501")
    print("\nDruk Ctrl+C om te stoppen\n")
    print("=" * 60)

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "streamlit_dashboard_nl.py",
                "--server.headless=false",
            ]
        )
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard gestopt")
        sys.exit(0)


if __name__ == "__main__":
    main()
