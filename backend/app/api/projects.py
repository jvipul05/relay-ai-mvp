from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ProjectRecord
from app.services.project_service import load_project_payload, build_investigation
from app.ai.investigation_agent import investigate_with_gemini
from app.retrieval.rag_service import retrieve_evidence
from ai_agent import normalize_language

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(ProjectRecord).order_by(ProjectRecord.name.asc()).all()
    return {"count": len(projects), "projects": [{"id": p.project_id, "name": p.name,
            "status": p.status, "risk_score": p.risk_score, "is_synthetic": bool(p.is_synthetic)} for p in projects]}


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
        return {
            "project_id": project_id,
            "model": __import__("os").getenv("GEMINI_MODEL_NAME", "gemini-flash-lite-latest"),
            "language": selected_language,
            "analysis": result,
            "retrieval": {"mode": retrieved["retrieval_mode"], "evidence_count": len(retrieved["results"])},
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Gemini investigation failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail=f"AI investigation failed ({type(exc).__name__}). Check backend logs.") from exc
