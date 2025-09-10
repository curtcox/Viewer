"""
Local development authentication routes.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user
from auth_providers import create_local_user

# Create blueprint for local auth routes
local_auth_bp = Blueprint('local_auth', __name__)


@local_auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Local development login - simple one-click login."""
    if request.method == 'POST':
        # Create or get a local development user
        user = create_local_user()

        # Log the user in
        login_user(user)

        flash(f'Welcome, {user.first_name}! You are now logged in as a local development user.', 'success')

        # Redirect to next URL or dashboard
        next_url = session.pop('next_url', None)
        if next_url:
            return redirect(next_url)
        return redirect(url_for('dashboard'))

    # GET request - show login page
    return render_template('local_login.html')


@local_auth_bp.route('/logout')
def logout():
    """Local development logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@local_auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Local development registration - create a new local user."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()

        # Create new local user
        user = create_local_user(
            email=email if email else None,
            first_name=first_name if first_name else None,
            last_name=last_name if last_name else None
        )

        # Log the user in
        login_user(user)

        flash(f'Welcome, {user.first_name}! Your local development account has been created.', 'success')

        # Redirect to next URL or dashboard
        next_url = session.pop('next_url', None)
        if next_url:
            return redirect(next_url)
        return redirect(url_for('dashboard'))

    # GET request - show registration page
    return render_template('local_register.html')
