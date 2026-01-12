#!/usr/bin/env python3
"""
DATARADAR Pricing Engine
- AI consensus on event tiers
- Structured pricing windows with start/end dates
- Email-ready format for easy extraction
"""

import os
import json
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

os.chdir('/Users/johnshay/DATARADAR')

# Read .env
env_vars = {}
with open('.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env_vars[key] = value

# Pricing Tiers
PRICING_TIERS = {
    "MINOR": {"increase": 5, "window_days": 7, "description": "Related awareness days, minor connections"},
    "MEDIUM": {"increase": 15, "window_days": 10, "description": "Birthdays, album anniversaries, related events"},
    "MAJOR": {"increase": 25, "window_days": 14, "description": "Death anniversaries, significant milestones"},
    "PEAK": {"increase": 35, "window_days": 14, "description": "Once-in-lifetime events, major auctions, 50th anniversaries"}
}

# Base prices by category
BASE_PRICES = {
    "death_nyc": 89,
    "shepard_fairey": 300,
    "musicians": 900,
    "space_nasa": 900,
    "disney": 150,
    "beatles": 500,
    "default": 100
}

TIER_PROMPT = """You are a pricing analyst for collectibles. Classify this event's significance for selling this item.

ITEM: {item_name}
CATEGORY: {category}
EVENT: {event_name}
EVENT DATE: {event_date}

TIERS:
- MINOR (5% increase): Loosely related awareness days, minor celebrity mentions, tangential connections
- MEDIUM (15% increase): Artist/subject birthdays, album release anniversaries, related cultural events
- MAJOR (25% increase): Death anniversaries, significant milestones (25th, 40th), documentary releases
- PEAK (35% increase): Once-in-lifetime (50th anniversaries), major auction house sales, viral cultural moments

Respond with ONLY a JSON object:
{{"tier": "MINOR|MEDIUM|MAJOR|PEAK", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}
"""


def query_claude_tier(item_name, category, event_name, event_date):
    """Query Claude for tier classification"""
    api_key = env_vars.get("CLAUDE_API_KEY")
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
                "max_tokens": 256,
                "messages": [{"role": "user", "content": TIER_PROMPT.format(
                    item_name=item_name, category=category,
                    event_name=event_name, event_date=event_date
                )}]
            },
            timeout=30
        )

        if resp.status_code == 200:
            content = resp.json()["content"][0]["text"]
            if "```" in content:
                content = content.split("```")[1].replace("json", "").split("```")[0]
            return {"source": "claude", **json.loads(content.strip())}
    except Exception as e:
        print(f"Claude error: {e}")
    return None


def query_openai_tier(item_name, category, event_name, event_date):
    """Query OpenAI for tier classification"""
    api_key = env_vars.get("OPENAI_API_KEY")
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
                "messages": [{"role": "user", "content": TIER_PROMPT.format(
                    item_name=item_name, category=category,
                    event_name=event_name, event_date=event_date
                )}],
                "max_tokens": 256
            },
            timeout=30
        )

        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            if "```" in content:
                content = content.split("```")[1].replace("json", "").split("```")[0]
            return {"source": "openai", **json.loads(content.strip())}
    except Exception as e:
        print(f"OpenAI error: {e}")
    return None


def query_gemini_tier(item_name, category, event_name, event_date):
    """Query Gemini for tier classification"""
    api_key = env_vars.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": TIER_PROMPT.format(
                    item_name=item_name, category=category,
                    event_name=event_name, event_date=event_date
                )}]}]
            },
            timeout=30
        )

        if resp.status_code == 200:
            content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            if "```" in content:
                content = content.split("```")[1].replace("json", "").split("```")[0]
            return {"source": "gemini", **json.loads(content.strip())}
    except Exception as e:
        print(f"Gemini error: {e}")
    return None


def get_ai_consensus(item_name, category, event_name, event_date):
    """Get consensus tier from multiple AIs"""
    results = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(query_claude_tier, item_name, category, event_name, event_date): "claude",
            executor.submit(query_openai_tier, item_name, category, event_name, event_date): "openai",
            executor.submit(query_gemini_tier, item_name, category, event_name, event_date): "gemini",
        }

        for future in as_completed(futures):
            try:
                result = future.result()
                if result and "tier" in result:
                    results.append(result)
            except Exception as e:
                print(f"Error: {e}")

    if not results:
        return {"tier": "MEDIUM", "confidence": 0.5, "consensus": False, "votes": {}}

    # Count votes
    tier_votes = {}
    tier_confidence = {}
    reasonings = []

    for r in results:
        tier = r.get("tier", "MEDIUM").upper()
        conf = r.get("confidence", 0.7)
        tier_votes[tier] = tier_votes.get(tier, 0) + 1
        tier_confidence[tier] = tier_confidence.get(tier, []) + [conf]
        if r.get("reasoning"):
            reasonings.append(f"{r['source']}: {r['reasoning']}")

    # Find winner
    winner = max(tier_votes, key=tier_votes.get)
    vote_count = tier_votes[winner]
    avg_confidence = sum(tier_confidence[winner]) / len(tier_confidence[winner])

    return {
        "tier": winner,
        "confidence": round(avg_confidence, 2),
        "consensus": vote_count >= 2,
        "votes": tier_votes,
        "reasonings": reasonings,
        "ai_count": len(results)
    }


def calculate_pricing_window(event_date_str, tier):
    """Calculate start and end dates for pricing window"""
    # Parse event date (assume current/next year)
    try:
        event_date = datetime.strptime(event_date_str, "%B %d")
        event_date = event_date.replace(year=datetime.now().year)
        if event_date < datetime.now():
            event_date = event_date.replace(year=datetime.now().year + 1)
    except:
        try:
            event_date = datetime.strptime(event_date_str, "%b %d")
            event_date = event_date.replace(year=datetime.now().year)
            if event_date < datetime.now():
                event_date = event_date.replace(year=datetime.now().year + 1)
        except:
            return None

    window_days = PRICING_TIERS[tier]["window_days"]

    # Price increase starts X days before, ends 2 days after
    start_date = event_date - timedelta(days=window_days)
    end_date = event_date + timedelta(days=2)

    return {
        "event_date": event_date.strftime("%Y-%m-%d"),
        "price_start": start_date.strftime("%Y-%m-%d"),
        "price_end": end_date.strftime("%Y-%m-%d"),
        "window_days": window_days
    }


def generate_pricing_recommendation(item_name, category, event_name, event_date):
    """Generate full pricing recommendation with AI consensus"""

    # Get AI consensus on tier
    consensus = get_ai_consensus(item_name, category, event_name, event_date)
    tier = consensus["tier"]

    # Get base price
    base_price = BASE_PRICES.get(category, BASE_PRICES["default"])

    # Calculate new price
    increase_pct = PRICING_TIERS[tier]["increase"]
    new_price = round(base_price * (1 + increase_pct / 100), 2)

    # Calculate window
    window = calculate_pricing_window(event_date, tier)

    return {
        "item": item_name,
        "category": category,
        "event": event_name,
        "event_date": event_date,
        "base_price": base_price,
        "tier": tier,
        "increase_percent": increase_pct,
        "new_price": new_price,
        "window": window,
        "ai_consensus": consensus
    }


def format_email_block(recommendation):
    """Format recommendation as extractable email block"""
    r = recommendation
    w = r.get("window", {})
    c = r.get("ai_consensus", {})

    email_block = f"""
================================================================================
DATEDRIVEN PRICING RECOMMENDATION
================================================================================

ITEM: {r['item']}
CATEGORY: {r['category']}
EVENT: {r['event']}

--------------------------------------------------------------------------------
PRICING DECISION
--------------------------------------------------------------------------------
TIER: {r['tier']}
BASE_PRICE: ${r['base_price']:.2f}
INCREASE: +{r['increase_percent']}%
NEW_PRICE: ${r['new_price']:.2f}

--------------------------------------------------------------------------------
PRICING WINDOW
--------------------------------------------------------------------------------
START_DATE: {w.get('price_start', 'N/A')}
END_DATE: {w.get('price_end', 'N/A')}
EVENT_DATE: {w.get('event_date', 'N/A')}

--------------------------------------------------------------------------------
AI CONSENSUS
--------------------------------------------------------------------------------
CONSENSUS_REACHED: {c.get('consensus', False)}
CONFIDENCE: {c.get('confidence', 0):.0%}
VOTES: {c.get('votes', {})}
AI_COUNT: {c.get('ai_count', 0)}

REASONING:
{chr(10).join('  - ' + r for r in c.get('reasonings', []))}

================================================================================
"""
    return email_block


def format_json_extract(recommendation):
    """Format as JSON for automated extraction"""
    r = recommendation
    w = r.get("window", {})

    return {
        "item": r["item"],
        "tier": r["tier"],
        "base_price": r["base_price"],
        "new_price": r["new_price"],
        "increase_percent": r["increase_percent"],
        "start_date": w.get("price_start"),
        "end_date": w.get("price_end"),
        "event_date": w.get("event_date"),
        "consensus": r["ai_consensus"].get("consensus"),
        "confidence": r["ai_consensus"].get("confidence")
    }


# Test with sample items
if __name__ == "__main__":
    test_items = [
        {"item": "John Lennon Portrait Print", "category": "beatles", "event": "John Lennon Death Anniversary", "date": "December 8"},
        {"item": "Apollo 11 Signed Memorabilia", "category": "space_nasa", "event": "Moon Landing Anniversary", "date": "July 20"},
        {"item": "Taylor Swift Signed Guitar", "category": "musicians", "event": "Eras Tour Concert", "date": "March 15"},
    ]

    print("=" * 60)
    print("DATEDRIVEN PRICING ENGINE - TEST RUN")
    print("=" * 60)

    all_recommendations = []

    for item in test_items:
        print(f"\nProcessing: {item['item']}...")
        rec = generate_pricing_recommendation(
            item["item"], item["category"], item["event"], item["date"]
        )
        all_recommendations.append(rec)
        print(format_email_block(rec))

    # Output JSON summary
    print("\n" + "=" * 60)
    print("JSON EXTRACT (for automation)")
    print("=" * 60)
    json_data = [format_json_extract(r) for r in all_recommendations]
    print(json.dumps(json_data, indent=2))
