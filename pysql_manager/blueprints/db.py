from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from db_helper import CredentialsCrypto, execute_query

db_bp = Blueprint('db_bp', __name__)

def get_creds():
    crypto = CredentialsCrypto(current_app.secret_key)
    return crypto.decrypt(session.get('creds'))

@db_bp.route('/dashboard')
def dashboard():
    creds = get_creds()
    if not creds:
        return redirect(url_for('auth_bp.login'))
        
    # Query server info
    version_res = execute_query(creds, "SELECT VERSION() AS version, USER() AS user")
    uptime_res = execute_query(creds, "SHOW STATUS LIKE 'Uptime'")
    
    server_info = {
        'version': version_res['rows'][0]['version'] if version_res['success'] and version_res['rows'] else 'Unknown',
        'user': version_res['rows'][0]['user'] if version_res['success'] and version_res['rows'] else 'Unknown',
        'uptime': 'Unknown'
    }
    
    if uptime_res['success'] and uptime_res['rows']:
        uptime_seconds = int(uptime_res['rows'][0]['Value'])
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        server_info['uptime'] = f"{days}d {hours}h {minutes}m"
        
    # Query databases details (CharSet, Collation, Size)
    db_details_query = """
        SELECT 
            s.SCHEMA_NAME AS `Database`, 
            s.DEFAULT_CHARACTER_SET_NAME AS `Charset`, 
            s.DEFAULT_COLLATION_NAME AS `Collation`,
            COALESCE(ROUND(SUM(t.DATA_LENGTH + t.INDEX_LENGTH) / 1024 / 1024, 2), 0.00) AS `SizeMB`
        FROM information_schema.SCHEMATA s
        LEFT JOIN information_schema.TABLES t ON s.SCHEMA_NAME = t.TABLE_SCHEMA
        GROUP BY s.SCHEMA_NAME, s.DEFAULT_CHARACTER_SET_NAME, s.DEFAULT_COLLATION_NAME
        ORDER BY s.SCHEMA_NAME
    """
    db_res = execute_query(creds, db_details_query)
    
    databases = db_res['rows'] if db_res['success'] else []
    
    return render_template('dashboard.html', server_info=server_info, databases=databases)

@db_bp.route('/database/create', methods=['POST'])
def create_db():
    creds = get_creds()
    db_name = request.form.get('db_name', '').strip()
    collation = request.form.get('collation', 'utf8mb4_general_ci')
    charset = collation.split('_')[0]
    
    if not db_name:
        flash("Database name cannot be empty.", "warning")
        return redirect(url_for('db_bp.dashboard'))
        
    # Create DB SQL
    query = f"CREATE DATABASE `{db_name}` CHARACTER SET {charset} COLLATE {collation}"
    res = execute_query(creds, query)
    
    if res['success']:
        flash(f"Database `{db_name}` created successfully!", "success")
    else:
        flash(f"Error creating database: {res['error']}", "danger")
        
    return redirect(url_for('db_bp.dashboard'))

@db_bp.route('/database/<db_name>/drop', methods=['POST'])
def drop_db(db_name):
    creds = get_creds()
    query = f"DROP DATABASE `{db_name}`"
    res = execute_query(creds, query)
    
    if res['success']:
        flash(f"Database `{db_name}` dropped successfully.", "success")
        return redirect(url_for('db_bp.dashboard'))
    else:
        flash(f"Error dropping database: {res['error']}", "danger")
        return redirect(url_for('db_bp.view_db', db_name=db_name))

@db_bp.route('/database/<db_name>')
def view_db(db_name):
    creds = get_creds()
    if not creds:
        return redirect(url_for('auth_bp.login'))
        
    # Get tables in the database
    tables_query = """
        SELECT 
            TABLE_NAME AS `Name`, 
            ENGINE AS `Engine`, 
            TABLE_COLLATION AS `Collation`, 
            TABLE_ROWS AS `Rows`, 
            ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024, 2) AS `SizeKB`, 
            AUTO_INCREMENT AS `AutoIncrement` 
        FROM information_schema.TABLES 
        WHERE TABLE_SCHEMA = %s
        ORDER BY TABLE_NAME
    """
    res = execute_query(creds, tables_query, (db_name,))
    tables = res['rows'] if res['success'] else []
    
    # Calculate totals
    total_tables = len(tables)
    total_rows = sum([row['Rows'] or 0 for row in tables])
    total_size = sum([row['SizeKB'] or 0.0 for row in tables])
    
    return render_template('db_dashboard.html', 
                           db_name=db_name, 
                           tables=tables, 
                           total_tables=total_tables, 
                           total_rows=total_rows, 
                           total_size=total_size)
