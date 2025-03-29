from flask import Blueprint, render_template, request, redirect, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from .models import User
from . import db
from .decorators import role_required  # ✅ Import the decorator
from flask_login import current_user
from .fim_monitor import start_fim_monitor, MONITOR_DIR
from threading import Thread


auth = Blueprint('auth', __name__)

@auth.route('/admin-dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    return render_template("admin_dashboard.html")

@auth.route('/employee-dashboard')
@login_required
@role_required('employee')
def employee_dashboard():
    return render_template("employee_dashboard.html")



@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)
            flash(f'Welcome {user.firstName}!', category='success')

            # Start FIM monitoring in a separate thread
            def start_monitoring():
                if user.role == 'admin':
                    start_fim_monitor(MONITOR_DIR, 'admin')
                else:
                    start_fim_monitor(MONITOR_DIR, 'employee')

            # Start monitoring in a separate thread
            thread = Thread(target=start_monitoring)
            thread.start()

            # Redirect correctly based on role
            if user.role == 'admin':
                return redirect(url_for('auth.admin_dashboard'))
            else:
                return redirect(url_for('auth.employee_dashboard'))
        else:
            flash('Invalid email or password', category='error')

    return render_template("login.html", user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/sign-up', methods=['POST', 'GET'])
def sign_up():
    admin_invite_code = "SAFEADMIN2025"  # Change as needed

    if request.method == 'POST':
        email = request.form.get('email')
        firstName = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        role = request.form.get('role')
        invite_code = request.form.get('invite_code') if role == 'admin' else None

        user = User.query.filter_by(email=email).first()

        if user:
            flash("Email already exists.", category='error')
        elif role == 'admin' and invite_code != admin_invite_code:
            flash("Invalid admin invite code!", category='error')
        elif len(email) < 6:
            flash('Email must be at least six characters.', category='error')
        elif len(firstName) < 2:
            flash('First Name too short.', category='error')
        elif password1 != password2:
            flash('Passwords do not match.', category='error')
        elif len(password1) < 7:
            flash('Password too short.', category='error')
        else:
            new_user = User(
                email=email,
                firstName=firstName,
                password=generate_password_hash(password1, method='pbkdf2:sha256'),
                role=role
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash(f'{role.capitalize()} account created!', category='success')
            return redirect(url_for('auth.login'))  # ✅ Redirect to login page after signup

    return render_template("sign_up.html", user=current_user)
