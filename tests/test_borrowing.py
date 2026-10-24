from datetime import date, timedelta
from tests.base_test import BaseTestCase
from models import db, Book, Student, BorrowRecord

class TestBorrowingWorkflow(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.admin = self.create_admin(username="circ_admin", password="password")
        self.user, self.student = self.create_student(username="circ_student", email="circ@test.edu", password="password")
        self.login("circ_admin", "password")

    def test_issue_available_book_success(self):
        book = self.create_book(title="Test Issue Book", total_copies=2, available_copies=2)
        due_date = (date.today() + timedelta(days=14)).strftime("%Y-%m-%d")

        resp = self.client.post("/admin/issue", data={
            "book_id": book.id,
            "student_id": self.student.id,
            "due_date": due_date,
            "notes": "Semester issue"
        }, follow_redirects=True)

        self.assertEqual(resp.status_code, 200)

        # Inventory check: available copies decreased
        updated_book = Book.query.filter_by(id=book.id).first()
        self.assertEqual(updated_book.available_copies, 1)

        # Record check
        record = BorrowRecord.query.filter_by(book_id=book.id, student_id=self.student.id).first()
        self.assertIsNotNone(record)
        self.assertEqual(record.status, "issued")
        self.assertEqual(record.issue_date, date.today())

    def test_reject_issue_when_no_copies_available(self):
        # Book with 0 available copies
        book = self.create_book(title="Out of Stock Book", total_copies=1, available_copies=0)
        due_date = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")

        resp = self.client.post("/admin/issue", data={
            "book_id": book.id,
            "student_id": self.student.id,
            "due_date": due_date
        }, follow_redirects=True)

        self.assertIn(b"No copies available right now", resp.data)

        # Verify no borrow record was added
        record = BorrowRecord.query.filter_by(book_id=book.id).first()
        self.assertIsNone(record)

    def test_return_book_and_inventory_increment(self):
        book = self.create_book(title="Returnable Book", total_copies=3, available_copies=2)
        record = BorrowRecord(
            book_id=book.id,
            student_id=self.student.id,
            issue_date=date.today() - timedelta(days=5),
            due_date=date.today() + timedelta(days=9),
            status="issued"
        )
        db.session.add(record)
        db.session.commit()

        # Trigger return
        resp = self.client.post(f"/admin/return/{record.id}", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Record status should be returned with return_date set
        updated_record = BorrowRecord.query.filter_by(id=record.id).first()
        self.assertEqual(updated_record.status, "returned")
        self.assertEqual(updated_record.return_date, date.today())

        # Inventory should be incremented back to 3
        updated_book = Book.query.filter_by(id=book.id).first()
        self.assertEqual(updated_book.available_copies, 3)

    def test_prevent_duplicate_returns(self):
        book = self.create_book(title="Duplicate Test Book", total_copies=2, available_copies=2)
        record = BorrowRecord(
            book_id=book.id,
            student_id=self.student.id,
            issue_date=date.today() - timedelta(days=10),
            due_date=date.today() - timedelta(days=2),
            return_date=date.today(),
            status="returned"
        )
        db.session.add(record)
        db.session.commit()

        # Attempt to return again
        resp = self.client.post(f"/admin/return/{record.id}", follow_redirects=True)
        self.assertIn(b"already recorded as returned", resp.data)

        # Inventory should NOT exceed total copies
        updated_book = Book.query.filter_by(id=book.id).first()
        self.assertEqual(updated_book.available_copies, 2)

    def test_overdue_book_identification(self):
        book = self.create_book(title="Overdue Test Book", total_copies=2, available_copies=1)

        # Record that was due 5 days ago
        overdue_record = BorrowRecord(
            book_id=book.id,
            student_id=self.student.id,
            issue_date=date.today() - timedelta(days=20),
            due_date=date.today() - timedelta(days=5),
            status="issued"
        )
        db.session.add(overdue_record)
        db.session.commit()

        self.assertTrue(overdue_record.is_overdue)
        self.assertEqual(overdue_record.days_overdue, 5)

        # Non-overdue record
        ontime_record = BorrowRecord(
            book_id=book.id,
            student_id=self.student.id,
            issue_date=date.today() - timedelta(days=2),
            due_date=date.today() + timedelta(days=12),
            status="issued"
        )
        db.session.add(ontime_record)
        db.session.commit()

        self.assertFalse(ontime_record.is_overdue)
        self.assertEqual(ontime_record.days_overdue, 0)
