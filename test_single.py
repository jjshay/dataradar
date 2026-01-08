#!/usr/bin/env python3
"""Quick test on a single artwork"""

import os
os.chdir('/Users/johnshay/ebay-key-dates')

from key_date_finder import KeyDateOrchestrator

orchestrator = KeyDateOrchestrator()

# Test with Muhammad Ali print
result = orchestrator.find_dates_for_artwork("Shepard Fairey Muhammad Ali 2006 Obey Giant Signed Print")

print("\n" + "=" * 60)
print("RESULTS:")
print("=" * 60)
for key, value in result.items():
    if value:
        print(f"{key}: {value}")
