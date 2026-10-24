from datetime import date
from flask import Blueprint, render_template, request, session, abort
from sqlalchemy import or_
from models import Book, Student, BorrowRecord
from auth_utils import student_required

student_bp = Blueprint("student", __name__, url_prefix="/student")

@student_bp.before_request
def check_student_access():
    return student_required(lambda: None)()

def get_current_student():
    student_id = session.get("student_id")
    if not student_id:
        # Check user profile
        student = Student.query.filter_by(user_id=session.get("user_id")).first()
        if student:
            session["student_id"] = student.id
            return student
        abort(403, description="Student profile not found.")
    student = Student.query.filter_by(id=student_id).first()
    if not student:
        abort(404, description="Student record not found.")
    return student

@student_bp.route("/dashboard")
def dashboard():
    student = get_current_student()
    today = date.today()

    active_borrows = BorrowRecord.query.filter_by(
        student_id=student.id,
        status="issued"
    ).order_by(BorrowRecord.due_date.asc()).all()

    overdue_count = sum(1 for b in active_borrows if b.due_date < today)
    total_borrowed = BorrowRecord.query.filter_by(student_id=student.id).count()

    recent_history = BorrowRecord.query.filter_by(
        student_id=student.id
    ).order_by(BorrowRecord.id.desc()).limit(5).all()

    return render_template(
        "student/dashboard.html",
        student=student,
        active_borrows=active_borrows,
        overdue_count=overdue_count,
        total_borrowed=total_borrowed,
        recent_history=recent_history,
        today=today
    )


@student_bp.route("/books")
def books():
    query_str = (request.args.get("q") or "").strip()
    category_filter = (request.args.get("category") or "").strip()
    availability_filter = request.args.get("available", "")
    page = request.args.get("page", 1, type=int)
    per_page = 12

    books_query = Book.query

    if query_str:
        search_filter = or_(
            Book.title.ilike(f"%{query_str}%"),
            Book.author.ilike(f"%{query_str}%"),
            Book.isbn.ilike(f"%{query_str}%")
        )
        books_query = books_query.filter(search_filter)

    if category_filter:
        books_query = books_query.filter(Book.category == category_filter)

    if availability_filter == "yes":
        books_query = books_query.filter(Book.available_copies > 0)
    elif availability_filter == "no":
        books_query = books_query.filter(Book.available_copies <= 0)

    pagination = books_query.order_by(Book.title.asc()).paginate(page=page, per_page=per_page, error_out=False)
    categories = [c[0] for c in Book.query.with_entities(Book.category).distinct().order_by(Book.category).all() if c[0]]

    return render_template(
        "student/books.html",
        pagination=pagination,
        books=pagination.items,
        query_str=query_str,
        category_filter=category_filter,
        availability_filter=availability_filter,
        categories=categories
    )


@student_bp.route("/my-books")
def my_books():
    student = get_current_student()
    today = date.today()

    issued_records = BorrowRecord.query.filter_by(
        student_id=student.id,
        status="issued"
    ).order_by(BorrowRecord.due_date.asc()).all()

    return render_template(
        "student/my_books.html",
        student=student,
        records=issued_records,
        today=today
    )


@student_bp.route("/history")
def history():
    student = get_current_student()
    today = date.today()
    page = request.args.get("page", 1, type=int)
    per_page = 15

    pagination = BorrowRecord.query.filter_by(
        student_id=student.id
    ).order_by(BorrowRecord.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "student/history.html",
        student=student,
        pagination=pagination,
        records=pagination.items,
        today=today
    )
