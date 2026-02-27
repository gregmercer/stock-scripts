#!/usr/bin/env python3
"""
Master script to run the complete ETF momentum portfolio analysis.

This script orchestrates all the analysis steps in the correct order:
1. Fetch historical weekly ETF performance data (52 weeks)
2. Calculate rolling 10-week scores
3. Generate rolling performance report
4. Calculate running portfolio with momentum strategy
5. Calculate dollar returns with SPY benchmark comparison

Usage:
    python run-analysis.py
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_command(description, command):
    """Run a command and handle errors."""
    print("=" * 80)
    print(f"STEP: {description}")
    print("=" * 80)
    print(f"Running: {' '.join(command)}")
    print()

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=False,
            text=True
        )
        print(f"✓ {description} completed successfully")
        print()
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error in {description}")
        print(f"Command failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error in {description}: {e}")
        return False

def main():
    """Run the complete analysis pipeline."""
    print("=" * 80)
    print("ETF Momentum Portfolio Analysis Pipeline")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Create output directory if it doesn't exist
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Step 1: Fetch historical weekly performance data (52 weeks)
    if not run_command(
        "Fetching 52 weeks of historical ETF performance data",
        ["python", "historical-price-change.py", "-w", "52", "-o"]
    ):
        print("Pipeline failed at step 1")
        sys.exit(1)

    # Find the most recent weekly performance file
    weekly_files = sorted(output_dir.glob("weekly-performance-*.json"))
    if not weekly_files:
        print("✗ Error: No weekly performance file found")
        sys.exit(1)

    weekly_file = weekly_files[-1]
    print(f"Using weekly performance file: {weekly_file}")
    print()

    # Step 2: Calculate rolling 10-week scores
    if not run_command(
        "Calculating rolling 10-week scores for top 10 ETFs",
        ["python", "rolling-ten-weeks.py", "-i", str(weekly_file), "-o"]
    ):
        print("Pipeline failed at step 2")
        sys.exit(1)

    # Find the most recent rolling performance file
    rolling_files = sorted(output_dir.glob("rolling-performance-*.json"))
    if not rolling_files:
        print("✗ Error: No rolling performance file found")
        sys.exit(1)

    rolling_file = rolling_files[-1]
    print(f"Using rolling performance file: {rolling_file}")
    print()

    # Step 3: Generate rolling performance report
    if not run_command(
        "Generating rolling performance report (top 10 by period)",
        ["python", "rolling-ten-weeks-report.py", "-i", str(rolling_file), "-o"]
    ):
        print("Pipeline failed at step 3")
        sys.exit(1)

    # Step 4: Calculate running portfolio with momentum strategy
    if not run_command(
        "Calculating running portfolio with momentum strategy",
        ["python", "running-portfolio.py", "-i", str(rolling_file), "-o"]
    ):
        print("Pipeline failed at step 4")
        sys.exit(1)

    # Step 5: Calculate dollar returns with SPY benchmark
    if not run_command(
        "Calculating dollar returns with SPY benchmark comparison",
        ["python", "rolling-dollar-return.py", "-w", str(weekly_file), "-p", str(rolling_file), "-o"]
    ):
        print("Pipeline failed at step 5")
        sys.exit(1)

    # Summary
    print("=" * 80)
    print("ANALYSIS COMPLETE!")
    print("=" * 80)
    print()
    print("Generated files:")
    print(f"  • {weekly_file.name}")
    print(f"  • {rolling_file.name}")

    # List all generated reports
    report_files = sorted(output_dir.glob("report-*.txt"))
    for report_file in report_files:
        # Only show reports from this run (check if modified recently)
        print(f"  • {report_file.name}")

    print()
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Next steps:")
    print("  1. Review report-rolling-performance-*.txt for top 10 ETFs by period")
    print("  2. Review report-running-portfolio-*.txt for momentum strategy portfolio")
    print("  3. Review report-dollar-return-*.txt for dollar returns vs SPY benchmark")

if __name__ == "__main__":
    main()
