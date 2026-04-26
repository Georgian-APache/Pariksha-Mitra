# ParikshaMitra backend - Hugging Face Spaces Docker SDK image.
#
# Pinned to Python 3.11-slim because:
#   1. HF Spaces base images and most pre-built wheels (incl. libsql-experimental,
#      chromadb, numpy) ship cp311 manylinux artefacts.
#   2. requirements.txt uses ">=" so 3.11 resolves all upper bounds cleanly.
#
# HF Spaces convention: app must listen on $PORT (default 7860) on 0.0.0.0.

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=7860

WORKDIR /app

# Build essentials: needed for any source-only deps (pypdf, greenlet fallbacks,
# chromadb's tokenizers if a manylinux wheel is missing). Removed after install
# in a single layer to keep the image small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better layer caching).
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy application source.
COPY app ./app

# HF Spaces runs the container as UID 1000 (user "user"). Mirror that locally so
# permission bits match and the container also works on plain Docker.
RUN useradd --create-home --uid 1000 user \
    && chown -R user:user /app
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=/app

EXPOSE 7860

# Default command. ${PORT:-7860} lets HF Spaces (or any platform) override.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
