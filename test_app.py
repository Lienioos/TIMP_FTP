import unittest
from app import app, get_users, save_users, get_user_by_username, hash_password, USERS_FILE
import json
import os
import tempfile
import time

class TestApp(unittest.TestCase):
    def setUp(self):
        global USERS_FILE
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        self.test_users_file = tempfile.NamedTemporaryFile(delete=False)
        with open(self.test_users_file.name, 'w') as f:
            json.dump([], f)
        
        self.original_users_file = USERS_FILE
        USERS_FILE = self.test_users_file.name
        
        save_users([])

    def tearDown(self):
        global USERS_FILE
        USERS_FILE = self.original_users_file
        self.test_users_file.close()
        time.sleep(0.1)
        try:
            os.unlink(self.test_users_file.name)
        except PermissionError:
            pass  

    def test_register_page(self):
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'\xd0\xa0\xd0\xb5\xd0\xb3\xd0\xb8\xd1\x81\xd1\x82\xd1\x80\xd0\xb0\xd1\x86\xd0\xb8\xd1\x8f', response.data)

    def test_register_success(self):
        response = self.client.post('/register', data={
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'\xd0\x92\xd0\xbe\xd0\xb9\xd1\x82\xd0\xb8', response.data)  # Should redirect to login page
        
        users = get_users()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['username'], 'testuser')
        self.assertEqual(users[0]['email'], 'test@example.com')

    def test_register_duplicate_username(self):

        self.client.post('/register', data={
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test1@example.com'
        })
        
        response = self.client.post('/register', data={
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test2@example.com'
        }, follow_redirects=True)
        
        self.assertIn(b'\xd0\x9f\xd0\xbe\xd0\xbb\xd1\x8c\xd0\xb7\xd0\xbe\xd0\xb2\xd0\xb0\xd1\x82\xd0\xb5\xd0\xbb\xd1\x8c \xd1\x81 \xd1\x82\xd0\xb0\xd0\xba\xd0\xb8\xd0\xbc \xd0\xb8\xd0\xbc\xd0\xb5\xd0\xbd\xd0\xb5\xd0\xbc \xd1\x83\xd0\xb6\xd0\xb5 \xd1\x81\xd1\x83\xd1\x89\xd0\xb5\xd1\x81\xd1\x82\xd0\xb2\xd1\x83\xd0\xb5\xd1\x82', response.data)

    def test_register_missing_fields(self):
        response = self.client.post('/register', data={
            'username': 'testuser'
        }, follow_redirects=True)
        
        self.assertIn(b'\xd0\x92\xd1\x81\xd0\xb5 \xd0\xbf\xd0\xbe\xd0\xbb\xd1\x8f \xd0\xbe\xd0\xb1\xd1\x8f\xd0\xb7\xd0\xb0\xd1\x82\xd0\xb5\xd0\xbb\xd1\x8c\xd0\xbd\xd1\x8b \xd0\xb4\xd0\xbb\xd1\x8f \xd0\xb7\xd0\xb0\xd0\xbf\xd0\xbe\xd0\xbb\xd0\xbd\xd0\xb5\xd0\xbd\xd0\xb8\xd1\x8f', response.data)

    def test_login_page(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'\xd0\x92\xd1\x85\xd0\xbe\xd0\xb4 \xd0\xb2 \xd1\x81\xd0\xb8\xd1\x81\xd1\x82\xd0\xb5\xd0\xbc\xd1\x83', response.data)

    def test_login_success(self):
        self.client.post('/register', data={
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com'
        })
        
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'\xd0\x94\xd0\xbe\xd0\xb1\xd1\x80\xd0\xbe \xd0\xbf\xd0\xbe\xd0\xb6\xd0\xb0\xd0\xbb\xd0\xbe\xd0\xb2\xd0\xb0\xd1\x82\xd1\x8c', response.data)

    def test_login_wrong_password(self):

        self.client.post('/register', data={
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com'
        })
        
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpass'
        }, follow_redirects=True)
        
        self.assertIn(b'\xd0\x9d\xd0\xb5\xd0\xb2\xd0\xb5\xd1\x80\xd0\xbd\xd0\xbe\xd0\xb5 \xd0\xb8\xd0\xbc\xd1\x8f \xd0\xbf\xd0\xbe\xd0\xbb\xd1\x8c\xd0\xb7\xd0\xbe\xd0\xb2\xd0\xb0\xd1\x82\xd0\xb5\xd0\xbb\xd1\x8f \xd0\xb8\xd0\xbb\xd0\xb8 \xd0\xbf\xd0\xb0\xd1\x80\xd0\xbe\xd0\xbb\xd1\x8c', response.data)

    def test_login_nonexistent_user(self):
        response = self.client.post('/login', data={
            'username': 'nonexistent',
            'password': 'testpass123'
        }, follow_redirects=True)
        
        self.assertIn(b'\xd0\x9d\xd0\xb5\xd0\xb2\xd0\xb5\xd1\x80\xd0\xbd\xd0\xbe\xd0\xb5 \xd0\xb8\xd0\xbc\xd1\x8f \xd0\xbf\xd0\xbe\xd0\xbb\xd1\x8c\xd0\xb7\xd0\xbe\xd0\xb2\xd0\xb0\xd1\x82\xd0\xb5\xd0\xbb\xd1\x8f \xd0\xb8\xd0\xbb\xd0\xb8 \xd0\xbf\xd0\xb0\xd1\x80\xd0\xbe\xd0\xbb\xd1\x8c', response.data)

    def test_logout(self):
        self.client.post('/register', data={
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com'
        })
        self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'\xd0\x92\xd1\x8b \xd0\xb2\xd1\x8b\xd1\x88\xd0\xbb\xd0\xb8 \xd0\xb8\xd0\xb7 \xd1\x81\xd0\xb8\xd1\x81\xd1\x82\xd0\xb5\xd0\xbc\xd1\x8b', response.data)

unittest.main() 