#gain access to database
from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func


class Note(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  data = db.Column(db.String(20000))
  date = db.Column(db.DateTime(timezone=True), default = func.now())
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

#represents table in database
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(500), unique=True, nullable=False)
    password = db.Column(db.String(500), nullable=False)
    firstName = db.Column(db.String(500), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'admin' or 'employee'

  
