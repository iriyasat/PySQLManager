from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, jsonify
from db_helper import CredentialsCrypto, execute_query, split_sql_script

query_bp = Blueprint('query_bp', __name__)

def get_creds():
    crypto = CredentialsCrypto(current_app.secret_key)
    return crypto.decrypt(session.get('creds'))

@query_bp.route('/sql', methods=['GET', 'POST'])
def sql_console():
    creds = get_creds()
    if not creds:
        return redirect(url_for('auth_bp.login'))
        
    db_name = request.args.get('db_name') or request.form.get('db_name')
    query_text = request.form.get('query_text', '').strip()
    
    execution_results = []
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1'
    
    if request.method == 'POST' and query_text:
        statements = split_sql_script(query_text)
        
        # Execute statements sequentially
        for stmt in statements:
            if not stmt.strip():
                continue
                
            res = execute_query(creds, stmt, database=db_name)
            execution_results.append(res)
            
            # Stop execution on the first error to mimic transaction/sequential behavior
            if not res['success']:
                break
                
        if is_ajax:
            return jsonify({
                'success': all(r['success'] for r in execution_results),
                'results': execution_results
            })
            
    # Gather column and table helpers for the current database
    db_info = {}
    if db_name:
        tables_res = execute_query(creds, f"SHOW TABLES FROM `{db_name}`")
        if tables_res['success']:
            tbl_key = f"Tables_in_{db_name}"
            for r in tables_res['rows']:
                t_name = r[tbl_key]
                cols_res = execute_query(creds, f"SHOW COLUMNS FROM `{db_name}`.`{t_name}`")
                db_info[t_name] = [c['Field'] for c in cols_res['rows']] if cols_res['success'] else []
                
    return render_template('sql_editor.html', 
                           db_name=db_name, 
                           query_text=query_text, 
                           results=execution_results,
                           db_info=db_info)
