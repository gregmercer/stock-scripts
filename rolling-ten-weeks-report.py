import json
import argparse
from pathlib import Path
from datetime import datetime

def generate_rolling_report(rolling_data):
    """
    Generate a text report from rolling performance data.
    Returns formatted report lines.
    """
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("Rolling 10-Week Performance Report")
    report_lines.append("Top 10 ETFs by Geometric Average")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Create table header
    report_lines.append(f"{'Period':<30} | {'Top 10 ETFs (by Geometric Average)'}")
    report_lines.append("-" * 80)

    # Process each rolling period
    for period in rolling_data:
        period_start = period['period_start']
        period_end = period['period_end']
        period_str = f"{period_start} - {period_end}"

        # Get top 10 tickers in order
        top_10_tickers = [etf['ticker'] for etf in period['top_10_etfs']]
        tickers_str = ", ".join(top_10_tickers)

        report_lines.append(f"{period_str:<30} | {tickers_str}")

    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("Detailed Breakdown")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Add detailed breakdown for each period
    for period in rolling_data:
        period_start = period['period_start']
        period_end = period['period_end']

        report_lines.append(f"Period: {period_start} to {period_end}")
        report_lines.append("-" * 80)

        # Table header for detailed view
        report_lines.append(f"{'Rank':<6} {'Ticker':<8} {'Geo Avg %':<14} {'Weeks Positive':<16} {'Most Recent %':<16}")
        report_lines.append("-" * 80)

        # Add each ETF
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
    parser = argparse.ArgumentParser(description='Generate text report from rolling performance JSON')
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

    # Generate report
    report_lines = generate_rolling_report(rolling_data)
    report_content = "\n".join(report_lines)

    # Output to file or console
    if args.output:
        # Create output directory if it doesn't exist
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Format filename using most recent period end date
        if rolling_data:
            latest_date = rolling_data[-1]['period_end']
            date_obj = datetime.strptime(latest_date, '%Y-%m-%d')
            filename = f"report-rolling-performance-{date_obj.strftime('%Y-%m-%d')}.txt"
        else:
            filename = f"report-rolling-performance-{datetime.now().strftime('%Y-%m-%d')}.txt"

        filepath = output_dir / filename

        with open(filepath, 'w') as f:
            f.write(report_content)

        print(f"Report written to {filepath}")
    else:
        print(report_content)
