import logging
from typing import Optional, Dict, Any, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask import current_app
import time
import json

logger = logging.getLogger(__name__)

class SlackAPIClient:
    """Slack API client with error handling, retry logic, and rate limiting"""

    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token or current_app.config.get('SLACK_BOT_TOKEN')
        if not self.bot_token:
            raise ValueError("Slack bot token is required")

        self.client = WebClient(token=self.bot_token)
        self.max_retries = 3
        self.base_delay = 1  # Base delay for exponential backoff

    def _retry_on_rate_limit(self, func, *args, **kwargs):
        """Execute function with rate limit retry logic"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except SlackApiError as e:
                if e.response["error"] == "rate_limited":
                    retry_after = int(e.response.get("retry_after", self.base_delay * (2 ** attempt)))
                    logger.warning(f"Rate limited, retrying after {retry_after} seconds (attempt {attempt + 1})")
                    time.sleep(retry_after)
                    continue
                else:
                    raise
        raise SlackApiError("Max retries exceeded for rate limited request")

    def post_message(self, channel: str, text: str = None, blocks: List[Dict] = None,
                    attachments: List[Dict] = None, thread_ts: str = None,
                    as_user: bool = False, ephemeral_user: str = None) -> Dict[str, Any]:
        """
        Post a message to a Slack channel

        Args:
            channel: Channel ID or name (e.g., #general, C1234567890)
            text: Plain text message (fallback for blocks)
            blocks: Rich formatting blocks
            attachments: Legacy attachments (deprecated, use blocks)
            thread_ts: Timestamp of parent message to reply to
            as_user: Post as the authenticated user instead of bot
            ephemeral_user: User ID to send ephemeral message to
        """
        try:
            kwargs = {
                'channel': channel,
                'text': text,
                'as_user': as_user
            }

            if blocks:
                kwargs['blocks'] = blocks
            if attachments:
                kwargs['attachments'] = attachments
            if thread_ts:
                kwargs['thread_ts'] = thread_ts

            if ephemeral_user:
                kwargs['user'] = ephemeral_user
                response = self._retry_on_rate_limit(self.client.chat_postEphemeral, **kwargs)
            else:
                response = self._retry_on_rate_limit(self.client.chat_postMessage, **kwargs)

            logger.info(f"Message posted to {channel}: {response['ts']}")
            return response

        except SlackApiError as e:
            logger.error(f"Error posting message to {channel}: {e.response['error']}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error posting message to {channel}: {str(e)}")
            raise

    def send_dm(self, user_id: str, text: str = None, blocks: List[Dict] = None,
               attachments: List[Dict] = None) -> Dict[str, Any]:
        """
        Send a direct message to a user

        Args:
            user_id: Slack user ID
            text: Plain text message
            blocks: Rich formatting blocks
            attachments: Legacy attachments
        """
        try:
            # Open DM channel with user
            dm_response = self._retry_on_rate_limit(
                self.client.conversations_open,
                users=[user_id]
            )

            channel_id = dm_response['channel']['id']

            # Send message to DM channel
            return self.post_message(
                channel=channel_id,
                text=text,
                blocks=blocks,
                attachments=attachments
            )

        except SlackApiError as e:
            logger.error(f"Error sending DM to user {user_id}: {e.response['error']}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending DM to user {user_id}: {str(e)}")
            raise

    def update_message(self, channel: str, ts: str, text: str = None,
                      blocks: List[Dict] = None, attachments: List[Dict] = None) -> Dict[str, Any]:
        """Update an existing message"""
        try:
            kwargs = {
                'channel': channel,
                'ts': ts,
                'text': text
            }

            if blocks:
                kwargs['blocks'] = blocks
            if attachments:
                kwargs['attachments'] = attachments

            response = self._retry_on_rate_limit(self.client.chat_update, **kwargs)
            logger.info(f"Message updated in {channel}: {ts}")
            return response

        except SlackApiError as e:
            logger.error(f"Error updating message {ts} in {channel}: {e.response['error']}")
            raise

    def delete_message(self, channel: str, ts: str) -> Dict[str, Any]:
        """Delete a message"""
        try:
            response = self._retry_on_rate_limit(
                self.client.chat_delete,
                channel=channel,
                ts=ts
            )
            logger.info(f"Message deleted from {channel}: {ts}")
            return response

        except SlackApiError as e:
            logger.error(f"Error deleting message {ts} from {channel}: {e.response['error']}")
            raise

    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information"""
        try:
            response = self._retry_on_rate_limit(
                self.client.users_info,
                user=user_id
            )
            return response['user']

        except SlackApiError as e:
            logger.error(f"Error getting user info for {user_id}: {e.response['error']}")
            raise

    def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get channel information"""
        try:
            response = self._retry_on_rate_limit(
                self.client.conversations_info,
                channel=channel_id
            )
            return response['channel']

        except SlackApiError as e:
            logger.error(f"Error getting channel info for {channel_id}: {e.response['error']}")
            raise

    def list_channels(self, types: str = "public_channel,private_channel") -> List[Dict[str, Any]]:
        """List all channels in the workspace"""
        try:
            response = self._retry_on_rate_limit(
                self.client.conversations_list,
                types=types,
                limit=1000
            )
            return response['channels']

        except SlackApiError as e:
            logger.error(f"Error listing channels: {e.response['error']}")
            raise

    def get_team_info(self) -> Dict[str, Any]:
        """Get team/workspace information"""
        try:
            response = self._retry_on_rate_limit(self.client.team_info)
            return response['team']

        except SlackApiError as e:
            logger.error(f"Error getting team info: {e.response['error']}")
            raise

    def upload_file(self, channels: str, file_path: str = None, content: str = None,
                   filename: str = None, title: str = None, initial_comment: str = None) -> Dict[str, Any]:
        """Upload a file to Slack"""
        try:
            kwargs = {
                'channels': channels,
                'filename': filename,
                'title': title,
                'initial_comment': initial_comment
            }

            if file_path:
                with open(file_path, 'rb') as file:
                    kwargs['file'] = file
                    response = self._retry_on_rate_limit(self.client.files_upload, **kwargs)
            elif content:
                kwargs['content'] = content
                response = self._retry_on_rate_limit(self.client.files_upload, **kwargs)
            else:
                raise ValueError("Either file_path or content must be provided")

            logger.info(f"File uploaded to {channels}: {response['file']['id']}")
            return response

        except SlackApiError as e:
            logger.error(f"Error uploading file to {channels}: {e.response['error']}")
            raise

    def add_reaction(self, channel: str, timestamp: str, name: str) -> Dict[str, Any]:
        """Add a reaction to a message"""
        try:
            response = self._retry_on_rate_limit(
                self.client.reactions_add,
                channel=channel,
                timestamp=timestamp,
                name=name
            )
            return response

        except SlackApiError as e:
            logger.error(f"Error adding reaction {name} to message {timestamp}: {e.response['error']}")
            raise

    def open_modal(self, trigger_id: str, view: Dict[str, Any]) -> Dict[str, Any]:
        """Open a modal dialog"""
        try:
            response = self._retry_on_rate_limit(
                self.client.views_open,
                trigger_id=trigger_id,
                view=view
            )
            return response

        except SlackApiError as e:
            logger.error(f"Error opening modal: {e.response['error']}")
            raise


# Message builder utilities
class SlackMessageBuilder:
    """Utility class for building rich Slack messages with Block Kit"""

    @staticmethod
    def create_text_block(text: str, block_type: str = "section") -> Dict[str, Any]:
        """Create a simple text block"""
        return {
            "type": block_type,
            "text": {
                "type": "mrkdwn",
                "text": text
            }
        }

    @staticmethod
    def create_button_block(text: str, action_id: str, value: str = None,
                           style: str = None, url: str = None) -> Dict[str, Any]:
        """Create a button element"""
        button = {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": text
            },
            "action_id": action_id
        }

        if value:
            button["value"] = value
        if style:
            button["style"] = style  # primary, danger
        if url:
            button["url"] = url

        return button

    @staticmethod
    def create_section_with_button(text: str, button_text: str,
                                  action_id: str, button_value: str = None) -> Dict[str, Any]:
        """Create a section with an accessory button"""
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text
            },
            "accessory": SlackMessageBuilder.create_button_block(
                button_text, action_id, button_value
            )
        }

    @staticmethod
    def create_divider() -> Dict[str, Any]:
        """Create a divider block"""
        return {"type": "divider"}

    @staticmethod
    def create_jobber_notification(event_type: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create formatted notification blocks for Jobber events"""
        blocks = []

        if event_type == "client_created":
            blocks.extend([
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"👤 *New Client Created*\n*{data.get('companyName', data.get('firstName', '') + ' ' + data.get('lastName', '')).strip()}*"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Email:*\n{data.get('email', 'Not provided')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*ID:*\n{data.get('id', 'Unknown')}"
                        }
                    ]
                }
            ])
        elif event_type == "job_created":
            # Extract client name from nested client object
            client_name = "Unknown"
            if 'client' in data and isinstance(data['client'], dict):
                client_name = data['client'].get('companyName', 'Unknown')

            blocks.extend([
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🆕 *New Job Created*\n*{data.get('title', 'Untitled Job')}*"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Client:*\n{client_name}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Status:*\n{data.get('jobStatus', 'Unknown')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Total:*\n${data.get('total', 0.00):.2f}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Start Date:*\n{data.get('start_date', 'TBD')}"
                        }
                    ]
                }
            ])
        elif event_type == "invoice_paid":
            # Extract client name from nested client object
            client_name = "Unknown"
            if 'client' in data and isinstance(data['client'], dict):
                client_name = data['client'].get('companyName', 'Unknown')

            blocks.extend([
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"💰 *Invoice Paid*\n*Invoice #{data.get('invoiceNumber', 'Unknown')}*"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Client:*\n{client_name}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Amount:*\n${data.get('total', 0.00):.2f}"
                        }
                    ]
                }
            ])
        else:
            # Handle unknown event types with a generic message
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📢 *Jobber Event*\n{event_type.replace('_', ' ').title()}"
                }
            })

        return blocks


# Utility functions for common operations
def get_slack_client() -> SlackAPIClient:
    """Get configured Slack API client"""
    return SlackAPIClient()

def send_jobber_notification_to_slack(channel: str, event_type: str, data: Dict[str, Any]):
    """Send a Jobber event notification to a Slack channel"""
    try:
        client = get_slack_client()
        blocks = SlackMessageBuilder.create_jobber_notification(event_type, data)

        client.post_message(
            channel=channel,
            text=f"Jobber {event_type.replace('_', ' ').title()}",  # Fallback text
            blocks=blocks
        )

    except Exception as e:
        logger.error(f"Failed to send Jobber notification to Slack: {str(e)}")

def format_error_message(error: str, context: str = None) -> List[Dict[str, Any]]:
    """Format an error message for Slack"""
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"❌ *Error*\n{error}"
            }
        }
    ]

    if context:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Context: {context}"
                }
            ]
        })

    return blocks