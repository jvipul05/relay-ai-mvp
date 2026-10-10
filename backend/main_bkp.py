from datetime import date, datetime, timezone
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    URL,
    create_engine,
    text,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from ai_agent import investigate_with_gemini

load_dotenv()

required_db_settings = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
missing_db_settings = [key for key in required_db_settings if not os.getenv(key)]
if missing_db_settings:
    raise RuntimeError(
        "Missing MySQL settings in backend/.env: " + ", ".join(missing_db_settings)
    )

database_url = URL.create(
    drivername="mysql+pymysql",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME"),
)
engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ----------------------------- Database models -----------------------------
class ProjectRecord(Base):
    __tablename__ = "relay_projects"

    project_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(64), nullable=False)
    planned_release = Column(Date, nullable=False)
    risk_score = Column(Integer, nullable=False, default=0)
    is_synthetic = Column(Boolean, nullable=False, default=True)


class ProjectTask(Base):
    __tablename__ = "relay_project_tasks"

    task_id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64), ForeignKey("relay_projects.project_id"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    status = Column(String(64), nullable=False)
    planned_date = Column(Date, nullable=False)
    forecast_date = Column(Date, nullable=False)
    owner = Column(String(255), nullable=False)


class TaskDependency(Base):
    __tablename__ = "relay_task_dependencies"
    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_task_id", name="uq_relay_task_dependency"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(
        String(64), ForeignKey("relay_project_tasks.task_id"), nullable=False, index=True
    )
    depends_on_task_id = Column(
        String(64), ForeignKey("relay_project_tasks.task_id"), nullable=False, index=True
    )


class ProjectDocument(Base):
    __tablename__ = "relay_project_documents"

    document_id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64), ForeignKey("relay_projects.project_id"), nullable=False, index=True
    )
    title = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    related_task_id = Column(
        String(64), ForeignKey("relay_project_tasks.task_id"), nullable=True, index=True
    )
    is_synthetic = Column(Boolean, nullable=False, default=True)


class RecoveryAction(Base):
    __tablename__ = "relay_recovery_actions"

    action_id = Column(String(32), primary_key=True)
    project_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending_approval")
    created_at = Column(DateTime, nullable=False)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    execution_result = Column(Text, nullable=True)
    verified_by = Column(String(255), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_result = Column(Text, nullable=True)


class ActionAudit(Base):
    __tablename__ = "relay_action_audit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(
        String(32), ForeignKey("relay_recovery_actions.action_id"), nullable=False, index=True
    )
    project_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    actor = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def utc_now_naive():
    # MySQL DATETIME has no timezone component; store UTC consistently.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc_iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def action_to_dict(action):
    return {
        "id": action.action_id,
        "project_id": action.project_id,
        "title": action.title,
        "description": action.description,
        "status": action.status,
        "created_at": to_utc_iso(action.created_at),
        "approved_by": action.approved_by,
        "approved_at": to_utc_iso(action.approved_at),
        "execution_result": action.execution_result,
        "verified_by": action.verified_by,
        "verified_at": to_utc_iso(action.verified_at),
        "verification_result": action.verification_result,
    }


def add_audit_event(db, action, event_type, actor, details=None):
    db.add(
        ActionAudit(
            action_id=action.action_id,
            project_id=action.project_id,
            event_type=event_type,
            actor=actor,
            details=details,
            created_at=utc_now_naive(),
        )
    )


def load_project_payload(db: Session, project_id: str) -> dict:
    """Build the existing API payload from MySQL records, not a Python constant."""
    project = db.query(ProjectRecord).filter_by(project_id=project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = (
        db.query(ProjectTask)
        .filter_by(project_id=project_id)
        .order_by(ProjectTask.planned_date.asc(), ProjectTask.task_id.asc())
        .all()
    )
    task_ids = [task.task_id for task in tasks]
    dependencies = []
    if task_ids:
        dependencies = (
            db.query(TaskDependency)
            .filter(TaskDependency.task_id.in_(task_ids))
            .all()
        )

    blocked_by_map = {}
    for dependency in dependencies:
        blocked_by_map.setdefault(dependency.task_id, []).append(dependency.depends_on_task_id)

    task_payloads = [
        {
            "id": task.task_id,
            "name": task.name,
            "status": task.status,
            "planned_date": task.planned_date.isoformat(),
            "forecast_date": task.forecast_date.isoformat(),
            "owner": task.owner,
            "blocked_by": sorted(blocked_by_map.get(task.task_id, [])),
        }
        for task in tasks
    ]

    documents = (
        db.query(ProjectDocument)
        .filter_by(project_id=project_id)
        .order_by(ProjectDocument.document_id.asc())
        .all()
    )
    evidence = [
        {
            "id": document.document_id,
            "title": document.title,
            "source": document.source,
            "finding": document.content,
            "related_task": document.related_task_id,
        }
        for document in documents
    ]

    return {
        "id": project.project_id,
        "name": project.name,
        "status": project.status,
        "planned_release": project.planned_release.isoformat(),
        "current_risk_score": project.risk_score,
        "tasks": task_payloads,
        "evidence": evidence,
    }


def build_investigation(project: dict) -> dict:
    tasks = project["tasks"]
    delayed_tasks = [
        task for task in tasks if task["status"] in {"Delayed", "Blocked", "At Risk"}
    ]
    vendor_task = next((task for task in tasks if task["id"] == "TASK-101"), None)
    vendor_delay_days = 0
    if vendor_task:
        planned = date.fromisoformat(vendor_task["planned_date"])
        forecast = date.fromisoformat(vendor_task["forecast_date"])
        vendor_delay_days = (forecast - planned).days

    root_causes = []
    vendor_evidence = next(
        (doc for doc in project["evidence"] if doc.get("related_task") == "TASK-101"), None
    )
    if vendor_task:
        root_causes.append(
            {
                "cause": "Vendor API delivery delay",
                "evidence_id": vendor_evidence["id"] if vendor_evidence else None,
                "impact": "Integration cannot proceed as planned.",
            }
        )
    dependency_evidence = next(
        (doc for doc in project["evidence"] if doc.get("related_task") != "TASK-101"), None
    )
    if any(task["blocked_by"] for task in tasks):
        root_causes.append(
            {
                "cause": "Sequential task dependencies",
                "evidence_id": dependency_evidence["id"] if dependency_evidence else None,
                "impact": "Downstream integration, testing, UAT, and release activities may be affected.",
            }
        )

    return {
        "project_id": project["id"],
        "project_name": project["name"],
        "summary": (
            f"{project['name']} is {project['status'].lower()} because delayed or at-risk "
            "tasks and their dependencies may affect downstream delivery."
        ),
        "risk_score": project["current_risk_score"],
        "risk_score_note": "Illustrative demo score out of 100, not a probability.",
        "vendor_delay_days": vendor_delay_days,
        "affected_task_count": len(delayed_tasks),
        "root_causes": root_causes,
        "affected_tasks": delayed_tasks,
        "evidence": project["evidence"],
        "recommended_next_step": (
            "Confirm the latest blocker and forecast dates with their owners, then evaluate "
            "which downstream tasks can proceed in parallel."
        ),
    }


app = FastAPI(
    title="Relay AI",
    description="AI-powered organizational intelligence and work execution",
    version="0.2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_database_tables():
    # Safe for existing data: creates missing tables only; it does not drop tables.
    Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {
        "application": "Relay AI",
        "version": "0.2.0",
        "message": "Organizational intelligence and work execution API",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/health/database")
def database_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database connection failed") from exc


@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(ProjectRecord).order_by(ProjectRecord.name.asc()).all()
    return {
        "count": len(projects),
        "projects": [
            {
                "id": project.project_id,
                "name": project.name,
                "status": project.status,
                "risk_score": project.risk_score,
            }
            for project in projects
        ],
    }


@app.get("/api/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    return load_project_payload(db, project_id)


@app.get("/api/projects/{project_id}/investigation")
def investigate_project(project_id: str, db: Session = Depends(get_db)):
    project = load_project_payload(db, project_id)
    return build_investigation(project)


@app.post("/api/projects/{project_id}/ai-investigation")
def ai_investigation(project_id: str, db: Session = Depends(get_db)):
    project = load_project_payload(db, project_id)
    investigation = build_investigation(project)
    try:
        result = investigate_with_gemini(project, investigation)
        return {
            "project_id": project_id,
            "model": "gemini-flash-lite-latest",
            "analysis": result,
        }
    except Exception as exc:
        # Avoid returning environment details or secrets in API error responses.
        print(f"Gemini investigation failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=502,
            detail=f"AI investigation failed ({type(exc).__name__}). Check backend logs.",
        ) from exc


# ----------------------------- Recovery actions -----------------------------
class ActionCreate(BaseModel):
    title: str
    description: str


class ActionApproval(BaseModel):
    approved_by: str = "Demo User"


class ActionVerification(BaseModel):
    verified_by: str = "Demo User"


def find_action(db: Session, project_id: str, action_id: str):
    # Ensure the project exists rather than relying on a hardcoded project ID.
    if db.query(ProjectRecord.project_id).filter_by(project_id=project_id).first() is None:
        raise HTTPException(status_code=404, detail="Project not found")
    action = (
        db.query(RecoveryAction)
        .filter_by(action_id=action_id, project_id=project_id)
        .first()
    )
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@app.get("/api/projects/{project_id}/actions")
def list_actions(project_id: str, db: Session = Depends(get_db)):
    if db.query(ProjectRecord.project_id).filter_by(project_id=project_id).first() is None:
        raise HTTPException(status_code=404, detail="Project not found")
    actions = (
        db.query(RecoveryAction)
        .filter_by(project_id=project_id)
        .order_by(RecoveryAction.created_at.desc())
        .all()
    )
    return {"count": len(actions), "actions": [action_to_dict(action) for action in actions]}


@app.post("/api/projects/{project_id}/actions")
def create_action(project_id: str, request: ActionCreate, db: Session = Depends(get_db)):
    if db.query(ProjectRecord.project_id).filter_by(project_id=project_id).first() is None:
        raise HTTPException(status_code=404, detail="Project not found")
    title = request.title.strip()
    description = request.description.strip()
    if not title or not description:
        raise HTTPException(status_code=400, detail="Title and description are required")

    try:
        # Readable demo IDs; max+1 avoids reuse when old actions have been deleted.
        existing_ids = [
            row[0] for row in db.query(RecoveryAction.action_id)
            .filter(RecoveryAction.action_id.like("ACT-%")).all()
        ]
        numeric_ids = []
        for existing_id in existing_ids:
            try:
                numeric_ids.append(int(existing_id.split("-", 1)[1]))
            except (IndexError, ValueError):
                continue
        action = RecoveryAction(
            action_id=f"ACT-{(max(numeric_ids, default=0) + 1):03d}",
            project_id=project_id,
            title=title,
            description=description,
            status="pending_approval",
            created_at=utc_now_naive(),
        )
        db.add(action)
        db.flush()
        add_audit_event(db, action, "created", "Demo User", "Recovery action created.")
        db.commit()
        db.refresh(action)
        return action_to_dict(action)
    except Exception:
        db.rollback()
        raise


@app.post("/api/projects/{project_id}/actions/{action_id}/approve")
def approve_action(
    project_id: str, action_id: str, request: ActionApproval, db: Session = Depends(get_db)
):
    action = find_action(db, project_id, action_id)
    if action.status != "pending_approval":
        raise HTTPException(status_code=409, detail="Only pending actions can be approved")
    try:
        action.status = "approved"
        action.approved_by = request.approved_by.strip() or "Demo User"
        action.approved_at = utc_now_naive()
        add_audit_event(db, action, "approved", action.approved_by, "Action approved.")
        db.commit()
        db.refresh(action)
        return action_to_dict(action)
    except Exception:
        db.rollback()
        raise


@app.post("/api/projects/{project_id}/actions/{action_id}/execute")
def execute_action(project_id: str, action_id: str, db: Session = Depends(get_db)):
    action = find_action(db, project_id, action_id)
    if action.status != "approved":
        raise HTTPException(status_code=409, detail="Action must be approved before execution")
    try:
        # Simulation only: no external system is modified.
        action.status = "executed"
        action.execution_result = (
            "Simulated execution completed successfully. No external system was changed."
        )
        add_audit_event(db, action, "executed", "Demo User", action.execution_result)
        db.commit()
        db.refresh(action)
        return action_to_dict(action)
    except Exception:
        db.rollback()
        raise


@app.post("/api/projects/{project_id}/actions/{action_id}/verify")
def verify_action(
    project_id: str, action_id: str, request: ActionVerification, db: Session = Depends(get_db)
):
    action = find_action(db, project_id, action_id)
    if action.status != "executed":
        raise HTTPException(status_code=409, detail="Only executed actions can be verified")
    try:
        action.status = "verified"
        action.verified_by = request.verified_by.strip() or "Demo User"
        action.verified_at = utc_now_naive()
        action.verification_result = (
            "Verification passed: the simulated execution result was recorded successfully."
        )
        add_audit_event(db, action, "verified", action.verified_by, action.verification_result)
        db.commit()
        db.refresh(action)
        return action_to_dict(action)
    except Exception:
        db.rollback()
        raise


@app.get("/api/projects/{project_id}/actions/{action_id}/audit")
def list_action_audit(project_id: str, action_id: str, db: Session = Depends(get_db)):
    find_action(db, project_id, action_id)
    events = (
        db.query(ActionAudit)
        .filter_by(project_id=project_id, action_id=action_id)
        .order_by(ActionAudit.created_at.asc(), ActionAudit.id.asc())
        .all()
    )
    return {
        "count": len(events),
        "events": [
            {
                "id": event.id,
                "action_id": event.action_id,
                "project_id": event.project_id,
                "event_type": event.event_type,
                "actor": event.actor,
                "details": event.details,
                "created_at": to_utc_iso(event.created_at),
            }
            for event in events
        ],
    }
