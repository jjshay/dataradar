#!/usr/bin/env python3
"""
eBay Pricing Automation for DateDriven
Automatically adjusts prices based on upcoming key dates from Google Calendar
"""

import os
import pickle
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
EBAY_SCOPES = ['https://api.ebay.com/oauth/api_scope/sell.inventory']

# Pricing rules: days before event -> price multiplier
DEFAULT_PRICING_RULES = {
    14: 1.15,   # 14+ days before: 15% markup
    7: 1.25,   # 7-13 days before: 25% markup
    3: 1.35,   # 3-6 days before: 35% markup (peak demand)
    0: 1.20,   # 0-2 days before: 20% markup (last chance)
    -7: 1.0,   # After event: back to base price
}


class EbayPricingClient:
    """eBay Inventory API client for price updates"""

    def __init__(self):
        self.client_id = os.getenv("EBAY_CLIENT_ID")
        self.client_secret = os.getenv("EBAY_CLIENT_SECRET")
        self.refresh_token = os.getenv("EBAY_REFRESH_TOKEN")
        self.access_token = None
        self.base_url = "https://api.ebay.com/sell/inventory/v1"

    def authenticate(self):
        """Get OAuth access token using refresh token"""
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            print("eBay API credentials not configured. Set these in .env:")
            print("  EBAY_CLIENT_ID=your_client_id")
            print("  EBAY_CLIENT_SECRET=your_client_secret")
            print("  EBAY_REFRESH_TOKEN=your_refresh_token")
            print("\nTo get credentials:")
            print("  1. Go to https://developer.ebay.com/")
            print("  2. Create an application")
            print("  3. Generate a User Token with sell.inventory scope")
            return False

        try:
            auth_url = "https://api.ebay.com/identity/v1/oauth2/token"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "scope": " ".join(EBAY_SCOPES)
            }

            resp = requests.post(
                auth_url,
                headers=headers,
                data=data,
                auth=(self.client_id, self.client_secret)
            )

            if resp.status_code == 200:
                self.access_token = resp.json()["access_token"]
                return True
            else:
                print(f"eBay auth failed: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"eBay auth error: {e}")
            return False

    def update_price(self, sku: str, offer_id: str, new_price: float, currency: str = "USD"):
        """Update price for a single listing"""
        if not self.access_token:
            if not self.authenticate():
                return None

        url = f"{self.base_url}/bulk_update_price_quantity"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "requests": [{
                "sku": sku,
                "offers": [{
                    "offerId": offer_id,
                    "price": {
                        "currency": currency,
                        "value": str(round(new_price, 2))
                    }
                }]
            }]
        }

        try:
            resp = requests.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"Price update failed: {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            print(f"Price update error: {e}")
            return None

    def bulk_update_prices(self, updates: list):
        """
        Bulk update prices for multiple listings
        updates: list of {"sku": str, "offer_id": str, "price": float}
        """
        if not self.access_token:
            if not self.authenticate():
                return None

        url = f"{self.base_url}/bulk_update_price_quantity"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # eBay allows up to 25 offers per call
        results = []
        for i in range(0, len(updates), 25):
            batch = updates[i:i+25]
            payload = {
                "requests": [{
                    "sku": item["sku"],
                    "offers": [{
                        "offerId": item["offer_id"],
                        "price": {
                            "currency": item.get("currency", "USD"),
                            "value": str(round(item["price"], 2))
                        }
                    }]
                } for item in batch]
            }

            try:
                resp = requests.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    results.extend(resp.json().get("responses", []))
                else:
                    print(f"Batch update failed: {resp.status_code}")
            except Exception as e:
                print(f"Batch update error: {e}")

        return results


class CalendarPricingEngine:
    """Reads calendar events and calculates dynamic prices"""

    def __init__(self, pricing_rules: dict = None):
        self.pricing_rules = pricing_rules or DEFAULT_PRICING_RULES
        self.calendar_service = None

    def get_calendar_service(self):
        """Authenticate with Google Calendar API"""
        creds = None

        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', CALENDAR_SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.calendar_service = build('calendar', 'v3', credentials=creds)
        return self.calendar_service

    def get_upcoming_events(self, days_ahead: int = 30):
        """Get all DateDriven events in the next N days"""
        if not self.calendar_service:
            self.get_calendar_service()

        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'

        events_result = self.calendar_service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            q='List:'  # Filter for DateDriven events
        ).execute()

        return events_result.get('items', [])

    def calculate_multiplier(self, days_until_event: int) -> float:
        """Calculate price multiplier based on days until event"""
        sorted_thresholds = sorted(self.pricing_rules.keys(), reverse=True)

        for threshold in sorted_thresholds:
            if days_until_event >= threshold:
                return self.pricing_rules[threshold]

        return 1.0  # Default: no change

    def get_pricing_recommendations(self, inventory_df: pd.DataFrame, days_ahead: int = 30):
        """
        Match calendar events to inventory and calculate recommended prices

        inventory_df should have columns: Title, SKU, OfferID, BasePrice
        """
        events = self.get_upcoming_events(days_ahead)
        recommendations = []

        print(f"\n Found {len(events)} upcoming DateDriven events")

        for event in events:
            summary = event.get('summary', '')

            # Extract artwork name from "List: Artwork Name"
            if 'List:' in summary:
                artwork_name = summary.split('List:')[1].strip()
            else:
                continue

            # Get event date
            start = event.get('start', {})
            event_date_str = start.get('date') or start.get('dateTime', '')[:10]

            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d')
            except:
                continue

            days_until = (event_date - datetime.now()).days
            multiplier = self.calculate_multiplier(days_until)

            # Find matching inventory items
            for idx, row in inventory_df.iterrows():
                title = str(row.get('Title', ''))

                # Fuzzy match - check if artwork name appears in title
                if artwork_name.lower()[:30] in title.lower() or title.lower()[:30] in artwork_name.lower():
                    base_price = float(row.get('BasePrice', row.get('Price', 0)))

                    if base_price > 0:
                        recommendations.append({
                            'title': title,
                            'sku': row.get('SKU', ''),
                            'offer_id': row.get('OfferID', ''),
                            'event': event.get('description', '').split('\n')[0],
                            'event_date': event_date_str,
                            'days_until': days_until,
                            'base_price': base_price,
                            'multiplier': multiplier,
                            'recommended_price': round(base_price * multiplier, 2)
                        })

        return recommendations


class ThreeDSellersClient:
    """
    3DSellers integration (if API available)
    Note: 3DSellers API availability varies - check your plan
    """

    def __init__(self):
        self.api_key = os.getenv("THREE_D_SELLERS_API_KEY")
        self.base_url = "https://api.3dsellers.com/v1"  # Placeholder

    def is_configured(self):
        return bool(self.api_key)

    def update_price(self, listing_id: str, new_price: float):
        """Update price via 3DSellers API"""
        if not self.is_configured():
            print("3DSellers API key not configured")
            print("Add THREE_D_SELLERS_API_KEY to your .env file")
            print("\nAlternatively, use 3DSellers' built-in automation rules:")
            print("  1. Log into 3DSellers dashboard")
            print("  2. Go to Automation > Rules")
            print("  3. Create rules based on your catalog categories")
            return None

        # Implementation depends on 3DSellers API documentation
        # This is a placeholder for when API details are available
        pass


def run_pricing_automation(
    inventory_path: str,
    days_ahead: int = 30,
    dry_run: bool = True,
    pricing_rules: dict = None
):
    """
    Main function to run pricing automation

    Args:
        inventory_path: Path to Excel with columns: Title, SKU, OfferID, BasePrice
        days_ahead: How many days ahead to look for events
        dry_run: If True, only show recommendations without updating
        pricing_rules: Custom pricing rules (days -> multiplier)
    """

    print("=" * 60)
    print("DATEDRIVEN PRICING AUTOMATION")
    print("=" * 60)

    # Load inventory
    try:
        inventory_df = pd.read_excel(inventory_path)
        print(f"\nLoaded {len(inventory_df)} inventory items")
    except Exception as e:
        print(f"Failed to load inventory: {e}")
        return

    # Initialize pricing engine
    engine = CalendarPricingEngine(pricing_rules)
    recommendations = engine.get_pricing_recommendations(inventory_df, days_ahead)

    if not recommendations:
        print("\nNo pricing recommendations - no matching events found")
        return

    print(f"\n{'='*60}")
    print(f"PRICING RECOMMENDATIONS ({len(recommendations)} items)")
    print(f"{'='*60}\n")

    for rec in recommendations:
        print(f"  {rec['title'][:50]}...")
        print(f"    Event: {rec['event'][:40]}... ({rec['days_until']} days)")
        print(f"    Price: ${rec['base_price']:.2f} -> ${rec['recommended_price']:.2f} ({rec['multiplier']:.0%})")
        print()

    if dry_run:
        print("\n[DRY RUN] No prices updated. Set dry_run=False to apply changes.")
        return recommendations

    # Apply price updates via eBay API
    ebay_client = EbayPricingClient()

    updates = [
        {
            'sku': rec['sku'],
            'offer_id': rec['offer_id'],
            'price': rec['recommended_price']
        }
        for rec in recommendations
        if rec['sku'] and rec['offer_id']
    ]

    if updates:
        print(f"\nUpdating {len(updates)} listings on eBay...")
        results = ebay_client.bulk_update_prices(updates)

        if results:
            success = sum(1 for r in results if r.get('statusCode') == 200)
            print(f"Successfully updated {success}/{len(updates)} listings")
    else:
        print("\nNo SKU/OfferID data available for eBay updates")
        print("Add SKU and OfferID columns to your inventory file")

    return recommendations


if __name__ == "__main__":
    import sys

    inventory_path = sys.argv[1] if len(sys.argv) > 1 else "/Applications/3DSELLERS.xlsx"

    # Show recommendations only (dry run)
    run_pricing_automation(
        inventory_path=inventory_path,
        days_ahead=30,
        dry_run=True,
        pricing_rules={
            14: 1.15,   # 15% markup 2+ weeks out
            7: 1.25,    # 25% markup 1-2 weeks out
            3: 1.35,    # 35% markup final week
            0: 1.20,    # 20% markup day-of
            -7: 1.0,    # Back to normal after
        }
    )
