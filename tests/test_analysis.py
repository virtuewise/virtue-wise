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
                "rationale": (
                    "The notes are consistent with this possibility, but do not "
                    "establish causation."
                ),
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

    result = analysis.create_analysis_draft(
        "Explore planning delays.", "ollama", "qwen3:8b", project
    )

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
        analysis.create_analysis_draft("Explore this idea.", "ollama", "qwen3:8b", ProjectModel())


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
    monkeypatch.setattr(
        analysis,
        "list_provider_catalog",
        lambda: [
            {
                "id": "ollama",
                "label": "Ollama",
                "available": False,
                "models": [],
                "note": "",
            }
        ],
    )
    response = TestClient(app).get("/api/analysis/status")

    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["providers"][0]["id"] == "ollama"


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

    def create_draft(text, provider, model_name, project):
        calls.append((text, provider, model_name, project.title))
        return expected

    monkeypatch.setattr(analysis, "create_analysis_draft", create_draft)
    response = TestClient(app).post(
        "/api/analysis/draft",
        json={
            "text": "Explore meeting delays.",
            "provider": "ollama",
            "model": "qwen3:8b",
            "consent": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["hypotheses"][0]["claim"] == expected.hypotheses[0].claim
    assert calls == [("Explore meeting delays.", "ollama", "qwen3:8b", "Saved local project")]


def test_provider_self_test_requires_explicit_consent(monkeypatch):
    called = []
    monkeypatch.setattr(
        analysis,
        "create_analysis_draft",
        lambda *args: called.append(args),
    )

    response = TestClient(app).post(
        "/api/analysis/self-test",
        json={"provider": "ollama", "model": "qwen3:8b", "consent": False},
    )

    assert response.status_code == 400
    assert "fictional sample prompt" in response.json()["detail"]
    assert called == []


def test_provider_self_test_rejects_user_supplied_content_fields():
    response = TestClient(app).post(
        "/api/analysis/self-test",
        json={
            "provider": "ollama",
            "model": "qwen3:8b",
            "consent": True,
            "text": "This private text must not be accepted by the smoke-test endpoint.",
        },
    )

    assert response.status_code == 422


def test_provider_self_test_uses_only_fictional_context(monkeypatch):
    expected = analysis.AnalysisDraft(
        summary="The sample provider returned a valid structured response.",
        hypotheses=[
            analysis.HypothesisSuggestion(
                claim="The fictional team may need to reduce planned work."
            )
        ],
    )
    calls = []

    def create_draft(text, provider, model_name, project):
        calls.append((text, provider, model_name, project))
        return expected

    monkeypatch.setattr(analysis, "create_analysis_draft", create_draft)
    monkeypatch.setattr(
        store,
        "load_model",
        lambda: pytest.fail("A provider self-test must not load the saved workspace."),
    )

    response = TestClient(app).post(
        "/api/analysis/self-test",
        json={"provider": "ollama", "model": "qwen3:8b", "consent": True},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "provider": "ollama",
        "model": "qwen3:8b",
        "structured_response": True,
        "hypothesis_count": 1,
    }
    assert len(calls) == 1
    prompt, provider, model_name, project = calls[0]
    assert "fictional sample data only" in prompt
    assert "planned three tasks and completed two" in prompt
    assert provider == "ollama"
    assert model_name == "qwen3:8b"
    assert project.title == "Provider connection test"
    assert project.statements == []
    assert project.hypotheses == []
    assert project.scenarios == []


@pytest.mark.parametrize(
    ("provider_error", "status_code"),
    [
        (analysis.AnalysisUnavailable("The provider rate limit was reached."), 503),
        (analysis.AnalysisTimeout("The provider took too long."), 504),
        (analysis.AnalysisInvalidResponse("The provider returned invalid JSON."), 502),
    ],
)
def test_provider_self_test_reports_provider_failures(
    monkeypatch,
    provider_error,
    status_code,
):
    def fail_analysis(*_args):
        raise provider_error

    monkeypatch.setattr(analysis, "create_analysis_draft", fail_analysis)
    response = TestClient(app).post(
        "/api/analysis/self-test",
        json={"provider": "openrouter", "model": "free-model", "consent": True},
    )

    assert response.status_code == status_code
    assert response.json()["detail"] == str(provider_error)


def test_analysis_request_body_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_DB", str(tmp_path / "analysis-size.sqlite3"))
    response = TestClient(app).post(
        "/api/analysis/draft",
        content=b"x" * 16_385,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413


def test_openrouter_catalog_only_lists_zero_price_models(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(analysis, "list_models", lambda: [])
    monkeypatch.setattr(
        analysis,
        "_request_provider_json",
        lambda *_args, **_kwargs: {
            "data": [
                {
                    "id": "vendor/free-model:free",
                    "name": "Free model",
                    "pricing": {"prompt": "0", "completion": "0"},
                },
                {
                    "id": "vendor/paid-model",
                    "name": "Paid model",
                    "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                },
                {"id": "vendor/unknown-price", "pricing": {}},
            ]
        },
    )

    provider = next(item for item in analysis.list_provider_catalog() if item["id"] == "openrouter")

    assert provider["available"] is True
    assert {item["id"] for item in provider["models"]} == {
        "vendor/free-model:free",
        "openrouter/free",
    }


def test_opencode_catalog_only_lists_models_with_zero_input_and_output_cost(monkeypatch):
    monkeypatch.setattr(analysis, "list_models", lambda: [])
    monkeypatch.setattr(
        analysis,
        "_opencode_request",
        lambda *_args, **_kwargs: {
            "providers": [
                {
                    "id": "openrouter",
                    "models": {
                        "free-model": {
                            "name": "Free model",
                            "cost": {"input": 0, "output": 0},
                        },
                        "paid-model": {
                            "name": "Paid model",
                            "cost": {"input": 1, "output": 1},
                        },
                        "unknown-price": {"name": "Unknown price"},
                    },
                }
            ]
        },
    )

    provider = next(item for item in analysis.list_provider_catalog() if item["id"] == "opencode")

    assert provider["available"] is True
    assert [item["id"] for item in provider["models"]] == ["openrouter/free-model"]


def test_opencode_analysis_disables_tools_and_deletes_temporary_session(monkeypatch):
    generated = {
        "summary": "A review-only result.",
        "hypotheses": [],
        "missing_information": [],
        "questions": [],
        "experiments": [],
        "scenarios": [],
    }
    calls = []

    def fake_request(path, payload=None, *, method=None, timeout=None):
        calls.append((path, payload, method, timeout))
        if path == "/config/providers":
            return {
                "providers": [
                    {
                        "id": "openrouter",
                        "models": {
                            "free-model": {
                                "cost": {"input": 0, "output": 0},
                            }
                        },
                    }
                ]
            }
        if path == "/session":
            return {"id": "session-123"}
        if path.endswith("/message"):
            return {
                "parts": [{"type": "text", "text": json.dumps(generated)}],
            }
        return {}

    monkeypatch.setattr(analysis, "_opencode_request", fake_request)
    result = analysis.create_analysis_draft(
        "opencode", "opencode", "openrouter/free-model", ProjectModel()
    )

    message_call = next(call for call in calls if call[0].endswith("/message"))
    assert message_call[1]["tools"] == {"*": False}
    assert result.summary == "A review-only result."
    assert calls[-1][0] == "/session/session-123"
    assert calls[-1][2] == "DELETE"
    message_call = next(call for call in calls if call[0].endswith("/message"))
    assert message_call[3] == analysis.ANALYSIS_TIMEOUT_SECONDS


def test_custom_compatible_provider_requires_https_or_loopback(monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_COMPAT_BASE_URL", "http://example.com/v1")
    monkeypatch.setenv("VIRTUE_WISE_COMPAT_API_KEY", "test-key")
    monkeypatch.setenv("VIRTUE_WISE_COMPAT_MODELS", "model-a")

    with pytest.raises(analysis.AnalysisUnavailable, match="HTTPS"):
        analysis._compatible_config()


def test_analysis_status_lists_provider_catalog_without_exposing_secrets(monkeypatch):
    catalog = [
        {
            "id": "openrouter",
            "label": "OpenRouter",
            "available": True,
            "models": [{"id": "free-model", "label": "Free model", "free": True}],
            "note": "Free models only.",
        }
    ]
    monkeypatch.setenv("OPENROUTER_API_KEY", "do-not-return-this")
    monkeypatch.setattr(analysis, "list_provider_catalog", lambda: catalog)

    response = TestClient(app).get("/api/analysis/status")

    assert response.status_code == 200
    assert response.json()["providers"] == catalog
    assert "do-not-return-this" not in response.text


def test_openrouter_analysis_uses_selected_free_model_and_bounded_json_output(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setattr(
        analysis,
        "_openrouter_free_models",
        lambda _key: [{"id": "vendor/model:free", "label": "Free model", "free": True}],
    )
    calls = []

    def fake_request(url, payload=None, *, headers=None, timeout=None, method=None):
        calls.append((url, payload, headers, timeout, method))
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "summary": "A tentative analysis.",
                                "hypotheses": [],
                                "missing_information": [],
                                "questions": [],
                                "experiments": [],
                                "scenarios": [],
                            }
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(analysis, "_request_provider_json", fake_request)

    result = analysis.create_analysis_draft(
        "Try to understand this.", "openrouter", "vendor/model:free", ProjectModel()
    )

    assert result.summary == "A tentative analysis."
    url, payload, headers, timeout, method = calls[0]
    assert url == analysis.OPENROUTER_CHAT_URL
    assert payload["model"] == "vendor/model:free"
    assert payload["max_tokens"] == 4096
    assert payload["response_format"] == {"type": "json_object"}
    assert headers == {"Authorization": "Bearer test-openrouter-key"}
    assert timeout == analysis.ANALYSIS_TIMEOUT_SECONDS
    assert method is None
