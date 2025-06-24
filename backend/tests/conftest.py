import pytest
import json
import hmac
import hashlib
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from faker import Faker
import factory
from factory import fuzzy

# Import app and models
from app import create_app, db
from models.slack_models import SlackTeam, SlackUser, SlackChannel, SlackMessage
from models.jobber_models import JobberClient, JobberJob, JobberInvoice

fake = Faker()

# Test Configuration
@pytest.fixture(scope="session")
def app():
    """Create application for testing"""
    app = create_app('testing')

    # Configure additional test settings
    app.config.update({
        'SLACK_BOT_TOKEN': 'xoxb-test-token',
        'SLACK_SIGNING_SECRET': 'test_signing_secret',
        'JOBBER_API_KEY': 'test_api_key',
        'JOBBER_API_SECRET': 'test_api_secret',
        'JOBBER_WEBHOOK_SECRET': 'test_webhook_secret',
        'JOBBER_BASE_URL': 'https://api.test-jobber.com'
    })

    return app

@pytest.fixture(scope="function")
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture(scope="function")
def app_context(app):
    """Create application context"""
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def mock_slack_client():
    """Mock Slack API client"""
    with patch('utils.slack_client.SlackAPIClient') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        # Mock common responses
        mock_instance.post_message.return_value = {
            'ok': True,
            'ts': '1234567890.123456'
        }
        mock_instance.send_dm.return_value = {
            'ok': True,
            'ts': '1234567890.123456'
        }
        mock_instance.get_user_info.return_value = {
            'id': 'U1234567890',
            'name': 'testuser',
            'real_name': 'Test User',
            'profile': {'email': 'test@example.com'}
        }
        mock_instance.get_channel_info.return_value = {
            'id': 'C1234567890',
            'name': 'general',
            'is_private': False,
            'is_archived': False
        }

        yield mock_instance

@pytest.fixture
def mock_jobber_client():
    """Mock Jobber API client"""
    with patch('utils.jobber_client.JobberAPIClient') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        # Mock common responses
        mock_instance.get_client.return_value = {
            'id': 'client_123',
            'companyName': 'Test Company',
            'firstName': 'John',
            'lastName': 'Doe',
            'email': 'john@testcompany.com'
        }
        mock_instance.get_job.return_value = {
            'id': 'job_123',
            'title': 'Test Job',
            'client': {'id': 'client_123'},
            'jobStatus': 'scheduled'
        }
        mock_instance.get_invoice.return_value = {
            'id': 'invoice_123',
            'invoiceNumber': 'INV-001',
            'client': {'id': 'client_123'},
            'invoiceStatus': 'sent',
            'total': 150.00
        }

        yield mock_instance

# Test Data Factories
class SlackTeamFactory(factory.Factory):
    class Meta:
        model = dict

    team_id = factory.LazyFunction(lambda: f"T{fake.random_int(min=100000000, max=999999999)}")
    domain = factory.LazyAttribute(lambda obj: fake.word())
    name = factory.LazyAttribute(lambda obj: f"{fake.company()} Team")

class SlackUserFactory(factory.Factory):
    class Meta:
        model = dict

    user_id = factory.LazyFunction(lambda: f"U{fake.random_int(min=100000000, max=999999999)}")
    team_id = factory.LazyFunction(lambda: f"T{fake.random_int(min=100000000, max=999999999)}")
    username = factory.LazyAttribute(lambda obj: fake.user_name())
    real_name = factory.LazyAttribute(lambda obj: fake.name())
    email = factory.LazyAttribute(lambda obj: fake.email())
    is_bot = False
    is_admin = False
    timezone = "America/New_York"

class SlackChannelFactory(factory.Factory):
    class Meta:
        model = dict

    channel_id = factory.LazyFunction(lambda: f"C{fake.random_int(min=100000000, max=999999999)}")
    team_id = factory.LazyFunction(lambda: f"T{fake.random_int(min=100000000, max=999999999)}")
    name = factory.LazyAttribute(lambda obj: fake.word())
    is_private = False
    is_archived = False
    topic = factory.LazyAttribute(lambda obj: fake.sentence())
    purpose = factory.LazyAttribute(lambda obj: fake.sentence())

class SlackMessageFactory(factory.Factory):
    class Meta:
        model = dict

    channel = factory.LazyFunction(lambda: f"C{fake.random_int(min=100000000, max=999999999)}")
    user = factory.LazyFunction(lambda: f"U{fake.random_int(min=100000000, max=999999999)}")
    text = factory.LazyAttribute(lambda obj: fake.sentence())
    ts = factory.LazyFunction(lambda: f"{fake.random_int(min=1600000000, max=1700000000)}.{fake.random_int(min=100000, max=999999)}")
    type = "message"

class JobberClientFactory(factory.Factory):
    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: fake.uuid4())
    companyName = factory.LazyAttribute(lambda obj: fake.company())
    firstName = factory.LazyAttribute(lambda obj: fake.first_name())
    lastName = factory.LazyAttribute(lambda obj: fake.last_name())
    email = factory.LazyAttribute(lambda obj: fake.email())
    phoneNumber = factory.LazyAttribute(lambda obj: fake.phone_number())

class JobberJobFactory(factory.Factory):
    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: fake.uuid4())
    title = factory.LazyAttribute(lambda obj: f"{fake.word().title()} {fake.word().title()}")
    client = factory.SubFactory(JobberClientFactory)
    jobStatus = fuzzy.FuzzyChoice(['draft', 'scheduled', 'active', 'completed', 'cancelled'])
    description = factory.LazyAttribute(lambda obj: fake.paragraph())

class JobberInvoiceFactory(factory.Factory):
    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: fake.uuid4())
    invoiceNumber = factory.LazyFunction(lambda: f"INV-{fake.random_int(min=1000, max=9999)}")
    client = factory.SubFactory(JobberClientFactory)
    invoiceStatus = fuzzy.FuzzyChoice(['draft', 'sent', 'viewed', 'paid', 'overdue'])
    total = factory.LazyFunction(lambda: round(fake.random.uniform(50, 5000), 2))

# Webhook Payload Fixtures
@pytest.fixture
def slack_message_event():
    """Sample Slack message event"""
    user_data = SlackUserFactory()
    channel_data = SlackChannelFactory()
    message_data = SlackMessageFactory(
        channel=channel_data['channel_id'],
        user=user_data['user_id']
    )

    return {
        'token': 'test_token',
        'team_id': 'T1234567890',
        'api_app_id': 'A1234567890',
        'event': {
            'type': 'message',
            'channel': message_data['channel'],
            'user': message_data['user'],
            'text': message_data['text'],
            'ts': message_data['ts']
        },
        'type': 'event_callback',
        'event_id': 'Ev1234567890',
        'event_time': 1234567890,
        'authorizations': [
            {
                'enterprise_id': None,
                'team_id': 'T1234567890',
                'user_id': 'U1234567890',
                'is_bot': True
            }
        ]
    }

@pytest.fixture
def slack_app_mention_event():
    """Sample Slack app mention event"""
    return {
        'token': 'test_token',
        'team_id': 'T1234567890',
        'api_app_id': 'A1234567890',
        'event': {
            'type': 'app_mention',
            'channel': 'C1234567890',
            'user': 'U1234567890',
            'text': '<@U0LAN0Z89> hello',
            'ts': '1234567890.123456'
        },
        'type': 'event_callback'
    }

@pytest.fixture
def slack_channel_created_event():
    """Sample Slack channel created event"""
    channel_data = SlackChannelFactory()
    return {
        'token': 'test_token',
        'team_id': channel_data['team_id'],
        'api_app_id': 'A1234567890',
        'event': {
            'type': 'channel_created',
            'channel': {
                'id': channel_data['channel_id'],
                'name': channel_data['name'],
                'created': 1234567890,
                'creator': 'U1234567890'
            }
        },
        'type': 'event_callback'
    }

@pytest.fixture
def slack_user_joined_event():
    """Sample Slack user joined event"""
    user_data = SlackUserFactory()
    return {
        'token': 'test_token',
        'team_id': user_data['team_id'],
        'api_app_id': 'A1234567890',
        'event': {
            'type': 'team_join',
            'user': {
                'id': user_data['user_id'],
                'name': user_data['username'],
                'real_name': user_data['real_name'],
                'profile': {
                    'email': user_data['email']
                }
            }
        },
        'type': 'event_callback'
    }

@pytest.fixture
def slack_block_actions_payload():
    """Sample Slack block actions payload"""
    return {
        'type': 'block_actions',
        'user': {
            'id': 'U1234567890',
            'name': 'testuser'
        },
        'api_app_id': 'A1234567890',
        'token': 'test_token',
        'container': {
            'type': 'message',
            'message_ts': '1234567890.123456'
        },
        'trigger_id': 'trigger_123456789',
        'team': {
            'id': 'T1234567890',
            'domain': 'testteam'
        },
        'channel': {
            'id': 'C1234567890',
            'name': 'general'
        },
        'actions': [
            {
                'action_id': 'jobber_view_job',
                'block_id': 'jobber_actions',
                'text': {
                    'type': 'plain_text',
                    'text': 'View Job'
                },
                'value': 'job_123',
                'type': 'button',
                'action_ts': '1234567890.123456'
            }
        ]
    }

@pytest.fixture
def jobber_client_webhook():
    """Sample Jobber client webhook payload"""
    client_data = JobberClientFactory()
    return {
        'topic': 'CLIENT_CREATE',
        'itemId': client_data['id'],
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'data': client_data
    }

@pytest.fixture
def jobber_job_webhook():
    """Sample Jobber job webhook payload"""
    job_data = JobberJobFactory()
    return {
        'topic': 'JOB_CREATE',
        'itemId': job_data['id'],
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'data': job_data
    }

@pytest.fixture
def jobber_invoice_webhook():
    """Sample Jobber invoice webhook payload"""
    invoice_data = JobberInvoiceFactory()
    return {
        'topic': 'INVOICE_CREATE',
        'itemId': invoice_data['id'],
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'data': invoice_data
    }

# Utility Functions
def generate_slack_signature(signing_secret: str, timestamp: str, body: str) -> str:
    """Generate Slack signature for testing"""
    sig_basestring = f'v0:{timestamp}:{body}'
    return 'v0=' + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

def generate_jobber_signature(webhook_secret: str, body: str) -> str:
    """Generate Jobber signature for testing"""
    return hmac.new(
        webhook_secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

@pytest.fixture
def slack_signature_headers():
    """Generate Slack signature headers for testing"""
    def _generate_headers(body: str, signing_secret: str = 'test_signing_secret'):
        timestamp = str(int(datetime.now().timestamp()))
        signature = generate_slack_signature(signing_secret, timestamp, body)
        return {
            'X-Slack-Request-Timestamp': timestamp,
            'X-Slack-Signature': signature,
            'Content-Type': 'application/json'
        }
    return _generate_headers

@pytest.fixture
def jobber_signature_headers():
    """Generate Jobber signature headers for testing"""
    def _generate_headers(body: str, webhook_secret: str = 'test_webhook_secret'):
        signature = generate_jobber_signature(webhook_secret, body)
        return {
            'X-Jobber-Signature': f'sha256={signature}',
            'Content-Type': 'application/json'
        }
    return _generate_headers