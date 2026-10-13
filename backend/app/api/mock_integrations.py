"""Synthetic Jira and Confluence connectors for safe end-to-end testing.

The configured URLs are used only to generate clickable preview links. These routes do
not authenticate to Atlassian or fetch remote Atlassian records; all records are marked
synthetic. Stable source identities and the RAG upsert prevent duplicates on repeated syncs.
"""
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ProjectConnectorConfig, ProjectRecord, ProjectTask
from app.retrieval.rag_service import ingest_document

router = APIRouter(prefix="/api/projects/{project_id}/integrations/mock", tags=["mock-integrations"])
ConnectorName = Literal["jira", "confluence"]
DEFAULT_URLS = {
    "jira": "https://example.atlassian.net",
    "confluence": "https://example.atlassian.net/wiki",
}


class SyncRequest(BaseModel):
    record_ids: list[str] | None = Field(default=None, description="Optional record IDs to ingest; omit to ingest all preview records.")


class ConnectorConfigRequest(BaseModel):
    base_url: str = Field(min_length=8, max_length=500)


def _project(db: Session, project_id: str):
    project = db.query(ProjectRecord).filter(ProjectRecord.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _normalise_url(raw_url: str) -> str:
    value = raw_url.strip()
    try:
        parts = urlsplit(value)
        _ = parts.port  # Accessing .port also validates an invalid numeric port.
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Enter a valid HTTP or HTTPS base URL.") from exc
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        raise HTTPException(status_code=422, detail="Base URL must begin with http:// or https://.")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise HTTPException(status_code=422, detail="Base URL cannot contain credentials, query parameters, or a fragment.")
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc, path, "", "")).rstrip("/")


def _connector_url(db: Session, project_id: str, source: ConnectorName) -> str:
    config = db.query(ProjectConnectorConfig).filter_by(project_id=project_id, provider=source).first()
    return config.base_url.rstrip("/") if config else DEFAULT_URLS[source]


def _config_payload(db: Session, project_id: str) -> dict:
    return {
        provider: {
            "provider": provider,
            "base_url": _connector_url(db, project_id, provider),
            "mode": "synthetic_demo",
        }
        for provider in ("jira", "confluence")
    }


def _records(db: Session, project_id: str, source: ConnectorName):
    project = _project(db, project_id)
    tasks = (db.query(ProjectTask).filter(ProjectTask.project_id == project_id)
             .order_by(ProjectTask.task_id.asc()).all())
    base_url = _connector_url(db, project_id, source)
    if source == "jira":
        records = []
        for index, task in enumerate(tasks, start=1):
            # Keep the original sequential key for one migration pass; source identity is
            # upgraded to a stable task-based key during ingest_document().
            key = f"DEMO-{project_id}-{index:03d}"
            stable_key = f"DEMO-{project_id}-{task.task_id}"
            url = f"{base_url}/browse/{stable_key}"
            content = (
                f"Jira demo issue {stable_key}: {task.name}. Project: {project.name} ({project_id}). "
                f"Status: {task.status}. Owner: {task.owner}. Planned date: {task.planned_date}. "
                f"Forecast date: {task.forecast_date}. Preview URL: {url}. "
                "This is synthetic demonstration data, not a live Jira issue. Confirm dates and blockers before taking action."
            )
            records.append({
                "record_id": stable_key, "legacy_record_id": key, "record_type": "jira_issue",
                "title": task.name, "status": task.status, "assignee": task.owner,
                "related_task_id": task.task_id, "content": content, "url": url, "is_synthetic": True,
            })
        if not records:
            stable_key = f"DEMO-{project_id}-PROJECT"
            url = f"{base_url}/browse/{stable_key}"
            records.append({
                "record_id": stable_key, "record_type": "jira_issue", "title": f"{project.name} delivery tracking",
                "status": project.status, "assignee": "Unassigned", "related_task_id": None,
                "content": f"Synthetic Jira preview for {project.name} ({project_id}). Status: {project.status}; risk score: {project.risk_score}. Preview URL: {url}.",
                "url": url, "is_synthetic": True,
            })
        return records

    tasks_text = "\n".join(
        f"- {task.task_id}: {task.name}; status={task.status}; owner={task.owner}; planned={task.planned_date}; forecast={task.forecast_date}"
        for task in tasks
    ) or "- No tasks are currently recorded."
    first_task_id = tasks[0].task_id if tasks else None
    page_records = [
        ("OVERVIEW", f"{project.name} — Delivery overview",
         f"{project.name} ({project_id}) delivery overview. Status: {project.status}. Risk score: {project.risk_score}/100. Planned release: {project.planned_release}. Task register:\n{tasks_text}"),
        ("RISKS", f"{project.name} — Risks and decisions",
         f"Risks and decisions for {project.name} ({project_id}). Review delayed tasks, dependencies, vendor commitments, acceptance criteria, and release readiness. Current project risk score is {project.risk_score}/100 and planned release is {project.planned_release}. Confirm assumptions with owners before treating this synthetic preview as an authoritative decision record."),
    ]
    records = []
    for suffix, title, body in page_records:
        record_id = f"CONF-{project_id}-{suffix}"
        url = f"{base_url}/pages/{record_id}"
        records.append({
            "record_id": record_id, "record_type": "confluence_page", "title": title,
            "status": project.status if suffix == "OVERVIEW" else "Current",
            "assignee": None, "related_task_id": None if suffix == "OVERVIEW" else first_task_id,
            "content": f"Confluence demo page: {body}\nPreview URL: {url}. This is synthetic demonstration content, not a live Confluence page.",
            "url": url, "is_synthetic": True,
        })
    return records


@router.get("/config")
def get_connector_config(project_id: str, db: Session = Depends(get_db)):
    _project(db, project_id)
    return {"project_id": project_id, "connectors": _config_payload(db, project_id),
            "notice": "URLs control synthetic preview links only; no Atlassian API is called."}


@router.put("/config/{source}")
def save_connector_config(project_id: str, source: ConnectorName, request: ConnectorConfigRequest, db: Session = Depends(get_db)):
    _project(db, project_id)
    base_url = _normalise_url(request.base_url)
    config = db.query(ProjectConnectorConfig).filter_by(project_id=project_id, provider=source).first()
    if config is None:
        config = ProjectConnectorConfig(project_id=project_id, provider=source, base_url=base_url)
        db.add(config)
    else:
        config.base_url = base_url
    db.commit()
    return {"project_id": project_id, "provider": source, "base_url": base_url,
            "mode": "synthetic_demo", "message": "Test link saved. Records remain synthetic."}


@router.get("/{source}/records")
def list_mock_records(project_id: str, source: ConnectorName, db: Session = Depends(get_db)):
    records = _records(db, project_id, source)
    return {
        "project_id": project_id, "source": source, "connector_mode": "synthetic_demo",
        "base_url": _connector_url(db, project_id, source), "count": len(records),
        "records": [{key: value for key, value in record.items() if key != "content"}
                    | {"content_preview": record["content"][:280]} for record in records],
    }


@router.post("/{source}/sync")
def sync_mock_records(project_id: str, source: ConnectorName, request: SyncRequest | None = None,
                      db: Session = Depends(get_db)):
    records = _records(db, project_id, source)
    requested_ids = set(request.record_ids) if request and request.record_ids is not None else None
    if requested_ids is not None:
        known_ids = {record["record_id"] for record in records} | {record.get("legacy_record_id") for record in records}
        unknown = requested_ids - known_ids
        if unknown:
            raise HTTPException(status_code=422, detail=f"Unknown record IDs for {source}: {', '.join(sorted(unknown))}")
        records = [record for record in records if record["record_id"] in requested_ids or record.get("legacy_record_id") in requested_ids]

    ingested = []
    try:
        for record in records:
            result = ingest_document(
                db=db, project_id=project_id, title=record["title"],
                source=f"mock-{source}:{record['record_id']}", content=record["content"],
                related_task_id=record["related_task_id"], is_synthetic=True,
            )
            ingested.append({
                "record_id": record["record_id"], "document_id": result["document_id"],
                "title": result["title"], "created": result["created"], "updated": result.get("updated", False),
                "chunks_indexed": result["chunks_indexed"], "url": record["url"],
            })
    except Exception as exc:
        db.rollback()
        print(f"Mock {source} sync failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail=f"Mock {source} sync failed; check backend logs") from exc

    return {
        "project_id": project_id, "source": source, "connector_mode": "synthetic_demo",
        "records_fetched": len(records),
        "documents_created": sum(1 for item in ingested if item["created"]),
        "documents_updated": sum(1 for item in ingested if item["updated"]),
        "already_present": sum(1 for item in ingested if not item["created"] and not item["updated"]),
        "chunks_indexed": sum(item["chunks_indexed"] for item in ingested),
        "records": ingested,
        "message": f"Synced {len(records)} synthetic {source} records. Stable source IDs update existing documents instead of creating duplicates.",
    }
