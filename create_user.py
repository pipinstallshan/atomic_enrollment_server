from models import create_user, init_db
from flask import Flask
import sys

def create_initial_user(username, email, password, role):
    """Create the initial user account."""
    # Create a minimal Flask application
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize the database
    init_db(app)
    
    # Create user within application context
    with app.app_context():
        try:
            user = create_user(username, email, password, role=role)
            print(f"Successfully created user: {username}")
            return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python create_user.py <username> <email> <password> <role>")
        sys.exit(1)
    
    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    role = sys.argv[4]
    if role not in ['admin', 'uploader']:
        print("Invalid role. Please use 'admin' or 'uploader'.")
        sys.exit(1)
    
    create_initial_user(username, email, password, role)