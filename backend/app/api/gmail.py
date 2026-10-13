"""Gmail OAuth and scheduled ingestion endpoints. No frontend changes required."""
import json
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import GMAIL_CONNECTOR_ENABLED
from app.models import GmailConnection, GmailOAuthState, GmailSyncConfig, ProjectRecord
from app.services.gmail_sync import create_flow, encrypt_credentials, load_client_config, sync_project

router = APIRouter(tags=["gmail-email-sync"])


def _ensure_gmail_enabled():
    if not GMAIL_CONNECTOR_ENABLED:
        raise HTTPException(status_code=403, detail="Gmail is disabled in the public demo. Enable it only on a private deployment.")


class GmailConfigRequest(BaseModel):
    keywords: list[str] = Field(min_length=1, max_length=20)
    interval_minutes: int = Field(default=15, ge=15, le=1440)
    enabled: bool = False


def _require_project(db: Session, project_id: str):
    if not db.query(ProjectRecord).filter(ProjectRecord.project_id == project_id).first():
        raise HTTPException(status_code=404, detail="Project not found")


@router.post("/api/projects/{project_id}/email-sync/gmail/connect")
def gmail_connect(project_id: str, db: Session = Depends(get_db)):
    _ensure_gmail_enabled()
    _require_project(db, project_id)
    try:
        load_client_config()
        state = secrets.token_urlsafe(32)
        state_row = GmailOAuthState(
            state=state,
            project_id=project_id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        db.add(state_row)
        db.commit()
        flow = create_flow(state)
        auth_url, _ = flow.authorization_url(
            access_type="offline", include_granted_scopes="true", prompt="consent"
        )
        # PKCE verifier must survive the redirect and be restored in the callback.
        state_row.code_verifier = flow.code_verifier
        db.commit()
        return {"project_id": project_id, "authorization_url": auth_url,
                "redirect_uri": flow.redirect_uri, "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
                "instructions": "Open authorization_url in a browser, sign in to Gmail, and approve read-only access."}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Could not start Gmail OAuth: {type(exc).__name__}: {exc}") from exc


@router.get("/api/email/gmail/callback")
def gmail_callback(code: str | None = None, state: str | None = None,
                   error: str | None = None, db: Session = Depends(get_db)):
    _ensure_gmail_enabled()
    if error:
        raise HTTPException(status_code=400, detail=f"Google authorization was not completed: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth code or state")
    state_row = db.query(GmailOAuthState).filter(GmailOAuthState.state == state).first()
    if not state_row:
        raise HTTPException(status_code=400, detail="OAuth state is invalid or already used. Start connect again.")
    expiry = state_row.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry < datetime.now(timezone.utc):
        db.delete(state_row)
        db.commit()
        raise HTTPException(status_code=400, detail="OAuth state expired. Start connect again.")
    project_id = state_row.project_id
    try:
        if not state_row.code_verifier:
            raise RuntimeError("PKCE verifier is missing. Start a new Gmail connect flow and use its fresh authorization URL.")
        flow = create_flow(state, code_verifier=state_row.code_verifier)
        flow.fetch_token(code=code)
        credentials = flow.credentials
        from googleapiclient.discovery import build
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        profile = service.users().getProfile(userId="me").execute()
        connection = db.query(GmailConnection).filter(GmailConnection.project_id == project_id).first()
        if connection is None:
            connection = GmailConnection(project_id=project_id, encrypted_credentials=encrypt_credentials(credentials))
            db.add(connection)
        connection.email_address = profile.get("emailAddress")
        connection.encrypted_credentials = encrypt_credentials(credentials)
        config = db.query(GmailSyncConfig).filter(GmailSyncConfig.project_id == project_id).first()
        if config is None:
            db.add(GmailSyncConfig(project_id=project_id, keywords_json="[]", interval_minutes=15, enabled=False))
        db.delete(state_row)
        db.commit()
        return {"status": "connected", "project_id": project_id, "email_address": connection.email_address,
                "next_step": f"Configure keywords with POST /api/projects/{project_id}/email-sync/gmail/config, then run a test sync."}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Gmail authorization callback failed: {type(exc).__name__}: {exc}") from exc


@router.post("/api/projects/{project_id}/email-sync/gmail/config")
def configure_gmail(project_id: str, request: GmailConfigRequest, db: Session = Depends(get_db)):
    _ensure_gmail_enabled()
    _require_project(db, project_id)
    if not db.query(GmailConnection).filter(GmailConnection.project_id == project_id).first():
        raise HTTPException(status_code=409, detail="Connect Gmail before configuring sync")
    keywords = [k.strip()[:100] for k in request.keywords if k and k.strip()]
    if not keywords:
        raise HTTPException(status_code=422, detail="At least one non-empty keyword is required")
    config = db.query(GmailSyncConfig).filter(GmailSyncConfig.project_id == project_id).first()
    if config is None:
        config = GmailSyncConfig(project_id=project_id)
        db.add(config)
    config.keywords_json = json.dumps(keywords)
    config.interval_minutes = request.interval_minutes
    config.enabled = request.enabled
    config.last_error = None
    db.commit()
    return {"project_id": project_id, "keywords": keywords, "interval_minutes": config.interval_minutes,
            "enabled": config.enabled, "message": "Configuration saved. Scheduled sync runs while Relay backend is running."}


@router.post("/api/projects/{project_id}/email-sync/gmail/run")
def run_gmail_sync(project_id: str, db: Session = Depends(get_db)):
    _ensure_gmail_enabled()
    _require_project(db, project_id)
    try:
        return sync_project(db, project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        print(f"Gmail sync failed for {project_id}: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail=f"Gmail sync failed: {type(exc).__name__}: {str(exc)[:300]}") from exc


@router.get("/api/projects/{project_id}/email-sync/gmail/status")
def gmail_status(project_id: str, db: Session = Depends(get_db)):
    if not GMAIL_CONNECTOR_ENABLED:
        return {
            "project_id": project_id, "connected": False, "email_address": None,
            "enabled": False, "keywords": [], "interval_minutes": 15,
            "last_sync_at": None, "last_error": None, "disabled": True,
            "message": "Gmail is disabled in the public demo. Enable it only on a private deployment.",
        }
    _require_project(db, project_id)
    connection = db.query(GmailConnection).filter(GmailConnection.project_id == project_id).first()
    config = db.query(GmailSyncConfig).filter(GmailSyncConfig.project_id == project_id).first()
    return {"project_id": project_id, "connected": bool(connection),
            "email_address": connection.email_address if connection else None,
            "enabled": config.enabled if config else False,
            "keywords": json.loads(config.keywords_json or "[]") if config else [],
            "interval_minutes": config.interval_minutes if config else 15,
            "last_sync_at": config.last_sync_at.isoformat() if config and config.last_sync_at else None,
            "last_error": config.last_error if config else None}


@router.delete("/api/projects/{project_id}/email-sync/gmail/disconnect")
def gmail_disconnect(project_id: str, db: Session = Depends(get_db)):
    _ensure_gmail_enabled()
    _require_project(db, project_id)
    connection = db.query(GmailConnection).filter(GmailConnection.project_id == project_id).first()
    config = db.query(GmailSyncConfig).filter(GmailSyncConfig.project_id == project_id).first()
    if connection:
        db.delete(connection)
    if config:
        config.enabled = False
        config.last_error = None
    db.commit()
    return {"project_id": project_id, "connected": False, "scheduled_sync_enabled": False}
