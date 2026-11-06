import hashlib
import unittest
from unittest.mock import MagicMock

from fastapi import BackgroundTasks, HTTPException
from starlette.requests import Request

from app.api.routes.auth import register, request_access
from app.models.access_request import AccessRequest
from app.schemas.auth import AccessRequestCreate, UserCreate


def make_request():
    return Request({"type": "http", "http_version": "1.1", "method": "POST", "scheme": "http", "path": "/", "raw_path": b"/", "query_string": b"", "headers": [], "client": ("127.0.0.1", 1234), "server": ("test", 80)})


class AccessRequestTests(unittest.TestCase):
    def test_request_persists_only_hash_and_schedules_discord_notification(self):
        db = MagicMock()
        db.scalar.return_value = None
        tasks = BackgroundTasks()

        result = request_access(make_request(), AccessRequestCreate(email="Reader@example.com"), tasks, db)

        self.assertIn("1–3 business days", result.message)
        stored = db.add.call_args.args[0]
        self.assertIsInstance(stored, AccessRequest)
        self.assertEqual(stored.email, "reader@example.com")
        self.assertEqual(len(stored.invite_code_hash), 64)
        task = tasks.tasks[0]
        self.assertEqual(task.func.__name__, "send_access_request_notification")
        self.assertEqual(task.args[0], "reader@example.com")
        self.assertEqual(hashlib.sha256(task.args[1].encode()).hexdigest(), stored.invite_code_hash)

    def test_fifth_wrong_code_locks_email(self):
        request = AccessRequest(email="reader@example.com", invite_code_hash=hashlib.sha256(b"right").hexdigest(), failed_attempts=4)
        db = MagicMock()
        db.scalar.side_effect = [request]

        with self.assertRaises(HTTPException) as error:
            register(UserCreate(email="reader@example.com", invite_code="wrong", username="reader_1", password="twelvecharacters"), db)

        self.assertEqual(error.exception.status_code, 423)
        self.assertEqual(request.failed_attempts, 5)
        self.assertIsNotNone(request.locked_at)
        db.commit.assert_called_once()

    def test_existing_access_request_is_not_resubmitted(self):
        db = MagicMock()
        db.scalar.side_effect = [None, AccessRequest(email="reader@example.com", invite_code_hash="a" * 64)]

        with self.assertRaises(HTTPException) as error:
            request_access(make_request(), AccessRequestCreate(email="reader@example.com"), BackgroundTasks(), db)

        self.assertEqual(error.exception.status_code, 409)
        db.add.assert_not_called()


if __name__ == "__main__":
    unittest.main()
