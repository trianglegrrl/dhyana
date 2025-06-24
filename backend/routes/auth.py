from flask import Blueprint, request, jsonify, session, redirect, current_app
from slack_sdk.oauth import AuthorizeUrlGenerator, RedirectUriPageRenderer
from slack_sdk.web import WebClient
import requests

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/slack/install', methods=['GET'])
def slack_install():
    """Initiate Slack OAuth flow"""
    # Slack OAuth configuration
    client_id = current_app.config.get('SLACK_CLIENT_ID')
    scopes = [
        'channels:read',
        'chat:write',
        'commands',
        'users:read',
        'team:read',
        'channels:history',
        'groups:history',
        'im:history',
        'mpim:history'
    ]

    authorize_url_generator = AuthorizeUrlGenerator(
        client_id=client_id,
        scopes=scopes,
        user_scopes=[]
    )

    authorize_url = authorize_url_generator.generate(state='slack-oauth-state')

    return redirect(authorize_url)

@auth_bp.route('/slack/oauth', methods=['GET'])
def slack_oauth_callback():
    """Handle Slack OAuth callback"""
    # Get authorization code from callback
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    if error:
        return jsonify({'error': f'OAuth error: {error}'}), 400

    if not code:
        return jsonify({'error': 'No authorization code received'}), 400

    # Exchange code for access token
    client_id = current_app.config.get('SLACK_CLIENT_ID')
    client_secret = current_app.config.get('SLACK_CLIENT_SECRET')

    try:
        client = WebClient()
        response = client.oauth_v2_access(
            client_id=client_id,
            client_secret=client_secret,
            code=code
        )

        if response['ok']:
            # Store team information
            team_info = response['team']
            access_token = response['access_token']
            bot_user_id = response['bot_user_id']

            # Save to database
            from models import SlackTeam

            team = SlackTeam.query.filter_by(team_id=team_info['id']).first()
            if not team:
                team = SlackTeam(
                    team_id=team_info['id'],
                    team_name=team_info['name'],
                    bot_token=access_token,
                    bot_user_id=bot_user_id
                )
            else:
                team.bot_token = access_token
                team.bot_user_id = bot_user_id
                team.is_active = True

            team.save()

            return jsonify({
                'message': 'Slack integration successful!',
                'team': team_info['name']
            })
        else:
            return jsonify({'error': 'Failed to exchange code for token'}), 400

    except Exception as e:
        current_app.logger.error(f"Slack OAuth error: {e}")
        return jsonify({'error': 'OAuth process failed'}), 500

@auth_bp.route('/jobber/auth', methods=['POST'])
def jobber_auth():
    """Authenticate with Jobber API"""
    data = request.get_json()
    api_key = data.get('api_key')
    api_secret = data.get('api_secret')

    if not api_key or not api_secret:
        return jsonify({'error': 'API key and secret are required'}), 400

    # Test the credentials by making a simple API call
    try:
        response = requests.get(
            f"{current_app.config['JOBBER_BASE_URL']}/api/account",
            headers={
                'X-API-Key': api_key,
                'X-API-Secret': api_secret,
                'Content-Type': 'application/json'
            }
        )

        if response.status_code == 200:
            # Store in session for now (in production, encrypt and store securely)
            session['jobber_api_key'] = api_key
            session['jobber_api_secret'] = api_secret

            account_info = response.json()
            return jsonify({
                'message': 'Jobber authentication successful',
                'account': account_info.get('name', 'Unknown')
            })
        else:
            return jsonify({
                'error': 'Invalid Jobber credentials',
                'status_code': response.status_code
            }), 401

    except Exception as e:
        current_app.logger.error(f"Jobber auth error: {e}")
        return jsonify({'error': 'Failed to authenticate with Jobber'}), 500

@auth_bp.route('/status', methods=['GET'])
def auth_status():
    """Check authentication status"""
    status = {
        'slack': False,
        'jobber': False
    }

    # Check Slack authentication
    from models import SlackTeam
    slack_teams = SlackTeam.query.filter_by(is_active=True).count()
    status['slack'] = slack_teams > 0

    # Check Jobber authentication
    status['jobber'] = 'jobber_api_key' in session and 'jobber_api_secret' in session

    return jsonify(status)

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Clear all authentication"""
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

@auth_bp.route('/slack/teams', methods=['GET'])
def get_authenticated_teams():
    """Get list of authenticated Slack teams"""
    from models import SlackTeam

    teams = SlackTeam.query.filter_by(is_active=True).all()
    return jsonify([{
        'team_id': team.team_id,
        'team_name': team.team_name,
        'team_domain': team.team_domain
    } for team in teams])

@auth_bp.route('/slack/teams/<team_id>/disconnect', methods=['POST'])
def disconnect_slack_team(team_id):
    """Disconnect a Slack team"""
    from models import SlackTeam

    team = SlackTeam.query.filter_by(team_id=team_id).first()
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    team.is_active = False
    team.bot_token = None
    team.save()

    return jsonify({'message': 'Team disconnected successfully'})