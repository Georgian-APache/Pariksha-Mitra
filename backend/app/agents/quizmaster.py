"""QuizMaster agent - generates and grades MCQs."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from app.agents.llm import gemini_json
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
from app.intelligence.concept_dag import get_dag

log = logging.getLogger("parikshamitra.quizmaster")


def _seed_bank() -> list[dict[str, Any]]:
    path = Path(DATA_DIR) / "seed_questions.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _seed_questions_for(concept_id: str, difficulty: int, n: int = 1) -> list[Question]:
    bank = _seed_bank()
    candidates = [q for q in bank if q.get("concept_id") == concept_id]
    if not candidates:
        return []
    # Sort by closeness to the requested difficulty, then take ``n``
    candidates.sort(key=lambda q: abs(q.get("difficulty", 3) - difficulty))
    out: list[Question] = []
    for q in candidates[:n]:
        out.append(
            Question(
                id=q.get("id") or str(uuid.uuid4()),
                concept_id=q["concept_id"],
                subject=q["subject"],
                difficulty=q.get("difficulty", difficulty),
                stem=q["stem"],
                options=q["options"],
                correct_index=q["correct_index"],
                explanation=q.get("explanation", ""),
                bilingual_hint=q.get("bilingual_hint"),
                source="seed",
            )
        )
    return out


async def generate_questions(
    *,
    keys: APIKeys,
    requests: list[dict],
    exam: str = "JEE_MAIN",
    prefer_seed: bool = True,
) -> list[Question]:
    """Each ``request`` is ``{concept_id, subject, difficulty}``."""

    dag = get_dag(exam)
    out: list[Question] = []
    pending: list[dict] = []
    for r in requests:
        cid = r["concept_id"]
        diff = int(r.get("difficulty", 3))
        subject = r.get("subject") or dag.info(cid).get("subject", "")
        if prefer_seed:
            seeds = _seed_questions_for(cid, diff, n=1)
            if seeds:
                out.extend(seeds)
                continue
        pending.append({"concept_id": cid, "subject": subject, "difficulty": diff})

    if pending:
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
            for q in payload.get("questions", []):
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
        except Exception as exc:  # noqa: BLE001
            log.warning("Quiz generation LLM failed, using stub. err=%s", exc)
            for r in pending:
                out.append(_stub_question(r["concept_id"], r["subject"], r["difficulty"]))
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
