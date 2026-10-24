from tests.base_test import BaseTestCase
from models import User, Student

class TestAuthentication(BaseTestCase):

    def test_password_hashing(self):
        user = User(username="hashtest", email="hash@test.com", role="student")
        user.set_password("Secret123!")
        self.assertNotEqual(user.password_hash, "Secret123!")
        self.assertTrue(user.check_password("Secret123!"))
        self.assertFalse(user.check_password("WrongPassword"))

    def test_student_registration_success(self):
        response = self.client.post("/auth/register", data={
            "username": "new_student",
            "full_name": "New Student",
            "student_id_number": "BCA-2026-999",
            "email": "new_student@college.edu",
            "department": "Computer Science & Engineering",
            "phone": "9876543210",
            "password": "mypassword123",
            "confirm_password": "mypassword123"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        user = User.query.filter_by(username="new_student").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.role, "student")

        student = Student.query.filter_by(student_id_number="BCA-2026-999").first()
        self.assertIsNotNone(student)
        self.assertEqual(student.full_name, "New Student")
        self.assertEqual(student.user_id, user.id)

    def test_registration_password_mismatch(self):
        response = self.client.post("/auth/register", data={
            "username": "mismatch_user",
            "full_name": "Mismatch User",
            "student_id_number": "BCA-000",
            "email": "mismatch@college.edu",
            "department": "Information Technology",
            "password": "password123",
            "confirm_password": "password999"
        }, follow_redirects=True)

        self.assertIn(b"Passwords do not match", response.data)
        self.assertIsNone(User.query.filter_by(username="mismatch_user").first())

    def test_registration_duplicate_username(self):
        self.create_admin(username="existing_user", email="exist@test.com")
        response = self.client.post("/auth/register", data={
            "username": "existing_user",
            "full_name": "Duplicate Student",
            "student_id_number": "BCA-111",
            "email": "another@test.com",
            "department": "IT",
            "password": "pass123456",
            "confirm_password": "pass123456"
        }, follow_redirects=True)

        self.assertIn(b"Username is already taken", response.data)

    def test_login_and_logout_admin(self):
        self.create_admin(username="testadmin", email="admin@lib.edu", password="adminpass")

        # Successful login
        resp = self.login("testadmin", "adminpass")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Librarian Dashboard", resp.data)

        # Logout
        logout_resp = self.logout()
        self.assertEqual(logout_resp.status_code, 200)
        self.assertIn(b"You have been securely logged out", logout_resp.data)

    def test_login_invalid_password(self):
        self.create_admin(username="testadmin", password="correct")
        resp = self.login("testadmin", "wrong")
        self.assertIn(b"Invalid credentials", resp.data)

    def test_role_based_access_admin_route_unauthenticated(self):
        # Accessing admin dashboard without login should redirect to login
        resp = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login", resp.headers["Location"])

    def test_role_based_access_student_forbidden_on_admin_route(self):
        # Student logged in attempting to access admin route gets 403
        self.create_student(username="stu1", email="stu1@test.com", password="pass")
        self.login("stu1", "pass")
        resp = self.client.get("/admin/dashboard")
        self.assertEqual(resp.status_code, 403)

    def test_role_based_access_admin_forbidden_on_student_route(self):
        # Admin logged in attempting to access student route gets 403
        self.create_admin(username="adm1", email="adm1@test.com", password="pass")
        self.login("adm1", "pass")
        resp = self.client.get("/student/dashboard")
        self.assertEqual(resp.status_code, 403)
