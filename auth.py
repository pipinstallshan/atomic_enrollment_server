from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import User
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Initialize login manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    logger.debug(f"Loading user with ID: {user_id}")
    return User.query.get(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    logger.debug("Login route accessed")
    logger.debug(f"Request method: {request.method}")
    
    if current_user.is_authenticated:
        logger.debug("User is already authenticated")
        return redirect(url_for('main.upload_file'))

    if request.method == 'POST':
        logger.debug("Processing login POST request")
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))

        logger.debug(f"Login attempt for username: {username}")
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            logger.debug("Password check successful")
            login_user(user, remember=remember, duration=timedelta(days=30))
            # Set session permanent to extend lifetime
            session.permanent = True
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.upload_file'))
        
        logger.debug("Login failed")
        flash('Invalid username or password')
    
    logger.debug("Rendering login template")
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    # Clear session
    session.clear()
    return redirect(url_for('auth.login'))

def init_auth(app):
    """Initialize authentication for the app."""
    logger.debug("Initializing authentication")
    
    # Set session lifetime
    app.permanent_session_lifetime = timedelta(days=30)
    
    # Initialize login manager
    login_manager.init_app(app)
    
    # Register blueprint
    app.register_blueprint(auth_bp)
    
    logger.debug("Authentication initialized")