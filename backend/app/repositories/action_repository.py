from sqlalchemy.orm import Session
from app.models import ActionAudit, ProjectRecord, RecoveryAction


def project_exists(db: Session, project_id: str) -> bool:
    return db.query(ProjectRecord.project_id).filter_by(project_id=project_id).first() is not None


def get_action(db: Session, project_id: str, action_id: str):
    return db.query(RecoveryAction).filter_by(project_id=project_id, action_id=action_id).first()


def list_actions(db: Session, project_id: str):
    return (db.query(RecoveryAction).filter_by(project_id=project_id)
            .order_by(RecoveryAction.created_at.desc()).all())


def list_audit(db: Session, project_id: str, action_id: str):
    return (db.query(ActionAudit).filter_by(project_id=project_id, action_id=action_id)
            .order_by(ActionAudit.created_at.asc(), ActionAudit.id.asc()).all())
