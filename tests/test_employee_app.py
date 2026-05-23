import unittest
from employee_app import app, execute_query

class TestEmployeeManagementSystem(unittest.TestCase):
    
    def setUp(self):
        self.app_client = app.test_client()
        app.config['TESTING'] = True

    def test_dashboard_view(self):
        """Test home dashboard overview stats load correctly"""
        response = self.app_client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Check if dashboard contains major dashboard texts
        html = response.data.decode('utf-8')
        self.assertIn("HR Core Portal", html)
        self.assertIn("Dashboard Overview", html)
        self.assertIn("Total Staff", html)
        self.assertIn("Payroll Commitment", html)

    def test_employees_list(self):
        """Test employees directory loads seeded records"""
        response = self.app_client.get('/employees')
        self.assertEqual(response.status_code, 200)
        
        html = response.data.decode('utf-8')
        self.assertIn("Alice Henderson", html)
        self.assertIn("alice.h@company.com", html)
        self.assertIn("Bob Miller", html)
        self.assertIn("Engineering", html)

    def test_departments_list(self):
        """Test departments list view contains seeded entries"""
        response = self.app_client.get('/departments')
        self.assertEqual(response.status_code, 200)
        
        html = response.data.decode('utf-8')
        self.assertIn("Engineering", html)
        self.assertIn("Sales &amp; Marketing", html)
        self.assertIn("Floor 4, Block A", html)

    def test_projects_list(self):
        """Test projects timelines view contains budgeted projects"""
        response = self.app_client.get('/projects')
        self.assertEqual(response.status_code, 200)
        
        html = response.data.decode('utf-8')
        self.assertIn("Project Apollo", html)
        self.assertIn("OmniChannel Portal", html)

    def test_add_and_delete_employee(self):
        """Test complete CRUD lifecycle by adding and then removing an employee record"""
        # 1. Post new employee details
        payload = {
            'employee_name': 'Test Integration User',
            'email': 'test.integration@company.com',
            'phone': '+1-999-1234',
            'salary': '85000.00',
            'joining_date': '2026-05-15',
            'department_id': '',  # Unassigned
            'status': 'on'
        }
        response = self.app_client.post('/employee/add', data=payload, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify employee exists in list
        html = response.data.decode('utf-8')
        self.assertIn("Test Integration User", html)
        self.assertIn("test.integration@company.com", html)
        
        # Query database to find the employee_id
        db_res = execute_query("SELECT employee_id FROM employees WHERE email = %s", ('test.integration@company.com',), fetch='one')
        self.assertTrue(db_res['success'])
        self.assertIsNotNone(db_res['data'])
        emp_id = db_res['data']['employee_id']
        
        # 2. Delete the created employee
        del_response = self.app_client.post(f'/employee/delete/{emp_id}', follow_redirects=True)
        self.assertEqual(del_response.status_code, 200)
        
        # Verify employee is removed from directory listing
        html_del = del_response.data.decode('utf-8')
        self.assertNotIn("Test Integration User", html_del)

if __name__ == '__main__':
    unittest.main()
