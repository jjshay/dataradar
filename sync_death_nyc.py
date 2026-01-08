#!/usr/bin/env python3
"""
Sync Death NYC dates to Google Calendar
"""

import os
import pickle
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pandas as pd

os.chdir('/Users/johnshay/DateDriven')

SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_calendar_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)


def parse_date_string(date_str, year=None):
    if not date_str or not isinstance(date_str, str):
        return None
    if year is None:
        year = datetime.now().year

    date_str = date_str.strip()

    # Handle date ranges: "July 18-21" → "July 18"
    import re
    range_match = re.match(r'(\w+)\s+(\d+)-\d+', date_str)
    if range_match:
        date_str = f"{range_match.group(1)} {range_match.group(2)}"

    # Handle "December 6-8" style
    range_match2 = re.match(r'(\w+)\s+(\d+)\s*-\s*(\w+\s+)?\d+', date_str)
    if range_match2:
        date_str = f"{range_match2.group(1)} {range_match2.group(2)}"

    # Handle relative dates
    relative_dates = {
        "first monday in may": (5, 1, 0),      # May, Monday, 1st occurrence
        "first monday of may": (5, 1, 0),
        "third saturday of september": (9, 5, 2),  # Sept, Saturday, 3rd
        "third saturday in september": (9, 5, 2),
        "first thursday of december": (12, 3, 0),
        "first tuesday of november": (11, 1, 0),
        "first tuesday after november 1": (11, 1, 0),
    }

    lower_str = date_str.lower()
    for pattern, (month, weekday, occurrence) in relative_dates.items():
        if pattern in lower_str:
            # Find nth weekday of month
            first_day = datetime(year, month, 1)
            first_weekday = first_day.weekday()
            days_until = (weekday - first_weekday) % 7
            target = first_day + timedelta(days=days_until + (7 * occurrence))
            return target

    # Handle vague dates
    vague_dates = {
        "early december": (12, 1),
        "early january": (1, 1),
        "early march": (3, 1),
        "late december": (12, 20),
        "mid december": (12, 15),
    }
    for pattern, (month, day) in vague_dates.items():
        if pattern in lower_str:
            return datetime(year, month, day)

    # Handle month-only
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }
    for month_name, month_num in months.items():
        if lower_str == month_name:
            return datetime(year, month_num, 1)

    # Standard formats
    formats = ["%B %d", "%b %d", "%m/%d", "%d %B", "%d %b"]
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.replace(year=year)
        except ValueError:
            continue
    return None


def sync_death_nyc():
    print("=" * 60)
    print("📅 SYNCING DEATH NYC TO GOOGLE CALENDAR")
    print("=" * 60)

    service = get_calendar_service()
    df = pd.read_excel('/Users/johnshay/DateDriven/DEATH_NYC_with_dates.xlsx')

    print(f"\n📦 Processing {len(df)} Death NYC items...")

    event_cols = ["PRIMARY_EVENT", "CULTURE_EVENT", "BRAND_EVENT",
                  "CHARACTER_EVENT", "ART_WORLD_EVENT", "BONUS_EVENT"]
    events_created = 0

    for idx, row in df.iterrows():
        title = str(row.get("Title", ""))[:50]
        if not title or pd.isna(row.get("Title")):
            continue

        print(f"\n🎨 {title}...")

        for col in event_cols:
            event_value = row.get(col)
            if pd.isna(event_value) or not event_value:
                continue

            # Parse "Event Name / Month Day" format
            parts = str(event_value).split("/")
            event_name = parts[0].strip()
            event_date_str = parts[1].strip() if len(parts) > 1 else None

            date = parse_date_string(event_date_str)
            if not date:
                print(f"   ⚠️  Could not parse: {event_date_str}")
                continue

            # Schedule for next year if date passed
            if date < datetime.now():
                date = date.replace(year=date.year + 1)

            # Create reminder 7 days before
            reminder_date = date - timedelta(days=7)

            event = {
                'summary': f'📦 List: {title}',
                'description': f'Key Date: {event_name}\n\nList this Death NYC piece before {event_date_str}',
                'start': {'date': reminder_date.strftime('%Y-%m-%d'), 'timeZone': 'America/Los_Angeles'},
                'end': {'date': reminder_date.strftime('%Y-%m-%d'), 'timeZone': 'America/Los_Angeles'},
                'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 1440}]},
            }

            try:
                service.events().insert(calendarId='primary', body=event).execute()
                print(f"   ✅ {event_name} -> {reminder_date.strftime('%b %d')}")
                events_created += 1
            except Exception as e:
                print(f"   ❌ Failed: {e}")

    print(f"\n✅ Created {events_created} calendar events!")


if __name__ == "__main__":
    sync_death_nyc()
