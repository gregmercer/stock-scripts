import json
import argparse
from pathlib import Path
from datetime import datetime

def calculate_rolling_ten_week_scores(weekly_data):
    """
    Calculate rolling 10-week scores for each ETF.
    Returns a list of rolling period objects with top 10 ETFs.
    """
    # Need at least 10 weeks of data
    if len(weekly_data) < 10:
        raise ValueError(f"Need at least 10 weeks of data, got {len(weekly_data)}")

    rolling_results = []

    # Calculate for each possible 10-week window
    for i in range(len(weekly_data) - 9):
        window = weekly_data[i:i+10]

        # Get the date range for this window
        start_date = window[0]['week_ending']
        end_date = window[-1]['week_ending']

        # Build a dictionary to track each ETF's performance
        etf_scores = {}

        # Process each week in the window
        for week in window:
            week_ending = week['week_ending']
            for etf in week['etfs']:
                ticker = etf['ticker']
                change_percent = etf['change_percent']

                if ticker not in etf_scores:
                    etf_scores[ticker] = {
                        'ticker': ticker,
                        'weeks_positive': 0,
                        'weekly_changes': []
                    }

                etf_scores[ticker]['weekly_changes'].append({
                    'change': change_percent,
                    'week_ending': week_ending
                })
                if change_percent > 0:
                    etf_scores[ticker]['weeks_positive'] += 1

        # Convert to list and sort by weeks_positive, then by most recent week
        etf_list = []
        for ticker, data in etf_scores.items():
            etf_list.append({
                'ticker': ticker,
                'weeks_positive': data['weeks_positive'],
                'most_recent_change': data['weekly_changes'][-1]['change'],
                'weekly_changes': data['weekly_changes']
            })

        # Sort by weeks_positive (descending), then by most_recent_change (descending)
        etf_list.sort(key=lambda x: (x['weeks_positive'], x['most_recent_change']), reverse=True)

        # Get top 10
        top_10 = etf_list[:10]

        # Format the result for this rolling period
        rolling_results.append({
            'period_start': start_date,
            'period_end': end_date,
            'top_10_etfs': [
                {
                    'ticker': etf['ticker'],
                    'weeks_positive': etf['weeks_positive'],
                    'most_recent_change': round(etf['most_recent_change'], 2),
                    'weekly_changes': [
                        {
                            'change': round(w['change'], 2),
                            'week_ending': w['week_ending']
                        }
                        for w in etf['weekly_changes']
                    ]
                }
                for etf in top_10
            ]
        })

    return rolling_results

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Calculate rolling 10-week scores from weekly performance JSON')
    parser.add_argument('-i', '--input', type=str, required=True,
                        help='Input JSON file path (e.g., output/weekly-performance-02-27-2026.json)')
    parser.add_argument('-o', '--output', action='store_true',
                        help='Write output to file in output/ directory')
    args = parser.parse_args()

    # Read input JSON file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{args.input}' not found")
        exit(1)

    with open(input_path, 'r') as f:
        weekly_data = json.load(f)

    # Calculate rolling scores
    try:
        rolling_scores = calculate_rolling_ten_week_scores(weekly_data)
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)

    # Convert to JSON
    json_output = json.dumps(rolling_scores, indent=2)

    # Output to file or console
    if args.output:
        # Create output directory if it doesn't exist
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Format filename using most recent period end date
        if rolling_scores:
            latest_date = rolling_scores[-1]['period_end']
            date_obj = datetime.strptime(latest_date, '%Y-%m-%d')
            filename = f"rolling-performance-{date_obj.strftime('%Y-%m-%d')}.json"
        else:
            filename = f"rolling-performance-{datetime.now().strftime('%Y-%m-%d')}.json"

        filepath = output_dir / filename

        with open(filepath, 'w') as f:
            f.write(json_output)

        print(f"Rolling performance data written to {filepath}")
    else:
        print(json_output)
