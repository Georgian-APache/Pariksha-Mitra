# ParikshaMitra — Phase M: Mental Health + Schedule Accountability + WhatsApp Alerts

> Three interconnected features that transform ParikshaMitra from a study tool into a holistic JEE companion. This file is a self-contained spec for Claude Code to implement each feature with minimal tokens.

## Architecture Overview

```
                    ┌──────────────────────┐
                    │   Onboarding (edit)   │  ← collect parent_phone, student mood baseline
                    └──────────┬───────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
  ┌───────────────┐   ┌──────────────────┐   ┌──────────────┐
  │ Mental Health  │   │ Schedule Tracker │   │  WhatsApp    │
  │   Companion    │   │ + Reality Check  │   │  Notifier    │
  │  (new agent)   │   │   Quiz Gate      │   │  (Twilio)    │
  └───────┬───────┘   └────────┬─────────┘   └──────┬───────┘
          │                    │                     │
          └────────────────────┼─────────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │  Dashboard (updated) │  ← new cards, mood tracker, accountability
                    └──────────────────────┘
```

---

## FEATURE 1: Mental Health AI Companion ("MindMitra")

### 1A. New DB columns on `User` model

**File:** `backend/app/db/models.py` — add to `User` class:

```python
# Mental health tracking
parent_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
parent_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
mood_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
# Each entry: {"timestamp": iso, "score": 1-10, "tags": ["anxious","overwhelmed",...], "note": ""}
stress_level: Mapped[float] = mapped_column(Float, default=5.0)  # running avg 1-10
mental_health_flags: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
# {"consecutive_low_mood": 0, "last_checkin": iso, "escalation_sent": false}
```

### 1B. New agent: `backend/app/agents/therapist.py`

This is a **new LangGraph node** — a JEE-aware mental health companion.

```python
"""Therapist agent — JEE-specific mental health companion.

NOT a replacement for professional help. Detects stress patterns,
provides coping strategies, and escalates to parents via WhatsApp
when consecutive distress signals are detected.
"""

THERAPIST_SYSTEM = """You are MindMitra, a compassionate mental health companion 
embedded in ParikshaMitra, tailored for Indian students preparing for JEE/NEET.

Your capabilities:
1. GAUGE STRESS: Analyze mood check-in scores (1-10), free-text feelings,
   study pattern disruptions (missed sessions, declining scores), and
   conversation tone to assess mental state.
2. EMPATHIZE & VALIDATE: Acknowledge the immense pressure of JEE prep.
   Reference relatable scenarios (comparison with peers, parental expectations,
   fear of drop year, coaching pressure, sleep deprivation).
3. PROVIDE COPING STRATEGIES specific to exam students:
   - 5-4-3-2-1 grounding for pre-exam anxiety
   - Pomodoro-break breathing exercises
   - Journaling prompts for overwhelm
   - Perspective reframing ("one bad mock ≠ failure")
   - Study-life balance micro-tips
4. DETECT RED FLAGS: If student expresses hopelessness, self-harm ideation,
   or extreme distress (mood ≤ 2 for 3+ days), output escalation_needed=true.
5. BILINGUAL: Respond in both English and Hindi. Use warm, peer-like tone.

NEVER:
- Diagnose mental health conditions
- Prescribe medication or replace therapy
- Dismiss feelings with "just study harder"
- Share student's private feelings with parents (only notify about missed sessions)

Output JSON matching TherapistOutput schema.
"""

THERAPIST_OUTPUT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "response_en": {"type": "STRING"},
        "response_hi": {"type": "STRING"},
        "detected_mood_score": {"type": "INTEGER"},  # 1-10 your assessment
        "mood_tags": {"type": "ARRAY", "items": {"type": "STRING"}},
        # e.g. ["anxious", "overwhelmed", "motivated", "burned_out"]
        "coping_suggestion": {"type": "STRING"},
        "escalation_needed": {"type": "BOOLEAN"},
        "escalation_reason": {"type": "STRING"},
        "follow_up_question": {"type": "STRING"},
    },
    "required": ["response_en", "response_hi", "detected_mood_score", "mood_tags",
                  "coping_suggestion", "escalation_needed"],
}
```

**Implementation pattern:** Follow existing `companion.py` structure exactly:
- `async def therapist_node(state, keys) -> StudentState`
- Use `gemini_json()` with the schema above
- Heuristic fallback if LLM fails
- Add trace step with `agent="therapist"`

### 1C. New route: `backend/app/routes/mental_health.py`

```python
router = APIRouter(prefix="/mental-health", tags=["mental_health"])

# POST /mental-health/checkin
# Body: {user_id, mood_score: 1-10, feeling_text: str, tags?: str[]}
# → Runs therapist agent, persists mood_history entry, returns AI response
# → If mood_score ≤ 3 for 3+ consecutive checkins, sets escalation flag

# POST /mental-health/chat
# Body: {user_id, message: str, conversation_id?: str}
# → Multi-turn therapeutic conversation using Gemini with therapist system prompt
# → Stores conversation in a new `MentalHealthChat` table
# → Returns {response_en, response_hi, mood_tags, coping_suggestion}

# GET /mental-health/{user_id}/history
# → Returns mood_history array + stress_level trend for the mood chart

# GET /mental-health/{user_id}/insights
# → Gemini analyzes mood_history + study_performance correlation
# → Returns {insight_en, insight_hi, recommendations: str[]}
```

### 1D. New DB model for chat persistence

**File:** `backend/app/db/models.py` — add:

```python
class MentalHealthChat(Base):
    __tablename__ = "mental_health_chats"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    mood_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mood_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
```

### 1E. Frontend: New page `frontend/src/app/mindmitra/page.tsx`

**Design spec:**
- Full-screen chat interface with soft, calming gradient background (lavender to soft blue)
- Top: mood check-in slider (emoji scale) that pulses gently on first visit of the day
- Chat bubbles: user = right-aligned, MindMitra = left with a brain avatar
- Each AI response shows both EN and HI in a tabbed/toggle view
- Bottom: coping strategy cards that slide up as suggestions
- Mood history chart (last 14 days) in a collapsible drawer
- Framer Motion transitions on all elements
- Colors: Distinct from main app — use calming palette (oklch soft purples/teals)

**Components to create:**
- `MoodCheckin.tsx` — emoji slider + optional text input
- `TherapistChat.tsx` — chat bubble interface with streaming feel
- `CopingCard.tsx` — animated suggestion cards
- `MoodChart.tsx` — Recharts line chart of mood over time

### 1F. Register in main.py

Add `mental_health` route import and `app.include_router()` following existing pattern.

### 1G. Dashboard integration

Add a "MindMitra" card on dashboard with:
- Current mood indicator (last check-in emoji)
- "How are you feeling?" quick-access button
- Alert banner if no check-in in 48h

---

## FEATURE 2: Schedule Accountability + Reality Check Quiz

### 2A. New DB model: `StudySession`

**File:** `backend/app/db/models.py`

```python
class StudySession(Base):
    __tablename__ = "study_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    plan_date: Mapped[str] = mapped_column(String(20))  # YYYY-MM-DD
    concept_id: Mapped[str] = mapped_column(String(80))
    subject: Mapped[str] = mapped_column(String(80))
    activity: Mapped[str] = mapped_column(String(20))
    scheduled_minutes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # "pending" | "completed" | "skipped" | "quiz_passed" | "quiz_failed"
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quiz_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
```

Add to `User` model:
```python
consecutive_misses: Mapped[int] = mapped_column(Integer, default=0)
last_parent_alert_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
```

### 2B. New route: `backend/app/routes/schedule.py`

```python
router = APIRouter(prefix="/schedule", tags=["schedule"])

# GET /schedule/{user_id}/today
# → Returns today's plan blocks with their completion status
# → Auto-creates StudySession rows from plan if not yet created for today

# POST /schedule/mark
# Body: {user_id, session_id, studied: bool}
# If studied=true:
#   → Generate a 5-question "reality check" quiz on that concept
#   → Return {quiz_questions: Question[], session_id}
#   → Student must score >= 60% to mark as "quiz_passed"
#   → If < 60%: mark as "quiz_failed", still counts as attempted
# If studied=false:
#   → Mark as "skipped", increment consecutive_misses
#   → If consecutive_misses >= 3: trigger WhatsApp alert to parent
#   → Reset consecutive_misses on any "completed"/"quiz_passed"

# POST /schedule/submit-reality-check
# Body: {user_id, session_id, answers: [{question_id, chosen_index}]}
# → Grade the reality check quiz
# → If score >= 0.6: status="quiz_passed", reset consecutive_misses
# → If score < 0.6: status="quiz_failed", show feedback
# → Return {score, graded_answers, passed: bool, feedback_en, feedback_hi}

# GET /schedule/{user_id}/weekly-summary
# → Returns {completed, skipped, quiz_passed, quiz_failed,
#            consecutive_misses, parent_alerted: bool}
```

### 2C. Auto-populate sessions from plan

When `GET /schedule/{user_id}/today` is called:
1. Look up `user.plan.days` for today's date
2. For each block, check if a `StudySession` already exists (by user_id + plan_date + concept_id)
3. If not, create one with status="pending"
4. Return the list sorted by block order

### 2D. Reality Check Quiz Generation

Reuse existing `generate_questions()` from `app.agents.quizmaster`:
```python
questions = await generate_questions(
    keys=keys,
    requests=[{"concept_id": session.concept_id, "subject": session.subject, "difficulty": 3}],
    exam=user.target_exam,
    prefer_seed=True,
    count=5,
)
```

### 2E. Frontend: Update `PlanStrip.tsx` to be interactive

Transform the existing read-only PlanStrip into an interactive accountability tracker:

**Each block gets:**
- Status indicator: Pending | Done | Skipped | Quiz
- "I studied this" button → opens reality check quiz modal
- "I skipped this" button → marks skip, shows warning if approaching 3 misses
- After quiz: show score with pass/fail badge and explanations

**New component:** `RealityCheckQuiz.tsx`
- Modal overlay with 5 MCQ questions
- Timer (optional, 10 min)
- Score reveal with confetti (pass) or encouragement (fail)
- Shows which answers were wrong with explanations

**New component:** `ScheduleTracker.tsx`
- Today's schedule as a vertical timeline
- Progress bar showing completed/total
- Warning badge: "2/3 misses — one more triggers parent alert"

### 2F. Dashboard integration

Replace/augment the PlanStrip card with the new interactive ScheduleTracker.

---

## FEATURE 3: WhatsApp Parent Notification

### 3A. Configuration

**File:** `backend/app/config.py` — add to `Settings`:

```python
# WhatsApp (Twilio) — set in .env
twilio_account_sid: str | None = None
twilio_auth_token: str | None = None
twilio_whatsapp_from: str = "whatsapp:+14155238886"  # Twilio sandbox default
parent_alert_miss_threshold: int = 3  # consecutive misses before alert
parent_alert_cooldown_hours: int = 24  # min hours between alerts
```

### 3B. New service: `backend/app/services/whatsapp.py`

```python
"""WhatsApp notification service via Twilio.

Uses Twilio's WhatsApp sandbox for dev (free), upgradeable to Twilio
WhatsApp Business API or Meta Cloud API for production.

Alternatives supported:
- TWILIO: twilio_account_sid + twilio_auth_token in .env
- META_CLOUD: whatsapp_phone_id + whatsapp_access_token in .env
- MOCK: if neither configured, logs messages to console (dev mode)
"""
import logging
from app.config import get_settings

log = logging.getLogger("parikshamitra.whatsapp")

async def send_parent_alert(
    parent_phone: str,
    parent_name: str,
    student_name: str,
    consecutive_misses: int,
    missed_topics: list[str],
) -> dict:
    """Send a WhatsApp message to parent about missed study sessions."""
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
    else:
        log.warning("WhatsApp not configured. Would send to %s: %s", parent_phone, message)
        return {"status": "mock", "message": message}


async def _send_twilio(phone: str, message: str, s) -> dict:
    """Send via Twilio WhatsApp API."""
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
        return {"status": "sent" if resp.is_success else "failed", 
                "sid": resp.json().get("sid", ""), "code": resp.status_code}
```

### 3C. Trigger logic in schedule route

In `POST /schedule/mark` when `studied=false`:

```python
user.consecutive_misses = (user.consecutive_misses or 0) + 1

if user.consecutive_misses >= settings.parent_alert_miss_threshold:
    if user.parent_phone and _cooldown_ok(user):
        missed_topics = await _get_recent_missed_topics(session, user.id, limit=5)
        result = await send_parent_alert(
            parent_phone=user.parent_phone,
            parent_name=user.parent_name or "Parent",
            student_name=user.display_name,
            consecutive_misses=user.consecutive_misses,
            missed_topics=missed_topics,
        )
        user.last_parent_alert_date = date.today().isoformat()
```

### 3D. Onboarding: Collect parent info

**File:** `backend/app/routes/onboarding.py` — update `StartRequest`:

```python
class StartRequest(BaseModel):
    # ... existing fields ...
    parent_phone: str | None = None  # "+91XXXXXXXXXX"
    parent_name: str | None = None
```

**File:** `backend/app/db/repositories.py` — update `upsert_user` to accept and save `parent_phone`, `parent_name`.

**File:** `frontend/src/app/onboarding/page.tsx` — add after daily hours slider:
- Parent name input field
- WhatsApp number input field  
- Privacy notice: "Your private conversations with MindMitra are never shared."

### 3E. Environment variables

**File:** `backend/.env.example` — add:
```env
# WhatsApp alerts via Twilio (optional — alerts logged to console if unset)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
PARENT_ALERT_MISS_THRESHOLD=3
PARENT_ALERT_COOLDOWN_HOURS=24
```

No new pip dependency needed — `httpx` is already in requirements.txt.

---

## IMPLEMENTATION ORDER (10 steps, for minimal token usage)

### Step 1: DB Schema Changes (do all at once)
1. Edit `backend/app/db/models.py`: add all new columns to `User`, add `MentalHealthChat` model, add `StudySession` model
2. Delete `backend/parikshamitra.db` to recreate schema

### Step 2: Config + Services
1. Edit `backend/app/config.py` — add Twilio settings
2. Create `backend/app/services/__init__.py` (empty)
3. Create `backend/app/services/whatsapp.py`

### Step 3: Agent + Prompts
1. Edit `backend/app/agents/prompts.py` — add `THERAPIST_SYSTEM` prompt and `therapist_user_prompt()` helper
2. Create `backend/app/agents/therapist.py`
3. Edit `backend/app/agents/state.py` — add `THERAPIST_OUTPUT_SCHEMA`, add `"therapist"` to AgentStep.agent Literal, add mood fields to `StudentState`

### Step 4: Repository Helpers
Edit `backend/app/db/repositories.py` — add helpers for mood, study sessions, chat messages, and update `upsert_user`

### Step 5: Backend Routes
1. Create `backend/app/routes/mental_health.py`
2. Create `backend/app/routes/schedule.py`
3. Edit `backend/app/routes/onboarding.py` — add parent fields
4. Edit `backend/app/main.py` — register new routers

### Step 6: Frontend Types
Edit `frontend/src/lib/types.ts` — add types for mood, study sessions, therapist responses

### Step 7: Frontend — MindMitra Page
1. Create `frontend/src/app/mindmitra/page.tsx`
2. Create `frontend/src/components/MoodCheckin.tsx`
3. Create `frontend/src/components/TherapistChat.tsx`
4. Create `frontend/src/components/CopingCard.tsx`
5. Create `frontend/src/components/MoodChart.tsx`

### Step 8: Frontend — Schedule Tracker
1. Create `frontend/src/components/ScheduleTracker.tsx`
2. Create `frontend/src/components/RealityCheckQuiz.tsx`

### Step 9: Frontend — Dashboard + Onboarding Updates
1. Edit `frontend/src/app/dashboard/page.tsx` — add MindMitra card + ScheduleTracker
2. Edit `frontend/src/app/onboarding/page.tsx` — add parent contact fields

### Step 10: Navigation
Edit `frontend/src/components/Header.tsx` — add MindMitra nav link

---

## KEY DESIGN DECISIONS

| Decision | Choice | Rationale |
|---|---|---|
| WhatsApp API | Twilio sandbox → prod | Free sandbox for dev, easy upgrade, no Meta Business verification needed initially |
| Therapist approach | Standalone route with shared `gemini_json` | Mental health chat is multi-turn, doesn't fit the single-pass agent graph |
| Reality check count | 5 questions | Quick but meaningful verification |
| Pass threshold | 60% (3/5) | Generous but prevents gaming |
| Parent alert threshold | 3 consecutive misses | Balances accountability with student autonomy |
| Alert cooldown | 24 hours | Prevents spam |
| Mood data privacy | Never sent to parents | Only missed sessions trigger alerts |
| Chat storage | Separate `MentalHealthChat` table | Multi-turn conversations grow large; relational storage is cleaner |

## FRONTEND DESIGN NOTES

**MindMitra page palette** (calming, distinct from main study UI):
- Background: oklch(0.97 0.01 280) — near-white lavender
- Primary: oklch(0.65 0.15 290) — soft purple
- Accent: oklch(0.72 0.12 200) — soft teal
- Danger: oklch(0.65 0.18 25) — warm coral for escalation

**Animations:**
- Mood slider: emoji scales up on hover with spring physics
- Chat bubbles: slide-in from left (AI) / right (user) with 200ms stagger
- Coping cards: accordion expand with content fade-in
- Reality check quiz: question cards flip-in, score reveals with counter animation

**Mobile-first:** All new components must work at 375px width.
