# Stock Scripts

Automated ETF momentum portfolio analysis using geometric average rankings and Python.

## Overview

This repository implements a momentum-based ETF portfolio strategy that tracks weekly performance for 32 sector and industry ETFs. The system uses geometric average returns to rank ETFs and automatically rotates holdings to maintain top performers. A complete analysis pipeline runs automatically every Friday at 2pm PST via GitHub Actions.

## Features

- Tracks 32 ETFs across various sectors (technology, healthcare, energy, financials, etc.)
- Calculates geometric average returns for accurate performance measurement
- Implements rolling 10-week momentum strategy
- Maintains a 5-ETF portfolio with automatic rotation based on top performers
- Calculates dollar returns with SPY (S&P 500) benchmark comparison
- Generates comprehensive reports automatically
- Stores historical data and reports in the `output/` directory

## Ranking Methodology

The system uses **geometric average** (compound annual growth rate) to rank ETF performance, which provides a more accurate measure of returns over time compared to arithmetic averages:

**Formula:** `[(1 + r₁/100) × (1 + r₂/100) × ... × (1 + rₙ/100)]^(1/n) - 1`

This accounts for compounding effects and is the standard method for measuring investment returns across multiple periods.

## Portfolio Strategy

1. **Initial Selection:** Start with top 5 ETFs ranked by geometric average over 10 weeks
2. **Momentum Rotation:** Each week, evaluate all ETFs using rolling 10-week windows
3. **Hold or Rotate:** Keep holdings that remain in top 10; replace those that fall out
4. **Position Sizing:** Each position starts at $20,000 when purchased
5. **Benchmark:** Compare performance against SPY (S&P 500) with equal capital invested

## ETFs Tracked

The script monitors major SPDR and sector ETFs including:
- Sector funds (XLK, XLF, XLE, XLV, etc.)
- Industry-specific funds (XBI, XOP, KRE, XRT, etc.)
- Specialized funds (XNTK, XSD, XHB, etc.)

## Usage

### Complete Analysis Pipeline

Run the entire analysis with one command:

```bash
# Install dependencies
uv sync

# Run complete pipeline (generates all reports)
uv run run-analysis.py
```

This executes:
1. Fetches 52 weeks of historical ETF data
2. Calculates rolling 10-week geometric averages
3. Generates rolling performance report
4. Calculates running portfolio with momentum rotation
5. Computes dollar returns vs SPY benchmark

### Individual Scripts

#### Weekly Performance Report
```bash
# Default: 10 weeks from current date
uv run weekly-performance.py

# Specify number of weeks
uv run weekly-performance.py -w 5

# Historical analysis (10 weeks ending on specific date)
uv run weekly-performance.py -w 10 -d 2026-02-20
```

#### Rolling 10-Week Analysis
```bash
# Generate rolling performance data
uv run rolling-ten-weeks.py -i output/weekly-performance-2026-02-27.json -o

# Generate text report
uv run rolling-ten-weeks-report.py -i output/rolling-performance-2026-02-27.json -o
```

#### Portfolio Tracking
```bash
# Calculate running portfolio with momentum rotation
uv run running-portfolio.py -i output/rolling-performance-2026-02-27.json -o
```

#### Dollar Returns
```bash
# Calculate dollar returns vs SPY benchmark
uv run rolling-dollar-return.py -w output/weekly-performance-2026-02-27.json -p output/rolling-performance-2026-02-27.json -o
```

### Automated Reports

The GitHub Actions workflow runs automatically every Friday at 2pm PST and:
1. Generates weekly performance report (geometric average rankings)
2. Runs complete analysis pipeline
3. Saves all reports to `output/` directory:
   - `weekly-performance-report-YYYY-MM-DD.txt` - Top performers by geometric average
   - `weekly-performance-YYYY-MM-DD.json` - Raw weekly data
   - `rolling-performance-YYYY-MM-DD.json` - Rolling 10-week top 10 ETFs
   - `report-rolling-performance-YYYY-MM-DD.txt` - Rolling period breakdown
   - `report-running-portfolio-YYYY-MM-DD.txt` - Portfolio rotation history
   - `report-dollar-return-YYYY-MM-DD.txt` - Dollar returns vs SPY
4. Commits and pushes changes

You can also trigger the workflow manually from the Actions tab in GitHub.

## Report Format

### Weekly Performance Report
- Top 5 ETFs ranked by geometric average
- Full performance table with geometric average, weeks positive, and weekly changes
- Complete ETF legend

### Rolling Performance Report
- Top 10 ETFs for each rolling 10-week period
- Ranked by geometric average with weeks positive for reference
- Period-by-period breakdown

### Running Portfolio Report
- 5-ETF portfolio composition over time
- Tracks additions and drops based on momentum
- Shows which ETFs entered/exited top 10

### Dollar Return Report
- Weekly portfolio values and position tracking
- Capital invested vs returns
- SPY benchmark comparison with equal capital
- Outperformance metrics

## Requirements

- Python 3.10+
- uv (Python package manager)
- Dependencies: yfinance, pandas, numpy

## Key Scripts

- `weekly-performance.py` - Fetches and ranks ETFs by geometric average
- `historical-price-change.py` - Fetches historical weekly data (52 weeks)
- `rolling-ten-weeks.py` - Calculates rolling 10-week geometric averages
- `rolling-ten-weeks-report.py` - Generates rolling performance text report
- `running-portfolio.py` - Tracks 5-ETF momentum portfolio
- `rolling-dollar-return.py` - Calculates dollar returns vs SPY
- `run-analysis.py` - Master script that runs complete pipeline

## License

MIT
