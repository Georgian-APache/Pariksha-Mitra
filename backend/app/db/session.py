"""SQLAlchemy 2.x async engine + session factory.

Supports two backends, picked from ``Settings.database_url``:

* **Local SQLite (default)** - any URL beginning with ``sqlite+aiosqlite:///``.
  This is what dev, tests, and ``parikshamitra.db`` use. Zero external deps
  beyond the existing ``aiosqlite`` package.

* **Turso / libSQL (production)** - URLs that either start with ``libsql://``
  or contain ``?authToken=`` (Turso's connection string format,
  ``libsql://<db>-<org>.turso.io?authToken=...``). These are rewritten to the
  ``sqlite+aiolibsql://`` SQLAlchemy dialect provided by the
  ``sqlalchemy-libsql`` package, which is loaded lazily only when needed.

The lazy import matters: ``sqlalchemy-libsql`` depends on
``libsql-experimental`` (a Rust extension) which only ships manylinux/macOS
wheels for cp311-cp313. On Python 3.14 (current local dev) the wheel is
unavailable and a source build needs Rust. By keeping the import inside the
libsql branch, local dev on 3.14 with the default SQLite URL works fine
without the package installed at all. ``requirements.txt`` pins
``sqlalchemy-libsql`` behind a ``python_version`` marker so the Docker image
(Python 3.11) gets it and local 3.14 quietly skips it.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _is_libsql_url(url: str) -> bool:
    """True if the URL targets a Turso / libSQL endpoint."""
    return url.startswith("libsql://") or "authToken=" in url


def _build_engine():
    """Construct the async engine, branching on the URL scheme.

    For Turso/libSQL the auth_token must be passed via connect_args (not in
    the URL query string) — that is how sqlalchemy-libsql 0.2.x reads it.
    """
    settings = get_settings()
    url = settings.database_url
    if _is_libsql_url(url):
        try:
            import sqlalchemy_libsql  # noqa: F401  (registers the dialect)
        except ImportError as exc:  # pragma: no cover - environment guard
            raise RuntimeError(
                "DATABASE_URL points at libsql/Turso but the 'sqlalchemy-libsql' "
                "package is not installed. Install it with "
                "`pip install sqlalchemy-libsql` (Python 3.11-3.13 only - 3.14 "
                "has no prebuilt libsql-experimental wheel yet)."
            ) from exc
        parsed = urlparse(url)
        # Extract authToken from query string; everything else goes on the SA URL.
        query_items = {}
        for pair in (parsed.query or "").split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                query_items[k] = v
        auth_token = query_items.pop("authToken", "")
        sa_url = f"sqlite+aiolibsql://{parsed.netloc}?secure=true"
        return create_async_engine(
            sa_url,
            echo=False,
            future=True,
            poolclass=AsyncAdaptedQueuePool,
            connect_args={"auth_token": auth_token},
        )
    return create_async_engine(url, echo=False, future=True)


engine = _build_engine()
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """Create all tables. Idempotent."""
    # Import models so they register on Base.metadata
    from app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
