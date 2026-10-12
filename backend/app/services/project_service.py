"""Project read models and deterministic baseline investigation."""
from datetime import date
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories import project_repository as repo


def load_project_payload(db: Session, project_id: str) -> dict:
    project = repo.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = repo.get_tasks(db, project_id)
    task_ids = [task.task_id for task in tasks]
    blocked_by_map: dict[str, list[str]] = {}
    for dep in repo.get_dependencies(db, task_ids):
        blocked_by_map.setdefault(dep.task_id, []).append(dep.depends_on_task_id)

    task_payloads = [{
        "id": task.task_id,
        "name": task.name,
        "status": task.status,
        "planned_date": task.planned_date.isoformat(),
        "forecast_date": task.forecast_date.isoformat(),
        "owner": task.owner,
        "blocked_by": sorted(blocked_by_map.get(task.task_id, [])),
    } for task in tasks]

    evidence = [{
        "id": doc.document_id,
        "title": doc.title,
        "source": doc.source,
        "finding": doc.content,
        "related_task": doc.related_task_id,
        "is_synthetic": bool(doc.is_synthetic),
    } for doc in repo.get_documents(db, project_id)]

    return {
        "id": project.project_id,
        "name": project.name,
        "status": project.status,
        "is_synthetic": bool(project.is_synthetic),
        "planned_release": project.planned_release.isoformat(),
        "current_risk_score": project.risk_score,
        "tasks": task_payloads,
        "evidence": evidence,
    }


def build_investigation(project: dict) -> dict:
    tasks = project["tasks"]
    risky_statuses = {"delayed", "blocked", "at risk"}
    affected_tasks = [t for t in tasks if t["status"].strip().lower() in risky_statuses]

    def delay_days(task):
        try:
            return max(0, (date.fromisoformat(task["forecast_date"]) - date.fromisoformat(task["planned_date"])).days)
        except (KeyError, TypeError, ValueError):
            return 0

    primary_task = max(tasks, key=delay_days, default=None)
    primary_delay = delay_days(primary_task) if primary_task else 0
    evidence = project["evidence"]
    primary_evidence = next((d for d in evidence if primary_task and d.get("related_task") == primary_task["id"]), None)
    root_causes = []

    if primary_task and (primary_delay > 0 or primary_task["status"].strip().lower() in risky_statuses):
        root_causes.append({
            "cause": f"Schedule risk: {primary_task['name']}",
            "evidence_id": primary_evidence["id"] if primary_evidence else None,
            "impact": f"Owned by {primary_task['owner']}; forecast is {primary_delay} day(s) later than plan.",
        })

    dependency_tasks = [task for task in tasks if task.get("blocked_by")]
    dependency_evidence = next((d for d in evidence if d.get("related_task") and any(t["id"] == d["related_task"] and t.get("blocked_by") for t in tasks)), None)
    if dependency_tasks:
        root_causes.append({
            "cause": "Task dependency chain",
            "evidence_id": dependency_evidence["id"] if dependency_evidence else None,
            "impact": f"{len(dependency_tasks)} task(s) have upstream dependencies that may affect delivery.",
        })

    next_step = (
        f"Confirm the forecast and blocker for '{primary_task['name']}' with {primary_task['owner']}, then assess downstream impact."
        if primary_task else "Confirm task owners and forecast dates, then assess dependencies."
    )
    return {
        "project_id": project["id"],
        "project_name": project["name"],
        "summary": f"{project['name']} is {project['status'].lower()} because schedule risk and task dependencies may affect its planned release on {project['planned_release']}.",
        "risk_score": project["current_risk_score"],
        "risk_score_note": "Illustrative demo score out of 100, not a probability.",
        # Retained for compatibility with the original Project Alpha UI.
        "vendor_delay_days": delay_days(next((t for t in tasks if t["id"] == "TASK-101"), None)) if any(t["id"] == "TASK-101" for t in tasks) else 0,
        "primary_delay_days": primary_delay,
        "primary_task": primary_task,
        "affected_task_count": len(affected_tasks),
        "root_causes": root_causes,
        "affected_tasks": affected_tasks,
        "evidence": evidence,
        "recommended_next_step": next_step,
    }
