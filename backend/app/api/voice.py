import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.voice import PrepareExpenseRequest, PrepareExpenseUpdateRequest
from app.services.voice_service import PendingActionStore, VoiceService

router = APIRouter(prefix="/voice", tags=["voice"])
pending_actions = PendingActionStore()


def service(db: Session) -> VoiceService:
    return VoiceService(db, pending_actions)


@router.get("/token")
def voice_token():
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
def voice_summary(db: Session = Depends(get_db)):
    return service(db).summary()


@router.post("/tools/prepare-expense")
def prepare_expense(payload: PrepareExpenseRequest, db: Session = Depends(get_db)):
    return service(db).prepare_expense(payload)


@router.post("/tools/prepare-update")
def prepare_update(
    payload: PrepareExpenseUpdateRequest, db: Session = Depends(get_db)
):
    return service(db).prepare_update(payload)


@router.post("/actions/{action_id}/confirm")
def confirm_action(action_id: str, db: Session = Depends(get_db)):
    return service(db).confirm(action_id)


@router.delete("/actions/{action_id}", status_code=204)
def cancel_action(action_id: str):
    pending_actions.cancel(action_id)
    return Response(status_code=204)

