"""Application factory — creates a FastAPI app bound to given settings."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.routes import create_router
from app.api.routes_agile import create_agile_router
from app.api.routes_assistant import create_assistant_router
from app.core.config import Settings, get_settings
from app.core.database import make_session_factory

_SCALAR_HTML = """\
<!doctype html>
<html>
  <head>
    <title>GenAI E2 — API Docs</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
  </head>
  <body>
    <script
      id="api-reference"
      data-url="/openapi.json"
      data-configuration='{
        "theme": "purple",
        "layout": "modern",
        "defaultHttpClient": {"targetKey": "python", "clientKey": "requests"}
      }'
    ></script>
    <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
  </body>
</html>
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    session_factory = make_session_factory(str(resolved.database_url))

    # Disable built-in Swagger UI and ReDoc; we serve Scalar instead.
    app = FastAPI(
        title="GenAI E2 — Freshservice to Jira",
        version="0.1.0",
        description=(
            "Recebe tickets do Freshservice, roteia para a squad correta e cria "
            "issues no Jira com rastreabilidade completa via PostgreSQL."
        ),
        docs_url=None,
        redoc_url=None,
    )
    app.state.settings = resolved
    app.state.session_factory = session_factory

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["ops"], summary="Health check")
    def health() -> dict[str, str]:
        """Retorna `{\"status\": \"ok\"}` quando a API está operacional."""
        return {"status": "ok"}

    @app.get("/docs", include_in_schema=False)
    def scalar_docs() -> HTMLResponse:
        return HTMLResponse(_SCALAR_HTML)

    app.include_router(create_router(resolved, session_factory))
    app.include_router(create_agile_router(resolved))
    app.include_router(create_assistant_router(resolved))

    return app


def _get_app() -> FastAPI:
    return create_app()


try:
    app = _get_app()
except Exception:  # noqa: BLE001
    app = None  # type: ignore[assignment]
