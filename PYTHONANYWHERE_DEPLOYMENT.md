# DATARADAR - PythonAnywhere Deployment Guide

## Overview

This guide will help you deploy DATARADAR to PythonAnywhere with:
- Flask web dashboard
- Scheduled daily deal scanner
- Automated eBay pricing updates

## Prerequisites

- PythonAnywhere Hacker account ($5/mo) - Required for unrestricted API access
- Your local DATARADAR folder with working credentials

## Step 1: Upload Files to PythonAnywhere

### Option A: Using Git (Recommended)

1. Go to **Consoles** > **Bash**
2. Run:
```bash
cd ~
git clone https://github.com/YOUR_USERNAME/DATARADAR.git
```

### Option B: Manual Upload

1. Go to **Files** tab
2. Create folder: `/home/YOUR_USERNAME/DATARADAR/`
3. Upload these files from your local DATARADAR folder:
   - `app_pythonanywhere.py`
   - `daily_scanner_pa.py`
   - `ebay_auto_pricing_pa.py`
   - `pricing_engine.py`
   - `requirements.txt`
   - `.env`
   - `token.pickle` (your Google OAuth token)
   - `pricing_rules.json`
   - `templates/` folder (with index.html)

## Step 2: Install Dependencies

1. Go to **Consoles** > **Bash**
2. Run:
```bash
cd ~/DATARADAR
pip3 install --user -r requirements.txt
```

## Step 3: Configure Web App

1. Go to **Web** tab
2. Click **Add a new web app**
3. Choose **Manual configuration** > **Python 3.10**
4. Set these values:

| Setting | Value |
|---------|-------|
| Source code | `/home/YOUR_USERNAME/DATARADAR` |
| Working directory | `/home/YOUR_USERNAME/DATARADAR` |

5. Edit the **WSGI configuration file** and replace ALL contents with:

```python
import sys
import os

project_home = '/home/YOUR_USERNAME/DATARADAR'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

from app_listings import app as application
```

6. Click **Reload** button

## Step 4: Set Up Scheduled Tasks

Go to **Tasks** tab and add these scheduled tasks:

### Daily Scanner (runs at 8:00 AM UTC)
```
08:00
cd /home/YOUR_USERNAME/DATARADAR && python3 daily_scanner_pa.py
```

### Pricing Update (runs at 9:00 AM UTC)
```
09:00
cd /home/YOUR_USERNAME/DATARADAR && python3 ebay_auto_pricing_pa.py --live
```

## Step 5: Verify Deployment

1. Visit your web app URL: `https://YOUR_USERNAME.pythonanywhere.com`
2. Check the health endpoint: `https://YOUR_USERNAME.pythonanywhere.com/health`
3. View console output in **Web** > **Log files**

## Environment Variables (.env file)

Make sure your `.env` file in `/home/YOUR_USERNAME/DATARADAR/` contains:

```
EBAY_CLIENT_ID=your_ebay_client_id
EBAY_CLIENT_SECRET=your_ebay_client_secret
EBAY_REFRESH_TOKEN=your_ebay_refresh_token
EBAY_DEV_ID=your_ebay_dev_id

CLAUDE_API_KEY=your_claude_key
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key

DATARADAR_SHEET_ID=11a-_IWhljPJHeKV8vdke-JiLmm_KCq-bedSceKB0kZI
```

## Google OAuth Token

The `token.pickle` file contains your Google OAuth credentials for Sheets/Calendar access.

**Important:** This token was generated locally and includes refresh capabilities.
If it expires, you'll need to regenerate locally and re-upload.

To regenerate if needed:
1. On your local machine, run: `python3 setup_google_auth.py`
2. Complete the OAuth flow in your browser
3. Upload the new `token.pickle` to PythonAnywhere

## Troubleshooting

### "No module named X" error
```bash
pip3 install --user MODULE_NAME
```

### API access blocked
Ensure you have the Hacker plan - free accounts block external API calls.

### Token refresh errors
Re-upload `token.pickle` from your local machine after re-authenticating.

### View logs
- Web app errors: **Web** > **Error log**
- Task output: **Tasks** > click on task to see output

## File Structure on PythonAnywhere

```
/home/YOUR_USERNAME/DATARADAR/
├── app_pythonanywhere.py      # Flask web app
├── daily_scanner_pa.py        # Scheduled daily scanner
├── ebay_auto_pricing_pa.py    # Scheduled pricing updates
├── pricing_engine.py          # Core pricing logic
├── requirements.txt           # Python dependencies
├── .env                       # API keys and secrets
├── token.pickle               # Google OAuth token
├── pricing_rules.json         # Backup of pricing rules
├── templates/
│   └── index.html             # Web dashboard template
└── logs/                      # Runtime logs
```

## Quick Commands (in PythonAnywhere Bash)

```bash
# Test daily scanner
cd ~/DATARADAR && python3 daily_scanner_pa.py

# Test pricing (dry run)
cd ~/DATARADAR && python3 ebay_auto_pricing_pa.py

# Test pricing (live)
cd ~/DATARADAR && python3 ebay_auto_pricing_pa.py --live

# Check health
curl https://YOUR_USERNAME.pythonanywhere.com/health
```
