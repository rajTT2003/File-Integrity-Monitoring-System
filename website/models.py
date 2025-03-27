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
  #columns
  #(type of column, set as primary key)
  id = db.Column(db.Integer, primary_key=True)
  #(type of column, status)
  email = db.Column(db.String(500), unique=True)
  password = db.Column(db.String(500)) 
  firstName = db.Column(db.String(500))
  role = db.Column(db.String(500))
  notes = db.relationship('Note')
  
