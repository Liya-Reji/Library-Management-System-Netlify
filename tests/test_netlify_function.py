import json
from unittest import TestCase
from netlify.functions.api import wsgi_handler, get_flask_app

class TestNetlifyFunction(TestCase):

    def setUp(self):
        self.app = get_flask_app()

    def test_netlify_function_get_stats(self):
        event = {
            "httpMethod": "GET",
            "path": "/.netlify/functions/api/stats",
            "headers": {
                "accept": "application/json"
            },
            "queryStringParameters": {},
            "body": ""
        }
        response = wsgi_handler(self.app, event, None)
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("total_titles", response["body"])

    def test_netlify_function_get_books(self):
        event = {
            "httpMethod": "GET",
            "path": "/api/books",
            "headers": {
                "accept": "application/json"
            },
            "queryStringParameters": {"q": ""},
            "body": ""
        }
        response = wsgi_handler(self.app, event, None)
        self.assertEqual(response["statusCode"], 200)
        data = json.loads(response["body"])
        self.assertIn("books", data)

    def test_netlify_function_login_bad_credentials(self):
        event = {
            "httpMethod": "POST",
            "path": "/api/auth/login",
            "headers": {
                "content-type": "application/json",
                "accept": "application/json"
            },
            "queryStringParameters": {},
            "body": json.dumps({"identifier": "wrong", "password": "wrong"})
        }
        response = wsgi_handler(self.app, event, None)
        self.assertEqual(response["statusCode"], 401)
        data = json.loads(response["body"])
        self.assertFalse(data["success"])

    def test_netlify_function_login_admin_success(self):
        from netlify.functions.api import ensure_database_ready
        ensure_database_ready(self.app)

        event = {
            "httpMethod": "POST",
            "path": "/api/auth/login",
            "headers": {
                "content-type": "application/json",
                "accept": "application/json"
            },
            "queryStringParameters": {},
            "body": json.dumps({"identifier": "admin", "password": "admin123"})
        }
        response = wsgi_handler(self.app, event, None)
        self.assertEqual(response["statusCode"], 200)
        data = json.loads(response["body"])
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["role"], "admin")
        self.assertIn("Set-Cookie", response["headers"])

    def test_netlify_function_login_rewrite_routing_with_rawurl(self):
        """Simulate Netlify rewrite where event['path'] is the function name and rawUrl contains the original URI."""
        from netlify.functions.api import ensure_database_ready
        ensure_database_ready(self.app)

        event = {
            "httpMethod": "POST",
            "path": "/.netlify/functions/api",
            "rawUrl": "https://library-lms-demo.netlify.app/api/auth/login",
            "headers": {
                "content-type": "application/json",
                "accept": "application/json"
            },
            "queryStringParameters": {},
            "body": json.dumps({"identifier": "admin", "password": "admin123"})
        }
        response = wsgi_handler(self.app, event, None)
        self.assertEqual(response["statusCode"], 200)
        data = json.loads(response["body"])
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["username"], "admin")

    def test_netlify_function_login_alias_endpoint(self):
        """Verify alias /api/login works seamlessly."""
        from netlify.functions.api import ensure_database_ready
        ensure_database_ready(self.app)

        event = {
            "httpMethod": "POST",
            "path": "/api/login",
            "headers": {
                "content-type": "application/json",
                "accept": "application/json"
            },
            "queryStringParameters": {},
            "body": json.dumps({"username": "admin", "password": "admin123"})
        }
        response = wsgi_handler(self.app, event, None)
        self.assertEqual(response["statusCode"], 200)
        data = json.loads(response["body"])
        self.assertTrue(data["success"])

    def test_netlify_function_api_root(self):
        """Verify root /api does not 404."""
        event = {
            "httpMethod": "GET",
            "path": "/api",
            "headers": {"accept": "application/json"},
            "queryStringParameters": {},
            "body": ""
        }
        response = wsgi_handler(self.app, event, None)
        self.assertEqual(response["statusCode"], 200)
        data = json.loads(response["body"])
        self.assertEqual(data["status"], "ok")
