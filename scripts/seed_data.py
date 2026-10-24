"""
Optional demo data seed script.
Populates sample books, students, and borrow records for local testing and college demonstrations.
Run manually with: python scripts/seed_data.py
"""
import sys
import os
from datetime import date, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from models import db, User, Student, Book, BorrowRecord

def seed_database():
    app = create_app()
    with app.app_context():
        # Ensure tables exist
        db.create_all()

        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@library.college.edu")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

        # 1. Seed Administrator if not present
        admin_user = User.query.filter_by(username=admin_username).first()
        if not admin_user:
            admin_user = User(
                username=admin_username,
                email=admin_email,
                role="admin"
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            print(f"[+] Created Administrator account: {admin_username} / {admin_password}")
        else:
            print(f"[*] Administrator '{admin_username}' already exists.")

        # 2. Seed Books
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

        book_objects = {}
        for b_data in sample_books:
            existing_book = Book.query.filter_by(title=b_data["title"]).first()
            if not existing_book:
                new_book = Book(**b_data)
                db.session.add(new_book)
                db.session.flush()
                book_objects[b_data["title"]] = new_book
                print(f"[+] Added book: {new_book.title}")
            else:
                book_objects[b_data["title"]] = existing_book

        # 3. Seed Students
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

        student_objects = {}
        for s_data in sample_students:
            existing_student = Student.query.filter_by(student_id_number=s_data["student_id_number"]).first()
            if not existing_student:
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
                db.session.flush()
                student_objects[s_data["username"]] = student
                print(f"[+] Created student: {student.full_name} ({s_data['username']}/student123)")
            else:
                student_objects[s_data["username"]] = existing_student

        # Commit initial users & books
        db.session.commit()

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
                # Overdue Loan (to showcase overdue badge in dashboard!)
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

        print("\nAll demo data seeded successfully!")
        print("Login credentials for demo:")
        print(" - Librarian: admin / admin123")
        print(" - Student:   student1 / student123")

if __name__ == "__main__":
    seed_database()
