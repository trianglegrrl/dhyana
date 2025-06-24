#!/usr/bin/env python3

import json
import hmac
import hashlib
from datetime import datetime
from urllib.parse import urlencode
from slack_sdk.signature import SignatureVerifier

def generate_slack_signature(signing_secret: str, timestamp: str, body: str) -> str:
    """Generate Slack signature for testing"""
    sig_basestring = f'v0:{timestamp}:{body}'
    return 'v0=' + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

# Test data for commands
form_data = {
    'token': 'test_token',
    'team_id': 'T1234567890',
    'team_domain': 'test',
    'command': '/jobber',
    'text': 'status',
    'user_id': 'U1234567890',
    'user_name': 'testuser',
    'channel_id': 'C1234567890',
    'channel_name': 'general',
    'response_url': 'https://hooks.slack.com/commands/T1234567890/123456789/abcdef'
}

# What Flask actually receives (from debug output)
actual_flask_body = 'token=test_token&team_id=T1234567890&team_domain=test&command=/jobber&text=status&user_id=U1234567890&user_name=testuser&channel_id=C1234567890&channel_name=general&response_url=https://hooks.slack.co'

# Test approach with different encodings
timestamp = str(int(datetime.now().timestamp()))

print("=== Commands Signature Debug ===")

# 1. Standard urlencode
test_body = urlencode(form_data)
print(f"1. Standard urlencode: {test_body[:200]}...")

# 2. With colon and comma replacement
flask_style_1 = test_body.replace('%3A', ':').replace('%2C', ',')
print(f"2. Colon/comma replaced: {flask_style_1[:200]}...")

# 3. With more URL decoding
flask_style_2 = test_body.replace('%3A', ':').replace('%2C', ',').replace('%2F', '/')
print(f"3. Colon/comma/slash replaced: {flask_style_2[:200]}...")

# 4. Full URL decode
import urllib.parse
fully_decoded = urllib.parse.unquote_plus(test_body)
print(f"4. Fully decoded: {fully_decoded[:200]}...")

# 5. Try to match exact Flask output
# The flask body seems to cut off, let me build what the full one should be
full_flask_body = urlencode(form_data, quote_via=urllib.parse.quote)
print(f"5. quote_via=quote: {full_flask_body[:200]}...")

# Test signatures
verifier = SignatureVerifier('test_signing_secret')

print(f"\n=== Signature Tests ===")
for name, body in [
    ("Standard urlencode", test_body),
    ("Colon/comma replaced", flask_style_1),
    ("Colon/comma/slash replaced", flask_style_2),
    ("Fully decoded", fully_decoded),
    ("quote_via=quote", full_flask_body)
]:
    sig = generate_slack_signature('test_signing_secret', timestamp, body)
    headers = {'X-Slack-Request-Timestamp': timestamp, 'X-Slack-Signature': sig}
    is_valid = verifier.is_valid_request(body.encode(), headers)
    print(f"{name:25}: valid={is_valid}")

    # Also compare to actual Flask body (truncated)
    if body.startswith(actual_flask_body):
        print(f"  -> Matches Flask output prefix!")