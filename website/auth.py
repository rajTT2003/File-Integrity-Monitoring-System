from flask import Blueprint, render_template, request,redirect, flash, url_for
#render_template allows us to use html pages/ template pages in folder templates
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user


auth = Blueprint('auth', __name__)


#methods - tells us what kind of http request it can handle
@auth.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    email = request.form.get('email')
    password = request.form.get('password')

    user = User.query.filter_by(email = email).first()
    if user:
      if check_password_hash(user.password, password):
        flash('Logged in Successfully!', category='success')
        login_user(user, remember=True)
        return redirect(url_for('views.home'))
      else:
        flash('Incorrect password, try again', category = 'error')
    else:
      flash('Email does not exist', category = 'error')

  #access data sent to this endpoint
  data = request.form
  print(data)
  #text=Testing , this is a variable accessible to the login.html
  return render_template("login.html", user = current_user)

@auth.route('/logout')
@login_required
def logout():
  logout_user()
  return redirect(url_for('auth.login'))


@auth.route('/sign-up', methods=['POST', 'GET'])
def sign_up():

  #get data from form
  if request.method == 'POST':
    email = request.form.get('email')
    firstName = request.form.get('firstName')
    password1 = request.form.get('password1')
    password2 = request.form.get('password2')

    user = User.query.filter_by(email = email).first()

    if user:
      flash("Email already exists.", category='error')

    #form validation
    elif len(email) < 6:
      #output message to user using flash
      flash('Email must be greater than four characters', category='error')
      # print('Password too short')
    elif len(firstName)  < 2:
      flash('First Name too short long', category='error')
    elif password1 != password2:
      flash('Password do not match.', category='error')
    elif len(password1) < 7:
      flash('Password too short', category='error')
    else:
      new_user = User(email=email, firstName = firstName, password= generate_password_hash(password1,method='pbkdf2:sha256'))
      db.session.add(new_user)
      db.session.commit()
      login_user(new_user, remember=True)
      #output message to user using flash
      flash('Account Created', category='success')
      return redirect(url_for('views.home'))


      

  return render_template("sign_up.html", user=current_user)