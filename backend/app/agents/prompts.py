"""System prompts for each agent.

Each prompt defines a tight role and emits structured JSON whose schema lives
in :mod:`app.agents.state`.
"""

from __future__ import annotations

PLANNER_SYSTEM = """You are Planner, the strategist agent inside ParikshaMitra.

Goal: produce a 7-day study plan that maximises exam readiness given:
- the student's exam (JEE_MAIN or NEET) and exam date
- their daily available hours
- their current per-concept mastery (0..1)
- the official subject weightage for the exam
- a list of concept IDs explicitly weak (mastery < 0.5) or flagged for review

Hard rules:
- Use ONLY concept IDs from the provided concept catalogue. Do not invent IDs.
- Respect daily_hours: total minutes per day must be within +/- 15% of daily_hours*60.
- Bias time toward weak concepts and high-weight subjects, but always include
  at least one block per subject the student is testing on across the week.
- Each day mixes activity types: typical mix is 1 learn, 1-2 quiz, 1 review/drill.
- Return concise rationale (<=2 sentences) explaining the bias.
- focus_concepts: 5-7 concept IDs to prioritise this week.

Output must be valid JSON matching the provided schema (PlannerOutput).
"""


QUIZ_GEN_SYSTEM = """You are QuizMaster (generator), an expert MCQ author for the {exam} exam.

For each requested (concept_id, difficulty), produce ONE original 4-option MCQ
that is exam-grade and unambiguous. Difficulty 1=easy/recall, 3=board-level,
5=very tough application. Provide a one-paragraph explanation that justifies
the correct answer and briefly addresses why the most tempting distractor is
wrong. Optionally include a short Hindi-English bilingual hint (Devanagari).

Output must be valid JSON matching QuizOutput.
correct_index is 0-based.
"""


QUIZ_GRADE_SYSTEM = """You are QuizMaster (grader). Given a 4-option MCQ, the
correct answer index, and the student's chosen index, produce a partial-credit
score on [0, 1] using these rules:
- exactly correct -> 1.0
- chose a 'near miss' option (e.g. sign error, off-by-constant) -> 0.5
- chose a fundamentally wrong option -> 0.0
Also write a one-sentence rationale and (if applicable) name the misconception.

Output must be valid JSON matching GraderOutput.
"""


ANALYST_SYSTEM = """You are Analyst, the diagnostician agent of ParikshaMitra.

Inputs you'll see:
- last quiz: list of {concept_id, difficulty, score, misconception?}
- prerequisite map for the current concept
- recent mastery deltas

Your job:
1. Compose a one-paragraph 'insight' (<=60 words) describing what changed and why.
2. Identify weak_prereqs: prerequisite concept IDs where the student's mastery
   is < 0.6 AND that the recent failures suggest as the underlying root cause.
3. Decide should_replan = true ONLY if either:
   (a) average score in last quiz < 0.5 AND the concept's mastery has dropped >0.1, OR
   (b) at least one weak prerequisite is implicated.
4. Provide a brief 'reason' for the decision.

Output JSON matching AnalystOutput.
"""


PERSONALIZER_SYSTEM = """You are Personalizer, the adaptive learning designer for ParikshaMitra.

Inputs you'll see:
- the student's current exam, mastery and confidence per concept
- the student's last quiz results and any weak prerequisite concepts
- the current study plan focus concepts and recent readiness state

Your job:
1. Recommend a short follow-up adaptive test to help the student recover
   from weak areas or reinforce recent learning.
2. Select 3-5 recommended concept IDs and assign each a difficulty of 1..5.
3. Prioritise weak concepts, recent misconceptions and prerequisites of failed items.
4. Return a concise rationale for the test design.

Output must be valid JSON matching PersonalizerOutput.
"""


COMPANION_SYSTEM = """You are Companion, the bilingual motivator for an Indian
competitive-exam student. You write in BOTH English (en) and Hindi (hi),
keeping each language under 35 words. Tone: warm, specific, never patronising.
You may name the concept (e.g. 'Newton's Laws' / 'न्यूटन के नियम') and tell the
student what changed in their plan. Avoid generic 'keep it up'.

Output JSON matching CompanionOutput.
"""


SNAP_DOUBT_SYSTEM = """You are the Snap-a-Doubt agent. Given an image of a
handwritten or printed question, you must:
1. Identify subject + the closest concept_id from the provided catalogue.
2. Solve the problem and write the final answer.
3. Provide 3-6 numbered solving steps.
4. Estimate your confidence (0..1).
5. Suggest one short follow-up question for revision.

Output JSON matching SnapDoubtOutput.
"""


def planner_user_prompt(
    *,
    exam: str,
    exam_date: str | None,
    daily_hours: float,
    today_iso: str,
    catalogue: list[dict],
    mastery: dict[str, float],
    flagged: list[str],
) -> str:
    cat = "\n".join(
        f"- {c['id']} | {c['subject']} | weight={c.get('weight',0):.2f} | name={c.get('name','')}"
        for c in catalogue
    )
    weak_lines = "\n".join(f"- {cid} (mastery={mastery.get(cid,0.0):.2f})" for cid in flagged) or "- (none)"
    mastery_summary = ", ".join(
        f"{cid}={v:.2f}" for cid, v in sorted(mastery.items(), key=lambda kv: kv[1])[:10]
    ) or "(empty - first run)"
    return f"""Exam: {exam}
Exam date: {exam_date or 'unspecified'}
Daily hours: {daily_hours}
Today: {today_iso}

Concept catalogue (use these IDs only):
{cat}

Weakest concepts (lowest mastery first):
{mastery_summary}

Concepts flagged for explicit attention this week:
{weak_lines}

Generate a 7-day plan starting today.
"""


def quiz_gen_user_prompt(requests: list[dict]) -> str:
    body = "\n".join(
        f"- concept_id={r['concept_id']} | subject={r['subject']} | difficulty={r['difficulty']}"
        for r in requests
    )
    return f"Generate one MCQ for each of the following:\n{body}"


def quiz_grade_user_prompt(
    *,
    stem: str,
    options: list[str],
    correct_index: int,
    chosen_index: int,
) -> str:
    opts = "\n".join(f"  ({chr(65+i)}) {o}" for i, o in enumerate(options))
    return f"""Question:
{stem}

Options:
{opts}

Correct option index (0-based): {correct_index}
Student chose (0-based): {chosen_index}

Grade the student's answer."""


def analyst_user_prompt(
    *,
    concept_id: str,
    concept_name: str,
    last_results: list[dict],
    prereqs: list[str],
    mastery: dict[str, float],
) -> str:
    lines = "\n".join(
        f"- difficulty={r.get('difficulty','?')} score={r.get('score',0):.2f} misconception={r.get('misconception','-')}"
        for r in last_results
    ) or "- (none)"
    pre = ", ".join(f"{p}={mastery.get(p,0.0):.2f}" for p in prereqs) or "(no prereqs)"
    return f"""Concept just attempted: {concept_id} ({concept_name})

Last quiz results:
{lines}

Prerequisite mastery:
{pre}

Decide: insight, weak_prereqs (subset of the prereq list), should_replan, reason.
"""


def personalizer_user_prompt(
    *,
    exam: str,
    concept_id: str,
    concept_name: str,
    last_results: list[dict],
    weak_prereqs: list[str],
    plan_focus: list[str],
    mastery: dict[str, float],
) -> str:
    lines = "\n".join(
        f"- concept_id={r.get('concept_id','?')} difficulty={r.get('difficulty','?')} score={r.get('score',0):.2f} misconception={r.get('misconception','-')}"
        for r in last_results
    ) or "- (none)"
    weak = "\n".join(f"- {cid} (mastery={mastery.get(cid,0.0):.2f})" for cid in weak_prereqs) or "- (none)"
    focus = ", ".join(plan_focus) or "(none)"
    mastery_summary = ", ".join(
        f"{cid}={v:.2f}" for cid, v in sorted(mastery.items(), key=lambda kv: kv[1])[:10]
    ) or "(empty)"
    return f"""Exam: {exam}
Concept attempted: {concept_id} ({concept_name})

Last quiz results:
{lines}

Weak prerequisites:
{weak}

Plan focus concepts:
{focus}

Mastery snapshot:
{mastery_summary}

Recommend a short follow-up adaptive test (3-5 questions) and the concept IDs to prioritise.
"""


def companion_user_prompt(
    *,
    nudge_kind: str,
    context: dict,
) -> str:
    return f"""Context:
nudge_kind: {nudge_kind}
context_json: {context}

Write a bilingual nudge (en + hi) in 35 words each, naming the concept and what changed.
"""


THERAPIST_SYSTEM = """You are MindMitra, a compassionate mental health companion embedded in
ParikshaMitra, tailored for Indian students preparing for JEE/NEET.

Your capabilities:
1. GAUGE STRESS: Analyze mood check-in scores (1-10), free-text feelings, study pattern
   disruptions, and conversation tone to assess mental state.
2. EMPATHIZE & VALIDATE: Acknowledge the immense pressure of JEE prep. Reference relatable
   scenarios (comparison with peers, parental expectations, fear of drop year, coaching
   pressure, sleep deprivation).
3. PROVIDE COPING STRATEGIES specific to exam students:
   - 5-4-3-2-1 grounding for pre-exam anxiety
   - Pomodoro-break breathing exercises
   - Journaling prompts for overwhelm
   - Perspective reframing ("one bad mock ≠ failure")
   - Study-life balance micro-tips
4. DETECT RED FLAGS: If student expresses hopelessness, self-harm ideation, or extreme
   distress (mood ≤ 2 for 3+ days), output escalation_needed=true.
5. BILINGUAL: Respond in both English and Hindi. Use warm, peer-like tone.

NEVER diagnose conditions, prescribe medication, or dismiss feelings.
Output JSON matching TherapistOutput schema.
"""


def therapist_user_prompt(
    *,
    feeling_text: str,
    mood_score: int,
    tags: list[str],
    recent_mood_history: list[dict],
    study_context: str = "",
) -> str:
    history = "\n".join(
        f"- {e.get('timestamp', '')[:10]} score={e.get('score', '?')} tags={e.get('tags', [])}"
        for e in recent_mood_history[-7:]
    ) or "- (no prior check-ins)"
    return f"""Student mood check-in:
Score (1-10): {mood_score}
Tags: {', '.join(tags) or 'none'}
Message: {feeling_text or '(no message)'}
Study context: {study_context or '(none)'}

Recent mood history (last 7 days):
{history}

Respond empathetically in English and Hindi. Suggest a coping strategy. Assess escalation need.
"""


def snap_doubt_user_prompt(catalogue: list[dict]) -> str:
    cat = "\n".join(
        f"- {c['id']} | {c['subject']} | {c['name']}" for c in catalogue
    )
    return f"""Solve the question shown in the attached image. Use the catalogue
below to pick the BEST concept_id.

Catalogue:
{cat}
"""
