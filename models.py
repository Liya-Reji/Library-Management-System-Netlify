from datetime import datetime, timezone, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def utcnow():
    return datetime.now(timezone.utc)

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")  # 'admin' or 'student'
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    student_profile = db.relationship("Student", backref="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == "admin"

    def is_student(self):
        return self.role == "student"

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    student_id_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    department = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    registration_date = db.Column(db.DateTime, default=utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    borrow_records = db.relationship("BorrowRecord", backref="student", lazy="dynamic", cascade="all, delete-orphan")

    def active_borrows_count(self):
        return self.borrow_records.filter_by(status="issued").count()

    def __repr__(self):
        return f"<Student {self.student_id_number} - {self.full_name}>"


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(30), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    author = db.Column(db.String(150), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False, index=True)
    publisher = db.Column(db.String(150), nullable=True)
    total_copies = db.Column(db.Integer, nullable=False, default=1)
    available_copies = db.Column(db.Integer, nullable=False, default=1)
    date_added = db.Column(db.DateTime, default=utcnow, nullable=False)

    borrow_records = db.relationship("BorrowRecord", backref="book", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def is_available(self):
        return self.available_copies > 0

    @property
    def issued_copies(self):
        return max(0, self.total_copies - self.available_copies)

    def __repr__(self):
        return f"<Book {self.title} by {self.author}>"


class BorrowRecord(db.Model):
    __tablename__ = "borrow_records"

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    issue_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="issued")  # 'issued' or 'returned'
    notes = db.Column(db.Text, nullable=True)

    @property
    def is_overdue(self):
        if self.status == "issued" and self.due_date:
            return date.today() > self.due_date
        return False

    @property
    def days_overdue(self):
        if self.is_overdue:
            return (date.today() - self.due_date).days
        return 0

    def __repr__(self):
        return f"<BorrowRecord Book:{self.book_id} Student:{self.student_id} Status:{self.status}>"
