"""Idempotently seed synthetic Relay demo records. Run from backend/ directory."""
from app.core.database import Base, SessionLocal, engine
from app import models  # registers all models with SQLAlchemy metadata
from app.models import ProjectRecord, ProjectTask, TaskDependency, ProjectDocument
from additional_demo_data import ADDITIONAL_PROJECTS, ADDITIONAL_TASKS, ADDITIONAL_DEPENDENCIES, ADDITIONAL_DOCUMENTS
from datetime import date

PROJECT = {
    "project_id": "PROJ-001",
    "name": "Project Alpha",
    "status": "At Risk",
    "planned_release": date(2026, 10, 20),
    "risk_score": 81,
    "is_synthetic": True,
}

TASKS = [
    {"task_id": "TASK-101", "project_id": "PROJ-001", "name": "Vendor API delivery", "status": "Delayed", "planned_date": date(2026, 10, 10), "forecast_date": date(2026, 10, 15), "owner": "External Vendor"},
    {"task_id": "TASK-102", "project_id": "PROJ-001", "name": "API integration", "status": "Blocked", "planned_date": date(2026, 10, 12), "forecast_date": date(2026, 10, 17), "owner": "Integration Team"},
    {"task_id": "TASK-103", "project_id": "PROJ-001", "name": "System testing", "status": "At Risk", "planned_date": date(2026, 10, 16), "forecast_date": date(2026, 10, 20), "owner": "QA Team"},
    {"task_id": "TASK-104", "project_id": "PROJ-001", "name": "User acceptance testing", "status": "Not Started", "planned_date": date(2026, 10, 19), "forecast_date": date(2026, 10, 23), "owner": "Business Team"},
    {"task_id": "TASK-105", "project_id": "PROJ-001", "name": "Production release", "status": "At Risk", "planned_date": date(2026, 10, 20), "forecast_date": date(2026, 10, 24), "owner": "Release Team"},
]

DEPENDENCIES = [
    {"task_id": "TASK-102", "depends_on_task_id": "TASK-101"},
    {"task_id": "TASK-103", "depends_on_task_id": "TASK-102"},
    {"task_id": "TASK-104", "depends_on_task_id": "TASK-103"},
    {"task_id": "TASK-105", "depends_on_task_id": "TASK-104"},
]

DOCUMENTS = [
    {"document_id": "DOC-001", "project_id": "PROJ-001", "title": "Vendor delivery update", "source": "Vendor email (synthetic demo data)", "content": "Vendor API delivery moved from October 10 to October 15 because the certification environment is unavailable.", "related_task_id": "TASK-101", "is_synthetic": True},
    {"document_id": "DOC-002", "project_id": "PROJ-001", "title": "Integration dependency", "source": "Project plan (synthetic demo data)", "content": "API integration cannot complete until the vendor API is available.", "related_task_id": "TASK-102", "is_synthetic": True},
    {"document_id": "DOC-003", "project_id": "PROJ-001", "title": "Testing dependency", "source": "Release plan (synthetic demo data)", "content": "System testing depends on integration; user acceptance testing and release follow testing.", "related_task_id": "TASK-103", "is_synthetic": True},
]


def main():
    # Safe bootstrap: create missing tables only. This never drops or truncates data.
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    inserted = {"projects": 0, "tasks": 0, "dependencies": 0, "documents": 0}
    try:
        projects = [PROJECT, *ADDITIONAL_PROJECTS]
        tasks = [*TASKS, *ADDITIONAL_TASKS]
        dependencies = [*DEPENDENCIES, *ADDITIONAL_DEPENDENCIES]
        documents = [*DOCUMENTS, *ADDITIONAL_DOCUMENTS]

        for values in projects:
            if db.get(ProjectRecord, values["project_id"]) is None:
                db.add(ProjectRecord(**values))
                inserted["projects"] += 1
        db.flush()

        for values in tasks:
            if db.get(ProjectTask, values["task_id"]) is None:
                db.add(ProjectTask(**values))
                inserted["tasks"] += 1
        db.flush()

        for values in dependencies:
            if db.query(TaskDependency).filter_by(**values).first() is None:
                db.add(TaskDependency(**values))
                inserted["dependencies"] += 1

        for values in documents:
            if db.get(ProjectDocument, values["document_id"]) is None:
                db.add(ProjectDocument(**values))
                inserted["documents"] += 1

        db.commit()
        print("Relay demo seed completed.")
        print("Inserted:", inserted)
        print("Existing records were preserved; no rows were deleted or overwritten.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        engine.dispose()

if __name__ == "__main__":
    main()
