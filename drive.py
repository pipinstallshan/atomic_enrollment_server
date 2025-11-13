# drive.py

from flask import Blueprint, render_template, redirect, url_for, jsonify, session, current_app, request, flash
from flask_login import login_required, current_user
from datetime import timedelta
import secrets
import logging
from drive_oauth import create_drive_oauth_flow, get_drive_user_info, save_drive_credentials, remove_drive_account
from models import DriveAccount
from google.auth.transport.requests import Request
from utils.role_helpers import roles_required

logger = logging.getLogger(__name__)

drive_bp = Blueprint('drive', __name__)

@drive_bp.route('/accounts')
@login_required
@roles_required('admin')  # Only admins can manage drive accounts
def accounts():
    """List connected drive accounts."""
    accounts = current_user.drive_accounts
    return render_template('drive.html', accounts=accounts)

@drive_bp.route('/connect')
@login_required
@roles_required('admin')  # Only admins can connect new drive accounts
def connect():
    """Start Google Drive OAuth flow."""
    # Clear any existing OAuth state
    session.pop('oauth_state', None)
    
    # Generate state token
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    session.modified = True
    
    # Start OAuth for Drive
    flow = create_drive_oauth_flow(state=state)
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    return redirect(auth_url)

@login_required
@drive_bp.route('/oauth2callback')
def oauth2callback():
    """
    Handle OAuth callback from Google Drive.
    """
    try:
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            flash('Drive authentication failed. Please try again.', 'error')
            return redirect(url_for('drive.accounts'))
            
        stored_state = session.get('oauth_state')
        if not state or not stored_state or state != stored_state:
            flash('Authentication session expired or mismatched state.', 'error')
            return redirect(url_for('drive.accounts'))
    
        # Exchange code for credentials
        flow = create_drive_oauth_flow(state=state)
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        # Ensure credentials are valid before making the request
        if credentials.expired:
            credentials.refresh(Request())
        
        # Retrieve user info
        drive_user_info = get_drive_user_info(credentials)  # Make sure get_drive_user_info returns the data
        if not drive_user_info:
            flash('Failed to retrieve Drive user info.', 'error')
            return redirect(url_for('drive.accounts'))
        
        # Save or update the Drive account in DB
        save_drive_credentials(current_user, credentials, drive_user_info)
        
        flash("Drive account connected successfully!", "success")
        return redirect(url_for('drive.accounts'))
    
    except Exception as e:
        logger.error(f"Error during Drive OAuth callback: {e}")
        flash('Failed to connect Google Drive. Please try again.', 'error')
        return redirect(url_for('drive.accounts'))


@login_required
@drive_bp.route('/disconnect/<int:account_id>', methods=['POST'])
def disconnect(account_id):
    """
    Remove a connected Drive account from DB.
    """
    account = DriveAccount.query.get_or_404(account_id)
    if account.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    remove_drive_account(account)  # In drive_oauth.py or similar
    return jsonify({'status': 'success'}), 200
