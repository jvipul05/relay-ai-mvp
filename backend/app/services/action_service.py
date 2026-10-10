"""Transactional recovery-action lifecycle; execution remains simulated."""
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models import ActionAudit, RecoveryAction
from app.repositories import action_repository as repo


def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc_iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def action_to_dict(action):
    return {
        "id": action.action_id, "project_id": action.project_id, "title": action.title,
        "description": action.description, "status": action.status,
        "created_at": to_utc_iso(action.created_at), "approved_by": action.approved_by,
        "approved_at": to_utc_iso(action.approved_at), "execution_result": action.execution_result,
        "verified_by": action.verified_by, "verified_at": to_utc_iso(action.verified_at),
        "verification_result": action.verification_result,
    }


def _audit(db, action, event_type, actor, details=None):
    db.add(ActionAudit(action_id=action.action_id, project_id=action.project_id,
                       event_type=event_type, actor=actor, details=details, created_at=utc_now_naive()))


def _get_project_action(db, project_id, action_id):
    if not repo.project_exists(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    action = repo.get_action(db, project_id, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


def list_actions(db, project_id):
    if not repo.project_exists(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    actions = repo.list_actions(db, project_id)
    return {"count": len(actions), "actions": [action_to_dict(a) for a in actions]}


def create_action(db, project_id, title, description):
    if not repo.project_exists(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    title, description = title.strip(), description.strip()
    if not title or not description:
        raise HTTPException(status_code=400, detail="Title and description are required")
    action = RecoveryAction(action_id=f"ACT-{uuid4().hex[:12].upper()}", project_id=project_id,
                            title=title, description=description, status="pending_approval", created_at=utc_now_naive())
    try:
        db.add(action)
        db.flush()
        _audit(db, action, "created", "Demo User", "Recovery action created.")
        db.commit()
        db.refresh(action)
        return action_to_dict(action)
    except Exception:
        db.rollback()
        raise


def _transition(db, project_id, action_id, expected, event_type, actor, mutate):
    action = _get_project_action(db, project_id, action_id)
    if action.status != expected:
        raise HTTPException(status_code=409, detail=f"Action must be in '{expected}' state")
    try:
        mutate(action)
        _audit(db, action, event_type, actor, getattr(action, "execution_result", None) if event_type == "executed" else getattr(action, "verification_result", None) if event_type == "verified" else f"Action {event_type}.")
        db.commit()
        db.refresh(action)
        return action_to_dict(action)
    except Exception:
        db.rollback()
        raise


def approve_action(db, project_id, action_id, approved_by):
    actor = approved_by.strip() or "Demo User"
    def mutate(action):
        action.status, action.approved_by, action.approved_at = "approved", actor, utc_now_naive()
    return _transition(db, project_id, action_id, "pending_approval", "approved", actor, mutate)


def execute_action(db, project_id, action_id):
    actor = "Demo User"
    def mutate(action):
        action.status = "executed"
        action.execution_result = "Simulated execution completed successfully. No external system was changed."
    return _transition(db, project_id, action_id, "approved", "executed", actor, mutate)


def verify_action(db, project_id, action_id, verified_by):
    actor = verified_by.strip() or "Demo User"
    def mutate(action):
        action.status, action.verified_by, action.verified_at = "verified", actor, utc_now_naive()
        action.verification_result = "Verification passed: the simulated execution result was recorded successfully."
    return _transition(db, project_id, action_id, "executed", "verified", actor, mutate)


def list_audit(db, project_id, action_id):
    _get_project_action(db, project_id, action_id)
    events = repo.list_audit(db, project_id, action_id)
    return {"count": len(events), "events": [{
        "id": e.id, "action_id": e.action_id, "project_id": e.project_id,
        "event_type": e.event_type, "actor": e.actor, "details": e.details,
        "created_at": to_utc_iso(e.created_at),
    } for e in events]}
