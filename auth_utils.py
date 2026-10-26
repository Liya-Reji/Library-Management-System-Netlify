import secrets
from functools import wraps
from flask import session, redirect, url_for, flash, request, abort, current_app

def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]

def validate_csrf():
    if current_app.config.get("TESTING") and not current_app.config.get("WTF_CSRF_ENABLED", False):
        return True
    
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        # Allow checking health checks or safe APIs if any
        if request.endpoint == "health" or request.path.startswith("/api/"):
            return True
        token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
        expected = session.get("csrf_token")
        if not expected or not token or not secrets.compare_digest(token, expected):
            abort(400, description="Invalid or missing CSRF token. Please submit the form again.")
    return True

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in as an administrator to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        if session.get("user_role") != "admin":
            flash("Access denied: Administrator privileges required.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access your student portal.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        if session.get("user_role") != "student":
            flash("Access denied: Student account required.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
