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
- Backtests the strategy over past calendar years into the `backtests/` directory

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

### Backtesting a Historical Year

Run the same strategy over a past calendar year:

```bash
# One year
uv run backtest.py --year 2025

# Several specific years
uv run backtest.py --year 2019 --year 2022

# An inclusive range
uv run backtest.py --from-year 2019 --to-year 2025
```

Results are written to `backtests/<year>/` using the same five file types as the
live pipeline, and a summary table of strategy vs SPY is printed at the end.
Filenames carry no date inside these folders, since the folder is the year and
the current year is rewritten every week; each report states its own coverage.

The current year is refreshed automatically by the Friday job, so
`backtests/<this year>/` always reflects the year so far. Completed years are
left alone once written.

**Results, 2019 onward.**

| Year  | Strategy |     SPY | Outperform |
|-------|---------:|--------:|-----------:|
| 2019  |   30.02% |  32.78% |     -2.76% |
| 2020  |   29.21% |  18.63% |    +10.58% |
| 2021  |   24.87% |  30.43% |     -5.56% |
| 2022  |   12.32% | -17.91% |    +30.23% |
| 2023  |   39.34% |  26.18% |    +13.16% |
| 2024  |   21.42% |  26.72% |     -5.30% |
| 2025  |   31.55% |  17.38% |    +14.17% |
| 2026* |   32.80% |   8.79% |    +24.01% |

\* 2026 is still in progress, covering 2026-01-02 through 2026-07-31. The Friday
job extends it each week.

Beats SPY in 4 of the 7 completed years, and is well ahead so far in 2026. The
pattern is coherent for a momentum strategy: it lags in steady bull years (2019,
2021, 2024) and shines when leadership rotates hard. 2022 is +30 points, staying
positive through a -18% market.

**Results, 2012-2018.** These years run on a partial universe (see below), so
they are not directly comparable to the table above.

| Year | Strategy |     SPY | Outperform | Universe |
|------|---------:|--------:|-----------:|---------:|
| 2012 |   17.91% |  14.05% |     +3.86% |    30/32 |
| 2013 |   34.85% |  33.94% |     +0.91% |    30/32 |
| 2014 |   22.13% |  15.63% |     +6.50% |    30/32 |
| 2015 |    1.81% |   0.74% |     +1.07% |    30/32 |
| 2016 |   29.82% |  11.57% |    +18.25% |    31/32 |
| 2017 |   21.76% |  21.71% |     +0.05% |    31/32 |
| 2018 |    7.28% |  -5.40% |    +12.68% |    31/32 |

Beats SPY in all seven, though four of the margins are under two points. The two
large wins are again rotational years: 2016 and 2018, the latter staying
positive through a -5% market. Across 2012-2025 the strategy beats SPY in 11 of
14 years.

Treat the clean sweep with some caution. A narrower universe means less
competition for the five slots, and these years sit further from the live
record, so they lean harder on the assumption that the current ETF list is a
reasonable one to have picked at the time.

As a check on the benchmark, the SPY column was compared against SPY's actual
adjusted-close return over each backtest window. The eight years where the
strategy needed no extra capital match to 0.00 points. The other six differ in
proportion to the capital added, which is expected: the benchmark receives the
same capital at the same time as the portfolio, making it a money-weighted
return rather than a pure buy-and-hold one.

**How the year is framed.** The strategy needs 10 weeks of history to rank ETFs,
so a backtest of year Y is seeded from the 10 weeks ending on the last Friday of
Y-1. Positions are entered at that close, which makes every week of Y live
performance and the result a clean calendar-year return. The dollar-return
report therefore opens with a flat entry row dated to the prior December.

Because both the portfolio and the SPY benchmark are measured over that same
window, the SPY figure will be close to, but not exactly, a quoted calendar-year
return.

**Universe coverage.** The 32-ETF list is fully listed only from June 2018, so
2019 onward is fully comparable. Earlier years run with fewer ETFs and are
flagged in the summary; 2012 is the earliest supported. An ETF must have a price
for all 10 weeks of a window to be ranked, so a fund that lists partway through
cannot win on a short post-launch streak.

Note that the ETF list is today's list, so any backtest uses a universe chosen
with present-day knowledge.

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
4. Refreshes `backtests/<current year>/` with the year-to-date backtest. This
   step is allowed to fail without holding back the weekly reports, and is
   skipped in early January until the new year has a completed week.
5. Commits and pushes changes

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
- `backtest.py` - Runs the strategy over one or more historical calendar years

## License

MIT
