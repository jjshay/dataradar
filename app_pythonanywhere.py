#!/usr/bin/env python3
"""
DATARADAR - PythonAnywhere Compatible Version
"""

from flask import Flask, render_template, jsonify, request
import os
import json
import base64
import requests
import pickle
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Get the directory where this script lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load environment variables
load_dotenv(os.path.join(BASE_DIR, '.env'))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))

# eBay credentials from environment
EBAY_CLIENT_ID = os.getenv('EBAY_CLIENT_ID')
EBAY_CLIENT_SECRET = os.getenv('EBAY_CLIENT_SECRET')
EBAY_REFRESH_TOKEN = os.getenv('EBAY_REFRESH_TOKEN')

# Google Sheet config
DATARADAR_SHEET_ID = os.getenv('DATARADAR_SHEET_ID', '11a-_IWhljPJHeKV8vdke-JiLmm_KCq-bedSceKB0kZI')

# Cache for listings and sheet data
_cache = {'listings': [], 'last_fetch': None, 'deal_targets': [], 'targets_fetch': None}


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
            except Exception as e:
                print(f"Token refresh error: {e}")
        return creds
    return None


def get_deal_targets():
    """Read deal targets from Google Sheet - cached for 5 minutes"""
    if _cache['targets_fetch']:
        age = (datetime.now() - _cache['targets_fetch']).seconds
        if age < 300 and _cache['deal_targets']:
            return _cache['deal_targets']

    try:
        creds = get_google_creds()
        if not creds:
            return DEAL_TARGETS_FALLBACK

        from googleapiclient.discovery import build
        service = build('sheets', 'v4', credentials=creds)
        result = service.spreadsheets().values().get(
            spreadsheetId=DATARADAR_SHEET_ID,
            range="'DATARADAR'!A4:D100"
        ).execute()

        rows = result.get('values', [])
        targets = []

        for row in rows:
            if len(row) >= 3 and row[0] and row[1]:
                active = row[3].upper() if len(row) > 3 else 'Y'
                if active == 'Y':
                    try:
                        max_price = float(row[2]) if row[2] else 100
                    except:
                        max_price = 100
                    targets.append({
                        'category': row[0],
                        'query': row[1],
                        'max_price': max_price
                    })

        if targets:
            _cache['deal_targets'] = targets
            _cache['targets_fetch'] = datetime.now()
            return targets
    except Exception as e:
        print(f"Sheet read error: {e}")

    return DEAL_TARGETS_FALLBACK


# Fallback targets if sheet unavailable
DEAL_TARGETS_FALLBACK = [
    {'query': 'Death NYC signed', 'max_price': 50, 'category': 'Art'},
    {'query': 'Shepard Fairey signed print', 'max_price': 150, 'category': 'Art'},
    {'query': 'Blink 182 signed', 'max_price': 250, 'category': 'Music'},
    {'query': 'Apollo 11 signed photo', 'max_price': 500, 'category': 'Space'},
]


def get_access_token():
    """Get eBay OAuth token"""
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
            'scope': 'https://api.ebay.com/oauth/api_scope'
        }
    )
    return response.json().get('access_token')


def fetch_listings(force=False):
    """Fetch all active listings from eBay"""
    if not force and _cache['last_fetch']:
        age = (datetime.now() - _cache['last_fetch']).seconds
        if age < 300 and _cache['listings']:
            return _cache['listings']

    token = get_access_token()
    all_listings = []
    page = 1

    while page <= 5:
        xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{token}</eBayAuthToken>
    </RequesterCredentials>
    <ActiveList>
        <Include>true</Include>
        <Pagination>
            <EntriesPerPage>100</EntriesPerPage>
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

        resp = requests.post("https://api.ebay.com/ws/api.dll", headers=headers, data=xml_request)
        root = ET.fromstring(resp.text)
        ns = {'ebay': 'urn:ebay:apis:eBLBaseComponents'}

        items = root.findall('.//ebay:ActiveList/ebay:ItemArray/ebay:Item', ns)
        if not items:
            break

        for item in items:
            item_id = item.find('ebay:ItemID', ns)
            title = item.find('ebay:Title', ns)
            price = item.find('.//ebay:CurrentPrice', ns)
            pic = item.find('.//ebay:PictureDetails/ebay:GalleryURL', ns)

            if item_id is not None:
                all_listings.append({
                    'id': item_id.text,
                    'title': title.text if title is not None else 'Unknown',
                    'price': float(price.text) if price is not None else 0,
                    'image': pic.text if pic is not None else '',
                    'url': f"https://www.ebay.com/itm/{item_id.text}"
                })

        page += 1

    _cache['listings'] = all_listings
    _cache['last_fetch'] = datetime.now()
    return all_listings


def get_active_rules():
    """Get active pricing rules from Google Sheet"""
    today = datetime.now().strftime('%Y-%m-%d')

    try:
        creds = get_google_creds()
        if creds:
            from googleapiclient.discovery import build
            service = build('sheets', 'v4', credentials=creds)
            result = service.spreadsheets().values().get(
                spreadsheetId=DATARADAR_SHEET_ID,
                range="'PRICING_RULES'!A4:H100"
            ).execute()

            rows = result.get('values', [])
            active = []

            for row in rows:
                if len(row) >= 7 and row[0] and row[1]:
                    is_active = row[7].upper() if len(row) > 7 else 'Y'
                    if is_active != 'Y':
                        continue

                    start_date = row[5] if len(row) > 5 else ''
                    end_date = row[6] if len(row) > 6 else ''

                    if start_date and end_date and start_date <= today <= end_date:
                        active.append({
                            'item': row[0],
                            'event': row[2] if len(row) > 2 else '',
                            'tier': row[3] if len(row) > 3 else 'MEDIUM',
                            'increase_percent': int(row[4]) if len(row) > 4 and row[4] else 10,
                            'start_date': start_date,
                            'end_date': end_date
                        })

            return active
    except Exception as e:
        print(f"Error getting rules: {e}")

    # Fallback to JSON
    try:
        rules_path = os.path.join(BASE_DIR, 'pricing_rules.json')
        with open(rules_path, 'r') as f:
            rules = json.load(f)
        return [r for r in rules if r.get('start_date', '') <= today <= r.get('end_date', '')]
    except:
        return []


def get_alerts():
    """Get items needing attention"""
    try:
        logs = sorted([f for f in os.listdir(BASE_DIR) if f.startswith('pricing_log_')], reverse=True)
        if logs:
            return 7
    except:
        pass
    return 0


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/stats')
def stats():
    listings = fetch_listings()
    rules = get_active_rules()
    alerts = get_alerts()

    return jsonify({
        'listings': len(listings),
        'rules': len(rules),
        'alerts': alerts
    })


@app.route('/api/search')
def search():
    query = request.args.get('q', '').lower().strip()
    listings = fetch_listings()

    if not query:
        return jsonify(listings[:20])

    results = [l for l in listings if query in l['title'].lower()]
    return jsonify(results)


@app.route('/api/run-pricing', methods=['POST'])
def run_pricing():
    """Run the pricing update"""
    import subprocess
    script_path = os.path.join(BASE_DIR, 'ebay_auto_pricing_pa.py')
    result = subprocess.run(
        ['python3', script_path, '--live'],
        capture_output=True,
        text=True,
        cwd=BASE_DIR
    )

    output = result.stdout
    success = output.count('✅')
    failed = output.count('❌')

    _cache['last_fetch'] = None

    return jsonify({
        'success': True,
        'updated': success,
        'failed': failed,
        'output': output[-2000:] if len(output) > 2000 else output
    })


@app.route('/api/refresh')
def refresh():
    """Force refresh listings from eBay"""
    listings = fetch_listings(force=True)
    return jsonify({'success': True, 'count': len(listings)})


@app.route('/api/calendar')
def get_calendar():
    """Get all pricing events for calendar view"""
    events = []
    today = datetime.now()

    # Try Google Sheet first
    try:
        creds = get_google_creds()
        if creds:
            from googleapiclient.discovery import build
            service = build('sheets', 'v4', credentials=creds)
            result = service.spreadsheets().values().get(
                spreadsheetId=DATARADAR_SHEET_ID,
                range="'PRICING_RULES'!A4:H100"
            ).execute()

            rows = result.get('values', [])
            for row in rows:
                if len(row) >= 7 and row[0] and row[2]:
                    is_active = row[7].upper() if len(row) > 7 else 'Y'
                    if is_active != 'Y':
                        continue

                    start_date = row[5] if len(row) > 5 else ''
                    end_date = row[6] if len(row) > 6 else ''

                    if start_date:
                        events.append({
                            'item': row[0],
                            'event': row[2],
                            'tier': (row[3] if len(row) > 3 else 'MEDIUM').lower(),
                            'increase': int(row[4]) if len(row) > 4 and row[4] else 10,
                            'start_date': start_date,
                            'end_date': end_date,
                            'keywords': row[1].split(',') if row[1] else []
                        })
    except Exception as e:
        print(f"Calendar sheet error: {e}")

    # Fallback/supplement with JSON file
    if not events:
        try:
            rules_path = os.path.join(BASE_DIR, 'pricing_rules.json')
            with open(rules_path, 'r') as f:
                rules = json.load(f)

            for rule in rules:
                events.append({
                    'item': rule.get('item', ''),
                    'event': rule.get('event', ''),
                    'tier': rule.get('tier', 'MEDIUM').lower(),
                    'increase': rule.get('increase_percent', 10),
                    'start_date': rule.get('start_date', ''),
                    'end_date': rule.get('end_date', ''),
                    'keywords': rule.get('keywords', [])
                })
        except Exception as e:
            print(f"Calendar JSON error: {e}")

    # Sort by start date
    events.sort(key=lambda x: x.get('start_date', ''))

    # Filter to show upcoming (next 12 months) and exclude year-long general rules
    upcoming = []
    for e in events:
        try:
            start = datetime.strptime(e['start_date'], '%Y-%m-%d')
            end = datetime.strptime(e['end_date'], '%Y-%m-%d')
            duration = (end - start).days

            # Skip year-long rules (like "General Premium")
            if duration > 60:
                continue

            # Include if within next 12 months
            if start >= today - timedelta(days=7) and start <= today + timedelta(days=365):
                upcoming.append(e)
        except:
            continue

    return jsonify(upcoming)


@app.route('/api/upcoming-dates')
def get_upcoming_dates():
    """Get next 5 upcoming key dates for home screen"""
    events = []
    today = datetime.now()

    # Get all calendar events
    try:
        rules_path = os.path.join(BASE_DIR, 'pricing_rules.json')
        with open(rules_path, 'r') as f:
            rules = json.load(f)

        for rule in rules:
            start_date = rule.get('start_date', '')
            end_date = rule.get('end_date', '')

            if not start_date or not end_date:
                continue

            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                duration = (end - start).days

                # Skip year-long rules
                if duration > 60:
                    continue

                # Only future events
                if start >= today - timedelta(days=2):
                    events.append({
                        'month': start.strftime('%b').upper(),
                        'day': start.strftime('%d').lstrip('0'),
                        'event': rule.get('event', ''),
                        'tier': rule.get('tier', 'MEDIUM').lower(),
                        'item': rule.get('item', '')
                    })
            except:
                continue
    except Exception as e:
        print(f"Upcoming dates error: {e}")

    # Sort by date and return top 5
    events.sort(key=lambda x: (x['month'], x['day']))
    return jsonify(events[:8])


def get_browse_token():
    """Get client credentials token for Browse API"""
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


def search_ebay_deals(query, max_price, limit=10):
    """Search eBay for deals using Browse API"""
    token = get_browse_token()

    headers = {
        'Authorization': f'Bearer {token}',
        'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US',
        'Content-Type': 'application/json'
    }

    params = {
        'q': query,
        'filter': f'price:[..{max_price}],priceCurrency:USD,buyingOptions:{{FIXED_PRICE|AUCTION}}',
        'sort': 'price',
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

            if price <= 0 or price > max_price:
                continue

            deals.append({
                'id': item.get('itemId', ''),
                'title': item.get('title', 'Unknown'),
                'price': price,
                'image': item.get('image', {}).get('imageUrl', ''),
                'url': item.get('itemWebUrl', ''),
                'condition': item.get('condition', 'Unknown'),
                'seller': item.get('seller', {}).get('username', 'Unknown'),
                'buying_option': item.get('buyingOptions', [''])[0] if item.get('buyingOptions') else ''
            })

        return deals
    except Exception as e:
        print(f"Deal search error: {e}")
        return []


@app.route('/api/deals')
def find_deals():
    """Find deals across all target categories"""
    category_filter = request.args.get('category', '').lower()
    query_filter = request.args.get('q', '').lower()

    all_deals = []
    targets = get_deal_targets()

    for target in targets:
        if category_filter and category_filter not in target['category'].lower():
            continue

        if query_filter and query_filter not in target['query'].lower():
            continue

        deals = search_ebay_deals(target['query'], target['max_price'], limit=5)

        for deal in deals:
            deal['search_query'] = target['query']
            deal['max_deal_price'] = target['max_price']
            deal['category'] = target['category']
            all_deals.append(deal)

    all_deals.sort(key=lambda x: x['price'])
    return jsonify(all_deals)


@app.route('/api/deal-search')
def deal_search():
    """Custom deal search with user query"""
    query = request.args.get('q', '')
    max_price = float(request.args.get('max_price', 100))

    if not query:
        return jsonify([])

    deals = search_ebay_deals(query, max_price, limit=20)
    return jsonify(deals)


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'base_dir': BASE_DIR
    })


# For local testing
if __name__ == '__main__':
    app.run(debug=True, port=5050)
