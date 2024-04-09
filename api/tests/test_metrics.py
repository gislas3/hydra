from django.test import TestCase
from django.test import Client


class MetricsTestView(TestCase):
    def setUp(self):
        self.metrics_url = "/api/metrics/"

    def test_metrics(self):
        client = Client()
        response = client.get(self.metrics_url)
        self.assertEqual(response.status_code, 200)

    def test_metrics_redirect(self):
        client = Client()
        response = client.get("/metrics/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.metrics_url)