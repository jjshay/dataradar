#!/usr/bin/env python3
"""
DateDriven - Sync Google Sheet to eBay Pricing
Reads pricing rules from a Google Sheet and updates eBay prices
"""

import os
import json
import csv
import pickle
from datetime import datetime
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

os.chdir('/Users/johnshay/DateDriven')

# Your Google Sheet ID (get from URL after /d/)
# Example: https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
SHEET_ID = os.environ.get('DATEDRIVEN_SHEET_ID', '')


def get_credentials():
    """Get Google credentials"""
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds
    return None


def read_rules_from_sheet(sheet_id):
    """Read pricing rules from Google Sheet"""
    creds = get_credentials()
    if not creds:
        print("No Google credentials found")
        return []

    service = build('sheets', 'v4', credentials=creds)

    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range='A2:L100'  # Skip header row
        ).execute()

        rows = result.get('values', [])
        return parse_rows(rows)

    except Exception as e:
        print(f"Error reading sheet: {e}")
        return []


def read_rules_from_csv(filename='pricing_control.csv'):
    """Read pricing rules from local CSV file"""
    rules = []

    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('ENABLED', '').upper() != 'TRUE':
                continue

            rules.append({
                'enabled': True,
                'category': row.get('CATEGORY', ''),
                'artist': row.get('ARTIST/TYPE', ''),
                'event': row.get('EVENT', ''),
                'event_date': row.get('EVENT_DATE', ''),
                'start_date': row.get('WINDOW_START', ''),
                'end_date': row.get('WINDOW_END', ''),
                'duration': int(row.get('DURATION_DAYS', 0) or 0),
                'tier': row.get('TIER', 'MINOR'),
                'increase_percent': int(row.get('PRICE_CHANGE_%', 0) or 0),
                'keywords': [k.strip() for k in row.get('KEYWORDS', '').split(',')],
                'notes': row.get('NOTES', '')
            })

    return rules


def parse_rows(rows):
    """Parse spreadsheet rows into rules"""
    rules = []

    for row in rows:
        if len(row) < 10:
            continue

        enabled = row[0].upper() == 'TRUE' if row[0] else False
        if not enabled:
            continue

        rules.append({
            'enabled': True,
            'category': row[1] if len(row) > 1 else '',
            'artist': row[2] if len(row) > 2 else '',
            'event': row[3] if len(row) > 3 else '',
            'event_date': row[4] if len(row) > 4 else '',
            'start_date': row[5] if len(row) > 5 else '',
            'end_date': row[6] if len(row) > 6 else '',
            'duration': int(row[7]) if len(row) > 7 and row[7] else 0,
            'tier': row[8] if len(row) > 8 else 'MINOR',
            'increase_percent': int(row[9]) if len(row) > 9 and row[9] else 0,
            'keywords': [k.strip() for k in row[10].split(',')] if len(row) > 10 and row[10] else [],
            'notes': row[11] if len(row) > 11 else ''
        })

    return rules


def filter_active_rules(rules):
    """Filter rules to only those in active window"""
    today = datetime.now().strftime('%Y-%m-%d')
    active = []

    for rule in rules:
        start = rule.get('start_date', '')
        end = rule.get('end_date', '')

        if start and end and start <= today <= end:
            active.append(rule)

    return active


def export_to_json(rules, filename='pricing_rules.json'):
    """Export rules to JSON for ebay_auto_pricing.py"""
    json_rules = []

    for r in rules:
        json_rules.append({
            'item': r['artist'],
            'keywords': r['keywords'],
            'event': r['event'],
            'tier': r['tier'],
            'increase_percent': r['increase_percent'],
            'start_date': r['start_date'],
            'end_date': r['end_date'],
            'category': r['category']
        })

    with open(filename, 'w') as f:
        json.dump(json_rules, f, indent=2)

    return json_rules


def main():
    print("=" * 60)
    print("DATEDRIVEN - Sync Sheet to eBay Pricing")
    print("=" * 60)

    # Try Google Sheet first, fall back to CSV
    rules = []

    if SHEET_ID:
        print(f"\nReading from Google Sheet: {SHEET_ID}")
        rules = read_rules_from_sheet(SHEET_ID)
    else:
        print("\nNo SHEET_ID set, reading from local CSV...")
        rules = read_rules_from_csv()

    print(f"Total rules loaded: {len(rules)}")

    # Filter to active windows
    active_rules = filter_active_rules(rules)
    print(f"Rules in active window: {len(active_rules)}")

    # Export to JSON
    export_to_json(active_rules)
    print(f"\n✅ Exported {len(active_rules)} active rules to pricing_rules.json")

    # Show summary
    print("\n" + "-" * 60)
    print("ACTIVE PRICING WINDOWS:")
    print("-" * 60)

    for r in active_rules:
        print(f"  {r['tier']:6} | +{r['increase_percent']:2}% | {r['artist'][:20]:20} | {r['event'][:25]}")

    print("\n" + "-" * 60)
    print("To apply these prices to eBay:")
    print("  python3 ebay_auto_pricing.py --live")
    print("-" * 60)


if __name__ == "__main__":
    main()
