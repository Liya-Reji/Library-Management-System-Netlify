"""
Netlify Serverless Function Handler for Library Management System.
Converts AWS Lambda / Netlify API Gateway events into WSGI requests for Flask.
Handles automatic schema creation and ensures default administrator credentials exist.
"""
import io
import os
import sys
import base64
import urllib.parse
from datetime import date, timedelta

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from models import db, User, Student, Book, BorrowRecord

_flask_app = None
_db_initialized = False

def get_flask_app():
    """Lazy initialize Flask application."""
    global _flask_app
    if _flask_app is None:
        env_mode = "production" if os.getenv("DATABASE_URL") else "development"
        _flask_app = create_app(env_mode)
    return _flask_app

def ensure_database_ready(app):
    """Ensure database tables exist and default admin account is populated on first invocation."""
    global _db_initialized
    if _db_initialized:
        return

    try:
        with app.app_context():
            db.create_all()

            # Ensure Administrator exists
            admin = User.query.filter_by(role="admin").first()
            if not admin:
                admin_user = os.getenv("ADMIN_USERNAME", "admin")
                admin_email = os.getenv("ADMIN_EMAIL", "admin@library.college.edu")
                admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")

                new_admin = User(
                    username=admin_user,
                    email=admin_email,
                    role="admin"
                )
                new_admin.set_password(admin_pass)
                db.session.add(new_admin)
                db.session.commit()
                print(f"[+] Initialized default administrator: {admin_user}")

            # Ensure default Student demo account exists
            student_user = User.query.filter_by(role="student").first()
            if not student_user:
                new_student = User(
                    username="student1",
                    email="student1@college.edu",
                    role="student"
                )
                new_student.set_password("student123")
                db.session.add(new_student)
                db.session.flush()

                student_profile = Student(
                    user_id=new_student.id,
                    roll_number="CS2026-001",
                    full_name="Alex Johnson",
                    department="Computer Science",
                    phone="9876543210"
                )
                db.session.add(student_profile)
                db.session.commit()
                print("[+] Initialized default student: student1")

            # Ensure sample books exist if catalog is completely empty
            if Book.query.count() == 0:
                sample_books = [
                    Book(title="Introduction to Algorithms (4th Edition)", author="Thomas H. Cormen", category="Computer Science", isbn="978-0262046305", total_copies=5, available_copies=5),
                    Book(title="Clean Code: Agile Software Craftsmanship", author="Robert C. Martin", category="Software Engineering", isbn="978-0132350884", total_copies=4, available_copies=4),
                    Book(title="Operating System Concepts (10th Edition)", author="Abraham Silberschatz", category="Computer Science", isbn="978-1119456339", total_copies=3, available_copies=3),
                    Book(title="Database System Concepts (7th Edition)", author="Abraham Silberschatz", category="Database Systems", isbn="978-0078022159", total_copies=4, available_copies=4),
                    Book(title="Python Crash Course (3rd Edition)", author="Eric Matthes", category="Programming", isbn="978-1718502703", total_copies=6, available_copies=6),
                    Book(title="Flask Web Development (2nd Edition)", author="Miguel Grinberg", category="Web Development", isbn="978-1491991732", total_copies=4, available_copies=4)
                ]
                db.session.add_all(sample_books)
                db.session.commit()
                print("[+] Seeded initial demonstration books.")

            _db_initialized = True
    except Exception as e:
        print(f"[!] Database auto-init error: {e}")

def wsgi_handler(app, event, context):
    """Bridge AWS Lambda / Netlify event to WSGI application."""
    method = event.get("httpMethod", "GET")
    path = event.get("path", "/")

    # Netlify function redirects from /.netlify/functions/api/... to /api/...
    if path.startswith("/.netlify/functions/api"):
        path = path.replace("/.netlify/functions/api", "/api", 1)
    elif not path.startswith("/api"):
        path = f"/api{path}"

    query_params = event.get("queryStringParameters") or {}
    query_string = urllib.parse.urlencode(query_params)

    headers = event.get("headers") or {}
    body = event.get("body") or ""

    if event.get("isBase64Encoded", False):
        body_bytes = base64.b64decode(body)
    else:
        body_bytes = body.encode("utf-8")

    environ = {
        "REQUEST_METHOD": method,
        "SCRIPT_NAME": "",
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "443",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": headers.get("x-forwarded-proto", "https"),
        "wsgi.input": io.BytesIO(body_bytes),
        "wsgi.errors": sys.stderr,
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }

    if "content-type" in headers:
        environ["CONTENT_TYPE"] = headers["content-type"]
    if "content-length" in headers:
        environ["CONTENT_LENGTH"] = headers["content-length"]
    else:
        environ["CONTENT_LENGTH"] = str(len(body_bytes))

    for key, value in headers.items():
        key_upper = key.upper().replace("-", "_")
        if key_upper not in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            environ[f"HTTP_{key_upper}"] = value

    response_status = []
    response_headers = []

    def start_response(status, res_headers, exc_info=None):
        response_status.append(status)
        response_headers.extend(res_headers)

    app_iter = app(environ, start_response)
    response_body = b"".join(app_iter)

    status_code = int(response_status[0].split(" ")[0]) if response_status else 200

    out_headers = {}
    multi_headers = {}

    for key, val in response_headers:
        if key.lower() == "set-cookie":
            multi_headers.setdefault("Set-Cookie", []).append(val)
        else:
            out_headers[key] = val

    result = {
        "statusCode": status_code,
        "headers": out_headers,
        "body": response_body.decode("utf-8", errors="replace"),
        "isBase64Encoded": False
    }

    if multi_headers:
        result["multiValueHeaders"] = multi_headers

    return result

def handler(event, context):
    app = get_flask_app()
    ensure_database_ready(app)
    return wsgi_handler(app, event, context)
