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
from urllib.parse import urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _is_libsql_url(url: str) -> bool:
    """True if the URL targets a Turso / libSQL endpoint."""
    return url.startswith("libsql://") or "authToken=" in url


def _to_libsql_sqlalchemy_url(raw: str) -> str:
    """Rewrite a ``libsql://...`` URL into ``sqlite+aiolibsql://...``.

    Turso publishes connection strings like
    ``libsql://my-db-org.turso.io?authToken=eyJ...``. The
    ``sqlalchemy-libsql`` async dialect expects the SQLAlchemy scheme
    ``sqlite+aiolibsql`` and, since Turso requires HTTPS, the ``secure=true``
    query flag (the dialect uses it to pick https vs http transport).
    Any extra query params from the user are preserved.
    """
    parsed = urlparse(raw)
    # The dialect itself parses authToken etc. - we just need to ensure
    # secure=true is set so libsql_experimental connects via HTTPS.
    query_pairs = []
    seen_secure = False
    if parsed.query:
        for pair in parsed.query.split("&"):
            if not pair:
                continue
            key = pair.split("=", 1)[0]
            if key == "secure":
                seen_secure = True
            query_pairs.append(pair)
    if not seen_secure:
        query_pairs.append("secure=true")
    new_query = "&".join(query_pairs)
    return urlunparse(("sqlite+aiolibsql", parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


def _build_engine():
    """Construct the async engine, branching on the URL scheme."""
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
        sa_url = _to_libsql_sqlalchemy_url(url)
        return create_async_engine(sa_url, echo=False, future=True)
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
