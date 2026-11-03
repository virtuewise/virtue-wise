"""Tests for the opt-in local model analysis adapter and API."""

import json

import pytest
from fastapi.testclient import TestClient

from app import analysis, store
from app.main import app
from app.models import ProjectModel, Statement


class FakeResponse:
    def __init__(self, payload):
        self.raw = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        return self.raw[:size]


class FakeOpener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        return FakeResponse(self.responses.pop(0))


def test_local_model_url_rejects_non_loopback_hosts(monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_OLLAMA_URL", "http://example.com:11434")

    with pytest.raises(analysis.AnalysisUnavailable):
        analysis._base_url()


def test_local_model_url_accepts_loopback_only(monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_OLLAMA_URL", "http://127.0.0.1:11435")

    assert analysis._base_url() == "http://127.0.0.1:11435"


def test_analysis_uses_structured_local_output_and_filters_unknown_evidence(monkeypatch):
    statement = Statement(text="Two planning meetings overran.", source_label="Test notes")
    project = ProjectModel(title="Planning", statements=[statement])
    generated = {
        "summary": "The notes describe repeated meeting overruns.",
        "hypotheses": [
            {
                "claim": "Agenda scope may contribute to overruns.",
                "rationale": "The notes are consistent with this possibility, but do not establish causation.",
                "evidence_statement_ids": [statement.id, "not-a-real-statement"],
                "counterpoints": ["Meeting overruns may have unrelated causes."],
            }
        ],
        "missing_information": ["Actual agenda duration and meeting attendance."],
        "questions": ["Which agenda items consistently overrun?"],
        "experiments": [
            {
                "question": "Would a time-boxed agenda reduce overruns?",
                "method": "Compare several meetings using a pre-agreed time-boxed agenda.",
                "limitations": "Other meeting conditions may change at the same time.",
            }
        ],
        "warnings": ["The model claims every suggestion is verified."],
        "scenarios": [
            {
                "name": "Use a time-boxed agenda",
                "assumptions": ["The agenda can be shortened."],
                "expected_outcome": "Meetings may finish closer to schedule.",
            }
        ],
    }
    opener = FakeOpener(
        [
            {"models": [{"name": "qwen3:8b"}]},
            {"message": {"content": json.dumps(generated)}},
        ]
    )
    monkeypatch.setattr(analysis, "build_opener", lambda *_args: opener)

    result = analysis.create_analysis_draft("Explore planning delays.", "qwen3:8b", project)

    assert result.hypotheses[0].evidence_statement_ids == [statement.id]
    assert any("unrecognized evidence reference" in warning for warning in result.warnings)
    assert not any("verified" in warning for warning in result.warnings)
    assert result.experiments[0].question == "Would a time-boxed agenda reduce overruns?"
    chat_request = json.loads(opener.requests[1][0].data)
    assert chat_request["stream"] is False
    assert chat_request["format"]["type"] == "object"
    assert "warnings" not in chat_request["format"]["properties"]
    assert "untrusted data" in chat_request["messages"][0]["content"]
    assert statement.id in chat_request["messages"][1]["content"]
    assert all(
        request.full_url.startswith("http://127.0.0.1:11434/") for request, _ in opener.requests
    )


def test_analysis_rejects_uninstalled_model(monkeypatch):
    opener = FakeOpener([{"models": [{"name": "other-model:latest"}]}])
    monkeypatch.setattr(analysis, "build_opener", lambda *_args: opener)

    with pytest.raises(analysis.AnalysisUnavailable, match="not installed"):
        analysis.create_analysis_draft("Explore this idea.", "qwen3:8b", ProjectModel())


def test_analysis_requires_explicit_local_processing_consent(tmp_path, monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_DB", str(tmp_path / "analysis.sqlite3"))
    client = TestClient(app)

    response = client.post(
        "/api/analysis/draft",
        json={"text": "Explore an idea.", "model": "qwen3:8b", "consent": False},
    )

    assert response.status_code == 400
    assert "Confirm" in response.json()["detail"]


def test_analysis_status_does_not_fail_when_local_model_is_absent(monkeypatch):
    def unavailable():
        raise analysis.AnalysisUnavailable("not running")

    monkeypatch.setattr(analysis, "list_models", unavailable)
    response = TestClient(app).get("/api/analysis/status")

    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["models"] == []


def test_analysis_endpoint_returns_review_only_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_DB", str(tmp_path / "analysis.sqlite3"))
    store.save_model(ProjectModel(title="Saved local project"))
    expected = analysis.AnalysisDraft(
        summary="A candidate explanation needs testing.",
        hypotheses=[
            analysis.HypothesisSuggestion(
                claim="A shorter agenda may reduce overruns.",
                rationale="This is a candidate explanation, not a verified result.",
            )
        ],
    )
    calls = []

    def create_draft(text, model_name, project):
        calls.append((text, model_name, project.title))
        return expected

    monkeypatch.setattr(analysis, "create_analysis_draft", create_draft)
    response = TestClient(app).post(
        "/api/analysis/draft",
        json={"text": "Explore meeting delays.", "model": "qwen3:8b", "consent": True},
    )

    assert response.status_code == 200
    assert response.json()["hypotheses"][0]["claim"] == expected.hypotheses[0].claim
    assert calls == [("Explore meeting delays.", "qwen3:8b", "Saved local project")]


def test_analysis_request_body_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_DB", str(tmp_path / "analysis-size.sqlite3"))
    response = TestClient(app).post(
        "/api/analysis/draft",
        content=b"x" * 16_385,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
