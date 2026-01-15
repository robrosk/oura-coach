import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import create_jwt_token, create_oauth_state, decode_oauth_state


class OAuthStateTests(unittest.TestCase):
    def test_oauth_state_round_trip(self):
        token = create_oauth_state({"purpose": "oura", "user_id": "user-123"})
        payload = decode_oauth_state(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("purpose"), "oura")
        self.assertEqual(payload.get("user_id"), "user-123")

    def test_oauth_state_rejects_wrong_type(self):
        jwt_token = create_jwt_token("user-1", "user@example.com")
        payload = decode_oauth_state(jwt_token)
        self.assertIsNone(payload)

    def test_oauth_state_expired(self):
        token = create_oauth_state({"purpose": "google"}, expires_minutes=-1)
        payload = decode_oauth_state(token)
        self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()
