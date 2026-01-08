"""
Key Date Finder for eBay Art Inventory
Uses 4 LLMs + Wikipedia to find relevant dates for Shepard Fairey prints
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
# API CLIENTS
# =============================================================================

class WikipediaAPI:
    """Fetch relevant dates from Wikipedia"""

    BASE_URL = "https://en.wikipedia.org/api/rest_v1"

    def search(self, query: str) -> dict:
        """Search Wikipedia for a topic"""
        url = f"{self.BASE_URL}/page/summary/{query.replace(' ', '_')}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"Wikipedia error: {e}")
        return {}

    def get_on_this_day(self, month: int, day: int) -> list:
        """Get events that happened on a specific date"""
        url = f"{self.BASE_URL}/feed/onthisday/events/{month}/{day}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("events", [])[:10]
        except Exception as e:
            print(f"Wikipedia on-this-day error: {e}")
        return []


class ClaudeAPI:
    """Anthropic Claude API client"""

    def __init__(self):
        self.api_key = os.getenv("CLAUDE_API_KEY")
        self.base_url = "https://api.anthropic.com/v1/messages"

    def find_dates(self, artwork_name: str, subject: str, context: str) -> dict:
        if not self.api_key or self.api_key.startswith("your_"):
            return {"error": "Claude API key not configured"}

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        prompt = f"""Find key dates relevant to selling this Shepard Fairey artwork on eBay.

Artwork: {artwork_name}
Subject/Theme: {subject}
Context: {context}

Return JSON with dates that would be good for listing/promoting this art:
{{
    "national_event": {{"name": "event name", "date": "Month Day"}},
    "key_event_1": {{"name": "event name", "date": "Month Day"}},
    "key_event_2": {{"name": "event name", "date": "Month Day"}},
    "key_event_3": {{"name": "event name", "date": "Month Day"}},
    "reasoning": "why these dates matter for selling this piece"
}}

Focus on: anniversaries, birthdays, cultural events, political events, art world dates."""

        try:
            resp = requests.post(self.base_url, headers=headers, json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            }, timeout=30)

            if resp.status_code == 200:
                content = resp.json()["content"][0]["text"]
                # Extract JSON from response
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                return {"source": "claude", "data": json.loads(content.strip())}
        except Exception as e:
            return {"error": f"Claude error: {e}"}
        return {"error": "Claude request failed"}


class OpenAIAPI:
    """OpenAI GPT API client"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1/chat/completions"

    def find_dates(self, artwork_name: str, subject: str, context: str) -> dict:
        if not self.api_key or self.api_key.startswith("your_"):
            return {"error": "OpenAI API key not configured"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        prompt = f"""Find key dates relevant to selling this Shepard Fairey artwork on eBay.

Artwork: {artwork_name}
Subject/Theme: {subject}
Context: {context}

Return JSON with dates that would be good for listing/promoting this art:
{{
    "national_event": {{"name": "event name", "date": "Month Day"}},
    "key_event_1": {{"name": "event name", "date": "Month Day"}},
    "key_event_2": {{"name": "event name", "date": "Month Day"}},
    "key_event_3": {{"name": "event name", "date": "Month Day"}},
    "reasoning": "why these dates matter for selling this piece"
}}

Focus on: anniversaries, birthdays, cultural events, political events, art world dates."""

        try:
            resp = requests.post(self.base_url, headers=headers, json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024
            }, timeout=30)

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


class GeminiAPI:
    """Google Gemini API client"""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    def find_dates(self, artwork_name: str, subject: str, context: str) -> dict:
        if not self.api_key or self.api_key.startswith("your_"):
            return {"error": "Gemini API key not configured"}

        prompt = f"""Find key dates relevant to selling this Shepard Fairey artwork on eBay.

Artwork: {artwork_name}
Subject/Theme: {subject}
Context: {context}

Return JSON with dates that would be good for listing/promoting this art:
{{
    "national_event": {{"name": "event name", "date": "Month Day"}},
    "key_event_1": {{"name": "event name", "date": "Month Day"}},
    "key_event_2": {{"name": "event name", "date": "Month Day"}},
    "key_event_3": {{"name": "event name", "date": "Month Day"}},
    "reasoning": "why these dates matter for selling this piece"
}}

Focus on: anniversaries, birthdays, cultural events, political events, art world dates."""

        try:
            resp = requests.post(
                f"{self.base_url}?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=30
            )

            if resp.status_code == 200:
                content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                return {"source": "gemini", "data": json.loads(content.strip())}
        except Exception as e:
            return {"error": f"Gemini error: {e}"}
        return {"error": "Gemini request failed"}


class GrokAPI:
    """xAI Grok API client"""

    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY")
        self.base_url = "https://api.x.ai/v1/chat/completions"

    def find_dates(self, artwork_name: str, subject: str, context: str) -> dict:
        if not self.api_key or self.api_key.startswith("your_"):
            return {"error": "Grok API key not configured"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        prompt = f"""Find key dates relevant to selling this Shepard Fairey artwork on eBay.

Artwork: {artwork_name}
Subject/Theme: {subject}
Context: {context}

Return JSON with dates that would be good for listing/promoting this art:
{{
    "national_event": {{"name": "event name", "date": "Month Day"}},
    "key_event_1": {{"name": "event name", "date": "Month Day"}},
    "key_event_2": {{"name": "event name", "date": "Month Day"}},
    "key_event_3": {{"name": "event name", "date": "Month Day"}},
    "reasoning": "why these dates matter for selling this piece"
}}

Focus on: anniversaries, birthdays, cultural events, political events, art world dates."""

        try:
            resp = requests.post(self.base_url, headers=headers, json={
                "model": "grok-3",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024
            }, timeout=30)

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


# =============================================================================
# MULTI-LLM ORCHESTRATOR
# =============================================================================

class KeyDateOrchestrator:
    """Coordinates 4 LLMs to find and validate key dates"""

    def __init__(self):
        self.wikipedia = WikipediaAPI()
        self.claude = ClaudeAPI()
        self.openai = OpenAIAPI()
        self.gemini = GeminiAPI()
        self.grok = GrokAPI()

    def extract_subject(self, artwork_name: str) -> str:
        """Extract the subject from artwork name"""
        if not artwork_name or not isinstance(artwork_name, str):
            return ""
        # Remove common prefixes
        name = artwork_name.replace("Shepard Fairey ", "")
        name = name.replace("Obey Giant", "").replace("Signed Print", "")
        # Extract year if present
        parts = name.split()
        subject_parts = [p for p in parts if not p.isdigit() and len(p) > 2]
        return " ".join(subject_parts).strip()

    def get_wikipedia_context(self, subject: str) -> str:
        """Get Wikipedia context for the subject"""
        wiki_data = self.wikipedia.search(subject)
        if wiki_data:
            return wiki_data.get("extract", "")[:500]
        return ""

    def find_dates_for_artwork(self, artwork_name: str) -> dict:
        """Query all 4 LLMs in parallel and combine results"""
        subject = self.extract_subject(artwork_name)
        wiki_context = self.get_wikipedia_context(subject)

        print(f"\n🎨 Processing: {artwork_name}")
        print(f"   Subject: {subject}")

        results = {}

        # Query all LLMs in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self.claude.find_dates, artwork_name, subject, wiki_context): "claude",
                executor.submit(self.openai.find_dates, artwork_name, subject, wiki_context): "openai",
                executor.submit(self.gemini.find_dates, artwork_name, subject, wiki_context): "gemini",
                executor.submit(self.grok.find_dates, artwork_name, subject, wiki_context): "grok",
            }

            for future in as_completed(futures):
                llm_name = futures[future]
                try:
                    result = future.result()
                    results[llm_name] = result
                    if "error" not in result:
                        print(f"   ✅ {llm_name}: found dates")
                    else:
                        print(f"   ❌ {llm_name}: {result.get('error', 'failed')}")
                except Exception as e:
                    results[llm_name] = {"error": str(e)}
                    print(f"   ❌ {llm_name}: {e}")

        # Combine and validate results
        return self.combine_results(results, artwork_name)

    def combine_results(self, results: dict, artwork_name: str) -> dict:
        """Combine results from multiple LLMs, prioritizing consensus"""
        combined = {
            "artwork": artwork_name,
            "national_event": None,
            "key_event_1": None,
            "key_event_2": None,
            "key_event_3": None,
            "key_event_4": None,
            "key_event_5": None,
            "sources": []
        }

        all_events = []

        for llm_name, result in results.items():
            if "error" not in result and "data" in result:
                data = result["data"]
                combined["sources"].append(llm_name)

                # Collect all events
                for key in ["national_event", "key_event_1", "key_event_2", "key_event_3"]:
                    if key in data and data[key]:
                        event = data[key]
                        if isinstance(event, dict) and "name" in event:
                            all_events.append({
                                "name": event.get("name"),
                                "date": event.get("date"),
                                "source": llm_name,
                                "type": key
                            })

        # Deduplicate and assign to slots
        seen_names = set()
        slot_index = 0
        slots = ["national_event", "key_event_1", "key_event_2", "key_event_3", "key_event_4", "key_event_5"]

        for event in all_events:
            if event["name"] and event["name"].lower() not in seen_names and slot_index < len(slots):
                seen_names.add(event["name"].lower())
                combined[slots[slot_index]] = f"{event['name']} / {event['date']}"
                slot_index += 1

        return combined


# =============================================================================
# MAIN SCRIPT
# =============================================================================

def process_inventory(excel_path: str, output_path: str = None):
    """Process the inventory Excel file and find key dates"""

    print("=" * 60)
    print("🔑 KEY DATE FINDER FOR EBAY ART INVENTORY")
    print("=" * 60)

    # Load inventory
    df = pd.read_excel(excel_path, sheet_name="EVENTS")
    print(f"\n📦 Loaded {len(df)} items from inventory")

    orchestrator = KeyDateOrchestrator()

    # Process each artwork
    for idx, row in df.iterrows():
        artwork_name = row.get("NAME", "")
        if not artwork_name or pd.isna(artwork_name) or not isinstance(artwork_name, str):
            continue

        result = orchestrator.find_dates_for_artwork(artwork_name)

        # Update dataframe
        if result.get("national_event"):
            df.at[idx, "NATIONAL EVENT 1"] = result["national_event"]
        if result.get("key_event_1"):
            df.at[idx, "KEY EVENT 1"] = result["key_event_1"]
        if result.get("key_event_2"):
            df.at[idx, "EVENT 2"] = result["key_event_2"]
        if result.get("key_event_3"):
            df.at[idx, "EVENT 3"] = result["key_event_3"]
        if result.get("key_event_4"):
            df.at[idx, "EVENT 4"] = result["key_event_4"]
        if result.get("key_event_5"):
            df.at[idx, "EVENT 5"] = result["key_event_5"]

    # Save results
    if output_path is None:
        output_path = excel_path.replace(".xlsx", "_with_dates.xlsx")

    df.to_excel(output_path, sheet_name="EVENTS", index=False)
    print(f"\n✅ Saved results to: {output_path}")

    return df


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
    else:
        excel_path = "/Applications/SHEPARD FAIREY.xlsx"

    process_inventory(excel_path)
