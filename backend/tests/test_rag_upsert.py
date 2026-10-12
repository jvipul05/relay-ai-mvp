from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import ProjectRecord, ProjectTask, ProjectDocument, DocumentChunk
import app.retrieval.rag_service as rag_service


@pytest.fixture()
def db_session(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = session_factory()
    db.add(ProjectRecord(
        project_id="PROJ-TEST", name="Test project", status="At Risk",
        planned_release=date(2026, 11, 1), risk_score=70, is_synthetic=True,
    ))
    db.add(ProjectTask(
        task_id="TASK-TEST", project_id="PROJ-TEST", name="Test task",
        status="Blocked", planned_date=date(2026, 10, 20),
        forecast_date=date(2026, 10, 23), owner="Test owner",
    ))
    db.commit()
    monkeypatch.setattr(rag_service, "embed_texts", lambda chunks: None)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_repeated_connector_ingest_does_not_duplicate_document_or_chunks(db_session):
    first = rag_service.ingest_document(
        db_session, "PROJ-TEST", "Jira issue", "mock-jira:DEMO-PROJ-TEST-TASK-TEST",
        "Synthetic issue: the test task is blocked.", "TASK-TEST", True,
    )
    second = rag_service.ingest_document(
        db_session, "PROJ-TEST", "Jira issue", "mock-jira:DEMO-PROJ-TEST-TASK-TEST",
        "Synthetic issue: the test task is blocked.", "TASK-TEST", True,
    )

    assert first["created"] is True
    assert second["created"] is False
    assert second["updated"] is False
    assert first["document_id"] == second["document_id"]
    assert db_session.query(ProjectDocument).filter_by(project_id="PROJ-TEST").count() == 1
    assert db_session.query(DocumentChunk).filter_by(document_id=first["document_id"]).count() == first["chunks_indexed"]


def test_same_source_content_change_updates_document_in_place(db_session):
    first = rag_service.ingest_document(
        db_session, "PROJ-TEST", "Jira issue", "mock-jira:DEMO-PROJ-TEST-TASK-TEST",
        "The test task is blocked.", "TASK-TEST", True,
    )
    updated = rag_service.ingest_document(
        db_session, "PROJ-TEST", "Jira issue updated", "mock-jira:DEMO-PROJ-TEST-TASK-TEST",
        "The test task is now in progress after a dependency was fixed.", "TASK-TEST", True,
    )

    assert updated["created"] is False
    assert updated["updated"] is True
    assert first["document_id"] == updated["document_id"]
    assert db_session.query(ProjectDocument).filter_by(project_id="PROJ-TEST").count() == 1
    document = db_session.get(ProjectDocument, first["document_id"])
    assert "now in progress" in document.content
    chunks = db_session.query(DocumentChunk).filter_by(document_id=first["document_id"]).all()
    assert chunks
    assert any("now in progress" in chunk.content for chunk in chunks)


def test_legacy_jira_source_is_migrated_to_task_stable_source(db_session):
    legacy = rag_service.ingest_document(
        db_session, "PROJ-TEST", "Legacy Jira issue", "mock-jira:DEMO-PROJ-TEST-001",
        "Old generated issue text.", "TASK-TEST", True,
    )
    migrated = rag_service.ingest_document(
        db_session, "PROJ-TEST", "Task-based Jira issue", "mock-jira:DEMO-PROJ-TEST-TASK-TEST",
        "Updated task-based issue text.", "TASK-TEST", True,
    )

    assert migrated["document_id"] == legacy["document_id"]
    assert migrated["updated"] is True
    assert db_session.query(ProjectDocument).filter_by(project_id="PROJ-TEST").count() == 1
    document = db_session.get(ProjectDocument, legacy["document_id"])
    assert document.source == "mock-jira:DEMO-PROJ-TEST-TASK-TEST"
