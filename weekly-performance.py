import yfinance as yf
import pandas as pd
import numpy as np
import argparse
from datetime import datetime, timedelta

def calculate_geometric_average(returns):
    """
    Calculate geometric average return from a series of percentage returns.
    Formula: [(1 + r1/100) * (1 + r2/100) * ... * (1 + rn/100)]^(1/n) - 1
    Returns percentage value.
    """
    if returns.isna().all():
        return np.nan

    # Filter out NaN values
    valid_returns = returns.dropna()
    if len(valid_returns) == 0:
        return np.nan

    # Convert percentage to decimal, add 1, multiply together
    product = np.prod(1 + valid_returns / 100)

    # Take nth root and subtract 1, convert back to percentage
    geo_avg = (product ** (1 / len(valid_returns)) - 1) * 100

    return geo_avg

def get_weekly_etf_performance(tickers, num_weeks=1, end_date=None):
    """
    Get weekly ETF performance data.

    Args:
        tickers: List of ETF ticker symbols
        num_weeks: Number of weeks to analyze (default: 1)
        end_date: End date for the analysis (YYYY-MM-DD format). If None, uses current date.
    """
    # Download enough historical data to cover the requested weeks
    # We need num_weeks + 1 data points to calculate num_weeks of changes
    period = f"{max(3, (num_weeks + 2) // 4)}mo"  # Ensure we have enough data

    # If end_date is provided, calculate start date and use date range
    if end_date:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        # Add a buffer to ensure we get enough data
        start_dt = end_dt - timedelta(weeks=num_weeks + 4)
        df = yf.download(tickers, start=start_dt.strftime('%Y-%m-%d'),
                        end=end_dt.strftime('%Y-%m-%d'), interval="1wk", progress=False)
    else:
        df = yf.download(tickers, period=period, interval="1wk", progress=False)

    # Use 'Adj Close' if available, otherwise fall back to 'Close'
    if 'Adj Close' in df.columns.levels[0]:
        data = df['Adj Close']
    else:
        data = df['Close']

    # Calculate percentage change for each week
    # pct_change() returns decimal (0.01), so we multiply by 100 for percentage (1.0%)
    pct_changes = data.pct_change() * 100

    # Get the last num_weeks of changes
    recent_changes = pct_changes.iloc[-num_weeks:]

    # Create a DataFrame with ETF tickers and multiple week columns
    results = pd.DataFrame({'ETF Ticker': data.columns})

    # Add each week as a column (most recent first)
    for i, (idx, row) in enumerate(recent_changes.iloc[::-1].iterrows()):
        week_label = f"Week {i+1}" if i > 0 else "Week 1 (Latest)"
        results[week_label] = row.values.round(2)

    # Count number of positive weeks
    week_columns = [col for col in results.columns if col.startswith('Week')]
    results['Weeks Positive'] = (results[week_columns] > 0).sum(axis=1)

    # Calculate geometric average for each ETF
    geo_averages = []
    for idx, row in results.iterrows():
        week_returns = row[week_columns].values
        geo_avg = calculate_geometric_average(pd.Series(week_returns))
        geo_averages.append(geo_avg)

    results['Geometric Avg'] = np.round(geo_averages, 2)

    # Reorder columns: ETF Ticker, Geometric Avg, Weeks Positive, then week columns
    cols = ['ETF Ticker', 'Geometric Avg', 'Weeks Positive'] + week_columns
    results = results[cols]

    # Sort by Geometric Average (descending)
    results = results.sort_values(by='Geometric Avg', ascending=False)

    return results

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
    parser = argparse.ArgumentParser(description='Display weekly ETF performance changes with geometric average')
    parser.add_argument('-w', '--weeks', type=int, default=10,
                        help='Number of weeks to display (default: 10)')
    parser.add_argument('-d', '--date', type=str, default=None,
                        help='End date for analysis in YYYY-MM-DD format (default: current date)')
    args = parser.parse_args()

    # Validate date format if provided
    if args.date:
        try:
            datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print("Error: Date must be in YYYY-MM-DD format")
            exit(1)

    # Get performance data
    performance = get_weekly_etf_performance(etf_list, num_weeks=args.weeks, end_date=args.date)

    # Set display options
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    # Display top 5 by Geometric Average FIRST
    print(f"--- Top 5 ETFs by Geometric Average ({args.weeks} weeks) ---")
    top_5 = performance.head(5)
    print(top_5.to_string(index=False))

    # Display legend for top 5
    print("\nTop 5 Legend:")
    for ticker in top_5['ETF Ticker']:
        print(f"{ticker:6} - {etf_names[ticker]}")

    # Display full results
    print(f"\n--- Full Weekly Performance Report ({args.weeks} weeks) ---")
    print(performance.to_string(index=False))

    # Display full legend
    print("\n--- Complete ETF Legend ---")
    for ticker in sorted(etf_list):
        print(f"{ticker:6} - {etf_names[ticker]}")
