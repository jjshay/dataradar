#!/usr/bin/env python3
"""
DATARADAR - Daily Deal Scanner (PythonAnywhere Version)
Reads artists from News Google Sheet and scans eBay for deals
"""

import os
import json
import pickle
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv

# Get the directory where this script lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Google Sheet config
NEWS_SHEET_ID = os.getenv('DATARADAR_SHEET_ID', '11a-_IWhljPJHeKV8vdke-JiLmm_KCq-bedSceKB0kZI')

# eBay credentials
EBAY_CLIENT_ID = os.getenv('EBAY_CLIENT_ID')
EBAY_CLIENT_SECRET = os.getenv('EBAY_CLIENT_SECRET')


def get_google_creds():
    """Load Google credentials with auto-refresh"""
    token_path = os.path.join(BASE_DIR, 'token.pickle')
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

        if creds and creds.expired and creds.refresh_token:
            try:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                print("Token refreshed successfully")
            except Exception as e:
                print(f"Token refresh failed: {e}")
                return None

        return creds
    return None


def get_ebay_token():
    """Get eBay Browse API token"""
    credentials = f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}"
    encoded_creds = base64.b64encode(credentials.encode()).decode()

    response = requests.post(
        'https://api.ebay.com/identity/v1/oauth2/token',
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {encoded_creds}'
        },
        data={
            'grant_type': 'client_credentials',
            'scope': 'https://api.ebay.com/oauth/api_scope'
        }
    )
    return response.json().get('access_token')


def read_news_sheet():
    """Read artists/events from News Google Sheet - PRICERADAR tab"""
    creds = get_google_creds()
    if not creds:
        print("No Google credentials available")
        return []

    from googleapiclient.discovery import build
    service = build('sheets', 'v4', credentials=creds)

    all_artists = []

    try:
        print("Reading PRICERADAR tab...")
        result = service.spreadsheets().values().get(
            spreadsheetId=NEWS_SHEET_ID,
            range="'PRICERADAR'!A:H"
        ).execute()

        rows = result.get('values', [])
        if rows:
            header = [h.upper() if h else '' for h in rows[0]]
            brand_idx = header.index('BRAND') if 'BRAND' in header else 3

            for row in rows[1:]:
                if len(row) > brand_idx and row[brand_idx]:
                    brand = row[brand_idx].strip()
                    if brand and len(brand) > 1:
                        all_artists.append({
                            'name': brand,
                            'source_tab': 'PRICERADAR',
                            'title': row[4] if len(row) > 4 else ''
                        })

        return all_artists

    except Exception as e:
        print(f"Error reading sheet: {e}")
        return []


def search_ebay_deals(query, max_price=200, limit=10):
    """Search eBay for deals"""
    token = get_ebay_token()

    headers = {
        'Authorization': f'Bearer {token}',
        'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US',
        'Content-Type': 'application/json'
    }

    params = {
        'q': f'{query} signed',
        'filter': f'price:[..{max_price}],priceCurrency:USD',
        'sort': 'newlyListed',
        'limit': limit
    }

    try:
        resp = requests.get(
            'https://api.ebay.com/buy/browse/v1/item_summary/search',
            headers=headers,
            params=params
        )

        if resp.status_code != 200:
            return []

        data = resp.json()
        items = data.get('itemSummaries', [])

        deals = []
        for item in items:
            price_info = item.get('price', {})
            price = float(price_info.get('value', 0))

            if price <= 0:
                continue

            deals.append({
                'id': item.get('itemId', ''),
                'title': item.get('title', 'Unknown'),
                'price': price,
                'url': item.get('itemWebUrl', ''),
                'condition': item.get('condition', 'Unknown'),
                'seller': item.get('seller', {}).get('username', 'Unknown'),
                'listed_date': item.get('itemCreationDate', '')
            })

        return deals
    except Exception as e:
        print(f"Search error for {query}: {e}")
        return []


def run_daily_scan():
    """Main daily scan function"""
    print("=" * 60)
    print(f"DATARADAR - Daily Deal Scanner (PythonAnywhere)")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Base Dir: {BASE_DIR}")
    print("=" * 60)

    # Read artists from News sheet
    print("\nReading News spreadsheet...")
    artists = read_news_sheet()

    if not artists:
        print("No artists found in sheet. Using default targets...")
        artists = [
            {'name': 'Death NYC', 'source_tab': 'default'},
            {'name': 'Shepard Fairey', 'source_tab': 'default'},
            {'name': 'Blink 182', 'source_tab': 'default'},
            {'name': 'Green Day', 'source_tab': 'default'},
            {'name': 'Taylor Swift', 'source_tab': 'default'},
            {'name': 'Foo Fighters', 'source_tab': 'default'},
        ]

    print(f"Found {len(artists)} artists to scan")

    # Deduplicate
    unique_artists = list({a['name']: a for a in artists}.values())
    print(f"Unique artists: {len(unique_artists)}")

    # Scan for deals
    all_deals = []

    for artist in unique_artists[:20]:
        name = artist['name']
        print(f"\nScanning: {name}...")

        deals = search_ebay_deals(name, max_price=300, limit=5)

        for deal in deals:
            deal['artist'] = name
            deal['source_tab'] = artist.get('source_tab', '')
            all_deals.append(deal)

        if deals:
            print(f"  Found {len(deals)} items")

    # Sort by price
    all_deals.sort(key=lambda x: x['price'])

    # Save results
    results = {
        'scan_date': datetime.now().isoformat(),
        'artists_scanned': len(unique_artists),
        'deals_found': len(all_deals),
        'deals': all_deals
    }

    results_file = os.path.join(BASE_DIR, f"scan_results_{datetime.now().strftime('%Y%m%d')}.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"SCAN COMPLETE")
    print(f"{'=' * 60}")
    print(f"Artists scanned: {len(unique_artists)}")
    print(f"Deals found: {len(all_deals)}")
    print(f"Results saved: {results_file}")

    # Show top deals
    if all_deals:
        print(f"\nTOP 10 DEALS:")
        print("-" * 60)
        for deal in all_deals[:10]:
            print(f"  ${deal['price']:>7.2f} | {deal['artist'][:15]:15} | {deal['title'][:40]}")

    return results


if __name__ == "__main__":
    run_daily_scan()
