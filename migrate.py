from flask_migrate import Migrate
from main import app
from models import db

# Initialize Flask-Migrate
migrate = Migrate(app, db)

if __name__ == '__main__':
    from flask.cli import FlaskGroup
    cli = FlaskGroup(app)
    cli()