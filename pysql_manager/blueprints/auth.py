from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from db_helper import CredentialsCrypto, get_db_connection

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to dashboard
    if 'creds' in session:
        return redirect(url_for('db_bp.dashboard'))
        
    form_data = {
        'host': 'localhost',
        'port': '3307',
        'username': 'root',
        'password': '',
        'database': ''
    }
    
    if request.method == 'POST':
        form_data['host'] = request.form.get('host', 'localhost').strip()
        form_data['port'] = request.form.get('port', '3307').strip()
        form_data['username'] = request.form.get('username', 'root').strip()
        form_data['password'] = request.form.get('password', '')
        form_data['database'] = request.form.get('database', '').strip()
        
        # Validate connection parameters
        try:
            conn = get_db_connection(form_data)
            conn.close()
            
            # Credentials are valid! Encrypt and save in session
            crypto = CredentialsCrypto(current_app.secret_key)
            session['creds'] = crypto.encrypt(form_data)
            
            flash('Connected successfully to MySQL server!', 'success')
            return redirect(url_for('db_bp.dashboard'))
            
        except Exception as e:
            flash(f"Connection failed: {str(e)}", 'danger')
            
    return render_template('login.html', form_data=form_data)

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth_bp.login'))
