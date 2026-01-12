#!/usr/bin/env python3
"""
DATARADAR - Direct eBay Pricing Automation
Uses Trading API to update prices on ANY listing
"""

import os
import json
import base64
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pickle
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from pricing_engine import (
    get_ai_consensus, calculate_pricing_window,
    PRICING_TIERS, BASE_PRICES
)

os.chdir('/Users/johnshay/DATARADAR')

# Read .env
env_vars = {}
with open('.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env_vars[key] = value

EBAY_CLIENT_ID = env_vars.get('EBAY_CLIENT_ID')
EBAY_CLIENT_SECRET = env_vars.get('EBAY_CLIENT_SECRET')
EBAY_DEV_ID = env_vars.get('EBAY_DEV_ID')
EBAY_REFRESH_TOKEN = env_vars.get('EBAY_REFRESH_TOKEN')

# eBay Trading API endpoint
TRADING_API_URL = "https://api.ebay.com/ws/api.dll"


class EbayTradingAPI:
    """eBay Trading API client for price updates"""

    def __init__(self):
        self.access_token = None
        self.token_expiry = None

    def get_access_token(self):
        """Get OAuth access token"""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token

        credentials = f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}"
        encoded_creds = base64.b64encode(credentials.encode()).decode()

        response = requests.post(
            'https://api.ebay.com/identity/v1/oauth2/token',
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {encoded_creds}'
            },
            data={
                'grant_type': 'refresh_token',
                'refresh_token': EBAY_REFRESH_TOKEN,
                'scope': 'https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory'
            }
        )

        if response.status_code == 200:
            data = response.json()
            self.access_token = data['access_token']
            self.token_expiry = datetime.now() + timedelta(seconds=data.get('expires_in', 7200) - 300)
            return self.access_token
        else:
            raise Exception(f"Token error: {response.text}")

    def get_active_listings(self, page=1, per_page=100):
        """Get all active listings using GetMyeBaySelling"""
        token = self.get_access_token()

        xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{token}</eBayAuthToken>
    </RequesterCredentials>
    <ActiveList>
        <Include>true</Include>
        <Pagination>
            <EntriesPerPage>{per_page}</EntriesPerPage>
            <PageNumber>{page}</PageNumber>
        </Pagination>
    </ActiveList>
    <DetailLevel>ReturnAll</DetailLevel>
</GetMyeBaySellingRequest>"""

        headers = {
            'X-EBAY-API-SITEID': '0',
            'X-EBAY-API-COMPATIBILITY-LEVEL': '967',
            'X-EBAY-API-CALL-NAME': 'GetMyeBaySelling',
            'X-EBAY-API-IAF-TOKEN': token,
            'Content-Type': 'text/xml'
        }

        response = requests.post(TRADING_API_URL, headers=headers, data=xml_request)
        return self._parse_listings_response(response.text)

    def _parse_listings_response(self, xml_text):
        """Parse GetMyeBaySelling response"""
        listings = []
        try:
            root = ET.fromstring(xml_text)
            ns = {'ebay': 'urn:ebay:apis:eBLBaseComponents'}

            # Check for errors
            ack = root.find('.//ebay:Ack', ns)
            if ack is not None and ack.text != 'Success':
                errors = root.findall('.//ebay:Errors/ebay:ShortMessage', ns)
                error_msgs = [e.text for e in errors if e.text]
                print(f"API Warning: {error_msgs}")

            # Parse active items
            items = root.findall('.//ebay:ActiveList/ebay:ItemArray/ebay:Item', ns)
            for item in items:
                item_id = item.find('ebay:ItemID', ns)
                title = item.find('ebay:Title', ns)
                price = item.find('.//ebay:CurrentPrice', ns)
                quantity = item.find('ebay:Quantity', ns)

                if item_id is not None:
                    listings.append({
                        'item_id': item_id.text,
                        'title': title.text if title is not None else 'Unknown',
                        'current_price': float(price.text) if price is not None else 0,
                        'quantity': int(quantity.text) if quantity is not None else 0
                    })
        except ET.ParseError as e:
            print(f"XML Parse error: {e}")
            print(f"Response: {xml_text[:500]}")

        return listings

    def update_price(self, item_id, new_price):
        """Update price for a single listing using ReviseFixedPriceItem"""
        token = self.get_access_token()

        xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<ReviseFixedPriceItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{token}</eBayAuthToken>
    </RequesterCredentials>
    <Item>
        <ItemID>{item_id}</ItemID>
        <StartPrice>{new_price:.2f}</StartPrice>
    </Item>
</ReviseFixedPriceItemRequest>"""

        headers = {
            'X-EBAY-API-SITEID': '0',
            'X-EBAY-API-COMPATIBILITY-LEVEL': '967',
            'X-EBAY-API-CALL-NAME': 'ReviseFixedPriceItem',
            'X-EBAY-API-IAF-TOKEN': token,
            'Content-Type': 'text/xml'
        }

        response = requests.post(TRADING_API_URL, headers=headers, data=xml_request)
        return self._parse_revise_response(response.text, item_id)

    def _parse_revise_response(self, xml_text, item_id):
        """Parse ReviseFixedPriceItem response"""
        try:
            root = ET.fromstring(xml_text)
            ns = {'ebay': 'urn:ebay:apis:eBLBaseComponents'}

            ack = root.find('.//ebay:Ack', ns)
            if ack is not None and ack.text in ['Success', 'Warning']:
                return {'success': True, 'item_id': item_id}
            else:
                errors = root.findall('.//ebay:Errors/ebay:LongMessage', ns)
                error_msgs = [e.text for e in errors if e.text]
                return {'success': False, 'item_id': item_id, 'errors': error_msgs}
        except ET.ParseError as e:
            return {'success': False, 'item_id': item_id, 'errors': [str(e)]}


def categorize_listing(title):
    """Determine category and base price from listing title"""
    title_lower = title.lower()

    if any(x in title_lower for x in ['death nyc']):
        return 'death_nyc', 89
    elif any(x in title_lower for x in ['shepard fairey', 'obey giant']):
        return 'shepard_fairey', 300
    elif any(x in title_lower for x in ['lennon', 'beatles', 'harrison', 'yoko', 'bag one']):
        return 'beatles', 500
    elif any(x in title_lower for x in ['apollo', 'armstrong', 'aldrin', 'collins', 'nasa', 'space']):
        return 'space_nasa', 900
    elif any(x in title_lower for x in ['disney', 'snow white', 'mickey', 'swarovski']):
        return 'disney', 150
    elif any(x in title_lower for x in ['guitar', 'signed', 'taylor swift', 'green day', 'blink', 'coldplay', 'flea']):
        return 'musicians', 900
    elif any(x in title_lower for x in ['muhammad ali', 'ali']):
        return 'death_nyc', 89
    elif any(x in title_lower for x in ['warhol', 'mao', 'wonder woman']):
        return 'death_nyc', 89
    else:
        return 'default', 100


def get_google_creds():
    """Load Google credentials with auto-refresh"""
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
            except:
                pass
        return creds
    return None


def get_active_pricing_windows():
    """Get pricing windows from Google Sheet - falls back to JSON if sheet unavailable"""
    SHEET_ID = '11a-_IWhljPJHeKV8vdke-JiLmm_KCq-bedSceKB0kZI'
    today = datetime.now().strftime('%Y-%m-%d')

    # Try to read from Google Sheet first
    try:
        creds = get_google_creds()
        if creds:
            service = build('sheets', 'v4', credentials=creds)
            result = service.spreadsheets().values().get(
                spreadsheetId=SHEET_ID,
                range="'PRICING_RULES'!A4:H100"
            ).execute()

            rows = result.get('values', [])
            active = []

            for row in rows:
                if len(row) >= 7 and row[0] and row[1]:
                    # Check if active
                    is_active = row[7].upper() if len(row) > 7 else 'Y'
                    if is_active != 'Y':
                        continue

                    # Parse keywords
                    keywords = [kw.strip() for kw in row[1].split(',')]

                    # Parse dates and check if active
                    start_date = row[5] if len(row) > 5 else ''
                    end_date = row[6] if len(row) > 6 else ''

                    if start_date and end_date and start_date <= today <= end_date:
                        try:
                            increase = int(row[4]) if row[4] else 10
                        except:
                            increase = 10

                        active.append({
                            'item': row[0],
                            'keywords': keywords,
                            'event': row[2] if len(row) > 2 else '',
                            'tier': row[3] if len(row) > 3 else 'MEDIUM',
                            'increase_percent': increase,
                            'start_date': start_date,
                            'end_date': end_date
                        })

            print(f"Loaded {len(active)} active rules from Google Sheet")

            # Sync to JSON backup whenever sheet is read successfully
            try:
                all_rules = []
                for row in rows:
                    if len(row) >= 7 and row[0] and row[1]:
                        is_active = row[7].upper() if len(row) > 7 else 'Y'
                        if is_active != 'Y':
                            continue
                        keywords = [kw.strip() for kw in row[1].split(',')]
                        try:
                            increase = int(row[4]) if row[4] else 10
                        except:
                            increase = 10
                        all_rules.append({
                            'item': row[0],
                            'keywords': keywords,
                            'event': row[2] if len(row) > 2 else '',
                            'tier': row[3] if len(row) > 3 else 'MEDIUM',
                            'increase_percent': increase,
                            'start_date': row[5] if len(row) > 5 else '',
                            'end_date': row[6] if len(row) > 6 else ''
                        })
                with open('pricing_rules.json', 'w') as f:
                    json.dump(all_rules, f, indent=2)
            except:
                pass  # Don't fail if backup sync fails

            return active
    except Exception as e:
        print(f"Sheet read error, falling back to JSON: {e}")

    # Fallback to JSON file
    try:
        with open('pricing_rules.json', 'r') as f:
            rules = json.load(f)
    except FileNotFoundError:
        print("No pricing_rules.json found.")
        return []

    active = []
    for rule in rules:
        start = rule.get('start_date')
        end = rule.get('end_date')
        if start and end and start <= today <= end:
            active.append(rule)

    return active


def match_listing_to_rule(listing_title, rules):
    """Find matching pricing rule for a listing"""
    title_lower = listing_title.lower()

    for rule in rules:
        keywords = rule.get('keywords', [])
        for kw in keywords:
            if kw.lower() in title_lower:
                return rule
    return None


def run_pricing_update(dry_run=True):
    """Main function to update eBay prices based on active windows"""
    print("=" * 70)
    print(f"DATEDRIVEN - eBay Auto Pricing {'(DRY RUN)' if dry_run else '(LIVE)'}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Initialize eBay API
    ebay = EbayTradingAPI()

    # Get active listings
    print("\nFetching active eBay listings...")
    listings = ebay.get_active_listings()
    print(f"Found {len(listings)} active listings")

    if not listings:
        print("No active listings found.")
        return

    # Get active pricing windows
    print("\nChecking active pricing windows...")
    active_rules = get_active_pricing_windows()
    print(f"Found {len(active_rules)} active pricing windows")

    # Process each listing
    updates = []
    skipped = []

    for listing in listings:
        item_id = listing['item_id']
        title = listing['title']
        current_price = listing['current_price']

        # Try to match to a rule
        rule = match_listing_to_rule(title, active_rules)

        if rule:
            tier = rule['tier']
            increase_pct = rule['increase_percent']

            # Calculate new price as % increase from CURRENT price
            new_price = round(current_price * (1 + increase_pct / 100), 2)

            # Only update if price would actually increase
            if new_price > current_price:
                updates.append({
                    'item_id': item_id,
                    'title': title[:50],
                    'current_price': current_price,
                    'new_price': new_price,
                    'tier': tier,
                    'increase_pct': increase_pct,
                    'event': rule.get('event', 'Unknown')
                })
        else:
            skipped.append({'item_id': item_id, 'title': title[:50]})

    # Summary
    print(f"\n{'=' * 70}")
    print("PRICING UPDATE SUMMARY")
    print(f"{'=' * 70}")
    print(f"Listings to update: {len(updates)}")
    print(f"Listings skipped (no matching rule): {len(skipped)}")

    if updates:
        print(f"\nPRICE CHANGES:")
        print("-" * 70)
        for u in updates:
            print(f"  {u['tier']:6} | ${u['current_price']:>8.2f} -> ${u['new_price']:>8.2f} (+{u['increase_pct']}%) | {u['title']}")

    # Execute updates
    if not dry_run and updates:
        print(f"\n{'=' * 70}")
        print("EXECUTING PRICE UPDATES...")
        print(f"{'=' * 70}")

        success_count = 0
        fail_count = 0

        for u in updates:
            result = ebay.update_price(u['item_id'], u['new_price'])
            if result['success']:
                print(f"  ✅ {u['title'][:40]} -> ${u['new_price']:.2f}")
                success_count += 1
            else:
                print(f"  ❌ {u['title'][:40]} - {result.get('errors', ['Unknown error'])}")
                fail_count += 1

        print(f"\nResults: {success_count} updated, {fail_count} failed")

    elif dry_run and updates:
        print(f"\n⚠️  DRY RUN - No changes made. Run with dry_run=False to apply.")

    # Save log
    log = {
        'timestamp': datetime.now().isoformat(),
        'dry_run': dry_run,
        'listings_found': len(listings),
        'active_rules': len(active_rules),
        'updates_planned': len(updates),
        'updates': updates
    }

    log_file = f"pricing_log_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(log_file, 'w') as f:
        json.dump(log, f, indent=2)
    print(f"\n✅ Log saved: {log_file}")

    return updates


def revert_prices(log_file):
    """Revert prices from a previous update using log file"""
    print(f"Reverting prices from: {log_file}")

    with open(log_file, 'r') as f:
        log = json.load(f)

    ebay = EbayTradingAPI()

    for u in log.get('updates', []):
        result = ebay.update_price(u['item_id'], u['current_price'])
        if result['success']:
            print(f"  ✅ Reverted: {u['title'][:40]} -> ${u['current_price']:.2f}")
        else:
            print(f"  ❌ Failed: {u['title'][:40]}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--live':
        run_pricing_update(dry_run=False)
    elif len(sys.argv) > 1 and sys.argv[1] == '--revert':
        if len(sys.argv) > 2:
            revert_prices(sys.argv[2])
        else:
            print("Usage: python ebay_auto_pricing.py --revert <log_file.json>")
    else:
        run_pricing_update(dry_run=True)
