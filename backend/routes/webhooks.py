import hmac
import hashlib
import json
from flask import Blueprint, request, jsonify, current_app
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier
from utils.jobber_client import JobberAPIClient, transform_jobber_client_to_model, transform_jobber_job_to_model, transform_jobber_invoice_to_model

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
            send_slack_notification_async(
                f"🆕 New Jobber client created: {model_data.get('company_name') or f'{model_data.get(\"first_name\")} {model_data.get(\"last_name\")}'}"
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
                f"🔧 New Jobber job created: {model_data.get('title', 'Untitled Job')}"
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
                f"✅ Jobber job completed: {model_data.get('title', 'Untitled Job')}"
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
                f"💰 New Jobber invoice created: #{model_data.get('invoice_number', invoice_id)} - ${model_data.get('total_amount', 0):.2f}"
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

def send_slack_notification_async(message: str):
    """Send Slack notification asynchronously (placeholder for Celery task)"""
    # This would be implemented as a Celery task in production
    current_app.logger.info(f"Slack notification: {message}")
    # TODO: Implement actual Slack notification using WebClient