from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, Response
import datetime
from db_helper import CredentialsCrypto, get_db_connection, execute_query, split_sql_script

data_bp = Blueprint('data_bp', __name__)

def get_creds():
    crypto = CredentialsCrypto(current_app.secret_key)
    return crypto.decrypt(session.get('creds'))

@data_bp.route('/database/<db_name>/import-export')
def export_import_view(db_name):
    creds = get_creds()
    if not creds:
        return redirect(url_for('auth_bp.login'))
        
    # Get tables in the database
    tables_res = execute_query(creds, f"SHOW TABLES FROM `{db_name}`")
    key = f"Tables_in_{db_name}"
    tables = [row[key] for row in tables_res['rows']] if tables_res['success'] else []
    
    return render_template('import_export.html', db_name=db_name, tables=tables)

@data_bp.route('/database/<db_name>/export', methods=['POST'])
def export_db(db_name):
    creds = get_creds()
    if not creds:
        return redirect(url_for('auth_bp.login'))
        
    selected_tables = request.form.getlist('tables')
    export_type = request.form.get('export_type', 'structure_data')
    
    if not selected_tables:
        flash("Please select at least one table to export.", "warning")
        return redirect(url_for('data_bp.export_import_view', db_name=db_name))
        
    # Generate the SQL dump as a streaming text file download
    def generate_sql():
        conn = None
        try:
            conn = get_db_connection(creds, database=db_name)
            cursor = conn.cursor()
            
            yield f"-- PySQLManager SQL Dump\n"
            yield f"-- Host: {creds.get('host')}:{creds.get('port')}\n"
            yield f"-- Generation Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            yield f"-- Database: `{db_name}`\n\n"
            
            yield "SET FOREIGN_KEY_CHECKS=0;\n\n"
            
            for table in selected_tables:
                yield f"-- --------------------------------------------------------\n"
                yield f"-- Table structure & data for table `{table}`\n"
                yield f"-- --------------------------------------------------------\n"
                
                # 1. Export Table Structure
                if export_type in ['structure_data', 'structure_only']:
                    yield f"DROP TABLE IF EXISTS `{table}`;\n"
                    cursor.execute(f"SHOW CREATE TABLE `{table}`")
                    create_res = cursor.fetchone()
                    create_sql = create_res['Create Table']
                    yield f"{create_sql};\n\n"
                    
                # 2. Export Table Data
                if export_type in ['structure_data', 'data_only']:
                    cursor.execute(f"SELECT * FROM `{table}`")
                    rows = cursor.fetchall()
                    
                    if rows:
                        cols = list(rows[0].keys())
                        col_list = ", ".join([f"`{c}`" for c in cols])
                        
                        # Chunk rows to write batch inserts (speeds up import significantly)
                        chunk_size = 100
                        for idx in range(0, len(rows), chunk_size):
                            chunk = rows[idx:idx+chunk_size]
                            val_strings = []
                            for row in chunk:
                                escaped_vals = [conn.escape(row[c]) for c in cols]
                                val_strings.append(f"({', '.join(escaped_vals)})")
                            
                            yield f"INSERT INTO `{table}` ({col_list}) VALUES\n" + ",\n".join(val_strings) + ";\n"
                        yield "\n"
                    else:
                        yield f"-- (No records found in table `{table}`)\n\n"
                        
            yield "SET FOREIGN_KEY_CHECKS=1;\n"
            
        except Exception as e:
            yield f"\n-- ERROR DURING DUMP GENERATION: {str(e)}\n"
        finally:
            if conn:
                conn.close()
                
    filename = f"{db_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    return Response(
        generate_sql(),
        mimetype="text/plain",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

@data_bp.route('/database/<db_name>/import', methods=['POST'])
def import_db(db_name):
    creds = get_creds()
    if not creds:
        return redirect(url_for('auth_bp.login'))
        
    if 'sql_file' not in request.files:
        flash("No file part uploaded.", "warning")
        return redirect(url_for('data_bp.export_import_view', db_name=db_name))
        
    uploaded_file = request.files['sql_file']
    if uploaded_file.filename == '':
        flash("No file selected for import.", "warning")
        return redirect(url_for('data_bp.export_import_view', db_name=db_name))
        
    if not uploaded_file.filename.endswith('.sql'):
        flash("Only SQL files (.sql) are supported for imports.", "warning")
        return redirect(url_for('data_bp.export_import_view', db_name=db_name))
        
    try:
        sql_content = uploaded_file.read().decode('utf-8', errors='ignore')
        statements = split_sql_script(sql_content)
        
        success_count = 0
        fail_count = 0
        error_msg = None
        
        for stmt in statements:
            if not stmt.strip():
                continue
            res = execute_query(creds, stmt, database=db_name)
            if res['success']:
                success_count += 1
            else:
                fail_count += 1
                error_msg = res['error']
                # Stop on error is the standard MySQL import script behavior
                break
                
        if fail_count > 0:
            flash(f"SQL Import partially completed. Executed: {success_count} statements successfully. Failed statement: {error_msg}", "danger")
        else:
            flash(f"SQL Import completed successfully! {success_count} statements executed.", "success")
            
    except Exception as e:
        flash(f"Failed to read/execute uploaded SQL file: {str(e)}", "danger")
        
    return redirect(url_for('db_bp.view_db', db_name=db_name))
