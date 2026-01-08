#!/usr/bin/env python3
"""
DateDriven Email Notifications
Sends pricing recommendations in extractable format
"""

import os
import json
import smtplib
import pickle
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pricing_engine import (
    get_ai_consensus, calculate_pricing_window,
    PRICING_TIERS, BASE_PRICES
)
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

os.chdir('/Users/johnshay/DateDriven')

# Read .env
env_vars = {}
with open('.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env_vars[key] = value


def get_upcoming_events(days_ahead=30):
    """Get calendar events in the next X days"""
    try:
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build('calendar', 'v3', credentials=creds)

        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=100,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return events_result.get('items', [])
    except Exception as e:
        print(f"Calendar error: {e}")
        return []


def parse_event_for_pricing(event):
    """Extract item and event info from calendar event"""
    summary = event.get('summary', '')
    description = event.get('description', '')

    # Extract item name (after "List:" or from description)
    item_name = ""
    if "List:" in summary:
        item_name = summary.split("List:")[1].strip()
    elif "📦" in summary:
        item_name = summary.replace("📦", "").strip()

    # Extract event name from description
    event_name = ""
    if "Key Date:" in description:
        event_name = description.split("Key Date:")[1].split("\n")[0].strip()

    # Get date
    start = event.get('start', {})
    event_date = start.get('date') or start.get('dateTime', '')[:10]

    return {
        "item": item_name,
        "event": event_name,
        "date": event_date,
        "raw_summary": summary
    }


def categorize_item(item_name):
    """Determine category from item name"""
    item_lower = item_name.lower()

    if any(x in item_lower for x in ['death nyc', 'muhammad ali', 'wonder woman', 'worker', 'mao', 'warhol']):
        return 'death_nyc'
    elif any(x in item_lower for x in ['shepard fairey', 'obey', 'sunset']):
        return 'shepard_fairey'
    elif any(x in item_lower for x in ['lennon', 'beatles', 'harrison', 'yoko']):
        return 'beatles'
    elif any(x in item_lower for x in ['apollo', 'armstrong', 'aldrin', 'collins', 'nasa', 'space']):
        return 'space_nasa'
    elif any(x in item_lower for x in ['disney', 'snow white', 'mickey']):
        return 'disney'
    elif any(x in item_lower for x in ['guitar', 'signed', 'taylor swift', 'green day', 'blink', 'coldplay']):
        return 'musicians'
    else:
        return 'default'


def generate_email_content(recommendations):
    """Generate email with extractable pricing blocks"""

    # Header
    email_body = f"""
================================================================================
DATEDRIVEN PRICING RECOMMENDATIONS
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
================================================================================

SUMMARY:
- Total Recommendations: {len(recommendations)}
- Price Increases Active: {sum(1 for r in recommendations if r.get('start_date'))}

================================================================================
EXTRACT_START
================================================================================

"""

    # Individual recommendations
    for i, r in enumerate(recommendations, 1):
        email_body += f"""
--------------------------------------------------------------------------------
RECOMMENDATION #{i}
--------------------------------------------------------------------------------
ITEM: {r.get('item', 'N/A')}
EVENT: {r.get('event', 'N/A')}
CATEGORY: {r.get('category', 'N/A')}

[PRICING]
TIER: {r.get('tier', 'N/A')}
BASE_PRICE: ${r.get('base_price', 0):.2f}
INCREASE_PERCENT: {r.get('increase_percent', 0)}
NEW_PRICE: ${r.get('new_price', 0):.2f}

[WINDOW]
START_DATE: {r.get('start_date', 'N/A')}
END_DATE: {r.get('end_date', 'N/A')}
EVENT_DATE: {r.get('event_date', 'N/A')}

[AI_CONSENSUS]
CONSENSUS_REACHED: {r.get('consensus', False)}
CONFIDENCE: {r.get('confidence', 0):.0%}
VOTES: {r.get('votes', {})}

"""

    # JSON block for automation
    email_body += f"""
================================================================================
EXTRACT_END
================================================================================

================================================================================
JSON_DATA_START
================================================================================
{json.dumps([{
    'item': r.get('item'),
    'tier': r.get('tier'),
    'base_price': r.get('base_price'),
    'new_price': r.get('new_price'),
    'increase_percent': r.get('increase_percent'),
    'start_date': r.get('start_date'),
    'end_date': r.get('end_date'),
    'consensus': r.get('consensus')
} for r in recommendations], indent=2)}
================================================================================
JSON_DATA_END
================================================================================

ACTION REQUIRED:
1. Review recommendations above
2. Apply pricing changes in 3DSellers or eBay
3. Set calendar reminders for end dates to revert prices

---
Generated by DateDriven Pricing Engine
https://github.com/jjshay/DateDriven
"""

    return email_body


def process_upcoming_and_notify(days_ahead=30):
    """Process upcoming events and generate notification"""
    print("=" * 60)
    print(f"DATEDRIVEN - Processing events in next {days_ahead} days")
    print("=" * 60)

    # Get calendar events
    events = get_upcoming_events(days_ahead)
    print(f"\nFound {len(events)} calendar events")

    # Filter to pricing-relevant events
    pricing_events = []
    for event in events:
        parsed = parse_event_for_pricing(event)
        if parsed['item'] and "📦" in event.get('summary', ''):
            pricing_events.append(parsed)

    print(f"Pricing-relevant events: {len(pricing_events)}")

    if not pricing_events:
        print("No pricing events found in the next 30 days.")
        return []

    # Process each event with AI consensus
    recommendations = []
    for pe in pricing_events:
        print(f"\nProcessing: {pe['item'][:40]}...")

        category = categorize_item(pe['item'])

        # Get AI consensus
        consensus = get_ai_consensus(
            pe['item'],
            category,
            pe['event'] or pe['item'],
            pe['date']
        )

        tier = consensus['tier']
        base_price = BASE_PRICES.get(category, BASE_PRICES['default'])
        increase_pct = PRICING_TIERS[tier]['increase']
        new_price = round(base_price * (1 + increase_pct / 100), 2)

        # Parse date for window calculation
        try:
            event_dt = datetime.strptime(pe['date'], '%Y-%m-%d')
            formatted_date = event_dt.strftime('%B %d')
        except:
            formatted_date = pe['date']

        window = calculate_pricing_window(formatted_date, tier)

        rec = {
            'item': pe['item'],
            'event': pe['event'] or pe['item'],
            'category': category,
            'tier': tier,
            'base_price': base_price,
            'increase_percent': increase_pct,
            'new_price': new_price,
            'start_date': window['price_start'] if window else None,
            'end_date': window['price_end'] if window else None,
            'event_date': pe['date'],
            'consensus': consensus.get('consensus', False),
            'confidence': consensus.get('confidence', 0),
            'votes': consensus.get('votes', {})
        }

        recommendations.append(rec)
        print(f"   {tier} | +{increase_pct}% | ${base_price} -> ${new_price}")

    # Generate email content
    email_content = generate_email_content(recommendations)

    # Save to file
    output_file = f"pricing_notification_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(output_file, 'w') as f:
        f.write(email_content)
    print(f"\n✅ Saved notification to: {output_file}")

    # Also save JSON
    json_file = f"pricing_data_{datetime.now().strftime('%Y%m%d')}.json"
    with open(json_file, 'w') as f:
        json.dump(recommendations, f, indent=2)
    print(f"✅ Saved JSON data to: {json_file}")

    return recommendations


if __name__ == "__main__":
    recommendations = process_upcoming_and_notify(days_ahead=60)

    if recommendations:
        print("\n" + "=" * 60)
        print("RECOMMENDATIONS SUMMARY")
        print("=" * 60)

        by_tier = {}
        for r in recommendations:
            tier = r['tier']
            by_tier[tier] = by_tier.get(tier, []) + [r]

        for tier in ['PEAK', 'MAJOR', 'MEDIUM', 'MINOR']:
            if tier in by_tier:
                pct = PRICING_TIERS[tier]['increase']
                print(f"\n{tier} (+{pct}%):")
                for r in by_tier[tier]:
                    print(f"  • {r['item'][:40]} | {r['start_date']} to {r['end_date']}")
