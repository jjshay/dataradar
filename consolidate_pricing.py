#!/usr/bin/env python3
"""
DATARADAR - Consolidate Pricing Data
Merges all scraped eBay pricing data into a master index
"""

import os
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

DOWNLOADS = Path('/Users/johnshay/Downloads')
OUTPUT_DIR = Path('/Users/johnshay/DATARADAR')

def clean_title(title):
    """Clean up eBay title"""
    # Remove "Opens in a new window or tab" suffix
    title = re.sub(r'Opens in a new window or tab$', '', title)
    return title.strip()

def parse_price(price_str):
    """Parse price string to float"""
    if not price_str:
        return 0.0
    # Remove $ and commas
    cleaned = re.sub(r'[$,]', '', str(price_str))
    try:
        return float(cleaned)
    except:
        return 0.0

def categorize_item(title):
    """Categorize item based on title keywords"""
    title_lower = title.lower()

    # KAWS categories
    if 'kaws' in title_lower:
        if '1000%' in title_lower or '1000 %' in title_lower:
            return 'KAWS', 'Bearbrick 1000%'
        if 'bearbrick' in title_lower or 'be@rbrick' in title_lower:
            if '400%' in title_lower:
                return 'KAWS', 'Bearbrick 400%'
            if '100%' in title_lower:
                return 'KAWS', 'Bearbrick 100%'
            return 'KAWS', 'Bearbrick'
        if 'companion' in title_lower:
            return 'KAWS', 'Companion'
        if 'chum' in title_lower:
            return 'KAWS', 'Chum'
        if 'bff' in title_lower:
            return 'KAWS', 'BFF'
        return 'KAWS', 'Other'

    # Bearbrick (non-KAWS)
    if 'bearbrick' in title_lower or 'be@rbrick' in title_lower:
        if '1000%' in title_lower:
            return 'Bearbrick', '1000%'
        if '400%' in title_lower:
            return 'Bearbrick', '400%'
        if '100%' in title_lower:
            return 'Bearbrick', '100%'
        if 'basquiat' in title_lower:
            return 'Bearbrick', 'Basquiat'
        return 'Bearbrick', 'Other'

    # Shepard Fairey / OBEY
    if 'shepard fairey' in title_lower or 'obey giant' in title_lower or 'obey' in title_lower:
        if 'hope' in title_lower:
            return 'Shepard Fairey', 'Hope'
        if 'make art not war' in title_lower:
            return 'Shepard Fairey', 'Make Art Not War'
        if 'peace' in title_lower:
            return 'Shepard Fairey', 'Peace'
        if 'andre' in title_lower:
            return 'Shepard Fairey', 'Andre'
        return 'Shepard Fairey', 'Print'

    # Death NYC
    if 'death nyc' in title_lower:
        return 'Death NYC', 'Print'

    # Banksy
    if 'banksy' in title_lower:
        return 'Banksy', 'Print'

    return 'Other', 'Uncategorized'

def load_csv_files():
    """Load all eBay CSV files from Downloads"""
    all_items = []

    # Find all ebay CSV files
    csv_files = list(DOWNLOADS.glob('ebay_*.csv'))

    for csv_file in csv_files:
        print(f"Loading {csv_file.name}...")
        is_sold = 'sold' in csv_file.name.lower()

        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    title = clean_title(row.get('title', ''))
                    if not title or 'WATCHED ITEM REMINDER' in title:
                        continue

                    price = parse_price(row.get('price_numeric') or row.get('price', '0'))
                    if price <= 0:
                        continue

                    artist, subcategory = categorize_item(title)

                    item = {
                        'title': title,
                        'price': price,
                        'sold_date': row.get('sold_date', ''),
                        'condition': row.get('condition', ''),
                        'url': row.get('item_url', ''),
                        'image': row.get('image_url', ''),
                        'item_id': row.get('item_id', ''),
                        'artist': artist,
                        'subcategory': subcategory,
                        'is_sold': is_sold,
                        'source_file': csv_file.name
                    }
                    all_items.append(item)
        except Exception as e:
            print(f"  Error loading {csv_file.name}: {e}")

    return all_items

def compute_price_stats(items):
    """Compute price statistics by category"""
    stats = defaultdict(lambda: {'prices': [], 'sold_prices': [], 'items': []})

    for item in items:
        key = (item['artist'], item['subcategory'])
        stats[key]['prices'].append(item['price'])
        stats[key]['items'].append(item)
        if item['is_sold']:
            stats[key]['sold_prices'].append(item['price'])

    result = {}
    for (artist, subcategory), data in stats.items():
        prices = sorted(data['prices'])
        sold_prices = sorted(data['sold_prices']) if data['sold_prices'] else prices

        key = f"{artist} - {subcategory}"
        result[key] = {
            'artist': artist,
            'subcategory': subcategory,
            'count': len(prices),
            'sold_count': len(data['sold_prices']),
            'min_price': min(prices),
            'max_price': max(prices),
            'avg_price': sum(prices) / len(prices),
            'median_price': prices[len(prices) // 2],
            'sold_avg': sum(sold_prices) / len(sold_prices) if sold_prices else 0,
            'sold_median': sold_prices[len(sold_prices) // 2] if sold_prices else 0,
            'sample_items': data['items'][:5]  # Keep 5 samples
        }

    return result

def main():
    print("=" * 60)
    print("DATARADAR - Consolidating Pricing Data")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Load all CSV files
    items = load_csv_files()
    print(f"\nTotal items loaded: {len(items)}")

    # Filter for key categories
    kaws_items = [i for i in items if i['artist'] == 'KAWS']
    bearbrick_items = [i for i in items if i['artist'] == 'Bearbrick']
    fairey_items = [i for i in items if i['artist'] == 'Shepard Fairey']
    death_nyc_items = [i for i in items if i['artist'] == 'Death NYC']

    print(f"\nKAWS items: {len(kaws_items)}")
    print(f"Bearbrick items: {len(bearbrick_items)}")
    print(f"Shepard Fairey items: {len(fairey_items)}")
    print(f"Death NYC items: {len(death_nyc_items)}")

    # Compute stats
    stats = compute_price_stats(items)

    # Save master index
    master_index = {
        'generated': datetime.now().isoformat(),
        'total_items': len(items),
        'categories': stats,
        'summary': {
            'KAWS': len(kaws_items),
            'Bearbrick': len(bearbrick_items),
            'Shepard Fairey': len(fairey_items),
            'Death NYC': len(death_nyc_items)
        }
    }

    output_file = OUTPUT_DIR / 'master_pricing_index.json'
    with open(output_file, 'w') as f:
        json.dump(master_index, f, indent=2, default=str)

    print(f"\nMaster index saved: {output_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("PRICE SUMMARY BY CATEGORY")
    print("=" * 60)

    for key, data in sorted(stats.items(), key=lambda x: x[1]['count'], reverse=True)[:20]:
        print(f"\n{key}")
        print(f"  Count: {data['count']} ({data['sold_count']} sold)")
        print(f"  Price Range: ${data['min_price']:.2f} - ${data['max_price']:.2f}")
        print(f"  Average: ${data['avg_price']:.2f} | Median: ${data['median_price']:.2f}")
        if data['sold_avg'] > 0:
            print(f"  Sold Avg: ${data['sold_avg']:.2f} | Sold Median: ${data['sold_median']:.2f}")

    return master_index

if __name__ == "__main__":
    main()
