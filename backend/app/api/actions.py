from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.action import ActionCreate, ActionApproval, ActionVerification
from app.services import action_service as service

router = APIRouter(prefix="/api/projects/{project_id}/actions", tags=["recovery actions"])

@router.get("")
def list_actions(project_id: str, db: Session = Depends(get_db)):
    return service.list_actions(db, project_id)

@router.post("")
def create_action(project_id: str, request: ActionCreate, db: Session = Depends(get_db)):
    return service.create_action(db, project_id, request.title, request.description)

@router.post("/{action_id}/approve")
def approve_action(project_id: str, action_id: str, request: ActionApproval, db: Session = Depends(get_db)):
    return service.approve_action(db, project_id, action_id, request.approved_by)

@router.post("/{action_id}/execute")
def execute_action(project_id: str, action_id: str, db: Session = Depends(get_db)):
    return service.execute_action(db, project_id, action_id)

@router.post("/{action_id}/verify")
def verify_action(project_id: str, action_id: str, request: ActionVerification, db: Session = Depends(get_db)):
    return service.verify_action(db, project_id, action_id, request.verified_by)

@router.get("/{action_id}/audit")
def list_action_audit(project_id: str, action_id: str, db: Session = Depends(get_db)):
    return service.list_audit(db, project_id, action_id)
