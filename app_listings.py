#!/usr/bin/env python3
"""
DATARADAR - Simple Web Interface
"""

from flask import Flask, render_template, jsonify, request
import os
import json
import base64
import requests
import pickle
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from googleapiclient.discovery import build

app = Flask(__name__)
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
EBAY_REFRESH_TOKEN = env_vars.get('EBAY_REFRESH_TOKEN')

# Google Sheet config
DATARADAR_SHEET_ID = '11a-_IWhljPJHeKV8vdke-JiLmm_KCq-bedSceKB0kZI'

# Cache for listings and sheet data
_cache = {'listings': [], 'last_fetch': None, 'deal_targets': [], 'targets_fetch': None}


def get_google_creds():
    """Load Google credentials with auto-refresh"""
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        if creds and creds.expired and creds.refresh_token:
            try:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
            except:
                pass
        return creds
    return None


def get_deal_targets():
    """Read deal targets from Google Sheet - cached for 5 minutes"""
    # Use cache if fresh
    if _cache['targets_fetch']:
        age = (datetime.now() - _cache['targets_fetch']).seconds
        if age < 300 and _cache['deal_targets']:
            return _cache['deal_targets']

    try:
        creds = get_google_creds()
        if not creds:
            return DEAL_TARGETS_FALLBACK

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
    {'query': 'Blink 182 signed', 'max_price': 250, 'category': 'Music'},
    {'query': 'Apollo 11 signed photo', 'max_price': 500, 'category': 'Space'},
]

# Deal finder targets - what to hunt for and max price to consider a deal
DEAL_TARGETS = [
    # Art
    {'query': 'Death NYC signed', 'max_price': 50, 'category': 'Art'},
    {'query': 'Death NYC framed', 'max_price': 60, 'category': 'Art'},
    {'query': 'Shepard Fairey signed print', 'max_price': 150, 'category': 'Art'},
    {'query': 'Obey Giant signed', 'max_price': 100, 'category': 'Art'},

    # Music - Rock Legends (authenticated)
    {'query': 'Red Hot Chili Peppers signed', 'max_price': 150, 'category': 'Music'},
    {'query': 'Chad Smith signed', 'max_price': 100, 'category': 'Music'},
    {'query': 'Guns N Roses signed', 'max_price': 200, 'category': 'Music'},
    {'query': 'Duff McKagan signed', 'max_price': 100, 'category': 'Music'},
    {'query': 'Motley Crue signed', 'max_price': 175, 'category': 'Music'},
    {'query': 'Tommy Lee signed', 'max_price': 150, 'category': 'Music'},
    {'query': 'Foo Fighters signed', 'max_price': 200, 'category': 'Music'},
    {'query': 'Dave Grohl signed', 'max_price': 175, 'category': 'Music'},

    # Pop Punk - Core bands
    {'query': 'Blink 182 signed', 'max_price': 250, 'category': 'Music'},
    {'query': 'Green Day signed', 'max_price': 250, 'category': 'Music'},
    {'query': 'Sum 41 signed', 'max_price': 150, 'category': 'Music'},
    {'query': 'Good Charlotte signed', 'max_price': 125, 'category': 'Music'},
    {'query': 'Simple Plan signed', 'max_price': 100, 'category': 'Music'},
    {'query': 'New Found Glory signed', 'max_price': 125, 'category': 'Music'},
    {'query': 'Fall Out Boy signed', 'max_price': 175, 'category': 'Music'},
    {'query': 'My Chemical Romance signed', 'max_price': 200, 'category': 'Music'},
    {'query': 'Paramore signed', 'max_price': 175, 'category': 'Music'},
    {'query': 'All Time Low signed', 'max_price': 125, 'category': 'Music'},
    {'query': 'Offspring signed', 'max_price': 150, 'category': 'Music'},
    {'query': 'Yellowcard signed', 'max_price': 125, 'category': 'Music'},
    {'query': 'Taking Back Sunday signed', 'max_price': 125, 'category': 'Music'},
    {'query': 'The Used signed', 'max_price': 100, 'category': 'Music'},
    {'query': 'A Day To Remember signed', 'max_price': 125, 'category': 'Music'},
    {'query': 'Brand New band signed', 'max_price': 150, 'category': 'Music'},
    {'query': 'NOFX signed', 'max_price': 125, 'category': 'Music'},
    {'query': 'Bad Religion signed', 'max_price': 125, 'category': 'Music'},
    {'query': 'Rise Against signed', 'max_price': 125, 'category': 'Music'},
    {'query': 'Jimmy Eat World signed', 'max_price': 125, 'category': 'Music'},
    {'query': 'Dashboard Confessional signed', 'max_price': 100, 'category': 'Music'},
    {'query': 'Panic At The Disco signed', 'max_price': 150, 'category': 'Music'},
    {'query': 'Pierce The Veil signed', 'max_price': 125, 'category': 'Music'},
    {'query': 'Sleeping With Sirens signed', 'max_price': 100, 'category': 'Music'},
    {'query': 'Mayday Parade signed', 'max_price': 100, 'category': 'Music'},

    # Other artists
    {'query': 'Taylor Swift signed', 'max_price': 200, 'category': 'Music'},
    {'query': 'Coldplay signed', 'max_price': 200, 'category': 'Music'},
    {'query': 'Ed Sheeran signed', 'max_price': 150, 'category': 'Music'},
    {'query': 'Beatles autograph signed', 'max_price': 500, 'category': 'Music'},

    # Authenticated items (JSA/BAS/PSA)
    {'query': 'signed vinyl JSA COA', 'max_price': 150, 'category': 'Music'},
    {'query': 'signed vinyl BAS COA', 'max_price': 150, 'category': 'Music'},
    {'query': 'signed album PSA', 'max_price': 150, 'category': 'Music'},
    {'query': 'signed guitar autographed COA', 'max_price': 300, 'category': 'Music'},
    {'query': 'signed concert poster', 'max_price': 75, 'category': 'Music'},

    # Space Memorabilia
    {'query': 'Apollo 11 signed photo', 'max_price': 500, 'category': 'Space'},
    {'query': 'Neil Armstrong signed', 'max_price': 750, 'category': 'Space'},
    {'query': 'Buzz Aldrin signed photo', 'max_price': 300, 'category': 'Space'},
    {'query': 'Michael Collins signed', 'max_price': 250, 'category': 'Space'},
    {'query': 'Apollo astronaut signed', 'max_price': 400, 'category': 'Space'},
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
    # Use cache if fresh (5 min)
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
    except:
        pass

    # Fallback to JSON
    try:
        with open('pricing_rules.json', 'r') as f:
            rules = json.load(f)
        return [r for r in rules if r.get('start_date', '') <= today <= r.get('end_date', '')]
    except:
        return []


def get_alerts():
    """Get count of items needing attention"""
    alerts = get_alert_details()
    return len(alerts)


def get_alert_details():
    """Get detailed list of items needing attention"""
    alerts = []
    listings = fetch_listings()

    # 1. Very low priced items (under $10) - might be mispriced
    for listing in listings:
        if listing['price'] < 10:
            alerts.append({
                'type': 'low_price',
                'title': listing['title'],
                'message': f"Very low price: ${listing['price']:.2f}",
                'item_id': listing['id'],
                'price': listing['price'],
                'url': listing['url']
            })

    # 2. Very high priced items (over $1000) - verify correct
    for listing in listings:
        if listing['price'] > 1000:
            alerts.append({
                'type': 'high_price',
                'title': listing['title'],
                'message': f"High value item: ${listing['price']:.2f}",
                'item_id': listing['id'],
                'price': listing['price'],
                'url': listing['url']
            })

    # 3. Check for failed updates from last pricing log
    try:
        logs = sorted([f for f in os.listdir('.') if f.startswith('pricing_log_')], reverse=True)
        if logs:
            with open(logs[0], 'r') as f:
                log = json.load(f)
            # Add failed items from log
            for item in log.get('failed', []):
                alerts.append({
                    'type': 'update_failed',
                    'title': item.get('title', 'Unknown'),
                    'message': item.get('error', 'Update failed'),
                    'item_id': item.get('id', ''),
                    'price': item.get('price', 0),
                    'url': f"https://www.ebay.com/itm/{item.get('id', '')}"
                })
    except:
        pass

    return alerts


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
    result = subprocess.run(
        ['python3', 'ebay_auto_pricing.py', '--live'],
        capture_output=True,
        text=True,
        cwd='/Users/johnshay/DATARADAR'
    )

    # Parse results
    output = result.stdout
    success = output.count('✅')
    failed = output.count('❌')

    # Clear cache to refresh listings
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


@app.route('/api/update-category-pricing', methods=['POST'])
def update_category_pricing():
    """Update prices for multiple items by category"""
    data = request.get_json()
    item_ids = data.get('item_ids', [])
    adjustment_type = data.get('adjustment_type', 'percent_increase')
    adjustment_value = float(data.get('adjustment_value', 0))

    if not item_ids:
        return jsonify({'success': False, 'error': 'No items provided'})

    if adjustment_value == 0:
        return jsonify({'success': False, 'error': 'No adjustment value'})

    # Get current listings to find prices
    listings = fetch_listings()
    listings_by_id = {l['id']: l for l in listings}

    token = get_access_token()
    updated = 0
    failed = 0

    for item_id in item_ids:
        listing = listings_by_id.get(item_id)
        if not listing:
            failed += 1
            continue

        old_price = listing['price']
        new_price = old_price

        # Calculate new price based on adjustment type
        if adjustment_type == 'percent_increase':
            new_price = old_price * (1 + adjustment_value / 100)
        elif adjustment_type == 'percent_decrease':
            new_price = old_price * (1 - adjustment_value / 100)
        elif adjustment_type == 'fixed_increase':
            new_price = old_price + adjustment_value
        elif adjustment_type == 'fixed_decrease':
            new_price = old_price - adjustment_value
        elif adjustment_type == 'set_price':
            new_price = adjustment_value

        # Ensure minimum price
        new_price = max(0.99, round(new_price, 2))

        # Skip if no change
        if abs(new_price - old_price) < 0.01:
            continue

        # Update on eBay
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

        try:
            resp = requests.post("https://api.ebay.com/ws/api.dll", headers=headers, data=xml_request, timeout=10)
            if '<Ack>Success</Ack>' in resp.text or '<Ack>Warning</Ack>' in resp.text:
                updated += 1
            else:
                failed += 1
        except Exception as e:
            print(f"Error updating {item_id}: {e}")
            failed += 1

    # Clear cache
    _cache['last_fetch'] = None

    return jsonify({
        'success': True,
        'updated': updated,
        'failed': failed,
        'total': len(item_ids)
    })


@app.route('/api/calendar')
def get_calendar():
    """Get all pricing events for calendar view"""
    events = []
    today = datetime.now()
    return_all = request.args.get('all', '').lower() == 'true'

    # Read from JSON file (primary source for key dates)
    try:
        with open('pricing_rules.json', 'r') as f:
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

    # If all=true, return all events (for month view calendar)
    if return_all:
        # Still filter out year-long rules for cleaner display
        filtered = []
        for e in events:
            try:
                start = datetime.strptime(e['start_date'], '%Y-%m-%d')
                end = datetime.strptime(e['end_date'], '%Y-%m-%d')
                duration = (end - start).days
                if duration <= 60:
                    filtered.append(e)
            except:
                filtered.append(e)
        return jsonify(filtered)

    # Filter to upcoming/active and exclude year-long rules
    upcoming = []
    for e in events:
        try:
            start = datetime.strptime(e['start_date'], '%Y-%m-%d')
            end = datetime.strptime(e['end_date'], '%Y-%m-%d')
            duration = (end - start).days

            # Skip year-long rules
            if duration > 60:
                continue

            # Include if: currently active OR starting within next 45 days
            is_active = start <= today <= end
            is_upcoming = start >= today and start <= today + timedelta(days=45)

            if is_active or is_upcoming:
                upcoming.append(e)
        except:
            continue

    return jsonify(upcoming)


@app.route('/api/upcoming-dates')
def get_upcoming_dates():
    """Get next 5 upcoming key dates for home screen"""
    events = []
    today = datetime.now()

    try:
        with open('pricing_rules.json', 'r') as f:
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

                if duration > 60:
                    continue

                # Include active or upcoming within 45 days
                is_active = start <= today <= end
                is_upcoming = start >= today and start <= today + timedelta(days=45)

                if is_active or is_upcoming:
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

    events.sort(key=lambda x: (x['month'], x['day']))
    return jsonify(events[:8])


def get_browse_token():
    """Get client credentials token for Browse API (searching eBay)"""
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

    # Search with price filter
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

            # Skip if price is 0 or too high
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
    """Find deals across all target categories - reads from Google Sheet"""
    category_filter = request.args.get('category', '').lower()
    query_filter = request.args.get('q', '').lower()

    all_deals = []
    targets = get_deal_targets()  # Read from Google Sheet

    for target in targets:
        # Filter by category if specified
        if category_filter and category_filter not in target['category'].lower():
            continue

        # Filter by query if specified
        if query_filter and query_filter not in target['query'].lower():
            continue

        deals = search_ebay_deals(target['query'], target['max_price'], limit=5)

        for deal in deals:
            deal['search_query'] = target['query']
            deal['max_deal_price'] = target['max_price']
            deal['category'] = target['category']
            all_deals.append(deal)

    # Sort by price (lowest first)
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


@app.route('/api/alerts')
def get_alerts_api():
    """Get detailed alerts for items needing attention"""
    alerts = get_alert_details()
    return jsonify(alerts)


@app.route('/api/underpriced')
def get_underpriced():
    """Find inventory items that should be boosted based on active pricing rules"""
    listings = fetch_listings()
    today = datetime.now()

    # Get active pricing rules from JSON
    active_rules = []
    try:
        with open('pricing_rules.json', 'r') as f:
            rules = json.load(f)

        for rule in rules:
            start_date = rule.get('start_date', '')
            end_date = rule.get('end_date', '')

            if start_date and end_date:
                try:
                    start = datetime.strptime(start_date, '%Y-%m-%d')
                    end = datetime.strptime(end_date, '%Y-%m-%d')

                    # Include if currently active
                    if start <= today <= end:
                        active_rules.append(rule)
                except:
                    continue
    except Exception as e:
        print(f"Error loading rules: {e}")
        return jsonify([])

    if not active_rules:
        return jsonify([])

    # Find listings that match active rules
    underpriced = []

    for listing in listings:
        title_lower = listing['title'].lower()

        for rule in active_rules:
            keywords = rule.get('keywords', [])
            matched = False

            for keyword in keywords:
                if keyword.lower() in title_lower:
                    matched = True
                    break

            if matched:
                # Calculate suggested price
                current_price = listing['price']
                boost_percent = rule.get('increase_percent', 10)
                suggested_price = round(current_price * (1 + boost_percent / 100), 2)

                underpriced.append({
                    'id': listing['id'],
                    'title': listing['title'],
                    'current_price': current_price,
                    'suggested_price': suggested_price,
                    'boost_percent': boost_percent,
                    'event': rule.get('event', ''),
                    'tier': rule.get('tier', 'MEDIUM'),
                    'url': listing['url'],
                    'image': listing.get('image', '')
                })
                break  # Don't double-count same listing

    # Sort by boost percent descending (highest opportunity first)
    underpriced.sort(key=lambda x: x['boost_percent'], reverse=True)

    return jsonify(underpriced)


if __name__ == '__main__':
    app.run(debug=True, port=5050)
