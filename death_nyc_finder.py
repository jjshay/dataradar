#!/usr/bin/env python3
"""
Death NYC Key Date Finder
Creative date discovery focused on POP CULTURE subjects, characters, and brands
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

# =============================================================================
# CREATIVE LLM PROMPTS FOR POP CULTURE
# =============================================================================

CREATIVE_PROMPT = """You are a POP CULTURE expert helping an eBay seller find the PERFECT dates to list Death NYC street art.

Death NYC creates mashup art combining pop culture icons, luxury brands, and famous artworks. Think creatively about when collectors would be MOST excited to buy.

ARTWORK DETAILS:
- Tags/Subjects: {tags}
- Characters: {characters}
- Franchises: {franchises}
- Themes: {themes}

GET CREATIVE! Find dates related to:
- Character birthdays or creation dates (Mickey Mouse's debut, Snoopy first appeared, etc.)
- Brand anniversaries (Louis Vuitton founded, Supreme first store, etc.)
- Movie/TV premiere dates
- Artist birthdays (Banksy exhibitions, KAWS drops, Warhol's birthday)
- Pop culture events (Met Gala, Art Basel, Comic-Con)
- Viral moments and anniversaries
- Fashion weeks
- Cultural moments that connect to the imagery

Return JSON with the BEST dates to sell this piece:
{{
    "primary_event": {{"name": "event name", "date": "Month Day", "why": "brief reason"}},
    "culture_event": {{"name": "event name", "date": "Month Day", "why": "brief reason"}},
    "brand_event": {{"name": "event name", "date": "Month Day", "why": "brief reason"}},
    "character_event": {{"name": "event name", "date": "Month Day", "why": "brief reason"}},
    "art_world_event": {{"name": "event name", "date": "Month Day", "why": "brief reason"}},
    "bonus_event": {{"name": "event name", "date": "Month Day", "why": "brief reason"}}
}}

Be specific with dates! Think like a collector - when would YOU want to buy this?"""


class ClaudeAPI:
    def __init__(self):
        self.api_key = os.getenv("CLAUDE_API_KEY")
        self.base_url = "https://api.anthropic.com/v1/messages"

    def find_dates(self, tags, characters, franchises, themes):
        if not self.api_key or self.api_key.startswith("your_"):
            return {"error": "Claude API key not configured"}

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        prompt = CREATIVE_PROMPT.format(
            tags=tags, characters=characters,
            franchises=franchises, themes=themes
        )

        try:
            resp = requests.post(self.base_url, headers=headers, json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            }, timeout=45)

            if resp.status_code == 200:
                content = resp.json()["content"][0]["text"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                return {"source": "claude", "data": json.loads(content.strip())}
        except Exception as e:
            return {"error": f"Claude error: {e}"}
        return {"error": "Claude request failed"}


class OpenAIAPI:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1/chat/completions"

    def find_dates(self, tags, characters, franchises, themes):
        if not self.api_key or self.api_key.startswith("your_"):
            return {"error": "OpenAI API key not configured"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        prompt = CREATIVE_PROMPT.format(
            tags=tags, characters=characters,
            franchises=franchises, themes=themes
        )

        try:
            resp = requests.post(self.base_url, headers=headers, json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024
            }, timeout=45)

            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                return {"source": "openai", "data": json.loads(content.strip())}
        except Exception as e:
            return {"error": f"OpenAI error: {e}"}
        return {"error": "OpenAI request failed"}


class GrokAPI:
    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY")
        self.base_url = "https://api.x.ai/v1/chat/completions"

    def find_dates(self, tags, characters, franchises, themes):
        if not self.api_key or self.api_key.startswith("your_"):
            return {"error": "Grok API key not configured"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        prompt = CREATIVE_PROMPT.format(
            tags=tags, characters=characters,
            franchises=franchises, themes=themes
        )

        try:
            resp = requests.post(self.base_url, headers=headers, json={
                "model": "grok-3",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024
            }, timeout=45)

            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                return {"source": "grok", "data": json.loads(content.strip())}
        except Exception as e:
            return {"error": f"Grok error: {e}"}
        return {"error": "Grok request failed"}


class DeathNYCOrchestrator:
    """Coordinates LLMs to find creative pop culture dates"""

    def __init__(self):
        self.claude = ClaudeAPI()
        self.openai = OpenAIAPI()
        self.grok = GrokAPI()

    def find_dates_for_artwork(self, title, tags, characters, franchises, themes):
        """Query all LLMs in parallel for creative date suggestions"""

        print(f"\n🎨 Processing: {title[:60]}...")
        print(f"   Tags: {tags[:80]}...")

        results = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.claude.find_dates, tags, characters, franchises, themes): "claude",
                executor.submit(self.openai.find_dates, tags, characters, franchises, themes): "openai",
                executor.submit(self.grok.find_dates, tags, characters, franchises, themes): "grok",
            }

            for future in as_completed(futures):
                llm_name = futures[future]
                try:
                    result = future.result()
                    results[llm_name] = result
                    if "error" not in result:
                        print(f"   ✅ {llm_name}: found dates")
                    else:
                        print(f"   ❌ {llm_name}: {result.get('error', 'failed')[:50]}")
                except Exception as e:
                    results[llm_name] = {"error": str(e)}
                    print(f"   ❌ {llm_name}: {e}")

        return self.combine_results(results, title)

    def combine_results(self, results, title):
        """Combine and prioritize results from multiple LLMs"""
        combined = {
            "artwork": title,
            "primary_event": None,
            "culture_event": None,
            "brand_event": None,
            "character_event": None,
            "art_world_event": None,
            "bonus_event": None,
            "sources": []
        }

        event_types = ["primary_event", "culture_event", "brand_event",
                       "character_event", "art_world_event", "bonus_event"]

        for llm_name, result in results.items():
            if "error" not in result and "data" in result:
                data = result["data"]
                combined["sources"].append(llm_name)

                for event_type in event_types:
                    if combined[event_type] is None and event_type in data and data[event_type]:
                        event = data[event_type]
                        if isinstance(event, dict) and "name" in event:
                            date_str = event.get("date", "")
                            name = event.get("name", "")
                            why = event.get("why", "")
                            combined[event_type] = f"{name} / {date_str}"

        return combined


def process_death_nyc(excel_path: str, output_path: str = None):
    """Process Death NYC inventory and find creative key dates"""

    print("=" * 60)
    print("🎭 DEATH NYC KEY DATE FINDER - POP CULTURE EDITION")
    print("=" * 60)

    df = pd.read_excel(excel_path, sheet_name="Products")

    # Filter Death NYC items
    death_nyc = df[df['ARTIST'].str.contains('death|nyc', case=False, na=False) |
                   df['Title'].str.contains('death nyc', case=False, na=False)].copy()

    print(f"\n📦 Found {len(death_nyc)} Death NYC items")

    orchestrator = DeathNYCOrchestrator()

    # Add new columns for events
    event_cols = ["PRIMARY_EVENT", "CULTURE_EVENT", "BRAND_EVENT",
                  "CHARACTER_EVENT", "ART_WORLD_EVENT", "BONUS_EVENT"]
    for col in event_cols:
        death_nyc[col] = None

    for idx, row in death_nyc.iterrows():
        title = str(row.get("Title", ""))
        tags = str(row.get("Tags", ""))
        characters = str(row.get("C: Character", ""))
        franchises = str(row.get("C: Franchise", ""))
        themes = str(row.get("C: Theme", ""))

        if not title or pd.isna(title):
            continue

        result = orchestrator.find_dates_for_artwork(
            title, tags, characters, franchises, themes
        )

        # Update dataframe
        if result.get("primary_event"):
            death_nyc.at[idx, "PRIMARY_EVENT"] = result["primary_event"]
        if result.get("culture_event"):
            death_nyc.at[idx, "CULTURE_EVENT"] = result["culture_event"]
        if result.get("brand_event"):
            death_nyc.at[idx, "BRAND_EVENT"] = result["brand_event"]
        if result.get("character_event"):
            death_nyc.at[idx, "CHARACTER_EVENT"] = result["character_event"]
        if result.get("art_world_event"):
            death_nyc.at[idx, "ART_WORLD_EVENT"] = result["art_world_event"]
        if result.get("bonus_event"):
            death_nyc.at[idx, "BONUS_EVENT"] = result["bonus_event"]

    # Save results
    if output_path is None:
        output_path = "/Users/johnshay/DateDriven/DEATH_NYC_with_dates.xlsx"

    death_nyc.to_excel(output_path, index=False)
    print(f"\n✅ Saved results to: {output_path}")

    return death_nyc


if __name__ == "__main__":
    import sys
    excel_path = sys.argv[1] if len(sys.argv) > 1 else "/Applications/3DSELLERS.xlsx"
    process_death_nyc(excel_path)
