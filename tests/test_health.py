import os
from unittest import mock
from tests.base_test import BaseTestCase
from app import create_app
from config import normalize_database_url

class TestHealthAndStartup(BaseTestCase):

    def test_health_endpoint(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        json_data = resp.get_json()
        self.assertEqual(json_data["status"], "healthy")
        self.assertEqual(json_data["database"], "connected")
        self.assertIn("timestamp", json_data)

    def test_landing_page_renders(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Modern Library Management", resp.data)

    def test_app_config_testing_mode(self):
        app = create_app("testing")
        self.assertTrue(app.config["TESTING"])
        self.assertFalse(app.config["DEBUG"])
        self.assertEqual(app.config["SQLALCHEMY_DATABASE_URI"], "sqlite:///:memory:")

    def test_app_config_development_mode(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            app = create_app("development")
            self.assertFalse(app.config["TESTING"])
            self.assertTrue("library.db" in app.config["SQLALCHEMY_DATABASE_URI"] or "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"])

    def test_production_fails_fast_when_database_url_missing(self):
        with mock.patch.dict(os.environ, {"DATABASE_URL": ""}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                create_app("production")
            self.assertIn("DATABASE_URL environment variable is required in production", str(ctx.exception))

    def test_production_normalizes_postgres_prefix(self):
        raw = "postgres://lib_user:secret_pass@db.render.com:5432/lib_db"
        with mock.patch.dict(os.environ, {"DATABASE_URL": raw}):
            with mock.patch("models.db.init_app"):
                app = create_app("production")
                self.assertEqual(
                    app.config["SQLALCHEMY_DATABASE_URI"],
                    "postgresql://lib_user:secret_pass@db.render.com:5432/lib_db"
                )

    def test_url_normalizer_handles_various_formats(self):
        self.assertIsNone(normalize_database_url(None))
        self.assertIsNone(normalize_database_url(""))
        self.assertEqual(
            normalize_database_url("postgres://u:p@host/db"),
            "postgresql://u:p@host/db"
        )
        self.assertEqual(
            normalize_database_url("postgresql://u:p@host/db"),
            "postgresql://u:p@host/db"
        )
