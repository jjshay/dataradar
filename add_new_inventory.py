#!/usr/bin/env python3
"""
Add key dates for new inventory items
"""

import os
import json
import pickle
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from concurrent.futures import ThreadPoolExecutor, as_completed

os.chdir('/Users/johnshay/DATARADAR')
load_dotenv()

# New inventory items to process
NEW_ITEMS = [
    # Art Prints
    {"name": "Muhammad Ali Limited Edition (11/11)", "subject": "Muhammad Ali boxing legend civil rights", "type": "art"},
    {"name": "Wonder Woman Women's Rights Print (24x36)", "subject": "Wonder Woman feminism women's rights DC Comics", "type": "art"},
    {"name": "Worker's Rights Social Justice Print", "subject": "worker's rights labor movement social justice protest art", "type": "art"},
    {"name": "Mao Zedong Large Print", "subject": "Mao Zedong Chinese revolution pop art Warhol", "type": "art"},
    {"name": "John Lennon Portrait Print", "subject": "John Lennon Beatles peace imagine", "type": "art"},
    {"name": "George Harrison Print", "subject": "George Harrison Beatles guitarist", "type": "art"},
    {"name": "John Lennon & Yoko Ono Print", "subject": "John Lennon Yoko Ono bed-in peace", "type": "art"},
    {"name": "Shepard Fairey Sunsets Are To Die For (Ed. 101)", "subject": "Shepard Fairey sunset landscape Obey Giant", "type": "art"},
    {"name": "Andy Warhol Print", "subject": "Andy Warhol pop art Factory", "type": "art"},
    {"name": "John Lennon Bag One Lithograph", "subject": "John Lennon Bag One erotic lithographs Yoko", "type": "art"},

    # NASA / Space
    {"name": "Apollo 11 Signed Memorabilia", "subject": "Apollo 11 moon landing 1969 NASA", "type": "space"},
    {"name": "Neil Armstrong Signed Item", "subject": "Neil Armstrong astronaut first man on moon Apollo 11", "type": "space"},
    {"name": "Buzz Aldrin Signed Item", "subject": "Buzz Aldrin astronaut Apollo 11 moon", "type": "space"},
    {"name": "Michael Collins Signed Item", "subject": "Michael Collins astronaut Apollo 11 command module", "type": "space"},
    {"name": "Walt Cunningham Signed Item", "subject": "Walt Cunningham astronaut Apollo 7", "type": "space"},
    {"name": "Eugene Kranz Signed Item", "subject": "Eugene Kranz NASA flight director Apollo 13 Mission Control", "type": "space"},

    # Music - Guitars & Memorabilia
    {"name": "Taylor Swift Signed Guitar", "subject": "Taylor Swift pop country Eras Tour", "type": "music"},
    {"name": "Flea (RHCP) Signed Item", "subject": "Flea Red Hot Chili Peppers bassist funk rock", "type": "music"},
    {"name": "Modest Mouse Signed Item", "subject": "Modest Mouse indie rock Float On Isaac Brock", "type": "music"},
    {"name": "Green Day Signed Item", "subject": "Green Day punk rock Billie Joe Armstrong American Idiot", "type": "music"},
    {"name": "Blink-182 Signed Item (All 3)", "subject": "Blink-182 punk pop Travis Barker Tom DeLonge Mark Hoppus", "type": "music"},
    {"name": "Jack Johnson Signed Item", "subject": "Jack Johnson acoustic surf rock Banana Pancakes", "type": "music"},
    {"name": "Third Eye Blind Signed Item", "subject": "Third Eye Blind 90s rock Semi-Charmed Life", "type": "music"},
    {"name": "OneRepublic Signed Item", "subject": "OneRepublic Ryan Tedder pop rock Apologize", "type": "music"},
    {"name": "The Beatles Memorabilia", "subject": "The Beatles British Invasion rock Lennon McCartney", "type": "music"},
    {"name": "Olivia Rodrigo Signed Item", "subject": "Olivia Rodrigo pop Gen Z drivers license SOUR", "type": "music"},
    {"name": "Matt Maeson Signed Item", "subject": "Matt Maeson indie rock Cringe", "type": "music"},
    {"name": "White Stripes Signed Item", "subject": "White Stripes Jack White garage rock Seven Nation Army", "type": "music"},
    {"name": "Coldplay Signed Item", "subject": "Coldplay Chris Martin British rock Yellow", "type": "music"},

    # Disney & Collectibles
    {"name": "Snow White Disney Collectible", "subject": "Snow White Disney princess 1937 animated film", "type": "disney"},
    {"name": "Disney Crystal Figurines", "subject": "Disney Swarovski crystal figurines collectibles", "type": "disney"},
    {"name": "Superplastic Gorillaz Figures", "subject": "Superplastic Gorillaz vinyl figures Damon Albarn Jamie Hewlett", "type": "collectible"},
]

# Prompt for finding key dates
DATE_PROMPT = """Find the BEST dates to sell this item on eBay. Think about:
- Birthdays, death anniversaries, debut dates
- Related events, holidays, awareness days
- Album releases, tour dates, movie premieres
- Cultural moments that drive collector interest

ITEM: {name}
SUBJECT: {subject}

Return JSON with 3-5 key dates:
{{
    "dates": [
        {{"event": "Event Name", "date": "Month Day", "why": "brief reason"}},
        ...
    ]
}}

Be specific with dates! Use actual calendar dates."""


def query_claude(name, subject):
    """Query Claude for key dates"""
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        return None

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": DATE_PROMPT.format(name=name, subject=subject)}]
            },
            timeout=45
        )

        if resp.status_code == 200:
            content = resp.json()["content"][0]["text"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content.strip())
    except Exception as e:
        print(f"   Claude error: {e}")
    return None


def query_openai(name, subject):
    """Query OpenAI for key dates"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": DATE_PROMPT.format(name=name, subject=subject)}],
                "max_tokens": 1024
            },
            timeout=45
        )

        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content.strip())
    except Exception as e:
        print(f"   OpenAI error: {e}")
    return None


def parse_date(date_str, year=None):
    """Parse date string to datetime"""
    if not date_str:
        return None
    if year is None:
        year = datetime.now().year

    date_str = date_str.strip()

    # Handle date ranges
    import re
    range_match = re.match(r'(\w+)\s+(\d+)-\d+', date_str)
    if range_match:
        date_str = f"{range_match.group(1)} {range_match.group(2)}"

    # Standard formats
    formats = ["%B %d", "%b %d", "%m/%d", "%d %B", "%d %b", "%B %dst", "%B %dnd", "%B %drd", "%B %dth"]
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str.replace("st", "").replace("nd", "").replace("rd", "").replace("th", ""), fmt.replace("st", "").replace("nd", "").replace("rd", "").replace("th", ""))
            return parsed.replace(year=year)
        except ValueError:
            continue

    return None


def create_calendar_event(service, item_name, event_name, event_date, days_before=7):
    """Create a calendar event"""
    date = parse_date(event_date)
    if not date:
        return None

    # If date passed, schedule for next year
    if date < datetime.now():
        date = date.replace(year=date.year + 1)

    reminder_date = date - timedelta(days=days_before)

    event = {
        'summary': f'📦 List: {item_name}',
        'description': f'Key Date: {event_name} on {event_date}\n\nList this item on eBay before the key date.',
        'start': {'date': reminder_date.strftime('%Y-%m-%d'), 'timeZone': 'America/Los_Angeles'},
        'end': {'date': reminder_date.strftime('%Y-%m-%d'), 'timeZone': 'America/Los_Angeles'},
        'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 1440}]},
    }

    try:
        created = service.events().insert(calendarId='primary', body=event).execute()
        return created
    except Exception as e:
        print(f"   Calendar error: {e}")
        return None


def process_items():
    """Process all new inventory items"""
    print("=" * 60)
    print("ADDING KEY DATES FOR NEW INVENTORY")
    print("=" * 60)

    # Load calendar credentials
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    service = build('calendar', 'v3', credentials=creds)

    total_events = 0
    results = []

    for item in NEW_ITEMS:
        print(f"\n🎨 {item['name']}")

        # Query LLMs in parallel
        dates_found = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(query_claude, item['name'], item['subject']): "claude",
                executor.submit(query_openai, item['name'], item['subject']): "openai",
            }

            for future in as_completed(futures):
                llm = futures[future]
                try:
                    result = future.result()
                    if result and "dates" in result:
                        print(f"   ✅ {llm}: {len(result['dates'])} dates")
                        dates_found.extend(result['dates'])
                except Exception as e:
                    print(f"   ❌ {llm}: {e}")

        # Deduplicate and create events
        seen_events = set()
        item_events = 0

        for date_info in dates_found:
            event_name = date_info.get('event', '')
            event_date = date_info.get('date', '')

            if not event_name or not event_date:
                continue

            # Skip duplicates
            key = f"{event_name.lower()[:20]}-{event_date}"
            if key in seen_events:
                continue
            seen_events.add(key)

            # Create calendar event
            result = create_calendar_event(service, item['name'], event_name, event_date)
            if result:
                print(f"   📅 {event_name} -> {event_date}")
                item_events += 1
                total_events += 1

        results.append({"item": item['name'], "events": item_events})

    print("\n" + "=" * 60)
    print(f"COMPLETE! Created {total_events} calendar events")
    print("=" * 60)

    # Summary
    print("\nSummary:")
    for r in results:
        print(f"  {r['item'][:40]}: {r['events']} events")

    return results


if __name__ == "__main__":
    process_items()
