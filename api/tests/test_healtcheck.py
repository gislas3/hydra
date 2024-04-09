from django.test import TestCase
from django.test import Client


class HealthcheckTestView(TestCase):
    def test_healthcheck(self):
        client = Client()
        response = client.get("/api/healthcheck/")
        self.assertEqual(response.status_code, 200)