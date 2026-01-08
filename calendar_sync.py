"""
Google Calendar Sync for eBay Key Dates
Pushes key dates to Google Calendar for listing reminders
"""

import os
import pickle
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pandas as pd

SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_calendar_service():
    """Authenticate and return Google Calendar service"""
    creds = None

    # Check for existing token
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("❌ Missing credentials.json!")
                print("\nTo set up Google Calendar API:")
                print("1. Go to https://console.cloud.google.com/")
                print("2. Create a new project or select existing")
                print("3. Enable Google Calendar API")
                print("4. Create OAuth 2.0 credentials (Desktop app)")
                print("5. Download credentials.json to this folder")
                return None

            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)


def parse_date_string(date_str: str, year: int = None) -> datetime:
    """Parse date strings like 'January 17' or 'Feb 15' into datetime"""
    if not date_str:
        return None

    if year is None:
        year = datetime.now().year

    # Common formats to try
    formats = [
        "%B %d",      # January 17
        "%b %d",      # Jan 17
        "%m/%d",      # 01/17
        "%d %B",      # 17 January
        "%d %b",      # 17 Jan
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str.strip(), fmt)
            return parsed.replace(year=year)
        except ValueError:
            continue

    return None


def create_calendar_event(service, artwork_name: str, event_name: str, event_date: str, days_before: int = 7):
    """Create a calendar event for an artwork key date"""

    date = parse_date_string(event_date)
    if not date:
        print(f"   ⚠️  Could not parse date: {event_date}")
        return None

    # If date has passed this year, schedule for next year
    if date < datetime.now():
        date = date.replace(year=date.year + 1)

    # Create reminder event (days_before the actual date)
    reminder_date = date - timedelta(days=days_before)

    event = {
        'summary': f'📦 List: {artwork_name}',
        'description': f'Key Date: {event_name} on {event_date}\n\nThis is a reminder to list this artwork on eBay before the key date.',
        'start': {
            'date': reminder_date.strftime('%Y-%m-%d'),
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            'date': reminder_date.strftime('%Y-%m-%d'),
            'timeZone': 'America/Los_Angeles',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 1440},  # 1 day before
            ],
        },
    }

    try:
        created = service.events().insert(calendarId='primary', body=event).execute()
        print(f"   ✅ Created: {event['summary']} for {reminder_date.strftime('%b %d')}")
        return created
    except Exception as e:
        print(f"   ❌ Failed to create event: {e}")
        return None


def sync_to_calendar(excel_path: str, days_before: int = 7):
    """Sync all key dates from Excel to Google Calendar"""

    print("=" * 60)
    print("📅 SYNCING KEY DATES TO GOOGLE CALENDAR")
    print("=" * 60)

    service = get_calendar_service()
    if not service:
        return

    # Load the Excel file
    df = pd.read_excel(excel_path, sheet_name="EVENTS")
    print(f"\n📦 Processing {len(df)} items...")

    event_columns = ["NATIONAL EVENT 1", "KEY EVENT 1", "EVENT 2", "EVENT 3", "EVENT 4", "EVENT 5"]
    events_created = 0

    for idx, row in df.iterrows():
        artwork_name = row.get("NAME", "")
        if not artwork_name:
            continue

        print(f"\n🎨 {artwork_name[:50]}...")

        for col in event_columns:
            event_value = row.get(col)
            if pd.isna(event_value) or not event_value:
                continue

            # Parse "Event Name / Month Day" format
            if "/" in str(event_value):
                parts = str(event_value).split("/")
                event_name = parts[0].strip()
                event_date = parts[1].strip() if len(parts) > 1 else None
            else:
                event_name = str(event_value)
                event_date = None

            if event_date:
                result = create_calendar_event(service, artwork_name, event_name, event_date, days_before)
                if result:
                    events_created += 1

    print(f"\n✅ Created {events_created} calendar events!")
    print(f"   Events are set {days_before} days before each key date")


if __name__ == "__main__":
    import sys

    excel_path = sys.argv[1] if len(sys.argv) > 1 else "/Applications/SHEPARD FAIREY.xlsx"
    days_before = int(sys.argv[2]) if len(sys.argv) > 2 else 7

    sync_to_calendar(excel_path, days_before)
