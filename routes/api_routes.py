import os
import re
from datetime import datetime, timezone, date, timedelta
from flask import Blueprint, request, jsonify, session
from sqlalchemy import or_, func
from models import db, User, Student, Book, BorrowRecord

api_bp = Blueprint("api", __name__, url_prefix="/api")
EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

# Helper for JSON serialization of Book
def serialize_book(b):
    return {
        "id": b.id,
        "isbn": b.isbn or "",
        "title": b.title,
        "author": b.author,
        "category": b.category,
        "publisher": b.publisher or "",
        "total_copies": b.total_copies,
        "available_copies": b.available_copies,
        "issued_copies": b.issued_copies,
        "is_available": b.is_available,
        "date_added": b.date_added.strftime("%Y-%m-%d") if b.date_added else ""
    }

# Helper for JSON serialization of Student
def serialize_student(s):
    return {
        "id": s.id,
        "student_id_number": s.student_id_number,
        "full_name": s.full_name,
        "email": s.email,
        "department": s.department,
        "phone": s.phone or "",
        "registration_date": s.registration_date.strftime("%Y-%m-%d") if s.registration_date else "",
        "active_borrows_count": s.active_borrows_count()
    }

# Helper for JSON serialization of BorrowRecord
def serialize_record(r, today=None):
    if today is None:
        today = date.today()
    days_left = (r.due_date - today).days if r.due_date else 0
    return {
        "id": r.id,
        "book_id": r.book_id,
        "book_title": r.book.title if r.book else "Unknown",
        "book_author": r.book.author if r.book else "",
        "book_category": r.book.category if r.book else "",
        "student_id": r.student_id,
        "student_name": r.student.full_name if r.student else "Unknown",
        "student_id_number": r.student.student_id_number if r.student else "",
        "student_department": r.student.department if r.student else "",
        "issue_date": r.issue_date.strftime("%Y-%m-%d") if r.issue_date else "",
        "due_date": r.due_date.strftime("%Y-%m-%d") if r.due_date else "",
        "return_date": r.return_date.strftime("%Y-%m-%d") if r.return_date else None,
        "status": r.status,
        "is_overdue": r.is_overdue,
        "days_overdue": r.days_overdue,
        "days_left": days_left,
        "notes": r.notes or ""
    }

# --- AUTH ENDPOINTS ---

@api_bp.route("/auth/me", methods=["GET"])
def current_user():
    if "user_id" not in session:
        return jsonify({"authenticated": False}), 200

    user = db.session.get(User, session["user_id"])
    if not user:
        session.clear()
        return jsonify({"authenticated": False}), 200

    student_data = None
    if user.is_student() and user.student_profile:
        student_data = serialize_student(user.student_profile)

    return jsonify({
        "authenticated": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        },
        "student": student_data
    }), 200


@api_bp.route("/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or request.form
    identifier = (data.get("identifier") or "").strip()
    password = data.get("password", "")

    if not identifier or not password:
        return jsonify({"success": False, "message": "Username/email and password are required."}), 400

    user = User.query.filter(
        (User.username.ilike(identifier)) | (User.email.ilike(identifier))
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"success": False, "message": "Invalid username/email or password."}), 401

    session.clear()
    session["user_id"] = user.id
    session["username"] = user.username
    session["user_role"] = user.role
    session["user_email"] = user.email

    student_data = None
    if user.is_student() and user.student_profile:
        session["student_id"] = user.student_profile.id
        session["student_name"] = user.student_profile.full_name
        student_data = serialize_student(user.student_profile)

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user.username}!",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        },
        "student": student_data
    }), 200


@api_bp.route("/auth/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    student_id_number = (data.get("student_id_number") or "").strip().upper()
    email = (data.get("email") or "").strip().lower()
    department = (data.get("department") or "").strip()
    phone = (data.get("phone") or "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    if not all([username, full_name, student_id_number, email, department, password, confirm_password]):
        return jsonify({"success": False, "message": "All required fields must be filled."}), 400

    if not EMAIL_REGEX.match(email):
        return jsonify({"success": False, "message": "Invalid email address format."}), 400

    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400

    if password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match."}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"success": False, "message": "Username is already taken."}), 400

    if User.query.filter_by(email=email).first() or Student.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email is already registered."}), 400

    if Student.query.filter_by(student_id_number=student_id_number).first():
        return jsonify({"success": False, "message": f"Student ID '{student_id_number}' is already registered."}), 400

    try:
        new_user = User(username=username, email=email, role="student")
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()

        new_student = Student(
            student_id_number=student_id_number,
            full_name=full_name,
            email=email,
            department=department,
            phone=phone if phone else None,
            user_id=new_user.id
        )
        db.session.add(new_student)
        db.session.commit()

        return jsonify({"success": True, "message": "Registration successful! You can now log in."}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Registration failed. Please check inputs."}), 500


@api_bp.route("/auth/logout", methods=["POST", "GET"])
def api_logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."}), 200

# --- PUBLIC / DASHBOARD STATS ---

@api_bp.route("/stats", methods=["GET"])
def get_stats():
    total_titles = Book.query.count()
    total_copies = db.session.query(func.sum(Book.total_copies)).scalar() or 0
    available_copies = db.session.query(func.sum(Book.available_copies)).scalar() or 0
    currently_issued = db.session.query(func.count(BorrowRecord.id)).filter_by(status="issued").scalar() or 0
    total_students = Student.query.count()

    today = date.today()
    overdue_count = db.session.query(func.count(BorrowRecord.id)).filter(
        BorrowRecord.status == "issued",
        BorrowRecord.due_date < today
    ).scalar() or 0

    return jsonify({
        "total_titles": total_titles,
        "total_copies": total_copies,
        "available_copies": available_copies,
        "currently_issued": currently_issued,
        "total_students": total_students,
        "overdue_count": overdue_count
    }), 200

# --- BOOKS ENDPOINTS ---

@api_bp.route("/books", methods=["GET"])
def list_books():
    query_str = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    available = request.args.get("available", "").strip()

    books_query = Book.query

    if query_str:
        books_query = books_query.filter(
            or_(
                Book.title.ilike(f"%{query_str}%"),
                Book.author.ilike(f"%{query_str}%"),
                Book.isbn.ilike(f"%{query_str}%"),
                Book.publisher.ilike(f"%{query_str}%")
            )
        )

    if category:
        books_query = books_query.filter(Book.category == category)

    if available == "yes":
        books_query = books_query.filter(Book.available_copies > 0)
    elif available == "no":
        books_query = books_query.filter(Book.available_copies <= 0)

    books = books_query.order_by(Book.id.desc()).all()
    categories = [c[0] for c in db.session.query(Book.category).distinct().order_by(Book.category).all() if c[0]]

    return jsonify({
        "books": [serialize_book(b) for b in books],
        "categories": categories,
        "total": len(books)
    }), 200


@api_bp.route("/books", methods=["POST"])
def add_book():
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Admin privileges required."}), 403

    data = request.get_json(silent=True) or request.form
    title = (data.get("title") or "").strip()
    author = (data.get("author") or "").strip()
    category = (data.get("category") or "").strip()
    isbn = (data.get("isbn") or "").strip()
    publisher = (data.get("publisher") or "").strip()

    try:
        total_copies = int(data.get("total_copies", 1))
        if total_copies < 1:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Total copies must be at least 1."}), 400

    if not title or not author or not category:
        return jsonify({"success": False, "message": "Title, Author, and Category are required."}), 400

    book = Book(
        title=title,
        author=author,
        category=category,
        isbn=isbn if isbn else None,
        publisher=publisher if publisher else None,
        total_copies=total_copies,
        available_copies=total_copies
    )
    db.session.add(book)
    db.session.commit()

    return jsonify({"success": True, "message": f"Book '{title}' added successfully.", "book": serialize_book(book)}), 201


@api_bp.route("/books/<int:book_id>", methods=["PUT", "POST"])
def edit_book(book_id):
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Admin privileges required."}), 403

    book = db.session.get(Book, book_id)
    if not book:
        return jsonify({"success": False, "message": "Book not found."}), 404

    data = request.get_json(silent=True) or request.form
    title = (data.get("title") or "").strip()
    author = (data.get("author") or "").strip()
    category = (data.get("category") or "").strip()
    isbn = (data.get("isbn") or "").strip()
    publisher = (data.get("publisher") or "").strip()

    try:
        new_total = int(data.get("total_copies", book.total_copies))
        new_available = int(data.get("available_copies", book.available_copies))
        if new_total < 1 or new_available < 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Copies must be non-negative integers (total >= 1)."}), 400

    if new_available > new_total:
        return jsonify({"success": False, "message": "Available copies cannot exceed total copies."}), 400

    active_issued = BorrowRecord.query.filter_by(book_id=book.id, status="issued").count()
    if new_total < active_issued:
        return jsonify({"success": False, "message": f"Cannot reduce total copies below {active_issued} (currently issued)."}), 400

    book.title = title or book.title
    book.author = author or book.author
    book.category = category or book.category
    book.isbn = isbn if isbn else None
    book.publisher = publisher if publisher else None
    book.total_copies = new_total
    book.available_copies = new_available

    db.session.commit()
    return jsonify({"success": True, "message": "Book updated successfully.", "book": serialize_book(book)}), 200


@api_bp.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Admin privileges required."}), 403

    book = db.session.get(Book, book_id)
    if not book:
        return jsonify({"success": False, "message": "Book not found."}), 404

    active_borrows = BorrowRecord.query.filter_by(book_id=book.id, status="issued").count()
    if active_borrows > 0:
        return jsonify({"success": False, "message": f"Cannot delete '{book.title}': {active_borrows} copy/copies currently issued."}), 400

    title = book.title
    db.session.delete(book)
    db.session.commit()
    return jsonify({"success": True, "message": f"Book '{title}' was removed from the catalog."}), 200

# --- STUDENTS ENDPOINTS ---

@api_bp.route("/students", methods=["GET"])
def list_students():
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Admin privileges required."}), 403

    query_str = (request.args.get("q") or "").strip()
    department = (request.args.get("department") or "").strip()

    students_query = Student.query
    if query_str:
        students_query = students_query.filter(
            or_(
                Student.full_name.ilike(f"%{query_str}%"),
                Student.student_id_number.ilike(f"%{query_str}%"),
                Student.email.ilike(f"%{query_str}%")
            )
        )
    if department:
        students_query = students_query.filter(Student.department == department)

    students = students_query.order_by(Student.id.desc()).all()
    departments = [d[0] for d in db.session.query(Student.department).distinct().order_by(Student.department).all() if d[0]]

    return jsonify({
        "students": [serialize_student(s) for s in students],
        "departments": departments,
        "total": len(students)
    }), 200


@api_bp.route("/students", methods=["POST"])
def add_student():
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Admin privileges required."}), 403

    data = request.get_json(silent=True) or request.form
    full_name = (data.get("full_name") or "").strip()
    student_id_number = (data.get("student_id_number") or "").strip().upper()
    email = (data.get("email") or "").strip().lower()
    department = (data.get("department") or "").strip()
    phone = (data.get("phone") or "").strip()

    if not full_name or not student_id_number or not email or not department:
        return jsonify({"success": False, "message": "Full Name, Student ID, Email, and Department are required."}), 400

    if Student.query.filter_by(student_id_number=student_id_number).first():
        return jsonify({"success": False, "message": f"Student ID '{student_id_number}' already exists."}), 400

    if Student.query.filter_by(email=email).first() or User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": f"Email '{email}' is already in use."}), 400

    try:
        default_username = student_id_number.lower().replace("-", "_")
        user = User(username=default_username, email=email, role="student")
        user.set_password("student123")
        db.session.add(user)
        db.session.flush()

        student = Student(
            student_id_number=student_id_number,
            full_name=full_name,
            email=email,
            department=department,
            phone=phone if phone else None,
            user_id=user.id
        )
        db.session.add(student)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Student '{full_name}' registered. Username: {default_username}, Password: student123",
            "student": serialize_student(student)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Failed to register student."}), 500


@api_bp.route("/students/<int:student_id>", methods=["PUT", "POST"])
def edit_student(student_id):
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Admin privileges required."}), 403

    student = db.session.get(Student, student_id)
    if not student:
        return jsonify({"success": False, "message": "Student not found."}), 404

    data = request.get_json(silent=True) or request.form
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    department = (data.get("department") or "").strip()
    phone = (data.get("phone") or "").strip()

    if not full_name or not email or not department:
        return jsonify({"success": False, "message": "Full Name, Email, and Department are required."}), 400

    existing = Student.query.filter(Student.email == email, Student.id != student.id).first()
    if existing:
        return jsonify({"success": False, "message": f"Email '{email}' is used by another student."}), 400

    student.full_name = full_name
    student.email = email
    student.department = department
    student.phone = phone if phone else None

    if student.user:
        student.user.email = email

    db.session.commit()
    return jsonify({"success": True, "message": "Student updated successfully.", "student": serialize_student(student)}), 200


@api_bp.route("/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Admin privileges required."}), 403

    student = db.session.get(Student, student_id)
    if not student:
        return jsonify({"success": False, "message": "Student not found."}), 404

    active_borrows = BorrowRecord.query.filter_by(student_id=student.id, status="issued").count()
    if active_borrows > 0:
        return jsonify({"success": False, "message": f"Cannot delete '{student.full_name}': has {active_borrows} book(s) currently issued."}), 400

    user_to_delete = student.user
    name = student.full_name
    db.session.delete(student)
    if user_to_delete:
        db.session.delete(user_to_delete)
    db.session.commit()

    return jsonify({"success": True, "message": f"Student record for '{name}' was deleted."}), 200

# --- CIRCULATION (ISSUE & RETURN) ENDPOINTS ---

@api_bp.route("/issue", methods=["POST"])
def issue_book():
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Admin privileges required."}), 403

    data = request.get_json(silent=True) or request.form
    book_id = data.get("book_id")
    student_id = data.get("student_id")
    due_date_str = data.get("due_date")
    notes = (data.get("notes") or "").strip()

    try:
        book_id = int(book_id)
        student_id = int(student_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Valid Book and Student must be selected."}), 400

    if not due_date_str:
        return jsonify({"success": False, "message": "Due date is required."}), 400

    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "message": "Invalid due date format (YYYY-MM-DD required)."}), 400

    if due_date < date.today():
        return jsonify({"success": False, "message": "Due date cannot be in the past."}), 400

    try:
        book = db.session.get(Book, book_id)
        student = db.session.get(Student, student_id)

        if not book:
            return jsonify({"success": False, "message": "Selected book does not exist."}), 404
        if not student:
            return jsonify({"success": False, "message": "Selected student does not exist."}), 404
        if book.available_copies <= 0:
            return jsonify({"success": False, "message": f"Cannot issue '{book.title}': No copies available."}), 400

        already_borrowed = BorrowRecord.query.filter_by(book_id=book.id, student_id=student.id, status="issued").first()
        if already_borrowed:
            return jsonify({"success": False, "message": f"Student '{student.full_name}' already has an active copy of this book."}), 400

        record = BorrowRecord(
            book_id=book.id,
            student_id=student.id,
            issue_date=date.today(),
            due_date=due_date,
            status="issued",
            notes=notes if notes else None
        )
        book.available_copies -= 1
        db.session.add(record)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Book '{book.title}' issued to {student.full_name} (Due: {due_date}).",
            "record": serialize_record(record)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Database transaction failed: {str(e)}"}), 500


@api_bp.route("/issued", methods=["GET"])
def active_issues():
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Admin privileges required."}), 403

    query_str = (request.args.get("q") or "").strip()
    status_filter = request.args.get("filter", "all")
    today = date.today()

    borrows_query = BorrowRecord.query.filter_by(status="issued")
    if query_str:
        borrows_query = borrows_query.join(Book).join(Student).filter(
            or_(
                Book.title.ilike(f"%{query_str}%"),
                Student.full_name.ilike(f"%{query_str}%"),
                Student.student_id_number.ilike(f"%{query_str}%")
            )
        )

    if status_filter == "overdue":
        borrows_query = borrows_query.filter(BorrowRecord.due_date < today)
    elif status_filter == "ontime":
        borrows_query = borrows_query.filter(BorrowRecord.due_date >= today)

    records = borrows_query.order_by(BorrowRecord.due_date.asc()).all()
    return jsonify({
        "records": [serialize_record(r, today) for r in records],
        "total": len(records)
    }), 200


@api_bp.route("/return/<int:record_id>", methods=["POST"])
def return_book(record_id):
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Admin privileges required."}), 403

    record = db.session.get(BorrowRecord, record_id)
    if not record:
        return jsonify({"success": False, "message": "Borrow record not found."}), 404

    if record.status == "returned":
        return jsonify({"success": False, "message": "This book transaction is already recorded as returned."}), 400

    try:
        record.status = "returned"
        record.return_date = date.today()

        book = record.book
        if book and book.available_copies < book.total_copies:
            book.available_copies += 1

        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"Book '{book.title}' was marked as returned by {record.student.full_name}.",
            "record": serialize_record(record)
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Return transaction failed: {str(e)}"}), 500


@api_bp.route("/history", methods=["GET"])
def history():
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Admin privileges required."}), 403

    status_filter = (request.args.get("status") or "").strip()
    query_str = (request.args.get("q") or "").strip()
    today = date.today()

    history_query = BorrowRecord.query.join(Book).join(Student)
    if query_str:
        history_query = history_query.filter(
            or_(
                Book.title.ilike(f"%{query_str}%"),
                Book.author.ilike(f"%{query_str}%"),
                Student.full_name.ilike(f"%{query_str}%"),
                Student.student_id_number.ilike(f"%{query_str}%")
            )
        )

    if status_filter == "issued":
        history_query = history_query.filter(BorrowRecord.status == "issued")
    elif status_filter == "returned":
        history_query = history_query.filter(BorrowRecord.status == "returned")
    elif status_filter == "overdue":
        history_query = history_query.filter(BorrowRecord.status == "issued", BorrowRecord.due_date < today)

    records = history_query.order_by(BorrowRecord.id.desc()).all()
    return jsonify({
        "records": [serialize_record(r, today) for r in records],
        "total": len(records)
    }), 200

# --- STUDENT PORTAL ENDPOINTS ---

@api_bp.route("/student/dashboard", methods=["GET"])
def student_dashboard():
    if session.get("user_role") != "student":
        return jsonify({"success": False, "message": "Student account required."}), 403

    student_id = session.get("student_id")
    student = Student.query.filter_by(user_id=session.get("user_id")).first() if not student_id else db.session.get(Student, student_id)
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    today = date.today()
    active_borrows = BorrowRecord.query.filter_by(student_id=student.id, status="issued").order_by(BorrowRecord.due_date.asc()).all()
    overdue_count = sum(1 for b in active_borrows if b.due_date < today)
    total_borrowed = BorrowRecord.query.filter_by(student_id=student.id).count()
    recent_history = BorrowRecord.query.filter_by(student_id=student.id).order_by(BorrowRecord.id.desc()).limit(5).all()

    return jsonify({
        "student": serialize_student(student),
        "active_borrows": [serialize_record(r, today) for r in active_borrows],
        "overdue_count": overdue_count,
        "total_borrowed": total_borrowed,
        "recent_history": [serialize_record(r, today) for r in recent_history]
    }), 200


@api_bp.route("/student/my-books", methods=["GET"])
def student_my_books():
    if session.get("user_role") != "student":
        return jsonify({"success": False, "message": "Student account required."}), 403

    student_id = session.get("student_id")
    student = Student.query.filter_by(user_id=session.get("user_id")).first() if not student_id else db.session.get(Student, student_id)
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    today = date.today()
    records = BorrowRecord.query.filter_by(student_id=student.id, status="issued").order_by(BorrowRecord.due_date.asc()).all()
    return jsonify({
        "records": [serialize_record(r, today) for r in records],
        "total": len(records)
    }), 200


@api_bp.route("/student/history", methods=["GET"])
def student_history():
    if session.get("user_role") != "student":
        return jsonify({"success": False, "message": "Student account required."}), 403

    student_id = session.get("student_id")
    student = Student.query.filter_by(user_id=session.get("user_id")).first() if not student_id else db.session.get(Student, student_id)
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    today = date.today()
    records = BorrowRecord.query.filter_by(student_id=student.id).order_by(BorrowRecord.id.desc()).all()
    return jsonify({
        "records": [serialize_record(r, today) for r in records],
        "total": len(records)
    }), 200
