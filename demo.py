#!/usr/bin/env python3
"""
DateDriven Demo Script
Demonstrates the multi-LLM key date discovery system
"""

import os
import sys

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from key_date_finder import KeyDateOrchestrator

def demo():
    """Run a demo on sample artworks"""

    print("=" * 60)
    print("🎯 DateDriven Demo - Multi-LLM Key Date Discovery")
    print("=" * 60)
    print()
    print("This demo queries 4 LLMs (Claude, GPT-4, Gemini, Grok)")
    print("to find optimal selling dates for art collectibles.")
    print()

    # Sample artworks to demo
    sample_artworks = [
        "Shepard Fairey Muhammad Ali 2006 Obey Giant Signed Print",
        "Shepard Fairey John Lennon Peace 2010 Obey Giant Signed Print",
        "Andy Warhol Campbell's Soup Cans 1962 Print",
    ]

    orchestrator = KeyDateOrchestrator()

    for artwork in sample_artworks:
        print("-" * 60)
        result = orchestrator.find_dates_for_artwork(artwork)

        print(f"\n📊 Results for: {artwork[:50]}...")
        print()

        if result.get("national_event"):
            print(f"   🏛️  National Event: {result['national_event']}")
        if result.get("key_event_1"):
            print(f"   📅 Key Event 1: {result['key_event_1']}")
        if result.get("key_event_2"):
            print(f"   📅 Key Event 2: {result['key_event_2']}")
        if result.get("key_event_3"):
            print(f"   📅 Key Event 3: {result['key_event_3']}")

        print(f"\n   Sources: {', '.join(result.get('sources', []))}")
        print()

    print("=" * 60)
    print("✅ Demo complete!")
    print()
    print("To process your own inventory:")
    print("  python run.py")
    print()
    print("Or use the Python API:")
    print("  from key_date_finder import process_inventory")
    print("  process_inventory('your_inventory.xlsx')")
    print("=" * 60)


if __name__ == "__main__":
    demo()
