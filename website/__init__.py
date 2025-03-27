from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
import os
import threading
from flask_login import LoginManager
from .fim_monitor import start_fim_monitor

db = SQLAlchemy()
DB_NAME = "safebank.db"
DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), DB_NAME)
MONITOR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Monitor"))


def create_app():
    app = Flask(__name__)
    
    # Encrypt cookies and session
    app.config['SECRET_KEY'] = 'random_string'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User, Note

    create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # Ensure the monitored directory exists
    os.makedirs(MONITOR_DIR, exist_ok=True)

    # Start FIM in a separate thread
    fim_thread = threading.Thread(target=start_fim_monitor, args=(MONITOR_DIR,), daemon=True)
    fim_thread.start()

    return app


def create_database(app):
    with app.app_context():
        if not path.exists(DB_PATH):
            db.create_all()
            print("Database created successfully!")
        else:
            print("Database already exists.")
