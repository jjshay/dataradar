# DateDriven

**AI-powered key date discovery for eBay sellers** - Orchestrates 4 LLMs (Claude, GPT-4, Gemini, Grok) + Wikipedia to find optimal listing dates for collectible inventory.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![LLMs](https://img.shields.io/badge/LLMs-4%20Models-purple.svg)

## The Problem

Selling art and collectibles on eBay? Timing matters. A Muhammad Ali print sells better around his birthday (Jan 17) or during Black History Month. A John Lennon piece peaks around his birthday (Oct 9) or the anniversary of his death (Dec 8).

Manually researching key dates for hundreds of inventory items is tedious and error-prone.

## The Solution

DateDriven automatically:
1. **Analyzes your inventory** - Extracts subjects from item names
2. **Queries Wikipedia** - Gets context about each subject
3. **Orchestrates 4 LLMs in parallel** - Claude, GPT-4, Gemini, and Grok each suggest relevant dates
4. **Combines & validates results** - Deduplicates and prioritizes consensus dates
5. **Syncs to Google Calendar** - Creates reminders before each key date

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DateDriven                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌─────────────────────────────────────────┐   │
│  │  Excel   │───▶│         KeyDateOrchestrator              │   │
│  │ Inventory│    │                                          │   │
│  └──────────┘    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  │   │
│                  │  │ Claude  │  │  GPT-4  │  │  Grok   │  │   │
│  ┌──────────┐    │  │   API   │  │   API   │  │   API   │  │   │
│  │Wikipedia │───▶│  └────┬────┘  └────┬────┘  └────┬────┘  │   │
│  │   API    │    │       │            │            │        │   │
│  └──────────┘    │       └────────────┼────────────┘        │   │
│                  │                    ▼                      │   │
│                  │           ┌───────────────┐              │   │
│                  │           │   Combine &   │              │   │
│                  │           │   Validate    │              │   │
│                  │           └───────┬───────┘              │   │
│                  └───────────────────┼──────────────────────┘   │
│                                      ▼                          │
│                  ┌───────────────────────────────────────┐      │
│                  │         Google Calendar API            │      │
│                  │    (Reminders 7 days before dates)     │      │
│                  └───────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

## Results

Tested on 98 Shepard Fairey art prints:

| Metric | Result |
|--------|--------|
| Items processed | 98 |
| Key dates found | 474 |
| Avg dates per item | 6 |
| LLMs responding | 3/4 (75%) |
| Processing time | ~5 min |

### Sample Output

| Artwork | Key Dates Found |
|---------|-----------------|
| Muhammad Ali Print | Ali's Birthday (Jan 17), Death Anniversary (Jun 3), Black History Month (Feb), Boxing Day (Dec 26) |
| Lenin Record | May Day (May 1), Lenin's Birthday (Apr 22), Russian Revolution (Nov 7) |
| John Lennon Canvas | Lennon's Birthday (Oct 9), Death Anniversary (Dec 8), Imagine Day (Oct 11) |
| Keith Haring Print | Haring's Birthday (May 4), Death Anniversary (Feb 16), World AIDS Day (Dec 1) |

## Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/DateDriven.git
cd DateDriven

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

Create a `.env` file with your API keys:

```env
CLAUDE_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_google_ai_key
GROK_API_KEY=your_xai_key
```

For Google Calendar integration:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable Google Calendar API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download as `credentials.json`

## Usage

### Basic Usage

```python
from key_date_finder import process_inventory

# Process your inventory Excel file
process_inventory('inventory.xlsx', 'output_with_dates.xlsx')
```

### Sync to Google Calendar

```python
from calendar_sync import sync_to_calendar

# Create calendar reminders 7 days before each key date
sync_to_calendar('output_with_dates.xlsx', days_before=7)
```

### Full Pipeline

```bash
python run.py
```

### Pop Culture Mode (Death NYC, Street Art)

For pop art and mashup artists like Death NYC, use the creative date finder that focuses on **subjects, characters, and brands** rather than release dates:

```python
from death_nyc_finder import process_death_nyc

# Find dates based on Mickey Mouse, Louis Vuitton, Banksy, etc.
process_death_nyc('inventory.xlsx', 'output_with_dates.xlsx')
```

This mode finds dates like:
- **Character Events**: Mickey Mouse Debut (Nov 18), Batman Day (Sept)
- **Brand Anniversaries**: Louis Vuitton Founded (Aug 4), Supreme NYC Opening
- **Art World**: Art Basel Miami (Dec), Warhol's Birthday (Aug 6)
- **Pop Culture**: Met Gala (May), Comic-Con (July), Oscars (March)

## Excel Format

Your inventory Excel should have an "EVENTS" sheet with these columns:

| Column | Description |
|--------|-------------|
| NAME | Full item name (e.g., "Shepard Fairey Muhammad Ali 2006 Signed Print") |
| NATIONAL EVENT 1 | (Output) National/major event date |
| KEY EVENT 1-5 | (Output) Relevant key dates |

## How the Multi-LLM Orchestration Works

1. **Parallel Queries**: All 4 LLMs are queried simultaneously using ThreadPoolExecutor
2. **Structured Output**: Each LLM returns JSON with event names and dates
3. **Consensus Building**: Results are deduplicated; events mentioned by multiple LLMs are prioritized
4. **Graceful Degradation**: If an LLM fails or times out, others continue

```python
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {
        executor.submit(self.claude.find_dates, artwork, subject, context): "claude",
        executor.submit(self.openai.find_dates, artwork, subject, context): "openai",
        executor.submit(self.gemini.find_dates, artwork, subject, context): "gemini",
        executor.submit(self.grok.find_dates, artwork, subject, context): "grok",
    }
```

## Project Structure

```
DateDriven/
├── key_date_finder.py   # Main orchestrator + LLM clients (Shepard Fairey, etc.)
├── death_nyc_finder.py  # Pop culture mode for mashup art (Death NYC, etc.)
├── calendar_sync.py     # Google Calendar integration
├── sync_death_nyc.py    # Death NYC calendar sync with smart date parser
├── ebay_pricing.py      # Automatic pricing based on calendar events
├── demo.py              # Demo script for showcasing
├── run.py               # CLI entry point
├── requirements.txt     # Python dependencies
├── .env.example         # API key template
└── README.md
```

## API Costs

Estimated costs per 100 items:
- Claude (Sonnet): ~$0.15
- GPT-4o: ~$0.20
- Gemini Flash: ~$0.01
- Grok: ~$0.10

**Total: ~$0.50 per 100 items**

## Automated Pricing (New!)

DateDriven can automatically adjust eBay prices based on upcoming key dates. Prices increase as key dates approach, maximizing revenue during peak collector interest.

### Pricing Rules

| Days Before Event | Price Multiplier |
|-------------------|------------------|
| 14+ days | 1.15x (15% markup) |
| 7-13 days | 1.25x (25% markup) |
| 3-6 days | 1.35x (35% markup) |
| 0-2 days | 1.20x (20% markup) |
| After event | 1.0x (base price) |

### Usage

```python
from ebay_pricing import run_pricing_automation

# Preview recommendations (dry run)
run_pricing_automation(
    inventory_path='inventory.xlsx',
    days_ahead=30,
    dry_run=True
)

# Apply price changes to eBay
run_pricing_automation(
    inventory_path='inventory.xlsx',
    days_ahead=30,
    dry_run=False
)
```

### eBay API Setup

1. Go to [eBay Developer Portal](https://developer.ebay.com/)
2. Create an application
3. Generate a User Token with `sell.inventory` scope
4. Add to `.env`:
```env
EBAY_CLIENT_ID=your_client_id
EBAY_CLIENT_SECRET=your_client_secret
EBAY_REFRESH_TOKEN=your_refresh_token
```

### 3DSellers Alternative

If you use 3DSellers, you can set up automation rules directly in their dashboard:
1. Log into 3DSellers
2. Go to Automation > Rules
3. Create catalog-based rules for seasonal pricing

## Future Enhancements

- [ ] Web UI for non-technical users
- [x] eBay API integration for automatic pricing
- [ ] More data sources (Wikidata, art databases)
- [ ] Price history correlation with key dates
- [ ] Batch processing with rate limiting
- [ ] Scheduled daily price updates via cron

## License

MIT License - See [LICENSE](LICENSE) for details.

## Author

Built by [John Shay](https://github.com/yourusername)

---

*DateDriven was built to solve a real problem: optimizing eBay listing timing for a collection of 98 Shepard Fairey prints. It demonstrates multi-LLM orchestration, API integration, and practical automation.*
