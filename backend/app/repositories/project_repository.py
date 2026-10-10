from sqlalchemy.orm import Session
from app.models import ProjectRecord, ProjectTask, TaskDependency, ProjectDocument


def list_projects(db: Session):
    return db.query(ProjectRecord).order_by(ProjectRecord.name.asc()).all()


def get_project(db: Session, project_id: str):
    return db.query(ProjectRecord).filter_by(project_id=project_id).first()


def get_tasks(db: Session, project_id: str):
    return (db.query(ProjectTask).filter_by(project_id=project_id)
            .order_by(ProjectTask.planned_date.asc(), ProjectTask.task_id.asc()).all())


def get_dependencies(db: Session, task_ids: list[str]):
    if not task_ids:
        return []
    return db.query(TaskDependency).filter(TaskDependency.task_id.in_(task_ids)).all()


def get_documents(db: Session, project_id: str):
    return (db.query(ProjectDocument).filter_by(project_id=project_id)
            .order_by(ProjectDocument.document_id.asc()).all())
