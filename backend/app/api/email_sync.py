"""Project-scoped Microsoft 365 connection and scheduled-sync endpoints."""
import json
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import EmailOAuthState, EmailSyncConnection, ProjectRecord
from app.email_sync.microsoft_graph import (
    DEFAULT_INTERVAL_MINUTES, complete_auth_flow, create_auth_flow, sync_project_emails,
)

router = APIRouter(tags=["microsoft-365-email-sync"])


class SyncConfigRequest(BaseModel):
    keywords: list[str] = Field(min_length=1, max_length=30, description="Project-specific phrases; only emails matching one are ingested")
    interval_minutes: int = Field(default=DEFAULT_INTERVAL_MINUTES, ge=15, le=1440)
    enabled: bool = True


def _project(db: Session, project_id: str) -> None:
    if not db.query(ProjectRecord).filter(ProjectRecord.project_id == project_id).first():
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("/api/projects/{project_id}/email-sync/status")
def email_sync_status(project_id: str, db: Session = Depends(get_db)):
    _project(db, project_id)
    c = db.query(EmailSyncConnection).filter(EmailSyncConnection.project_id == project_id).first()
    if not c:
        return {"project_id": project_id, "provider": "microsoft_graph", "connected": False,
                "sync_enabled": False, "configured": False, "message": "Connect Microsoft 365 to get started."}
    keywords = json.loads(c.keywords_json or "[]")
    return {"project_id": project_id, "provider": c.provider, "connected": True,
            "connected_email": c.connected_email, "sync_enabled": bool(c.sync_enabled),
            "configured": bool(keywords), "keywords": keywords,
            "interval_minutes": c.interval_minutes, "last_sync_at": c.last_sync_at,
            "last_attempt_at": c.last_attempt_at, "last_success_at": c.last_success_at, "last_sync_status": c.last_sync_status,
            "last_sync_error": c.last_sync_error}


@router.post("/api/projects/{project_id}/email-sync/connect")
def connect_microsoft(project_id: str, db: Session = Depends(get_db)):
    _project(db, project_id)
    try:
        state, authorization_url, flow = create_auth_flow(project_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    db.query(EmailOAuthState).filter(EmailOAuthState.project_id == project_id).delete(synchronize_session=False)
    db.add(EmailOAuthState(state=state, project_id=project_id, flow_json=json.dumps(flow),
                           expires_at=datetime.utcnow() + timedelta(minutes=10)))
    db.commit()
    return {"project_id": project_id, "provider": "Microsoft Outlook / Microsoft 365",
            "authorization_url": authorization_url,
            "instructions": "Open authorization_url in your browser and sign in. Relay requests read-only Mail.Read access.",
            "expires_in_minutes": 10}


@router.get("/api/email/microsoft/callback")
def microsoft_callback(request: Request, state: str = Query(...), db: Session = Depends(get_db)):
    try:
        project_id, email = complete_auth_flow(db, state, dict(request.query_params))
        return {"status": "connected", "project_id": project_id, "mailbox": email,
                "next_step": f"Configure project keywords at POST /api/projects/{project_id}/email-sync/config before enabling scheduled sync."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Microsoft OAuth callback failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail="Microsoft sign-in failed. Check backend logs and Entra app settings.") from exc


@router.post("/api/projects/{project_id}/email-sync/config")
def configure_email_sync(project_id: str, request: SyncConfigRequest, db: Session = Depends(get_db)):
    _project(db, project_id)
    c = db.query(EmailSyncConnection).filter(EmailSyncConnection.project_id == project_id).first()
    if not c:
        raise HTTPException(status_code=409, detail="Connect Microsoft 365 before configuring sync.")
    cleaned = list(dict.fromkeys(" ".join(k.strip().split()) for k in request.keywords if k.strip()))
    if not cleaned:
        raise HTTPException(status_code=422, detail="At least one non-empty keyword is required. Sync remains disabled.")
    c.keywords_json = json.dumps(cleaned, ensure_ascii=False)
    c.interval_minutes = request.interval_minutes
    c.sync_enabled = request.enabled
    c.last_sync_status = "configured" if request.enabled else "disabled"
    c.last_sync_error = None
    db.commit()
    return {"project_id": project_id, "configured": True, "sync_enabled": bool(c.sync_enabled),
            "keywords": cleaned, "interval_minutes": c.interval_minutes,
            "message": "Scheduled read-only inbox sync configured. Emails are ingested only when subject/body matches a configured keyword."}


@router.post("/api/projects/{project_id}/email-sync/run")
def run_email_sync_now(project_id: str, db: Session = Depends(get_db)):
    _project(db, project_id)
    try:
        return sync_project_emails(db, project_id, force=True)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Outlook sync failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail="Outlook sync failed. Check status and backend logs.") from exc


@router.post("/api/projects/{project_id}/email-sync/disable")
def disable_email_sync(project_id: str, db: Session = Depends(get_db)):
    _project(db, project_id)
    c = db.query(EmailSyncConnection).filter(EmailSyncConnection.project_id == project_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Outlook is not connected for this project.")
    c.sync_enabled = False
    c.last_sync_status = "disabled"
    db.commit()
    return {"project_id": project_id, "sync_enabled": False, "message": "Scheduled sync disabled. Existing indexed documents were not deleted."}
