from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import ProjectDocument, ProjectRecord
from app.retrieval.rag_service import ingest_document, reindex_project_documents, retrieve_evidence

router = APIRouter(prefix="/api/projects/{project_id}/documents", tags=["documents-rag"])


class IngestDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    source: str = Field(min_length=1, max_length=255, description="For example: email:vendor-update-001 or upload:status-report.txt")
    content: str = Field(min_length=20, max_length=100000)
    related_task_id: str | None = Field(default=None, max_length=64)
    is_synthetic: bool = True


class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)


def _require_project(db: Session, project_id: str):
    if not db.query(ProjectRecord).filter(ProjectRecord.project_id == project_id).first():
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("")
def list_documents(project_id: str, db: Session = Depends(get_db)):
    _require_project(db, project_id)
    docs = db.query(ProjectDocument).filter(ProjectDocument.project_id == project_id).order_by(ProjectDocument.title.asc()).all()
    return {"project_id": project_id, "count": len(docs), "documents": [
        {"document_id": d.document_id, "title": d.title, "source": d.source,
         "related_task_id": d.related_task_id, "is_synthetic": d.is_synthetic}
        for d in docs
    ]}


@router.post("/ingest")
def ingest(project_id: str, request: IngestDocumentRequest, db: Session = Depends(get_db)):
    _require_project(db, project_id)
    if request.related_task_id:
        from app.models import ProjectTask
        task = db.query(ProjectTask).filter(ProjectTask.project_id == project_id, ProjectTask.task_id == request.related_task_id).first()
        if not task:
            raise HTTPException(status_code=422, detail="related_task_id does not belong to this project")
    try:
        return ingest_document(db, project_id, request.title, request.source, request.content,
                               request.related_task_id, request.is_synthetic)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        print(f"Document ingestion failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="Document ingestion failed; check backend logs") from exc


@router.post("/reindex")
def reindex(project_id: str, db: Session = Depends(get_db)):
    _require_project(db, project_id)
    try:
        return reindex_project_documents(db, project_id)
    except Exception as exc:
        db.rollback()
        print(f"Document reindex failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="Document reindex failed; check backend logs") from exc


@router.post("/search")
def search(project_id: str, request: SearchRequest, db: Session = Depends(get_db)):
    _require_project(db, project_id)
    return {"project_id": project_id, "query": request.query, **retrieve_evidence(db, project_id, request.query, request.top_k)}
