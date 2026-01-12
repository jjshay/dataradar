#!/usr/bin/env python3
"""
eBay OAuth Helper - Generates refresh token for API access
Run this once to authorize DATARADAR to update your eBay listings
"""

import os
import base64
import webbrowser
from urllib.parse import urlencode, parse_qs, urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from dotenv import load_dotenv

load_dotenv()

# eBay OAuth endpoints
SANDBOX_AUTH_URL = "https://auth.sandbox.ebay.com/oauth2/authorize"
SANDBOX_TOKEN_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
PROD_AUTH_URL = "https://auth.ebay.com/oauth2/authorize"
PROD_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

# Required scope for pricing updates
SCOPES = "https://api.ebay.com/oauth/api_scope/sell.inventory"

# Your registered RuName from eBay Developer Portal
REDIRECT_URI = "Gauntlet_Gallery-Gauntlet-Gaunt-dpmhyxh"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback from eBay"""

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if 'code' in query:
            self.server.auth_code = query['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                </body></html>
            """)
        else:
            self.server.auth_code = None
            error = query.get('error', ['Unknown error'])[0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"<html><body><h1>Error: {error}</h1></body></html>".encode())

    def log_message(self, format, *args):
        pass  # Suppress logging


def get_auth_url(client_id: str, sandbox: bool = True) -> str:
    """Generate eBay OAuth authorization URL"""
    base_url = SANDBOX_AUTH_URL if sandbox else PROD_AUTH_URL

    params = {
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': SCOPES,
    }

    return f"{base_url}?{urlencode(params)}"


def exchange_code_for_tokens(code: str, client_id: str, client_secret: str, sandbox: bool = True) -> dict:
    """Exchange authorization code for access/refresh tokens"""
    token_url = SANDBOX_TOKEN_URL if sandbox else PROD_TOKEN_URL

    # Create Basic auth header
    credentials = f"{client_id}:{client_secret}"
    encoded_creds = base64.b64encode(credentials.encode()).decode()

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {encoded_creds}'
    }

    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }

    response = requests.post(token_url, headers=headers, data=data)
    return response.json()


def run_oauth_flow():
    """Run the full OAuth flow to get refresh token"""

    client_id = os.getenv('EBAY_CLIENT_ID')
    client_secret = os.getenv('EBAY_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("ERROR: EBAY_CLIENT_ID and EBAY_CLIENT_SECRET must be set in .env")
        return

    # Detect sandbox vs production
    sandbox = 'SBX' in client_id or 'sandbox' in client_id.lower()
    env_type = "SANDBOX" if sandbox else "PRODUCTION"

    print("=" * 60)
    print(f"eBay OAuth Flow ({env_type})")
    print("=" * 60)
    print(f"\nClient ID: {client_id[:30]}...")
    print(f"Environment: {env_type}")
    print(f"\nThis will open your browser to authorize DATARADAR.")
    print("You'll need to log into your eBay account and approve access.\n")

    input("Press Enter to continue...")

    # Start local server for callback
    server = HTTPServer(('localhost', 8888), OAuthCallbackHandler)
    server.auth_code = None

    # Open browser to authorization URL
    auth_url = get_auth_url(client_id, sandbox)
    print(f"\nOpening browser to:\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("Waiting for authorization...")

    # Wait for callback
    while server.auth_code is None:
        server.handle_request()

    print(f"\nReceived authorization code: {server.auth_code[:20]}...")

    # Exchange code for tokens
    print("\nExchanging code for tokens...")
    tokens = exchange_code_for_tokens(server.auth_code, client_id, client_secret, sandbox)

    if 'error' in tokens:
        print(f"\nERROR: {tokens.get('error')}")
        print(f"Description: {tokens.get('error_description', 'Unknown')}")
        return

    refresh_token = tokens.get('refresh_token')
    access_token = tokens.get('access_token')
    expires_in = tokens.get('expires_in', 0)

    print("\n" + "=" * 60)
    print("SUCCESS! Here are your tokens:")
    print("=" * 60)
    print(f"\nRefresh Token (save this!):\n{refresh_token}\n")
    print(f"Access Token (expires in {expires_in}s):\n{access_token[:50]}...\n")

    print("\nAdd this to your .env file:")
    print(f"EBAY_REFRESH_TOKEN={refresh_token}")

    # Offer to update .env automatically
    update = input("\nUpdate .env file automatically? (y/n): ").strip().lower()
    if update == 'y':
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        with open(env_path, 'a') as f:
            f.write(f"\nEBAY_REFRESH_TOKEN={refresh_token}\n")
        print(f"Updated {env_path}")

    print("\nDone! You can now run ebay_pricing.py to update prices.")


if __name__ == "__main__":
    run_oauth_flow()
