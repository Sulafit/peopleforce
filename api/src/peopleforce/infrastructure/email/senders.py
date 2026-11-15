from html import escape
from typing import Protocol

import httpx
import structlog

log = structlog.get_logger()


class EmailDeliveryError(Exception):
    pass


class EmailSender(Protocol):
    async def send_magic_link(self, to: str, link: str, expires_minutes: int) -> None: ...


class ConsoleEmailSender:
    """Development only: prints the link instead of sending mail."""

    async def send_magic_link(self, to: str, link: str, expires_minutes: int) -> None:
        log.info("magic_link_email", to=to, link=link, expires_minutes=expires_minutes)


class ResendEmailSender:
    def __init__(self, api_key: str, sender: str) -> None:
        self._api_key = api_key
        self._sender = sender

    async def send_magic_link(self, to: str, link: str, expires_minutes: int) -> None:
        safe_link = escape(link, quote=True)
        html = (
            '<div style="font-family:system-ui,sans-serif;font-size:16px;line-height:1.5;color:#1d1b26">'
            '<h1 style="font-size:22px">Your PeopleForce sign-in link</h1>'
            "<p>Use the button below to open your freelance journey. "
            f"The link works once and expires in {expires_minutes} minutes.</p>"
            f'<p><a href="{safe_link}" style="display:inline-block;padding:12px 22px;'
            "border:3px solid #1d1b26;"
            'border-radius:16px;background:#ffc83d;color:#1d1b26;font-weight:700;text-decoration:none">'
            "Open my journey</a></p>"
            '<p style="font-size:14px;color:#55525f">If you did not ask for this email, you can ignore it. '
            "Nobody can sign in without opening the link.</p></div>"
        )
        text = (
            "Your PeopleForce sign-in link\n\n"
            f"Open your freelance journey: {link}\n\n"
            f"The link works once and expires in {expires_minutes} minutes.\n"
            "If you did not ask for this email, you can ignore it."
        )
        payload = {
            "from": self._sender,
            "to": [to],
            "subject": "Your PeopleForce sign-in link",
            "html": html,
            "text": text,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    json=payload,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
        except httpx.HTTPError as exc:
            raise EmailDeliveryError(f"resend unreachable: {exc}") from exc
        if response.status_code >= 400:
            # Body may echo the recipient; log status only.
            raise EmailDeliveryError(f"resend responded {response.status_code}")
