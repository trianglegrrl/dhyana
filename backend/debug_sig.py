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

# Test data - using the same as the test
slack_block_actions_payload = {
    'type': 'block_actions',
    'user': {'id': 'U1234567890', 'name': 'testuser'},
    'api_app_id': 'A1234567890',
    'token': 'test_token',
    'container': {'type': 'message', 'message_ts': '1234567890.123456'},
    'trigger_id': 'trigger_123456789',
    'team': {'id': 'T1234567890', 'domain': 'testteam'},
    'channel': {'id': 'C1234567890', 'name': 'general'},
    'actions': [{
        'action_id': 'jobber_view_job',
        'block_id': 'jobber_actions',
        'text': {'type': 'plain_text', 'text': 'View Job'},
        'value': 'job_123',
        'type': 'button',
        'action_ts': '1234567890.123456'
    }]
}

payload_str = json.dumps(slack_block_actions_payload)
print(f"Payload JSON: {payload_str[:200]}...")

# Test urlencode output
test_body = urlencode({'payload': payload_str})
print(f"\nTest body (urlencode): {test_body[:200]}...")

# Test with %3A replaced with :
colon_replaced = test_body.replace('%3A', ':')
print(f"\nColon replaced: {colon_replaced[:200]}...")

# Try other common URL encoding differences
comma_replaced = colon_replaced.replace('%2C', ',')
print(f"\nComma also replaced: {comma_replaced[:200]}...")

# Try replacing all the main URL encodings
import urllib.parse
# Decode everything
fully_decoded = urllib.parse.unquote_plus(test_body)
print(f"\nFully decoded: {fully_decoded[:200]}...")

# Let me create a function to mimic Flask's form encoding
def flask_style_encode(data):
    """Try to mimic how Flask encodes form data"""
    # Start with standard urlencode
    encoded = urlencode(data)
    # Common differences in encoding
    encoded = encoded.replace('%3A', ':')  # colons
    encoded = encoded.replace('%2C', ',')  # commas
    return encoded

flask_style_body = flask_style_encode({'payload': payload_str})
print(f"\nFlask style body: {flask_style_body[:200]}...")

# Test all variations with signatures
timestamp = str(int(datetime.now().timestamp()))
verifier = SignatureVerifier('test_signing_secret')

print(f"\n--- Signature Tests ---")
for name, body in [
    ("Original urlencode", test_body),
    ("Colon replaced", colon_replaced),
    ("Comma also replaced", comma_replaced),
    ("Fully decoded", fully_decoded),
    ("Flask style", flask_style_body)
]:
    sig = generate_slack_signature('test_signing_secret', timestamp, body)
    headers = {'X-Slack-Request-Timestamp': timestamp, 'X-Slack-Signature': sig}
    is_valid = verifier.is_valid_request(body.encode(), headers)
    print(f"{name:20}: {sig[:20]}... valid={is_valid}")