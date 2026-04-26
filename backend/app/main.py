"""FastAPI entry point for ParikshaMitra."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Agentic AI study companion for Indian competitive exams.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name}

    # Lazy import routers so each phase can ship independently
    from app.routes import (  # noqa: WPS433
        calendar as calendar_routes,
        doubt as doubt_routes,
        graph as graph_routes,
        insights as insights_routes,
        onboarding as onboarding_routes,
        plan as plan_routes,
        quiz as quiz_routes,
        rag as rag_routes,
        stream as stream_routes,
        users as user_routes,
        voice as voice_routes,
    )

    for r in (
        user_routes.router,
        onboarding_routes.router,
        plan_routes.router,
        quiz_routes.router,
        stream_routes.router,
        doubt_routes.router,
        graph_routes.router,
        rag_routes.router,
        calendar_routes.router,
        voice_routes.router,
        insights_routes.router,
    ):
        app.include_router(r)

    return app


app = create_app()
