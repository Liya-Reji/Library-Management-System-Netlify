"""
Safe Demonstration Data Seeding Script.
Usage:
  - Local development:
      python scripts/seed_data.py
  - In production (requires explicit confirmation flag):
      python scripts/seed_data.py --confirm-production

Guarantees:
  - Idempotent: can be executed multiple times without duplicating books, students, or loans.
  - Never overwrites existing administrator accounts or passwords.
  - Checks unique constraints (ISBN, book title, student ID, student email, username).
"""
import sys
import os
from datetime import date, timedelta
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from models import db, User, Student, Book, BorrowRecord

def mask_connection_url(url):
    if not url:
        return "None"
    try:
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(f":{parsed.password}@", ":****@")
            return parsed._replace(netloc=netloc).geturl()
    except Exception:
        pass
    return "Configured Database URL"

def seed_database():
    is_production = os.getenv("FLASK_ENV") == "production"
    confirmed = "--confirm-production" in sys.argv

    if is_production and not confirmed:
        print("\n[!] SAFETY GUARD: Application is running in PRODUCTION environment.")
        print("[!] Demo data will NOT be automatically inserted without explicit confirmation.")
        print("[!] If you wish to seed demonstration records into production, run:")
        print("    python scripts/seed_data.py --confirm-production\n")
        return

    app = create_app()
    with app.app_context():
        # Ensure tables exist
        db.create_all()

        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        print(f"[*] Target Database: {mask_connection_url(db_uri)}")

        # 1. Administrator Account Check / Preservation
        existing_any_admin = User.query.filter_by(role="admin").first()
        if existing_any_admin:
            print(f"[*] Administrator account '{existing_any_admin.username}' already exists. Preserving credentials.")
        else:
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            admin_email = os.getenv("ADMIN_EMAIL", "admin@library.college.edu")
            admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

            admin_user = User(
                username=admin_username,
                email=admin_email,
                role="admin"
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"[+] Created initial demonstration administrator: '{admin_username}'")

        # 2. Seed Books (Idempotent by title and ISBN)
        sample_books = [
            {
                "title": "Introduction to Algorithms (4th Edition)",
                "author": "Thomas H. Cormen, Charles E. Leiserson",
                "category": "Computer Science",
                "isbn": "978-0262046305",
                "publisher": "MIT Press",
                "total_copies": 5,
                "available_copies": 5
            },
            {
                "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
                "author": "Robert C. Martin",
                "category": "Software Engineering",
                "isbn": "978-0132350884",
                "publisher": "Prentice Hall",
                "total_copies": 4,
                "available_copies": 4
            },
            {
                "title": "Operating System Concepts (10th Edition)",
                "author": "Abraham Silberschatz, Peter B. Galvin",
                "category": "Computer Science",
                "isbn": "978-1119456339",
                "publisher": "Wiley",
                "total_copies": 3,
                "available_copies": 3
            },
            {
                "title": "Database System Concepts (7th Edition)",
                "author": "Abraham Silberschatz, Henry F. Korth",
                "category": "Database Systems",
                "isbn": "978-0078022159",
                "publisher": "McGraw-Hill",
                "total_copies": 4,
                "available_copies": 4
            },
            {
                "title": "Computer Networking: A Top-Down Approach",
                "author": "James F. Kurose, Keith W. Ross",
                "category": "Networking",
                "isbn": "978-0136681557",
                "publisher": "Pearson",
                "total_copies": 3,
                "available_copies": 3
            },
            {
                "title": "Python Crash Course (3rd Edition)",
                "author": "Eric Matthes",
                "category": "Programming",
                "isbn": "978-1718502703",
                "publisher": "No Starch Press",
                "total_copies": 6,
                "available_copies": 6
            },
            {
                "title": "Artificial Intelligence: A Modern Approach",
                "author": "Stuart Russell, Peter Norvig",
                "category": "Artificial Intelligence",
                "isbn": "978-0134610993",
                "publisher": "Pearson",
                "total_copies": 3,
                "available_copies": 3
            },
            {
                "title": "Flask Web Development: Developing Web Applications with Python",
                "author": "Miguel Grinberg",
                "category": "Web Development",
                "isbn": "978-1491991732",
                "publisher": "O'Reilly Media",
                "total_copies": 4,
                "available_copies": 4
            }
        ]

        books_added = 0
        for b_data in sample_books:
            existing = Book.query.filter(
                (Book.title == b_data["title"]) | (Book.isbn == b_data["isbn"])
            ).first()
            if not existing:
                new_book = Book(**b_data)
                db.session.add(new_book)
                books_added += 1

        db.session.commit()
        if books_added > 0:
            print(f"[+] Added {books_added} new demonstration book(s) to catalog.")
        else:
            print("[*] Demonstration books already present. No duplicates added.")

        # 3. Seed Students (Idempotent by student ID, email, username)
        sample_students = [
            {
                "username": "student1",
                "full_name": "Aarav Patel",
                "student_id_number": "BCA-2026-001",
                "email": "aarav.patel@college.edu",
                "department": "Bachelor of Computer Applications (BCA)",
                "phone": "+91 9876543210"
            },
            {
                "username": "student2",
                "full_name": "Priya Sharma",
                "student_id_number": "CSE-2026-015",
                "email": "priya.sharma@college.edu",
                "department": "Computer Science & Engineering",
                "phone": "+91 9876543211"
            },
            {
                "username": "student3",
                "full_name": "Rohan Gupta",
                "student_id_number": "IT-2026-022",
                "email": "rohan.gupta@college.edu",
                "department": "Information Technology",
                "phone": "+91 9876543212"
            }
        ]

        students_added = 0
        for s_data in sample_students:
            user_exists = User.query.filter(
                (User.username == s_data["username"]) | (User.email == s_data["email"])
            ).first()
            student_exists = Student.query.filter(
                (Student.student_id_number == s_data["student_id_number"]) | (Student.email == s_data["email"])
            ).first()

            if not user_exists and not student_exists:
                user = User(
                    username=s_data["username"],
                    email=s_data["email"],
                    role="student"
                )
                user.set_password("student123")
                db.session.add(user)
                db.session.flush()

                student = Student(
                    student_id_number=s_data["student_id_number"],
                    full_name=s_data["full_name"],
                    email=s_data["email"],
                    department=s_data["department"],
                    phone=s_data["phone"],
                    user_id=user.id
                )
                db.session.add(student)
                students_added += 1

        db.session.commit()
        if students_added > 0:
            print(f"[+] Added {students_added} demonstration student profile(s).")
        else:
            print("[*] Demonstration students already present. No duplicates added.")

        # 4. Seed Demonstrative Borrow Records if table is empty
        if BorrowRecord.query.count() == 0:
            today = date.today()
            b1 = Book.query.filter_by(title="Introduction to Algorithms (4th Edition)").first()
            b2 = Book.query.filter_by(title="Clean Code: A Handbook of Agile Software Craftsmanship").first()
            b3 = Book.query.filter_by(title="Python Crash Course (3rd Edition)").first()
            s1 = Student.query.filter_by(student_id_number="BCA-2026-001").first()
            s2 = Student.query.filter_by(student_id_number="CSE-2026-015").first()

            if b1 and s1 and b1.available_copies > 0:
                # Active On-Time Loan
                r1 = BorrowRecord(
                    book_id=b1.id,
                    student_id=s1.id,
                    issue_date=today - timedelta(days=5),
                    due_date=today + timedelta(days=9),
                    status="issued",
                    notes="Semester study copy"
                )
                b1.available_copies -= 1
                db.session.add(r1)

            if b2 and s2 and b2.available_copies > 0:
                # Overdue Loan (to showcase overdue badge in dashboard)
                r2 = BorrowRecord(
                    book_id=b2.id,
                    student_id=s2.id,
                    issue_date=today - timedelta(days=20),
                    due_date=today - timedelta(days=6),
                    status="issued",
                    notes="Overdue project reference"
                )
                b2.available_copies -= 1
                db.session.add(r2)

            if b3 and s1:
                # Returned Loan
                r3 = BorrowRecord(
                    book_id=b3.id,
                    student_id=s1.id,
                    issue_date=today - timedelta(days=30),
                    due_date=today - timedelta(days=16),
                    return_date=today - timedelta(days=18),
                    status="returned",
                    notes="Returned on time"
                )
                db.session.add(r3)

            db.session.commit()
            print("[+] Seeded demonstration borrow transactions (1 active, 1 overdue, 1 returned).")

        print("\n[+] Verification complete: database is ready.")

if __name__ == "__main__":
    seed_database()
