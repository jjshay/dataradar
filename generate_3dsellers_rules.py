#!/usr/bin/env python3
"""
Generate 3DSellers automation rules from AI-consensus pricing
Creates importable rules with exact start/end dates
"""

import os
import json
import pickle
from datetime import datetime, timedelta
from pricing_engine import (
    get_ai_consensus, calculate_pricing_window, PRICING_TIERS, BASE_PRICES,
    format_email_block, format_json_extract
)
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

os.chdir('/Users/johnshay/DATARADAR')

# All inventory items with categories
INVENTORY = [
    # Death NYC
    {"name": "Death NYC Print", "category": "death_nyc", "keywords": ["Death NYC", "DEATH NYC"]},

    # Shepard Fairey
    {"name": "Shepard Fairey Print", "category": "shepard_fairey", "keywords": ["Shepard Fairey", "Obey Giant", "Sunsets"]},

    # Beatles / Lennon
    {"name": "John Lennon Portrait Print", "category": "beatles", "keywords": ["John Lennon", "Lennon"]},
    {"name": "George Harrison Print", "category": "beatles", "keywords": ["George Harrison", "Harrison"]},
    {"name": "John Lennon & Yoko Ono Print", "category": "beatles", "keywords": ["Yoko", "Lennon Ono"]},
    {"name": "John Lennon Bag One Lithograph", "category": "beatles", "keywords": ["Bag One", "Lennon Lithograph"]},
    {"name": "The Beatles Memorabilia", "category": "beatles", "keywords": ["Beatles"]},

    # Space / NASA
    {"name": "Apollo 11 Signed Memorabilia", "category": "space_nasa", "keywords": ["Apollo 11", "Apollo"]},
    {"name": "Neil Armstrong Signed Item", "category": "space_nasa", "keywords": ["Neil Armstrong", "Armstrong"]},
    {"name": "Buzz Aldrin Signed Item", "category": "space_nasa", "keywords": ["Buzz Aldrin", "Aldrin"]},
    {"name": "Michael Collins Signed Item", "category": "space_nasa", "keywords": ["Michael Collins"]},
    {"name": "Walt Cunningham Signed Item", "category": "space_nasa", "keywords": ["Walt Cunningham", "Cunningham"]},
    {"name": "Eugene Kranz Signed Item", "category": "space_nasa", "keywords": ["Eugene Kranz", "Kranz", "Mission Control"]},

    # Musicians
    {"name": "Taylor Swift Signed Guitar", "category": "musicians", "keywords": ["Taylor Swift"]},
    {"name": "Flea (RHCP) Signed Item", "category": "musicians", "keywords": ["Flea", "Red Hot Chili Peppers", "RHCP"]},
    {"name": "Modest Mouse Signed Item", "category": "musicians", "keywords": ["Modest Mouse"]},
    {"name": "Green Day Signed Item", "category": "musicians", "keywords": ["Green Day"]},
    {"name": "Blink-182 Signed Item", "category": "musicians", "keywords": ["Blink-182", "Blink 182"]},
    {"name": "Jack Johnson Signed Item", "category": "musicians", "keywords": ["Jack Johnson"]},
    {"name": "Third Eye Blind Signed Item", "category": "musicians", "keywords": ["Third Eye Blind"]},
    {"name": "OneRepublic Signed Item", "category": "musicians", "keywords": ["OneRepublic"]},
    {"name": "Olivia Rodrigo Signed Item", "category": "musicians", "keywords": ["Olivia Rodrigo"]},
    {"name": "Matt Maeson Signed Item", "category": "musicians", "keywords": ["Matt Maeson"]},
    {"name": "White Stripes Signed Item", "category": "musicians", "keywords": ["White Stripes", "Jack White"]},
    {"name": "Coldplay Signed Item", "category": "musicians", "keywords": ["Coldplay"]},

    # Art
    {"name": "Muhammad Ali Limited Edition", "category": "death_nyc", "keywords": ["Muhammad Ali", "Ali"]},
    {"name": "Wonder Woman Women's Rights Print", "category": "death_nyc", "keywords": ["Wonder Woman"]},
    {"name": "Worker's Rights Social Justice Print", "category": "death_nyc", "keywords": ["Worker", "Social Justice"]},
    {"name": "Mao Zedong Large Print", "category": "death_nyc", "keywords": ["Mao", "Zedong"]},
    {"name": "Andy Warhol Print", "category": "death_nyc", "keywords": ["Andy Warhol", "Warhol"]},

    # Disney
    {"name": "Snow White Disney Collectible", "category": "disney", "keywords": ["Snow White", "Disney"]},
    {"name": "Disney Crystal Figurines", "category": "disney", "keywords": ["Disney", "Swarovski", "Crystal"]},
    {"name": "Superplastic Gorillaz Figures", "category": "disney", "keywords": ["Gorillaz", "Superplastic"]},
]

# Key events to process
KEY_EVENTS = [
    # Beatles / Lennon
    {"event": "John Lennon Death Anniversary", "date": "December 8", "items": ["John Lennon", "Beatles", "Yoko", "Bag One"]},
    {"event": "John Lennon Birthday", "date": "October 9", "items": ["John Lennon", "Beatles", "Lennon"]},
    {"event": "George Harrison Birthday", "date": "February 25", "items": ["George Harrison", "Beatles"]},
    {"event": "George Harrison Death Anniversary", "date": "November 29", "items": ["George Harrison", "Beatles"]},
    {"event": "Beatles Ed Sullivan Performance", "date": "February 9", "items": ["Beatles"]},

    # Space / NASA
    {"event": "Moon Landing Anniversary (Apollo 11)", "date": "July 20", "items": ["Apollo 11", "Neil Armstrong", "Buzz Aldrin", "Michael Collins", "NASA"]},
    {"event": "Apollo 11 Launch Anniversary", "date": "July 16", "items": ["Apollo 11", "NASA"]},
    {"event": "Neil Armstrong Birthday", "date": "August 5", "items": ["Neil Armstrong", "Apollo"]},
    {"event": "Buzz Aldrin Birthday", "date": "January 20", "items": ["Buzz Aldrin", "Apollo"]},
    {"event": "Space Exploration Day", "date": "July 20", "items": ["NASA", "Apollo", "Space"]},

    # Musicians
    {"event": "Taylor Swift Birthday", "date": "December 13", "items": ["Taylor Swift"]},
    {"event": "Green Day American Idiot Anniversary", "date": "September 21", "items": ["Green Day"]},
    {"event": "Blink-182 Enema of the State Anniversary", "date": "June 1", "items": ["Blink-182"]},
    {"event": "Red Hot Chili Peppers Day", "date": "April 22", "items": ["Flea", "RHCP"]},
    {"event": "Record Store Day", "date": "April 19", "items": ["Taylor Swift", "Green Day", "Blink-182", "Coldplay", "White Stripes"]},

    # Art / Pop Culture
    {"event": "Andy Warhol Birthday", "date": "August 6", "items": ["Andy Warhol", "Warhol"]},
    {"event": "Andy Warhol Death Anniversary", "date": "February 22", "items": ["Andy Warhol", "Warhol"]},
    {"event": "Muhammad Ali Birthday", "date": "January 17", "items": ["Muhammad Ali", "Ali"]},
    {"event": "Muhammad Ali Death Anniversary", "date": "June 3", "items": ["Muhammad Ali", "Ali"]},
    {"event": "International Women's Day", "date": "March 8", "items": ["Wonder Woman", "Women's Rights"]},
    {"event": "Labor Day", "date": "September 1", "items": ["Worker", "Labor"]},
    {"event": "Art Basel Miami", "date": "December 5", "items": ["Death NYC", "Shepard Fairey", "Street Art"]},

    # Disney
    {"event": "Snow White Anniversary (1937)", "date": "December 21", "items": ["Snow White", "Disney"]},
    {"event": "Mickey Mouse Birthday", "date": "November 18", "items": ["Mickey", "Disney"]},

    # Auction Houses
    {"event": "Heritage Auctions Space Sale", "date": "July 20", "items": ["Apollo", "NASA", "Space"]},
    {"event": "Heritage Auctions Urban Art", "date": "May 9", "items": ["Death NYC", "Shepard Fairey", "Street Art"]},
    {"event": "Heritage Auctions Music Memorabilia", "date": "April 18", "items": ["Guitar", "Signed", "Music"]},
    {"event": "Julien's Auctions Music Icons", "date": "May 30", "items": ["Guitar", "Signed", "Music", "Beatles"]},
    {"event": "Julien's Auctions Rock n Roll", "date": "November 21", "items": ["Guitar", "Rock", "Music"]},
]


def get_calendar_events():
    """Get events from Google Calendar"""
    try:
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build('calendar', 'v3', credentials=creds)

        # Get events for next year
        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=365)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=500,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return events_result.get('items', [])
    except Exception as e:
        print(f"Calendar error: {e}")
        return []


def match_item_to_event(item, event):
    """Check if item matches event"""
    item_keywords = item.get("keywords", [])
    event_items = event.get("items", [])

    for kw in item_keywords:
        for ei in event_items:
            if kw.lower() in ei.lower() or ei.lower() in kw.lower():
                return True
    return False


def generate_all_rules():
    """Generate pricing rules for all item-event combinations"""
    print("=" * 70)
    print("GENERATING 3DSELLERS PRICING RULES WITH AI CONSENSUS")
    print("=" * 70)

    all_rules = []
    email_blocks = []

    for event in KEY_EVENTS:
        print(f"\n📅 {event['event']} ({event['date']})")

        for item in INVENTORY:
            if not match_item_to_event(item, event):
                continue

            print(f"   Processing: {item['name']}...", end=" ")

            # Get AI consensus
            consensus = get_ai_consensus(
                item['name'],
                item['category'],
                event['event'],
                event['date']
            )

            tier = consensus['tier']
            base_price = BASE_PRICES.get(item['category'], BASE_PRICES['default'])
            increase_pct = PRICING_TIERS[tier]['increase']
            new_price = round(base_price * (1 + increase_pct / 100), 2)

            # Calculate window
            window = calculate_pricing_window(event['date'], tier)

            print(f"{tier} (+{increase_pct}%) - Consensus: {consensus.get('consensus', False)}")

            rule = {
                "item": item['name'],
                "keywords": item['keywords'],
                "category": item['category'],
                "event": event['event'],
                "event_date": event['date'],
                "tier": tier,
                "base_price": base_price,
                "increase_percent": increase_pct,
                "new_price": new_price,
                "start_date": window['price_start'] if window else None,
                "end_date": window['price_end'] if window else None,
                "consensus": consensus.get('consensus', False),
                "confidence": consensus.get('confidence', 0),
                "votes": consensus.get('votes', {}),
                "reasonings": consensus.get('reasonings', [])
            }

            all_rules.append(rule)

            # Generate email block
            email_block = f"""
================================================================================
PRICING RULE
================================================================================
ITEM: {item['name']}
KEYWORDS: {', '.join(item['keywords'])}
EVENT: {event['event']}

TIER: {tier}
BASE_PRICE: ${base_price:.2f}
INCREASE: +{increase_pct}%
NEW_PRICE: ${new_price:.2f}

START_DATE: {window['price_start'] if window else 'N/A'}
END_DATE: {window['price_end'] if window else 'N/A'}

CONSENSUS: {consensus.get('consensus', False)}
CONFIDENCE: {consensus.get('confidence', 0):.0%}
================================================================================
"""
            email_blocks.append(email_block)

    return all_rules, email_blocks


def export_3dsellers_csv(rules):
    """Export rules as CSV for 3DSellers import"""
    csv_lines = ["Rule Name,Keywords,Price Change,Start Date,End Date"]

    for r in rules:
        name = f"{r['event'][:30]} - {r['item'][:20]}"
        keywords = "|".join(r['keywords'])
        change = f"+{r['increase_percent']}%"
        start = r['start_date'] or ""
        end = r['end_date'] or ""

        csv_lines.append(f'"{name}","{keywords}","{change}","{start}","{end}"')

    return "\n".join(csv_lines)


def export_summary(rules):
    """Export summary by tier"""
    summary = {
        "MINOR": [],
        "MEDIUM": [],
        "MAJOR": [],
        "PEAK": []
    }

    for r in rules:
        summary[r['tier']].append(r)

    output = []
    for tier, items in summary.items():
        pct = PRICING_TIERS[tier]['increase']
        output.append(f"\n{'='*60}")
        output.append(f"{tier} TIER (+{pct}%) - {len(items)} rules")
        output.append(f"{'='*60}")
        for item in items:
            output.append(f"  {item['item'][:35]:35} | {item['event'][:25]:25} | {item['start_date']} to {item['end_date']}")

    return "\n".join(output)


if __name__ == "__main__":
    rules, email_blocks = generate_all_rules()

    # Save rules as JSON
    with open('pricing_rules.json', 'w') as f:
        json.dump(rules, f, indent=2)
    print(f"\n✅ Saved {len(rules)} rules to pricing_rules.json")

    # Save CSV for 3DSellers
    csv_content = export_3dsellers_csv(rules)
    with open('3dsellers_rules.csv', 'w') as f:
        f.write(csv_content)
    print(f"✅ Saved CSV for 3DSellers import: 3dsellers_rules.csv")

    # Save email blocks
    with open('pricing_email_blocks.txt', 'w') as f:
        f.write("\n".join(email_blocks))
    print(f"✅ Saved email blocks: pricing_email_blocks.txt")

    # Print summary
    print(export_summary(rules))

    # Print JSON extract for automation
    print("\n" + "=" * 60)
    print("JSON EXTRACT (first 5 for preview)")
    print("=" * 60)
    print(json.dumps([{
        "item": r["item"],
        "tier": r["tier"],
        "increase": f"+{r['increase_percent']}%",
        "start": r["start_date"],
        "end": r["end_date"],
        "consensus": r["consensus"]
    } for r in rules[:5]], indent=2))
