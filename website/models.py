# models.py
from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func

# No need to import FIMHandler here anymore
# from .fim_monitor import FIMHandler  # Remove this line

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(20000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    firstName = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'employee'
    
    # 🔥 Transient Attribute (Not stored in DB)
    @property
    def fim_handler(self):
        # Move the import inside the method to avoid circular imports
        from website.handler import FIMHandler
        if not hasattr(self, '_fim_handler'):
            self._fim_handler = FIMHandler(self.role, self.firstName)
        return self._fim_handler
