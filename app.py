import os
from flask import Flask, render_template, jsonify
from config import config_by_name, get_database_url
from models import db
from auth_utils import generate_csrf_token, validate_csrf
from routes.public_routes import public_bp
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.student_routes import student_bp
from routes.api_routes import api_bp

def create_app(config_name=None):
    if not config_name:
        config_name = os.getenv("FLASK_ENV", "development").lower()
        if config_name not in config_by_name:
            config_name = "default"

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Enforce database requirements in production
    if config_name == "production":
        db_uri = get_database_url(is_production=True)
        app.config["SQLALCHEMY_DATABASE_URI"] = db_uri

    # Initialize extensions
    db.init_app(app)

    # CORS support for Netlify and cross-origin frontend
    @app.after_request
    def add_cors_headers(response):
        from flask import request
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        return response

    @app.before_request
    def handle_options_preflight():
        from flask import request
        if request.method == "OPTIONS":
            response = app.make_default_options_response()
            origin = request.headers.get("Origin")
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
            return response

    # CSRF hook
    @app.before_request
    def handle_csrf():
        validate_csrf()

    # Context processors
    @app.context_processor
    def inject_helpers():
        return {
            "csrf_token": generate_csrf_token()
        }

    # Register blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(api_bp)

    # Error handlers
    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html", message=getattr(e, "description", "Bad Request")), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html", message=getattr(e, "description", "Access Denied")), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    # CLI command for safe manual DB schema creation
    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables safely without dropping existing data."""
        db.create_all()
        print("Database tables initialized successfully.")

    return app

# Application instance for Gunicorn / WSGI
app = create_app(os.getenv("FLASK_ENV", "production" if os.getenv("RENDER") else "development"))

if __name__ == "__main__":
    # In local development, ensure tables exist automatically
    with app.app_context():
        db.create_all()
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
