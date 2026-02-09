#!/usr/bin/env python3
"""
DATARADAR - Deal Finder App
Find underpriced items on eBay to buy and resell
"""

from flask import Flask, render_template, jsonify, request
import os
import json
import base64
import requests
import pickle
from datetime import datetime
from googleapiclient.discovery import build

app = Flask(__name__, template_folder='templates')
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

# Google Sheet config
DATARADAR_SHEET_ID = '11a-_IWhljPJHeKV8vdke-JiLmm_KCq-bedSceKB0kZI'

# Cache
_cache = {'deal_targets': [], 'targets_fetch': None}


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
# Min price helps filter out fakes (too cheap = suspicious)
DEAL_TARGETS_FALLBACK = [
    # Mr. Brainwash - legit prints usually $150+
    {'query': 'Mr Brainwash signed print', 'min_price': 100, 'max_price': 500, 'category': 'Mr. Brainwash'},
    {'query': 'Mr Brainwash Life is Beautiful', 'min_price': 100, 'max_price': 600, 'category': 'Mr. Brainwash'},
    {'query': 'MBW signed print', 'min_price': 75, 'max_price': 400, 'category': 'Mr. Brainwash'},
    {'query': 'Brainwash Banksy Thrower', 'min_price': 100, 'max_price': 500, 'category': 'Mr. Brainwash'},

    # Shepard Fairey - legit prints usually $100+
    {'query': 'Shepard Fairey signed print', 'min_price': 75, 'max_price': 400, 'category': 'Shepard Fairey'},
    {'query': 'Obey Giant signed', 'min_price': 50, 'max_price': 300, 'category': 'Shepard Fairey'},
    {'query': 'Shepard Fairey Obama Hope', 'min_price': 150, 'max_price': 800, 'category': 'Shepard Fairey'},
    {'query': 'Shepard Fairey Peace Guard', 'min_price': 75, 'max_price': 350, 'category': 'Shepard Fairey'},
    {'query': 'Shepard Fairey Lotus', 'min_price': 75, 'max_price': 400, 'category': 'Shepard Fairey'},

    # Space memorabilia - signed with COA
    {'query': 'Neil Armstrong signed photo COA', 'min_price': 500, 'max_price': 5000, 'category': 'Space'},
    {'query': 'Buzz Aldrin signed photo COA', 'min_price': 100, 'max_price': 800, 'category': 'Space'},
    {'query': 'Michael Collins signed photo COA', 'min_price': 100, 'max_price': 600, 'category': 'Space'},
    {'query': 'astronaut signed COA authenticated', 'min_price': 100, 'max_price': 1000, 'category': 'Space'},

    # Signed Pickguards with COA
    {'query': 'signed pickguard COA', 'min_price': 75, 'max_price': 500, 'category': 'Pickguard'},
    {'query': 'autographed pickguard COA', 'min_price': 75, 'max_price': 500, 'category': 'Pickguard'},
    {'query': 'guitar pickguard signed authenticated', 'min_price': 100, 'max_price': 600, 'category': 'Pickguard'},

    # Vinyl Records - signed with COA
    {'query': 'Fred Again signed vinyl COA', 'min_price': 75, 'max_price': 500, 'category': 'Vinyl'},
    {'query': 'Taylor Swift signed vinyl COA', 'min_price': 100, 'max_price': 600, 'category': 'Vinyl'},
    {'query': 'signed vinyl COA authenticated', 'min_price': 75, 'max_price': 500, 'category': 'Vinyl'},
    {'query': 'autographed vinyl record COA', 'min_price': 75, 'max_price': 500, 'category': 'Vinyl'},
]


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


def search_ebay_deals(query, max_price, min_price=0, limit=10):
    """Search eBay for deals using Browse API"""
    token = get_browse_token()

    headers = {
        'Authorization': f'Bearer {token}',
        'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US',
        'Content-Type': 'application/json'
    }

    # Build price filter with min and max
    if min_price > 0:
        price_filter = f'price:[{min_price}..{max_price}]'
    else:
        price_filter = f'price:[..{max_price}]'

    params = {
        'q': query,
        'filter': f'{price_filter},priceCurrency:USD,buyingOptions:{{FIXED_PRICE|AUCTION}}',
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
                'buying_option': item.get('buyingOptions', [''])[0] if item.get('buyingOptions') else '',
                'location': item.get('itemLocation', {}).get('country', '')
            })

        return deals
    except Exception as e:
        print(f"Deal search error: {e}")
        return []


@app.route('/')
def index():
    return render_template('deals.html')


@app.route('/api/stats')
def stats():
    targets = get_deal_targets()
    return jsonify({
        'targets': len(targets),
        'categories': len(set(t['category'] for t in targets))
    })


@app.route('/api/targets')
def get_targets():
    """Get all deal targets"""
    targets = get_deal_targets()
    return jsonify(targets)


@app.route('/api/scan')
def scan_deals():
    """Scan all targets for deals"""
    category_filter = request.args.get('category', '').lower()
    targets = get_deal_targets()

    all_deals = []

    for target in targets:
        if category_filter and category_filter not in target['category'].lower():
            continue

        deals = search_ebay_deals(target['query'], target['max_price'], limit=5)

        for deal in deals:
            deal['search_query'] = target['query']
            deal['max_deal_price'] = target['max_price']
            deal['category'] = target['category']
            all_deals.append(deal)

    # Sort by price
    all_deals.sort(key=lambda x: x['price'])

    return jsonify(all_deals)


@app.route('/api/search')
def search():
    """Custom search with user query"""
    query = request.args.get('q', '')
    min_price = float(request.args.get('min_price', 0))
    max_price = float(request.args.get('max_price', 500))

    if not query:
        return jsonify([])

    deals = search_ebay_deals(query, max_price, min_price, limit=20)
    return jsonify(deals)


@app.route('/api/comps')
def get_comps():
    """Get deals organized by artist/category"""
    targets = get_deal_targets()

    # Group targets by category
    by_category = {}
    for t in targets:
        cat = t['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(t)

    # Scan each category
    results = {}
    for cat, cat_targets in by_category.items():
        results[cat] = []
        for target in cat_targets[:3]:  # Limit to 3 per category for speed
            min_price = target.get('min_price', 0)
            max_price = target.get('max_price', 500)
            deals = search_ebay_deals(target['query'], max_price, min_price, limit=3)
            for deal in deals:
                deal['search_query'] = target['query']
                deal['min_deal_price'] = min_price
                deal['max_deal_price'] = max_price
                results[cat].append(deal)

    return jsonify(results)


# Watchlist storage (in-memory for now, could be Google Sheet)
WATCHLIST_FILE = 'watchlist.json'

def load_watchlist():
    """Load watchlist from file"""
    try:
        if os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_watchlist(items):
    """Save watchlist to file"""
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(items, f, indent=2)


@app.route('/api/watchlist')
def get_watchlist():
    """Get all watchlist items"""
    items = load_watchlist()
    return jsonify(items)


@app.route('/api/watchlist/add', methods=['POST'])
def add_to_watchlist():
    """Add item to watchlist"""
    data = request.get_json()

    item = {
        'id': data.get('id', ''),
        'title': data.get('title', ''),
        'price': data.get('price', 0),
        'url': data.get('url', ''),
        'image': data.get('image', ''),
        'notes': data.get('notes', ''),
        'added': datetime.now().isoformat(),
        'status': 'watching'  # watching, ended, purchased
    }

    items = load_watchlist()

    # Check if already exists
    if not any(i['id'] == item['id'] for i in items):
        items.append(item)
        save_watchlist(items)

    return jsonify({'success': True, 'count': len(items)})


@app.route('/api/watchlist/remove', methods=['POST'])
def remove_from_watchlist():
    """Remove item from watchlist"""
    data = request.get_json()
    item_id = data.get('id', '')

    items = load_watchlist()
    items = [i for i in items if i['id'] != item_id]
    save_watchlist(items)

    return jsonify({'success': True, 'count': len(items)})


@app.route('/api/watchlist/update', methods=['POST'])
def update_watchlist_item():
    """Update watchlist item status/notes"""
    data = request.get_json()
    item_id = data.get('id', '')

    items = load_watchlist()
    for item in items:
        if item['id'] == item_id:
            if 'status' in data:
                item['status'] = data['status']
            if 'notes' in data:
                item['notes'] = data['notes']
            if 'price' in data:
                item['price'] = data['price']
            break

    save_watchlist(items)
    return jsonify({'success': True})


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'app': 'deals'})


if __name__ == '__main__':
    app.run(debug=True, port=5051)
