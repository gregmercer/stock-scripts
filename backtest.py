#!/usr/bin/env python3
"""
Run the ETF momentum strategy over a single historical calendar year.

The strategy needs 10 weeks of history to rank ETFs, so a backtest of year Y is
seeded from the 10 weeks ending on the last Friday of Y-1. Positions are entered
at that close, which means every week of Y is live performance and the result is
a clean calendar-year return.

Output goes to backtests/<year>/ and mirrors the live pipeline:

    weekly-performance-<last week>.json        raw weekly price changes
    rolling-performance-<last week>.json       rolling 10-week rankings
    report-rolling-performance-<last week>.txt top 10 by period
    report-running-portfolio-<last week>.txt   holdings and rotations
    report-dollar-return-<last week>.txt       dollar returns vs SPY

Usage:
    python backtest.py --year 2025
    python backtest.py --year 2019 --year 2020 --year 2021
    python backtest.py --from-year 2019 --to-year 2025
"""

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

LOOKBACK_WEEKS = 10

# Returned when a year has no completed weeks yet, which happens when the
# weekly job first runs after a new year starts. Distinct from a failure.
SKIPPED = object()

# The universe is fully listed from this point on. Earlier years still run, but
# with fewer than 32 ETFs to choose from, so results are not directly comparable.
FULL_UNIVERSE_FROM = 2019
EARLIEST_USABLE_YEAR = 2012


def fridays_in_year(year):
    """Every Friday falling inside the calendar year."""
    d = date(year, 1, 1)
    d += timedelta(days=(4 - d.weekday()) % 7)  # advance to the first Friday
    out = []
    while d.year == year:
        out.append(d)
        d += timedelta(days=7)
    return out


def week_bounds(year):
    """
    Work out the exact weeks a backtest of `year` needs.

    Returns (fetch_start, fetch_end, first_week, last_week) as dates, where
    first_week is the earliest lookback week and last_week is the final Friday
    of the year.
    """
    year_fridays = fridays_in_year(year)
    first_of_year = year_fridays[0]
    last_week = year_fridays[-1]

    # The 10 lookback weeks end on the last Friday before the year starts
    first_week = first_of_year - timedelta(weeks=LOOKBACK_WEEKS)

    # Fetch with a buffer on both sides: pct_change() consumes the first bar,
    # and yfinance's end bound excludes the final week.
    fetch_start = first_week - timedelta(weeks=3)
    fetch_end = last_week + timedelta(weeks=2)
    return fetch_start, fetch_end, first_week, last_week


def run(description, command):
    """Run a pipeline step, surfacing failures."""
    print(f"  → {description}")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    FAILED: {' '.join(command)}", file=sys.stderr)
        print(result.stdout[-2000:], file=sys.stderr)
        print(result.stderr[-2000:], file=sys.stderr)
        return False
    return True


def slice_to_backtest_window(path, first_week, last_week):
    """
    Trim the fetched data to exactly the lookback weeks plus the target year,
    and report how much of the universe was actually available.
    """
    weekly = json.loads(path.read_text())

    # Cap at the most recent completed week: for a year still in progress
    # yfinance returns a partial bar for the current week, which would show up
    # as a real weekly change measured over only part of the week.
    lo = first_week.isoformat()
    hi = min(last_week, date.today() - timedelta(days=1)).isoformat()
    kept = [w for w in weekly if lo <= w['week_ending'] <= hi]

    if not kept:
        raise SystemExit(f"No weekly data in range {lo}..{hi} - nothing to backtest")

    path.write_text(json.dumps(kept, indent=2))

    coverage = [len(w['etfs']) for w in kept]

    # Fewer than five ranked ETFs cannot fill the portfolio, and the run would
    # otherwise report a meaningless -100% rather than failing.
    if min(coverage) < 5:
        thin = next(w['week_ending'] for w in kept if len(w['etfs']) < 5)
        raise SystemExit(
            f"Only {min(coverage)} ETFs have data for week {thin} - too few to run a backtest. "
            "This usually means the price download failed or the year predates most of the universe."
        )

    return kept, min(coverage), max(coverage)


def backtest_year(year, repo_root):
    print(f"\n{'=' * 70}\nBacktest {year}\n{'=' * 70}")

    fetch_start, fetch_end, first_week, last_week = week_bounds(year)
    out_dir = repo_root / "backtests" / str(year)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Start clean. The year still in progress is re-run every week, and the
    # pipeline scripts name their output after the last week of data, so
    # anything left behind would linger under an out-of-date name.
    for old in out_dir.iterdir():
        if old.is_file():
            old.unlink()

    print(f"  Lookback weeks : {first_week} .. {first_week + timedelta(weeks=LOOKBACK_WEEKS - 1)}")
    print(f"  Output         : {out_dir.relative_to(repo_root)}/")

    if not run("fetching weekly price changes", [
        "uv", "run", "historical-price-change.py",
        "--start", fetch_start.isoformat(),
        "--end", fetch_end.isoformat(),
        "-o", "--output-dir", str(out_dir),
    ]):
        return None

    produced = sorted(out_dir.glob("weekly-performance-*.json"))
    if not produced:
        print("  FAILED: fetcher produced no file", file=sys.stderr)
        return None
    raw_file = produced[-1]
    for stale in produced[:-1]:
        stale.unlink()

    kept, min_cov, max_cov = slice_to_backtest_window(raw_file, first_week, last_week)

    # The pipeline scripts name their output after the last week of data. Inside
    # backtests/<year>/ that suffix is redundant, and for the year in progress it
    # would change every week, so strip it. Each report states its own coverage.
    actual_last = kept[-1]['week_ending']
    weekly_file = out_dir / "weekly-performance.json"
    raw_file.rename(weekly_file)

    # Early in a new year there are lookback weeks but nothing to measure yet.
    # Writing a report here would show a meaningless flat 0.00% return.
    if not [w for w in kept if w['week_ending'] >= f"{year}-01-01"]:
        print(f"  SKIPPED: {year} has no completed weeks yet")
        for leftover in out_dir.iterdir():
            if leftover.is_file():
                leftover.unlink()
        out_dir.rmdir()
        return SKIPPED

    covered_from = kept[LOOKBACK_WEEKS]['week_ending'] if len(kept) > LOOKBACK_WEEKS else actual_last
    print(f"  Backtest weeks : {covered_from} .. {actual_last}")
    print(f"  {len(kept)} weeks, {min_cov}-{max_cov} of 32 ETFs available per week")
    if actual_last < last_week.isoformat():
        print(f"  NOTE: {year} is incomplete; covers through {actual_last} rather than {last_week}")
    if min_cov < 32:
        print(f"  NOTE: {year} ran on a partial universe; not comparable to {FULL_UNIVERSE_FROM}+ results")

    rolling_file = out_dir / "rolling-performance.json"
    dollar_file = out_dir / "report-dollar-return.txt"

    # Each step writes a file named after the last week of data; rename it to
    # the stable name once written.
    steps = [
        ("computing rolling 10-week rankings", rolling_file,
         ["uv", "run", "rolling-ten-weeks.py", "-i", str(weekly_file), "-o", "--output-dir", str(out_dir)]),
        ("writing rolling performance report", out_dir / "report-rolling-performance.txt",
         ["uv", "run", "rolling-ten-weeks-report.py", "-i", str(rolling_file), "-o", "--output-dir", str(out_dir)]),
        ("writing running portfolio report", out_dir / "report-running-portfolio.txt",
         ["uv", "run", "running-portfolio.py", "-i", str(rolling_file), "-o", "--output-dir", str(out_dir)]),
        ("writing dollar return report", dollar_file,
         ["uv", "run", "rolling-dollar-return.py", "-w", str(weekly_file), "-p", str(rolling_file),
          "-o", "--output-dir", str(out_dir)]),
    ]
    for description, final_path, command in steps:
        if not run(description, command):
            return None
        dated = final_path.with_name(f"{final_path.stem}-{actual_last}{final_path.suffix}")
        if not dated.exists():
            print(f"  FAILED: expected {dated.name} from '{description}'", file=sys.stderr)
            return None
        dated.rename(final_path)

    return summarise(dollar_file, year, min_cov, actual_last)


def summarise(report_path, year, min_cov, last_week):
    """Pull the headline figures out of a finished dollar-return report."""
    import re

    text = report_path.read_text()
    portfolio = text.split("Portfolio Performance:")[1].split("S&P 500 Benchmark")[0]
    spy = text.split("S&P 500 Benchmark")[1].split("Outperformance")[0]

    def field(section, label):
        m = re.search(rf"^\s+{label}:\s+\$?\s*(-?[\d,]+\.\d\d)%?\s*$", section, re.M)
        return float(m.group(1).replace(",", "")) if m else float("nan")

    return {
        "year": year,
        "portfolio_return": field(portfolio, "True Return"),
        "spy_return": field(spy, "Return"),
        "capital_invested": field(portfolio, "Total Capital Invested"),
        "universe": min_cov,
        "last_week": last_week,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Backtest the ETF momentum strategy over one or more calendar years"
    )
    parser.add_argument("--year", type=int, action="append", default=None,
                        help="Year to backtest; repeat for several (e.g. --year 2024 --year 2025)")
    parser.add_argument("--from-year", type=int, default=None,
                        help="Start of an inclusive range of years")
    parser.add_argument("--to-year", type=int, default=None,
                        help="End of an inclusive range of years")
    args = parser.parse_args()

    years = list(args.year or [])
    if args.from_year or args.to_year:
        if not (args.from_year and args.to_year):
            parser.error("--from-year and --to-year must be used together")
        if args.from_year > args.to_year:
            parser.error("--from-year must not be later than --to-year")
        years += list(range(args.from_year, args.to_year + 1))
    if not years:
        parser.error("specify --year, or --from-year with --to-year")

    this_year = datetime.now().year
    years = sorted(set(years))
    for y in years:
        if y < EARLIEST_USABLE_YEAR:
            parser.error(f"{y} is too early - too few ETFs had listed; {EARLIEST_USABLE_YEAR} is the earliest supported")
        if y > this_year:
            parser.error(f"{y} is in the future")
        if y == this_year:
            print(f"NOTE: {y} is still in progress; its backtest covers only the weeks so far")

    repo_root = Path(__file__).resolve().parent
    outcomes = [backtest_year(y, repo_root) for y in years]
    results = [r for r in outcomes if r is not None and r is not SKIPPED]

    if results:
        print(f"\n{'=' * 70}\nSummary\n{'=' * 70}")
        print(f"{'Year':<8} {'Strategy':>10} {'SPY':>10} {'Outperform':>12} {'Universe':>10}")
        print("-" * 70)
        for r in results:
            flag = "" if r["universe"] == 32 else "  *"
            partial = "" if r["last_week"].startswith(str(r["year"])) and \
                r["last_week"] >= f"{r['year']}-12-24" else f"  (through {r['last_week']})"
            print(f"{r['year']:<8} {r['portfolio_return']:>9.2f}% {r['spy_return']:>9.2f}% "
                  f"{r['portfolio_return'] - r['spy_return']:>11.2f}% {r['universe']:>7}/32{flag}{partial}")
        if any(r["universe"] < 32 for r in results):
            print("\n  * partial universe - not directly comparable to full-universe years")

    failed = sum(1 for r in outcomes if r is None)
    if failed:
        print(f"\n{failed} year(s) failed", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
