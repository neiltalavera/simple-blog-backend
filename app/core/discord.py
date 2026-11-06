import asyncio
import json
import logging
import math
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


def _retry_after_seconds(error: HTTPError) -> float | None:
    header = error.headers.get("Retry-After") if error.headers else None
    try:
        delay = float(header) if header is not None else None
    except (TypeError, ValueError):
        delay = None

    if delay is None:
        try:
            body = json.loads(error.read())
            delay = float(body.get("retry_after"))
        except (TypeError, ValueError, json.JSONDecodeError, AttributeError):
            return None

    return delay if math.isfinite(delay) and delay >= 0 else None


async def send_login_notification(email: str, webhook_url: str | None, discord_uid: str | None) -> None:
    """Post one login embed to Discord. Notification failures do not affect sign-in."""
    await send_notification("User Login", f"{email} just logged in!", webhook_url, discord_uid)


async def send_access_request_notification(email: str, invite_code: str, webhook_url: str | None, discord_uid: str | None) -> None:
    """Send the requester email and invite code to the configured Discord webhook."""
    await send_notification("New Access Request", f"Email: {email}\nInvite code: {invite_code}", webhook_url, discord_uid)


async def send_notification(title: str, description: str, webhook_url: str | None, discord_uid: str | None) -> None:
    """Post one embed to Discord. Notification failures do not affect the caller."""
    if not webhook_url:
        return

    has_uid = bool(discord_uid and discord_uid.isascii() and discord_uid.isdigit())
    payload = {
        "content": f"<@{discord_uid}>" if has_uid else "",
        "embeds": [{
            "title": title,
            "description": description,
            "color": 5814783,
        }],
        "attachments": [],
        "allowed_mentions": {"parse": [], "users": [discord_uid]} if has_uid else {"parse": []},
    }
    try:
        request = Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "fastapi-blog/1.0"},
            method="POST",
        )
    except (TypeError, ValueError):
        logger.warning("Discord login notification URL is invalid")
        return
    for attempt in range(2):
        try:
            with await asyncio.to_thread(urlopen, request, timeout=3) as response:
                if not 200 <= response.status < 300:
                    logger.warning("Discord login notification returned HTTP %s", response.status)
            return
        except HTTPError as error:
            if error.code == 429 and attempt == 0:
                delay = await asyncio.to_thread(_retry_after_seconds, error)
                error.close()
                if delay is not None:
                    # Follow Discord's Retry-After value, then make one bounded retry.
                    await asyncio.sleep(delay)
                    continue
            logger.warning("Discord login notification returned HTTP %s", error.code)
            error.close()
            return
        except (URLError, TimeoutError, OSError, ValueError):
            # Do not log the request URL: Discord webhook URLs contain the secret token.
            logger.warning("Discord login notification could not be delivered")
            return
