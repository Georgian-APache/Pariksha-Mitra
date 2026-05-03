# ParikshaMitra — Replication Instructions for AI Agents

Use this document to rebuild **ParikshaMitra**: same product behavior, dual-stack architecture (Next.js + FastAPI), agent orchestration, and UI/UX patterns. Treat paths as relative to the repository root unless noted.

---

## 1. Product definition

**What it is:** An agentic AI study companion for Indian competitive exams (JEE Main, NEET, GATE, custom labels). It runs a **15-question onboarding diagnostic**, maintains a **concept-level mastery map** tied to a **prerequisite DAG**, computes **readiness**, generates a **7-day plan**, supports **adaptive quizzes** with lightweight CAT-style difficulty, **Snap-a-Doubt** (image/PDF), **RAG library** uploads, **voice ask**, **calendar (.ics) export**, and a **live agent trace** via SSE.

**UX pillars:**

- **Dark-first** UI with optional **light** theme (`data-theme` on `<html>`, persisted `pm.theme`).
- **Sticky header**: logo “ParikshaMitra”, Brain icon in gradient badge, “Agentic” outline badge, hackathon/team credit (`TeamCredit`), nav links (Dashboard, Quiz, Concept Graph, Snap-a-Doubt, Library), **streak HUD**.
- **Main**: max-width container (`max-w-7xl`), horizontal padding, scrollable content.
- **Global chrome**: footer team credit, floating **voice mic**, **Sonner** toasts (top-right, rich colors), **error boundary** around page children.
- **Typography**: Geist Sans / Geist Mono (Next.js `next/font/google`).
- **Motion**: Framer Motion on key screens (e.g. diagnostic question transitions).
- **Visual language**: Purple primary (`oklch` ~280 hue), cyan accent (~200), cards with border + subtle glass; gradient mesh background on `body` (fixed attachment).

---

## 2. Monorepo layout

```
frontend/          # Next.js 16 App Router
backend/           # FastAPI app package under backend/app/
```

Deliverables mirror this split: a **browser client** and a **Python API** that share no runtime but agree on HTTP contracts and JSON shapes.

---

## 3. Technology stack

### Frontend (`frontend/package.json`)

- **Next.js** 16.x (App Router), **React** 19.x
- **TypeScript**
- **Tailwind CSS** v4 (`@import "tailwindcss"` in `globals.css`, `@theme` tokens)
- **Radix UI** primitives (dialog, label, select, tabs, toast, tooltip, progress, slider, etc.)
- **framer-motion**, **lucide-react**, **recharts**, **cytoscape** + **react-cytoscapejs**, **sonner**, **class-variance-authority**, **tailwind-merge**

### Backend (`backend/requirements.txt`)

- **FastAPI**, **uvicorn[standard]**
- **Pydantic v2**, **pydantic-settings**
- **SQLAlchemy 2 async**, **aiosqlite** (local default)
- Optional **sqlalchemy-libsql** + Turso URL for production (`libsql://…` / `authToken=`)
- **LangGraph** (state graph for agents)
- **google-genai** (Gemini structured JSON), **groq** (optional fallback / voice transcription)
- **tenacity** (retries), **httpx**, **sse-starlette** (SSE)
- **networkx** (concept DAG), **numpy**
- **chromadb** + **pypdf** (RAG ingestion)
- **python-multipart** (uploads)

### Infrastructure conventions

- Backend listens on **`PORT`** in Docker/HF Spaces (default **7860**); local dev often **8000**.
- Frontend dev uses **`next.config.ts` rewrites**: `/pm-api/:path*` → backend origin (`BACKEND_DEV_PROXY_URL` or `http://127.0.0.1:8000`).
- CORS: backend allows configured origins plus regex for `localhost` / `127.0.0.1` with any port.

---

## 4. Configuration & secrets

### Backend (`backend/app/config.py`, env / `.env`)

| Variable | Role |
|----------|------|
| `DATABASE_URL` | Default local SQLite async URL under backend dir; or Turso/libSQL |
| `CORS_ORIGINS` | Comma-separated browser origins |
| `DEFAULT_GEMINI_API_KEY` | Server-side Gemini fallback |
| `DEFAULT_GROQ_API_KEY` | Server-side Groq fallback |
| `DEBUG` | Boolean |

**BYOK:** Every route that uses LLMs accepts optional headers **`X-Gemini-Key`** and **`X-Groq-Key`**; they override defaults.

### Frontend

| Variable | Role |
|----------|------|
| `NEXT_PUBLIC_API_URL` | If set, API calls go to this absolute origin (no `/pm-api`). If unset, use same-origin **`/pm-api`** rewrite |
| `BACKEND_DEV_PROXY_URL` | Rewrite target for `/pm-api` in dev |

### Client-side persistence

| Key | Storage | Purpose |
|-----|---------|---------|
| `pm.user_id` | `localStorage` | Current student id after onboarding start |
| `pm.theme` | `localStorage` | `dark` \| `light` \| `system` |
| `pm.diagnostic.questions` | `sessionStorage` | Diagnostic MCQ payload between onboarding and diagnostic page |
| `pm.last_run_id` | `sessionStorage` | Latest LangGraph run id for SSE |
| `pm.last_nudge` | `sessionStorage` | Last bilingual nudge JSON |

---

## 5. Static domain data (must ship with backend)

Under `backend/app/data/`:

- **`jee_dag.json`** — Concept graph for JEE_MAIN, GATE, and non-NEET exams (nodes: id, name, subject, weight, prereqs).
- **`neet_dag.json`** — NEET-specific graph.
- **`seed_questions.json`** — Curated MCQ bank keyed by `concept_id` / `subject`; used so diagnostics work when LLMs fail or rate-limit.

**DAG selection:** `get_dag(exam)` maps `NEET` → `neet_dag.json`, else → `jee_dag.json` (case-normalized).

---

## 6. Persistence model

ORM: SQLAlchemy (`backend/app/db/models.py`).

**`users`** (primary key string id UUID):

- Profile: `display_name`, `target_exam`, `exam_date`, `daily_hours`, `streak_days`, `last_active_date`
- JSON blobs: `mastery` (concept_id → float 0..1), `confidence`, `last_seen`, `sm2` (per-concept SM-2 card dicts), `plan` (weekly plan + nested `follow_up_test`), `readiness_history` (list of `{timestamp, readiness}`)

**Other tables:** `quiz_sessions`, `quiz_attempts`, `agent_trace_logs`, `rag_documents` — support sessions, grading history, persisted trace rows, RAG metadata.

**Initialization:** `init_db()` on app lifespan creates tables.

---

## 7. Core algorithms (reimplement faithfully)

### Readiness (`backend/app/intelligence/readiness.py`)

Composite score **0–100**:

`readiness = 100 * (0.4 * coverage + 0.3 * weighted_mastery + 0.2 * revision_sm2 + 0.1 * mock_trend)`

- **coverage / mastery:** derived from DAG + mastery dict (`concept_dag`, weighted helpers).
- **revision:** from SM-2 card due dates vs today (partial credit if mildly overdue).
- **mock_trend:** slope from last up to 7 readiness history points, normalized.

### SM-2 (`backend/app/intelligence/sm2.py`)

Cards stored per concept; `sm2_update` after quizzes/diagnostic blends intervals.

### CAT-lite (`backend/app/intelligence/cat_lite.py`)

Adaptive difficulty state stored in quiz session `state`; `next_difficulty` adjusts from performance.

### Rank prediction (`backend/app/intelligence/predictor.py`)

Monte-Carlo style **readiness percentile** projection from `exam_date` and history when date is set (`plan` dashboard).

---

## 8. Agent layer (LangGraph)

**Shared state:** Pydantic `StudentState` (`backend/app/agents/state.py`) — user profile, mastery, sm2, plan, diagnostic vs quiz results, readiness, weak prereqs, nudge, trace list, intent.

**LLM wrappers:** `backend/app/agents/llm.py` — `gemini_json` with **JSON schema** (`response_schema`), retries; Groq chat + transcription.

**Prompts:** Centralized in `backend/app/agents/prompts.py`.

**Nodes (summary):**

| Node | Responsibility |
|------|----------------|
| **analyst** | Recompute readiness, weak prerequisites, optional LLM “insight”; set `_should_replan` for routing |
| **planner** | 7-day `WeeklyPlan` from LLM + **heuristic fallback**; sanitize LLM blocks (`activity` ∈ learn/quiz/review/drill) |
| **personalizer** | LLM chooses follow-up test requests; `generate_questions`; writes `plan.follow_up_test` |
| **companion** | Bilingual **en/hi** nudge (LLM + heuristic) |

**Graphs** (`backend/app/agents/graph.py`):

1. **Full graph:** `analyst` → conditional → `planner` **or** skip to **`personalizer`** → `companion` → END.  
2. **Diagnostic graph:** always `analyst` → `planner` → `personalizer` → `companion` (first-time onboarding).

**Orchestration** (`backend/app/agents/orchestrator.py`):

- `run_diagnostic` / `run_post_quiz` compile graph, invoke `ainvoke({"student": state, "keys": keys})`, assign `run_id`.
- **`TraceBus`**: in-process pub/sub; `AgentStep` pushed as nodes run; closed when run completes.

**SSE:** `GET /stream/agent-trace/{run_id}` (`sse-starlette`) streams events `step` (JSON `AgentStep`), `ping`, `done`.

---

## 9. HTTP API surface (FastAPI)

Base path is **root** on the API host (frontend prefixes with `/pm-api` in dev).

| Prefix | Purpose |
|--------|---------|
| `/healthz` | Liveness JSON |
| `/users` | `POST` create / `GET /{user_id}` |
| `/onboard` | `POST /start` diagnostic MCQs; `POST /submit` grade + run diagnostic graph + persist |
| `/plan` | `GET /{user_id}/dashboard`; `POST /replan` full graph replan |
| `/quiz` | `POST /start`, `/answer`, `/finish` (finish runs post-quiz graph) |
| `/doubt` | Multimodal doubt (upload) |
| `/graph` | `GET /{user_id}` cytoscape payload + mastery |
| `/rag` | Upload, list docs, grounded quiz |
| `/calendar` | `GET /{user_id}.ics` |
| `/voice` | Voice ask (Groq STT + Gemini) |
| `/insights` | Dashboard insight POST |
| `/stream` | SSE agent trace |

**Auth model:** No end-user JWT; identity is **`user_id`** + optional API key headers for LLM providers.

---

## 10. Request/response shapes (align with frontend types)

Mirror `frontend/src/lib/types.ts` and backend Pydantic models:

- **`Question`:** id, concept_id, subject, difficulty 1–5, stem, options[4], correct_index, explanation, bilingual_hint?, source?
- **`WeeklyPlan`:** generated_at?, rationale, focus_concepts, days[{date, total_minutes, blocks[{subject, concept_id, minutes, activity, note?}]}]
- **`Readiness`:** coverage, mastery, revision, mock_trend, readiness, computed_at?
- **`Dashboard`:** aggregates plan, readiness, history, mastery, subject_mastery, rank_prediction?, nudge
- **Diagnostic:** `POST /onboard/start` returns `{ user_id, questions }`; **`POST /onboard/submit`** body includes full `questions` + `answers[{question_id, chosen_index}]`; response includes `run_id`, `readiness`, `plan`, `nudge`, `mastery`, `trace_count`

---

## 11. Frontend application map

### Routing (`frontend/src/app/`)

| Route | Role |
|-------|------|
| `/` | Marketing / hero CTA → onboarding |
| `/onboarding` | Step 1: exam profile → `POST /onboard/start` → save `user_id`, stash questions → `/onboarding/diagnostic` |
| `/onboarding/diagnostic` | 15 MCQs from sessionStorage; last step “Submit + generate plan” → `POST /onboard/submit` → dashboard |
| `/dashboard` | Load `GET /plan/{user_id}/dashboard`; charts (readiness gauge, radar, trend, rank); plan strip; agent trace; replan; pomodoro |
| `/quiz` | Adaptive/drill quiz flow via `/quiz/*` |
| `/graph` | Cytoscape concept graph |
| `/doubt` | Snap-a-Doubt uploads |
| `/library` | RAG docs + grounded quiz |

### API client (`frontend/src/lib/api.ts`)

- JSON `api()` with retries, timeouts, sanitized errors.
- **`API_URL`:** empty → `/pm-api` relative paths.
- **`uploadForm`** for multipart.
- **`absoluteApiUrl`** for SSE (`EventSource`) and downloads.

### Notable UI components (`frontend/src/components/`)

- **Header**, **StreakHud**, **ThemeToggle** (portal), **VoiceMic**, **TeamCredit**, **AgentTrace**, **PlanStrip**, **Pomodoro**, **ExplainSlider**, **IcsExportButton**, **ConceptGraph** (cytoscape), **charts/** (ReadinessGauge, SubjectRadar, TrendChart, RankPredictor), **ui/** primitives (Button, Card, Badge, Input, Dialog, Progress — cva-based variants).

### Styling tokens (`frontend/src/app/globals.css`)

- `@theme` defines semantic colors (`background`, `foreground`, `primary`, `accent`, `destructive`, `success`, `warning`, `border`, `card`, …).
- Dark default; **`[data-theme="light"]`** block overrides tokens and body gradients.
- Utilities: `.glass`, `.shimmer`, `.scrollbar-thin`.

---

## 12. Quiz flow (logic)

1. **`POST /quiz/start`:** resolve `concept_id` (body override → plan focus → weakest mastery in DAG); build CAT state; generate questions (`prefer_seed=True`); persist session; return first question + progress + cat snapshot.
2. **`POST /quiz/answer`:** grade (deterministic correct match + optional LLM partial credit); update mastery, SM-2, CAT; return next question or terminal status.
3. **`POST /quiz/finish`:** run **`run_post_quiz`** graph; return `run_id` etc.; client may open SSE.

---

## 13. Replication workflow (recommended order)

1. **Scaffold backend:** FastAPI app, lifespan DB init, CORS, `/healthz`.
2. **Implement models + SQLite async session**; migrations optional if using `create_all`.
3. **Import DAG JSON + seed bank**; implement `ConceptDAG`, readiness, SM-2, CAT-lite, predictor.
4. **Implement repositories** (user upsert/get, state updates, quiz sessions, traces, RAG metadata).
5. **Implement LLM layer** (Gemini JSON schema + retries; Groq optional).
6. **Define `StudentState`, prompts, WeeklyPlan sanitization**, graph wiring, orchestrator + SSE bus + `/stream/agent-trace/{run_id}`.
7. **Implement routes** in dependency order: users → onboard → plan dashboard → quiz → graph → rag → doubt → voice → calendar → insights.
8. **Scaffold frontend:** Next.js App Router, layout, globals.css tokens, ThemeProvider, Header, fonts.
9. **Implement `api.ts`, `byok.ts`, types**, then pages mirroring flows above.
10. **Wire dev proxy** (`next.config.ts` rewrites).
11. **Polish UX:** loading states, toasts on errors, motion on diagnostic, charts on dashboard, graph visualization.

---

## 14. Verification checklist

- Local: backend `/healthz` OK; frontend `/pm-api/healthz` OK via rewrite.
- Onboarding: start returns 15 questions; submit persists user, returns plan + nudge + run_id without 500 when LLM output is imperfect (sanitized planner).
- Dashboard: readiness numbers stable; rank prediction appears when `exam_date` set.
- Quiz: full answer loop + finish triggers SSE steps.
- Theme toggle persists; layout intact on mobile (nav may collapse — match reference or add sheet menu).
- Production paths: set `DATABASE_URL` for Turso; `CORS_ORIGINS` for frontend origin; timeouts adequate for long agent runs.

---

## 15. Explicit non-requirements

- You may substitute hosting (Vercel + HF Spaces / Railway / Fly) as long as rewrite/CORS/env vars preserve behavior.
- You do **not** need feature parity with future forks unless specified — this document reflects the described codebase architecture.

---

*End of replication instructions.*
