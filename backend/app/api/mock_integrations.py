"""Runtime demo connectors for Jira and Confluence.

These endpoints intentionally return synthetic records; they do not call Atlassian.
They demonstrate the connector -> normalization -> MySQL/RAG ingestion workflow.
"""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ProjectRecord, ProjectTask
from app.retrieval.rag_service import ingest_document

router = APIRouter(prefix="/api/projects/{project_id}/integrations/mock", tags=["mock-integrations"])


class SyncRequest(BaseModel):
    record_ids: list[str] | None = Field(default=None, description="Optional record IDs to ingest; omit to ingest all returned demo records.")


def _project(db: Session, project_id: str):
    project = db.query(ProjectRecord).filter(ProjectRecord.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _records(db: Session, project_id: str, source: Literal["jira", "confluence"]):
    project = _project(db, project_id)
    tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project_id).order_by(ProjectTask.task_id.asc()).all()
    if source == "jira":
        records = []
        for index, task in enumerate(tasks, start=1):
            key = f"DEMO-{project_id}-{index:03d}"
            content = (
                f"Jira issue {key}: {task.name}. Project: {project.name} ({project_id}). "
                f"Status: {task.status}. Owner: {task.owner}. Planned date: {task.planned_date}. "
                f"Forecast date: {task.forecast_date}. This is synthetic demonstration data. "
                f"Investigate delays, blockers, dependencies and delivery impact before taking action."
            )
            records.append({
                "record_id": key, "record_type": "jira_issue", "title": task.name,
                "status": task.status, "assignee": task.owner, "related_task_id": task.task_id,
                "content": content, "url": f"mock://jira/browse/{key}", "is_synthetic": True,
            })
        if not records:
            records.append({
                "record_id": f"DEMO-{project_id}-001", "record_type": "jira_issue",
                "title": f"{project.name} delivery tracking", "status": project.status,
                "assignee": "Unassigned", "related_task_id": None,
                "content": f"Synthetic Jira issue for {project.name} ({project_id}). Project status: {project.status}; risk score: {project.risk_score}.",
                "url": f"mock://jira/browse/DEMO-{project_id}-001", "is_synthetic": True,
            })
        return records

    tasks_text = "\\n".join(
        f"- {task.task_id}: {task.name}; status={task.status}; owner={task.owner}; planned={task.planned_date}; forecast={task.forecast_date}"
        for task in tasks
    ) or "- No tasks are currently recorded."
    first_task_id = tasks[0].task_id if tasks else None
    return [
        {
            "record_id": f"CONF-{project_id}-OVERVIEW", "record_type": "confluence_page",
            "title": f"{project.name} — Delivery overview", "status": project.status,
            "assignee": None, "related_task_id": None,
            "content": f"Confluence demo page: {project.name} ({project_id}) delivery overview. Project status: {project.status}. Risk score: {project.risk_score}/100. Planned release: {project.planned_release}. Task register:\\n{tasks_text}\\nThis is synthetic demonstration content, not a real Confluence page.",
            "url": f"mock://confluence/pages/CONF-{project_id}-OVERVIEW", "is_synthetic": True,
        },
        {
            "record_id": f"CONF-{project_id}-RISKS", "record_type": "confluence_page",
            "title": f"{project.name} — Risks and decisions", "status": "Current",
            "assignee": None, "related_task_id": first_task_id,
            "content": f"Confluence demo page: risks and decisions for {project.name} ({project_id}). Review delayed tasks, dependencies, vendor commitments, acceptance criteria, and release readiness. Current project risk score is {project.risk_score}/100 and planned release is {project.planned_release}. Confirm assumptions with owners before treating this synthetic page as an authoritative decision record.",
            "url": f"mock://confluence/pages/CONF-{project_id}-RISKS", "is_synthetic": True,
        },
    ]


@router.get("/{source}/records")
def list_mock_records(project_id: str, source: Literal["jira", "confluence"], db: Session = Depends(get_db)):
    records = _records(db, project_id, source)
    return {
        "project_id": project_id,
        "source": source,
        "connector_mode": "synthetic_demo",
        "count": len(records),
        "records": [{key: value for key, value in record.items() if key != "content"} | {"content_preview": record["content"][:280]} for record in records],
    }


@router.post("/{source}/sync")
def sync_mock_records(project_id: str, source: Literal["jira", "confluence"], request: SyncRequest | None = None, db: Session = Depends(get_db)):
    records = _records(db, project_id, source)
    selected_ids = set(request.record_ids) if request and request.record_ids is not None else None
    if selected_ids is not None:
        unknown = selected_ids - {record["record_id"] for record in records}
        if unknown:
            raise HTTPException(status_code=422, detail=f"Unknown record IDs for {source}: {', '.join(sorted(unknown))}")
        records = [record for record in records if record["record_id"] in selected_ids]
    ingested = []
    try:
        for record in records:
            result = ingest_document(
                db=db,
                project_id=project_id,
                title=record["title"],
                source=f"mock-{source}:{record['record_id']}",
                content=record["content"],
                related_task_id=record["related_task_id"],
                is_synthetic=True,
            )
            ingested.append({
                "record_id": record["record_id"],
                "document_id": result["document_id"],
                "title": result["title"],
                "created": result["created"],
                "chunks_indexed": result["chunks_indexed"],
            })
    except Exception as exc:
        db.rollback()
        print(f"Mock {source} sync failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail=f"Mock {source} sync failed; check backend logs") from exc
    return {
        "project_id": project_id, "source": source, "connector_mode": "synthetic_demo",
        "records_fetched": len(records),
        "documents_created": sum(1 for item in ingested if item["created"]),
        "already_present": sum(1 for item in ingested if not item["created"]),
        "chunks_indexed": sum(item["chunks_indexed"] for item in ingested),
        "records": ingested,
        "message": f"Fetched {len(records)} synthetic {source} records and indexed them for RAG.",
    }
