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
