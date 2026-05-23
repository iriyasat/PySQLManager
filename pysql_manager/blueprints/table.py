from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
import urllib.parse
from db_helper import CredentialsCrypto, execute_query

table_bp = Blueprint('table_bp', __name__)

def get_creds():
    crypto = CredentialsCrypto(current_app.secret_key)
    return crypto.decrypt(session.get('creds'))

def get_primary_keys(creds: dict, db_name: str, table_name: str) -> list:
    query = f"SHOW KEYS FROM `{db_name}`.`{table_name}` WHERE Key_name = 'PRIMARY'"
    res = execute_query(creds, query)
    if res['success'] and res['rows']:
        return [row['Column_name'] for row in res['rows']]
    return []

# Create Table Form and Action
@table_bp.route('/database/<db_name>/table/create', methods=['GET', 'POST'])
def create_table(db_name):
    creds = get_creds()
    if not creds:
        return redirect(url_for('auth_bp.login'))
        
    num_fields = int(request.args.get('num_fields', 4))
    
    if request.method == 'POST':
        table_name = request.form.get('table_name', '').strip()
        engine = request.form.get('engine', 'InnoDB')
        collation = request.form.get('collation', 'utf8mb4_general_ci')
        charset = collation.split('_')[0]
        
        if not table_name:
            flash("Table name cannot be empty.", "warning")
            return redirect(url_for('table_bp.create_table', db_name=db_name, num_fields=num_fields))
            
        col_defs = []
        primary_keys = []
        unique_keys = []
        indexes = []
        
        for i in range(num_fields):
            name = request.form.get(f'field_name_{i}', '').strip()
            if not name:
                continue
                
            t = request.form.get(f'field_type_{i}', 'INT')
            length = request.form.get(f'field_length_{i}', '').strip()
            default_type = request.form.get(f'field_default_{i}')
            default_val = request.form.get(f'field_default_value_{i}', '').strip()
            collation_val = request.form.get(f'field_collation_{i}', '')
            attrib = request.form.get(f'field_attribute_{i}', '')
            nullable = request.form.get(f'field_null_{i}') == 'on'
            index = request.form.get(f'field_index_{i}', '')
            ai = request.form.get(f'field_ai_{i}') == 'on'
            
            # Start column sql definition
            col_def = f"`{name}` {t}"
            if length:
                col_def += f"({length})"
                
            if attrib:
                col_def += f" {attrib}"
                
            if not nullable:
                col_def += " NOT NULL"
            else:
                col_def += " NULL"
                
            if default_type == 'USER_DEFINED':
                col_def += f" DEFAULT '{default_val}'"
            elif default_type == 'NULL':
                col_def += " DEFAULT NULL"
            elif default_type == 'CURRENT_TIMESTAMP':
                col_def += " DEFAULT CURRENT_TIMESTAMP"
                
            if ai:
                col_def += " AUTO_INCREMENT"
                
            col_defs.append(col_def)
            
            if index == 'PRIMARY':
                primary_keys.append(f"`{name}`")
            elif index == 'UNIQUE':
                unique_keys.append(name)
            elif index == 'INDEX':
                indexes.append(name)
                
        if not col_defs:
            flash("Table must contain at least one column.", "warning")
            return redirect(url_for('table_bp.create_table', db_name=db_name, num_fields=num_fields))
            
        if primary_keys:
            col_defs.append(f"PRIMARY KEY ({', '.join(primary_keys)})")
            
        # Construct Create Statement
        query = f"CREATE TABLE `{db_name}`.`{table_name}` (\n  " + ",\n  ".join(col_defs) + f"\n) ENGINE={engine} DEFAULT CHARSET={charset} COLLATE={collation};"
        
        # Execute Table Creation
        res = execute_query(creds, query)
        if res['success']:
            # Run index alterations for UNIQUE and INDEX fields
            for col in unique_keys:
                execute_query(creds, f"ALTER TABLE `{db_name}`.`{table_name}` ADD UNIQUE (`{col}`)")
            for col in indexes:
                execute_query(creds, f"ALTER TABLE `{db_name}`.`{table_name}` ADD INDEX (`{col}`)")
                
            flash(f"Table `{table_name}` created successfully!", "success")
            return redirect(url_for('db_bp.view_db', db_name=db_name))
        else:
            flash(f"Error creating table: {res['error']}", "danger")
            
    return render_template('table_create.html', db_name=db_name, num_fields=num_fields)

# Browse Table Records
@table_bp.route('/database/<db_name>/table/<table_name>/browse')
def browse_table(db_name, table_name):
    creds = get_creds()
    if not creds:
        return redirect(url_for('auth_bp.login'))
        
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 25))
    offset = (page - 1) * limit
    
    sort_col = request.args.get('sort')
    sort_dir = request.args.get('dir', 'ASC').upper()
    if sort_dir not in ['ASC', 'DESC']:
        sort_dir = 'ASC'
        
    search_col = request.args.get('search_col', '').strip()
    search_val = request.args.get('search_val', '').strip()
    
    # Query table columns
    schema_res = execute_query(creds, f"SHOW COLUMNS FROM `{db_name}`.`{table_name}`")
    columns = [row['Field'] for row in schema_res['rows']] if schema_res['success'] else []
    
    # Primary keys
    pkeys = get_primary_keys(creds, db_name, table_name)
    
    # Construct queries
    where_clause = ""
    params = []
    if search_col and search_val and search_col in columns:
        where_clause = f" WHERE `{search_col}` LIKE %s"
        params.append(f"%{search_val}%")
        
    # Count rows
    count_query = f"SELECT COUNT(*) AS cnt FROM `{db_name}`.`{table_name}`" + where_clause
    count_res = execute_query(creds, count_query, tuple(params))
    total_rows = count_res['rows'][0]['cnt'] if count_res['success'] else 0
    
    # Query data rows
    order_clause = ""
    if sort_col and sort_col in columns:
        order_clause = f" ORDER BY `{sort_col}` {sort_dir}"
        
    select_query = f"SELECT * FROM `{db_name}`.`{table_name}`" + where_clause + order_clause + " LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    data_res = execute_query(creds, select_query, tuple(params))
    rows = data_res['rows'] if data_res['success'] else []
    
    # Calculate pages
    total_pages = max(1, (total_rows + limit - 1) // limit)
    
    return render_template('table_browse.html',
                           db_name=db_name,
                           table_name=table_name,
                           columns=columns,
                           pkeys=pkeys,
                           rows=rows,
                           page=page,
                           limit=limit,
                           total_rows=total_rows,
                           total_pages=total_pages,
                           sort_col=sort_col,
                           sort_dir=sort_dir,
                           search_col=search_col,
                           search_val=search_val)

# Table Schema Structure View
@table_bp.route('/database/<db_name>/table/<table_name>/structure')
def table_structure(db_name, table_name):
    creds = get_creds()
    if not creds:
        return redirect(url_for('auth_bp.login'))
        
    # Query columns
    cols_query = f"SHOW FULL COLUMNS FROM `{db_name}`.`{table_name}`"
    cols_res = execute_query(creds, cols_query)
    columns = cols_res['rows'] if cols_res['success'] else []
    
    # Query index structures
    idx_query = f"SHOW INDEXES FROM `{db_name}`.`{table_name}`"
    idx_res = execute_query(creds, idx_query)
    indexes = idx_res['rows'] if idx_res['success'] else []
    
    # Query foreign keys
    fk_query = """
        SELECT 
            CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME, UPDATE_RULE, DELETE_RULE
        FROM information_schema.KEY_COLUMN_USAGE k
        JOIN information_schema.REFERENTIAL_CONSTRAINTS r USING (CONSTRAINT_NAME, CONSTRAINT_SCHEMA)
        WHERE k.CONSTRAINT_SCHEMA = %s AND k.TABLE_NAME = %s AND k.REFERENCED_TABLE_NAME IS NOT NULL
    """
    fk_res = execute_query(creds, fk_query, (db_name, table_name))
    foreign_keys = fk_res['rows'] if fk_res['success'] else []
    
    # Database list for foreign key constraint additions
    db_tables_res = execute_query(creds, f"SHOW TABLES FROM `{db_name}`")
    key = f"Tables_in_{db_name}"
    available_tables = [r[key] for r in db_tables_res['rows']] if db_tables_res['success'] else []
    
    return render_template('table_structure.html',
                           db_name=db_name,
                           table_name=table_name,
                           columns=columns,
                           indexes=indexes,
                           foreign_keys=foreign_keys,
                           available_tables=available_tables)

# Add Table Column
@table_bp.route('/database/<db_name>/table/<table_name>/column/add', methods=['POST'])
def add_column(db_name, table_name):
    creds = get_creds()
    col_name = request.form.get('col_name', '').strip()
    col_type = request.form.get('col_type', 'VARCHAR')
    col_length = request.form.get('col_length', '').strip()
    col_null = request.form.get('col_null') == 'on'
    col_default_type = request.form.get('col_default')
    col_default_val = request.form.get('col_default_value', '').strip()
    col_position = request.form.get('col_position', 'LAST')
    col_pos_after = request.form.get('col_pos_after', '')
    
    if not col_name:
        flash("Column name cannot be empty.", "warning")
        return redirect(url_for('table_bp.table_structure', db_name=db_name, table_name=table_name))
        
    query = f"ALTER TABLE `{db_name}`.`{table_name}` ADD COLUMN `{col_name}` {col_type}"
    if col_length:
        query += f"({col_length})"
        
    if not col_null:
        query += " NOT NULL"
    else:
        query += " NULL"
        
    if col_default_type == 'USER_DEFINED':
        query += f" DEFAULT '{col_default_val}'"
    elif col_default_type == 'NULL':
        query += " DEFAULT NULL"
    elif col_default_type == 'CURRENT_TIMESTAMP':
        query += " DEFAULT CURRENT_TIMESTAMP"
        
    if col_position == 'FIRST':
        query += " FIRST"
    elif col_position == 'AFTER' and col_pos_after:
        query += f" AFTER `{col_pos_after}`"
        
    res = execute_query(creds, query)
    if res['success']:
        flash(f"Column `{col_name}` added successfully.", "success")
    else:
        flash(f"Error adding column: {res['error']}", "danger")
        
    return redirect(url_for('table_bp.table_structure', db_name=db_name, table_name=table_name))

# Drop Table Column
@table_bp.route('/database/<db_name>/table/<table_name>/column/drop/<col_name>', methods=['POST'])
def drop_column(db_name, table_name, col_name):
    creds = get_creds()
    query = f"ALTER TABLE `{db_name}`.`{table_name}` DROP COLUMN `{col_name}`"
    res = execute_query(creds, query)
    if res['success']:
        flash(f"Column `{col_name}` dropped successfully.", "success")
    else:
        flash(f"Error dropping column: {res['error']}", "danger")
    return redirect(url_for('table_bp.table_structure', db_name=db_name, table_name=table_name))

# Add Foreign Key Relationship
@table_bp.route('/database/<db_name>/table/<table_name>/fk/add', methods=['POST'])
def add_foreign_key(db_name, table_name):
    creds = get_creds()
    constraint_name = request.form.get('constraint_name', '').strip()
    column_name = request.form.get('column_name')
    ref_table = request.form.get('ref_table')
    ref_column = request.form.get('ref_column')
    on_delete = request.form.get('on_delete', 'RESTRICT')
    on_update = request.form.get('on_update', 'RESTRICT')
    
    if not constraint_name:
        # Generate random unique name
        import time
        constraint_name = f"fk_{table_name}_{column_name}_{int(time.time())}"
        
    query = f"ALTER TABLE `{db_name}`.`{table_name}` ADD CONSTRAINT `{constraint_name}` FOREIGN KEY (`{column_name}`) REFERENCES `{db_name}`.`{ref_table}` (`{ref_column}`) ON DELETE {on_delete} ON UPDATE {on_update}"
    res = execute_query(creds, query)
    if res['success']:
        flash(f"Foreign Key `{constraint_name}` created successfully.", "success")
    else:
        flash(f"Error adding foreign key constraint: {res['error']}", "danger")
    return redirect(url_for('table_bp.table_structure', db_name=db_name, table_name=table_name))

# Drop Foreign Key Constraint
@table_bp.route('/database/<db_name>/table/<table_name>/fk/drop/<fk_name>', methods=['POST'])
def drop_foreign_key(db_name, table_name, fk_name):
    creds = get_creds()
    query = f"ALTER TABLE `{db_name}`.`{table_name}` DROP FOREIGN KEY `{fk_name}`"
    res = execute_query(creds, query)
    if res['success']:
        # Also drop the corresponding index that MySQL created automatically if desired, 
        # but dropping the foreign key constraint is the main goal.
        flash(f"Foreign Key `{fk_name}` dropped successfully.", "success")
    else:
        flash(f"Error dropping foreign key constraint: {res['error']}", "danger")
    return redirect(url_for('table_bp.table_structure', db_name=db_name, table_name=table_name))

# Insert or Edit Row
@table_bp.route('/database/<db_name>/table/<table_name>/insert', methods=['GET', 'POST'])
def insert_row(db_name, table_name):
    creds = get_creds()
    if not creds:
        return redirect(url_for('auth_bp.login'))
        
    # Get columns details
    schema_res = execute_query(creds, f"SHOW FULL COLUMNS FROM `{db_name}`.`{table_name}`")
    columns = schema_res['rows'] if schema_res['success'] else []
    
    # Check if we are in EDIT mode
    is_edit = False
    edit_where = {}
    row_data = {}
    
    edit_pk_params = request.args.to_dict()
    # Remove standard routing arguments
    edit_pk_params.pop('db_name', None)
    edit_pk_params.pop('table_name', None)
    
    if edit_pk_params:
        is_edit = True
        edit_where = edit_pk_params
        
        # Build SELECT WHERE statement to retrieve the existing row
        where_parts = []
        params = []
        for k, v in edit_where.items():
            where_parts.append(f"`{k}` = %s")
            params.append(v)
            
        select_query = f"SELECT * FROM `{db_name}`.`{table_name}` WHERE " + " AND ".join(where_parts) + " LIMIT 1"
        row_res = execute_query(creds, select_query, tuple(params))
        if row_res['success'] and row_res['rows']:
            row_data = row_res['rows'][0]
        else:
            flash("Could not find the requested record for editing.", "warning")
            return redirect(url_for('table_bp.browse_table', db_name=db_name, table_name=table_name))
            
    if request.method == 'POST':
        # Read form inputs
        fields = []
        values = []
        
        for col in columns:
            col_name = col['Field']
            val = request.form.get(f'val_{col_name}')
            is_null = request.form.get(f'null_{col_name}') == 'on'
            
            # If auto increment and empty, omit it from insert list to let database generate it
            if col['Extra'] == 'auto_increment' and not val and not is_edit:
                continue
                
            fields.append(f"`{col_name}`")
            if is_null:
                values.append(None)
            else:
                values.append(val)
                
        if is_edit:
            # Construct UPDATE query
            update_parts = []
            update_params = []
            for col_name_raw, val_val in zip(fields, values):
                update_parts.append(f"{col_name_raw} = %s")
                update_params.append(val_val)
                
            where_parts = []
            for k, v in edit_where.items():
                where_parts.append(f"`{k}` = %s")
                update_params.append(v)
                
            query = f"UPDATE `{db_name}`.`{table_name}` SET " + ", ".join(update_parts) + " WHERE " + " AND ".join(where_parts)
            res = execute_query(creds, query, tuple(update_params))
            if res['success']:
                flash("Record updated successfully.", "success")
                return redirect(url_for('table_bp.browse_table', db_name=db_name, table_name=table_name))
            else:
                flash(f"Error updating record: {res['error']}", "danger")
        else:
            # Construct INSERT query
            placeholders = ", ".join(["%s"] * len(values))
            query = f"INSERT INTO `{db_name}`.`{table_name}` ({', '.join(fields)}) VALUES ({placeholders})"
            res = execute_query(creds, query, tuple(values))
            if res['success']:
                flash("Record inserted successfully.", "success")
                return redirect(url_for('table_bp.browse_table', db_name=db_name, table_name=table_name))
            else:
                flash(f"Error inserting record: {res['error']}", "danger")
                
    return render_template('table_insert.html',
                           db_name=db_name,
                           table_name=table_name,
                           columns=columns,
                           is_edit=is_edit,
                           row_data=row_data)

# Delete Row
@table_bp.route('/database/<db_name>/table/<table_name>/delete-row', methods=['POST'])
def delete_row(db_name, table_name):
    creds = get_creds()
    if not creds:
        return redirect(url_for('auth_bp.login'))
        
    # Read query parameters to identify the row (usually primary keys)
    row_identifiers = request.form.to_dict()
    
    where_parts = []
    params = []
    for k, v in row_identifiers.items():
        where_parts.append(f"`{k}` = %s")
        params.append(v)
        
    if not where_parts:
        flash("Failed to delete record: No unique identifiers provided.", "warning")
        return redirect(url_for('table_bp.browse_table', db_name=db_name, table_name=table_name))
        
    query = f"DELETE FROM `{db_name}`.`{table_name}` WHERE " + " AND ".join(where_parts) + " LIMIT 1"
    res = execute_query(creds, query, tuple(params))
    if res['success']:
        flash("Record deleted successfully.", "success")
    else:
        flash(f"Error deleting record: {res['error']}", "danger")
        
    return redirect(url_for('table_bp.browse_table', db_name=db_name, table_name=table_name))

# Table Operations (Rename, Copy, Truncate, Drop, Alter Engine)
@table_bp.route('/database/<db_name>/table/<table_name>/operations', methods=['GET', 'POST'])
def table_operations(db_name, table_name):
    creds = get_creds()
    if not creds:
        return redirect(url_for('auth_bp.login'))
        
    # Query active table details
    status_query = f"SHOW TABLE STATUS FROM `{db_name}` LIKE '{table_name}'"
    status_res = execute_query(creds, status_query)
    table_status = status_res['rows'][0] if status_res['success'] and status_res['rows'] else {}
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'rename':
            new_name = request.form.get('new_name', '').strip()
            if not new_name:
                flash("New table name cannot be empty.", "warning")
            else:
                query = f"RENAME TABLE `{db_name}`.`{table_name}` TO `{db_name}`.`{new_name}`"
                res = execute_query(creds, query)
                if res['success']:
                    flash(f"Table `{table_name}` renamed to `{new_name}` successfully.", "success")
                    return redirect(url_for('table_bp.browse_table', db_name=db_name, table_name=new_name))
                else:
                    flash(f"Error renaming table: {res['error']}", "danger")
                    
        elif action == 'copy':
            copy_name = request.form.get('copy_name', '').strip()
            copy_type = request.form.get('copy_type', 'structure_data')
            
            if not copy_name:
                flash("Copy table name cannot be empty.", "warning")
            else:
                # 1. Copy structure
                struct_query = f"CREATE TABLE `{db_name}`.`{copy_name}` LIKE `{db_name}`.`{table_name}`"
                res1 = execute_query(creds, struct_query)
                if res1['success']:
                    if copy_type == 'structure_data':
                        # 2. Copy data
                        data_query = f"INSERT INTO `{db_name}`.`{copy_name}` SELECT * FROM `{db_name}`.`{table_name}`"
                        res2 = execute_query(creds, data_query)
                        if res2['success']:
                            flash(f"Table `{table_name}` structure and data copied to `{copy_name}` successfully.", "success")
                        else:
                            flash(f"Table structure copied, but data copying failed: {res2['error']}", "warning")
                    else:
                        flash(f"Table structure copied to `{copy_name}` successfully.", "success")
                    return redirect(url_for('table_bp.browse_table', db_name=db_name, table_name=copy_name))
                else:
                    flash(f"Error copying table structure: {res1['error']}", "danger")
                    
        elif action == 'alter_options':
            new_engine = request.form.get('engine', 'InnoDB')
            new_collation = request.form.get('collation', 'utf8mb4_general_ci')
            new_charset = new_collation.split('_')[0]
            auto_inc = request.form.get('auto_increment', '').strip()
            
            queries = [
                f"ALTER TABLE `{db_name}`.`{table_name}` ENGINE = {new_engine}",
                f"ALTER TABLE `{db_name}`.`{table_name}` CONVERT TO CHARACTER SET {new_charset} COLLATE {new_collation}"
            ]
            if auto_inc:
                queries.append(f"ALTER TABLE `{db_name}`.`{table_name}` AUTO_INCREMENT = {int(auto_inc)}")
                
            errors = []
            for q in queries:
                res = execute_query(creds, q)
                if not res['success']:
                    errors.append(res['error'])
                    
            if not errors:
                flash("Table options updated successfully.", "success")
            else:
                flash(f"Some updates failed: {', '.join(errors)}", "danger")
                
        elif action == 'truncate':
            query = f"TRUNCATE TABLE `{db_name}`.`{table_name}`"
            res = execute_query(creds, query)
            if res['success']:
                flash(f"Table `{table_name}` truncated successfully (all rows deleted).", "success")
                return redirect(url_for('table_bp.browse_table', db_name=db_name, table_name=table_name))
            else:
                flash(f"Error truncating table: {res['error']}", "danger")
                
        elif action == 'drop':
            query = f"DROP TABLE `{db_name}`.`{table_name}`"
            res = execute_query(creds, query)
            if res['success']:
                flash(f"Table `{table_name}` dropped successfully.", "success")
                return redirect(url_for('db_bp.view_db', db_name=db_name))
            else:
                flash(f"Error dropping table: {res['error']}", "danger")
                
    return render_template('table_operations.html',
                           db_name=db_name,
                           table_name=table_name,
                           table_status=table_status)
