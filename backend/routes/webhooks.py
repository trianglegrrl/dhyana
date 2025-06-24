import hmac
import hashlib
import json
from flask import Blueprint, request, jsonify, current_app
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier

webhooks_bp = Blueprint('webhooks', __name__)

@webhooks_bp.route('/slack/events', methods=['POST'])
def slack_events():
    """Handle Slack Events API webhooks"""
    # Verify Slack signature
    signature_verifier = SignatureVerifier(current_app.config['SLACK_SIGNING_SECRET'])

    if not signature_verifier.is_valid_request(request.get_data(), request.headers):
        return jsonify({'error': 'Invalid request signature'}), 401

    data = request.get_json()

    # Handle URL verification challenge
    if data.get('type') == 'url_verification':
        return jsonify({'challenge': data.get('challenge')})

    # Handle events
    if data.get('type') == 'event_callback':
        event = data.get('event', {})
        event_type = event.get('type')

        if event_type == 'message':
            handle_slack_message(event, data.get('team_id'))
        elif event_type == 'app_mention':
            handle_slack_mention(event, data.get('team_id'))
        elif event_type == 'channel_created':
            handle_slack_channel_created(event, data.get('team_id'))
        elif event_type == 'team_join':
            handle_slack_user_joined(event, data.get('team_id'))

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

@webhooks_bp.route('/jobber/webhooks', methods=['POST'])
def jobber_webhooks():
    """Handle Jobber webhooks"""
    # Verify Jobber webhook signature if they provide one
    # For now, we'll implement basic webhook handling

    data = request.get_json()
    event_type = data.get('event_type')

    if event_type == 'client.created':
        handle_jobber_client_created(data)
    elif event_type == 'client.updated':
        handle_jobber_client_updated(data)
    elif event_type == 'job.created':
        handle_jobber_job_created(data)
    elif event_type == 'job.updated':
        handle_jobber_job_updated(data)
    elif event_type == 'invoice.created':
        handle_jobber_invoice_created(data)
    elif event_type == 'invoice.updated':
        handle_jobber_invoice_updated(data)
    elif event_type == 'invoice.paid':
        handle_jobber_invoice_paid(data)

    return jsonify({'status': 'received'})

# Slack event handlers
def handle_slack_message(event, team_id):
    """Handle new Slack messages"""
    from models import SlackMessage, SlackChannel
    from app import db

    # Don't process bot messages
    if event.get('bot_id'):
        return

    # Store message in database
    message = SlackMessage(
        message_ts=event.get('ts'),
        channel_id=event.get('channel'),
        user_id=event.get('user'),
        text=event.get('text'),
        message_type=event.get('subtype', 'message'),
        thread_ts=event.get('thread_ts')
    )

    try:
        message.save()
    except Exception as e:
        current_app.logger.error(f"Error saving message: {e}")

def handle_slack_mention(event, team_id):
    """Handle app mentions"""
    # Process the mention and respond if needed
    pass

def handle_slack_channel_created(event, team_id):
    """Handle new channel creation"""
    from models import SlackChannel

    channel = SlackChannel(
        channel_id=event.get('channel', {}).get('id'),
        team_id=team_id,
        name=event.get('channel', {}).get('name'),
        is_private=event.get('channel', {}).get('is_private', False)
    )

    try:
        channel.save()
    except Exception as e:
        current_app.logger.error(f"Error saving channel: {e}")

def handle_slack_user_joined(event, team_id):
    """Handle new user joining team"""
    from models import SlackUser

    user = SlackUser(
        user_id=event.get('user', {}).get('id'),
        team_id=team_id,
        username=event.get('user', {}).get('name'),
        real_name=event.get('user', {}).get('real_name'),
        email=event.get('user', {}).get('profile', {}).get('email')
    )

    try:
        user.save()
    except Exception as e:
        current_app.logger.error(f"Error saving user: {e}")

def handle_slack_block_actions(payload):
    """Handle block actions from interactive components"""
    pass

def handle_slack_modal_submission(payload):
    """Handle modal form submissions"""
    pass

def handle_slack_shortcut(payload):
    """Handle global shortcuts"""
    pass

def handle_jobber_command(text, user_id, channel_id, team_id):
    """Handle /jobber slash command"""
    # Basic command parsing
    if not text:
        return jsonify({
            'text': 'Available commands: /jobber clients, /jobber jobs, /jobber invoices'
        })

    parts = text.strip().split()
    command = parts[0] if parts else ''

    if command == 'clients':
        return handle_jobber_clients_command(parts[1:], user_id, channel_id)
    elif command == 'jobs':
        return handle_jobber_jobs_command(parts[1:], user_id, channel_id)
    elif command == 'invoices':
        return handle_jobber_invoices_command(parts[1:], user_id, channel_id)

    return jsonify({'text': f'Unknown command: {command}'})

def handle_jobber_clients_command(args, user_id, channel_id):
    """Handle jobber clients command"""
    from models import JobberClient

    clients = JobberClient.query.filter_by(is_active=True).limit(5).all()

    if not clients:
        return jsonify({'text': 'No active clients found'})

    text = "Recent clients:\n"
    for client in clients:
        name = client.company_name or f"{client.first_name} {client.last_name}"
        text += f"• {name}\n"

    return jsonify({'text': text})

def handle_jobber_jobs_command(args, user_id, channel_id):
    """Handle jobber jobs command"""
    from models import JobberJob

    jobs = JobberJob.query.limit(5).all()

    if not jobs:
        return jsonify({'text': 'No jobs found'})

    text = "Recent jobs:\n"
    for job in jobs:
        text += f"• {job.title} - {job.status}\n"

    return jsonify({'text': text})

def handle_jobber_invoices_command(args, user_id, channel_id):
    """Handle jobber invoices command"""
    from models import JobberInvoice

    invoices = JobberInvoice.query.limit(5).all()

    if not invoices:
        return jsonify({'text': 'No invoices found'})

    text = "Recent invoices:\n"
    for invoice in invoices:
        text += f"• {invoice.invoice_number} - {invoice.status} - ${invoice.total_amount}\n"

    return jsonify({'text': text})

# Jobber webhook handlers
def handle_jobber_client_created(data):
    """Handle new Jobber client creation"""
    from models import JobberClient

    client_data = data.get('client', {})

    client = JobberClient(
        jobber_client_id=str(client_data.get('id')),
        company_name=client_data.get('company_name'),
        first_name=client_data.get('first_name'),
        last_name=client_data.get('last_name'),
        email=client_data.get('email'),
        phone=client_data.get('phone')
    )

    try:
        client.save()
        current_app.logger.info(f"New Jobber client created: {client.jobber_client_id}")
    except Exception as e:
        current_app.logger.error(f"Error creating Jobber client: {e}")

def handle_jobber_client_updated(data):
    """Handle Jobber client updates"""
    pass

def handle_jobber_job_created(data):
    """Handle new Jobber job creation"""
    pass

def handle_jobber_job_updated(data):
    """Handle Jobber job updates"""
    pass

def handle_jobber_invoice_created(data):
    """Handle new Jobber invoice creation"""
    pass

def handle_jobber_invoice_updated(data):
    """Handle Jobber invoice updates"""
    pass

def handle_jobber_invoice_paid(data):
    """Handle Jobber invoice payment"""
    pass