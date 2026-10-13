from datetime import date

import pytest

import ai_agent
from app.api.intelligence import _scenario_simulation
from app.api.projects import ProjectCreateRequest
from app.models import ProjectRecord, ProjectTask


def test_gemini_fallback_uses_next_model_for_503(monkeypatch):
    class UnavailableError(Exception):
        status_code = 503

    class FakeModels:
        def __init__(self):
            self.calls = []

        def generate_content(self, *, model, contents, config):
            self.calls.append(model)
            if model == "primary-model":
                raise UnavailableError("503 UNAVAILABLE: temporarily overloaded")
            return {"model": model, "text": "ok"}

    fake_models = FakeModels()
    class FakeClient:
        models = fake_models

    monkeypatch.setattr(ai_agent, "client", FakeClient())
    monkeypatch.setattr(ai_agent, "MODEL_NAME", "primary-model")
    monkeypatch.setattr(ai_agent, "MODEL_FALLBACKS", ("fallback-model", "last-model"))

    response, model_used = ai_agent.generate_content_with_fallback(
        operation="unit-test",
        contents="test",
        config={},
    )

    assert model_used == "fallback-model"
    assert response["text"] == "ok"
    assert fake_models.calls == ["primary-model", "fallback-model"]


def test_gemini_fallback_does_not_retry_authentication_errors(monkeypatch):
    class AuthError(Exception):
        status_code = 401

    class FakeModels:
        def __init__(self):
            self.calls = []

        def generate_content(self, *, model, contents, config):
            self.calls.append(model)
            raise AuthError("401 UNAUTHENTICATED")

    fake_models = FakeModels()
    class FakeClient:
        models = fake_models

    monkeypatch.setattr(ai_agent, "client", FakeClient())
    monkeypatch.setattr(ai_agent, "MODEL_NAME", "primary-model")
    monkeypatch.setattr(ai_agent, "MODEL_FALLBACKS", ("fallback-model",))

    with pytest.raises(AuthError):
        ai_agent.generate_content_with_fallback(
            operation="unit-test",
            contents="test",
            config={},
        )

    assert fake_models.calls == ["primary-model"]


def test_scenario_simulator_returns_transparent_alternatives():
    project = ProjectRecord(
        project_id="PROJ-TEST",
        name="Test",
        status="At Risk",
        planned_release=date(2026, 11, 20),
        risk_score=40,
        is_synthetic=True,
    )
    tasks = [
        ProjectTask(
            task_id="TASK-TEST",
            project_id="PROJ-TEST",
            name="Integration",
            status="Blocked",
            planned_date=date(2026, 11, 10),
            forecast_date=date(2026, 11, 10),
            owner="Team A",
        )
    ]

    result = _scenario_simulation(project, tasks, delay_days=5, delay_source="test assumption")
    scenarios = result["scenarios"]

    assert [item["name"] for item in scenarios] == [
        "Do nothing", "Parallelize eligible work", "Reduce critical-path scope"
    ]
    assert [item["projected_slip_days"] for item in scenarios] == [5, 3, 2]
    assert all(0 <= item["risk_index"] <= 100 for item in scenarios)
    assert "not a probability" in result["risk_score_note"]
    assert result["simulation_basis"] == "test assumption"


def test_project_creation_request_accepts_minimum_required_fields():
    request = ProjectCreateRequest.model_validate({
        "name": "Customer Portal",
        "planned_release": "2026-12-15",
    })

    assert request.name == "Customer Portal"
    assert request.project_id is None
    assert request.risk_score == 25
    assert request.tasks == []
