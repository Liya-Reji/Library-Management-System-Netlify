from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from sqlalchemy import or_, func
from models import db, Book, Student, BorrowRecord, User
from auth_utils import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Apply admin_required to all routes in this blueprint
@admin_bp.before_request
def check_admin_access():
    return admin_required(lambda: None)()

# ----------------- DASHBOARD -----------------
@admin_bp.route("/dashboard")
def dashboard():
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

    recent_borrows = BorrowRecord.query.order_by(BorrowRecord.issue_date.desc(), BorrowRecord.id.desc()).limit(8).all()
    overdue_list = BorrowRecord.query.filter(
        BorrowRecord.status == "issued",
        BorrowRecord.due_date < today
    ).order_by(BorrowRecord.due_date.asc()).limit(5).all()

    return render_template(
        "admin/dashboard.html",
        total_titles=total_titles,
        total_copies=total_copies,
        available_copies=available_copies,
        currently_issued=currently_issued,
        total_students=total_students,
        overdue_count=overdue_count,
        recent_borrows=recent_borrows,
        overdue_list=overdue_list,
        today=today
    )

# ----------------- BOOK MANAGEMENT -----------------
@admin_bp.route("/books")
def books():
    query_str = (request.args.get("q") or "").strip()
    category_filter = (request.args.get("category") or "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 10

    books_query = Book.query

    if query_str:
        search_filter = or_(
            Book.title.ilike(f"%{query_str}%"),
            Book.author.ilike(f"%{query_str}%"),
            Book.isbn.ilike(f"%{query_str}%"),
            Book.publisher.ilike(f"%{query_str}%")
        )
        books_query = books_query.filter(search_filter)

    if category_filter:
        books_query = books_query.filter(Book.category == category_filter)

    pagination = books_query.order_by(Book.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    categories = [c[0] for c in db.session.query(Book.category).distinct().order_by(Book.category).all() if c[0]]

    return render_template(
        "admin/books.html",
        pagination=pagination,
        books=pagination.items,
        query_str=query_str,
        category_filter=category_filter,
        categories=categories
    )


@admin_bp.route("/books/add", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        author = (request.form.get("author") or "").strip()
        category = (request.form.get("category") or "").strip()
        isbn = (request.form.get("isbn") or "").strip()
        publisher = (request.form.get("publisher") or "").strip()
        total_copies_raw = request.form.get("total_copies", "1")

        if not title or not author or not category:
            flash("Title, Author, and Category are required fields.", "danger")
            return render_template("admin/book_form.html", is_edit=False, form=request.form)

        try:
            total_copies = int(total_copies_raw)
            if total_copies < 1:
                raise ValueError()
        except ValueError:
            flash("Total copies must be a positive integer (at least 1).", "danger")
            return render_template("admin/book_form.html", is_edit=False, form=request.form)

        new_book = Book(
            title=title,
            author=author,
            category=category,
            isbn=isbn if isbn else None,
            publisher=publisher if publisher else None,
            total_copies=total_copies,
            available_copies=total_copies
        )
        db.session.add(new_book)
        db.session.commit()

        flash(f"Book '{title}' added successfully!", "success")
        return redirect(url_for("admin.books"))

    return render_template("admin/book_form.html", is_edit=False, form={})


@admin_bp.route("/books/edit/<int:book_id>", methods=["GET", "POST"])
def edit_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for("admin.books"))

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        author = (request.form.get("author") or "").strip()
        category = (request.form.get("category") or "").strip()
        isbn = (request.form.get("isbn") or "").strip()
        publisher = (request.form.get("publisher") or "").strip()
        total_copies_raw = request.form.get("total_copies", str(book.total_copies))
        available_copies_raw = request.form.get("available_copies", str(book.available_copies))

        if not title or not author or not category:
            flash("Title, Author, and Category are required.", "danger")
            return render_template("admin/book_form.html", is_edit=True, book=book, form=request.form)

        try:
            new_total = int(total_copies_raw)
            new_available = int(available_copies_raw)
            if new_total < 1 or new_available < 0:
                raise ValueError()
        except ValueError:
            flash("Copies must be non-negative integers (total copies >= 1).", "danger")
            return render_template("admin/book_form.html", is_edit=True, book=book, form=request.form)

        if new_available > new_total:
            flash("Available copies cannot exceed total copies.", "danger")
            return render_template("admin/book_form.html", is_edit=True, book=book, form=request.form)

        # Check currently issued copies consistency
        active_issued = BorrowRecord.query.filter_by(book_id=book.id, status="issued").count()
        if new_total < active_issued:
            flash(f"Cannot reduce total copies below {active_issued} because {active_issued} copies are currently issued to students.", "danger")
            return render_template("admin/book_form.html", is_edit=True, book=book, form=request.form)

        book.title = title
        book.author = author
        book.category = category
        book.isbn = isbn if isbn else None
        book.publisher = publisher if publisher else None
        book.total_copies = new_total
        book.available_copies = new_available

        db.session.commit()
        flash(f"Book '{book.title}' updated successfully.", "success")
        return redirect(url_for("admin.books"))

    return render_template("admin/book_form.html", is_edit=True, book=book, form=book.__dict__)


@admin_bp.route("/books/delete/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for("admin.books"))

    # Check for active issued copies
    active_borrows = BorrowRecord.query.filter_by(book_id=book.id, status="issued").count()
    if active_borrows > 0:
        flash(f"Cannot delete '{book.title}' because {active_borrows} copy/copies are currently issued.", "danger")
        return redirect(url_for("admin.books"))

    title = book.title
    db.session.delete(book)
    db.session.commit()
    flash(f"Book '{title}' was removed from the library catalog.", "info")
    return redirect(url_for("admin.books"))

# ----------------- STUDENT MANAGEMENT -----------------
@admin_bp.route("/students")
def students():
    query_str = (request.args.get("q") or "").strip()
    dept_filter = (request.args.get("department") or "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 10

    students_query = Student.query

    if query_str:
        search_filter = or_(
            Student.full_name.ilike(f"%{query_str}%"),
            Student.student_id_number.ilike(f"%{query_str}%"),
            Student.email.ilike(f"%{query_str}%")
        )
        students_query = students_query.filter(search_filter)

    if dept_filter:
        students_query = students_query.filter(Student.department == dept_filter)

    pagination = students_query.order_by(Student.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    departments = [d[0] for d in db.session.query(Student.department).distinct().order_by(Student.department).all() if d[0]]

    return render_template(
        "admin/students.html",
        pagination=pagination,
        students=pagination.items,
        query_str=query_str,
        dept_filter=dept_filter,
        departments=departments
    )


@admin_bp.route("/students/add", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        student_id_number = (request.form.get("student_id_number") or "").strip().upper()
        email = (request.form.get("email") or "").strip().lower()
        department = (request.form.get("department") or "").strip()
        phone = (request.form.get("phone") or "").strip()

        if not full_name or not student_id_number or not email or not department:
            flash("Full Name, Student ID, Email, and Department are required.", "danger")
            return render_template("admin/student_form.html", is_edit=False, form=request.form)

        if Student.query.filter_by(student_id_number=student_id_number).first():
            flash(f"Student ID '{student_id_number}' already exists.", "danger")
            return render_template("admin/student_form.html", is_edit=False, form=request.form)

        if Student.query.filter_by(email=email).first() or User.query.filter_by(email=email).first():
            flash(f"Email '{email}' is already in use.", "danger")
            return render_template("admin/student_form.html", is_edit=False, form=request.form)

        try:
            # Also create corresponding login user account for student with default password: student123
            default_username = student_id_number.lower().replace("-", "_")
            user = User(
                username=default_username,
                email=email,
                role="student"
            )
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

            flash(f"Student '{full_name}' registered successfully! (Login username: {default_username}, password: student123)", "success")
            return redirect(url_for("admin.students"))

        except Exception as e:
            db.session.rollback()
            flash("Failed to register student. Please check the inputs.", "danger")
            return render_template("admin/student_form.html", is_edit=False, form=request.form)

    return render_template("admin/student_form.html", is_edit=False, form={})


@admin_bp.route("/students/edit/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    student = db.session.get(Student, student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("admin.students"))

    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        department = (request.form.get("department") or "").strip()
        phone = (request.form.get("phone") or "").strip()

        if not full_name or not email or not department:
            flash("Full Name, Email, and Department are required.", "danger")
            return render_template("admin/student_form.html", is_edit=True, student=student, form=request.form)

        existing = Student.query.filter(Student.email == email, Student.id != student.id).first()
        if existing:
            flash(f"Email '{email}' is already used by another student.", "danger")
            return render_template("admin/student_form.html", is_edit=True, student=student, form=request.form)

        student.full_name = full_name
        student.email = email
        student.department = department
        student.phone = phone if phone else None

        if student.user:
            student.user.email = email

        db.session.commit()
        flash(f"Student '{student.full_name}' updated successfully.", "success")
        return redirect(url_for("admin.students"))

    return render_template("admin/student_form.html", is_edit=True, student=student, form=student.__dict__)


@admin_bp.route("/students/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    student = db.session.get(Student, student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("admin.students"))

    active_borrows = BorrowRecord.query.filter_by(student_id=student.id, status="issued").count()
    if active_borrows > 0:
        flash(f"Cannot delete student '{student.full_name}' because they have {active_borrows} book(s) currently issued.", "danger")
        return redirect(url_for("admin.students"))

    user_to_delete = student.user
    name = student.full_name
    db.session.delete(student)
    if user_to_delete:
        db.session.delete(user_to_delete)
    db.session.commit()

    flash(f"Student record for '{name}' was deleted.", "info")
    return redirect(url_for("admin.students"))

# ----------------- BOOK ISSUE & RETURN -----------------
@admin_bp.route("/issue", methods=["GET", "POST"])
def issue_book():
    preselected_book_id = request.args.get("book_id", type=int)
    preselected_student_id = request.args.get("student_id", type=int)

    if request.method == "POST":
        book_id = request.form.get("book_id", type=int)
        student_id = request.form.get("student_id", type=int)
        due_date_str = request.form.get("due_date")
        notes = (request.form.get("notes") or "").strip()

        if not book_id or not student_id or not due_date_str:
            flash("Please select a book, a student, and a valid due date.", "danger")
            return redirect(url_for("admin.issue_book"))

        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid due date format. Please select a valid date.", "danger")
            return redirect(url_for("admin.issue_book"))

        if due_date < date.today():
            flash("Due date cannot be in the past.", "danger")
            return redirect(url_for("admin.issue_book"))

        # Database transaction with inventory check
        try:
            # Re-fetch book and student inside transaction
            book = db.session.get(Book, book_id)
            student = db.session.get(Student, student_id)

            if not book:
                flash("Selected book does not exist.", "danger")
                return redirect(url_for("admin.issue_book"))

            if not student:
                flash("Selected student does not exist.", "danger")
                return redirect(url_for("admin.issue_book"))

            if book.available_copies <= 0:
                flash(f"Cannot issue '{book.title}': No copies available right now.", "danger")
                return redirect(url_for("admin.issue_book"))

            # Optional guard: Check if student already has this exact book currently issued
            already_borrowed = BorrowRecord.query.filter_by(
                book_id=book.id,
                student_id=student.id,
                status="issued"
            ).first()
            if already_borrowed:
                flash(f"Student '{student.full_name}' already has an active issued copy of this book.", "warning")
                return redirect(url_for("admin.issue_book"))

            # Create borrow record
            record = BorrowRecord(
                book_id=book.id,
                student_id=student.id,
                issue_date=date.today(),
                due_date=due_date,
                status="issued",
                notes=notes if notes else None
            )

            # Atomic inventory reduction
            book.available_copies -= 1

            db.session.add(record)
            db.session.commit()

            flash(f"Book '{book.title}' successfully issued to {student.full_name} (Due: {due_date.strftime('%b %d, %Y')}).", "success")
            return redirect(url_for("admin.issued_books"))

        except Exception as e:
            db.session.rollback()
            flash(f"Database error while issuing book: {str(e)}", "danger")
            return redirect(url_for("admin.issue_book"))

    # GET request
    available_books = Book.query.filter(Book.available_copies > 0).order_by(Book.title).all()
    students_list = Student.query.order_by(Student.full_name).all()
    default_due_date = date.today() + timedelta(days=current_app.config.get("DEFAULT_LOAN_DAYS", 14))

    return render_template(
        "admin/issue_book.html",
        available_books=available_books,
        students=students_list,
        default_due_date=default_due_date.strftime("%Y-%m-%d"),
        preselected_book_id=preselected_book_id,
        preselected_student_id=preselected_student_id
    )


@admin_bp.route("/issued")
def issued_books():
    query_str = (request.args.get("q") or "").strip()
    status_filter = request.args.get("filter", "all")  # all, overdue, active
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

    return render_template(
        "admin/issued_books.html",
        records=records,
        today=today,
        query_str=query_str,
        status_filter=status_filter
    )


@admin_bp.route("/return/<int:record_id>", methods=["POST"])
def return_book(record_id):
    try:
        record = db.session.get(BorrowRecord, record_id)
        if not record:
            flash("Borrow record not found.", "danger")
            return redirect(url_for("admin.issued_books"))

        # Prevent duplicate returns
        if record.status == "returned":
            flash("This book transaction was already recorded as returned.", "warning")
            return redirect(url_for("admin.issued_books"))

        # Update borrow record
        record.status = "returned"
        record.return_date = date.today()

        # Safely increment inventory without exceeding total_copies
        book = record.book
        if book.available_copies < book.total_copies:
            book.available_copies += 1

        db.session.commit()
        flash(f"Book '{book.title}' was successfully marked as returned by {record.student.full_name}.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Transaction failed: {str(e)}", "danger")

    return redirect(url_for("admin.issued_books"))


@admin_bp.route("/history")
def history():
    status_filter = (request.args.get("status") or "").strip()
    query_str = (request.args.get("q") or "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 15

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

    today = date.today()
    if status_filter == "issued":
        history_query = history_query.filter(BorrowRecord.status == "issued")
    elif status_filter == "returned":
        history_query = history_query.filter(BorrowRecord.status == "returned")
    elif status_filter == "overdue":
        history_query = history_query.filter(BorrowRecord.status == "issued", BorrowRecord.due_date < today)

    pagination = history_query.order_by(BorrowRecord.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "admin/history.html",
        pagination=pagination,
        records=pagination.items,
        status_filter=status_filter,
        query_str=query_str,
        today=today
    )
