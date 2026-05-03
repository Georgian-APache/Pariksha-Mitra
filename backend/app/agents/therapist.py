"""MindMitra — direct conversational mental health companion for exam-prep students."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any

from app.agents.llm import gemini_chat, groq_chat
from app.config import APIKeys, get_settings

log = logging.getLogger("parikshamitra.therapist")

# ---------------------------------------------------------------------------
# Crisis detection — runs on the current message only, never skipped
# ---------------------------------------------------------------------------

_CRISIS_PATTERNS = re.compile(
    r"\b(kill\w*\s*(my|him|her|them)?self|suicide|suicidal|want\s+to\s+die|end\s+(my|it\s+all)|"
    r"no\s+reason\s+to\s+live|can'?t\s+(go\s+on|take\s+it|do\s+this)|"
    r"harm\s+myself|self.?harm|hurt\s+myself|don'?t\s+want\s+to\s+be\s+here|"
    r"feel\s+like\s+(dying|ending\s+it)|rather\s+(be\s+dead|not\s+exist)|"
    r"don'?t\s+want\s+to\s+(live|exist)|wish\s+I\s+(was|were)\s+dead)\b",
    re.IGNORECASE,
)

_DISTRESS_PATTERNS = re.compile(
    r"\b(hopeless|worthless|useless|failure|give\s+up|can'?t\s+cope|falling\s+apart|"
    r"breaking\s+down|exhausted|burned?\s+out|depressed|anxious|panic|terrified|"
    r"scared|worried|nervous|overwhelmed|stressed|don'?t\s+(feel\s+like|want\s+to))\b",
    re.IGNORECASE,
)

_POSITIVE_PATTERNS = re.compile(
    r"\b(good|great|happy|excited|motivated|confident|ready|better|fine|okay|awesome)\b",
    re.IGNORECASE,
)


def detect_crisis(text: str) -> bool:
    return bool(_CRISIS_PATTERNS.search(text))


def infer_mood_score(text: str, default: int = 5) -> int:
    if detect_crisis(text):
        return 1
    if _DISTRESS_PATTERNS.search(text):
        return 3
    if _POSITIVE_PATTERNS.search(text):
        return 7
    return default


_CRISIS_RESPONSE: dict[str, Any] = {
    "response_en": (
        "I'm really glad you told me this. What you're feeling right now is serious, "
        "and you deserve real support — not just from an AI. Please reach out to iCall "
        "right now: 📞 9152987821 (free, confidential, Mon–Sat 8am–10pm). "
        "If you're in immediate danger, please call 112. "
        "You matter, and this moment is not the end of your story."
    ),
    "response_hi": (
        "मुझे खुशी है कि आपने मुझे बताया। आप जो महसूस कर रहे हैं वो बहुत गंभीर है। "
        "कृपया अभी iCall को call करें: 📞 9152987821 (निःशुल्क, गोपनीय)। "
        "आप अकेले नहीं हैं — मदद उपलब्ध है।"
    ),
    "detected_mood_score": 1,
    "mood_tags": ["crisis", "needs_support"],
    "coping_suggestion": (
        "Please call iCall now: 9152987821. They are trained counsellors who understand "
        "the pressure of exam prep. This call could change everything."
    ),
    "escalation_needed": True,
    "escalation_reason": "Crisis language detected.",
    "follow_up_question": "Can you tell me one person near you right now you could talk to?",
}


# ---------------------------------------------------------------------------
# System prompt builder — embeds live student context
# ---------------------------------------------------------------------------

def _days_until(exam_date_str: str | None) -> str:
    if not exam_date_str:
        return "unknown"
    try:
        d = date.fromisoformat(exam_date_str)
        delta = (d - date.today()).days
        if delta < 0:
            return "exam passed"
        return f"{delta} days away"
    except ValueError:
        return "unknown"


def _mood_summary(mood_history: list[dict]) -> str:
    if not mood_history:
        return "no mood data yet"
    recent = mood_history[-5:]
    scores = [e.get("score", 5) for e in recent]
    avg = sum(scores) / len(scores)
    trend = "improving" if len(scores) > 1 and scores[-1] > scores[0] else \
            "declining" if len(scores) > 1 and scores[-1] < scores[0] else "stable"
    latest_tags = recent[-1].get("tags", [])
    tag_str = f", recent tags: {', '.join(latest_tags)}" if latest_tags else ""
    return f"avg {avg:.1f}/10 over last {len(scores)} entries, trend: {trend}{tag_str}"


def _build_system(profile: dict[str, Any]) -> str:
    name = profile.get("display_name", "Student")
    exam = profile.get("target_exam", "JEE").replace("_", " ")
    exam_date = profile.get("exam_date")
    daily_hours = profile.get("daily_hours", 3)
    streak = profile.get("streak_days", 0)
    mood_history = profile.get("mood_history", [])
    stress = profile.get("stress_level", 5)
    consecutive_misses = profile.get("consecutive_misses", 0)

    return f"""You are MindMitra, a warm and empathetic mental health companion specifically for Indian competitive exam students.

STUDENT PROFILE:
- Name: {name}
- Preparing for: {exam}
- Exam date: {exam_date or 'not set'} ({_days_until(exam_date)})
- Daily study target: {daily_hours}h/day
- Current streak: {streak} days
- Mood trend: {_mood_summary(mood_history)}
- Stress level: {stress}/10
- Consecutive missed sessions: {consecutive_misses}

YOUR ROLE:
- Be a caring, non-judgmental companion who understands the unique pressure of JEE/NEET prep
- Respond directly and naturally to what the student says — do NOT give generic advice
- Use {name}'s name occasionally to make it personal
- Reference their actual situation (exam name, days left, streak) when relevant
- If they seem distressed, acknowledge it before offering any advice
- Keep responses concise (2-4 sentences) unless they need more support
- Mix Hindi and English naturally if appropriate (Hinglish is fine)
- Never be preachy or lecture them
- If they're just chatting, chat back — you don't have to make everything about mental health

IMPORTANT:
- You are NOT a doctor or therapist — if someone needs professional help, direct them to iCall: 9152987821
- Never dismiss or minimize their feelings
- Crisis situations (self-harm, suicide) have already been handled before this message reaches you
""".strip()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_therapist_chat(
    *,
    keys: APIKeys,
    user_message: str,
    conversation_history: list[dict[str, str]],
    student_profile: dict[str, Any],
) -> dict[str, Any]:
    """
    Direct conversational MindMitra. Crisis detection runs on user_message only.
    conversation_history: list of {"role": "user"|"assistant", "content": str}
    student_profile: dict with display_name, target_exam, exam_date, daily_hours,
                     streak_days, mood_history, stress_level, consecutive_misses
    """
    if detect_crisis(user_message):
        log.warning("Crisis language detected.")
        return _CRISIS_RESPONSE

    mood_score = infer_mood_score(user_message)
    system = _build_system(student_profile)
    s = get_settings()

    response_text: str | None = None

    # Try Groq first (fast, separate quota from Gemini)
    if keys.groq:
        try:
            groq_messages = [{"role": "system", "content": system}]
            for turn in conversation_history:
                groq_messages.append({"role": turn["role"], "content": turn["content"]})
            groq_messages.append({"role": "user", "content": user_message})
            response_text = await groq_chat(
                keys=keys,
                messages=groq_messages,
                model=s.groq_strong_model,
                temperature=0.75,
            )
        except Exception as exc:
            log.warning("MindMitra Groq failed: %s", exc)

    # Fall back to Gemini
    if not response_text and keys.gemini:
        try:
            response_text = await gemini_chat(
                keys=keys,
                system=system,
                history=conversation_history,
                message=user_message,
                model=s.gemini_default_model,
                temperature=0.75,
            )
        except Exception as exc:
            log.warning("MindMitra Gemini failed: %s", exc)

    if not response_text:
        response_text = _fallback_text(user_message, mood_score, student_profile)

    tags = _infer_tags(user_message, mood_score)

    return {
        "response_en": response_text,
        "response_hi": response_text,
        "detected_mood_score": mood_score,
        "mood_tags": tags,
        "coping_suggestion": "",
        "escalation_needed": mood_score <= 2,
        "escalation_reason": "Very low mood detected." if mood_score <= 2 else "",
        "follow_up_question": "",
    }


# ---------------------------------------------------------------------------
# Legacy entry point — kept for /checkin which still uses feeling_text + score
# ---------------------------------------------------------------------------

async def run_therapist(
    *,
    keys: APIKeys,
    feeling_text: str,
    mood_score: int,
    tags: list[str],
    recent_mood_history: list[dict],
    study_context: str = "",
    crisis_text: str | None = None,
) -> dict[str, Any]:
    """Used by /checkin. Wraps run_therapist_chat with minimal profile."""
    check = crisis_text if crisis_text is not None else feeling_text
    if detect_crisis(check):
        log.warning("Crisis language detected in checkin.")
        return _CRISIS_RESPONSE

    if mood_score == 5:
        mood_score = infer_mood_score(check, default=5)

    profile = {"mood_history": recent_mood_history, "stress_level": mood_score}
    history: list[dict[str, str]] = []

    try:
        result = await run_therapist_chat(
            keys=keys,
            user_message=feeling_text,
            conversation_history=history,
            student_profile=profile,
        )
        result["detected_mood_score"] = mood_score
        result["mood_tags"] = result.get("mood_tags") or tags or ["neutral"]
        return result
    except Exception as exc:
        log.warning("Therapist checkin failed: %s", exc)
        return _legacy_fallback(mood_score, tags)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_tags(text: str, mood_score: int = 5) -> list[str]:
    tags: list[str] = []
    if detect_crisis(text):
        return ["crisis", "needs_support"]
    if _DISTRESS_PATTERNS.search(text):
        tags.append("distressed")
    if re.search(r"\b(anxious|panic|nervous|scared|worried)\b", text, re.I):
        tags.append("anxious")
    if re.search(r"\b(exhaust|tired|sleep|burnout|burned)\b", text, re.I):
        tags.append("exhausted")
    if re.search(r"\b(motivat|confident|ready|excited)\b", text, re.I):
        tags.append("motivated")
    if not tags:
        tags.append("neutral" if mood_score >= 5 else "low")
    return tags


def _fallback_text(text: str, mood_score: int, profile: dict) -> str:
    name = profile.get("display_name", "")
    name_part = f"{name}, " if name and name != "Student" else ""
    if mood_score <= 3:
        return (
            f"Hey {name_part}I hear you — that's a tough feeling and it's completely valid. "
            "JEE prep can be really draining. Take a breath, even a 10-minute break can help reset things. "
            "Want to talk about what's going on?"
        )
    return (
        f"Hey {name_part}thanks for checking in! "
        "How's the prep going — anything specific on your mind today?"
    )


def _legacy_fallback(mood_score: int, tags: list[str]) -> dict[str, Any]:
    low = mood_score <= 4
    en = (
        "I hear you — JEE prep can feel crushing sometimes. Take a short break, even 10 minutes outside helps."
        if low else
        "Good to hear from you! Consistent effort really does add up. What are you working on today?"
    )
    return {
        "response_en": en,
        "response_hi": en,
        "detected_mood_score": mood_score,
        "mood_tags": tags or (["overwhelmed"] if low else ["motivated"]),
        "coping_suggestion": "Try 5 minutes of deep breathing." if low else "Keep a short study journal.",
        "escalation_needed": mood_score <= 2,
        "escalation_reason": "Very low mood." if mood_score <= 2 else "",
        "follow_up_question": "What would make today a little better?",
    }
