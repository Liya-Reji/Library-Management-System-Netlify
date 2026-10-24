from datetime import datetime, timezone
from flask import Blueprint, render_template, jsonify
from sqlalchemy import text
from models import db, Book, Student, BorrowRecord

public_bp = Blueprint("public", __name__)

@public_bp.route("/")
def index():
    # Public catalog snapshot
    featured_books = Book.query.order_by(Book.date_added.desc()).limit(6).all()
    stats = {
        "total_titles": Book.query.count(),
        "total_copies": db.session.query(db.func.sum(Book.total_copies)).scalar() or 0,
        "available_copies": db.session.query(db.func.sum(Book.available_copies)).scalar() or 0,
        "students_count": Student.query.count()
    }
    return render_template("index.html", featured_books=featured_books, stats=stats)


@public_bp.route("/health")
def health():
    db_status = "connected"
    http_code = 200
    try:
        # Perform lightweight DB query
        db.session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        http_code = 503

    return jsonify({
        "status": "healthy" if http_code == 200 else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "version": "1.0.0"
    }), http_code
