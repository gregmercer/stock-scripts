import yfinance as yf
import pandas as pd
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

def select_price_frame(df):
    """
    Pick the price frame to work from.

    yfinance auto-adjusts by default and returns those prices under 'Close',
    omitting 'Adj Close' entirely. But when a ticker has no data at all for the
    requested range it still emits an 'Adj Close' group containing only that
    failed ticker, every value NaN. Naively preferring 'Adj Close' therefore
    blanks the whole dataset - which is what a backtest spanning an ETF's
    inception does. Choose whichever group actually carries the most tickers,
    keeping the old 'Adj Close' preference when both are fully populated.
    """
    available = df.columns.levels[0]
    best_frame, best_usable = None, -1
    for level in ('Adj Close', 'Close'):
        if level not in available:
            continue
        frame = df[level]
        usable = sum(1 for t in frame.columns if not frame[t].isna().all())
        if usable > best_usable:
            best_frame, best_usable = frame, usable
    return best_frame


def get_weekly_etf_performance(tickers, num_weeks=10, weeks_ago=0, start=None, end=None):
    """
    Fetch weekly ETF performance.

    By default the window is anchored to today (num_weeks back, optionally
    offset by weeks_ago). Passing start/end instead fetches an explicit date
    range, which is what backtests need so their results stay reproducible
    rather than shifting as time passes.
    """
    if start or end:
        df = yf.download(tickers, start=start, end=end, interval="1wk", progress=False)
    else:
        # Download enough historical data to cover the requested weeks plus offset
        total_weeks_needed = num_weeks + weeks_ago + 4
        period = f"{max(12, (total_weeks_needed // 4))}mo"
        df = yf.download(tickers, period=period, interval="1wk", progress=False)

    data = select_price_frame(df)

    # Calculate percentage change for each week
    pct_changes = data.pct_change() * 100

    if start or end:
        # Keep the whole fetched range; the caller slices to the weeks it wants.
        # The first row is dropped because pct_change() leaves it undefined.
        recent_changes = pct_changes.iloc[1:]
        recent_data = data.iloc[1:]
    else:
        # Get the window starting from weeks_ago
        if weeks_ago > 0:
            end_idx = -(weeks_ago + 1)
            start_idx = end_idx - num_weeks + 1
        else:
            end_idx = None
            start_idx = -num_weeks

        recent_changes = pct_changes.iloc[start_idx:end_idx]
        recent_data = data.iloc[start_idx:end_idx]

    # Build list of objects for each week (Friday close)
    weekly_records = []
    for idx, row in recent_changes.iterrows():
        # yfinance weekly data is indexed to Monday, adjust to Friday (add 4 days)
        friday_date = idx + timedelta(days=4)
        date_str = friday_date.strftime('%Y-%m-%d')
        week_data = {
            'week_ending': date_str,
            'etfs': []
        }

        for ticker in data.columns:
            pct_change = row[ticker]
            price = recent_data.loc[idx, ticker]

            if pd.notna(pct_change) and pd.notna(price):
                week_data['etfs'].append({
                    'ticker': ticker,
                    'price': round(float(price), 2),
                    'change_percent': round(float(pct_change), 2)
                })

        # Sort ETFs by change_percent descending
        week_data['etfs'].sort(key=lambda x: x['change_percent'], reverse=True)
        weekly_records.append(week_data)

    return weekly_records

# List of ETFs to track
etf_list = [
    "XRT", "XSW", "XTN", "XNTK", "XPH", "XOP", "XES", "KRE", "KCE", "KIE",
    "XHS", "XHE", "KBE", "RWR", "XBI", "XLB", "XLI", "XLRE", "XLU", "XLK",
    "XLF", "XLG", "XAR", "XLC", "XLP", "XLV", "XME", "XSD", "XTL", "XLY",
    "XHB", "XLE"
]

# ETF names for legend
etf_names = {
    "XRT": "SPDR S&P Retail ETF",
    "XSW": "SPDR S&P Software & Services ETF",
    "XTN": "SPDR S&P Transportation ETF",
    "XNTK": "SPDR NYSE Technology ETF",
    "XPH": "SPDR S&P Pharmaceuticals ETF",
    "XOP": "SPDR S&P Oil & Gas Exploration & Production ETF",
    "XES": "SPDR S&P Oil & Gas Equipment & Services ETF",
    "KRE": "SPDR S&P Regional Banking ETF",
    "KCE": "SPDR S&P Capital Markets ETF",
    "KIE": "SPDR S&P Insurance ETF",
    "XHS": "SPDR S&P Health Care Services ETF",
    "XHE": "SPDR S&P Health Care Equipment ETF",
    "KBE": "SPDR S&P Bank ETF",
    "RWR": "SPDR Dow Jones REIT ETF",
    "XBI": "SPDR S&P Biotech ETF",
    "XLB": "Materials Select Sector SPDR Fund",
    "XLI": "Industrial Select Sector SPDR Fund",
    "XLRE": "Real Estate Select Sector SPDR Fund",
    "XLU": "Utilities Select Sector SPDR Fund",
    "XLK": "Technology Select Sector SPDR Fund",
    "XLF": "Financial Select Sector SPDR Fund",
    "XLG": "Invesco S&P 500 Top 50 ETF",
    "XAR": "SPDR S&P Aerospace & Defense ETF",
    "XLC": "Communication Services Select Sector SPDR Fund",
    "XLP": "Consumer Staples Select Sector SPDR Fund",
    "XLV": "Health Care Select Sector SPDR Fund",
    "XME": "SPDR S&P Metals & Mining ETF",
    "XSD": "SPDR S&P Semiconductor ETF",
    "XTL": "SPDR S&P Telecom ETF",
    "XLY": "Consumer Discretionary Select Sector SPDR Fund",
    "XHB": "SPDR S&P Homebuilders ETF",
    "XLE": "Energy Select Sector SPDR Fund"
}

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Generate weekly ETF performance data as JSON')
    parser.add_argument('-w', '--weeks', type=int, default=10,
                        help='Number of weeks to include (default: 10)')
    parser.add_argument('--ago', type=int, default=0,
                        help='Start the window N weeks ago (default: 0 = most recent)')
    parser.add_argument('--start', type=str, default=None,
                        help='Fetch an explicit date range starting YYYY-MM-DD (overrides -w/--ago)')
    parser.add_argument('--end', type=str, default=None,
                        help='Fetch an explicit date range ending YYYY-MM-DD (overrides -w/--ago)')
    parser.add_argument('-o', '--output', action='store_true',
                        help='Write output to file in the output directory')
    parser.add_argument('--output-dir', type=str, default='output',
                        help='Directory to write output to (default: output)')
    args = parser.parse_args()

    # Get performance data
    weekly_records = get_weekly_etf_performance(
        etf_list,
        num_weeks=args.weeks,
        weeks_ago=args.ago,
        start=args.start,
        end=args.end
    )

    # Convert to JSON
    json_output = json.dumps(weekly_records, indent=2)

    # Output to file or console
    if args.output:
        # Create output directory if it doesn't exist
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Format filename using most recent week ending date
        if weekly_records:
            latest_date = weekly_records[-1]['week_ending']
            date_obj = datetime.strptime(latest_date, '%Y-%m-%d')
            filename = f"weekly-performance-{date_obj.strftime('%Y-%m-%d')}.json"
        else:
            filename = f"weekly-performance-{datetime.now().strftime('%Y-%m-%d')}.json"

        filepath = output_dir / filename

        with open(filepath, 'w') as f:
            f.write(json_output)

        print(f"JSON data written to {filepath}")
    else:
        print(json_output)
