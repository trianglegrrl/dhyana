import pytest
import json
from unittest.mock import patch, MagicMock
from slack_sdk.errors import SlackApiError

from utils.slack_client import SlackAPIClient, SlackMessageBuilder, get_slack_client


class TestSlackAPIClient:
    """Test Slack API client functionality"""

    def test_client_initialization_with_token(self):
        """Test client initialization with token"""
        client = SlackAPIClient(bot_token='xoxb-test-token')
        assert client.bot_token == 'xoxb-test-token'
        assert client.max_retries == 3

    def test_client_initialization_no_token_raises_error(self, app_context):
        """Test that missing token raises error"""
        with app_context.app_context():
            # Temporarily remove the token from config
            original_token = app_context.config.get('SLACK_BOT_TOKEN')
            app_context.config['SLACK_BOT_TOKEN'] = None

            with pytest.raises(ValueError, match="Slack bot token is required"):
                SlackAPIClient()

            # Restore the token
            app_context.config['SLACK_BOT_TOKEN'] = original_token

    @patch('utils.slack_client.WebClient')
    def test_post_message_success(self, mock_webclient):
        """Test successful message posting"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.chat_postMessage.return_value = {
            'ok': True,
            'ts': '1234567890.123456'
        }

        slack_client = SlackAPIClient(bot_token='xoxb-test-token')
        result = slack_client.post_message(
            channel='C1234567890',
            text='Test message',
            blocks=[{'type': 'section', 'text': {'type': 'mrkdwn', 'text': 'Test'}}]
        )

        assert result['ok'] is True
        assert result['ts'] == '1234567890.123456'
        mock_client.chat_postMessage.assert_called_once()

    @patch('utils.slack_client.WebClient')
    def test_post_message_ephemeral(self, mock_webclient):
        """Test ephemeral message posting"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.chat_postEphemeral.return_value = {
            'ok': True,
            'ts': '1234567890.123456'
        }

        slack_client = SlackAPIClient(bot_token='xoxb-test-token')
        result = slack_client.post_message(
            channel='C1234567890',
            text='Ephemeral message',
            ephemeral_user='U1234567890'
        )

        assert result['ok'] is True
        mock_client.chat_postEphemeral.assert_called_once()

    @patch('utils.slack_client.WebClient')
    def test_send_dm_success(self, mock_webclient):
        """Test successful DM sending"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client

        # Mock conversation open and message post
        mock_client.conversations_open.return_value = {
            'channel': {'id': 'D1234567890'}
        }
        mock_client.chat_postMessage.return_value = {
            'ok': True,
            'ts': '1234567890.123456'
        }

        slack_client = SlackAPIClient(bot_token='xoxb-test-token')
        result = slack_client.send_dm(
            user_id='U1234567890',
            text='DM message'
        )

        assert result['ok'] is True
        mock_client.conversations_open.assert_called_once_with(users=['U1234567890'])
        mock_client.chat_postMessage.assert_called_once()

    @patch('utils.slack_client.WebClient')
    def test_update_message_success(self, mock_webclient):
        """Test successful message update"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.chat_update.return_value = {
            'ok': True,
            'ts': '1234567890.123456'
        }

        slack_client = SlackAPIClient(bot_token='xoxb-test-token')
        result = slack_client.update_message(
            channel='C1234567890',
            ts='1234567890.123456',
            text='Updated message'
        )

        assert result['ok'] is True
        mock_client.chat_update.assert_called_once()

    @patch('utils.slack_client.WebClient')
    def test_delete_message_success(self, mock_webclient):
        """Test successful message deletion"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.chat_delete.return_value = {
            'ok': True,
            'ts': '1234567890.123456'
        }

        slack_client = SlackAPIClient(bot_token='xoxb-test-token')
        result = slack_client.delete_message(
            channel='C1234567890',
            ts='1234567890.123456'
        )

        assert result['ok'] is True
        mock_client.chat_delete.assert_called_once()

    @patch('utils.slack_client.WebClient')
    def test_get_user_info_success(self, mock_webclient):
        """Test successful user info retrieval"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.users_info.return_value = {
            'user': {
                'id': 'U1234567890',
                'name': 'testuser',
                'real_name': 'Test User'
            }
        }

        slack_client = SlackAPIClient(bot_token='xoxb-test-token')
        result = slack_client.get_user_info('U1234567890')

        assert result['id'] == 'U1234567890'
        assert result['name'] == 'testuser'
        mock_client.users_info.assert_called_once_with(user='U1234567890')

    @patch('utils.slack_client.WebClient')
    def test_get_channel_info_success(self, mock_webclient):
        """Test successful channel info retrieval"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.conversations_info.return_value = {
            'channel': {
                'id': 'C1234567890',
                'name': 'general',
                'is_private': False
            }
        }

        slack_client = SlackAPIClient(bot_token='xoxb-test-token')
        result = slack_client.get_channel_info('C1234567890')

        assert result['id'] == 'C1234567890'
        assert result['name'] == 'general'
        mock_client.conversations_info.assert_called_once_with(channel='C1234567890')

    @patch('utils.slack_client.WebClient')
    def test_list_channels_success(self, mock_webclient):
        """Test successful channel listing"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.conversations_list.return_value = {
            'channels': [
                {'id': 'C1234567890', 'name': 'general'},
                {'id': 'C0987654321', 'name': 'random'}
            ]
        }

        slack_client = SlackAPIClient(bot_token='xoxb-test-token')
        result = slack_client.list_channels()

        assert len(result) == 2
        assert result[0]['name'] == 'general'
        mock_client.conversations_list.assert_called_once()

    @patch('utils.slack_client.WebClient')
    def test_get_team_info_success(self, mock_webclient):
        """Test successful team info retrieval"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.team_info.return_value = {
            'team': {
                'id': 'T1234567890',
                'name': 'Test Team',
                'domain': 'testteam'
            }
        }

        slack_client = SlackAPIClient(bot_token='xoxb-test-token')
        result = slack_client.get_team_info()

        assert result['id'] == 'T1234567890'
        assert result['name'] == 'Test Team'
        mock_client.team_info.assert_called_once()

    @patch('utils.slack_client.WebClient')
    @patch('time.sleep')
    def test_retry_on_rate_limit(self, mock_sleep, mock_webclient):
        """Test retry logic on rate limit errors"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client

        # First call fails with rate limit, second succeeds
        rate_limit_error = SlackApiError(
            message="Rate limited",
            response={'error': 'rate_limited', 'retry_after': 1}
        )
        mock_client.chat_postMessage.side_effect = [
            rate_limit_error,
            {'ok': True, 'ts': '1234567890.123456'}
        ]

        slack_client = SlackAPIClient(bot_token='xoxb-test-token')
        result = slack_client.post_message(channel='C1234567890', text='Test')

        assert result['ok'] is True
        assert mock_client.chat_postMessage.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch('utils.slack_client.WebClient')
    def test_api_error_propagation(self, mock_webclient):
        """Test that non-rate-limit API errors are propagated"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client

        api_error = SlackApiError(
            message="Invalid channel",
            response={'error': 'channel_not_found'}
        )
        mock_client.chat_postMessage.side_effect = api_error

        slack_client = SlackAPIClient(bot_token='xoxb-test-token')

        with pytest.raises(SlackApiError):
            slack_client.post_message(channel='INVALID', text='Test')

    @patch('utils.slack_client.WebClient')
    def test_upload_file_success(self, mock_webclient):
        """Test successful file upload"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.files_upload.return_value = {
            'ok': True,
            'file': {'id': 'F1234567890', 'name': 'test.txt'}
        }

        slack_client = SlackAPIClient(bot_token='xoxb-test-token')
        result = slack_client.upload_file(
            channels='C1234567890',
            content='Test file content',
            filename='test.txt',
            title='Test File'
        )

        assert result['ok'] is True
        assert result['file']['name'] == 'test.txt'
        mock_client.files_upload.assert_called_once()

    @patch('utils.slack_client.WebClient')
    def test_add_reaction_success(self, mock_webclient):
        """Test successful reaction addition"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.reactions_add.return_value = {'ok': True}

        slack_client = SlackAPIClient(bot_token='xoxb-test-token')
        result = slack_client.add_reaction(
            channel='C1234567890',
            timestamp='1234567890.123456',
            name='thumbsup'
        )

        assert result['ok'] is True
        mock_client.reactions_add.assert_called_once()

    @patch('utils.slack_client.WebClient')
    def test_open_modal_success(self, mock_webclient):
        """Test successful modal opening"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.views_open.return_value = {
            'ok': True,
            'view': {'id': 'V1234567890'}
        }

        modal_view = {
            'type': 'modal',
            'title': {'type': 'plain_text', 'text': 'Test Modal'},
            'blocks': []
        }

        slack_client = SlackAPIClient(bot_token='xoxb-test-token')
        result = slack_client.open_modal(
            trigger_id='trigger_123456789',
            view=modal_view
        )

        assert result['ok'] is True
        mock_client.views_open.assert_called_once()


class TestSlackMessageBuilder:
    """Test Slack message builder utilities"""

    def test_create_text_block(self):
        """Test creating text blocks"""
        block = SlackMessageBuilder.create_text_block("Test message")

        assert block['type'] == 'section'
        assert block['text']['type'] == 'mrkdwn'
        assert block['text']['text'] == 'Test message'

    def test_create_text_block_header(self):
        """Test creating header blocks"""
        block = SlackMessageBuilder.create_text_block("Header", block_type='header')

        assert block['type'] == 'header'
        assert block['text']['type'] == 'mrkdwn'  # Implementation uses mrkdwn consistently
        assert block['text']['text'] == 'Header'

    def test_create_button_block(self):
        """Test creating button blocks"""
        block = SlackMessageBuilder.create_button_block(
            text="Click me",
            action_id="button_click",
            value="button_value",
            style="primary"
        )

        assert block['type'] == 'button'
        assert block['text']['text'] == 'Click me'
        assert block['action_id'] == 'button_click'
        assert block['value'] == 'button_value'
        assert block['style'] == 'primary'

    def test_create_button_block_with_url(self):
        """Test creating button blocks with URL"""
        block = SlackMessageBuilder.create_button_block(
            text="Visit Site",
            action_id="visit_site",
            url="https://example.com"
        )

        assert block['type'] == 'button'
        assert block['url'] == 'https://example.com'

    def test_create_section_with_button(self):
        """Test creating section with button accessory"""
        block = SlackMessageBuilder.create_section_with_button(
            text="Message with button",
            button_text="Action",
            action_id="action_click",
            button_value="action_value"
        )

        assert block['type'] == 'section'
        assert block['text']['text'] == 'Message with button'
        assert block['accessory']['type'] == 'button'
        assert block['accessory']['text']['text'] == 'Action'

    def test_create_divider(self):
        """Test creating divider blocks"""
        block = SlackMessageBuilder.create_divider()
        assert block['type'] == 'divider'

    def test_create_jobber_notification_client_created(self):
        """Test creating Jobber client notification"""
        client_data = {
            'id': 'client_123',
            'companyName': 'Test Company',
            'firstName': 'John',
            'lastName': 'Doe',
            'email': 'john@testcompany.com'
        }

        blocks = SlackMessageBuilder.create_jobber_notification('client_created', client_data)

        assert len(blocks) > 0
        # Check that it contains client information
        text_content = str(blocks)
        assert 'Test Company' in text_content
        assert 'john@testcompany.com' in text_content

    def test_create_jobber_notification_job_created(self):
        """Test creating Jobber job notification"""
        job_data = {
            'id': 'job_123',
            'title': 'Test Job',
            'client': {
                'companyName': 'Test Company'
            },
            'jobStatus': 'scheduled'
        }

        blocks = SlackMessageBuilder.create_jobber_notification('job_created', job_data)

        assert len(blocks) > 0
        # Check that it contains job information
        text_content = str(blocks)
        assert 'Test Job' in text_content
        assert 'Test Company' in text_content

    def test_create_jobber_notification_invoice_paid(self):
        """Test creating Jobber invoice paid notification"""
        invoice_data = {
            'id': 'invoice_123',
            'invoiceNumber': 'INV-001',
            'client': {
                'companyName': 'Test Company'
            },
            'total': 150.00,
            'invoiceStatus': 'paid'
        }

        blocks = SlackMessageBuilder.create_jobber_notification('invoice_paid', invoice_data)

        assert len(blocks) > 0
        # Check that it contains invoice information
        text_content = str(blocks)
        assert 'INV-001' in text_content
        assert '$150.00' in text_content

    def test_create_jobber_notification_unknown_type(self):
        """Test creating notification for unknown event type"""
        blocks = SlackMessageBuilder.create_jobber_notification('unknown_event', {})

        assert len(blocks) > 0
        # Should create a generic notification
        text_content = str(blocks)
        assert 'Jobber Event' in text_content


class TestSlackClientUtilities:
    """Test utility functions"""

    def test_get_slack_client_success(self, app_context):
        """Test getting Slack client instance"""
        with app_context.app_context():
            client = get_slack_client()
            assert isinstance(client, SlackAPIClient)

    def test_get_slack_client_no_token(self, app_context):
        """Test getting Slack client without token"""
        with app_context.app_context():
            # Temporarily remove the token from config
            original_token = app_context.config.get('SLACK_BOT_TOKEN')
            app_context.config['SLACK_BOT_TOKEN'] = None

            with pytest.raises(ValueError):
                get_slack_client()

            # Restore the token
            app_context.config['SLACK_BOT_TOKEN'] = original_token

    @patch('utils.slack_client.get_slack_client')
    def test_send_jobber_notification_to_slack(self, mock_get_client):
        """Test sending Jobber notification to Slack"""
        from utils.slack_client import send_jobber_notification_to_slack

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.post_message.return_value = {'ok': True, 'ts': '123'}

        data = {
            'id': 'client_123',
            'companyName': 'Test Company'
        }

        send_jobber_notification_to_slack(
            channel='C1234567890',
            event_type='client_created',
            data=data
        )

        mock_client.post_message.assert_called_once()
        call_args = mock_client.post_message.call_args
        assert call_args[1]['channel'] == 'C1234567890'
        assert len(call_args[1]['blocks']) > 0

    def test_format_error_message(self):
        """Test error message formatting"""
        from utils.slack_client import format_error_message

        blocks = format_error_message("Test error", "Test context")

        assert len(blocks) > 0
        # Check that error information is included
        text_content = str(blocks)
        assert 'Test error' in text_content
        assert 'Test context' in text_content

    def test_format_error_message_no_context(self):
        """Test error message formatting without context"""
        from utils.slack_client import format_error_message

        blocks = format_error_message("Test error")

        assert len(blocks) > 0
        text_content = str(blocks)
        assert 'Test error' in text_content