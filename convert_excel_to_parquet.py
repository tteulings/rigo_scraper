#!/usr/bin/env python3
"""
Convert existing Excel files to Parquet format for faster loading.
Run this once on existing runs, then the scraper will save both formats going forward.
"""

import os
import pandas as pd
from pathlib import Path
from tqdm import tqdm

def convert_run_to_parquet(run_path: Path) -> bool:
    """Convert a single run's Excel file to Parquet"""
    try:
        # Find Excel file
        excel_files = [f for f in os.listdir(run_path) if f.endswith('.xlsx') and not f.startswith('~$')]
        
        if not excel_files:
            print(f"  [!] No Excel file found in {run_path.name}")
            return False
        
        excel_path = run_path / excel_files[0]
        parquet_path = run_path / "data.parquet"
        
        # Skip if parquet already exists and is newer than Excel
        if parquet_path.exists():
            if parquet_path.stat().st_mtime > excel_path.stat().st_mtime:
                print(f"  [OK] Parquet already up-to-date: {run_path.name}")
                return True
        
        print(f"  Converting: {run_path.name}")
        print(f"    Excel: {excel_path.name} ({excel_path.stat().st_size / 1024 / 1024:.2f} MB)")
        
        # Read Excel
        try:
            df = pd.read_excel(excel_path, sheet_name="Alle Data", engine="openpyxl")
        except Exception:
            try:
                df = pd.read_excel(excel_path, sheet_name="All Data", engine="openpyxl")
            except Exception:
                df = pd.read_excel(excel_path, sheet_name=0, engine="openpyxl")
        
        # Save as Parquet with compression
        df.to_parquet(
            parquet_path,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        
        parquet_size = parquet_path.stat().st_size / 1024 / 1024
        excel_size = excel_path.stat().st_size / 1024 / 1024
        savings = (1 - parquet_size / excel_size) * 100
        
        print(f"    Parquet: data.parquet ({parquet_size:.2f} MB)")
        print(f"    Savings: {savings:.1f}% smaller")
        
        # Test read speed
        import time
        
        start = time.time()
        _ = pd.read_parquet(parquet_path)
        parquet_time = time.time() - start
        
        start = time.time()
        _ = pd.read_excel(excel_path, sheet_name="Alle Data" if "Alle Data" in pd.ExcelFile(excel_path).sheet_names else "All Data")
        excel_time = time.time() - start
        
        speedup = excel_time / parquet_time
        print(f"    Speed: {speedup:.1f}x faster ({parquet_time:.2f}s vs {excel_time:.2f}s)")
        
        return True
        
    except Exception as e:
        print(f"  [ERROR] Converting {run_path.name}: {e}")
        return False

def main():
    """Convert all runs in outputs/data"""
    data_dir = Path("outputs/data")
    
    if not data_dir.exists():
        print(f"[ERROR] Data directory not found: {data_dir}")
        return
    
    # Find all run directories
    run_dirs = [d for d in data_dir.iterdir() if d.is_dir() and d.name.startswith('run_')]
    
    if not run_dirs:
        print("No run directories found")
        return
    
    print(f"Found {len(run_dirs)} runs to convert\n")
    
    success_count = 0
    for run_dir in tqdm(run_dirs, desc="Converting runs"):
        if convert_run_to_parquet(run_dir):
            success_count += 1
        print()  # Empty line between runs
    
    print(f"\n[SUCCESS] Converted {success_count}/{len(run_dirs)} runs successfully")
    print(f"\nNext steps:")
    print(f"1. Dashboard will now load Parquet files (10x faster!)")
    print(f"2. Excel files are kept for manual export/inspection")
    print(f"3. Future scrapes will automatically create both formats")

if __name__ == "__main__":
    main()

