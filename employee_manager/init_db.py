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
            print("Creating database 'employee_management'...")
            cursor.execute("CREATE DATABASE IF NOT EXISTS employee_management CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
            conn.commit()
            
            # Reconnect directly to the new database
            cursor.execute("USE employee_management;")
            
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
                    email           VARCHAR(100)    NULL UNIQUE,
                    phone           VARCHAR(20)     NULL,
                    salary          DECIMAL(10,2)   NOT NULL,
                    joining_date    DATE            NOT NULL,
                    department_id   INT             NULL,
                    status          BOOLEAN         NULL DEFAULT TRUE,
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
                ("Engineering", "Dhaka"),
                ("Marketing", "Chittagong"),
                ("Human Resources", "Sylhet"),
                ("Finance", "Dhaka"),
                ("Operations", "Khulna"),
                ("Customer Support", "Rajshahi"),
                ("Research & Development", "Dhaka"),
                ("Sales", "Barisal"),
                ("Legal Affairs", "Dhaka"),
                ("Procurement", "Comilla"),
                ("IT Support", "Rangpur"),
                ("Administration", "Mymensingh"),
                ("Business Development", "Dhaka"),
                ("Public Relations", "Sylhet"),
                ("Quality Assurance", "Khulna"),
                ("Security Management", "Chittagong"),
                ("Training & Development", "Rajshahi"),
                ("Data Science", "Dhaka"),
                ("Cloud Infrastructure", "Dhaka"),
                ("Product Management", "Barisal"),
                ("Technical Support", "Comilla"),
                ("Internal Audit", "Sylhet"),
                ("Mobile Development", "Dhaka"),
                ("UI/UX Design", "Khulna"),
                ("Supply Chain", "Rangpur")
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
                ("Tanvir Ahmed", "tanvir.ahmed@company.com", "01712000001", 72000.00, "2022-02-15", depts["Human Resources"], True),
                ("Mehjabin Noor", "mehjabin.noor@company.com", "01712000002", 64000.00, "2021-11-03", depts["Engineering"], True),
                ("Sabbir Hasan", "sabbir.hasan@company.com", "01712000003", 59000.00, "2020-08-12", depts["Operations"], True),
                ("Farzana Kabir", "farzana.kabir@company.com", "01712000004", 81000.00, "2019-04-25", depts["Human Resources"], True),
                ("Rakib Chowdhury", "rakib.chowdhury@company.com", "01712000005", 52000.00, "2023-06-19", depts["Quality Assurance"], True),
                ("Nusrat Jahan", "nusrat.jahan@company.com", "01712000006", 47000.00, "2022-09-10", depts["Security Management"], True),
                ("Imran Hossain", "imran.hossain@company.com", "01712000007", 98000.00, "2018-01-15", depts["Training & Development"], True),
                ("Tania Sultana", "tania.sultana@company.com", "01712000008", 76000.00, "2020-12-01", depts["Technical Support"], True),
                ("Mahmudul Karim", "mahmudul.karim@company.com", "01712000009", 61000.00, "2021-07-21", depts["Legal Affairs"], True),
                ("Rifat Ara", "rifat.ara@company.com", "01712000010", 55000.00, "2022-05-18", depts["Customer Support"], True),
                ("Zamilur Rahman", "zamilur.rahman@company.com", "01712000011", 88000.00, "2019-10-12", depts["Finance"], True),
                ("Sadia Islam", "sadia.islam@company.com", "01712000012", 49000.00, "2023-08-30", depts["Operations"], True),
                ("Arifur Rahman", "arifur.rahman@company.com", "01712000013", 93000.00, "2017-06-01", depts["Engineering"], True),
                ("Jesmin Akter", "jesmin.akter@company.com", "01712000014", 67000.00, "2021-04-14", depts["Sales"], True),
                ("Kamrul Hasan", "kamrul.hasan@company.com", "01712000015", 78000.00, "2020-09-05", depts["Research & Development"], True),
                ("Tasnim Jahan", "tasnim.jahan@company.com", "01712000016", 52000.00, "2022-11-22", depts["Customer Support"], True),
                ("Monirul Islam", "monirul.islam@company.com", "01712000017", 71000.00, "2021-03-10", depts["IT Support"], True),
                ("Sharmin Sultana", "sharmin.sultana@company.com", "01712000018", 83000.00, "2019-12-05", depts["Data Science"], True),
                ("Asif Iqbal", "asif.iqbal@company.com", "01712000019", 58000.00, "2023-02-14", depts["Public Relations"], True),
                ("Dilara Begum", "dilara.begum@company.com", "01712000020", 69000.00, "2020-07-19", depts["Quality Assurance"], True),
                ("Mahbubur Rahman", "mahbubur.rahman@company.com", "01712000021", 105000.00, "2016-03-25", depts["Cloud Infrastructure"], True),
                ("Nasrin Sultana", "nasrin.sultana@company.com", "01712000022", 60000.00, "2022-01-10", depts["Technical Support"], True),
                ("Tareq Aziz", "tareq.aziz@company.com", "01712000023", 74000.00, "2020-10-18", depts["Product Management"], True),
                ("Laila Akhter", "laila.akhter@company.com", "01712000024", 82000.00, "2019-05-15", depts["Internal Audit"], True),
                ("Mustafizur Rahman", "mustafizur.rahman@company.com", "01712000025", 65000.00, "2021-12-01", depts["Supply Chain"], True)
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
                ("Smart Hospital Management", "2024-01-01", "2024-12-31", 550000.00),
                ("E-Commerce ERP System", "2024-02-14", "2025-02-14", 720000.00),
                ("AI Recruitment Assistant", "2024-03-01", "2025-01-31", 410000.00),
                ("Banking Security Upgrade", "2023-11-10", "2024-10-30", 880000.00),
                ("Digital Learning Hub", "2024-04-20", "2025-04-19", 360000.00),
                ("Cloud Migration Project", "2024-05-05", "2025-05-05", 960000.00),
                ("Retail POS Modernization", "2023-12-01", "2024-09-30", 290000.00),
                ("IoT Smart Farming Platform", "2024-06-01", "2025-06-01", 610000.00),
                ("Logistics Tracking System", "2024-01-18", "2024-11-18", 470000.00),
                ("Customer Loyalty App", "2024-02-25", "2025-01-20", 315000.00),
                ("HR Self-Service Portal", "2024-03-12", "2025-03-11", 285000.00),
                ("Data Analytics Warehouse", "2024-04-01", "2025-03-31", 520000.00),
                ("Smart City Dashboard", "2024-05-15", "2025-04-15", 450000.00),
                ("Automated Quality Control", "2024-06-20", "2025-05-20", 380000.00),
                ("Virtual Classroom Platform", "2024-07-01", "2025-06-30", 295000.00),
                ("Fleet Management System", "2024-08-10", "2025-07-10", 510000.00),
                ("Cyber Security Audit", "2024-09-01", "2025-02-28", 175000.00),
                ("E-Learning Content Library", "2024-10-15", "2025-09-15", 220000.00),
                ("Real-time Inventory Portal", "2024-11-01", "2025-10-31", 630000.00),
                ("CRM Integration API", "2024-12-05", "2025-06-05", 140000.00),
                ("Employee Wellness App", "2025-01-10", "2025-12-10", 95000.00),
                ("Blockchain Ledger Proof", "2025-02-01", "2025-11-30", 320000.00),
                ("AI Customer Agent chatbot", "2025-03-01", "2025-08-31", 180000.00),
                ("Content Delivery Network", "2025-04-01", "2026-03-31", 750000.00),
                ("Automated Billing Engine", "2025-05-10", "2026-04-10", 260000.00)
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
                (emps["Tanvir Ahmed"], projs["Smart Hospital Management"], "2024-01-15"),
                (emps["Mehjabin Noor"], projs["Smart Hospital Management"], "2024-01-20"),
                (emps["Sabbir Hasan"], projs["E-Commerce ERP System"], "2024-02-20"),
                (emps["Farzana Kabir"], projs["AI Recruitment Assistant"], "2024-03-10"),
                (emps["Rakib Chowdhury"], projs["Banking Security Upgrade"], "2023-11-20"),
                (emps["Nusrat Jahan"], projs["Digital Learning Hub"], "2024-04-25"),
                (emps["Imran Hossain"], projs["Cloud Migration Project"], "2024-05-15"),
                (emps["Tania Sultana"], projs["Retail POS Modernization"], "2023-12-10"),
                (emps["Mahmudul Karim"], projs["IoT Smart Farming Platform"], "2024-06-10"),
                (emps["Rifat Ara"], projs["Logistics Tracking System"], "2024-01-25"),
                (emps["Zamilur Rahman"], projs["Customer Loyalty App"], "2024-03-01"),
                (emps["Sadia Islam"], projs["HR Self-Service Portal"], "2024-03-20"),
                (emps["Arifur Rahman"], projs["Data Analytics Warehouse"], "2024-04-10"),
                (emps["Jesmin Akter"], projs["Smart City Dashboard"], "2024-05-20"),
                (emps["Kamrul Hasan"], projs["Automated Quality Control"], "2024-07-01"),
                (emps["Tasnim Jahan"], projs["Virtual Classroom Platform"], "2024-07-15"),
                (emps["Monirul Islam"], projs["Fleet Management System"], "2024-08-20"),
                (emps["Sharmin Sultana"], projs["Cyber Security Audit"], "2024-09-05"),
                (emps["Asif Iqbal"], projs["E-Learning Content Library"], "2024-10-20"),
                (emps["Dilara Begum"], projs["Real-time Inventory Portal"], "2024-11-10"),
                (emps["Mahbubur Rahman"], projs["CRM Integration API"], "2024-12-15"),
                (emps["Nasrin Sultana"], projs["Employee Wellness App"], "2025-01-15"),
                (emps["Tareq Aziz"], projs["Blockchain Ledger Proof"], "2025-02-10"),
                (emps["Laila Akhter"], projs["AI Customer Agent chatbot"], "2025-03-10"),
                (emps["Mustafizur Rahman"], projs["Content Delivery Network"], "2025-04-10")
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
