"""FastAPI app factory, middleware, exception handlers (modular-plan.md
§2.3). Routers are included as they exist; each later step (30, 31, 33,
36...) adds one `app.include_router(...)` line here as that router is
built.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.config import get_settings
from backend.providers.base import ProviderError


def create_app() -> FastAPI:
    app = FastAPI(title="AushadhiNet API")

    # Explicit origin allow-list, never a wildcard: the Next.js frontend
    # runs on a different origin (localhost:3000) than the API
    # (localhost:8000) even in local mode, and a real cloud deployment
    # needs its actual frontend origin(s) configured via
    # CORS_ALLOWED_ORIGINS (backend/config.py) -- found and fixed during
    # the security audit, which had flagged an earlier `allow_origins=["*"]`
    # as a real gap rather than something to ship silently.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_allowed_origins_list,
        allow_methods=["*"], allow_headers=["*"],
    )

    @app.exception_handler(ProviderError)
    async def _provider_error_handler(request: Request, exc: ProviderError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def _validation_error_handler(request: Request, exc: ValidationError):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    from backend.api.webhooks_twilio import router as twilio_router
    from backend.api.webhooks_ivr import router as ivr_router
    from backend.api.simulator import router as simulator_router
    from backend.api.officer import router as officer_router
    from backend.api.public import router as public_router
    from backend.api.agent_api import router as agent_router
    app.include_router(twilio_router)
    app.include_router(ivr_router)
    app.include_router(simulator_router)
    app.include_router(officer_router)
    app.include_router(public_router)
    app.include_router(agent_router)

    return app


app = create_app()
