import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Student

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        if session.get("user_role") == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        identifier = (request.form.get("identifier") or "").strip()
        password = request.form.get("password", "")

        if not identifier or not password:
            flash("Please enter both username/email and password.", "danger")
            return render_template("login.html", identifier=identifier)

        user = User.query.filter(
            (User.username.ilike(identifier)) | (User.email.ilike(identifier))
        ).first()

        if not user or not user.check_password(password):
            flash("Invalid credentials. Please verify your username/email and password.", "danger")
            return render_template("login.html", identifier=identifier)

        # Successful login
        session.clear()
        session["user_id"] = user.id
        session["username"] = user.username
        session["user_role"] = user.role
        session["user_email"] = user.email

        if user.is_student() and user.student_profile:
            session["student_id"] = user.student_profile.id
            session["student_name"] = user.student_profile.full_name

        flash(f"Welcome back, {user.username}!", "success")
        next_page = request.args.get("next")

        if next_page and next_page.startswith("/"):
            return redirect(next_page)

        if user.is_admin():
            return redirect(url_for("admin.dashboard"))
        else:
            return redirect(url_for("student.dashboard"))

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("public.index"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        full_name = (request.form.get("full_name") or "").strip()
        student_id_number = (request.form.get("student_id_number") or "").strip().upper()
        email = (request.form.get("email") or "").strip().lower()
        department = (request.form.get("department") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        form_data = {
            "username": username,
            "full_name": full_name,
            "student_id_number": student_id_number,
            "email": email,
            "department": department,
            "phone": phone
        }

        # Validation
        if not all([username, full_name, student_id_number, email, department, password, confirm_password]):
            flash("All required fields must be filled out.", "danger")
            return render_template("register.html", form_data=form_data)

        if not EMAIL_REGEX.match(email):
            flash("Please enter a valid email address.", "danger")
            return render_template("register.html", form_data=form_data)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html", form_data=form_data)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html", form_data=form_data)

        # Uniqueness checks
        if User.query.filter_by(username=username).first():
            flash("Username is already taken. Please choose another.", "danger")
            return render_template("register.html", form_data=form_data)

        if User.query.filter_by(email=email).first() or Student.query.filter_by(email=email).first():
            flash("An account with this email address already exists.", "danger")
            return render_template("register.html", form_data=form_data)

        if Student.query.filter_by(student_id_number=student_id_number).first():
            flash(f"Student ID '{student_id_number}' is already registered.", "danger")
            return render_template("register.html", form_data=form_data)

        try:
            # Create user and student in one transaction
            new_user = User(
                username=username,
                email=email,
                role="student"
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()  # to obtain new_user.id

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

            flash("Registration successful! You can now log in with your credentials.", "success")
            return redirect(url_for("auth.login"))

        except Exception as e:
            db.session.rollback()
            flash(f"An unexpected error occurred during registration. Please try again.", "danger")
            return render_template("register.html", form_data=form_data)

    return render_template("register.html", form_data={})


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("public.index"))
