from datetime import date, timedelta
from tests.base_test import BaseTestCase
from models import db, User, Student, Book, BorrowRecord

class TestApiEndpoints(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.admin = self.create_admin(username="api_admin", password="password123")
        self.user, self.student = self.create_student(username="api_student", email="student_api@test.edu", password="password123")

    def test_api_stats(self):
        self.create_book(title="Book 1", total_copies=3, available_copies=3)
        resp = self.client.get("/api/stats")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["total_titles"], 1)
        self.assertEqual(data["total_copies"], 3)
        self.assertEqual(data["available_copies"], 3)
        self.assertEqual(data["total_students"], 1)

    def test_api_login_success_and_logout(self):
        resp = self.client.post("/api/auth/login", json={
            "identifier": "api_admin",
            "password": "password123"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["role"], "admin")

        # Test auth/me
        me_resp = self.client.get("/api/auth/me")
        self.assertEqual(me_resp.status_code, 200)
        me_data = me_resp.get_json()
        self.assertTrue(me_data["authenticated"])
        self.assertEqual(me_data["user"]["username"], "api_admin")

        # Test logout
        logout_resp = self.client.post("/api/auth/logout")
        self.assertEqual(logout_resp.status_code, 200)
        me_after = self.client.get("/api/auth/me").get_json()
        self.assertFalse(me_after["authenticated"])

    def test_api_login_invalid_password(self):
        resp = self.client.post("/api/auth/login", json={
            "identifier": "api_admin",
            "password": "wrong_password"
        })
        self.assertEqual(resp.status_code, 401)
        data = resp.get_json()
        self.assertFalse(data["success"])

    def test_api_register_student(self):
        resp = self.client.post("/api/auth/register", json={
            "username": "new_api_student",
            "student_id_number": "STU-API-001",
            "full_name": "API Student",
            "email": "new_api@college.edu",
            "department": "Computer Science & Engineering",
            "phone": "9998887776",
            "password": "securepassword",
            "confirm_password": "securepassword"
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertTrue(data["success"])

    def test_api_books_list_and_search(self):
        self.create_book(title="Data Structures in Python", category="CS")
        self.create_book(title="Cloud Computing with Kubernetes", category="DevOps")

        resp = self.client.get("/api/books?q=Python")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data["books"]), 1)
        self.assertEqual(data["books"][0]["title"], "Data Structures in Python")

    def test_api_book_add_edit_delete(self):
        # Login as admin
        self.client.post("/api/auth/login", json={"identifier": "api_admin", "password": "password123"})

        # Add book
        add_resp = self.client.post("/api/books", json={
            "title": "New Tech Book",
            "author": "Tech Author",
            "category": "Tech",
            "isbn": "978-1111222233",
            "total_copies": 5
        })
        self.assertEqual(add_resp.status_code, 201)
        book_id = add_resp.get_json()["book"]["id"]

        # Edit book
        edit_resp = self.client.put(f"/api/books/{book_id}", json={
            "title": "Updated Tech Book",
            "author": "Tech Author",
            "category": "Tech",
            "total_copies": 6,
            "available_copies": 6
        })
        self.assertEqual(edit_resp.status_code, 200)
        self.assertEqual(edit_resp.get_json()["book"]["title"], "Updated Tech Book")

        # Delete book
        del_resp = self.client.delete(f"/api/books/{book_id}")
        self.assertEqual(del_resp.status_code, 200)
        self.assertIsNone(Book.query.filter_by(id=book_id).first())

    def test_api_issue_and_return_workflow(self):
        # Login as admin
        self.client.post("/api/auth/login", json={"identifier": "api_admin", "password": "password123"})
        book = self.create_book(title="Borrowable Book", total_copies=2, available_copies=2)

        # Issue book
        due_date = (date.today() + timedelta(days=14)).strftime("%Y-%m-%d")
        issue_resp = self.client.post("/api/issue", json={
            "book_id": book.id,
            "student_id": self.student.id,
            "due_date": due_date
        })
        self.assertEqual(issue_resp.status_code, 201)
        record_id = issue_resp.get_json()["record"]["id"]

        # Check stock reduced
        b_updated = Book.query.filter_by(id=book.id).first()
        self.assertEqual(b_updated.available_copies, 1)

        # Return book
        return_resp = self.client.post(f"/api/return/{record_id}")
        self.assertEqual(return_resp.status_code, 200)

        # Check stock restored
        b_restored = Book.query.filter_by(id=book.id).first()
        self.assertEqual(b_restored.available_copies, 2)
