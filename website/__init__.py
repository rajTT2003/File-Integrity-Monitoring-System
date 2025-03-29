from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
import os
from flask_login import LoginManager, current_user

# Initialize SQLAlchemy
db = SQLAlchemy()

# Database configuration
DB_NAME = "safebank.db"
DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), DB_NAME)
MONITOR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Monitor"))


def create_app():
    app = Flask(__name__)

    # Encrypt cookies and session
    app.config['SECRET_KEY'] = 'random_string'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
    db.init_app(app)

    # Register Blueprints
    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    # Import models
    from .models import User, Note

    # Create database if it doesn't exist
    create_database(app)

    # Configure Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Make `user` available in templates (prevents Jinja errors)
    @app.context_processor
    def inject_user():
        return dict(user=current_user)

    # Ensure the monitored directory exists
    os.makedirs(MONITOR_DIR, exist_ok=True)

    # ❌ Remove FIM thread here (Fix applied)
    
    return app

def create_database(app):
    with app.app_context():
        if not path.exists(DB_PATH):
            try:
                db.create_all()
                print("Database created successfully!")
            except Exception as e:
                print(f"Error creating database: {e}")
        else:
            print("Database already exists.")
