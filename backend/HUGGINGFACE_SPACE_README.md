---
title: ParikshaMitra Backend
emoji: ""
colorFrom: indigo
colorTo: cyan
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Agentic AI study companion for Indian competitive exams (FastAPI).
---

# ParikshaMitra Backend on Hugging Face Spaces

This file is the README that lives at the root of the **HF Space repository**
(separate from the GitHub repo). The YAML frontmatter above is what HF reads
to configure the Space - it must stay at the very top.

The Space runs the FastAPI app from `backend/Dockerfile` (Python 3.11 slim,
non-root user, listens on `$PORT` which HF sets to `7860`).

## Free tier resources

- **Docker SDK, free hardware**: 16 GB RAM, 2 vCPU, 50 GB ephemeral disk
- **No sleep** for Docker Spaces (unlike Streamlit/Gradio, which idle after 48h)
- Build minutes are uncapped on free tier as of 2026-Q1

## One-time setup

1. Create a free HF account and a User Access Token with **write** scope at
   <https://huggingface.co/settings/tokens>.
2. Install the CLI in any Python env:
   ```bash
   pip install -U "huggingface_hub[cli]"
   ```

## Three-step push

From the `backend/` directory:

```bash
# 1. Authenticate (paste the token from step 1 above)
huggingface-cli login

# 2. Create the Space (only needed the first time)
huggingface-cli repo create parikshamitra-backend \
    --type space \
    --space_sdk docker

# 3. Push. HF expects a flat repo where the Dockerfile sits at the root,
#    so we copy this file in as README.md and push the backend/ tree only.
git init
git remote add space https://huggingface.co/spaces/<your-username>/parikshamitra-backend
cp HUGGINGFACE_SPACE_README.md README.md
git add Dockerfile .dockerignore requirements.txt app/ README.md
git commit -m "Deploy ParikshaMitra backend"
git push -u space main
```

After the push, HF will build the Docker image (~3-5 min) and the Space will be
live at `https://<your-username>-parikshamitra-backend.hf.space`. Hit
`/healthz` to verify.

## Environment variables to set in the Space settings

Open Space -> Settings -> Variables and Secrets and add:

| Name | Type | Value |
|---|---|---|
| `CORS_ORIGINS` | Variable | `https://<your-app>.vercel.app,https://<your-app>-*.vercel.app` |
| `DATABASE_URL` | Secret | `libsql://<db>-<org>.turso.io?authToken=<turso-token>` |
| `DEFAULT_GEMINI_API_KEY` | Secret | *(optional; leave blank to enforce BYOK)* |
| `DEFAULT_GROQ_API_KEY` | Secret | *(optional)* |
| `DEBUG` | Variable | `false` |

The Space restarts automatically when secrets change. BYOK headers
(`X-Gemini-Key`, `X-Groq-Key`) from the Vercel frontend take precedence
over any server-side defaults.

## Provisioning Turso (free libSQL cloud)

```bash
# install the Turso CLI (one-liner from https://docs.turso.tech)
curl -sSfL https://get.tur.so/install.sh | bash

turso auth login
turso db create parikshamitra
turso db show parikshamitra --url        # -> libsql://...turso.io
turso db tokens create parikshamitra     # -> long token string
```

Concatenate them into a single connection string and paste it as the
`DATABASE_URL` secret above:

```
libsql://parikshamitra-<org>.turso.io?authToken=<token>
```

The backend's `app/db/session.py` detects this URL prefix automatically and
loads the `sqlalchemy-libsql` async dialect. Local development (without
`DATABASE_URL` set) keeps using `sqlite+aiosqlite:///parikshamitra.db`.

## Updating the deployed Space

Subsequent deploys are just `git push space main` from `backend/`. HF
rebuilds the image only when files that affect the build (Dockerfile,
requirements, source) actually change.

## Troubleshooting

- **Build fails on `libsql-experimental`**: confirm the base image is
  `python:3.11-slim`. The package only ships wheels for cp311-cp313 manylinux.
- **CORS blocked from Vercel**: re-check `CORS_ORIGINS` includes both your
  production domain and the `https://*.vercel.app` preview pattern.
- **DB writes lost between requests**: that means you forgot to set
  `DATABASE_URL`. The default SQLite file lives on the ephemeral container
  disk and is wiped on every restart.
