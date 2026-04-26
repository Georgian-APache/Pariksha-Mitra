# ParikshaMitra (परीक्षा मित्र)

> An AI that studies you, so you can study smarter. An agentic AI study companion for Indian competitive exams.

Built better than the deck, on a strict zero-cost stack, in 2 days.

## What's in the box

A live LangGraph **4+1** cognitive architecture (Orchestrator + Planner + QuizMaster + Analyst + Companion) that autonomously plans, tests, diagnoses and re-plans a JEE / NEET aspirant's preparation - everything the original deck promised, plus twelve net-new surprises.

**Deck-aligned features**

- 15-question diagnostic that calibrates a per-concept knowledge graph
- Autonomous weekly plan biased to weak topics + exam weightage
- Adaptive **CAT-lite** quiz engine (levels 1-5; +3 correct / -2 wrong)
- **SM-2** spaced repetition (>0.8 -> 2x; 0.5-0.8 hold; <0.5 -> 1d reset)
- Concept dependency DAG (70 nodes JEE / 53 NEET) with prerequisite-gap detection
- Readiness score `0.4*Coverage + 0.3*Mastery + 0.2*Revision + 0.1*Mock`
- Bilingual (en + hi) Companion nudges
- Persistent Student Knowledge Graph

**Surprises (net-new vs the deck)**

1. **Live agent reasoning trace** - SSE-streamed LangGraph node steps animated in the quiz pane
2. **Snap-a-Doubt** - photograph any handwritten problem, Gemini Vision solves + auto-tags the concept
3. **Interactive Concept Graph** - Cytoscape force-directed view, mastery heatmap, click-to-drill
4. **Predictive Rank Simulator** - Monte Carlo over readiness deltas; outputs 90% CI percentile by exam day
5. **PDF-RAG over NCERT** - Gemini embeddings + Chroma; grounded MCQs with page citations
6. **Voice mode** - Web Speech API STT/TTS in Hindi + English, plus a Gemini tutor route
7. **Explain-it-like-... slider** - 5-yo / Grade 10 / IIT prep / Hindi-only re-explanations
8. **Pomodoro + micro-quiz** - 25/5 ring timer with Web Audio chime; break auto-pops a 2-Q drill
9. **Streak + Exam-Day HUD** - animated flame counter with countdown to exam
10. **One-tap ICS export** of the weekly plan to any calendar app
11. **AI dashboard insight** - Gemini reasoning model writes a 2-sentence EN+HI brief on what to do next
12. **Light/dark theme toggle** - OKLCH palettes with AA contrast in both modes

See `DEMO.md` for the 90-second walkthrough script and
`implementation_plan.md` + `progress.md` for the live engineering log.

## Stack

- **LLM**: Google Gemini 2.0 / 2.5 Flash via free AI Studio (BYOK headers - never persisted server-side)
- **Voice / fallback**: Groq `llama-3.1-8b-instant` + `whisper-large-v3-turbo` (free)
- **Backend**: Python 3.11+ / FastAPI / LangGraph / Pydantic v2 / SQLAlchemy 2 (async) / Chroma / NetworkX
- **Frontend**: Next.js 16 + Tailwind v4 + shadcn-style primitives + Recharts + Cytoscape + Framer Motion
- **Persistence**: SQLite (local) -> Turso libSQL (cloud, free)
- **Hosting**: HF Spaces (FastAPI Docker) + Vercel (Next.js) + Turso (DB)

## Quick start (local)

```powershell
# 1. Backend
cd backend
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env  # edit if you want a dev fallback key
uvicorn app.main:app --reload --port 8000

# 2. Frontend (in a second terminal)
cd frontend
npm install
npm run dev   # http://localhost:3000
```

Open the app, click **Add key**, paste your free Gemini API key from
<https://aistudio.google.com/apikey> (no credit card required), and start the
diagnostic.

## Layout

```
parikshamitra/
  backend/   FastAPI + LangGraph 4+1 agents + intelligence engines
  frontend/  Next.js App Router UI
  ParikshaMitra.pdf       Original concept deck
  implementation_plan.md  Engineering checklist (live)
  progress.md             Live build status
```

See `implementation_plan.md` and `progress.md` for the running checklist.

## Deploying for free (HF Spaces + Vercel + Turso)

The whole stack runs on free tiers, no credit card required. Three pieces:

| Piece | Host | Free tier |
|---|---|---|
| Backend (FastAPI Docker) | Hugging Face Spaces | 16 GB RAM, 2 vCPU, **no sleep** |
| Frontend (Next.js) | Vercel Hobby | unlimited deploys, edge CDN |
| Database (libSQL) | Turso | 9 GB, 1 B row reads / mo |

### 1. Provision Turso (~2 min)

```bash
curl -sSfL https://get.tur.so/install.sh | bash    # one-line CLI install
turso auth login
turso db create parikshamitra
turso db show parikshamitra --url                  # libsql://...turso.io
turso db tokens create parikshamitra               # long JWT
```

Build the connection string: `libsql://<db>-<org>.turso.io?authToken=<token>`.
Keep it for the next step. The backend's `app/db/session.py` detects this URL
automatically and routes through the `sqlalchemy-libsql` async dialect; the
local SQLite path stays unchanged when the env var is unset.

### 2. Deploy backend to Hugging Face Spaces (~5 min)

```bash
cd backend
pip install -U "huggingface_hub[cli]"
huggingface-cli login                              # paste a write-scope token
huggingface-cli repo create parikshamitra-backend --type space --space_sdk docker

git init
cp HUGGINGFACE_SPACE_README.md README.md           # YAML frontmatter HF needs
git remote add space https://huggingface.co/spaces/<your-username>/parikshamitra-backend
git add Dockerfile .dockerignore requirements.txt app/ README.md
git commit -m "Deploy ParikshaMitra backend"
git push -u space main
```

Then in the Space's **Settings -> Variables and Secrets** add:

- `DATABASE_URL` (secret) - the Turso connection string from step 1
- `CORS_ORIGINS` - `https://<your-app>.vercel.app,https://<your-app>-*.vercel.app`
- `DEBUG=false`
- (optional) `DEFAULT_GEMINI_API_KEY` / `DEFAULT_GROQ_API_KEY` - leave blank to enforce BYOK

Public URL: `https://<your-username>-parikshamitra-backend.hf.space`. Hit
`/healthz` to verify. See `backend/HUGGINGFACE_SPACE_README.md` for the full
playbook including troubleshooting.

### 3. Deploy frontend to Vercel (~3 min)

```bash
cd frontend
npx vercel                                          # first run links the project
npx vercel --prod                                   # production deploy
```

Or import the GitHub repo at <https://vercel.com/new> and point the root to
`frontend/`. `frontend/vercel.json` already declares `framework: "nextjs"` and
the `npm run build` script. The build script keeps `--webpack` because Windows
local dev lacks the SWC native binary; on Vercel's Linux builders it still
works (just slightly slower than the default Turbopack/SWC pipeline) and
avoids any drift between local and prod toolchains.

In Vercel **Settings -> Environment Variables** add (for Production + Preview):

- `NEXT_PUBLIC_API_URL=https://<your-username>-parikshamitra-backend.hf.space`

A template lives at `frontend/.env.production.example`.

### 4. Smoke test the public stack

```bash
curl https://<hf-username>-parikshamitra-backend.hf.space/healthz
# -> {"status":"ok","app":"ParikshaMitra"}
```

Open the Vercel URL, paste a free Gemini key, run the diagnostic. You should
see writes land in Turso (`turso db shell parikshamitra "select * from users"`).

### Cost ceiling

Zero, forever, as long as you stay within the free tiers above. BYOK keeps
LLM cost off your card too - each user pastes their own Gemini AI Studio key.

## License

MIT (TBD on push).
