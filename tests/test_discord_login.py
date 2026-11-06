import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.error import HTTPError

from fastapi import BackgroundTasks, HTTPException

from app.api.routes import auth
from app.core import discord
from app.schemas.auth import LoginRequest


class DiscordNotificationTests(unittest.TestCase):
    def test_sends_login_text_in_embed_and_disables_mentions(self):
        response = MagicMock()
        response.status = 204
        context = MagicMock()
        context.__enter__.return_value = response

        with patch.object(discord, "urlopen", return_value=context) as open_url:
            asyncio.run(discord.send_login_notification("reader@example.com", "https://discord.com/api/webhooks/123/test-token", "448147540203012117"))

        request = open_url.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(payload["content"], "<@448147540203012117>")
        self.assertEqual(payload["embeds"], [{
            "title": "User Login",
            "description": "reader@example.com just logged in!",
            "color": 5814783,
        }])
        self.assertEqual(payload["attachments"], [])
        self.assertEqual(payload["allowed_mentions"], {"parse": [], "users": ["448147540203012117"]})
        self.assertEqual(open_url.call_args.kwargs["timeout"], 3)

    def test_skips_delivery_when_webhook_is_not_configured(self):
        with patch.object(discord, "urlopen") as open_url:
            asyncio.run(discord.send_login_notification("reader@example.com", None, None))
        open_url.assert_not_called()

    def test_forbidden_response_is_logged_without_retrying(self):
        forbidden = HTTPError("https://discord.com/api/webhooks/123/token", 403, "forbidden", {}, None)
        with patch.object(discord, "urlopen", side_effect=forbidden) as open_url:
            with self.assertLogs(discord.logger, level="WARNING") as captured:
                asyncio.run(discord.send_login_notification("reader@example.com", "https://discord.com/api/webhooks/123/token", "448147540203012117"))
        self.assertEqual(open_url.call_count, 1)
        self.assertIn("HTTP 403", captured.output[0])

    def test_discord_rate_limit_does_not_break_notification_caller(self):
        rate_limit = HTTPError("https://discord.com/api/webhooks/123/token", 429, "rate limited", {"Retry-After": "0.25"}, None)
        response = MagicMock()
        response.status = 204
        context = MagicMock()
        context.__enter__.return_value = response
        with patch.object(discord, "urlopen", side_effect=[rate_limit, context]) as open_url, patch.object(discord.asyncio, "sleep", new_callable=AsyncMock) as sleep:
            asyncio.run(discord.send_login_notification("reader@example.com", "https://discord.com/api/webhooks/123/token", "448147540203012117"))
        sleep.assert_awaited_once_with(0.25)
        self.assertEqual(open_url.call_count, 2)

    def test_successful_login_schedules_notification_after_authentication(self):
        user = MagicMock(id=42, email="reader@example.com", hashed_password="hashed")
        database = MagicMock()
        database.scalar.return_value = user
        background_tasks = BackgroundTasks()
        payload = LoginRequest(email="Reader@example.com", password="password")

        with patch.object(auth, "verify_password", return_value=True), patch.object(auth, "create_access_token", return_value="test-token"):
            token = auth.login(payload, background_tasks, database)

        self.assertEqual(token.access_token, "test-token")
        self.assertEqual(len(background_tasks.tasks), 1)
        task = background_tasks.tasks[0]
        self.assertIs(task.func, auth.send_login_notification)
        self.assertEqual(task.args[0], str(payload.email))
        self.assertEqual(bool(task.args[1]), bool(auth.settings.discord_webhook_url))
        self.assertEqual(bool(task.args[2]), bool(auth.settings.discord_uid))

    def test_failed_login_does_not_schedule_notification(self):
        database = MagicMock()
        database.scalar.return_value = None
        background_tasks = BackgroundTasks()

        with self.assertRaises(HTTPException) as error:
            auth.login(LoginRequest(email="missing@example.com", password="password"), background_tasks, database)

        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(background_tasks.tasks, [])


if __name__ == "__main__":
    unittest.main()
