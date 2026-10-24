from tests.base_test import BaseTestCase
from models import Book

class TestBookManagement(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.admin = self.create_admin(username="book_admin", password="password")
        self.login("book_admin", "password")

    def test_add_book_success(self):
        resp = self.client.post("/admin/books/add", data={
            "title": "Clean Architecture",
            "author": "Robert C. Martin",
            "category": "Software Engineering",
            "isbn": "978-0134494166",
            "publisher": "Prentice Hall",
            "total_copies": 4
        }, follow_redirects=True)

        self.assertEqual(resp.status_code, 200)
        book = Book.query.filter_by(title="Clean Architecture").first()
        self.assertIsNotNone(book)
        self.assertEqual(book.total_copies, 4)
        self.assertEqual(book.available_copies, 4)

    def test_add_book_invalid_copies(self):
        resp = self.client.post("/admin/books/add", data={
            "title": "Invalid Book",
            "author": "Author",
            "category": "Science",
            "total_copies": -1
        }, follow_redirects=True)

        self.assertIn(b"Total copies must be a positive integer", resp.data)
        self.assertIsNone(Book.query.filter_by(title="Invalid Book").first())

    def test_search_books(self):
        self.create_book(title="Data Structures and Algorithm Analysis", author="Mark Allen Weiss", category="CS")
        self.create_book(title="Artificial Intelligence: Modern Approach", author="Stuart Russell", category="AI")

        # Search by title keyword
        resp = self.client.get("/admin/books?q=Structures")
        self.assertIn(b"Data Structures", resp.data)
        self.assertNotIn(b"Artificial Intelligence", resp.data)

        # Search by author keyword
        resp2 = self.client.get("/admin/books?q=Russell")
        self.assertIn(b"Artificial Intelligence", resp2.data)
        self.assertNotIn(b"Data Structures", resp2.data)

    def test_edit_book_prevent_available_exceeding_total(self):
        book = self.create_book(title="Editable Book", total_copies=3, available_copies=3)

        resp = self.client.post(f"/admin/books/edit/{book.id}", data={
            "title": "Editable Book",
            "author": "Test Author",
            "category": "Science",
            "total_copies": 2,
            "available_copies": 3  # available > total should be rejected
        }, follow_redirects=True)

        self.assertIn(b"Available copies cannot exceed total copies", resp.data)
        # Verify book unchanged in database
        book_refresh = Book.query.filter_by(id=book.id).first()
        self.assertEqual(book_refresh.total_copies, 3)

    def test_delete_book(self):
        book = self.create_book(title="Deletable Book", total_copies=1, available_copies=1)
        resp = self.client.post(f"/admin/books/delete/{book.id}", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(Book.query.filter_by(id=book.id).first())
