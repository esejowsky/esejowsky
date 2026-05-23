"""Best-effort alerts for new opportunities. Both channels are optional."""
import smtplib
from email.message import EmailMessage

import httpx

from app.config import get_settings


def _send_telegram(text: str, s) -> None:
    if not (s.notify_telegram_bot_token and s.notify_telegram_chat_id):
        return
    httpx.post(
        f"https://api.telegram.org/bot{s.notify_telegram_bot_token}/sendMessage",
        json={"chat_id": s.notify_telegram_chat_id, "text": text},
        timeout=15.0,
    )


def _send_email(text: str, s) -> None:
    if not (s.notify_smtp_host and s.notify_smtp_from and s.notify_smtp_to):
        return
    msg = EmailMessage()
    msg["Subject"] = "Allegro arbitrage — nowe okazje"
    msg["From"] = s.notify_smtp_from
    msg["To"] = s.notify_smtp_to
    msg.set_content(text)
    with smtplib.SMTP(s.notify_smtp_host, s.notify_smtp_port) as server:
        server.starttls()
        if s.notify_smtp_user:
            server.login(s.notify_smtp_user, s.notify_smtp_password)
        server.send_message(msg)


def notify(text: str) -> None:
    s = get_settings()
    for sender in (_send_telegram, _send_email):
        try:
            sender(text, s)
        except Exception as exc:  # noqa: BLE001 — alerts must never crash a scan
            print(f"[notify] {sender.__name__} failed: {exc}")
