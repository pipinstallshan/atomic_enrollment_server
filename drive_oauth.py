# drive_oauth.py

import os
import mimetypes
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from models import DriveAccount, db
from dotenv import load_dotenv
load_dotenv()

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile"
]

def create_drive_oauth_flow(state=None):
    """
    Create an OAuth flow for Google Drive with your client config.
    You might want to adapt the redirect URI to the route for the drive blueprint.
    """
    redirect_uri = "https://atomic.steamlined.solutions/drive/oauth2callback"
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri]
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=DRIVE_SCOPES,
        state=state,
        redirect_uri=redirect_uri
    )
    return flow

def get_drive_user_info(credentials):
    """
    Optional: get user info from the Drive API or from the /userinfo endpoint.
    For example, you might get the user's email to store in your DB.
    """
    # Ensure credentials are valid before making the request
    if credentials.expired:
        credentials.refresh(Request())
    # For drive, you can just store the email if you want
    service = build('oauth2', 'v2', credentials=credentials)
    user_info = service.userinfo().get().execute()
    return user_info


def save_drive_credentials(user, credentials, drive_user_info):
    """
    Save or update the user's Drive account in DB.
    Similar to how you used to save YouTube credentials, 
    but now we store drive-specific info.
    """
    acct = DriveAccount.query.filter_by(email=drive_user_info['email'], user_id=user.id).first()
    if not acct:
        acct = DriveAccount(
            email=drive_user_info['email'],
            user_id=user.id
        )
    
    acct.refresh_token = credentials.refresh_token
    acct.access_token = credentials.token
    acct.token_expiry = credentials.expiry
    acct.account_name = drive_user_info.get('name', 'Drive User')

    db.session.add(acct)
    db.session.commit()

def remove_drive_account(account):
    db.session.delete(account)
    db.session.commit()

def get_valid_drive_credentials(account):
    """
    Rebuild the credentials from the stored DB info and refresh if needed.
    """
    creds = Credentials(
        token=account.access_token,
        refresh_token=account.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=DRIVE_SCOPES
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            account.access_token = creds.token
            account.token_expiry = creds.expiry
            # Possibly update refresh token if it changed
            if creds.refresh_token != account.refresh_token:
                account.refresh_token = creds.refresh_token
            db.session.commit()
        except Exception as e:
            # Mark for reauth if token can't refresh
            account.needs_reauth = True
            db.session.commit()
            raise
    return creds


def upload_file_to_drive(file_path, title, user_id=None, folder_id=None):
    """
    Upload a file to Google Drive, returning a shareable link.
    
    - file_path: local path to the MP4
    - user_id: which user this belongs to
    - folder_id: optional folder in Drive to upload to
    """
    from flask_login import current_user

    # pick an account (like how you used to pick a random or specific YT channel),
    # but now it’s drive accounts:
    acct = pick_drive_account_for_upload(user_id)  # implement your logic
    creds = get_valid_drive_credentials(acct)
    
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Create metadata
    file_metadata = {
        'name': title,
    }
    if folder_id:
        file_metadata['parents'] = [folder_id]
    
    media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=True)

    request = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    )
    response = None
    while response is None:
        status, response = request.next_chunk()
        # optional: track upload progress
    file_id = response.get('id')

    # Make it shareable, for instance "anyone with the link can view"
    permission_body = {
        'role': 'reader',
        'type': 'anyone'
    }
    drive_service.permissions().create(
        fileId=file_id,
        body=permission_body
    ).execute()

    share_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    return share_link

def pick_drive_account_for_upload(user_id=None):
    """
    Either pick a random drive account or the first one. 
    Example placeholder logic:
    """
    from models import DriveAccount
    if user_id is not None:
        accts = DriveAccount.query.filter_by(user_id=user_id).all()
    else:
        accts = DriveAccount.query.filter_by().all()
    if not accts:
        raise ValueError("No Google Drive accounts connected")
    # do your random or best pick logic
    return accts[0]
