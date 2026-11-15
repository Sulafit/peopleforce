from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from dishka import Provider, make_async_container
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from peopleforce.core.config import Settings, get_settings
from peopleforce.core.errors import install_error_handlers
from peopleforce.core.logging import configure_logging
from peopleforce.di.providers import InfrastructureProvider, RequestProvider
from peopleforce.modules.auth.api import router as auth_router
from peopleforce.modules.freelancer.api import router as assets_router
from peopleforce.modules.gamification.api import router as gamification_router
from peopleforce.modules.onboarding.api import router as onboarding_router
from peopleforce.modules.progression.api import router as progression_router

log = structlog.get_logger()
API_PREFIX = "/api/v1"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def create_app(settings: Settings | None = None, overrides: list[Provider] | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json_logs=settings.is_production)

    container = make_async_container(
        InfrastructureProvider(settings), RequestProvider(), FastapiProvider(), *(overrides or [])
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await container.close()

    app = FastAPI(
        title="PeopleForce API",
        version="0.1.0",
        docs_url=f"{API_PREFIX}/docs",
        openapi_url=f"{API_PREFIX}/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )
    install_error_handlers(app)

    @app.middleware("http")
    async def same_origin_guard(request: Request, call_next):
        """CSRF defence in depth (cookies are also SameSite=Lax): browsers send Origin on unsafe requests,
        and it must be our own public origin."""
        origin = request.headers.get("origin")
        if request.method in UNSAFE_METHODS and origin and origin.rstrip("/") not in settings.allowed_origins:
            log.warning("origin_rejected", origin=origin, path=request.url.path)
            return JSONResponse(
                {
                    "error": {
                        "code": "forbidden_origin",
                        "message": "Request origin not allowed.",
                        "details": {},
                    }
                },
                status_code=403,
            )
        response = await call_next(request)
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    system = APIRouter(tags=["system"])

    @system.get("/health")
    async def health() -> JSONResponse:
        """Liveness plus a database round trip. Used by Docker and Dokploy health checks."""
        try:
            engine = await container.get(AsyncEngine)
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception as exc:
            log.error("health_check_failed", error=str(exc))
            return JSONResponse({"status": "degraded", "database": "down"}, status_code=503)
        return JSONResponse({"status": "ok", "database": "up"})

    for router in (
        system,
        auth_router,
        onboarding_router,
        progression_router,
        assets_router,
        gamification_router,
    ):
        app.include_router(router, prefix=API_PREFIX)

    setup_dishka(container, app)
    return app


def app_factory() -> FastAPI:
    """Entry point for `uvicorn peopleforce.main:app_factory --factory`."""
    return create_app()
