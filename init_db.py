import pymysql
import sys

def initialize_database():
    connection_params = {
        'host': 'localhost',
        'port': 3307,
        'user': 'root',
        'password': '',
        'charset': 'utf8mb4'
    }
    
    print("Connecting to MySQL server on port 3307...")
    try:
        conn = pymysql.connect(**connection_params)
    except Exception as e:
        print(f"ERROR: Could not connect to MySQL server: {e}")
        print("Please verify that XAMPP MySQL is active and listening on port 3307.")
        sys.exit(1)
        
    try:
        with conn.cursor() as cursor:
            # 1. Create database
            print("Creating database 'employee_management_system'...")
            cursor.execute("CREATE DATABASE IF NOT EXISTS employee_management_system CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
            conn.commit()
            
            # Reconnect directly to the new database
            cursor.execute("USE employee_management_system;")
            
            # Disable foreign key checks temporarily for rebuild
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            
            # Drop tables if they exist to start fresh
            print("Dropping existing tables if any...")
            cursor.execute("DROP TABLE IF EXISTS employee_projects;")
            cursor.execute("DROP TABLE IF EXISTS projects;")
            cursor.execute("DROP TABLE IF EXISTS employees;")
            cursor.execute("DROP TABLE IF EXISTS departments;")
            
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            
            # 2. Create departments table
            print("Creating 'departments' table...")
            cursor.execute("""
                CREATE TABLE departments (
                    department_id   INT             NOT NULL AUTO_INCREMENT,
                    department_name VARCHAR(100)    NOT NULL,
                    location        VARCHAR(100)    NULL,
                    CONSTRAINT pk_departments PRIMARY KEY (department_id)
                ) ENGINE=InnoDB;
            """)
            
            # 3. Create employees table
            print("Creating 'employees' table...")
            cursor.execute("""
                CREATE TABLE employees (
                    employee_id     INT             NOT NULL AUTO_INCREMENT,
                    employee_name   VARCHAR(100)    NOT NULL,
                    email           VARCHAR(100)    NOT NULL UNIQUE,
                    phone           VARCHAR(20)     NULL,
                    salary          DECIMAL(10,2)   NOT NULL,
                    joining_date    DATE            NOT NULL,
                    department_id   INT             NULL,
                    status          BOOLEAN         NOT NULL DEFAULT TRUE,
                    CONSTRAINT pk_employees     PRIMARY KEY (employee_id),
                    CONSTRAINT fk_emp_dept      FOREIGN KEY (department_id)
                                                REFERENCES departments(department_id)
                                                ON DELETE SET NULL
                                                ON UPDATE CASCADE
                ) ENGINE=InnoDB;
            """)
            
            # 4. Create projects table
            print("Creating 'projects' table...")
            cursor.execute("""
                CREATE TABLE projects (
                    project_id      INT             NOT NULL AUTO_INCREMENT,
                    project_name    VARCHAR(100)    NOT NULL,
                    start_date      DATE            NULL,
                    end_date        DATE            NULL,
                    budget          DECIMAL(12,2)   NULL,
                    CONSTRAINT pk_projects PRIMARY KEY (project_id)
                ) ENGINE=InnoDB;
            """)
            
            # 5. Create employee_projects table
            print("Creating 'employee_projects' table...")
            cursor.execute("""
                CREATE TABLE employee_projects (
                    id              INT             NOT NULL AUTO_INCREMENT,
                    employee_id     INT             NOT NULL,
                    project_id      INT             NOT NULL,
                    assigned_date   DATE            NULL,
                    CONSTRAINT pk_employee_projects PRIMARY KEY (id),
                    CONSTRAINT fk_ep_employee       FOREIGN KEY (employee_id)
                                                    REFERENCES employees(employee_id)
                                                    ON DELETE CASCADE
                                                    ON UPDATE CASCADE,
                    CONSTRAINT fk_ep_project        FOREIGN KEY (project_id)
                                                    REFERENCES projects(project_id)
                                                    ON DELETE CASCADE
                                                    ON UPDATE CASCADE
                ) ENGINE=InnoDB;
            """)
            
            conn.commit()
            print("Schema tables created successfully!")
            
            # 6. Seed mock records
            print("Seeding mock departments...")
            cursor.executemany("""
                INSERT INTO departments (department_name, location) VALUES (%s, %s)
            """, [
                ("Engineering", "Floor 4, Block A"),
                ("Sales & Marketing", "Floor 2, Block B"),
                ("Human Resources", "Floor 3, Block A"),
                ("Finance & Payroll", "Floor 3, Block C")
            ])
            
            conn.commit()
            
            # Get department IDs to associate employees correctly
            cursor.execute("SELECT department_id, department_name FROM departments;")
            depts = {row[1]: row[0] for row in cursor.fetchall()}
            
            print("Seeding mock employees...")
            cursor.executemany("""
                INSERT INTO employees (employee_name, email, phone, salary, joining_date, department_id, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [
                ("Alice Henderson", "alice.h@company.com", "+1-555-0101", 95000.00, "2024-02-15", depts["Engineering"], True),
                ("Bob Miller", "bob.m@company.com", "+1-555-0102", 82000.00, "2024-06-10", depts["Engineering"], True),
                ("Charlie Cooper", "charlie.c@company.com", "+1-555-0103", 68000.00, "2025-01-20", depts["Sales & Marketing"], True),
                ("Diana Prince", "diana.p@company.com", "+1-555-0104", 75000.00, "2024-11-01", depts["Human Resources"], True),
                ("Ethan Hunt", "ethan.h@company.com", "+1-555-0105", 110000.00, "2023-05-12", depts["Engineering"], True),
                ("Fiona Gallagher", "fiona.g@company.com", "+1-555-0106", 58000.00, "2025-03-05", depts["Finance & Payroll"], True),
                ("George Clark", "george.c@company.com", "+1-555-0107", 72000.00, "2024-08-18", depts["Sales & Marketing"], False)
            ])
            
            conn.commit()
            
            # Get employee IDs
            cursor.execute("SELECT employee_id, employee_name FROM employees;")
            emps = {row[1]: row[0] for row in cursor.fetchall()}
            
            print("Seeding mock projects...")
            cursor.executemany("""
                INSERT INTO projects (project_name, start_date, end_date, budget)
                VALUES (%s, %s, %s, %s)
            """, [
                ("Project Apollo", "2025-06-01", "2026-03-31", 250000.00),
                ("OmniChannel Portal", "2025-09-15", "2026-08-30", 185000.00),
                ("HR Core Migration", "2026-01-10", "2026-07-15", 75000.00),
                ("Corporate Rebranding", "2026-04-01", "2026-11-30", 120000.00)
            ])
            
            conn.commit()
            
            # Get project IDs
            cursor.execute("SELECT project_id, project_name FROM projects;")
            projs = {row[1]: row[0] for row in cursor.fetchall()}
            
            print("Seeding mock employee-project assignments...")
            cursor.executemany("""
                INSERT INTO employee_projects (employee_id, project_id, assigned_date)
                VALUES (%s, %s, %s)
            """, [
                (emps["Alice Henderson"], projs["Project Apollo"], "2025-05-20"),
                (emps["Bob Miller"], projs["Project Apollo"], "2025-05-25"),
                (emps["Ethan Hunt"], projs["Project Apollo"], "2025-05-20"),
                (emps["Bob Miller"], projs["OmniChannel Portal"], "2025-09-01"),
                (emps["Charlie Cooper"], projs["OmniChannel Portal"], "2025-09-10"),
                (emps["Diana Prince"], projs["HR Core Migration"], "2026-01-05"),
                (emps["Fiona Gallagher"], projs["HR Core Migration"], "2026-01-08")
            ])
            
            conn.commit()
            print("Seeding completed successfully!")
            
    except Exception as e:
        print(f"ERROR executing script: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()
        print("Database initialization finished.")

if __name__ == '__main__':
    initialize_database()
