# ParikshaMitra - 90 Second Demo Script

> Use this as the speaker track for a hackathon demo or screen recording. Total: ~90 seconds. Every line maps to one click.

## Pre-flight (10 seconds before recording)

1. Both servers running:
   ```powershell
   # Terminal 1
   cd backend; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --port 8000

   # Terminal 2
   cd frontend; npm run dev
   ```
2. Browser open at <http://localhost:3000>; localStorage cleared.
3. Have a free Gemini key ready from <https://aistudio.google.com/apikey>.
4. (Optional) Print one handwritten physics question on paper for the Snap-a-Doubt segment.

## The 90 second walkthrough

### 0:00 - 0:08 - The hook (landing page)

> "ParikshaMitra is an agentic AI study companion for India's 40 million competitive-exam students. It runs on free Gemini tier - zero cost forever. Let me show you four things no other study app does."

Click **Add key**, paste Gemini key, save. Click **Start free diagnostic**.

### 0:08 - 0:25 - Step 1: Setup + Diagnostic (deck step 1)

> "Pick exam, date, study hours. Fifteen-question calibration spans physics, chemistry and math. I'll deliberately tank Newton's Laws and vectors..."

Fill: JEE Main, 2026-04-19, 3h. Click **Start 15-question diagnostic**. Power-skim through 15 questions, intentionally fumbling a Newton's Laws and a Vectors question, getting most others right. Submit.

### 0:25 - 0:40 - Step 2: Autonomous planning (deck step 2)

> "Within seconds, the LangGraph 4+1 architecture ran: Analyst diagnosed me, Planner generated a 7-day schedule biased toward weak topics, Companion wrote a bilingual nudge."

Land on **Dashboard**. Show:
- **Readiness gauge**: 38/100
- **Subject radar**: Physics low, Math low
- **Predicted percentile**: 41 +/- 5 by exam day
- **This week's plan**: scrolling daily blocks; Newton's Laws shows up multiple times
- **Companion nudge** card with English + Hindi text

### 0:40 - 0:65 - Step 3: THE WOW MOMENT - reflective replanning (deck step 3, plus surprise #1)

> "Here is the surprise. I'll start an adaptive Newton's Laws quiz. Watch the right pane: every LangGraph agent step streams live."

Click **Adaptive quiz** -> the question loads. Submit a wrong answer; submit a half-right answer; submit a wrong answer. Quiz auto-finishes after 5 Q's; the right sidebar fills with:
- Orchestrator: "Run started"
- Analyst: "Readiness 33/100, 3 weak prereqs"
- Planner: "Replanned week" (the WOW moment)
- Companion: "Bilingual nudge ready"

> "The Analyst found my Vectors mastery is 0.2 - it walked the dependency DAG, flagged the prerequisite, the Planner re-ran, the Companion explained the change in Hindi and English. No human prompt."

### 0:65 - 0:78 - Surprises 2 + 3: Snap-a-Doubt + Concept Graph

Click **Snap-a-Doubt**. Take a photo of the printed handwritten question. The Gemini Vision agent answers, identifies the concept, mastery ticks up by 0.05.

> "That photo just got tagged into my knowledge graph. Speaking of which..."

Click **Concept Graph**. Cytoscape view appears with mastery heatmap.

> "Red is weak, green is strong. Click the red Vectors node, drill 5 questions on it - directly from the graph."

### 0:78 - 0:90 - Surprises 4 + 5: rank prediction + voice

Back to **Dashboard**, point at **Predicted exam-day percentile** card with the 90% confidence band.

> "Monte Carlo over 2,000 trajectories of my readiness deltas. By April 19th I'm projected at 88 plus or minus 3 percentile."

Tap floating mic, say in Hindi: "Newton ka tisra niyam samjhao."

> "Web Speech API. Speech in, Gemini reasoning, speech out. Hindi or English. Zero cost."

Land. Done.

## The closing line

> "ParikshaMitra: an AI that studies *you*, so you can study smarter. Free Gemini key, free deploy, free hosting, free forever. Built in 2 days on the deck's exact 4+1 cognitive architecture - plus seven things the deck did not promise."

## What the audience just saw (recap card)

| Deck promise | Shipped | Bonus surprise |
|---|---|---|
| Smart Onboarding 15-Q | yes | live agent reasoning trace (SSE) |
| Performance Dashboard (radar + insight) | yes | Snap-a-Doubt multimodal Gemini Vision |
| Dynamic Quiz Engine (CAT-lite) | yes | interactive Cytoscape concept graph |
| Spaced Repetition Calendar | yes | predictive Monte Carlo rank simulator |
| Bilingual Companion | yes | voice mode (Web Speech API) |
| 4+1 LangGraph architecture | yes | PDF-RAG over NCERT chapters |
| SM-2 + readiness 0.4*Cov+0.3*Mast+0.2*Rev+0.1*Mock | yes | Pomodoro micro-quiz + streak HUD + ICS export |

## Recording tips

- 1280x720 capture (good for hackathon submissions).
- Hide the API key field after pasting (use blur in OBS or paste then delete the visible text from the input).
- If a Gemini call is slow, narrate the agent trace pane while it streams - it makes the wait part of the demo.
- Have the Hindi voice prompt rehearsed; Web Speech API STT is sensitive to accent and noise.
