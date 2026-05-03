"""WhatsApp notification service via Twilio (or mock if unconfigured)."""

from __future__ import annotations

import logging
from datetime import date as date_t, timedelta

from app.config import get_settings

log = logging.getLogger("parikshamitra.whatsapp")


async def send_crisis_alert(
    parent_phone: str,
    parent_name: str,
    student_name: str,
    trigger_message: str,
) -> dict:
    """Sent immediately when crisis language is detected in MindMitra chat."""
    s = get_settings()
    excerpt = trigger_message[:120].replace("\n", " ")
    message = (
        f"🚨 ParikshaMitra — URGENT Alert\n\n"
        f"Dear {parent_name},\n\n"
        f"Your child {student_name} may be in distress. Our AI companion detected language "
        f"that may indicate a mental health crisis.\n\n"
        f'Message excerpt: "{excerpt}..."\n\n'
        f"Please check on {student_name} immediately.\n\n"
        f"If they are in immediate danger, call 112.\n"
        f"Mental health support: iCall 9152987821 (free, Mon–Sat 8am–10pm)\n\n"
        f"— ParikshaMitra AI Study Companion"
    )
    if s.twilio_account_sid and s.twilio_auth_token:
        result = await _send_twilio(parent_phone, message, s)
    else:
        log.warning("WhatsApp not configured. Crisis alert would send to %s", parent_phone)
        result = {"status": "mock", "message": message}
    log.warning(
        "CRISIS ALERT fired for student=%s parent=%s status=%s",
        student_name, parent_phone, result.get("status"),
    )
    return result


async def send_parent_alert(
    parent_phone: str,
    parent_name: str,
    student_name: str,
    consecutive_misses: int,
    missed_topics: list[str],
) -> dict:
    s = get_settings()
    message = (
        f"ParikshaMitra Alert\n\n"
        f"Dear {parent_name},\n\n"
        f"{student_name} has missed {consecutive_misses} consecutive study sessions.\n"
        f"Topics missed: {', '.join(missed_topics[:5])}\n\n"
        f"Please check in with them. Regular study is crucial for JEE preparation.\n\n"
        f"— ParikshaMitra AI Study Companion"
    )
    if s.twilio_account_sid and s.twilio_auth_token:
        return await _send_twilio(parent_phone, message, s)
    log.warning("WhatsApp not configured. Would send to %s: %s", parent_phone, message)
    return {"status": "mock", "message": message}


async def _send_twilio(phone: str, message: str, s) -> dict:
    import httpx
    url = f"https://api.twilio.com/2010-04-01/Accounts/{s.twilio_account_sid}/Messages.json"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            auth=(s.twilio_account_sid, s.twilio_auth_token),
            data={
                "From": s.twilio_whatsapp_from,
                "To": f"whatsapp:+{phone.lstrip('+')}",
                "Body": message,
            },
        )
        return {
            "status": "sent" if resp.is_success else "failed",
            "sid": resp.json().get("sid", ""),
            "code": resp.status_code,
        }


def cooldown_ok(last_alert_date: str | None, cooldown_hours: int) -> bool:
    if not last_alert_date:
        return True
    try:
        last = date_t.fromisoformat(last_alert_date)
        return (date_t.today() - last).total_seconds() / 3600 >= cooldown_hours
    except ValueError:
        return True
