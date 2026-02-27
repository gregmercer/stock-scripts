import json
import argparse
from pathlib import Path
from datetime import datetime
import yfinance as yf

INITIAL_POSITION_VALUE = 20000
INITIAL_PORTFOLIO_VALUE = 100000

def fetch_sp500_returns(start_date, end_date):
    """
    Fetch S&P 500 returns for the given date range using SPY ETF.
    Returns weekly percentage changes.
    """
    try:
        from datetime import datetime, timedelta
        import pandas as pd

        print(f"Downloading SPY data from {start_date} to {end_date}...")

        # Download SPY data
        spy_data = yf.download('SPY', start=start_date, end=end_date, interval='1wk', progress=False)

        print(f"SPY data shape: {spy_data.shape}")

        if spy_data.empty:
            print("ERROR: SPY data is empty")
            return {}

        # Handle both single and multi-ticker column formats
        if 'Adj Close' in spy_data.columns:
            if isinstance(spy_data.columns, pd.MultiIndex):
                prices = spy_data['Adj Close']['SPY']
            else:
                prices = spy_data['Adj Close']
        else:
            if isinstance(spy_data.columns, pd.MultiIndex):
                prices = spy_data['Close']['SPY']
            else:
                prices = spy_data['Close']

        print(f"First few SPY prices:")
        print(prices.head())

        # Calculate percentage changes
        pct_changes = prices.pct_change() * 100

        # Build lookup by week ending date
        sp500_lookup = {}
        for idx, change in pct_changes.items():
            date_str = idx.strftime('%Y-%m-%d')
            sp500_lookup[date_str] = float(change) if not pd.isna(change) else 0.0

            # Also add Friday of that week
            days_until_friday = (4 - idx.weekday()) % 7
            friday = idx + timedelta(days=days_until_friday)
            friday_str = friday.strftime('%Y-%m-%d')
            if friday_str != date_str:
                sp500_lookup[friday_str] = float(change) if not pd.isna(change) else 0.0

        print(f"Loaded SPY data for {len(sp500_lookup)} dates")
        print(f"First 5 SPY dates: {list(sp500_lookup.keys())[:5]}")
        return sp500_lookup
    except Exception as e:
        print(f"ERROR: Could not fetch SPY data: {e}")
        import traceback
        traceback.print_exc()
        return {}




def calculate_running_portfolio(rolling_data):
    """
    Calculate a running portfolio that maintains top performers across periods.

    Rules:
    1. Start with top 5 from first period
    2. For each subsequent period:
       - Keep current holdings if they're still in top 10
       - Drop any that fall out of top 10
       - Fill empty slots with highest ranked ETFs from top 10 that aren't already held
    """
    if not rolling_data:
        return []

    portfolio_history = []

    # Initialize with top 5 from first period
    first_period = rolling_data[0]
    current_portfolio = [etf['ticker'] for etf in first_period['top_10_etfs'][:5]]

    portfolio_history.append({
        'period_start': first_period['period_start'],
        'period_end': first_period['period_end'],
        'portfolio': current_portfolio.copy(),
        'changes': {
            'added': current_portfolio.copy(),
            'dropped': []
        }
    })

    # Process each subsequent period
    for period in rolling_data[1:]:
        top_10_tickers = [etf['ticker'] for etf in period['top_10_etfs']]

        # Track changes
        added = []
        dropped = []

        # Check which current holdings are still in top 10
        new_portfolio = []
        for ticker in current_portfolio:
            if ticker in top_10_tickers:
                new_portfolio.append(ticker)
            else:
                dropped.append(ticker)

        # Fill empty slots with highest ranked from top 10 that aren't already held
        slots_to_fill = 5 - len(new_portfolio)
        for ticker in top_10_tickers:
            if slots_to_fill == 0:
                break
            if ticker not in new_portfolio:
                new_portfolio.append(ticker)
                added.append(ticker)
                slots_to_fill -= 1

        # Update current portfolio
        current_portfolio = new_portfolio

        portfolio_history.append({
            'period_start': period['period_start'],
            'period_end': period['period_end'],
            'portfolio': current_portfolio.copy(),
            'changes': {
                'added': added,
                'dropped': dropped
            }
        })

    return portfolio_history

def calculate_portfolio_returns(weekly_data, portfolio_history, sp500_lookup):
    """
    Calculate dollar returns for the running portfolio.

    Each position starts at $20,000 when bought.
    Portfolio starts at $100,000 (5 positions × $20k).
    Track capital invested, cash from sales, and capital additions.
    Compare to S&P 500 benchmark.
    """
    # Build a lookup for weekly changes by ticker and date
    weekly_changes_lookup = {}
    for week in weekly_data:
        week_ending = week['week_ending']
        for etf in week['etfs']:
            ticker = etf['ticker']
            if ticker not in weekly_changes_lookup:
                weekly_changes_lookup[ticker] = {}
            weekly_changes_lookup[ticker][week_ending] = etf['change_percent']

    # Track position values
    position_values = {}
    weekly_portfolio_values = []

    # Track capital
    total_capital_invested = INITIAL_PORTFOLIO_VALUE
    cash_available = 0  # Cash from sales not yet reinvested

    # Initialize first portfolio
    first_entry = portfolio_history[0]
    for ticker in first_entry['portfolio']:
        position_values[ticker] = {
            'value': INITIAL_POSITION_VALUE,
            'entry_date': first_entry['period_end'],
            'entry_value': INITIAL_POSITION_VALUE
        }

    # Get all unique week ending dates from the weekly data, sorted
    all_weeks = sorted(set(week['week_ending'] for week in weekly_data))

    # Find the starting week (first period end date)
    start_week = first_entry['period_end']
    start_index = all_weeks.index(start_week) if start_week in all_weeks else 0

    # Track which portfolio period we're in
    period_index = 0
    current_portfolio_tickers = set(first_entry['portfolio'])

    # Track S&P 500 benchmark with equal capital additions
    sp500_value = INITIAL_PORTFOLIO_VALUE
    sp500_total_capital_invested = INITIAL_PORTFOLIO_VALUE

    # Process each week from start
    for week_idx in range(start_index, len(all_weeks)):
        week_ending = all_weeks[week_idx]
        capital_added_this_week = 0
        sp500_capital_added_this_week = 0

        # Check if we need to update portfolio (new period starts)
        if period_index < len(portfolio_history) - 1:
            next_period = portfolio_history[period_index + 1]
            if week_ending == next_period['period_end']:
                # Update portfolio for new period
                period_index += 1
                new_portfolio_tickers = set(next_period['portfolio'])

                # Handle drops - sell positions and add to cash
                for ticker in current_portfolio_tickers - new_portfolio_tickers:
                    if ticker in position_values:
                        sale_value = position_values[ticker]['value']
                        cash_available += sale_value
                        del position_values[ticker]

                # Handle adds - buy new positions at $20k
                for ticker in new_portfolio_tickers - current_portfolio_tickers:
                    # Check if we have enough cash
                    if cash_available >= INITIAL_POSITION_VALUE:
                        # Use cash from sales
                        cash_available -= INITIAL_POSITION_VALUE
                    else:
                        # Need to add capital
                        capital_needed = INITIAL_POSITION_VALUE - cash_available
                        total_capital_invested += capital_needed
                        capital_added_this_week += capital_needed

                        # Add same amount to S&P 500 benchmark
                        sp500_total_capital_invested += capital_needed
                        sp500_capital_added_this_week += capital_needed
                        sp500_value += capital_needed

                        cash_available = 0

                    position_values[ticker] = {
                        'value': INITIAL_POSITION_VALUE,
                        'entry_date': week_ending,
                        'entry_value': INITIAL_POSITION_VALUE
                    }

                current_portfolio_tickers = new_portfolio_tickers

        # Apply weekly changes to all held positions
        week_total = 0
        position_details = []

        for ticker in current_portfolio_tickers:
            if ticker in position_values:
                # Get the change for this week
                if ticker in weekly_changes_lookup and week_ending in weekly_changes_lookup[ticker]:
                    change_pct = weekly_changes_lookup[ticker][week_ending]
                    old_value = position_values[ticker]['value']
                    new_value = old_value * (1 + change_pct / 100)
                    position_values[ticker]['value'] = new_value

                    position_details.append({
                        'ticker': ticker,
                        'value': new_value,
                        'change_pct': change_pct,
                        'entry_date': position_values[ticker]['entry_date'],
                        'entry_value': position_values[ticker]['entry_value'],
                        'gain_loss': new_value - position_values[ticker]['entry_value']
                    })

                    week_total += new_value
                else:
                    # No data for this week, keep previous value
                    week_total += position_values[ticker]['value']
                    position_details.append({
                        'ticker': ticker,
                        'value': position_values[ticker]['value'],
                        'change_pct': 0,
                        'entry_date': position_values[ticker]['entry_date'],
                        'entry_value': position_values[ticker]['entry_value'],
                        'gain_loss': position_values[ticker]['value'] - position_values[ticker]['entry_value']
                    })

        # Calculate true performance based on capital invested
        net_gain_loss = week_total + cash_available - total_capital_invested
        true_return_pct = (net_gain_loss / total_capital_invested) * 100

        # Update S&P 500 benchmark (apply weekly return AFTER capital additions)
        sp500_change_pct = sp500_lookup.get(week_ending, None)
        if sp500_change_pct is not None and sp500_change_pct == sp500_change_pct:  # Check for NaN
            sp500_value = sp500_value * (1 + sp500_change_pct / 100)
        elif sp500_change_pct is None:
            # No SPY data for this week - likely future date or market holiday
            pass

        sp500_net_gain_loss = sp500_value - sp500_total_capital_invested
        sp500_return_pct = (sp500_net_gain_loss / sp500_total_capital_invested) * 100

        weekly_portfolio_values.append({
            'week_ending': week_ending,
            'total_value': week_total,
            'positions': position_details,
            'cash_available': cash_available,
            'total_capital_invested': total_capital_invested,
            'capital_added_this_week': capital_added_this_week,
            'net_gain_loss': net_gain_loss,
            'true_return_pct': true_return_pct,
            'sp500_value': sp500_value,
            'sp500_total_capital_invested': sp500_total_capital_invested,
            'sp500_capital_added_this_week': sp500_capital_added_this_week,
            'sp500_net_gain_loss': sp500_net_gain_loss,
            'sp500_return_pct': sp500_return_pct
        })

    return weekly_portfolio_values


def generate_dollar_return_report(weekly_portfolio_values):
    """
    Generate a text report showing dollar returns over time.
    """
    report_lines = []
    report_lines.append("=" * 140)
    report_lines.append("Rolling Portfolio Dollar Return Report")
    report_lines.append(f"Initial Portfolio Value: ${INITIAL_PORTFOLIO_VALUE:,.2f}")
    report_lines.append(f"Initial Position Size: ${INITIAL_POSITION_VALUE:,.2f} per position")
    report_lines.append("=" * 140)
    report_lines.append("")

    if not weekly_portfolio_values:
        report_lines.append("No data available")
        return report_lines

    # Summary statistics
    final_week = weekly_portfolio_values[-1]
    final_value = final_week['total_value']
    final_cash = final_week['cash_available']
    total_capital_invested = final_week['total_capital_invested']
    capital_added = total_capital_invested - INITIAL_PORTFOLIO_VALUE
    net_gain_loss = final_week['net_gain_loss']
    true_return_pct = final_week['true_return_pct']
    sp500_final_value = final_week['sp500_value']
    sp500_total_capital_invested = final_week['sp500_total_capital_invested']
    sp500_capital_added = sp500_total_capital_invested - INITIAL_PORTFOLIO_VALUE
    sp500_net_gain_loss = final_week['sp500_net_gain_loss']
    sp500_return_pct = final_week['sp500_return_pct']
    outperformance = true_return_pct - sp500_return_pct

    report_lines.append("SUMMARY")
    report_lines.append("-" * 140)
    report_lines.append("Portfolio Performance:")
    report_lines.append(f"  Initial Capital:        ${INITIAL_PORTFOLIO_VALUE:>12,.2f}")
    report_lines.append(f"  Capital Added:          ${capital_added:>12,.2f}")
    report_lines.append(f"  Total Capital Invested: ${total_capital_invested:>12,.2f}")
    report_lines.append(f"  Final Portfolio Value:  ${final_value:>12,.2f}")
    report_lines.append(f"  Cash Available:         ${final_cash:>12,.2f}")
    report_lines.append(f"  Total Assets:           ${final_value + final_cash:>12,.2f}")
    report_lines.append(f"  Net Gain/Loss:          ${net_gain_loss:>12,.2f}")
    report_lines.append(f"  True Return:            {true_return_pct:>12.2f}%")
    report_lines.append("")
    report_lines.append("S&P 500 Benchmark (Equal Capital Invested):")
    report_lines.append(f"  Initial Capital:        ${INITIAL_PORTFOLIO_VALUE:>12,.2f}")
    report_lines.append(f"  Capital Added:          ${sp500_capital_added:>12,.2f}")
    report_lines.append(f"  Total Capital Invested: ${sp500_total_capital_invested:>12,.2f}")
    report_lines.append(f"  Final Value:            ${sp500_final_value:>12,.2f}")
    report_lines.append(f"  Net Gain/Loss:          ${sp500_net_gain_loss:>12,.2f}")
    report_lines.append(f"  Return:                 {sp500_return_pct:>12.2f}%")
    report_lines.append("")
    report_lines.append(f"Outperformance:           {outperformance:>12.2f}%")
    report_lines.append(f"Number of Weeks:          {len(weekly_portfolio_values):>12}")
    report_lines.append("")

    # Weekly portfolio values table
    report_lines.append("=" * 180)
    report_lines.append("Weekly Portfolio Values vs SPY (S&P 500)")
    report_lines.append("=" * 180)
    report_lines.append("")
    report_lines.append(
        f"{'Week':<12} {'Portfolio':<16} {'Port Return':<13} {'Port Capital':<16} "
        f"{'VOO Value':<16} {'VOO Return':<13} {'VOO Capital':<16} {'Outperform':<13}"
    )
    report_lines.append("-" * 180)

    for week_data in weekly_portfolio_values:
        week_ending = week_data['week_ending']
        total_value = week_data['total_value']
        true_return = week_data['true_return_pct']
        capital_invested = week_data['total_capital_invested']

        voo_value = week_data['sp500_value']
        voo_return = week_data['sp500_return_pct']
        voo_capital = week_data['sp500_total_capital_invested']
        outperform = true_return - voo_return

        report_lines.append(
            f"{week_ending:<12} ${total_value:>13,.2f} {true_return:>11.2f}% ${capital_invested:>13,.2f} "
            f"${voo_value:>13,.2f} {voo_return:>11.2f}% ${voo_capital:>13,.2f} {outperform:>11.2f}%"
        )

    report_lines.append("")
    report_lines.append("=" * 140)
    report_lines.append("Detailed Position Tracking")
    report_lines.append("=" * 140)
    report_lines.append("")

    # Detailed position tracking for each week
    for week_data in weekly_portfolio_values:
        report_lines.append(f"Week Ending: {week_data['week_ending']}")
        report_lines.append(
            f"Portfolio Value: ${week_data['total_value']:,.2f} | "
            f"Cash: ${week_data['cash_available']:,.2f} | "
            f"Capital Invested: ${week_data['total_capital_invested']:,.2f}"
        )
        if week_data['capital_added_this_week'] > 0:
            report_lines.append(f"*** Capital Added This Week: ${week_data['capital_added_this_week']:,.2f} ***")
        report_lines.append("-" * 140)
        report_lines.append(
            f"{'Ticker':<8} {'Current Value':<18} {'Week Change %':<16} "
            f"{'Entry Date':<15} {'Entry Value':<18} {'Position Gain/Loss':<20}"
        )
        report_lines.append("-" * 140)

        for pos in week_data['positions']:
            report_lines.append(
                f"{pos['ticker']:<8} ${pos['value']:>15,.2f} {pos['change_pct']:>14.2f}% "
                f"{pos['entry_date']:<15} ${pos['entry_value']:>15,.2f} ${pos['gain_loss']:>17,.2f}"
            )

        report_lines.append("")

    return report_lines


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Calculate dollar returns for running portfolio'
    )
    parser.add_argument('-w', '--weekly', type=str, required=True,
                        help='Weekly performance JSON file (e.g., output/weekly-performance-02-27-2026.json)')
    parser.add_argument('-p', '--portfolio', type=str, required=True,
                        help='Running portfolio JSON file (need to create this output from running-portfolio.py)')
    parser.add_argument('-o', '--output', action='store_true',
                        help='Write output to file in output/ directory')
    args = parser.parse_args()

    # Read weekly performance JSON
    weekly_path = Path(args.weekly)
    if not weekly_path.exists():
        print(f"Error: Weekly performance file '{args.weekly}' not found")
        exit(1)

    with open(weekly_path, 'r') as f:
        weekly_data = json.load(f)

    # Read portfolio history JSON
    portfolio_path = Path(args.portfolio)
    if not portfolio_path.exists():
        print(f"Error: Portfolio file '{args.portfolio}' not found")
        print("Note: You need to modify running-portfolio.py to output JSON, or provide the rolling-performance.json file")
        exit(1)

    with open(portfolio_path, 'r') as f:
        portfolio_data = json.load(f)

    # Check if this is rolling-performance data (has top_10_etfs) or portfolio history
    # For now, we'll need to calculate portfolio history from rolling-performance
    if portfolio_data and 'top_10_etfs' in portfolio_data[0]:
        # This is rolling-performance data, need to calculate portfolio history
        portfolio_history = calculate_running_portfolio(portfolio_data)
    else:
        portfolio_history = portfolio_data

    # Fetch S&P 500 data for comparison
    if weekly_data:
        from datetime import datetime
        start_date = weekly_data[0]['week_ending']
        end_date = weekly_data[-1]['week_ending']
        today = datetime.now().strftime('%Y-%m-%d')

        print(f"Fetching SPY data from {start_date} to {end_date}...")
        print(f"Today's date: {today}")

        # If end date is in the future, use today instead
        if end_date > today:
            print(f"WARNING: End date {end_date} is in the future. Using today ({today}) instead.")
            end_date = today

        sp500_lookup = fetch_sp500_returns(start_date, end_date)
        print(f"Sample SPY dates: {list(sp500_lookup.keys())[:5]}")
        print(f"Sample weekly dates: {[w['week_ending'] for w in weekly_data[:5]]}")
    else:
        sp500_lookup = {}

    # Calculate returns
    weekly_portfolio_values = calculate_portfolio_returns(weekly_data, portfolio_history, sp500_lookup)

    # Generate report
    report_lines = generate_dollar_return_report(weekly_portfolio_values)
    report_content = "\n".join(report_lines)

    # Output to file or console
    if args.output:
        # Create output directory if it doesn't exist
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Format filename using most recent week
        if weekly_portfolio_values:
            latest_date = weekly_portfolio_values[-1]['week_ending']
            date_obj = datetime.strptime(latest_date, '%Y-%m-%d')
            filename = f"report-dollar-return-{date_obj.strftime('%Y-%m-%d')}.txt"
        else:
            filename = f"report-dollar-return-{datetime.now().strftime('%Y-%m-%d')}.txt"

        filepath = output_dir / filename

        with open(filepath, 'w') as f:
            f.write(report_content)

        print(f"Dollar return report written to {filepath}")
    else:
        print(report_content)
