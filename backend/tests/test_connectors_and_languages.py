from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import ProjectConnectorConfig, ProjectRecord, ProjectTask
from app.api.mock_integrations import _normalise_url, _records
from ai_agent import normalize_language


@pytest.fixture()
def connector_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    session.add(ProjectRecord(
        project_id="PROJ-LINK-TEST",
        name="Connector test",
        status="At Risk",
        planned_release=date(2026, 11, 1),
        risk_score=70,
        is_synthetic=True,
    ))
    session.add(ProjectTask(
        task_id="TASK-LINK-TEST",
        project_id="PROJ-LINK-TEST",
        name="Test integration",
        status="Blocked",
        planned_date=date(2026, 10, 20),
        forecast_date=date(2026, 10, 23),
        owner="Integration Team",
    ))
    session.add_all([
        ProjectConnectorConfig(
            project_id="PROJ-LINK-TEST",
            provider="jira",
            base_url="https://jira.example.test",
        ),
        ProjectConnectorConfig(
            project_id="PROJ-LINK-TEST",
            provider="confluence",
            base_url="https://wiki.example.test/wiki",
        ),
    ])
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_dynamic_connector_links_use_project_configuration(connector_db):
    jira = _records(connector_db, "PROJ-LINK-TEST", "jira")
    confluence = _records(connector_db, "PROJ-LINK-TEST", "confluence")

    assert jira[0]["url"] == "https://jira.example.test/browse/DEMO-PROJ-LINK-TEST-TASK-LINK-TEST"
    assert confluence[0]["url"] == "https://wiki.example.test/wiki/pages/CONF-PROJ-LINK-TEST-OVERVIEW"
    assert jira[0]["is_synthetic"] is True
    assert confluence[0]["is_synthetic"] is True


def test_connector_url_normalization_removes_trailing_slash():
    assert _normalise_url("  https://jira.example.test/  ") == "https://jira.example.test"


@pytest.mark.parametrize("url", [
    "ftp://jira.example.test",
    "https://user:password@jira.example.test",
    "https://jira.example.test?project=demo",
    "https://jira.example.test/#fragment",
    "not-a-url",
])
def test_connector_url_rejects_unsafe_or_invalid_values(url):
    with pytest.raises(HTTPException) as error:
        _normalise_url(url)
    assert error.value.status_code == 422


@pytest.mark.parametrize("language", [
    "English", "Hindi", "Spanish", "French", "German",
    "Portuguese", "Japanese", "Korean", "Arabic", "Chinese (Simplified)",
])
def test_ai_output_language_allowlist(language):
    assert normalize_language(language) == language


def test_unknown_ai_output_language_is_rejected():
    with pytest.raises(ValueError):
        normalize_language("Klingon")
