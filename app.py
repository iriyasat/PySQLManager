import logging
from flask import Flask, session, redirect, url_for, request
from db_helper import CredentialsCrypto, execute_query

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Set a secure, stable secret key for session signing and credentials encryption.
app.secret_key = 'pysqlmanager_secure_encryption_and_session_signing_key_9933'

# Context processor to dynamically inject database navigation tree into sidebar
@app.context_processor
def inject_sidebar_data():
    if 'creds' not in session:
        return {'sidebar_databases': [], 'active_db': None, 'active_table': None}
        
    # Extract path parameters to highlight active items in the sidebar
    active_db = request.view_args.get('db_name') if request.view_args else None
    active_table = request.view_args.get('table_name') if request.view_args else None
    
    try:
        crypto = CredentialsCrypto(app.secret_key)
        creds = crypto.decrypt(session['creds'])
        if not creds:
            return {'sidebar_databases': [], 'active_db': None, 'active_table': None}
            
        # Get list of all databases
        db_res = execute_query(creds, "SHOW DATABASES")
        if not db_res['success']:
            return {'sidebar_databases': [], 'active_db': None, 'active_table': None}
            
        databases = []
        # Standard system databases to display or group separately
        system_dbs = ['information_schema', 'mysql', 'performance_schema', 'sys']
        
        for row in db_res['rows']:
            db_name = row['Database']
            is_system = db_name.lower() in system_dbs
            
            # Query tables for each database
            tables_res = execute_query(creds, f"SHOW TABLES FROM `{db_name}`")
            tables = []
            if tables_res['success']:
                key = f"Tables_in_{db_name}"
                tables = [r[key] for r in tables_res['rows'] if key in r]
            
            databases.append({
                'name': db_name,
                'tables': tables,
                'is_system': is_system
            })
            
        # Sort databases: user databases first, system databases at the end
        databases.sort(key=lambda x: (x['is_system'], x['name'].lower()))
        
        return {
            'sidebar_databases': databases,
            'active_db': active_db,
            'active_table': active_table,
            'current_user': creds.get('username'),
            'current_host': creds.get('host'),
            'current_port': creds.get('port')
        }
    except Exception as e:
        logger.error(f"Error in sidebar context processor: {e}")
        return {'sidebar_databases': [], 'active_db': None, 'active_table': None}

# Global login checker
@app.before_request
def require_login():
    allowed_endpoints = ['auth_bp.login', 'static']
    if 'creds' not in session:
        if request.endpoint and request.endpoint not in allowed_endpoints:
            return redirect(url_for('auth_bp.login'))

@app.route('/')
def index():
    return redirect(url_for('db_bp.dashboard'))

# Import and register blueprints
from blueprints.auth import auth_bp
from blueprints.db import db_bp
from blueprints.table import table_bp
from blueprints.query import query_bp
from blueprints.data_ops import data_bp

app.register_blueprint(auth_bp)
app.register_blueprint(db_bp)
app.register_blueprint(table_bp)
app.register_blueprint(query_bp)
app.register_blueprint(data_bp)

if __name__ == '__main__':
    # Run Flask server locally
    app.run(host='0.0.0.0', port=5001, debug=True)
