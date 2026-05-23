import unittest
from db_helper import CredentialsCrypto, split_sql_script
from app import app

class TestPySQLManager(unittest.TestCase):
    
    def setUp(self):
        self.secret_key = "test_secret_key_1234"
        self.crypto = CredentialsCrypto(self.secret_key)
        self.app_client = app.test_client()
        app.config['TESTING'] = True

    def test_credentials_crypto(self):
        """Test encryption and decryption of MySQL server login details"""
        original_creds = {
            'host': 'localhost',
            'port': '3307',
            'username': 'root',
            'password': 'safe_password',
            'database': 'test_db'
        }
        
        token = self.crypto.encrypt(original_creds)
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        
        decrypted_creds = self.crypto.decrypt(token)
        self.assertEqual(decrypted_creds['host'], original_creds['host'])
        self.assertEqual(decrypted_creds['port'], original_creds['port'])
        self.assertEqual(decrypted_creds['username'], original_creds['username'])
        self.assertEqual(decrypted_creds['password'], original_creds['password'])
        self.assertEqual(decrypted_creds['database'], original_creds['database'])

    def test_sql_splitter(self):
        """Test separating multi-statement SQL dumps while preserving comments and quotes"""
        sql_script = """
        -- Simple comment
        CREATE TABLE `users` (
            id INT PRIMARY KEY,
            name VARCHAR(50), -- nested comments
            comment TEXT
        );
        # Another line comment
        INSERT INTO `users` VALUES (1, "name;with;semicolons", 'nested;quotes');
        /*
          Block Comment
        */
        SELECT * FROM `users`;
        """
        
        statements = split_sql_script(sql_script)
        self.assertEqual(len(statements), 3)
        
        self.assertTrue(statements[0].startswith("CREATE TABLE `users`"))
        self.assertTrue(statements[1].startswith("INSERT INTO `users`"))
        self.assertTrue(statements[2].startswith("SELECT * FROM `users`"))
        
        # Verify semicolon in string wasn't split
        self.assertIn("name;with;semicolons", statements[1])

    def test_unauthenticated_redirect(self):
        """Test redirect to login page for unauthorized sessions"""
        response = self.app_client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith(url_for_login := '/login'))

if __name__ == '__main__':
    unittest.main()
