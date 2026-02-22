import yfinance as yf
import pandas as pd
import argparse

def get_weekly_etf_performance(tickers, num_weeks=1):
    # Download enough historical data to cover the requested weeks
    # We need num_weeks + 1 data points to calculate num_weeks of changes
    period = f"{max(3, (num_weeks + 2) // 4)}mo"  # Ensure we have enough data
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

    # Reorder columns to put Weeks Positive after ETF Ticker
    cols = ['ETF Ticker', 'Weeks Positive'] + week_columns
    results = results[cols]

    # Sort by the most recent week (Week 1)
    results = results.sort_values(by='Week 1 (Latest)', ascending=False)

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
    parser = argparse.ArgumentParser(description='Display weekly ETF performance changes')
    parser.add_argument('-w', '--weeks', type=int, default=10,
                        help='Number of weeks to display (default: 10)')
    args = parser.parse_args()

    # Get performance data
    performance = get_weekly_etf_performance(etf_list, num_weeks=args.weeks)

    # Set display options
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    # Display top 5 by Weeks Positive FIRST
    print(f"--- Top 5 ETFs by Weeks Positive ({args.weeks} weeks) ---")
    top_5 = performance.sort_values(by='Weeks Positive', ascending=False).head(5)
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
