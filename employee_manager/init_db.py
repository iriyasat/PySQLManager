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
            
            # 6. Seed new records
            print("Seeding departments...")
            cursor.execute("""
                INSERT INTO departments (department_name, location) VALUES
                ('Human Resources', 'Dhaka'),
                ('Software Development', 'Dhaka'),
                ('Finance', 'Chattogram'),
                ('Marketing', 'Dhaka'),
                ('Customer Support', 'Sylhet'),
                ('Research and Development', 'Gazipur'),
                ('Cyber Security', 'Dhaka'),
                ('Operations', 'Khulna'),
                ('Sales', 'Rajshahi'),
                ('Logistics', 'Narayanganj'),
                ('Administration', 'Cumilla'),
                ('Cloud Infrastructure', 'Dhaka'),
                ('Data Analytics', 'Dhaka'),
                ('Quality Assurance', 'Barishal'),
                ('Networking', 'Rangpur'),
                ('AI Engineering', 'Dhaka'),
                ('Procurement', 'Mymensingh'),
                ('Business Development', 'Dhaka'),
                ('Technical Support', 'Bogura'),
                ('Mobile App Development', 'Dhaka'),
                ('Legal Affairs', 'Dhaka'),
                ('Content Management', 'Sylhet'),
                ('Public Relations', 'Chattogram'),
                ('Product Management', 'Dhaka'),
                ('Training and Development', 'Gazipur');
            """)
            
            print("Seeding employees...")
            cursor.execute("""
                INSERT INTO employees 
                (employee_name, email, phone, salary, joining_date, department_id, status)
                VALUES
                ('Tanvir Hasan', 'tanvir.hasan@grameenit.com', '01711223344', 55000.00, '2022-03-15', 2, TRUE),
                ('Nusrat Jahan', 'nusrat.jahan@banglatech.com', '01822334455', 62000.00, '2021-11-20', 4, TRUE),
                ('Mehedi Rahman', 'mehedi.rahman@robi.com', '01633445566', 48000.00, '2023-01-10', 5, TRUE),
                ('Sadia Islam', 'sadia.islam@waltonbd.com', '01944556677', 70000.00, '2020-06-18', 1, TRUE),
                ('Rakib Ahmed', 'rakib.ahmed@brainstation23.com', '01555667788', 88000.00, '2019-09-25', 16, TRUE),
                ('Farzana Akter', 'farzana.akter@pathao.com', '01766778899', 51000.00, '2022-07-30', 9, TRUE),
                ('Jubayer Hossain', 'jubayer.hossain@beximco.com', '01877889900', 46000.00, '2021-12-11', 3, TRUE),
                ('Sharmin Sultana', 'sharmin.sultana@daraz.com', '01988990011', 75000.00, '2018-05-22', 12, TRUE),
                ('Sabbir Khan', 'sabbir.khan@pridesys.com', '01699001122', 53000.00, '2023-02-14', 14, TRUE),
                ('Tanjina Noor', 'tanjina.noor@sslwireless.com', '01710112233', 69000.00, '2020-08-08', 13, TRUE),
                ('Mahmudul Hasan', 'mahmudul.hasan@shopup.com', '01821223344', 72000.00, '2021-04-17', 18, TRUE),
                ('Nafisa Karim', 'nafisa.karim@technohaven.com', '01932334455', 58000.00, '2022-09-19', 20, TRUE),
                ('Raihan Chowdhury', 'raihan.chowdhury@bjitgroup.com', '01643445566', 93000.00, '2019-01-05', 7, TRUE),
                ('Israt Jahan', 'israt.jahan@datasoft-bd.com', '01754556677', 61000.00, '2020-12-13', 6, TRUE),
                ('Fahim Ahmed', 'fahim.ahmed@grameenphone.com', '01865667788', 66000.00, '2021-03-28', 15, TRUE),
                ('Mariam Sultana', 'mariam.sultana@pickaboo.com', '01976778899', 47000.00, '2023-06-01', 22, TRUE),
                ('Arif Rahman', 'arif.rahman@wedevs.com', '01587889900', 81000.00, '2018-10-10', 2, TRUE),
                ('Tasnia Ahmed', 'tasnia.ahmed@brainstation23.com', '01798990011', 59000.00, '2022-05-05', 24, TRUE),
                ('Shakib Hossain', 'shakib.hossain@kodeeo.com', '01809001122', 54000.00, '2021-08-23', 10, TRUE),
                ('Rifat Karim', 'rifat.karim@revesoft.com', '01910112233', 86000.00, '2019-11-14', 16, TRUE),
                ('Anika Noor', 'anika.noor@sheba.xyz', '01621223344', 52000.00, '2020-04-21', 19, TRUE),
                ('Mizanur Rahman', 'mizanur.rahman@agami.com', '01732334455', 64000.00, '2021-07-09', 11, TRUE),
                ('Afsana Mim', 'afsana.mim@nagad.com', '01843445566', 68000.00, '2022-02-12', 8, TRUE),
                ('Towhid Islam', 'towhid.islam@10minuteschool.com', '01954556677', 57000.00, '2023-03-18', 23, TRUE),
                ('Jannatul Ferdous', 'jannatul.ferdous@bdjobs.com', '01565667788', 49000.00, '2020-10-27', 25, TRUE);
            """)

            print("Seeding projects...")
            cursor.execute("""
                INSERT INTO projects
                (project_name, start_date, end_date, budget)
                VALUES
                ('Smart Payroll System', '2024-01-10', '2024-10-15', 1500000.00),
                ('AI Customer Chatbot', '2023-07-01', '2024-05-30', 2200000.00),
                ('E-Commerce Mobile App', '2024-03-20', '2025-01-10', 3400000.00),
                ('Cloud Migration Project', '2023-09-12', '2024-11-25', 4100000.00),
                ('Cyber Security Audit', '2024-02-01', '2024-06-15', 900000.00),
                ('HR Automation Platform', '2023-11-11', '2024-08-20', 1700000.00),
                ('Digital Banking Solution', '2024-04-18', '2025-02-28', 5200000.00),
                ('Warehouse Management System', '2023-05-05', '2024-03-10', 2600000.00),
                ('Smart Attendance Tracker', '2024-01-25', '2024-09-01', 1200000.00),
                ('Business Intelligence Dashboard', '2023-12-15', '2024-10-10', 3000000.00),
                ('Online Learning Platform', '2024-02-20', '2025-01-05', 2800000.00),
                ('POS System Upgrade', '2023-06-14', '2024-04-17', 1450000.00),
                ('Fleet Tracking System', '2024-05-01', '2025-02-20', 3700000.00),
                ('IoT Energy Monitoring', '2023-08-08', '2024-07-07', 2500000.00),
                ('Corporate Website Redesign', '2024-03-03', '2024-09-12', 800000.00),
                ('ERP Integration', '2023-10-22', '2025-03-30', 6200000.00),
                ('Call Center Optimization', '2024-01-17', '2024-12-19', 1950000.00),
                ('AI Fraud Detection', '2024-04-04', '2025-04-04', 4800000.00),
                ('Data Warehouse Development', '2023-07-21', '2024-11-14', 3500000.00),
                ('Microservices Architecture', '2024-02-11', '2025-05-25', 4100000.00),
                ('Mobile Banking App', '2023-09-29', '2025-01-15', 5600000.00),
                ('Inventory Prediction System', '2024-03-09', '2024-12-28', 2400000.00),
                ('Customer Feedback Analyzer', '2024-05-12', '2025-02-01', 2100000.00),
                ('Virtual Meeting Platform', '2023-11-19', '2024-09-30', 2750000.00),
                ('Digital Document Archive', '2024-01-08', '2024-10-05', 1600000.00);
            """)

            print("Seeding employee-project assignments...")
            cursor.execute("""
                INSERT INTO employee_projects
                (employee_id, project_id, assigned_date)
                VALUES
                (5, 2, '2024-01-15'),
                (1, 1, '2024-02-01'),
                (3, 5, '2024-02-10'),
                (7, 4, '2024-03-05'),
                (10, 10, '2024-03-12'),
                (14, 6, '2024-01-22'),
                (20, 18, '2024-04-14'),
                (2, 15, '2024-02-28'),
                (9, 9, '2024-01-18'),
                (12, 3, '2024-03-30'),
                (17, 20, '2024-04-11'),
                (6, 17, '2024-02-05'),
                (4, 8, '2024-01-25'),
                (8, 19, '2024-03-16'),
                (13, 5, '2024-04-01'),
                (11, 7, '2024-02-13'),
                (18, 11, '2024-03-22'),
                (21, 14, '2024-01-27'),
                (16, 24, '2024-04-07'),
                (15, 13, '2024-03-18'),
                (22, 16, '2024-02-16'),
                (19, 22, '2024-04-20'),
                (23, 21, '2024-01-31'),
                (24, 23, '2024-05-02'),
                (25, 25, '2024-03-09');
            """)
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
