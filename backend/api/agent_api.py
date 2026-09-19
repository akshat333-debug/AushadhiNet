"""Exposes the officer agent over HTTP (architecture.md §4's `POST
/agent/ask` endpoint). Requires an authenticated officer -- the agent
answers on their behalf and logs actions under their jurisdiction.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.agent.agent import AgentAnswer, OfficerCtx, ask
from backend.deps import AuthUser, require_role

router = APIRouter(prefix="/agent", tags=["agent"])


class AskRequest(BaseModel):
    question: str


@router.post("/ask")
def agent_ask(body: AskRequest, user: AuthUser = Depends(require_role("block", "district", "state"))) -> AgentAnswer:
    return ask(body.question, OfficerCtx(uid=user.uid, jurisdiction=user.jurisdiction))
