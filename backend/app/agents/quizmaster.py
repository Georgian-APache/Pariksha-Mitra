"""QuizMaster agent - generates and grades MCQs."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

import re

from app.agents.llm import gemini_json, groq_chat
from app.agents.prompts import (
    QUIZ_GEN_SYSTEM,
    QUIZ_GRADE_SYSTEM,
    quiz_gen_user_prompt,
    quiz_grade_user_prompt,
)
from app.agents.state import (
    GRADER_OUTPUT_SCHEMA,
    QUESTION_OUTPUT_SCHEMA,
    GradedAnswer,
    Question,
)
from app.config import APIKeys, DATA_DIR, get_settings
from app.intelligence.concept_dag import ConceptDAG, get_dag

log = logging.getLogger("parikshamitra.quizmaster")


def _seed_bank() -> list[dict[str, Any]]:
    path = Path(DATA_DIR) / "seed_questions.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _row_to_question(row: dict[str, Any], *, concept_id: str, subject: str) -> Question:
    """Build a Question from a seed bank row, attributing mastery to ``concept_id``."""

    return Question(
        id=str(uuid.uuid4()),
        concept_id=concept_id,
        subject=subject or row.get("subject", ""),
        difficulty=int(row.get("difficulty", 3)),
        stem=row["stem"],
        options=list(row["options"]),
        correct_index=int(row["correct_index"]),
        explanation=row.get("explanation", ""),
        bilingual_hint=row.get("bilingual_hint"),
        source="seed",
    )


def _best_seed_row(rows: list[dict[str, Any]], difficulty: int) -> dict[str, Any] | None:
    if not rows:
        return None
    return sorted(rows, key=lambda q: abs(int(q.get("difficulty", 3)) - difficulty))[0]


def _parse_json_object(text: str) -> dict[str, Any]:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```$", "", t)
    return json.loads(t)


async def _try_groq_quiz_batch(
    *,
    keys: APIKeys,
    pending: list[dict],
    exam: str,
    dag: ConceptDAG,
) -> list[Question] | None:
    """Optional Groq fallback when Gemini fails (returns None on any error)."""

    if not keys.groq:
        return None
    try:
        s = get_settings()
        sys = (
            QUIZ_GEN_SYSTEM.format(exam=exam)
            + " Output ONLY a single JSON object with key 'questions' (array of objects). "
            "Each object: concept_id, subject, difficulty, stem, options (4 strings), "
            "correct_index (0-3), explanation, optional bilingual_hint."
        )
        user = quiz_gen_user_prompt(pending)
        raw = await groq_chat(
            keys=keys,
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
            temperature=0.4,
            model=s.groq_fast_model,
        )
        payload = _parse_json_object(raw)
        out: list[Question] = []
        for q in payload.get("questions", []):
            cid = q["concept_id"]
            out.append(
                Question(
                    id=str(uuid.uuid4()),
                    concept_id=cid,
                    subject=q.get("subject") or dag.info(cid).get("subject", ""),
                    difficulty=int(q.get("difficulty", 3)),
                    stem=q["stem"],
                    options=q["options"],
                    correct_index=int(q["correct_index"]),
                    explanation=q.get("explanation", ""),
                    bilingual_hint=q.get("bilingual_hint"),
                    source="generated",
                )
            )
        if len(out) >= len(pending):
            return out[: len(pending)]
    except Exception as exc:  # noqa: BLE001
        log.warning("Groq quiz batch failed: %s", exc)
    return None


async def generate_questions(
    *,
    keys: APIKeys,
    requests: list[dict],
    exam: str = "JEE_MAIN",
    prefer_seed: bool = True,
) -> list[Question]:
    """Each ``request`` is ``{concept_id, subject, difficulty}``.

    Fills from the curated seed bank first (exact concept, then same subject, then any),
    so diagnostics stay real MCQs even when Gemini is rate-limited. LLM batch is a
    fallback; Groq JSON is tried next; generic stubs are last resort.
    """

    bank = _seed_bank()
    dag = get_dag(exam)
    used_stems: set[str] = set()
    out: list[Question] = []
    pending: list[dict] = []

    for r in requests:
        cid = r["concept_id"]
        diff = int(r.get("difficulty", 3))
        subject = str(r.get("subject") or dag.info(cid).get("subject", ""))

        row: dict[str, Any] | None = None
        if prefer_seed and bank:
            exact = [q for q in bank if q.get("concept_id") == cid and q.get("stem", "") not in used_stems]
            row = _best_seed_row(exact, diff)
            if row is None:
                subj_pool = [
                    q for q in bank if q.get("subject") == subject and q.get("stem", "") not in used_stems
                ]
                row = _best_seed_row(subj_pool, diff)
            if row is None:
                global_pool = [q for q in bank if q.get("stem", "") not in used_stems]
                row = _best_seed_row(global_pool, diff)

        if row is not None:
            used_stems.add(str(row["stem"]))
            out.append(_row_to_question(row, concept_id=cid, subject=subject))
            continue

        pending.append({"concept_id": cid, "subject": subject, "difficulty": diff})

    if not pending:
        return out

    try:
        s = get_settings()
        payload = await gemini_json(
            keys=keys,
            prompt=quiz_gen_user_prompt(pending),
            schema=QUESTION_OUTPUT_SCHEMA,
            system=QUIZ_GEN_SYSTEM.format(exam=exam),
            model=s.gemini_default_model,
            temperature=0.7,
        )
        gen = payload.get("questions", [])
        if len(gen) < len(pending):
            raise ValueError(f"Gemini returned {len(gen)} questions, expected {len(pending)}")
        for q in gen:
            out.append(
                Question(
                    id=str(uuid.uuid4()),
                    concept_id=q["concept_id"],
                    subject=q.get("subject") or dag.info(q["concept_id"]).get("subject", ""),
                    difficulty=int(q.get("difficulty", 3)),
                    stem=q["stem"],
                    options=q["options"],
                    correct_index=int(q["correct_index"]),
                    explanation=q.get("explanation", ""),
                    bilingual_hint=q.get("bilingual_hint"),
                    source="generated",
                )
            )
        return out
    except Exception as exc:  # noqa: BLE001
        log.warning("Quiz generation Gemini failed, trying Groq then seed stubs. err=%s", exc)

    groq_qs = await _try_groq_quiz_batch(keys=keys, pending=pending, exam=exam, dag=dag)
    if groq_qs and len(groq_qs) >= len(pending):
        out.extend(groq_qs[: len(pending)])
        return out

    # Last resort: reuse seed rows (allow stem repeats) before generic stubs.
    for i, r in enumerate(pending):
        cid, subject, diff = r["concept_id"], r["subject"], int(r["difficulty"])
        row = None
        if bank:
            subj = [q for q in bank if q.get("subject") == subject]
            row = _best_seed_row(subj, diff) if subj else None
            if row is None:
                row = bank[i % len(bank)]
        if row is not None:
            out.append(_row_to_question(row, concept_id=cid, subject=subject))
        else:
            out.append(_stub_question(cid, subject, diff))
    return out


def _stub_question(concept_id: str, subject: str, difficulty: int) -> Question:
    return Question(
        id=str(uuid.uuid4()),
        concept_id=concept_id,
        subject=subject or "Mathematics",
        difficulty=difficulty,
        stem=f"[Stub] Sample question on {concept_id}. Choose the conceptually correct option.",
        options=["Definition A", "Application B", "Edge case C", "Common mistake D"],
        correct_index=1,
        explanation="Stub explanation - the LLM was unavailable; this is a placeholder.",
        bilingual_hint=None,
        source="generated",
    )


async def grade_answer(
    *,
    keys: APIKeys,
    question: Question,
    chosen_index: int,
) -> GradedAnswer:
    if chosen_index == question.correct_index:
        return GradedAnswer(
            question_id=question.id,
            chosen_index=chosen_index,
            correct=True,
            score=1.0,
            rationale=question.explanation or "Correct.",
        )
    # LLM partial-credit grader
    try:
        s = get_settings()
        payload = await gemini_json(
            keys=keys,
            prompt=quiz_grade_user_prompt(
                stem=question.stem,
                options=question.options,
                correct_index=question.correct_index,
                chosen_index=chosen_index,
            ),
            schema=GRADER_OUTPUT_SCHEMA,
            system=QUIZ_GRADE_SYSTEM,
            model=s.gemini_default_model,
            temperature=0.2,
        )
        score = float(payload.get("score", 0.0))
        return GradedAnswer(
            question_id=question.id,
            chosen_index=chosen_index,
            correct=False,
            score=max(0.0, min(1.0, score)),
            rationale=payload.get("rationale", question.explanation),
            misconception=payload.get("misconception"),
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Grading LLM failed, score=0 fallback. err=%s", exc)
        return GradedAnswer(
            question_id=question.id,
            chosen_index=chosen_index,
            correct=False,
            score=0.0,
            rationale=question.explanation or "Incorrect.",
            misconception=None,
        )
