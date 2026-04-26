# ParikshaMitra - Implementation Plan

> Companion document to `parikshamitra-2day-build_*.plan.md`. This file is the single source of truth for the engineering checklist while the build is in flight. `progress.md` tracks live status.

## 0. Conventions

- All paths relative to repo root: `c:\Users\Georgian\OneDrive\Desktop\ParikshaMitra\`
- Backend: Python 3.14 venv at `backend/.venv`, deps in `backend/requirements.txt`
- Frontend: Next.js 15 App Router at `frontend/`, pnpm/npm with shadcn/ui
- BYOK: every API request from frontend includes header `X-Gemini-Key` (and optional `X-Groq-Key`); backend never persists keys.

## 1. Phase A - Scaffolding (Todo: `scaffold`)

### 1.1 Backend skeleton
- [x] `backend/.venv` created (Python 3.14.3)
- [x] `backend/requirements.txt` pinned
- [ ] `pip install -r requirements.txt` succeeds
- [ ] `backend/app/__init__.py`, `backend/app/main.py` (FastAPI + CORS + health)
- [ ] `backend/app/config.py` - `Settings` (pydantic-settings) with `DATABASE_URL`, `CORS_ORIGINS`, model picks; BYOK header parsing helper
- [ ] `backend/app/db/__init__.py`, `db/models.py`, `db/session.py`, `db/repositories.py`
- [ ] `backend/.env.example` with placeholder keys
- [ ] `backend/run.ps1` convenience launcher (`uvicorn app.main:app --reload --port 8000`)

### 1.2 Frontend skeleton
- [ ] `npx create-next-app@latest frontend` (TS, Tailwind, App Router, no src dir)
- [ ] shadcn/ui init + base components (`button card input dialog progress badge tabs toast sheet`)
- [ ] `frontend/lib/byok.ts` - localStorage wrapper for `gemini_key` / `groq_key`
- [ ] `frontend/lib/api.ts` - typed fetch wrapper that injects BYOK headers and base URL from `NEXT_PUBLIC_API_URL`
- [ ] `frontend/components/ui/key-modal.tsx` - first-run modal asking for free Gemini key with "get one free" link
- [ ] `frontend/app/layout.tsx` - shell, dark mode, exam-day countdown HUD slot
- [ ] `frontend/app/page.tsx` - landing page

### 1.3 Repo hygiene
- [ ] Root `README.md` with one-shot run instructions
- [ ] `.gitignore` covering `.venv/`, `node_modules/`, `*.db`, `.env`, `.next/`, `chroma_store/`
- [ ] `progress.md` (live status, this file's sibling)

## 2. Phase B - LangGraph 4+1 Agents (Todo: `agents-graph`)

Files under `backend/app/agents/`:
- [ ] `state.py` - `StudentState`, `SM2Card`, `WeeklyPlan`, `AgentStep`, `Question`, `QuizSession`
- [ ] `prompts.py` - JSON schemas + system prompts for Planner, QuizMaster (gen + grade), Analyst, Companion
- [ ] `llm.py` - thin Gemini + Groq client wrappers, retry with tenacity, structured-output via `responseSchema`
- [ ] `planner.py`, `quizmaster.py`, `analyst.py`, `companion.py` (one node each, returns partial state update + `AgentStep`)
- [ ] `graph.py` - `StateGraph` wiring with conditional edges (`should_replan`, `should_intervene`)
- [ ] `orchestrator.py` - public `run_diagnostic`, `run_quiz_turn`, `run_replan` async helpers that yield trace events

## 3. Phase C - Intelligence Engine (Todo: `intelligence`)

Files under `backend/app/intelligence/`:
- [ ] `sm2.py` - `update(card, score) -> SM2Card` (>0.8 -> *2; 0.5-0.8 -> hold; <0.5 -> 1d reset). Also `due_today(cards) -> list`.
- [ ] `cat_lite.py` - `next_level(history) -> 1..5` with the +3/-2 rule and clamp.
- [ ] `concept_dag.py` - NetworkX DiGraph loaded from `data/jee_dag.json`; `prerequisites_of(node)`, `weak_prereqs(node, mastery)`.
- [ ] `readiness.py` - `0.4*coverage + 0.3*mastery + 0.2*revision + 0.1*mock_trend`
- [ ] `predictor.py` - Monte Carlo over readiness deltas; outputs mean + 90% CI percentile by exam date
- [ ] `data/jee_dag.json` - ~80 nodes (Physics, Chem, Math) with `prereqs`, `weight` (exam weightage), `subject`
- [ ] `data/neet_dag.json` - ~80 nodes (Physics, Chem, Bio)
- [ ] `data/seed_questions.json` - ~250 MCQs across topics, difficulty 1-5, with explanation + concept tag

## 4. Phase D - Diagnostic Flow (Todo: `diagnostic-flow`)

- [ ] `routes/onboarding.py` - `POST /onboard/start` (returns 15 calibration MCQs spanning subjects); `POST /onboard/submit` (runs Analyst+Planner, persists, returns plan + readiness)
- [ ] `routes/plan.py` - `GET /plan/current`, `POST /plan/replan`
- [ ] `db/models.py` - `User`, `Session`, `Mastery`, `SM2Card`, `Plan`, `QuizAttempt`, `Trace`
- [ ] Frontend `app/onboarding/page.tsx` - exam picker, date picker, hours/day, BYOK gate
- [ ] Frontend `app/onboarding/diagnostic/page.tsx` - 15-Q wizard with progress bar
- [ ] Frontend `app/dashboard/page.tsx` - readiness gauge, radar chart (per-subject), today's plan strip
- [ ] Components: `ReadinessGauge.tsx`, `RadarChart.tsx`, `PlanStrip.tsx`

## 5. Phase E - Adaptive Quiz + Live Trace (Todo: `adaptive-quiz`)

- [ ] `routes/quiz.py` - `POST /quiz/start`, `POST /quiz/answer`, `POST /quiz/finish` (triggers analyst + maybe replan)
- [ ] `routes/stream.py` - `GET /stream/agent-trace/{run_id}` SSE endpoint
- [ ] QuizMaster: per-question difficulty selection via CAT-lite + Gemini structured-output for explanations + partial credit
- [ ] Frontend `app/quiz/page.tsx` - QuizPlayer with explain-it-like-... slider
- [ ] Frontend `components/AgentTrace.tsx` - subscribes to SSE, animated step list
- [ ] Reflective replan trigger: if Analyst detects mastery drop > 0.15 OR weak prereq, fires Companion + Planner

## 6. Phase F - Surprise: Snap-a-Doubt (Todo: `surprise-multimodal`)

- [ ] `routes/doubt.py` - `POST /doubt/snap` (multipart image) -> Gemini 2.0 Flash Vision -> JSON {answer, steps, concept_tag, confidence}
- [ ] Update `mastery[concept_tag]` if user marks "still unclear"
- [ ] Frontend `app/doubt/page.tsx` - file picker + camera capture + result card

## 7. Phase G - Surprise: Concept Graph (Todo: `surprise-graph`)

- [ ] `routes/graph.py` - `GET /graph/concepts` returns nodes + edges + mastery overlay
- [ ] `POST /graph/drill/{concept_id}` - launches a focused 5-Q QuizSession
- [ ] Frontend `app/graph/page.tsx` - Cytoscape.js force-directed view, mastery heatmap (red->amber->green), click->drill modal

## 8. Phase H - Surprise: PDF-RAG (Todo: `surprise-rag`)

- [ ] `rag/ingestion.py` - pypdf -> chunk -> Gemini `text-embedding-004` -> Chroma collection per user
- [ ] `rag/retrieval.py` - top-k retrieval helper
- [ ] `routes/rag.py` - `POST /rag/upload`, `POST /rag/quiz/{collection}` (grounded MCQs with citations)
- [ ] Frontend `app/library/page.tsx` - upload PDFs, see ingestion progress, launch grounded quiz

## 9. Phase I - Surprise: Voice + Pomodoro + ICS (Todo: `surprise-voice-pomodoro`)

- [ ] Frontend `components/VoiceMic.tsx` - Web Speech API STT + speechSynthesis TTS, language toggle hi-IN/en-IN
- [ ] Frontend `components/Pomodoro.tsx` - 25/5 timer with break-time micro-quiz pop
- [ ] Frontend `components/StreakHud.tsx` - streak count + days-to-exam countdown
- [ ] Backend `routes/calendar.py` - `GET /calendar/ics` returns `.ics` file built from current plan
- [ ] (Optional, Day 2 hour 11+ slack) Groq Whisper STT route as upgrade path

## 10. Phase J - Polish (Todo: `polish`)

- [ ] Custom Tailwind theme matching deck (deep indigo + cyan accents)
- [ ] Framer Motion page transitions and trace animations
- [ ] Mobile responsive (test at 375px)
- [ ] Dark mode default with light toggle
- [ ] AI-generated dashboard insight blurb (Gemini 2.5 Flash, 1 call/dashboard load, cached 5 min)

## 11. Phase K - Deploy (Todo: `deploy`)

- [ ] `backend/Dockerfile` (Python 3.11 slim base, non-root user, port 7860 for HF Spaces)
- [ ] `backend/.dockerignore`
- [ ] HF Space `Dockerfile` README + repo push
- [ ] Turso DB provision + `DATABASE_URL` env (libsql driver fallback to local sqlite)
- [ ] Frontend `vercel.json` + env `NEXT_PUBLIC_API_URL`
- [ ] CORS config update with prod origins
- [ ] Smoke test public URL end-to-end

## 12. Phase L - Demo + Docs (Todo: `demo`)

- [ ] `README.md` - architecture, setup, BYOK key instructions, demo flow
- [ ] `DEMO.md` - 90-second walkthrough script
- [ ] Hero screenshot + GIF in `docs/`

## Risk Log

| Risk | Mitigation | Status |
|---|---|---|
| Python 3.14 incompatibility with some libs | Pin loose, fall back to `numpy`+`sklearn` knn instead of Chroma if needed | open |
| Gemini 250 RPD on 2.5 Flash | Use 2.0 Flash for bulk, 2.5 Flash only for replan/insight | mitigated by config |
| HF Space ephemeral disk | Turso DB; Chroma rebuilt from PDFs at boot | mitigated |
| Time overrun on Day 2 | Surprises 8-10 (Calendar, ICS, Pomodoro upgrades) gated behind slack | scoped |

