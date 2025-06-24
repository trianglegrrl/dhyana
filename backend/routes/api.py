from flask import Blueprint, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from models import SlackTeam, SlackUser, SlackChannel, JobberClient, JobberJob, JobberInvoice

api_bp = Blueprint('api', __name__)
db = SQLAlchemy()

# Slack API endpoints
@api_bp.route('/slack/teams', methods=['GET'])
def get_slack_teams():
    """Get all Slack teams"""
    teams = SlackTeam.query.filter_by(is_active=True).all()
    return jsonify([team.to_dict() for team in teams])

@api_bp.route('/slack/teams/<team_id>', methods=['GET'])
def get_slack_team(team_id):
    """Get specific Slack team"""
    team = SlackTeam.query.filter_by(team_id=team_id).first()
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    return jsonify(team.to_dict())

@api_bp.route('/slack/teams/<team_id>/users', methods=['GET'])
def get_slack_users(team_id):
    """Get users for a specific team"""
    users = SlackUser.query.filter_by(team_id=team_id).all()
    return jsonify([user.to_dict() for user in users])

@api_bp.route('/slack/teams/<team_id>/channels', methods=['GET'])
def get_slack_channels(team_id):
    """Get channels for a specific team"""
    channels = SlackChannel.query.filter_by(team_id=team_id, is_archived=False).all()
    return jsonify([channel.to_dict() for channel in channels])

# Jobber API endpoints
@api_bp.route('/jobber/clients', methods=['GET'])
def get_jobber_clients():
    """Get all Jobber clients"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    clients = JobberClient.query.filter_by(is_active=True).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'clients': [client.to_dict() for client in clients.items],
        'total': clients.total,
        'pages': clients.pages,
        'current_page': clients.page
    })

@api_bp.route('/jobber/clients/<client_id>', methods=['GET'])
def get_jobber_client(client_id):
    """Get specific Jobber client"""
    client = JobberClient.query.filter_by(jobber_client_id=client_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404
    return jsonify(client.to_dict())

@api_bp.route('/jobber/clients', methods=['POST'])
def create_jobber_client():
    """Create new Jobber client"""
    data = request.get_json()

    client = JobberClient(
        jobber_client_id=data.get('jobber_client_id'),
        company_name=data.get('company_name'),
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        email=data.get('email'),
        phone=data.get('phone'),
        address_line1=data.get('address_line1'),
        city=data.get('city'),
        province=data.get('province'),
        postal_code=data.get('postal_code'),
        country=data.get('country'),
        notes=data.get('notes'),
        tags=data.get('tags', [])
    )

    try:
        client.save()
        return jsonify(client.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@api_bp.route('/jobber/clients/<client_id>', methods=['PUT'])
def update_jobber_client(client_id):
    """Update Jobber client"""
    client = JobberClient.query.filter_by(jobber_client_id=client_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404

    data = request.get_json()

    # Update fields
    for field in ['company_name', 'first_name', 'last_name', 'email', 'phone',
                  'address_line1', 'city', 'province', 'postal_code', 'country', 'notes', 'tags']:
        if field in data:
            setattr(client, field, data[field])

    try:
        client.save()
        return jsonify(client.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@api_bp.route('/jobber/clients/<client_id>', methods=['DELETE'])
def delete_jobber_client(client_id):
    """Soft delete Jobber client"""
    client = JobberClient.query.filter_by(jobber_client_id=client_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404

    client.is_active = False
    client.save()
    return jsonify({'message': 'Client deactivated successfully'})

@api_bp.route('/jobber/jobs', methods=['GET'])
def get_jobber_jobs():
    """Get all Jobber jobs"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    client_id = request.args.get('client_id')

    query = JobberJob.query
    if client_id:
        query = query.filter_by(client_id=client_id)

    jobs = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'jobs': [job.to_dict() for job in jobs.items],
        'total': jobs.total,
        'pages': jobs.pages,
        'current_page': jobs.page
    })

@api_bp.route('/jobber/jobs/<job_id>', methods=['GET'])
def get_jobber_job(job_id):
    """Get specific Jobber job"""
    job = JobberJob.query.filter_by(jobber_job_id=job_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job.to_dict())

@api_bp.route('/jobber/invoices', methods=['GET'])
def get_jobber_invoices():
    """Get all Jobber invoices"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    client_id = request.args.get('client_id')
    status = request.args.get('status')

    query = JobberInvoice.query
    if client_id:
        query = query.filter_by(client_id=client_id)
    if status:
        query = query.filter_by(status=status)

    invoices = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'invoices': [invoice.to_dict() for invoice in invoices.items],
        'total': invoices.total,
        'pages': invoices.pages,
        'current_page': invoices.page
    })

@api_bp.route('/jobber/invoices/<invoice_id>', methods=['GET'])
def get_jobber_invoice(invoice_id):
    """Get specific Jobber invoice"""
    invoice = JobberInvoice.query.filter_by(jobber_invoice_id=invoice_id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    return jsonify(invoice.to_dict())