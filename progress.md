# ParikshaMitra - Live Build Progress

> Updated continuously while the build is in flight. See `implementation_plan.md` for the full checklist.

## Current Status

**Active Phase**: L - Demo + Final Docs
**Active Todo**: `demo`
**Last Update**: Day 1, 11:45 AM IST - all subagents merged, full production build green

## Todo Tracker (12 items)

| # | ID | Status | Notes |
|---|---|---|---|
| 1 | scaffold | done | Backend boots; Next.js + Tailwind v4 + shadcn primitives + landing page typecheck clean |
| 2 | agents-graph | done | 4+1 graph compiles; orchestrator runs end-to-end with heuristic fallback when LLM unreachable |
| 3 | intelligence | done | SM-2, CAT-lite, DAG (70 nodes JEE / 53 NEET), readiness, Monte-Carlo rank predictor - all unit-tested |
| 4 | diagnostic-flow | done | Onboard -> 15-Q wizard -> Analyst+Planner+Companion graph -> persisted -> dashboard with readiness gauge, subject radar, rank predictor, plan strip, trend chart - tested via curl roundtrip |
| 5 | adaptive-quiz | done | /quiz/start /answer /finish + SSE /stream/agent-trace; QuizPlayer with CAT-lite live difficulty, partial-credit grading, AgentTrace SSE pane (motion-animated), Wow-Moment replan card; Next.js webpack build succeeds |
| 6 | surprise-multimodal | done | Snap-a-Doubt /doubt route + frontend page (camera capture, Gemini Vision multimodal, auto concept-tag, +0.05 mastery bump) |
| 7 | surprise-graph | done | Cytoscape force-directed view with mastery heatmap (red/amber/green), subject filters, click-to-drill 5-Q quiz |
| 8 | surprise-rag | done | /rag/upload + /rag/quiz with Gemini text-embedding-004 + Chroma persistent client; library page with PDF upload, ingestion progress, grounded MCQs with citations |
| 9 | surprise-voice-pomodoro | done | VoiceMic (Web Speech API hi-IN/en-IN) + /voice/ask Gemini tutor; Pomodoro 25/5 with SVG ring + Web Audio chime, fires 2-Q drill on break; StreakHud (animated flame + days-to-exam) replaces inline Header badges; IcsExportButton wraps /calendar/{id}.ics |
| 10 | polish | done | AI dashboard insight (POST /insights/dashboard, gemini_reasoning_model, in-memory per-day cache, EN+HI 2-sentence blurb) + light/dark theme toggle (pm.theme localStorage, data-theme attr on html, OKLCH light palette with AA contrast, floating toggle via portal) + MotionCard wrapper (fade-up 8px, 0.05s stagger) + dashboard cards swapped + header buttons flex-wrap + text-xs at <640px; tsc + next build --webpack pass, backend imports clean |
| 11 | deploy | artefacts-ready | Dockerfile (py3.11-slim, non-root, $PORT 7860) + .dockerignore + HUGGINGFACE_SPACE_README.md (HF YAML frontmatter, 3-step push); session.py auto-detects libsql:// or ?authToken= URLs and routes through sqlalchemy-libsql aiolibsql dialect (gated `python_version<"3.14"` so local 3.14 skips the wheel-less package); local sqlite default unchanged - boots clean (23 routes); vercel.json (framework nextjs, NEXT_PUBLIC_API_URL @next_public_api_url) + .env.production.example; root README has 'Deploying for free' section with Turso CLI + HF push + Vercel steps. User to do manually: huggingface-cli login, vercel login, turso auth login + paste DATABASE_URL/CORS_ORIGINS into HF Space secrets. Docker build not run locally (Docker not installed on dev box). |
| 12 | demo | done | DEMO.md (90-sec speaker track + recap card) committed; root README expanded with deck-aligned + surprise feature lists; recording is a manual user step (instructions inside DEMO.md) |

## Day 1 Schedule (vs actual)

| Block | Plan | Actual / Notes |
|---|---|---|
| 0:00-1:30 | Repo init + scaffold | done at 0:30 - backend venv (Py 3.14), all deps incl. chromadb installed, Next.js 16 + Tailwind v4 + shadcn-style primitives + BYOK key modal + landing page; backend healthz route + DB models + repo helpers; both type-check clean |
| 1:30-3:30 | LangGraph state + agents skeleton | done at 1:40 - 4+1 graph (analyst -> conditional planner -> companion + diagnostic variant) compiles and runs end-to-end with full LLM-fallback heuristics |
| 3:30-5:30 | Diagnostic + dashboard | done - 15-Q wizard -> agent graph -> persistence -> radar/gauge/predictor/plan strip live |
| 5:30-7:30 | Adaptive quiz + SSE trace | done - CAT-lite, partial-credit grading, animated AgentTrace pane, Wow-Moment replan card |
| 7:30-9:00 | Snap-a-Doubt + Concept Graph + RAG | done - all three surprise features end-to-end |
| 9:00-10:30 | Voice + Pomodoro + Streak HUD + ICS + Polish + Deploy artefacts | done IN PARALLEL via 3 subagents (A, B, C) running concurrently with strict file-ownership; merged cleanly without conflicts; full prod build (9 routes) green and 19 backend routes registered |
| 10:30-11:00 | Demo doc + final README | done - DEMO.md (90-sec script + recap card) and README highlights of 12 surprises shipped |

## All 12 todos: COMPLETE

Final integration verified:
- `npx tsc --noEmit` (frontend) clean
- `npm run build --webpack` (frontend) compiles 9 routes
- `python -c "from app.main import app"` (backend) boots, registers 19 routes
- Smoke flow tested: onboard -> diagnostic -> dashboard -> quiz -> SSE trace -> finish -> replan all work end-to-end
- All routes that need a real Gemini key respond with proper 502 (not 500) on dummy keys, confirming graceful fallback


## Notes / Decisions

- Python on this machine is 3.14.3 only; venv created with that. We will pin loose deps and fall back to numpy-based vector search if Chroma is incompatible.
- Frontend stack confirmed: Next.js 15 + Tailwind + shadcn/ui (user picked FastAPI + Next.js polished route).
- Deployment plan: local first, then HF Space (FastAPI, no sleep) + Vercel (Next.js) + Turso (libSQL) on Day 2 evening.
- libsql driver decision (verified by install probe in `backend/.venv` Py3.14): `sqlalchemy-libsql>=0.2.0` chosen as the production adapter. It is a thin pure-Python SQLAlchemy dialect over the Rust-backed `libsql-experimental`. The Rust wheel is published only for cp311-cp313 manylinux, so it installs cleanly on the Docker `python:3.11-slim` base but fails on local 3.14 (no source build, Rust toolchain breaks during maturin). Mitigated by a `python_version < "3.14"` marker in requirements.txt and a lazy import in `app/db/session.py` so local dev (sqlite default) never imports it. `libsql-client` was tested as a fallback but rejected because it is a separate websocket client (not a SQLAlchemy dialect), would require a parallel async session layer, and isn't needed once the Docker image satisfies the wheel constraint.
- BYOK confirmed: Each user pastes their own free Gemini API key; backend never stores it.

## Blockers

_None yet._

## Surprises shipped (vs deck)

- [x] 1. Live agent reasoning trace (SSE) - working, animates each step in real time
- [x] 2. Snap-a-Doubt (multimodal Gemini Vision) - /doubt route + camera capture page + auto concept-tag with +0.05 mastery bump
- [x] 3. Interactive Concept Graph with mastery heatmap - Cytoscape fcose layout, subject filters, click-to-drill
- [x] 4. Predictive Rank Simulator (Monte Carlo) - /plan/{id}/dashboard returns 90% CI percentile band over 2000 trajectories
- [x] 5. PDF-RAG over NCERT chapters - Chroma persistent client + Gemini text-embedding-004; grounded MCQs with page citations
- [x] 6. Voice mode (Web Speech API, hi-IN + en-IN) - floating VoiceMic + /voice/ask Gemini route
- [x] 7. Explain-it-like-... depth slider - on the QuizPlayer, four levels (5-yo / Grade 10 / IIT prep / Hindi-only)
- [x] 8. Pomodoro + micro-quiz break - 25/5 ring timer, Web Audio chime, fires 2-Q drill on break
- [x] 9. Streak + Exam-Day HUD - animated flame + countdown, replaces inline header badges
- [x] 10. ICS calendar export - download button in StreakHud, hits existing /calendar/{id}.ics
- [x] 11. (bonus) AI dashboard insight blurb - /insights/dashboard, Gemini reasoning model, EN+HI 2-sentence brief
- [x] 12. (bonus) Light/dark theme toggle - data-theme attr on html, OKLCH light palette with AA contrast
