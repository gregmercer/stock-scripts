# Stock Scripts

Automated ETF performance tracking and reporting using Python and GitHub Actions.

## Overview

This repository tracks weekly performance changes for a curated list of sector and industry ETFs. A GitHub Actions workflow runs automatically every Friday at 2pm PST to generate a performance report and commit it to the repository.

## Features

- Tracks 32 ETFs across various sectors (technology, healthcare, energy, financials, etc.)
- Calculates weekly percentage changes over configurable time periods
- Identifies top performers based on number of positive weeks
- Generates timestamped reports automatically
- Stores historical reports in the `output/` directory

## ETFs Tracked

The script monitors major SPDR and sector ETFs including:
- Sector funds (XLK, XLF, XLE, XLV, etc.)
- Industry-specific funds (XBI, XOP, KRE, XRT, etc.)
- Specialized funds (XNTK, XSD, XHB, etc.)

## Usage

### Run Locally

```bash
# Install dependencies
uv sync

# Run with default settings (10 weeks)
uv run weekly-price-change.py

# Specify number of weeks
uv run weekly-price-change.py -w 5
```

### Automated Reports

The GitHub Actions workflow runs automatically every Friday at 2pm PST and:
1. Fetches latest ETF data
2. Generates a report file named `report-MM-DD-YYYY.txt`
3. Saves it to the `output/` directory
4. Commits and pushes the changes

You can also trigger the workflow manually from the Actions tab in GitHub.

## Report Format

Each report includes:
1. Top 5 ETFs by number of positive weeks (with legend)
2. Full performance table for all ETFs
3. Complete ETF legend with full names

## Requirements

- Python 3.10+
- uv (Python package manager)
- Dependencies: yfinance, pandas

## License

MIT
