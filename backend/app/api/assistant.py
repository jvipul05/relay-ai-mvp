from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import ProjectRecord, ProjectTask, TaskDependency
from app.services.project_service import load_project_payload
from app.retrieval.rag_service import retrieve_evidence

router = APIRouter(prefix="/api/projects/{project_id}", tags=["assistant-and-visualizations"])
portfolio_router = APIRouter(prefix="/api", tags=["assistant-and-visualizations"])

class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)

class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=8)
    top_k: int = Field(default=5, ge=1, le=8)

@router.post("/chat")
def project_chat(project_id: str, request: ChatRequest, db: Session = Depends(get_db)):
    project = load_project_payload(db, project_id)
    retrieval = retrieve_evidence(db, project_id, request.message, request.top_k)
    try:
        from ai_agent import chat_with_rag
        result = chat_with_rag(project, request.message, retrieval.get("results", []), [m.model_dump() for m in request.history])
        return {"project_id": project_id, "model": "gemini-flash-lite-latest", "retrieval_mode": retrieval.get("retrieval_mode"),
                "evidence_count": len(retrieval.get("results", [])), **result}
    except Exception as exc:
        print(f"RAG chat failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail=f"RAG chat failed ({type(exc).__name__}). Check backend logs.") from exc

@router.get("/graph")
def project_graph(project_id: str, db: Session = Depends(get_db)):
    project = db.query(ProjectRecord).filter(ProjectRecord.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project_id).all()
    task_ids = {t.task_id for t in tasks}
    dependencies = db.query(TaskDependency).filter(TaskDependency.task_id.in_(task_ids)).all() if task_ids else []
    return {"project_id": project_id,
            "nodes": [{"id": t.task_id, "label": t.name, "status": t.status, "owner": t.owner,
                       "planned_date": t.planned_date.isoformat(), "forecast_date": t.forecast_date.isoformat()} for t in tasks],
            "edges": [{"from": d.depends_on_task_id, "to": d.task_id} for d in dependencies
                      if d.depends_on_task_id in task_ids and d.task_id in task_ids]}

@portfolio_router.get("/portfolio")
def portfolio(db: Session = Depends(get_db)):
    projects = db.query(ProjectRecord).order_by(ProjectRecord.name.asc()).all()
    result = []
    for p in projects:
        tasks = db.query(ProjectTask).filter(ProjectTask.project_id == p.project_id).all()
        statuses = {str(t.status).strip().lower() for t in tasks}
        risk_tasks = sum(1 for t in tasks if str(t.status).strip().lower() in {"delayed", "blocked", "at risk", "atrisk"})
        slips = sum(1 for t in tasks if t.forecast_date and t.planned_date and t.forecast_date > t.planned_date)
        result.append({"id": p.project_id, "name": p.name, "status": p.status, "risk_score": p.risk_score,
                       "planned_release": p.planned_release.isoformat(), "task_count": len(tasks),
                       "risk_task_count": risk_tasks, "forecast_slips": slips})
    return {"count": len(result), "projects": result,
            "summary": {"high_risk_projects": sum(1 for p in result if p["risk_score"] >= 70),
                        "risk_tasks": sum(p["risk_task_count"] for p in result),
                        "forecast_slips": sum(p["forecast_slips"] for p in result)}}
