"""Application factory — creates a FastAPI app bound to given settings."""
from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import create_router
from app.core.config import Settings, get_settings
from app.core.database import make_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    session_factory = make_session_factory(str(resolved.database_url))

    app = FastAPI(title="GenAI E2 Freshservice to Jira", version="0.1.0")
    app.state.settings = resolved
    app.state.session_factory = session_factory

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(create_router(resolved, session_factory))

    return app


def _get_app() -> FastAPI:
    """Lazy app instance for `uvicorn app.main:app`.

    Created at first import when DATABASE_URL is available in the environment.
    Tests call ``create_app(settings)`` directly and never hit this.
    """
    return create_app()


# Module-level instance for `uvicorn app.main:app`
# Only initialised when running as a server (env var DATABASE_URL must be set).
try:
    app = _get_app()
except Exception:  # noqa: BLE001
    # In test environments the env var may not be set at import time.
    # Tests import create_app directly, so this is acceptable.
    app = None  # type: ignore[assignment]
