import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.auth import current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.voice import (
    PrepareExpenseRequest,
    PrepareExpenseUpdateRequest,
    SearchExpensesRequest,
)
from app.services.voice_service import PendingActionStore, VoiceService

router = APIRouter(prefix="/voice", tags=["voice"])
pending_actions = PendingActionStore()


def service(db: Session, user: User) -> VoiceService:
    return VoiceService(db, pending_actions, user)


@router.get("/token")
def voice_token(_user: User = Depends(current_user)):
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise HTTPException(503, "AssemblyAI is not configured")
    try:
        response = httpx.get(
            "https://agents.assemblyai.com/v1/token",
            params={"expires_in_seconds": 60, "max_session_duration_seconds": 900},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Unable to create AssemblyAI session token") from exc
    return {
        "token": response.json()["token"],
        "agent_id": os.getenv("ASSEMBLYAI_AGENT_ID"),
    }


@router.post("/tools/summary")
def voice_summary(
    db: Session = Depends(get_db), user: User = Depends(current_user)
):
    return service(db, user).summary()


@router.post("/tools/categories")
def voice_categories(
    db: Session = Depends(get_db), user: User = Depends(current_user)
):
    return service(db, user).categories()


@router.post("/tools/search-expenses")
def search_expenses(
    payload: SearchExpensesRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return service(db, user).search_expenses(payload)


@router.post("/tools/prepare-expense")
def prepare_expense(
    payload: PrepareExpenseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return service(db, user).prepare_expense(payload)


@router.post("/tools/prepare-update")
def prepare_update(
    payload: PrepareExpenseUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return service(db, user).prepare_update(payload)


@router.post("/actions/{action_id}/confirm")
def confirm_action(
    action_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return service(db, user).confirm(action_id)


@router.delete("/actions/{action_id}", status_code=204)
def cancel_action(action_id: str, user: User = Depends(current_user)):
    pending_actions.cancel(action_id, user.id)
    return Response(status_code=204)
