"""Relay Ripple Intelligence: grounded change analysis, scenario estimates, and feedback."""
import json
import re
from time import perf_counter
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai_agent import analyze_ripple_with_gemini, normalize_language
from app.core.database import get_db
from app.models import (
    ProjectRecord,
    ProjectTask,
    ProjectDocument,
    TaskDependency,
    RelayIntelligenceRecord,
)
from app.retrieval.rag_service import retrieve_evidence

router = APIRouter(prefix="/api/intelligence", tags=["ripple-intelligence"])


class RippleRequest(BaseModel):
    project_id: str = Field(min_length=2, max_length=64)
    change_text: str = Field(min_length=10, max_length=6000)
    source: str = Field(default="manual", min_length=1, max_length=100)
    language: str = Field(default="English", max_length=40)
    assumed_delay_days: int = Field(default=3, ge=0, le=365)


class OutcomeRequest(BaseModel):
    status: str = Field(pattern="^(worked|partially_worked|did_not_work)$")
    notes: str = Field(default="", max_length=3000)


def _date_slip(task: ProjectTask) -> int:
    if not task.planned_date or not task.forecast_date:
        return 0
    return max(0, (task.forecast_date - task.planned_date).days)


def _portfolio_context(db: Session) -> tuple[list[dict], dict[str, dict]]:
    projects = db.query(ProjectRecord).order_by(ProjectRecord.name.asc()).all()
    tasks = db.query(ProjectTask).order_by(ProjectTask.planned_date.asc()).all()
    dependencies = db.query(TaskDependency).all()
    by_project: dict[str, list[ProjectTask]] = {}
    task_by_id = {task.task_id: task for task in tasks}
    blocked_by: dict[str, list[str]] = {}
    for task in tasks:
        by_project.setdefault(task.project_id, []).append(task)
    for dependency in dependencies:
        if dependency.task_id in task_by_id and dependency.depends_on_task_id in task_by_id:
            blocked_by.setdefault(dependency.task_id, []).append(dependency.depends_on_task_id)

    owner_projects: dict[str, set[str]] = {}
    for task in tasks:
        owner = (task.owner or "").strip()
        if owner and owner.lower() not in {"unassigned", "tbd", "n/a"}:
            owner_projects.setdefault(owner.casefold(), set()).add(task.project_id)

    context = []
    display_by_id = {}
    for project in projects:
        project_tasks = by_project.get(project.project_id, [])
        shared_resources = sorted({
            task.owner.strip()
            for task in project_tasks
            if task.owner and len(owner_projects.get(task.owner.strip().casefold(), set())) > 1
        })
        task_summaries = [{
            "id": task.task_id,
            "name": task.name,
            "status": task.status,
            "owner": task.owner,
            "planned_date": task.planned_date.isoformat() if task.planned_date else None,
            "forecast_date": task.forecast_date.isoformat() if task.forecast_date else None,
            "blocked_by": sorted(blocked_by.get(task.task_id, [])),
        } for task in project_tasks[:40]]
        item = {
            "id": project.project_id,
            "name": project.name,
            "status": project.status,
            "planned_release": project.planned_release.isoformat() if project.planned_release else None,
            "risk_score": int(project.risk_score or 0),
            "tasks": task_summaries,
            "shared_resources": shared_resources,
            "task_count": len(project_tasks),
            "blocked_task_count": sum(1 for task in project_tasks if str(task.status).strip().lower() == "blocked"),
            "at_risk_task_count": sum(1 for task in project_tasks if str(task.status).strip().lower() in {"blocked", "delayed", "at risk", "atrisk"}),
        }
        context.append(item)
        display_by_id[project.project_id] = item
    return context, display_by_id


def _scenario_simulation(project: ProjectRecord, tasks: list[ProjectTask], delay_days: int, delay_source: str) -> dict:
    """Transparent rule-based scenarios; risk is an illustrative index, not probability."""
    baseline_slip = max((_date_slip(task) for task in tasks), default=0)
    blocked_count = sum(1 for task in tasks if str(task.status).strip().lower() == "blocked")
    base_risk = max(0, min(100, int(project.risk_score or 0)))
    planned_release = project.planned_release
    setups = [
        {
            "name": "Do nothing",
            "remaining_delay": delay_days,
            "risk_relief": 0,
            "tradeoff": "No immediate intervention; downstream work remains exposed.",
            "assumptions": ["The event delay adds to the current maximum task slip."],
        },
        {
            "name": "Parallelize eligible work",
            "remaining_delay": (delay_days + 1) // 2,
            "risk_relief": 6,
            "tradeoff": "Requires genuinely independent tasks and available capacity; resource conflicts must be checked.",
            "assumptions": ["Up to half of the new delay can be overlapped with independent work."],
        },
        {
            "name": "Reduce critical-path scope",
            "remaining_delay": max(0, delay_days - min(3, delay_days)),
            "risk_relief": 10,
            "tradeoff": "Could protect the release date but may defer non-essential scope and needs stakeholder approval.",
            "assumptions": ["Scope review can remove up to three days from the critical path."],
        },
    ]
    results = []
    for setup in setups:
        added_slip = baseline_slip + setup["remaining_delay"]
        release = planned_release + timedelta(days=added_slip)
        raw_risk = base_risk + min(30, setup["remaining_delay"] * 4 + min(10, blocked_count * 2))
        risk_index = max(0, min(100, raw_risk - setup["risk_relief"]))
        results.append({
            "name": setup["name"],
            "estimated_release_date": release.isoformat(),
            "projected_slip_days": added_slip,
            "remaining_event_delay_days": setup["remaining_delay"],
            "risk_index": risk_index,
            "tradeoff": setup["tradeoff"],
            "assumptions": setup["assumptions"],
        })
    notes = [
        "These are illustrative scenario calculations, not calibrated forecasts or probabilities.",
        f"The new event delay is {delay_days} day(s), based on {delay_source}.",
        f"The current maximum task slip used as baseline is {baseline_slip} day(s).",
        f"The current project has {blocked_count} blocked task(s).",
        "Dates use the project release date plus the maximum task slip and the scenario delay; critical-path topology is not fully modeled.",
    ]
    return {
        "simulation_basis": delay_source,
        "assumed_event_delay_days": delay_days,
        "baseline_max_task_slip_days": baseline_slip,
        "blocked_task_count": blocked_count,
        "risk_score_note": "Risk index is an illustrative 0–100 score, not a probability.",
        "scenarios": results,
        "assumptions": notes,
    }


def _heuristic_project_ids(change_text: str, portfolio: list[dict], selected_id: str) -> set[str]:
    text = change_text.casefold()
    result = {selected_id}
    resource_terms = ("resource", "developer", "engineer", "capacity", "reassign", "owner", "team", "staff")
    tokens = {token for token in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", text) if len(token) >= 4}
    selected = next((project for project in portfolio if project["id"] == selected_id), None)
    selected_owners = {
        str(task.get("owner", "")).strip().casefold()
        for task in (selected or {}).get("tasks", [])
        if str(task.get("owner", "")).strip().casefold() not in {"", "unassigned", "tbd", "n/a"}
    }
    for project in portfolio:
        if project["id"] == selected_id:
            continue
        candidate_names = [project["name"], *(task["name"] for task in project["tasks"])]
        if any({word for word in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", name.casefold())} & tokens for name in candidate_names):
            result.add(project["id"])
            continue
        if any(term in text for term in resource_terms):
            owners = {
                str(task.get("owner", "")).strip().casefold()
                for task in project["tasks"]
                if str(task.get("owner", "")).strip().casefold() not in {"", "unassigned", "tbd", "n/a"}
            }
            if selected_owners & owners:
                result.add(project["id"])
    return result


@router.post("/ripple")
def analyze_ripple(request: RippleRequest, db: Session = Depends(get_db)):
    request_started_at = perf_counter()
    project = db.query(ProjectRecord).filter(ProjectRecord.project_id == request.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        language = normalize_language(request.language)
        context_started_at = perf_counter()
        portfolio, display_by_id = _portfolio_context(db)
        print(
            f"AI_STAGE_TIMING operation=ripple stage=portfolio_context "
            f"duration_ms={(perf_counter() - context_started_at) * 1000:.1f}"
        )
        retrieval_started_at = perf_counter()
        evidence_result = retrieve_evidence(
            db, request.project_id, request.change_text, top_k=8
        )
        evidence = evidence_result.get("results", [])
        print(
            f"AI_STAGE_TIMING operation=ripple stage=retrieval "
            f"duration_ms={(perf_counter() - retrieval_started_at) * 1000:.1f}"
        )
        generation_started_at = perf_counter()
        analysis = analyze_ripple_with_gemini(
            change_text=request.change_text,
            project_id=project.project_id,
            project_name=project.name,
            portfolio_context=portfolio,
            evidence=evidence,
            language=language,
        )
        print(
            f"AI_STAGE_TIMING operation=ripple stage=generation_and_validation "
            f"duration_ms={(perf_counter() - generation_started_at) * 1000:.1f}"
        )
        model_meta = analysis.pop("_relay_meta", {})
        estimated_days = int(analysis.get("estimated_delay_days") or 0)
        delay_basis = analysis.get("delay_basis", "unknown")
        if estimated_days > 0 and delay_basis in {"explicit", "inferred"}:
            simulation_days = estimated_days
            simulation_source = f"Gemini extraction ({delay_basis})"
        else:
            simulation_days = request.assumed_delay_days
            simulation_source = "user-provided what-if assumption"

        selected_tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project.project_id).all()
        simulation = _scenario_simulation(project, selected_tasks, simulation_days, simulation_source)
        affected_ids = set(analysis.get("affected_project_ids", []))
        affected_ids.update(_heuristic_project_ids(request.change_text, portfolio, project.project_id))
        affected_ids = {item for item in affected_ids if item in display_by_id}
        analysis["affected_project_ids"] = sorted(affected_ids)
        impacted_projects = [display_by_id[item] for item in sorted(affected_ids)]

        payload = {
            "change_text": request.change_text,
            "source": request.source,
            "project_id": project.project_id,
            "project_name": project.name,
            "analysis": analysis,
            "impacted_projects": impacted_projects,
            "simulation": simulation,
            "evidence": evidence,
            "retrieval_mode": evidence_result.get("retrieval_mode"),
            "model": model_meta.get("model"),
            "fallback_used": bool(model_meta.get("fallback_used", False)),
            "language": language,
        }
        record_id = f"RIP-{uuid4().hex[:20].upper()}"
        db.add(RelayIntelligenceRecord(
            record_id=record_id,
            project_id=project.project_id,
            record_type="change_ripple",
            title=(analysis.get("changed_entity") or "Project change")[:255],
            summary=analysis.get("executive_summary", "Ripple analysis completed.")[:10000],
            payload_json=json.dumps(payload, ensure_ascii=False),
            created_at=datetime.utcnow(),
        ))
        db.commit()
        print(
            f"AI_STAGE_TIMING operation=ripple stage=total "
            f"duration_ms={(perf_counter() - request_started_at) * 1000:.1f}"
        )
        return {"record_id": record_id, **payload}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        print(f"RIPPLE_ANALYSIS_FAILED project={request.project_id} error={type(exc).__name__}: {exc}")
        raise HTTPException(status_code=503, detail="Ripple analysis is temporarily unavailable. No actions were executed. Please retry shortly.") from exc


@router.get("/history")
def get_ripple_history(project_id: str, limit: int = 10, db: Session = Depends(get_db)):
    if not db.query(ProjectRecord).filter(ProjectRecord.project_id == project_id).first():
        raise HTTPException(status_code=404, detail="Project not found.")
    limit = max(1, min(30, limit))
    rows = (db.query(RelayIntelligenceRecord)
            .filter(RelayIntelligenceRecord.project_id == project_id)
            .order_by(RelayIntelligenceRecord.created_at.desc())
            .limit(limit).all())
    result = []
    for row in rows:
        try:
            payload = json.loads(row.payload_json)
        except (TypeError, ValueError):
            payload = {}
        result.append({
            "record_id": row.record_id,
            "record_type": row.record_type,
            "title": row.title,
            "summary": row.summary,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "outcome_status": row.outcome_status,
            "outcome_notes": row.outcome_notes,
            "payload": payload,
        })
    return {"project_id": project_id, "count": len(result), "records": result}


@router.post("/{record_id}/outcome")
def record_ripple_outcome(record_id: str, request: OutcomeRequest, db: Session = Depends(get_db)):
    record = db.query(RelayIntelligenceRecord).filter(
        RelayIntelligenceRecord.record_id == record_id,
        RelayIntelligenceRecord.record_type == "change_ripple",
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Ripple analysis record not found.")
    record.outcome_status = request.status
    record.outcome_notes = request.notes.strip() or None
    record.outcome_recorded_at = datetime.utcnow()
    db.commit()
    return {
        "record_id": record.record_id,
        "outcome_status": record.outcome_status,
        "outcome_notes": record.outcome_notes,
        "outcome_recorded_at": record.outcome_recorded_at.isoformat(),
    }
