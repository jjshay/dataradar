#!/usr/bin/env python3
"""
DATARADAR - Google Sheets Pricing Control Panel
Creates and syncs a spreadsheet for managing pricing rules
"""

import os
import json
import pickle
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

os.chdir('/Users/johnshay/DATARADAR')

# Google Sheets scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar.readonly'
]

SPREADSHEET_NAME = "DATARADAR Pricing Control"


def get_credentials():
    """Get or refresh Google credentials"""
    creds = None

    if os.path.exists('token_sheets.pickle'):
        with open('token_sheets.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Try to use existing calendar credentials
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())

        with open('token_sheets.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


def create_pricing_spreadsheet(service):
    """Create the pricing control spreadsheet"""
    spreadsheet = {
        'properties': {'title': SPREADSHEET_NAME},
        'sheets': [
            {
                'properties': {
                    'title': 'Pricing Rules',
                    'gridProperties': {'frozenRowCount': 1}
                }
            },
            {
                'properties': {
                    'title': 'Categories',
                    'gridProperties': {'frozenRowCount': 1}
                }
            },
            {
                'properties': {
                    'title': 'Update Log',
                    'gridProperties': {'frozenRowCount': 1}
                }
            }
        ]
    }

    result = service.spreadsheets().create(body=spreadsheet).execute()
    spreadsheet_id = result['spreadsheetId']
    print(f"Created spreadsheet: {result['spreadsheetUrl']}")

    return spreadsheet_id


def setup_pricing_rules_sheet(service, spreadsheet_id):
    """Set up the Pricing Rules sheet with headers and sample data"""

    # Headers
    headers = [
        ['ENABLED', 'CATEGORY', 'ARTIST/TYPE', 'EVENT', 'EVENT_DATE',
         'WINDOW_START', 'WINDOW_END', 'DURATION_DAYS', 'TIER',
         'PRICE_CHANGE_%', 'KEYWORDS', 'NOTES']
    ]

    # Sample data based on current rules
    sample_data = [
        ['TRUE', 'Art - Pop', 'Death NYC', 'General Premium', '2026-12-31',
         '2026-01-01', '2026-12-31', '365', 'MINOR', '5',
         'Death NYC, DEATH NYC', 'Year-round baseline'],

        ['TRUE', 'Art - Street', 'Shepard Fairey', 'Obama Hope Anniversary', '2026-01-17',
         '2026-01-07', '2026-01-19', '12', 'MEDIUM', '15',
         'Shepard Fairey, Obey Giant, Obey', 'Annual event'],

        ['TRUE', 'Art - Pop', 'Muhammad Ali', 'Muhammad Ali Birthday', '2026-01-17',
         '2026-01-07', '2026-01-19', '12', 'MEDIUM', '15',
         'Muhammad Ali, Ali, boxing', 'Annual birthday'],

        ['TRUE', 'Music', 'Matt Maeson', 'Matt Maeson Birthday', '2026-01-17',
         '2026-01-07', '2026-01-19', '12', 'MEDIUM', '15',
         'Matt Maeson', 'Annual birthday'],

        ['TRUE', 'Space/NASA', 'Buzz Aldrin', 'Buzz Aldrin Birthday', '2026-01-20',
         '2026-01-10', '2026-01-22', '12', 'MEDIUM', '15',
         'Buzz Aldrin, Aldrin, Apollo 11, Apollo', 'Annual birthday'],

        ['TRUE', 'Music - Beatles', 'George Harrison', 'George Harrison Birthday', '2026-02-25',
         '2026-02-15', '2026-02-27', '12', 'MEDIUM', '15',
         'George Harrison, Harrison', 'Annual birthday'],

        ['TRUE', 'Music - Beatles', 'Beatles', 'Ed Sullivan Anniversary', '2026-02-09',
         '2026-01-30', '2026-02-11', '12', 'MEDIUM', '15',
         'Beatles, Lennon, McCartney', 'Historic performance'],

        ['TRUE', 'Art - Pop', 'Andy Warhol', 'Warhol Death Anniversary', '2026-02-22',
         '2026-02-08', '2026-02-24', '16', 'MAJOR', '25',
         'Warhol, Andy Warhol', 'Major anniversary'],

        ['FALSE', 'Space/NASA', 'Apollo 11', 'Moon Landing Anniversary', '2026-07-20',
         '2026-07-06', '2026-07-22', '16', 'PEAK', '35',
         'Apollo 11, Moon Landing, NASA, Armstrong, Aldrin', 'Major milestone - activate closer to date'],

        ['FALSE', 'Music - Beatles', 'John Lennon', 'Lennon Death Anniversary', '2026-12-08',
         '2026-11-24', '2026-12-10', '16', 'MAJOR', '25',
         'John Lennon, Lennon, Yoko', 'Major anniversary - activate closer to date'],

        ['FALSE', 'Art - Street', 'All Street Art', 'Art Basel Miami', '2026-12-05',
         '2026-11-28', '2026-12-07', '9', 'PEAK', '35',
         'Death NYC, Shepard Fairey, Banksy, Street Art', 'Major art event'],

        ['FALSE', 'Music', 'Taylor Swift', 'Taylor Swift Birthday', '2026-12-13',
         '2026-12-03', '2026-12-15', '12', 'MEDIUM', '15',
         'Taylor Swift', 'Annual birthday'],
    ]

    # Write headers
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='Pricing Rules!A1:L1',
        valueInputOption='RAW',
        body={'values': headers}
    ).execute()

    # Write sample data
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='Pricing Rules!A2:L13',
        valueInputOption='RAW',
        body={'values': sample_data}
    ).execute()

    # Format header row
    requests = [
        {
            'repeatCell': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 0,
                    'endRowIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.8},
                        'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)'
            }
        },
        # Add data validation for ENABLED column (TRUE/FALSE)
        {
            'setDataValidation': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 1,
                    'endRowIndex': 100,
                    'startColumnIndex': 0,
                    'endColumnIndex': 1
                },
                'rule': {
                    'condition': {
                        'type': 'ONE_OF_LIST',
                        'values': [{'userEnteredValue': 'TRUE'}, {'userEnteredValue': 'FALSE'}]
                    },
                    'showCustomUi': True,
                    'strict': True
                }
            }
        },
        # Add data validation for TIER column
        {
            'setDataValidation': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 1,
                    'endRowIndex': 100,
                    'startColumnIndex': 8,
                    'endColumnIndex': 9
                },
                'rule': {
                    'condition': {
                        'type': 'ONE_OF_LIST',
                        'values': [
                            {'userEnteredValue': 'MINOR'},
                            {'userEnteredValue': 'MEDIUM'},
                            {'userEnteredValue': 'MAJOR'},
                            {'userEnteredValue': 'PEAK'}
                        ]
                    },
                    'showCustomUi': True,
                    'strict': True
                }
            }
        },
        # Auto-resize columns
        {
            'autoResizeDimensions': {
                'dimensions': {
                    'sheetId': 0,
                    'dimension': 'COLUMNS',
                    'startIndex': 0,
                    'endIndex': 12
                }
            }
        }
    ]

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': requests}
    ).execute()


def setup_categories_sheet(service, spreadsheet_id):
    """Set up the Categories reference sheet"""

    headers = [['CATEGORY', 'BASE_PRICE', 'DESCRIPTION', 'KEYWORDS']]

    data = [
        ['Art - Pop', '$89', 'Death NYC and similar pop art', 'Death NYC, DEATH NYC'],
        ['Art - Street', '$300', 'Shepard Fairey, Banksy style', 'Shepard Fairey, Obey Giant, Banksy'],
        ['Music - Beatles', '$500', 'Beatles, Lennon, Harrison memorabilia', 'Beatles, Lennon, Harrison, Yoko'],
        ['Music', '$900', 'Signed guitars, music memorabilia', 'guitar, signed, Taylor Swift, Green Day'],
        ['Space/NASA', '$900', 'Apollo, NASA, astronaut items', 'Apollo, NASA, Armstrong, Aldrin, Space'],
        ['Disney', '$150', 'Disney collectibles', 'Disney, Mickey, Snow White'],
    ]

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='Categories!A1:D1',
        valueInputOption='RAW',
        body={'values': headers}
    ).execute()

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='Categories!A2:D7',
        valueInputOption='RAW',
        body={'values': data}
    ).execute()

    # Format
    requests = [
        {
            'repeatCell': {
                'range': {'sheetId': 1, 'startRowIndex': 0, 'endRowIndex': 1},
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.4},
                        'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)'
            }
        },
        {
            'autoResizeDimensions': {
                'dimensions': {'sheetId': 1, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 4}
            }
        }
    ]

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': requests}
    ).execute()


def setup_log_sheet(service, spreadsheet_id):
    """Set up the Update Log sheet"""

    headers = [['TIMESTAMP', 'ACTION', 'ITEMS_UPDATED', 'ITEMS_FAILED', 'TOTAL_REVENUE_CHANGE', 'LOG_FILE']]

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='Update Log!A1:F1',
        valueInputOption='RAW',
        body={'values': headers}
    ).execute()

    # Format
    requests = [
        {
            'repeatCell': {
                'range': {'sheetId': 2, 'startRowIndex': 0, 'endRowIndex': 1},
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.6, 'green': 0.2, 'blue': 0.2},
                        'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)'
            }
        },
        {
            'autoResizeDimensions': {
                'dimensions': {'sheetId': 2, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 6}
            }
        }
    ]

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': requests}
    ).execute()


def read_pricing_rules_from_sheet(service, spreadsheet_id):
    """Read pricing rules from Google Sheet"""
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range='Pricing Rules!A2:L100'
    ).execute()

    rows = result.get('values', [])
    rules = []

    for row in rows:
        if len(row) < 11:
            continue

        enabled = row[0].upper() == 'TRUE'
        if not enabled:
            continue

        rule = {
            'category': row[1],
            'artist': row[2],
            'event': row[3],
            'event_date': row[4],
            'start_date': row[5],
            'end_date': row[6],
            'duration': int(row[7]) if row[7] else 0,
            'tier': row[8],
            'increase_percent': int(row[9]) if row[9] else 0,
            'keywords': [k.strip() for k in row[10].split(',')] if row[10] else [],
            'notes': row[11] if len(row) > 11 else ''
        }
        rules.append(rule)

    return rules


def export_rules_to_json(rules, filename='pricing_rules.json'):
    """Export sheet rules to JSON for ebay_auto_pricing.py"""
    json_rules = []

    for r in rules:
        json_rules.append({
            'item': r['artist'],
            'keywords': r['keywords'],
            'event': r['event'],
            'tier': r['tier'],
            'increase_percent': r['increase_percent'],
            'start_date': r['start_date'],
            'end_date': r['end_date']
        })

    with open(filename, 'w') as f:
        json.dump(json_rules, f, indent=2)

    print(f"Exported {len(json_rules)} rules to {filename}")
    return json_rules


def log_update_to_sheet(service, spreadsheet_id, success_count, fail_count, log_file):
    """Log an update to the Update Log sheet"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    row = [[timestamp, 'PRICE_UPDATE', str(success_count), str(fail_count), '', log_file]]

    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range='Update Log!A:F',
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': row}
    ).execute()


def main():
    """Main function to set up or sync the pricing spreadsheet"""
    print("=" * 60)
    print("DATEDRIVEN - Google Sheets Pricing Control")
    print("=" * 60)

    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)

    # Check if spreadsheet already exists
    spreadsheet_id = None
    config_file = 'sheets_config.json'

    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
            spreadsheet_id = config.get('spreadsheet_id')
            print(f"\nUsing existing spreadsheet: {spreadsheet_id}")

    if not spreadsheet_id:
        print("\nCreating new pricing control spreadsheet...")
        spreadsheet_id = create_pricing_spreadsheet(service)

        print("Setting up Pricing Rules sheet...")
        setup_pricing_rules_sheet(service, spreadsheet_id)

        print("Setting up Categories sheet...")
        setup_categories_sheet(service, spreadsheet_id)

        print("Setting up Update Log sheet...")
        setup_log_sheet(service, spreadsheet_id)

        # Save config
        with open(config_file, 'w') as f:
            json.dump({'spreadsheet_id': spreadsheet_id}, f)

        print(f"\n✅ Spreadsheet created!")
        print(f"   URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")

    # Read and export rules
    print("\nReading rules from spreadsheet...")
    rules = read_pricing_rules_from_sheet(service, spreadsheet_id)
    print(f"Found {len(rules)} enabled rules")

    export_rules_to_json(rules)

    print("\n" + "=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    print(f"\nSpreadsheet URL:")
    print(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    print("\nTo update eBay prices using sheet rules:")
    print("  1. Edit rules in Google Sheets")
    print("  2. Run: python sheets_pricing_control.py")
    print("  3. Run: python ebay_auto_pricing.py --live")


if __name__ == "__main__":
    main()
