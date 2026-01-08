#!/usr/bin/env python3
"""
Main runner script for eBay Key Date Finder
"""

import sys
from key_date_finder import process_inventory
from calendar_sync import sync_to_calendar


def main():
    excel_path = "/Applications/SHEPARD FAIREY.xlsx"

    print("\n" + "=" * 60)
    print("🎨 SHEPARD FAIREY EBAY KEY DATE FINDER")
    print("=" * 60)
    print("\nThis tool will:")
    print("1. Read your inventory from Excel")
    print("2. Query 4 LLMs (Claude, GPT, Gemini, Grok) for key dates")
    print("3. Use Wikipedia for additional context")
    print("4. Fill in the EVENT columns in your spreadsheet")
    print("5. Sync dates to Google Calendar")

    print("\n" + "-" * 60)
    print("STEP 1: Finding key dates with 4 LLMs...")
    print("-" * 60)

    output_path = excel_path.replace(".xlsx", "_with_dates.xlsx")
    df = process_inventory(excel_path, output_path)

    print("\n" + "-" * 60)
    print("STEP 2: Syncing to Google Calendar...")
    print("-" * 60)

    sync_to_calendar(output_path)

    print("\n" + "=" * 60)
    print("✅ COMPLETE!")
    print("=" * 60)
    print(f"\nUpdated spreadsheet: {output_path}")
    print("Calendar events created for upcoming key dates")


if __name__ == "__main__":
    main()
