from tests.base_test import BaseTestCase
from app import create_app

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
        app = create_app("development")
        self.assertFalse(app.config["TESTING"])
        self.assertTrue("library.db" in app.config["SQLALCHEMY_DATABASE_URI"] or "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"])
