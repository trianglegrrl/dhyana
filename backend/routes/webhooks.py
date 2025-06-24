import hmac
import hashlib
import json
from flask import Blueprint, request, jsonify, current_app
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier
from utils.jobber_client import JobberAPIClient, transform_jobber_client_to_model, transform_jobber_job_to_model, transform_jobber_invoice_to_model
from utils.slack_client import SlackAPIClient, SlackMessageBuilder, get_slack_client, send_jobber_notification_to_slack, format_error_message

webhooks_bp = Blueprint('webhooks', __name__)

@webhooks_bp.route('/slack/events', methods=['POST'])
def slack_events():
    """Handle Slack Events API webhooks"""
    try:
        # Verify Slack signature
        signature_verifier = SignatureVerifier(current_app.config['SLACK_SIGNING_SECRET'])

        if not signature_verifier.is_valid_request(request.get_data(), request.headers):
            return jsonify({'error': 'Invalid request signature'}), 401

        # Parse JSON with error handling
        try:
            data = request.get_json()
            if data is None:
                current_app.logger.warning("No JSON data received in Slack webhook")
                return jsonify({'status': 'ok'})
        except Exception as e:
            current_app.logger.error(f"Failed to parse JSON in Slack webhook: {e}")
            return jsonify({'status': 'ok'})

        # Handle URL verification challenge
        if data.get('type') == 'url_verification':
            return jsonify({'challenge': data.get('challenge')})

        # Handle events
        if data.get('type') == 'event_callback':
            event = data.get('event', {})
            event_type = event.get('type')

            try:
                if event_type == 'message':
                    handle_slack_message(event, data.get('team_id'))
                elif event_type == 'app_mention':
                    handle_slack_mention(event, data.get('team_id'))
                elif event_type == 'channel_created':
                    handle_slack_channel_created(event, data.get('team_id'))
                elif event_type == 'team_join':
                    handle_slack_user_joined(event, data.get('team_id'))
            except Exception as e:
                current_app.logger.error(f"Error handling Slack event {event_type}: {e}")

        return jsonify({'status': 'ok'})
    except Exception as e:
        current_app.logger.error(f"Unexpected error in Slack events webhook: {e}")
        return jsonify({'status': 'ok'})

@webhooks_bp.route('/slack/interactions', methods=['POST'])
def slack_interactions():
    """Handle Slack interactive components (buttons, modals, etc.)"""
    # Verify Slack signature
    signature_verifier = SignatureVerifier(current_app.config['SLACK_SIGNING_SECRET'])

    if not signature_verifier.is_valid_request(request.get_data(), request.headers):
        return jsonify({'error': 'Invalid request signature'}), 401

    payload = json.loads(request.form.get('payload'))

    interaction_type = payload.get('type')

    if interaction_type == 'block_actions':
        handle_slack_block_actions(payload)
    elif interaction_type == 'view_submission':
        handle_slack_modal_submission(payload)
    elif interaction_type == 'shortcut':
        handle_slack_shortcut(payload)

    return jsonify({'status': 'ok'})

@webhooks_bp.route('/slack/commands', methods=['POST'])
def slack_commands():
    """Handle Slack slash commands"""
    # Verify Slack signature
    signature_verifier = SignatureVerifier(current_app.config['SLACK_SIGNING_SECRET'])

    if not signature_verifier.is_valid_request(request.get_data(), request.headers):
        return jsonify({'error': 'Invalid request signature'}), 401

    command = request.form.get('command')
    text = request.form.get('text')
    user_id = request.form.get('user_id')
    channel_id = request.form.get('channel_id')
    team_id = request.form.get('team_id')

    # Handle different slash commands
    if command == '/jobber':
        return handle_jobber_command(text, user_id, channel_id, team_id)

    return jsonify({'text': 'Unknown command'})

def verify_jobber_signature(request) -> bool:
    """Verify Jobber webhook signature using HMAC-SHA256"""
    webhook_secret = current_app.config.get('JOBBER_WEBHOOK_SECRET')
    if not webhook_secret:
        current_app.logger.warning("JOBBER_WEBHOOK_SECRET not configured - skipping signature verification")
        return True  # Allow webhooks if secret not configured for development

    # Get signature from header (common formats: X-Jobber-Signature, X-Hub-Signature-256)
    signature_header = request.headers.get('X-Jobber-Signature') or request.headers.get('X-Hub-Signature-256')
    if not signature_header:
        return False

    # Get raw request body
    raw_body = request.get_data()

    # Calculate expected signature
    expected_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    # Handle different signature formats
    if signature_header.startswith('sha256='):
        received_signature = signature_header[7:]  # Remove 'sha256=' prefix
    else:
        received_signature = signature_header

    # Use constant-time comparison
    return hmac.compare_digest(expected_signature, received_signature)

@webhooks_bp.route('/jobber/webhooks', methods=['POST'])
def jobber_webhooks():
    """Handle Jobber webhooks"""
    # Verify Jobber webhook signature
    if not verify_jobber_signature(request):
        current_app.logger.warning("Invalid Jobber webhook signature")
        return jsonify({'error': 'Invalid signature'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    # Jobber webhook format: topic field indicates event type
    topic = data.get('topic')

    try:
        if topic == 'CLIENT_CREATE':
            handle_jobber_client_created(data)
        elif topic == 'CLIENT_UPDATE':
            handle_jobber_client_updated(data)
        elif topic == 'JOB_CREATE':
            handle_jobber_job_created(data)
        elif topic == 'JOB_UPDATE':
            handle_jobber_job_updated(data)
        elif topic == 'JOB_COMPLETE':
            handle_jobber_job_updated(data)  # Handle completion as update
        elif topic == 'INVOICE_CREATE':
            handle_jobber_invoice_created(data)
        elif topic == 'INVOICE_UPDATE':
            handle_jobber_invoice_updated(data)
        elif topic == 'QUOTE_CREATE':
            # Handle quote creation if needed
            current_app.logger.info(f"Quote created: {data}")
        elif topic == 'QUOTE_APPROVAL':
            # Handle quote approval if needed
            current_app.logger.info(f"Quote approved: {data}")
        else:
            current_app.logger.warning(f"Unknown webhook topic: {topic}")

    except Exception as e:
        current_app.logger.error(f"Error processing webhook {topic}: {e}")
        # Return 200 to prevent retries for data issues
        return jsonify({'status': 'error', 'message': str(e)}), 200

    return jsonify({'status': 'received'})

# Slack event handlers
def handle_slack_message(event, team_id):
    """Handle new Slack messages"""
    from models.slack_models import SlackMessage, SlackChannel, SlackUser
    from app import db

    # Don't process bot messages or our own messages
    if event.get('bot_id') or event.get('subtype') == 'bot_message':
        return

    try:
        # Ensure channel exists
        channel_id = event.get('channel')
        channel = SlackChannel.query.filter_by(channel_id=channel_id, team_id=team_id).first()
        if not channel:
            # Fetch channel info and create it
            try:
                slack_client = get_slack_client()
                channel_info = slack_client.get_channel_info(channel_id)
                channel = SlackChannel(
                    channel_id=channel_id,
                    team_id=team_id,
                    name=channel_info.get('name'),
                    is_private=channel_info.get('is_private', False),
                    is_archived=channel_info.get('is_archived', False),
                    topic=channel_info.get('topic', {}).get('value'),
                    purpose=channel_info.get('purpose', {}).get('value')
                )
                channel.save()
            except Exception as e:
                current_app.logger.warning(f"Could not fetch channel info for {channel_id}: {e}")

        # Ensure user exists
        user_id = event.get('user')
        if user_id:
            user = SlackUser.query.filter_by(user_id=user_id, team_id=team_id).first()
            if not user:
                try:
                    slack_client = get_slack_client()
                    user_info = slack_client.get_user_info(user_id)
                    user = SlackUser(
                        user_id=user_id,
                        team_id=team_id,
                        username=user_info.get('name'),
                        real_name=user_info.get('real_name'),
                        email=user_info.get('profile', {}).get('email'),
                        is_bot=user_info.get('is_bot', False),
                        is_admin=user_info.get('is_admin', False)
                    )
                    user.save()
                except Exception as e:
                    current_app.logger.warning(f"Could not fetch user info for {user_id}: {e}")

        # Store message in database
        message = SlackMessage(
            message_ts=event.get('ts'),
            channel_id=channel_id,
            user_id=user_id,
            text=event.get('text'),
            message_type=event.get('subtype', 'message'),
            thread_ts=event.get('thread_ts')
        )

        message.save()
        current_app.logger.info(f"Saved message {event.get('ts')} from {user_id} in {channel_id}")

    except Exception as e:
        current_app.logger.error(f"Error handling message event: {e}")

def handle_slack_mention(event, team_id):
    """Handle app mentions"""
    from models.slack_models import SlackChannel

    try:
        text = event.get('text', '').lower()
        channel_id = event.get('channel')
        user_id = event.get('user')
        ts = event.get('ts')

        slack_client = get_slack_client()

        # Simple mention responses
        if 'help' in text:
            blocks = [
                SlackMessageBuilder.create_text_block(
                    "👋 *I can help you with:*\n"
                    "• `/jobber clients` - View recent clients\n"
                    "• `/jobber jobs` - View recent jobs\n"
                    "• `/jobber invoices` - View recent invoices\n"
                    "• Just mention me for general help!"
                ),
                SlackMessageBuilder.create_divider(),
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "I also send notifications when:\n• New jobs are created\n• Jobs are completed\n• Invoices are paid"
                    }
                }
            ]

            slack_client.post_message(
                channel=channel_id,
                text="Here's how I can help you with Jobber!",
                blocks=blocks,
                thread_ts=ts
            )

        elif 'status' in text or 'stats' in text:
            # Get quick stats
            from models.jobber_models import JobberJob, JobberInvoice, JobberClient

            active_jobs = JobberJob.query.filter_by(status='active').count()
            pending_invoices = JobberInvoice.query.filter_by(status='pending').count()
            total_clients = JobberClient.query.filter_by(is_active=True).count()

            blocks = [
                SlackMessageBuilder.create_text_block(
                    f"📊 *Current Jobber Status*\n"
                    f"• Active Jobs: {active_jobs}\n"
                    f"• Pending Invoices: {pending_invoices}\n"
                    f"• Total Clients: {total_clients}"
                )
            ]

            slack_client.post_message(
                channel=channel_id,
                text="Here's your current Jobber status",
                blocks=blocks,
                thread_ts=ts
            )

        else:
            # Default response
            blocks = [
                SlackMessageBuilder.create_text_block(
                    f"👋 Hi <@{user_id}>, I'm your Jobber assistant!\n"
                    "Type `@jobber-bot help` for available commands."
                )
            ]

            # Add reaction to the original message
            slack_client.add_reaction(channel_id, ts, 'wave')

            slack_client.post_message(
                channel=channel_id,
                text="Hi! I'm your Jobber assistant.",
                blocks=blocks,
                thread_ts=ts
            )

    except Exception as e:
        current_app.logger.error(f"Error handling mention: {e}")

def handle_slack_channel_created(event, team_id):
    """Handle new channel creation"""
    from models.slack_models import SlackChannel

    try:
        channel_data = event.get('channel', {})
        channel = SlackChannel(
            channel_id=channel_data.get('id'),
            team_id=team_id,
            name=channel_data.get('name'),
            is_private=channel_data.get('is_private', False),
            is_archived=channel_data.get('is_archived', False),
            topic=channel_data.get('topic', {}).get('value'),
            purpose=channel_data.get('purpose', {}).get('value')
        )

        channel.save()
        current_app.logger.info(f"Created channel: {channel.name} ({channel.channel_id})")

    except Exception as e:
        current_app.logger.error(f"Error saving channel: {e}")

def handle_slack_user_joined(event, team_id):
    """Handle new user joining team"""
    from models.slack_models import SlackUser

    try:
        user_data = event.get('user', {})
        user = SlackUser(
            user_id=user_data.get('id'),
            team_id=team_id,
            username=user_data.get('name'),
            real_name=user_data.get('real_name'),
            email=user_data.get('profile', {}).get('email'),
            is_bot=user_data.get('is_bot', False),
            is_admin=user_data.get('is_admin', False)
        )

        user.save()
        current_app.logger.info(f"User joined: {user.real_name} ({user.user_id})")

        # Send welcome DM to new user
        try:
            slack_client = get_slack_client()
            welcome_blocks = [
                SlackMessageBuilder.create_text_block(
                    f"👋 Welcome to the team, {user.real_name or user.username}!"
                ),
                SlackMessageBuilder.create_text_block(
                    "I'm your Jobber assistant. I can help you with:\n"
                    "• Viewing clients, jobs, and invoices\n"
                    "• Getting notifications about new jobs and payments\n"
                    "• Quick status updates"
                ),
                SlackMessageBuilder.create_text_block(
                    "Try mentioning me in any channel or use `/jobber help` to get started!"
                )
            ]

            slack_client.send_dm(
                user_id=user.user_id,
                text="Welcome to the team! I'm your Jobber assistant.",
                blocks=welcome_blocks
            )

        except Exception as e:
            current_app.logger.warning(f"Could not send welcome DM to {user.user_id}: {e}")

    except Exception as e:
        current_app.logger.error(f"Error saving user: {e}")

def handle_slack_channel_rename(event, team_id):
    """Handle channel rename events"""
    from models.slack_models import SlackChannel

    try:
        channel_data = event.get('channel', {})
        channel = SlackChannel.query.filter_by(
            channel_id=channel_data.get('id'),
            team_id=team_id
        ).first()

        if channel:
            channel.name = channel_data.get('name')
            channel.save()
            current_app.logger.info(f"Channel renamed: {channel.name} ({channel.channel_id})")

    except Exception as e:
        current_app.logger.error(f"Error handling channel rename: {e}")

def handle_slack_channel_archive(event, team_id):
    """Handle channel archive events"""
    from models.slack_models import SlackChannel

    try:
        channel_id = event.get('channel')
        channel = SlackChannel.query.filter_by(
            channel_id=channel_id,
            team_id=team_id
        ).first()

        if channel:
            channel.is_archived = True
            channel.save()
            current_app.logger.info(f"Channel archived: {channel.name} ({channel.channel_id})")

    except Exception as e:
        current_app.logger.error(f"Error handling channel archive: {e}")

def handle_slack_user_change(event, team_id):
    """Handle user profile change events"""
    from models.slack_models import SlackUser

    try:
        user_data = event.get('user', {})
        user = SlackUser.query.filter_by(
            user_id=user_data.get('id'),
            team_id=team_id
        ).first()

        if user:
            user.username = user_data.get('name')
            user.real_name = user_data.get('real_name')
            user.email = user_data.get('profile', {}).get('email')
            user.is_admin = user_data.get('is_admin', False)
            user.save()
            current_app.logger.info(f"User updated: {user.real_name} ({user.user_id})")

    except Exception as e:
        current_app.logger.error(f"Error handling user change: {e}")

def handle_slack_block_actions(payload):
    """Handle block actions from interactive components"""
    try:
        actions = payload.get('actions', [])
        user_id = payload.get('user', {}).get('id')
        channel_id = payload.get('channel', {}).get('id')
        response_url = payload.get('response_url')

        for action in actions:
            action_id = action.get('action_id')
            value = action.get('value')

            if action_id.startswith('jobber_'):
                handle_jobber_action(action_id, value, user_id, channel_id, response_url)
            elif action_id.startswith('slack_'):
                handle_slack_action(action_id, value, user_id, channel_id, response_url)

    except Exception as e:
        current_app.logger.error(f"Error handling block actions: {e}")

def handle_slack_modal_submission(payload):
    """Handle modal form submissions"""
    try:
        view = payload.get('view', {})
        view_id = view.get('callback_id')
        user_id = payload.get('user', {}).get('id')
        values = view.get('state', {}).get('values', {})

        if view_id == 'jobber_job_form':
            handle_jobber_job_form_submission(values, user_id)
        elif view_id == 'jobber_client_form':
            handle_jobber_client_form_submission(values, user_id)

    except Exception as e:
        current_app.logger.error(f"Error handling modal submission: {e}")

def handle_slack_shortcut(payload):
    """Handle global shortcuts"""
    try:
        callback_id = payload.get('callback_id')
        trigger_id = payload.get('trigger_id')
        user_id = payload.get('user', {}).get('id')

        slack_client = get_slack_client()

        if callback_id == 'jobber_dashboard':
            # Show Jobber dashboard modal
            modal_view = create_jobber_dashboard_modal()
            slack_client.open_modal(trigger_id, modal_view)

        elif callback_id == 'jobber_quick_stats':
            # Show quick stats modal
            modal_view = create_jobber_stats_modal()
            slack_client.open_modal(trigger_id, modal_view)

    except Exception as e:
        current_app.logger.error(f"Error handling shortcut: {e}")

def handle_jobber_action(action_id, value, user_id, channel_id, response_url):
    """Handle Jobber-related button actions"""
    try:
        if action_id == 'jobber_view_job':
            # Fetch and display job details
            from models.jobber_models import JobberJob
            job = JobberJob.query.filter_by(jobber_job_id=value).first()
            if job:
                blocks = create_job_detail_blocks(job)
                post_response_message(response_url, blocks, f"Job Details: {job.title}")

        elif action_id == 'jobber_view_client':
            # Fetch and display client details
            from models.jobber_models import JobberClient
            client = JobberClient.query.filter_by(jobber_client_id=value).first()
            if client:
                blocks = create_client_detail_blocks(client)
                name = client.company_name or f"{client.first_name} {client.last_name}"
                post_response_message(response_url, blocks, f"Client Details: {name}")

    except Exception as e:
        current_app.logger.error(f"Error handling Jobber action {action_id}: {e}")

def handle_slack_action(action_id, value, user_id, channel_id, response_url):
    """Handle Slack-specific actions"""
    try:
        if action_id == 'slack_help':
            blocks = create_help_blocks()
            post_response_message(response_url, blocks, "Help & Commands")

    except Exception as e:
        current_app.logger.error(f"Error handling Slack action {action_id}: {e}")

def post_response_message(response_url, blocks, text):
    """Post a response message using response URL"""
    import requests

    try:
        response = requests.post(response_url, json={
            'text': text,
            'blocks': blocks,
            'response_type': 'ephemeral'  # Only visible to the user
        })
        response.raise_for_status()

    except Exception as e:
        current_app.logger.error(f"Error posting response message: {e}")

def create_job_detail_blocks(job):
    """Create blocks for job detail display"""
    return [
        SlackMessageBuilder.create_text_block(
            f"🔧 *Job Details*\n*{job.title}*"
        ),
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Status:*\n{job.status.title()}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Total:*\n${job.total_amount:.2f}" if job.total_amount else "*Total:*\nNot set"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Start Date:*\n{job.start_date.strftime('%Y-%m-%d') if job.start_date else 'TBD'}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*End Date:*\n{job.end_date.strftime('%Y-%m-%d') if job.end_date else 'TBD'}"
                }
            ]
        }
    ]

def create_client_detail_blocks(client):
    """Create blocks for client detail display"""
    name = client.company_name or f"{client.first_name} {client.last_name}"
    return [
        SlackMessageBuilder.create_text_block(
            f"👤 *Client Details*\n*{name}*"
        ),
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Email:*\n{client.email or 'Not provided'}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Phone:*\n{client.phone or 'Not provided'}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Status:*\n{'Active' if client.is_active else 'Inactive'}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Created:*\n{client.created_at.strftime('%Y-%m-%d') if client.created_at else 'Unknown'}"
                }
            ]
        }
    ]

def create_help_blocks():
    """Create help blocks"""
    return [
        SlackMessageBuilder.create_text_block(
            "🤖 *Jobber Bot Help*\n"
            "Here's what I can do for you:"
        ),
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*Slash Commands:*\n"
                           "• `/jobber clients` - View recent clients\n"
                           "• `/jobber jobs` - View recent jobs\n"
                           "• `/jobber invoices` - View recent invoices"
                },
                {
                    "type": "mrkdwn",
                    "text": "*Mentions:*\n"
                           "• `@jobber-bot help` - Show this help\n"
                           "• `@jobber-bot status` - Show quick stats\n"
                           "• Just mention me for general help"
                }
            ]
        },
        SlackMessageBuilder.create_divider(),
        SlackMessageBuilder.create_text_block(
            "🔔 *Automatic Notifications:*\n"
            "I'll automatically notify you when:\n"
            "• New jobs are created\n"
            "• Jobs are completed\n"
            "• Invoices are paid"
        )
    ]

def create_jobber_dashboard_modal():
    """Create the Jobber dashboard modal"""
    from models.jobber_models import JobberJob, JobberInvoice, JobberClient

    active_jobs = JobberJob.query.filter_by(status='active').count()
    pending_invoices = JobberInvoice.query.filter_by(status='pending').count()
    total_clients = JobberClient.query.filter_by(is_active=True).count()

    return {
        "type": "modal",
        "callback_id": "jobber_dashboard",
        "title": {
            "type": "plain_text",
            "text": "Jobber Dashboard"
        },
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📊 *Dashboard Overview*\n\n"
                           f"• *Active Jobs:* {active_jobs}\n"
                           f"• *Pending Invoices:* {pending_invoices}\n"
                           f"• *Total Clients:* {total_clients}"
                }
            },
            SlackMessageBuilder.create_divider(),
            {
                "type": "actions",
                "elements": [
                    SlackMessageBuilder.create_button_block(
                        "View Recent Jobs", "jobber_view_jobs", "recent_jobs"
                    ),
                    SlackMessageBuilder.create_button_block(
                        "View Recent Clients", "jobber_view_clients", "recent_clients"
                    )
                ]
            }
        ]
    }

def create_jobber_stats_modal():
    """Create the Jobber stats modal"""
    from models.jobber_models import JobberJob, JobberInvoice
    from sqlalchemy import func

    # Get some basic stats
    total_jobs = JobberJob.query.count()
    completed_jobs = JobberJob.query.filter_by(status='completed').count()
    total_invoices = JobberInvoice.query.count()
    paid_invoices = JobberInvoice.query.filter_by(status='paid').count()

    return {
        "type": "modal",
        "callback_id": "jobber_stats",
        "title": {
            "type": "plain_text",
            "text": "Jobber Statistics"
        },
        "blocks": [
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Jobs:*\n{total_jobs}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Completed Jobs:*\n{completed_jobs}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Invoices:*\n{total_invoices}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Paid Invoices:*\n{paid_invoices}"
                    }
                ]
            }
        ]
    }

def handle_jobber_command(text, user_id, channel_id, team_id):
    """Handle /jobber slash command"""
    # Basic command parsing
    if not text:
        blocks = [
            SlackMessageBuilder.create_text_block(
                "🤖 *Jobber Commands*\n"
                "Here are the available commands:"
            ),
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Data Commands:*\n"
                               "• `/jobber clients` - View recent clients\n"
                               "• `/jobber jobs` - View recent jobs\n"
                               "• `/jobber invoices` - View recent invoices"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Quick Commands:*\n"
                               "• `/jobber help` - Show this help\n"
                               "• `/jobber status` - Show quick stats\n"
                               "• `/jobber dashboard` - Open dashboard"
                    }
                ]
            }
        ]

        return jsonify({
            'response_type': 'ephemeral',
            'text': 'Jobber Commands',
            'blocks': blocks
        })

    parts = text.strip().split()
    command = parts[0] if parts else ''

    if command == 'clients':
        return handle_jobber_clients_command(parts[1:], user_id, channel_id)
    elif command == 'jobs':
        return handle_jobber_jobs_command(parts[1:], user_id, channel_id)
    elif command == 'invoices':
        return handle_jobber_invoices_command(parts[1:], user_id, channel_id)
    elif command == 'help':
        return handle_jobber_help_command(user_id, channel_id)
    elif command == 'status':
        return handle_jobber_status_command(user_id, channel_id)
    elif command == 'dashboard':
        return handle_jobber_dashboard_command(user_id, channel_id)

    return jsonify({
        'response_type': 'ephemeral',
        'text': f'Unknown command: {command}\nType `/jobber help` for available commands.'
    })

def handle_jobber_help_command(user_id, channel_id):
    """Handle /jobber help command"""
    blocks = create_help_blocks()
    return jsonify({
        'response_type': 'ephemeral',
        'text': 'Jobber Bot Help',
        'blocks': blocks
    })

def handle_jobber_status_command(user_id, channel_id):
    """Handle /jobber status command"""
    from models.jobber_models import JobberJob, JobberInvoice, JobberClient

    active_jobs = JobberJob.query.filter_by(status='active').count()
    pending_invoices = JobberInvoice.query.filter_by(status='pending').count()
    total_clients = JobberClient.query.filter_by(is_active=True).count()

    blocks = [
        SlackMessageBuilder.create_text_block(
            f"📊 *Current Jobber Status*\n"
            f"• Active Jobs: {active_jobs}\n"
            f"• Pending Invoices: {pending_invoices}\n"
            f"• Total Clients: {total_clients}"
        )
    ]

    return jsonify({
        'response_type': 'ephemeral',
        'text': 'Jobber Status',
        'blocks': blocks
    })

def handle_jobber_dashboard_command(user_id, channel_id):
    """Handle /jobber dashboard command"""
    # Return a response that will trigger a modal
    blocks = [
        SlackMessageBuilder.create_section_with_button(
            "Click below to open your Jobber dashboard:",
            "Open Dashboard",
            "jobber_open_dashboard",
            "dashboard"
        )
    ]

    return jsonify({
        'response_type': 'ephemeral',
        'text': 'Jobber Dashboard',
        'blocks': blocks
    })

def handle_jobber_clients_command(args, user_id, channel_id):
    """Handle jobber clients command"""
    from models.jobber_models import JobberClient

    clients = JobberClient.query.filter_by(is_active=True).limit(10).all()

    if not clients:
        blocks = [
            SlackMessageBuilder.create_text_block(
                "📋 *No active clients found*\n"
                "Your client list is empty or all clients are inactive."
            )
        ]
        return jsonify({
            'response_type': 'ephemeral',
            'text': 'No active clients found',
            'blocks': blocks
        })

    # Create blocks for client list
    blocks = [
        SlackMessageBuilder.create_text_block(
            f"👥 *Recent Active Clients ({len(clients)} shown)*"
        )
    ]

    for client in clients:
        name = client.company_name or f"{client.first_name} {client.last_name}"
        email = client.email or "No email"
        phone = client.phone or "No phone"

        client_block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{name}*\n📧 {email}\n📞 {phone}"
            },
            "accessory": SlackMessageBuilder.create_button_block(
                "View Details",
                "jobber_view_client",
                client.jobber_client_id
            )
        }
        blocks.append(client_block)

    if len(clients) == 10:
        blocks.append(SlackMessageBuilder.create_text_block(
            "_Showing first 10 clients. Use Jobber dashboard for complete list._"
        ))

    return jsonify({
        'response_type': 'ephemeral',
        'text': 'Recent Active Clients',
        'blocks': blocks
    })

def handle_jobber_jobs_command(args, user_id, channel_id):
    """Handle jobber jobs command"""
    from models.jobber_models import JobberJob

    jobs = JobberJob.query.order_by(JobberJob.created_at.desc()).limit(10).all()

    if not jobs:
        blocks = [
            SlackMessageBuilder.create_text_block(
                "🔧 *No jobs found*\n"
                "No jobs have been synced from Jobber yet."
            )
        ]
        return jsonify({
            'response_type': 'ephemeral',
            'text': 'No jobs found',
            'blocks': blocks
        })

    # Create blocks for job list
    blocks = [
        SlackMessageBuilder.create_text_block(
            f"🔧 *Recent Jobs ({len(jobs)} shown)*"
        )
    ]

    for job in jobs:
        status_emoji = {
            'active': '🟢',
            'completed': '✅',
            'cancelled': '❌',
            'pending': '🟡'
        }.get(job.status.lower(), '⚪')

        total = f"${job.total_amount:.2f}" if job.total_amount else "Not set"

        job_block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{job.title}*\n{status_emoji} {job.status.title()} • {total}"
            },
            "accessory": SlackMessageBuilder.create_button_block(
                "View Details",
                "jobber_view_job",
                job.jobber_job_id
            )
        }
        blocks.append(job_block)

    if len(jobs) == 10:
        blocks.append(SlackMessageBuilder.create_text_block(
            "_Showing 10 most recent jobs. Use Jobber dashboard for complete list._"
        ))

    return jsonify({
        'response_type': 'ephemeral',
        'text': 'Recent Jobs',
        'blocks': blocks
    })

def handle_jobber_invoices_command(args, user_id, channel_id):
    """Handle jobber invoices command"""
    from models.jobber_models import JobberInvoice

    invoices = JobberInvoice.query.order_by(JobberInvoice.created_at.desc()).limit(10).all()

    if not invoices:
        blocks = [
            SlackMessageBuilder.create_text_block(
                "💰 *No invoices found*\n"
                "No invoices have been synced from Jobber yet."
            )
        ]
        return jsonify({
            'response_type': 'ephemeral',
            'text': 'No invoices found',
            'blocks': blocks
        })

    # Create blocks for invoice list
    blocks = [
        SlackMessageBuilder.create_text_block(
            f"💰 *Recent Invoices ({len(invoices)} shown)*"
        )
    ]

    for invoice in invoices:
        status_emoji = {
            'paid': '✅',
            'pending': '🟡',
            'overdue': '🔴',
            'draft': '📝'
        }.get(invoice.status.lower(), '⚪')

        total = f"${invoice.total_amount:.2f}" if invoice.total_amount else "$0.00"

        invoice_block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Invoice #{invoice.invoice_number}*\n{status_emoji} {invoice.status.title()} • {total}"
            },
            "accessory": SlackMessageBuilder.create_button_block(
                "View Details",
                "jobber_view_invoice",
                invoice.jobber_invoice_id
            )
        }
        blocks.append(invoice_block)

    if len(invoices) == 10:
        blocks.append(SlackMessageBuilder.create_text_block(
            "_Showing 10 most recent invoices. Use Jobber dashboard for complete list._"
        ))

    return jsonify({
        'response_type': 'ephemeral',
        'text': 'Recent Invoices',
        'blocks': blocks
    })

# Jobber webhook handlers
def handle_jobber_client_created(data):
    """Handle new client creation from Jobber"""
    from models.jobber_models import JobberClient
    from app import db

    try:
        client_id = data.get('itemId')
        if not client_id:
            current_app.logger.error("No itemId in client created webhook")
            return

        # Fetch full client data from Jobber API
        jobber_client = JobberAPIClient()
        client_data = jobber_client.get_client(client_id)

        if not client_data:
            current_app.logger.error(f"Could not fetch client data for ID: {client_id}")
            return

        # Transform and save client
        model_data = transform_jobber_client_to_model(client_data)

        # Use upsert method to create or update
        was_new = not JobberClient.query.filter_by(jobber_client_id=client_id).first()
        client = JobberClient.upsert(client_id, **model_data)

        if was_new:
            current_app.logger.info(f"Created new client: {client_id}")
            # Send Slack notification
            client_name = model_data.get('company_name') or f'{model_data.get("first_name")} {model_data.get("last_name")}'
            send_slack_notification_async(
                f"🆕 New Jobber client created: {client_name}",
                event_type="client_created",
                data={
                    'client_name': client_name,
                    'email': model_data.get('email'),
                    'phone': model_data.get('phone'),
                    'client_id': client_id
                }
            )
        else:
            current_app.logger.info(f"Updated existing client: {client_id}")

    except Exception as e:
        current_app.logger.error(f"Error handling client created webhook: {e}")

def handle_jobber_client_updated(data):
    """Handle client updates from Jobber"""
    from models.jobber_models import JobberClient
    from app import db

    try:
        client_id = data.get('itemId')
        if not client_id:
            current_app.logger.error("No itemId in client updated webhook")
            return

        # Fetch full client data from Jobber API
        jobber_client = JobberAPIClient()
        client_data = jobber_client.get_client(client_id)

        if not client_data:
            current_app.logger.error(f"Could not fetch client data for ID: {client_id}")
            return

        # Transform and update client using upsert
        model_data = transform_jobber_client_to_model(client_data)
        client = JobberClient.upsert(client_id, **model_data)
        current_app.logger.info(f"Updated client: {client_id}")

    except Exception as e:
        current_app.logger.error(f"Error handling client updated webhook: {e}")

def handle_jobber_job_created(data):
    """Handle new job creation from Jobber"""
    from models.jobber_models import JobberJob
    from app import db

    try:
        job_id = data.get('itemId')
        if not job_id:
            current_app.logger.error("No itemId in job created webhook")
            return

        # Fetch full job data from Jobber API
        jobber_client = JobberAPIClient()
        job_data = jobber_client.get_job(job_id)

        if not job_data:
            current_app.logger.error(f"Could not fetch job data for ID: {job_id}")
            return

        # Transform and save job using upsert
        model_data = transform_jobber_job_to_model(job_data)

        # Use upsert method to create or update
        was_new = not JobberJob.query.filter_by(jobber_job_id=job_id).first()
        job = JobberJob.upsert(job_id, **model_data)

        if was_new:
            current_app.logger.info(f"Created new job: {job_id}")
            # Send Slack notification
            send_slack_notification_async(
                f"🔧 New Jobber job created: {model_data.get('title', 'Untitled Job')}",
                event_type="job_created",
                data={
                    'title': model_data.get('title', 'Untitled Job'),
                    'client_name': model_data.get('client_name', 'Unknown'),
                    'status': model_data.get('status', 'Unknown'),
                    'total': model_data.get('total_amount', 0),
                    'start_date': model_data.get('start_date', 'TBD'),
                    'job_id': job_id
                }
            )
        else:
            current_app.logger.info(f"Updated existing job: {job_id}")

    except Exception as e:
        current_app.logger.error(f"Error handling job created webhook: {e}")

def handle_jobber_job_updated(data):
    """Handle job updates from Jobber"""
    from models.jobber_models import JobberJob
    from app import db

    try:
        job_id = data.get('itemId')
        if not job_id:
            current_app.logger.error("No itemId in job updated webhook")
            return

        # Fetch full job data from Jobber API
        jobber_client = JobberAPIClient()
        job_data = jobber_client.get_job(job_id)

        if not job_data:
            current_app.logger.error(f"Could not fetch job data for ID: {job_id}")
            return

        # Get old status before update for completion notification
        existing_job = JobberJob.query.filter_by(jobber_job_id=job_id).first()
        old_status = existing_job.status if existing_job else None

        # Transform and update job using upsert
        model_data = transform_jobber_job_to_model(job_data)
        job = JobberJob.upsert(job_id, **model_data)
        current_app.logger.info(f"Updated job: {job_id}")

        # Send notification for job completion
        new_status = model_data.get('status')
        if old_status != 'completed' and new_status == 'completed':
            send_slack_notification_async(
                f"✅ Jobber job completed: {model_data.get('title', 'Untitled Job')}",
                event_type="job_completed",
                data={
                    'title': model_data.get('title', 'Untitled Job'),
                    'client_name': model_data.get('client_name', 'Unknown'),
                    'status': new_status,
                    'total': model_data.get('total_amount', 0),
                    'job_id': job_id
                }
            )

    except Exception as e:
        current_app.logger.error(f"Error handling job updated webhook: {e}")

def handle_jobber_invoice_created(data):
    """Handle new invoice creation from Jobber"""
    from models.jobber_models import JobberInvoice
    from app import db

    try:
        invoice_id = data.get('itemId')
        if not invoice_id:
            current_app.logger.error("No itemId in invoice created webhook")
            return

        # Fetch full invoice data from Jobber API
        jobber_client = JobberAPIClient()
        invoice_data = jobber_client.get_invoice(invoice_id)

        if not invoice_data:
            current_app.logger.error(f"Could not fetch invoice data for ID: {invoice_id}")
            return

        # Transform and save invoice using upsert
        model_data = transform_jobber_invoice_to_model(invoice_data)

        # Use upsert method to create or update
        was_new = not JobberInvoice.query.filter_by(jobber_invoice_id=invoice_id).first()
        invoice = JobberInvoice.upsert(invoice_id, **model_data)

        if was_new:
            current_app.logger.info(f"Created new invoice: {invoice_id}")
            # Send Slack notification
            send_slack_notification_async(
                f"💰 New Jobber invoice created: #{model_data.get('invoice_number', invoice_id)} - ${model_data.get('total_amount', 0):.2f}",
                event_type="invoice_created",
                data={
                    'invoice_number': model_data.get('invoice_number', invoice_id),
                    'client_name': model_data.get('client_name', 'Unknown'),
                    'total': model_data.get('total_amount', 0),
                    'status': model_data.get('status', 'Unknown'),
                    'invoice_id': invoice_id
                }
            )
        else:
            current_app.logger.info(f"Updated existing invoice: {invoice_id}")

    except Exception as e:
        current_app.logger.error(f"Error handling invoice created webhook: {e}")

def handle_jobber_invoice_updated(data):
    """Handle invoice updates from Jobber"""
    from models.jobber_models import JobberInvoice
    from app import db

    try:
        invoice_id = data.get('itemId')
        if not invoice_id:
            current_app.logger.error("No itemId in invoice updated webhook")
            return

        # Fetch full invoice data from Jobber API
        jobber_client = JobberAPIClient()
        invoice_data = jobber_client.get_invoice(invoice_id)

        if not invoice_data:
            current_app.logger.error(f"Could not fetch invoice data for ID: {invoice_id}")
            return

        # Get old status before update for payment notification
        existing_invoice = JobberInvoice.query.filter_by(jobber_invoice_id=invoice_id).first()
        old_status = existing_invoice.status if existing_invoice else None

        # Transform and update invoice using upsert
        model_data = transform_jobber_invoice_to_model(invoice_data)
        invoice = JobberInvoice.upsert(invoice_id, **model_data)
        current_app.logger.info(f"Updated invoice: {invoice_id}")

        # Send notification for payment
        new_status = model_data.get('status')
        if old_status != 'paid' and new_status == 'paid':
            send_slack_notification_async(
                f"💸 Invoice paid: #{model_data.get('invoice_number', invoice_id)} - ${model_data.get('total_amount', 0):.2f}"
            )

    except Exception as e:
        current_app.logger.error(f"Error handling invoice updated webhook: {e}")

def send_slack_notification_async(message: str, channel: str = None, event_type: str = None, data: dict = None):
    """Send Slack notification asynchronously"""
    try:
        # Default notification channel (could be configured per team/workspace)
        if not channel:
            channel = current_app.config.get('SLACK_DEFAULT_CHANNEL', '#general')

        slack_client = get_slack_client()

        if event_type and data:
            # Use rich formatting for structured events
            blocks = SlackMessageBuilder.create_jobber_notification(event_type, data)
            slack_client.post_message(
                channel=channel,
                text=message,  # Fallback text
                blocks=blocks
            )
        else:
            # Simple text message
            slack_client.post_message(
                channel=channel,
                text=message
            )

        current_app.logger.info(f"Slack notification sent to {channel}: {message}")

    except Exception as e:
        current_app.logger.error(f"Failed to send Slack notification: {e}")
        # Don't raise exception to avoid breaking webhook processing