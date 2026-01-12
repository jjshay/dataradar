#!/usr/bin/env python3
"""
DATARADAR Health Check
Run this to verify all systems are working
"""

import os
import pickle
import requests
import subprocess

os.chdir('/Users/johnshay/DATARADAR')

def check_mark(ok):
    return "✅" if ok else "❌"

print("=" * 50)
print("DATARADAR HEALTH CHECK")
print("=" * 50)

issues = []

# 1. Check .env file
env_ok = os.path.exists('.env')
print(f"{check_mark(env_ok)} .env file exists")
if not env_ok:
    issues.append("Missing .env file")

# 2. Check Google token
token_ok = False
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as f:
        creds = pickle.load(f)
    has_sheets = 'spreadsheets' in str(creds.scopes)
    token_ok = has_sheets and creds.refresh_token
    print(f"{check_mark(token_ok)} Google token (sheets={has_sheets}, refresh={creds.refresh_token is not None})")
else:
    print(f"{check_mark(False)} Google token - MISSING")
    issues.append("Run: python3 setup_google_auth.py")

# 3. Check web app running
try:
    resp = requests.get('http://localhost:5050/api/stats', timeout=5)
    webapp_ok = resp.status_code == 200
    data = resp.json()
    print(f"{check_mark(webapp_ok)} Web app running ({data.get('listings', 0)} listings)")
except:
    webapp_ok = False
    print(f"{check_mark(False)} Web app - NOT RUNNING")
    issues.append("Run: launchctl load ~/Library/LaunchAgents/com.dataradar.webapp.plist")

# 4. Check daily scanner scheduled
result = subprocess.run(['launchctl', 'list'], capture_output=True, text=True)
scanner_ok = 'com.dataradar.dailyscan' in result.stdout
print(f"{check_mark(scanner_ok)} Daily scanner scheduled")
if not scanner_ok:
    issues.append("Run: launchctl load ~/Library/LaunchAgents/com.dataradar.dailyscan.plist")

# 5. Check eBay API
try:
    env_vars = {}
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                env_vars[k] = v

    import base64
    creds = f"{env_vars['EBAY_CLIENT_ID']}:{env_vars['EBAY_CLIENT_SECRET']}"
    encoded = base64.b64encode(creds.encode()).decode()

    resp = requests.post(
        'https://api.ebay.com/identity/v1/oauth2/token',
        headers={'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f'Basic {encoded}'},
        data={'grant_type': 'client_credentials', 'scope': 'https://api.ebay.com/oauth/api_scope'}
    )
    ebay_ok = resp.status_code == 200
    print(f"{check_mark(ebay_ok)} eBay API connection")
except Exception as e:
    ebay_ok = False
    print(f"{check_mark(False)} eBay API - {e}")
    issues.append("Check eBay credentials in .env")

# 6. Check logs directory
logs_ok = os.path.exists('logs')
print(f"{check_mark(logs_ok)} Logs directory")
if not logs_ok:
    os.makedirs('logs')
    print("  Created logs directory")

print("\n" + "=" * 50)
if issues:
    print("ISSUES FOUND:")
    for issue in issues:
        print(f"  • {issue}")
else:
    print("ALL SYSTEMS OK ✅")
print("=" * 50)
