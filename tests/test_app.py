"""Behavioral tests for the VIRTUE WISE prototype API."""

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import Request
from fastapi.testclient import TestClient

from app import store
from app.main import app
from app.models import Statement


def test_client(tmp_path, monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_DB", str(tmp_path / "test.sqlite3"))
    return TestClient(app)


def put_with_revision(client, path, *args, **kwargs):
    """Send a replacement/import using the current server revision."""
    headers = dict(kwargs.pop("headers", {}))
    headers["If-Match"] = client.get("/api/model").headers["etag"]
    return client.put(path, *args, headers=headers, **kwargs)


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


def test_statement_edit_and_delete_guards(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    created = client.post("/api/statements", json={"text": "Original statement"})
    statement = created.json()["statements"][0]
    edited = client.put(
        f"/api/statements/{statement['id']}",
        json={**statement, "text": "Corrected statement"},
    )
    assert edited.status_code == 200
    assert edited.json()["statements"][0]["text"] == "Corrected statement"

    hypothesis = client.post(
        "/api/hypotheses",
        json={"claim": "A possibility", "evidence_statement_ids": [statement["id"]]},
    ).json()["hypotheses"][0]
    blocked = client.delete(f"/api/statements/{statement['id']}")
    assert blocked.status_code == 409

    client.put(
        f"/api/hypotheses/{hypothesis['id']}",
        json={
            "claim": hypothesis["claim"],
            "rationale": "",
            "evidence_statement_ids": [],
            "uncertainty": "unknown",
        },
    )
    assert client.delete(f"/api/statements/{statement['id']}").status_code == 204
    assert client.delete(f"/api/statements/{statement['id']}").status_code == 404


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


def test_editing_reviewed_evidence_reopens_hypothesis_review(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    statement = client.post(
        "/api/statements",
        json={"text": "Initial observation", "source_label": "Planning notes"},
    ).json()["statements"][0]
    hypothesis = client.post(
        "/api/hypotheses",
        json={
            "claim": "A candidate explanation",
            "evidence_statement_ids": [statement["id"]],
        },
    ).json()["hypotheses"][0]
    reviewed = client.patch(
        f"/api/hypotheses/{hypothesis['id']}/review",
        json={"status": "accepted", "note": "Reviewed against the original note."},
    )
    assert reviewed.json()["hypotheses"][0]["review_status"] == "accepted"

    edited_statement = client.put(
        f"/api/statements/{statement['id']}",
        json={**statement, "text": "Corrected observation"},
    )
    updated_hypothesis = edited_statement.json()["hypotheses"][0]
    assert updated_hypothesis["review_status"] == "proposed"
    assert updated_hypothesis["review_note"] == ""
    assert updated_hypothesis["reviewed_at"] is None

    accepted_again = client.patch(
        f"/api/hypotheses/{hypothesis['id']}/review",
        json={"status": "accepted", "note": "Reviewed again."},
    )
    assert accepted_again.json()["hypotheses"][0]["review_status"] == "accepted"
    changed_claim = client.put(
        f"/api/hypotheses/{hypothesis['id']}",
        json={
            "claim": "A materially changed explanation",
            "rationale": "",
            "evidence_statement_ids": [statement["id"]],
            "uncertainty": "tentative",
        },
    )
    updated_hypothesis = changed_claim.json()["hypotheses"][0]
    assert updated_hypothesis["review_status"] == "proposed"
    assert updated_hypothesis["review_note"] == ""
    assert updated_hypothesis["reviewed_at"] is None


def test_scenario_create_update_delete_and_compare(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    first = client.post(
        "/api/scenarios",
        json={
            "name": "Reduce scope",
            "assumptions": ["One owner is available"],
            "expected_outcome": "Earlier feedback",
        },
    )
    second = client.post(
        "/api/scenarios",
        json={"name": "Keep scope", "assumptions": ["Capacity remains stable"]},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    scenarios = second.json()["scenarios"]
    scenario_id = scenarios[0]["id"]
    edited = client.put(
        f"/api/scenarios/{scenario_id}",
        json={
            "name": "Reduce scope carefully",
            "assumptions": ["One owner is available", "Dependencies stay stable"],
            "expected_outcome": "Earlier feedback",
        },
    )
    assert edited.status_code == 200
    assert len(edited.json()["scenarios"]) == 2
    assert edited.json()["scenarios"][0]["name"] == "Reduce scope carefully"
    assert client.delete(f"/api/scenarios/{scenario_id}").status_code == 204
    assert len(client.get("/api/model").json()["scenarios"]) == 1


def test_json_import_validates_before_replacing_model(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    put_with_revision(
        client,
        "/api/model", json={"title": "Keep this model"})
    invalid = put_with_revision(client, "/api/import",
        files={"upload": ("invalid.json", b'{"schema_version": 99}', "application/json")},
    )
    assert invalid.status_code == 422
    assert client.get("/api/model").json()["title"] == "Keep this model"

    payload = {
        "schema_version": 1,
        "title": "Imported plan",
        "statements": [{"id": "statement-1", "text": "A sourced note"}],
        "hypotheses": [
            {
                "id": "hypothesis-1",
                "claim": "A tentative link",
                "evidence_statement_ids": ["statement-1"],
            }
        ],
        "scenarios": [{"id": "scenario-1", "name": "Option A"}],
    }
    imported = put_with_revision(client, "/api/import",
        files={"upload": ("model.json", json.dumps(payload), "application/json")},
    )
    assert imported.status_code == 200
    assert imported.json()["title"] == "Imported plan"
    assert imported.json()["hypotheses"][0]["evidence_statement_ids"] == ["statement-1"]


def test_documented_demo_model_imports_and_preserves_links(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    example_path = Path(__file__).resolve().parents[1] / "examples" / "demo-project.json"
    with example_path.open("rb") as example:
        imported = put_with_revision(client, "/api/import",
            files={"upload": ("demo-project.json", example, "application/json")},
        )
    assert imported.status_code == 200
    model = imported.json()
    assert model["title"] == "Improve a small team planning cycle"
    assert len(model["statements"]) == 3
    assert len(model["hypotheses"]) == 1
    assert len(model["scenarios"]) == 2
    statement_ids = {statement["id"] for statement in model["statements"]}
    assert set(model["hypotheses"][0]["evidence_statement_ids"]) <= statement_ids


def test_import_rejects_dangling_evidence_and_oversized_upload(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    payload = {
        "schema_version": 1,
        "hypotheses": [{"claim": "Broken link", "evidence_statement_ids": ["absent"]}],
    }
    invalid = put_with_revision(client, "/api/import",
        files={"upload": ("model.json", json.dumps(payload), "application/json")},
    )
    assert invalid.status_code == 422
    oversized = put_with_revision(client, "/api/import",
        files={"upload": ("large.json", b" " * 2_000_001, "application/json")},
    )
    assert oversized.status_code == 413


def test_export_and_delete(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    put_with_revision(
        client,
        "/api/model", json={"title": "Sample plan", "goal": "Learn from a small trial"})
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


def test_duplicate_evidence_links_are_rejected_without_corrupting_saved_model(
    tmp_path, monkeypatch
):
    client = test_client(tmp_path, monkeypatch)
    statement = client.post("/api/statements", json={"text": "A sourced observation"}).json()[
        "statements"
    ][0]

    invalid = client.post(
        "/api/hypotheses",
        json={
            "claim": "A candidate explanation",
            "evidence_statement_ids": [statement["id"], statement["id"]],
        },
    )

    assert invalid.status_code == 422
    assert client.get("/api/model").json()["hypotheses"] == []


def test_duplicate_evidence_links_are_rejected_on_update_and_import(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    statement = client.post("/api/statements", json={"text": "A sourced observation"}).json()[
        "statements"
    ][0]
    hypothesis = client.post(
        "/api/hypotheses",
        json={"claim": "A candidate explanation"},
    ).json()["hypotheses"][0]

    invalid_update = client.put(
        f"/api/hypotheses/{hypothesis['id']}",
        json={
            "claim": hypothesis["claim"],
            "rationale": "",
            "evidence_statement_ids": [statement["id"], statement["id"]],
            "uncertainty": "unknown",
        },
    )
    assert invalid_update.status_code == 422
    assert client.get("/api/model").json()["hypotheses"][0]["evidence_statement_ids"] == []

    invalid_import = put_with_revision(client, "/api/import",
        files={
            "upload": (
                "duplicate-evidence.json",
                json.dumps(
                    {
                        "schema_version": 1,
                        "statements": [{"id": "s1", "text": "A source"}],
                        "hypotheses": [
                            {
                                "id": "h1",
                                "claim": "A claim",
                                "evidence_statement_ids": ["s1", "s1"],
                            }
                        ],
                    }
                ),
                "application/json",
            )
        },
    )
    assert invalid_import.status_code == 422
    assert client.get("/api/model").json()["title"] == "Untitled project"


def test_record_deletions_preserve_saved_model_when_persistence_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_DB", str(tmp_path / "delete-failure.sqlite3"))
    client = TestClient(app, raise_server_exceptions=False)
    statement = client.post("/api/statements", json={"text": "A statement to retain"}).json()[
        "statements"
    ][0]
    scenario = client.post("/api/scenarios", json={"name": "A scenario to retain"}).json()[
        "scenarios"
    ][0]

    def fail_save(_model):
        raise OSError("simulated storage failure")

    monkeypatch.setattr(store, "mutate_model", fail_save)
    statement_delete = client.delete(f"/api/statements/{statement['id']}")
    scenario_delete = client.delete(f"/api/scenarios/{scenario['id']}")

    assert statement_delete.status_code == 500
    assert scenario_delete.status_code == 500
    saved = store.load_model()
    assert [item.id for item in saved.statements] == [statement["id"]]
    assert [item.id for item in saved.scenarios] == [scenario["id"]]


def test_security_headers_are_present_on_application_responses(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    response = client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == ("camera=(), microphone=(), geolocation=()")


def test_state_changing_request_rejects_cross_origin_origin_header(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    response = put_with_revision(client, "/api/model",
        json={"title": "Should not be saved"},
        headers={"Origin": "https://attacker.example"},
    )
    assert response.status_code == 403
    assert client.get("/api/model").json()["title"] == "Untitled project"


def test_state_changing_request_accepts_matching_origin(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    response = put_with_revision(client, "/api/model",
        json={"title": "Same-origin update"},
        headers={"Origin": "http://testserver"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Same-origin update"


def test_state_changing_request_rejects_cross_site_fetch_metadata(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    response = client.delete(
        "/api/model",
        headers={"Sec-Fetch-Site": "cross-site"},
    )
    assert response.status_code == 403
    assert client.get("/api/model").status_code == 200


def test_state_changing_request_rejects_cross_origin_referer(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    response = put_with_revision(client, "/api/model",
        json={"title": "Should not be saved"},
        headers={"Referer": "https://attacker.example/form"},
    )
    assert response.status_code == 403
    assert client.get("/api/model").json()["title"] == "Untitled project"


def test_untrusted_host_header_is_rejected(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    response = client.get("/health", headers={"Host": "attacker.example"})
    assert response.status_code == 400


def test_import_rejects_invalid_utf8_and_malformed_json_without_replacing_model(
    tmp_path, monkeypatch
):
    client = test_client(tmp_path, monkeypatch)
    put_with_revision(
        client,
        "/api/model", json={"title": "Keep this model"})
    invalid_payloads = [
        b"\\xff\\xfe",
        b'{"title": "SENSITIVE-CANARY",',
        b"[" * 3000,
    ]
    for payload in invalid_payloads:
        response = put_with_revision(client, "/api/import",
            files={"upload": ("invalid.json", payload, "application/json")},
        )
        assert response.status_code == 422
        assert "SENSITIVE-CANARY" not in response.text
        assert client.get("/api/model").json()["title"] == "Keep this model"


def test_import_rejects_duplicate_keys_and_nonstandard_json_numbers(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    put_with_revision(
        client,
        "/api/model", json={"title": "Keep this model"})
    invalid_payloads = [
        b'{"schema_version": 1, "title": "first", "title": "second"}',
        b'{"schema_version": 1, "goal": NaN}',
    ]
    for payload in invalid_payloads:
        response = put_with_revision(client, "/api/import",
            files={"upload": ("ambiguous.json", payload, "application/json")},
        )
        assert response.status_code == 422
        assert client.get("/api/model").json()["title"] == "Keep this model"


def test_declared_oversized_import_request_is_rejected_before_parsing(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    response = put_with_revision(client, "/api/import",
        content=b"not a multipart body",
        headers={"Content-Length": "2100001", "Content-Type": "multipart/form-data"},
    )
    assert response.status_code == 413


def test_request_validation_errors_do_not_echo_submitted_values(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    response = client.post(
        "/api/statements",
        json={
            "text": "A valid text value",
            "source_label": "SENSITIVE-CANARY",
            "unexpected_secret": "SENSITIVE-CANARY",
        },
    )
    assert response.status_code == 422
    assert "SENSITIVE-CANARY" not in response.text
    assert "unexpected_secret" in response.text


def test_json_export_can_restore_a_deleted_model(tmp_path, monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_DB", str(tmp_path / "restore.sqlite3"))
    with TestClient(app) as client:
        statement = client.post(
            "/api/statements",
            json={"text": "A backed-up statement", "source_label": "Recovery fixture"},
        ).json()["statements"][0]
        hypothesis = client.post(
            "/api/hypotheses",
            json={
                "claim": "A backed-up hypothesis",
                "evidence_statement_ids": [statement["id"]],
            },
        ).json()["hypotheses"][0]
        client.patch(
            f"/api/hypotheses/{hypothesis['id']}/review",
            json={"status": "accepted", "note": "Verified in the fixture."},
        )
        client.post(
            "/api/scenarios",
            json={"name": "Backup scenario", "assumptions": ["A stable assumption"]},
        )

        backup = client.get("/api/export").content
        exported = json.loads(backup)
        assert client.delete("/api/model").status_code == 204
        assert client.get("/api/model").json()["statements"] == []

        restored = put_with_revision(client, "/api/import",
            files={"upload": ("backup.json", backup, "application/json")},
        )
        assert restored.status_code == 200
        model = restored.json()
        assert model["id"] == exported["id"]
        assert model["statements"][0]["id"] == statement["id"]
        assert model["hypotheses"][0]["evidence_statement_ids"] == [statement["id"]]
        assert model["hypotheses"][0]["review_status"] == "accepted"
        assert model["scenarios"][0]["name"] == "Backup scenario"


def test_concurrent_statement_creates_do_not_lose_updates(tmp_path, monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_DB", str(tmp_path / "concurrent.sqlite3"))
    with TestClient(app) as client:

        def create_statement(index):
            return client.post(
                "/api/statements",
                json={"text": f"Concurrent statement {index}"},
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            responses = list(executor.map(create_statement, range(12)))

        assert all(response.status_code == 201 for response in responses)
        saved = client.get("/api/model").json()
        assert len(saved["statements"]) == 12
        assert {item["text"] for item in saved["statements"]} == {
            f"Concurrent statement {index}" for index in range(12)
        }


def test_chunked_import_request_without_content_length_is_bounded(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    put_with_revision(
        client,
        "/api/model", json={"title": "Preserve this model"})
    boundary = "virtue-wise-boundary"
    body = (
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="upload"; filename="large.json"\r\n'
            "Content-Type: application/json\r\n\r\n"
        ).encode()
        + (b"0" * 2_100_001)
        + f"\r\n--{boundary}--\r\n".encode()
    )
    chunks = (body[index : index + 65536] for index in range(0, len(body), 65536))
    response = put_with_revision(client, "/api/import",
        content=chunks,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Transfer-Encoding": "chunked",
        },
    )
    assert response.status_code == 413
    assert client.get("/api/model").json()["title"] == "Preserve this model"


def test_database_write_transactions_serialize_independent_connections(tmp_path, monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_DB", str(tmp_path / "concurrent.sqlite3"))
    store.load_model()

    def append_statement(index):
        def mutate(model):
            model.statements.append(Statement(text=f"Concurrent statement {index}"))

        store.mutate_model(mutate)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(append_statement, range(40)))

    saved = store.load_model()
    assert len(saved.statements) == 40
    assert {item.text for item in saved.statements} == {
        f"Concurrent statement {index}" for index in range(40)
    }


def test_database_mutation_rolls_back_when_callback_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("VIRTUE_WISE_DB", str(tmp_path / "rollback.sqlite3"))
    original = store.save_model(store.load_model())

    def fail_after_mutation(model):
        model.title = "This must not persist"
        raise RuntimeError("simulated mutation failure")

    try:
        store.mutate_model(fail_after_mutation)
    except RuntimeError as exc:
        assert str(exc) == "simulated mutation failure"
    else:
        raise AssertionError("Expected mutation failure")

    restored = store.load_model()
    assert restored.id == original.id
    assert restored.title == original.title


def test_import_body_timeout_returns_408_without_replacing_model(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    put_with_revision(
        client,
        "/api/model", json={"title": "Preserve this model"})
    monkeypatch.setattr("app.main.IMPORT_BODY_TIMEOUT_SECONDS", 0.01)
    original_receive = Request.receive

    async def slow_receive(request):
        if request.url.path == "/api/import":
            await asyncio.sleep(0.05)
        return await original_receive(request)

    monkeypatch.setattr(Request, "receive", slow_receive)
    response = put_with_revision(client, "/api/import",
        files={"upload": ("backup.json", b'{"schema_version": 1}', "application/json")},
    )
    assert response.status_code == 408
    assert client.get("/api/model").json()["title"] == "Preserve this model"


def test_import_capacity_limit_returns_503(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    monkeypatch.setattr("app.main.IMPORT_SLOT_WAIT_SECONDS", 0.01)
    monkeypatch.setattr("app.main._IMPORT_LOCK", threading.BoundedSemaphore(0))
    response = put_with_revision(client, "/api/import",
        files={"upload": ("backup.json", b'{"schema_version": 1}', "application/json")},
    )
    assert response.status_code == 503
    assert response.headers["retry-after"] == "1"



def test_full_model_replacement_requires_current_revision(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    initial = client.get("/api/model")
    assert initial.headers["etag"] == '"empty"'

    saved = put_with_revision(client, "/api/model", json={"title": "Current project"})
    assert saved.status_code == 200
    current = client.get("/api/model")
    assert current.headers["etag"] == f'"{saved.json()["updated_at"]}"'

    stale = client.put(
        "/api/model",
        json={"title": "Stale replacement"},
        headers={"If-Match": initial.headers["etag"]},
    )
    assert stale.status_code == 412
    assert client.get("/api/model").json()["title"] == "Current project"

    missing = client.put("/api/model", json={"title": "No precondition"})
    assert missing.status_code == 428
    assert client.get("/api/model").json()["title"] == "Current project"


def test_import_rejects_stale_revision_without_replacing_model(tmp_path, monkeypatch):
    client = test_client(tmp_path, monkeypatch)
    stale_revision = client.get("/api/model").headers["etag"]
    created = client.post("/api/statements", json={"text": "A newer saved statement"})
    assert created.status_code == 201

    imported = client.put(
        "/api/import",
        files={
            "upload": (
                "stale.json",
                b'{"schema_version": 1, "title": "Stale import"}',
                "application/json",
            )
        },
        headers={"If-Match": stale_revision},
    )
    assert imported.status_code == 412
    saved = client.get("/api/model").json()
    assert saved["title"] == "Untitled project"
    assert saved["statements"][0]["text"] == "A newer saved statement"
