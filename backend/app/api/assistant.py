from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ProjectRecord, ProjectTask, TaskDependency
from app.services.project_service import load_project_payload
from app.retrieval.rag_service import retrieve_evidence
from ai_agent import chat_with_rag, normalize_language

router = APIRouter(prefix="/api/projects/{project_id}", tags=["assistant-and-visualizations"])
portfolio_router = APIRouter(prefix="/api", tags=["assistant-and-visualizations"])


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=8)
    top_k: int = Field(default=5, ge=1, le=8)
    language: str = Field(default="English", max_length=40)


@router.post("/chat")
def project_chat(project_id: str, request: ChatRequest, db: Session = Depends(get_db)):
    project = load_project_payload(db, project_id)
    try:
        language = normalize_language(request.language)
        retrieval = retrieve_evidence(db, project_id, request.message, request.top_k)
        result = chat_with_rag(
            project, request.message, retrieval.get("results", []),
            [message.model_dump() for message in request.history], language=language,
        )
        return {
            "project_id": project_id,
            "model": __import__("os").getenv("GEMINI_MODEL_NAME", "gemini-flash-lite-latest"),
            "language": language,
            "retrieval_mode": retrieval.get("retrieval_mode"),
            "evidence_count": len(retrieval.get("results", [])),
            **result,
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        print(f"RAG chat failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail=f"RAG chat failed ({type(exc).__name__}). Check backend logs.") from exc


@router.get("/graph")
def project_graph(project_id: str, db: Session = Depends(get_db)):
    project = db.query(ProjectRecord).filter(ProjectRecord.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project_id).all()
    task_ids = {task.task_id for task in tasks}
    dependencies = db.query(TaskDependency).filter(TaskDependency.task_id.in_(task_ids)).all() if task_ids else []
    return {
        "project_id": project_id,
        "nodes": [{"id": task.task_id, "label": task.name, "status": task.status, "owner": task.owner,
                   "planned_date": task.planned_date.isoformat(), "forecast_date": task.forecast_date.isoformat()}
                  for task in tasks],
        "edges": [{"from": dependency.depends_on_task_id, "to": dependency.task_id}
                  for dependency in dependencies
                  if dependency.depends_on_task_id in task_ids and dependency.task_id in task_ids],
    }


@portfolio_router.get("/portfolio")
def portfolio(db: Session = Depends(get_db)):
    projects = db.query(ProjectRecord).order_by(ProjectRecord.name.asc()).all()
    result = []
    for project in projects:
        tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project.project_id).all()
        risk_tasks = sum(
            1 for task in tasks
            if str(task.status).strip().lower() in {"delayed", "blocked", "at risk", "atrisk"}
        )
        slips = sum(
            1 for task in tasks
            if task.forecast_date and task.planned_date and task.forecast_date > task.planned_date
        )
        result.append({
            "id": project.project_id, "name": project.name, "status": project.status,
            "risk_score": project.risk_score, "planned_release": project.planned_release.isoformat(),
            "task_count": len(tasks), "risk_task_count": risk_tasks, "forecast_slips": slips,
            "is_synthetic": bool(project.is_synthetic),
        })
    return {
        "count": len(result), "projects": result,
        "summary": {
            "high_risk_projects": sum(1 for item in result if item["risk_score"] >= 70),
            "risk_tasks": sum(item["risk_task_count"] for item in result),
            "forecast_slips": sum(item["forecast_slips"] for item in result),
        },
    }
