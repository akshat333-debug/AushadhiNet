"""Pub/Sub push endpoint for the ingest worker (cloud mode). Cloud Run only
gets CPU while serving a request, so a long-lived pull subscriber is not
reliable there; Pub/Sub pushes each message here instead, signed with a
Google OIDC token for a dedicated service account.
"""
from __future__ import annotations

import base64
import json
import logging

from fastapi import APIRouter, Header, HTTPException, Request, Response

from backend.config import get_settings

router = APIRouter(prefix="/internal/pubsub", tags=["internal"])
log = logging.getLogger(__name__)


def _verify_push_token(authorization: str | None) -> None:
    settings = get_settings()
    if "REPLACE_ME" in (settings.pubsub_push_audience, settings.pubsub_push_service_account):
        raise HTTPException(503, "Pub/Sub push is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing push token")
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token
    try:
        claims = id_token.verify_oauth2_token(
            authorization[len("Bearer "):], google_requests.Request(), audience=settings.pubsub_push_audience,
        )
    except ValueError as exc:
        raise HTTPException(401, "invalid push token") from exc
    if claims.get("email") != settings.pubsub_push_service_account or not claims.get("email_verified"):
        raise HTTPException(403, "push token is not from the configured service account")


@router.post("/ingest")
async def pubsub_ingest(request: Request, authorization: str | None = Header(default=None)) -> Response:
    if get_settings().mode != "cloud":
        raise HTTPException(404, "cloud mode only")
    _verify_push_token(authorization)
    try:
        envelope = await request.json()
        payload = json.loads(base64.b64decode(envelope["message"]["data"]))
    except (ValueError, KeyError, TypeError):
        log.warning("dropping malformed Pub/Sub push envelope")
        return Response(status_code=204)  # ack: redelivering a malformed message can never succeed
    from backend.runtime import handle_inbound
    handle_inbound(payload)  # an exception here returns 500, so Pub/Sub retries with backoff
    return Response(status_code=204)
