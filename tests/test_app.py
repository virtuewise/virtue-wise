"""Behavioral tests for the first prototype API."""

import json

from fastapi.testclient import TestClient

from app import store
from app.main import app


def test_client(tmp_path, monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_DB", str(tmp_path / "test.sqlite3"))
    return TestClient(app)


def test_health_and_empty_model(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    assert client.get("/health").json()["status"] == "ok"
    response = client.get("/api/model")
    assert response.status_code == 200
    assert response.json()["schema_version"] == 1
    assert response.json()["statements"] == []


def test_statement_and_hypothesis_provenance(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    statement = client.post(
        "/api/statements",
        json={"text": "The sample team completed two tasks", "source_label": "Planning notes"},
    )
    assert statement.status_code == 201
    statement_id = statement.json()["statements"][0]["id"]
    invalid = client.post(
        "/api/hypotheses",
        json={"claim": "More focus improves delivery", "evidence_statement_ids": ["missing-id"]},
    )
    assert invalid.status_code == 422
    valid = client.post(
        "/api/hypotheses",
        json={
            "claim": "A shorter task list may improve delivery",
            "rationale": "The example is small and not conclusive.",
            "evidence_statement_ids": [statement_id],
            "uncertainty": "tentative",
        },
    )
    assert valid.status_code == 201
    hypothesis = valid.json()["hypotheses"][0]
    assert hypothesis["evidence_statement_ids"] == [statement_id]
    assert hypothesis["review_status"] == "proposed"


def test_review_transition_does_not_change_statements(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    client.post("/api/statements", json={"text": "A user-provided observation"})
    created = client.post("/api/hypotheses", json={"claim": "A tentative explanation"})
    hypothesis_id = created.json()["hypotheses"][0]["id"]
    response = client.patch(
        f"/api/hypotheses/{hypothesis_id}/review",
        json={"status": "revised", "note": "Needs another example."},
    )
    assert response.status_code == 200
    assert response.json()["hypotheses"][0]["review_status"] == "revised"
    assert response.json()["hypotheses"][0]["review_note"] == "Needs another example."
    assert response.json()["statements"][0]["text"] == "A user-provided observation"


def test_export_and_delete(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    client.put("/api/model", json={"title": "Sample plan", "goal": "Learn from a small trial"})
    exported = client.get("/api/export")
    assert exported.status_code == 200
    assert exported.headers["content-disposition"].endswith('filename="virtue-wise-model.json"')
    assert json.loads(exported.text)["title"] == "Sample plan"
    deleted = client.delete("/api/model")
    assert deleted.status_code == 204
    assert client.get("/api/model").json()["statements"] == []


def test_store_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_DB", str(tmp_path / "roundtrip.sqlite3"))
    model = store.save_model(store.load_model())
    restored = store.load_model()
    assert restored.id == model.id
    assert restored.schema_version == 1
