#!/usr/bin/env python3
"""
Re-authenticate Google with Calendar + Sheets scopes
"""
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow

os.chdir('/Users/johnshay/DATARADAR')

# Scopes needed for Calendar + Sheets
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/spreadsheets'
]

# Delete old token
if os.path.exists('token.pickle'):
    os.remove('token.pickle')
    print("Removed old token")

# Create new auth flow
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=8080)

# Save new token
with open('token.pickle', 'wb') as token:
    pickle.dump(creds, token)

print("New token saved with Calendar + Sheets access!")
print(f"Scopes: {creds.scopes}")
