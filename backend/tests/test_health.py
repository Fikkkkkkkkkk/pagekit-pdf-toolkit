"""Smoke test for the foundation API."""

import unittest

from app import create_app


class HealthTest(unittest.TestCase):
    def test_health(self):
        response = create_app().test_client().get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
