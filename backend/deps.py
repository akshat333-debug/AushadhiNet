"""Auth dependencies (modular-plan.md §2.3): role- and jurisdiction-based
access control. In cloud mode, a Firebase Auth ID token's custom claims
carry role and jurisdiction; in local mode, a plain `dev:<uid>:<role>:
<jurisdiction>` bearer token stands in (never accepted in cloud mode).
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException

from backend.config import get_settings


@dataclass
class AuthUser:
    uid: str
    role: str          # "facility" | "block" | "district" | "state" | "public"
    jurisdiction: str  # e.g. "mh/nashik", "mh", or "national"


def _decode_local_dev_token(token: str) -> AuthUser:
    parts = token.split(":")
    if len(parts) != 4 or parts[0] != "dev":
        raise HTTPException(401, "malformed local dev token (expected dev:<uid>:<role>:<jurisdiction>)")
    _, uid, role, jurisdiction = parts
    return AuthUser(uid=uid, role=role, jurisdiction=jurisdiction)


def _decode_firebase_token(token: str) -> AuthUser:
    from firebase_admin import auth as fb_auth

    decoded = fb_auth.verify_id_token(token)
    return AuthUser(
        uid=decoded["uid"], role=decoded.get("role", "facility"),
        jurisdiction=decoded.get("jurisdiction", ""),
    )


def _authenticate(authorization: str | None) -> AuthUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    token = authorization[len("Bearer "):]
    settings = get_settings()
    if settings.mode == "cloud":
        return _decode_firebase_token(token)
    return _decode_local_dev_token(token)


def require_role(*allowed_roles: str):
    """FastAPI dependency factory: `Depends(require_role("district", "state"))`."""
    def dependency(authorization: str | None = Header(default=None)) -> AuthUser:
        user = _authenticate(authorization)
        if user.role not in allowed_roles:
            raise HTTPException(403, f"role '{user.role}' not permitted; requires one of {allowed_roles}")
        return user
    return dependency


def check_jurisdiction(user: AuthUser, resource_jurisdiction: str) -> None:
    """A user's jurisdiction "mh" covers "mh/nashik"; "national" (state-
    level national admin) covers everything. Raises 403 if not covered."""
    if user.jurisdiction == "national":
        return
    if resource_jurisdiction == user.jurisdiction or resource_jurisdiction.startswith(f"{user.jurisdiction}/"):
        return
    raise HTTPException(403, f"user jurisdiction '{user.jurisdiction}' does not cover '{resource_jurisdiction}'")
