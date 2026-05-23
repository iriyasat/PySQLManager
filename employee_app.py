import logging
from flask import Flask, render_template, request, redirect, url_for, flash
import pymysql
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder='employee_templates',
    static_folder='employee_static',
    static_url_path='/employee_static'
)
app.secret_key = 'employee_management_system_secure_secret_key_1012'

def get_db_connection():
    """
    Establishes a connection to the employee_management_system database on port 3307.
    """
    return pymysql.connect(
        host='localhost',
        port=3307,
        user='root',
        password='',
        database='employee_management_system',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def execute_query(query: str, params: tuple = None, fetch: str = 'all'):
    """
    Utility helper to execute queries and manage connection closing safely.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if fetch == 'all':
                result = cursor.fetchall()
            elif fetch == 'one':
                result = cursor.fetchone()
            else:
                result = cursor.rowcount
            conn.commit()
            return {'success': True, 'data': result, 'error': None}
    except pymysql.MySQLError as e:
        if conn:
            conn.rollback()
        error_msg = f"({e.args[0]}) {e.args[1]}" if len(e.args) > 1 else str(e)
        logger.error(f"Database Error: {error_msg} in query: {query}")
        return {'success': False, 'data': None, 'error': error_msg}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"General Error: {e} in query: {query}")
        return {'success': False, 'data': None, 'error': str(e)}
    finally:
        if conn:
            conn.close()

# 1. Home Dashboard
@app.route('/')
def dashboard():
    # Metrics
    emp_cnt = execute_query("SELECT COUNT(*) AS cnt FROM employees", fetch='one')
    dept_cnt = execute_query("SELECT COUNT(*) AS cnt FROM departments", fetch='one')
    proj_cnt = execute_query("SELECT COUNT(*) AS cnt FROM projects", fetch='one')
    budget_sum = execute_query("SELECT SUM(budget) AS budget FROM projects", fetch='one')
    payroll_sum = execute_query("SELECT SUM(salary) AS total FROM employees WHERE status = 1", fetch='one')
    
    metrics = {
        'employees': emp_cnt['data']['cnt'] if emp_cnt['success'] else 0,
        'departments': dept_cnt['data']['cnt'] if dept_cnt['success'] else 0,
        'projects': proj_cnt['data']['cnt'] if proj_cnt['success'] else 0,
        'budget': budget_sum['data']['budget'] if budget_sum['success'] and budget_sum['data']['budget'] is not None else 0.0,
        'payroll': payroll_sum['data']['total'] if payroll_sum['success'] and payroll_sum['data']['total'] is not None else 0.0
    }
    
    # Department load distribution (active employees)
    dept_dist_query = """
        SELECT d.department_name, COUNT(e.employee_id) AS emp_count 
        FROM departments d
        LEFT JOIN employees e ON d.department_id = e.department_id AND e.status = 1
        GROUP BY d.department_id, d.department_name
        ORDER BY emp_count DESC;
    """
    dept_dist = execute_query(dept_dist_query)
    dept_distribution = dept_dist['data'] if dept_dist['success'] else []
    
    # Recent hires (last 5)
    recent_hires_query = """
        SELECT e.employee_name, d.department_name, e.joining_date 
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.department_id
        ORDER BY e.joining_date DESC
        LIMIT 5;
    """
    recent_res = execute_query(recent_hires_query)
    recent_hires = recent_res['data'] if recent_res['success'] else []
    
    # Projects timelines
    proj_timeline_query = """
        SELECT project_name, start_date, end_date, budget,
               (SELECT COUNT(*) FROM employee_projects ep WHERE ep.project_id = p.project_id) AS member_count
        FROM projects p
        ORDER BY end_date ASC
        LIMIT 4;
    """
    timeline_res = execute_query(proj_timeline_query)
    projects_timeline = timeline_res['data'] if timeline_res['success'] else []
    
    return render_template('index.html',
                           metrics=metrics,
                           dept_distribution=dept_distribution,
                           recent_hires=recent_hires,
                           projects_timeline=projects_timeline)

# 2. Employees View & CRUD
@app.route('/employees')
def employees_list():
    dept_filter = request.args.get('department_id', '')
    status_filter = request.args.get('status', '')
    search_q = request.args.get('q', '').strip()
    
    # Base query
    query = """
        SELECT e.employee_id, e.employee_name, e.email, e.phone, e.salary, e.joining_date, e.status, d.department_name, d.department_id
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.department_id
    """
    where_clauses = []
    params = []
    
    if dept_filter:
        where_clauses.append("e.department_id = %s")
        params.append(int(dept_filter))
    if status_filter != '':
        where_clauses.append("e.status = %s")
        params.append(int(status_filter))
    if search_q:
        where_clauses.append("(e.employee_name LIKE %s OR e.email LIKE %s OR e.phone LIKE %s)")
        q_wildcard = f"%{search_q}%"
        params.extend([q_wildcard, q_wildcard, q_wildcard])
        
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
        
    query += " ORDER BY e.employee_name ASC"
    
    emp_res = execute_query(query, tuple(params) if params else None)
    employees = emp_res['data'] if emp_res['success'] else []
    
    # Fetch departments for filter dropdown
    depts_res = execute_query("SELECT department_id, department_name FROM departments ORDER BY department_name ASC")
    departments = depts_res['data'] if depts_res['success'] else []
    
    return render_template('employees.html',
                           employees=employees,
                           departments=departments,
                           selected_dept=dept_filter,
                           selected_status=status_filter,
                           search_q=search_q)

@app.route('/employee/add', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        name = request.form.get('employee_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip() or None
        salary = request.form.get('salary', '0.00').strip()
        joining_date = request.form.get('joining_date', '').strip()
        dept_id = request.form.get('department_id', '').strip() or None
        status = 1 if request.form.get('status') == 'on' else 0
        
        insert_query = """
            INSERT INTO employees (employee_name, email, phone, salary, joining_date, department_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        res = execute_query(insert_query, (name, email, phone, salary, joining_date, dept_id, status), fetch='count')
        
        if res['success']:
            flash(f"Employee '{name}' added successfully!", "success")
            return redirect(url_for('employees_list'))
        else:
            flash(f"Error adding employee: {res['error']}", "danger")
            
    # Fetch departments for select list
    depts_res = execute_query("SELECT department_id, department_name FROM departments ORDER BY department_name ASC")
    departments = depts_res['data'] if depts_res['success'] else []
    
    return render_template('employee_form.html',
                           is_edit=False,
                           departments=departments,
                           employee={})

@app.route('/employee/edit/<int:emp_id>', methods=['GET', 'POST'])
def edit_employee(emp_id):
    if request.method == 'POST':
        name = request.form.get('employee_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip() or None
        salary = request.form.get('salary', '0.00').strip()
        joining_date = request.form.get('joining_date', '').strip()
        dept_id = request.form.get('department_id', '').strip() or None
        status = 1 if request.form.get('status') == 'on' else 0
        
        update_query = """
            UPDATE employees 
            SET employee_name=%s, email=%s, phone=%s, salary=%s, joining_date=%s, department_id=%s, status=%s
            WHERE employee_id=%s
        """
        res = execute_query(update_query, (name, email, phone, salary, joining_date, dept_id, status, emp_id), fetch='count')
        
        if res['success']:
            flash(f"Employee '{name}' updated successfully.", "success")
            return redirect(url_for('employees_list'))
        else:
            flash(f"Error updating employee: {res['error']}", "danger")
            
    # Fetch current details
    emp_res = execute_query("SELECT * FROM employees WHERE employee_id = %s", (emp_id,), fetch='one')
    employee = emp_res['data'] if emp_res['success'] else None
    
    if not employee:
        flash("Employee not found.", "warning")
        return redirect(url_for('employees_list'))
        
    # Fetch departments for select list
    depts_res = execute_query("SELECT department_id, department_name FROM departments ORDER BY department_name ASC")
    departments = depts_res['data'] if depts_res['success'] else []
    
    return render_template('employee_form.html',
                           is_edit=True,
                           departments=departments,
                           employee=employee)

@app.route('/employee/delete/<int:emp_id>', methods=['POST'])
def delete_employee(emp_id):
    res = execute_query("DELETE FROM employees WHERE employee_id = %s", (emp_id,), fetch='count')
    if res['success']:
        flash("Employee record removed successfully.", "success")
    else:
        flash(f"Error deleting employee: {res['error']}", "danger")
    return redirect(url_for('employees_list'))

@app.route('/employee/toggle-status/<int:emp_id>', methods=['POST'])
def toggle_employee_status(emp_id):
    emp_res = execute_query("SELECT status, employee_name FROM employees WHERE employee_id = %s", (emp_id,), fetch='one')
    if emp_res['success'] and emp_res['data']:
        new_status = 0 if emp_res['data']['status'] else 1
        name = emp_res['data']['employee_name']
        execute_query("UPDATE employees SET status = %s WHERE employee_id = %s", (new_status, emp_id), fetch='count')
        status_txt = "active" if new_status else "inactive"
        flash(f"Employee '{name}' status set to {status_txt}.", "success")
    return redirect(url_for('employees_list'))

# 3. Departments View & CRUD
@app.route('/departments')
def departments_list():
    query = """
        SELECT d.department_id, d.department_name, d.location, 
               COUNT(e.employee_id) AS head_count, 
               COALESCE(ROUND(AVG(e.salary), 2), 0.00) AS avg_salary
        FROM departments d
        LEFT JOIN employees e ON d.department_id = e.department_id AND e.status = 1
        GROUP BY d.department_id, d.department_name, d.location
        ORDER BY d.department_name ASC;
    """
    res = execute_query(query)
    departments = res['data'] if res['success'] else []
    return render_template('departments.html', departments=departments)

@app.route('/department/add', methods=['GET', 'POST'])
def add_department():
    if request.method == 'POST':
        name = request.form.get('department_name', '').strip()
        location = request.form.get('location', '').strip() or None
        
        insert_query = "INSERT INTO departments (department_name, location) VALUES (%s, %s)"
        res = execute_query(insert_query, (name, location), fetch='count')
        
        if res['success']:
            flash(f"Department '{name}' created successfully!", "success")
            return redirect(url_for('departments_list'))
        else:
            flash(f"Error creating department: {res['error']}", "danger")
            
    return render_template('department_form.html', is_edit=False, department={})

@app.route('/department/edit/<int:dept_id>', methods=['GET', 'POST'])
def edit_department(dept_id):
    if request.method == 'POST':
        name = request.form.get('department_name', '').strip()
        location = request.form.get('location', '').strip() or None
        
        update_query = "UPDATE departments SET department_name=%s, location=%s WHERE department_id=%s"
        res = execute_query(update_query, (name, location, dept_id), fetch='count')
        
        if res['success']:
            flash(f"Department '{name}' updated successfully.", "success")
            return redirect(url_for('departments_list'))
        else:
            flash(f"Error updating department: {res['error']}", "danger")
            
    dept_res = execute_query("SELECT * FROM departments WHERE department_id = %s", (dept_id,), fetch='one')
    department = dept_res['data'] if dept_res['success'] else None
    
    if not department:
        flash("Department not found.", "warning")
        return redirect(url_for('departments_list'))
        
    return render_template('department_form.html', is_edit=True, department=department)

@app.route('/department/delete/<int:dept_id>', methods=['POST'])
def delete_department(dept_id):
    res = execute_query("DELETE FROM departments WHERE department_id = %s", (dept_id,), fetch='count')
    if res['success']:
        flash("Department dropped successfully. Assigned employees have department reset to NULL.", "success")
    else:
        flash(f"Error deleting department: {res['error']}", "danger")
    return redirect(url_for('departments_list'))

# 4. Projects View & CRUD
@app.route('/projects')
def projects_list():
    query = """
        SELECT p.project_id, p.project_name, p.start_date, p.end_date, p.budget, 
               COUNT(ep.employee_id) AS member_count,
               COALESCE(SUM(e.salary), 0.00) AS resources_cost
        FROM projects p
        LEFT JOIN employee_projects ep ON p.project_id = ep.project_id
        LEFT JOIN employees e ON ep.employee_id = e.employee_id
        GROUP BY p.project_id, p.project_name, p.start_date, p.end_date, p.budget
        ORDER BY p.project_name ASC;
    """
    res = execute_query(query)
    projects = res['data'] if res['success'] else []
    
    # Calculate timeline progress for each project
    today = datetime.date.today()
    for proj in projects:
        start = proj.get('start_date')
        end = proj.get('end_date')
        
        if start and end:
            if today < start:
                proj['progress'] = 0
            elif today > end:
                proj['progress'] = 100
            else:
                total_days = (end - start).days
                elapsed_days = (today - start).days
                proj['progress'] = int((elapsed_days / total_days) * 100) if total_days > 0 else 0
        else:
            proj['progress'] = 0
            
    return render_template('projects.html', projects=projects)

@app.route('/project/add', methods=['GET', 'POST'])
def add_project():
    if request.method == 'POST':
        name = request.form.get('project_name', '').strip()
        start = request.form.get('start_date', '').strip() or None
        end = request.form.get('end_date', '').strip() or None
        budget = request.form.get('budget', '0.00').strip() or None
        
        insert_query = "INSERT INTO projects (project_name, start_date, end_date, budget) VALUES (%s, %s, %s, %s)"
        res = execute_query(insert_query, (name, start, end, budget), fetch='count')
        
        if res['success']:
            flash(f"Project '{name}' established successfully!", "success")
            return redirect(url_for('projects_list'))
        else:
            flash(f"Error creating project: {res['error']}", "danger")
            
    return render_template('project_form.html', is_edit=False, project={})

@app.route('/project/edit/<int:proj_id>', methods=['GET', 'POST'])
def edit_project(proj_id):
    if request.method == 'POST':
        name = request.form.get('project_name', '').strip()
        start = request.form.get('start_date', '').strip() or None
        end = request.form.get('end_date', '').strip() or None
        budget = request.form.get('budget', '0.00').strip() or None
        
        update_query = "UPDATE projects SET project_name=%s, start_date=%s, end_date=%s, budget=%s WHERE project_id=%s"
        res = execute_query(update_query, (name, start, end, budget, proj_id), fetch='count')
        
        if res['success']:
            flash(f"Project '{name}' updated successfully.", "success")
            return redirect(url_for('projects_list'))
        else:
            flash(f"Error updating project: {res['error']}", "danger")
            
    proj_res = execute_query("SELECT * FROM projects WHERE project_id = %s", (proj_id,), fetch='one')
    project = proj_res['data'] if proj_res['success'] else None
    
    if not project:
        flash("Project not found.", "warning")
        return redirect(url_for('projects_list'))
        
    return render_template('project_form.html', is_edit=True, project=project)

@app.route('/project/delete/<int:proj_id>', methods=['POST'])
def delete_project(proj_id):
    res = execute_query("DELETE FROM projects WHERE project_id = %s", (proj_id,), fetch='count')
    if res['success']:
        flash("Project dropped successfully.", "success")
    else:
        flash(f"Error deleting project: {res['error']}", "danger")
    return redirect(url_for('projects_list'))

# 5. Assignments Manager
@app.route('/assignments')
def assignments_view():
    # Fetch projects and their details
    proj_query = """
        SELECT p.project_id, p.project_name, p.budget, COUNT(ep.employee_id) AS staff_count
        FROM projects p
        LEFT JOIN employee_projects ep ON p.project_id = ep.project_id
        GROUP BY p.project_id, p.project_name, p.budget;
    """
    proj_res = execute_query(proj_query)
    projects = proj_res['data'] if proj_res['success'] else []
    
    # Query staff allocated on each project
    alloc_query = """
        SELECT ep.id, ep.employee_id, ep.project_id, ep.assigned_date, e.employee_name, e.email, d.department_name
        FROM employee_projects ep
        JOIN employees e ON ep.employee_id = e.employee_id
        LEFT JOIN departments d ON e.department_id = d.department_id
        ORDER BY ep.assigned_date DESC;
    """
    alloc_res = execute_query(alloc_query)
    allocations = alloc_res['data'] if alloc_res['success'] else []
    
    # Group allocations by project_id
    project_assignments = {}
    for alloc in allocations:
        p_id = alloc['project_id']
        if p_id not in project_assignments:
            project_assignments[p_id] = []
        project_assignments[p_id].append(alloc)
        
    # Get active employees lists for form options
    emp_options_res = execute_query("SELECT employee_id, employee_name, email FROM employees WHERE status = 1 ORDER BY employee_name ASC")
    employees = emp_options_res['data'] if emp_options_res['success'] else []
    
    return render_template('assignments.html',
                           projects=projects,
                           project_assignments=project_assignments,
                           employees=employees)

@app.route('/assignment/add', methods=['POST'])
def add_assignment():
    emp_id = request.form.get('employee_id')
    proj_id = request.form.get('project_id')
    assigned_date = request.form.get('assigned_date', '').strip() or datetime.date.today().strftime('%Y-%m-%d')
    
    # Verify unique constraint
    check_query = "SELECT id FROM employee_projects WHERE employee_id = %s AND project_id = %s"
    check_res = execute_query(check_query, (emp_id, proj_id), fetch='one')
    
    if check_res['success'] and check_res['data']:
        flash("Employee is already assigned to this project.", "warning")
        return redirect(url_for('assignments_view'))
        
    insert_query = """
        INSERT INTO employee_projects (employee_id, project_id, assigned_date)
        VALUES (%s, %s, %s)
    """
    res = execute_query(insert_query, (emp_id, proj_id, assigned_date), fetch='count')
    if res['success']:
        flash("Employee allocated to project successfully.", "success")
    else:
        flash(f"Error assigning employee: {res['error']}", "danger")
        
    return redirect(url_for('assignments_view'))

@app.route('/assignment/delete/<int:alloc_id>', methods=['POST'])
def delete_assignment(alloc_id):
    res = execute_query("DELETE FROM employee_projects WHERE id = %s", (alloc_id,), fetch='count')
    if res['success']:
        flash("Employee unallocated from project.", "success")
    else:
        flash(f"Error deleting allocation: {res['error']}", "danger")
    return redirect(url_for('assignments_view'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
