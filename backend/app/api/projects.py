from datetime import date
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ProjectDocument, ProjectRecord, ProjectTask
from app.services.project_service import load_project_payload, build_investigation
from app.ai.investigation_agent import investigate_with_gemini
from app.retrieval.rag_service import retrieve_evidence
from ai_agent import normalize_language

router = APIRouter(prefix="/api/projects", tags=["projects"])

class ProjectTaskInput(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    owner: str = Field(default="Unassigned", max_length=255)
    status: str = Field(default="Planned", max_length=64)
    planned_date: date | None = None
    forecast_date: date | None = None


class ProjectCreateRequest(BaseModel):
    project_id: str | None = Field(default=None, min_length=3, max_length=64)
    name: str = Field(min_length=2, max_length=255)
    status: str = Field(default="Planning", max_length=64)
    planned_release: date
    risk_score: int = Field(default=25, ge=0, le=100)
    description: str = Field(default="", max_length=10000)
    tasks: list[ProjectTaskInput] = Field(default_factory=list, max_length=30)



@router.get("")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(ProjectRecord).order_by(ProjectRecord.name.asc()).all()
    return {"count": len(projects), "projects": [{"id": p.project_id, "name": p.name,
            "status": p.status, "risk_score": p.risk_score, "is_synthetic": bool(p.is_synthetic)} for p in projects]}


@router.post("")
def create_project(request: ProjectCreateRequest, db: Session = Depends(get_db)):
    """Create a project, optional starter tasks, and a searchable project-brief record."""
    project_id = (request.project_id or f"PROJ-{uuid4().hex[:8].upper()}").strip().upper()
    if db.query(ProjectRecord).filter(ProjectRecord.project_id == project_id).first():
        raise HTTPException(status_code=409, detail=f"Project ID '{project_id}' already exists.")

    project = ProjectRecord(
        project_id=project_id,
        name=request.name.strip(),
        status=request.status.strip() or "Planning",
        planned_release=request.planned_release,
        risk_score=request.risk_score,
        is_synthetic=False,
    )
    db.add(project)
    try:
        db.flush()
        created_tasks = []
        suffix = project_id.replace("-", "")[-8:]
        for index, task_input in enumerate(request.tasks, start=1):
            planned = task_input.planned_date or request.planned_release
            forecast = task_input.forecast_date or planned
            task_id = f"TASK-{suffix}-{index:03d}"
            if db.query(ProjectTask).filter(ProjectTask.task_id == task_id).first():
                task_id = f"TASK-{uuid4().hex[:12].upper()}"
            task = ProjectTask(
                task_id=task_id,
                project_id=project_id,
                name=task_input.name.strip(),
                status=task_input.status.strip() or "Planned",
                planned_date=planned,
                forecast_date=forecast,
                owner=task_input.owner.strip() or "Unassigned",
            )
            db.add(task)
            created_tasks.append(task_id)

        description = request.description.strip()
        if description:
            brief = ProjectDocument(
                document_id=f"DOC-{uuid4().hex[:24].upper()}",
                project_id=project_id,
                title=f"{request.name.strip()} — Project brief",
                source=f"project-brief:{project_id}",
                content=description,
                related_task_id=None,
                is_synthetic=False,
            )
            db.add(brief)

        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Project or task identifiers already exist. Choose a different Project ID.") from exc
    except Exception:
        db.rollback()
        raise

    return {
        "id": project_id,
        "name": project.name,
        "status": project.status,
        "planned_release": project.planned_release.isoformat(),
        "risk_score": project.risk_score,
        "is_synthetic": False,
        "tasks_created": len(created_tasks),
        "task_ids": created_tasks,
        "project_brief_added": bool(request.description.strip()),
    }


@router.get("/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    return load_project_payload(db, project_id)


@router.get("/{project_id}/investigation")
def investigate_project(project_id: str, db: Session = Depends(get_db)):
    return build_investigation(load_project_payload(db, project_id))


@router.post("/{project_id}/ai-investigation")
def ai_investigation(
    project_id: str,
    language: str = Query(default="English", max_length=40),
    db: Session = Depends(get_db),
):
    project = load_project_payload(db, project_id)
    investigation = build_investigation(project)
    try:
        selected_language = normalize_language(language)
        retrieval_query = (
            f"Project {project.get('name')} risk causes blockers delays dependencies "
            f"release {project.get('planned_release')} "
            + " ".join(f"{t.get('name', '')} {t.get('status', '')} {t.get('owner', '')}" for t in project.get("tasks", []))
        )
        retrieved = retrieve_evidence(db, project_id, retrieval_query, top_k=5)
        investigation["retrieved_evidence"] = retrieved["results"]
        investigation["retrieval_mode"] = retrieved["retrieval_mode"]
        project["retrieved_evidence"] = retrieved["results"]
        result = investigate_with_gemini(project, investigation, language=selected_language)
        model_meta = result.pop("_relay_meta", {})
        return {
            "project_id": project_id,
            "model": model_meta.get("model", __import__("os").getenv("GEMINI_MODEL_NAME", "gemini-flash-lite-latest")),
            "fallback_used": bool(model_meta.get("fallback_used", False)),
            "language": selected_language,
            "analysis": result,
            "retrieval": {"mode": retrieved["retrieval_mode"], "evidence_count": len(retrieved["results"])},
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Gemini investigation failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail=f"AI investigation failed ({type(exc).__name__}). Check backend logs.") from exc
