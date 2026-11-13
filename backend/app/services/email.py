"""Transactional email via Brevo's HTTP API (Render free tier blocks SMTP ports)."""

from html import escape

import httpx

from app.config import settings

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def send_episode_email(to: str, title: str, summary: str, episode_url: str) -> None:
    html = f"""\
<div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#111">
  <p style="color:#666;font-size:13px;margin:0 0 8px">Your daily briefing is ready</p>
  <h2 style="margin:0 0 12px">{escape(title)}</h2>
  <p style="line-height:1.5">{escape(summary)}</p>
  <p style="margin:24px 0">
    <a href="{escape(episode_url)}"
       style="background:#111;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none">
      Listen to the episode
    </a>
  </p>
  <p style="color:#888;font-size:12px">Or open this link: {escape(episode_url)}</p>
</div>"""
    resp = httpx.post(
        BREVO_URL,
        headers={"api-key": settings.brevo_api_key, "accept": "application/json"},
        json={
            "sender": {"email": settings.email_from, "name": settings.email_from_name},
            "to": [{"email": to}],
            "subject": f"Your briefing: {title}",
            "htmlContent": html,
        },
        timeout=30.0,
    )
    resp.raise_for_status()
