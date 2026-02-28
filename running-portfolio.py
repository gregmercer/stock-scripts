import json
import argparse
from pathlib import Path
from datetime import datetime

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

def generate_portfolio_report(portfolio_history, rolling_data):
    """
    Generate a text report from portfolio history.
    Includes top 10 reference data for verification.
    """
    report_lines = []
    report_lines.append("=" * 100)
    report_lines.append("Running Portfolio Report")
    report_lines.append("Maintains Top 5 ETFs with Momentum-Based Rotation (by Geometric Average)")
    report_lines.append("=" * 100)
    report_lines.append("")
    report_lines.append("Rules:")
    report_lines.append("  - Start with top 5 from first period (ranked by geometric average)")
    report_lines.append("  - Keep holdings if they remain in top 10")
    report_lines.append("  - Drop holdings that fall out of top 10")
    report_lines.append("  - Fill empty slots with highest ranked ETFs not already held")
    report_lines.append("")
    report_lines.append("=" * 100)
    report_lines.append("")

    # Create summary table
    report_lines.append(f"{'Period':<30} | {'Portfolio (5 ETFs)':<40} | {'Changes'}")
    report_lines.append("-" * 100)

    for entry in portfolio_history:
        period_str = f"{entry['period_start']} - {entry['period_end']}"
        portfolio_str = ", ".join(entry['portfolio'])

        # Format changes
        changes_parts = []
        if entry['changes']['added']:
            changes_parts.append(f"+{', '.join(entry['changes']['added'])}")
        if entry['changes']['dropped']:
            changes_parts.append(f"-{', '.join(entry['changes']['dropped'])}")

        changes_str = " ".join(changes_parts) if changes_parts else "No changes"

        report_lines.append(f"{period_str:<30} | {portfolio_str:<40} | {changes_str}")

    report_lines.append("")
    report_lines.append("=" * 100)
    report_lines.append("Detailed Period Breakdown")
    report_lines.append("=" * 100)
    report_lines.append("")

    # Detailed breakdown
    for entry in portfolio_history:
        report_lines.append(f"Period: {entry['period_start']} to {entry['period_end']}")
        report_lines.append("-" * 100)
        report_lines.append(f"Portfolio: {', '.join(entry['portfolio'])}")

        if entry['changes']['added']:
            report_lines.append(f"Added:    {', '.join(entry['changes']['added'])}")
        if entry['changes']['dropped']:
            report_lines.append(f"Dropped:  {', '.join(entry['changes']['dropped'])}")
        if not entry['changes']['added'] and not entry['changes']['dropped']:
            report_lines.append("No changes from previous period")

        report_lines.append("")

    report_lines.append("=" * 100)
    report_lines.append("Top 10 Reference Data (for verification)")
    report_lines.append("=" * 100)
    report_lines.append("")

    # Add top 10 for each period
    for period in rolling_data:
        report_lines.append(f"Period: {period['period_start']} to {period['period_end']}")
        report_lines.append("-" * 100)
        report_lines.append(f"{'Rank':<6} {'Ticker':<8} {'Geo Avg %':<14} {'Weeks Positive':<16} {'Most Recent %':<16}")
        report_lines.append("-" * 100)

        for rank, etf in enumerate(period['top_10_etfs'], 1):
            ticker = etf['ticker']
            geo_avg = etf.get('geometric_avg', 0.0)
            weeks_pos = etf['weeks_positive']
            recent_change = etf['most_recent_change']

            report_lines.append(
                f"{rank:<6} {ticker:<8} {geo_avg:>12.2f}% {weeks_pos:<16} {recent_change:>14.2f}%"
            )

        report_lines.append("")

    return report_lines

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Generate running portfolio from rolling performance data'
    )
    parser.add_argument('-i', '--input', type=str, required=True,
                        help='Input JSON file path (e.g., output/rolling-performance-02-27-2026.json)')
    parser.add_argument('-o', '--output', action='store_true',
                        help='Write output to file in output/ directory')
    args = parser.parse_args()

    # Read input JSON file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{args.input}' not found")
        exit(1)

    with open(input_path, 'r') as f:
        rolling_data = json.load(f)

    # Calculate running portfolio
    portfolio_history = calculate_running_portfolio(rolling_data)

    # Generate report
    report_lines = generate_portfolio_report(portfolio_history, rolling_data)
    report_content = "\n".join(report_lines)

    # Output to file or console
    if args.output:
        # Create output directory if it doesn't exist
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Format filename using most recent period end date
        if portfolio_history:
            latest_date = portfolio_history[-1]['period_end']
            date_obj = datetime.strptime(latest_date, '%Y-%m-%d')
            filename = f"report-running-portfolio-{date_obj.strftime('%Y-%m-%d')}.txt"
        else:
            filename = f"report-running-portfolio-{datetime.now().strftime('%Y-%m-%d')}.txt"

        filepath = output_dir / filename

        with open(filepath, 'w') as f:
            f.write(report_content)

        print(f"Running portfolio report written to {filepath}")
    else:
        print(report_content)
