from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user

def roles_required(*roles):
    """
    Decorator factory that checks if the current_user's role is one of the allowed roles.
    
    Usage:
        @login_required
        @roles_required('admin')
        def admin_page():
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('main.upload_file'))
            return fn(*args, **kwargs)
        return decorated_view
    return decorator 