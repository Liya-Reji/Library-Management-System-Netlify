import unittest
from datetime import date, timedelta
from app import create_app
from models import db, User, Student, Book, BorrowRecord

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def create_admin(self, username="admin_user", email="admin@test.edu", password="password123"):
        user = User(username=username, email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    def create_student(self, username="student_user", email="student@test.edu", password="password123", student_id="STU-001"):
        user = User(username=username, email=email, role="student")
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        student = Student(
            student_id_number=student_id,
            full_name="Test Student",
            email=email,
            department="Computer Science",
            user_id=user.id
        )
        db.session.add(student)
        db.session.commit()
        return user, student

    def create_book(self, title="Test Book", author="Test Author", category="Science", total_copies=3, available_copies=3):
        book = Book(
            title=title,
            author=author,
            category=category,
            isbn="123-456-789",
            publisher="Test Publisher",
            total_copies=total_copies,
            available_copies=available_copies
        )
        db.session.add(book)
        db.session.commit()
        return book

    def login(self, identifier, password):
        return self.client.post("/auth/login", data={
            "identifier": identifier,
            "password": password
        }, follow_redirects=True)

    def logout(self):
        return self.client.get("/auth/logout", follow_redirects=True)
