"""
Send OTP / transactional email via Resend, SMTP, or dev-only console logging.

Environment (pick one path for production):
- RESEND_API_KEY + RESEND_FROM  → Resend HTTP API
- SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM → TLS SMTP
- TADAA_DEV_LOG_OTP=1          → print OTP to server stdout (local dev only)
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.text import MIMEText


class EmailNotConfiguredError(RuntimeError):
    pass


def send_otp_email(to_email: str, code: str, subject: str = "Your TADAA verification code") -> None:
    body_text = (
        f"Your verification code is: {code}\n\n"
        "It expires in 10 minutes. If you did not request this, ignore this message."
    )
    body_html = (
        f"<p>Your verification code is:</p>"
        f"<p style=\"font-size:24px;font-weight:bold;letter-spacing:4px\">{code}</p>"
        "<p>This code expires in 10 minutes.</p>"
    )

    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    if resend_key:
        _send_resend(
            resend_key,
            os.environ.get("RESEND_FROM", "onboarding@resend.dev"),
            to_email,
            subject,
            body_text,
            body_html,
        )
        return

    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    if smtp_host:
        _send_smtp(
            smtp_host,
            int(os.environ.get("SMTP_PORT", "587")),
            os.environ.get("SMTP_USER", ""),
            os.environ.get("SMTP_PASSWORD", ""),
            os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", "noreply@localhost")),
            to_email,
            subject,
            body_text,
        )
        return

    if os.environ.get("TADAA_DEV_LOG_OTP", "").lower() in ("1", "true", "yes"):
        print(f"[TADAA DEV OTP] to={to_email} code={code}", flush=True)
        return

    raise EmailNotConfiguredError(
        "No email provider configured. Set RESEND_API_KEY, or SMTP_*, "
        "or TADAA_DEV_LOG_OTP=1 for local development."
    )


def _send_resend(
    api_key: str,
    from_addr: str,
    to_email: str,
    subject: str,
    text: str,
    html: str,
) -> None:
    try:
        import httpx
    except ImportError as e:
        raise EmailNotConfiguredError("httpx is required for Resend. pip install httpx") from e

    r = httpx.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": from_addr,
            "to": [to_email],
            "subject": subject,
            "text": text,
            "html": html,
        },
        timeout=30.0,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Resend API error {r.status_code}: {r.text}")


def _send_smtp(
    host: str,
    port: int,
    user: str,
    password: str,
    from_addr: str,
    to_email: str,
    subject: str,
    body: str,
) -> None:
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls(context=context)
        if user:
            server.login(user, password)
        server.sendmail(from_addr, [to_email], msg.as_string())
