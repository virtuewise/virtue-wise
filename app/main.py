"""HTTP API and static interface for the VIRTUE WISE prototype."""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Response, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import store
from app.models import Hypothesis, ProjectModel, Scenario, Statement, now_utc

STATIC_DIR = Path(__file__).parent / "static"


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    status: str
    note: str = Field(default="", max_length=2000)


class HypothesisUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    claim: str = Field(min_length=1, max_length=2000)
    rationale: str = Field(default="", max_length=2000)
    evidence_statement_ids: list[str] = Field(default_factory=list, max_length=100)
    uncertainty: str = "unknown"


class ScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    assumptions: list[str] = Field(default_factory=list, max_length=100)
    expected_outcome: str = Field(default="", max_length=2000)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application lifecycle hook; storage initializes lazily."""
    yield


app = FastAPI(
    title="VIRTUE WISE",
    description="A local-first, evidence-aware project model prototype.",
    version="0.2.0",
    lifespan=lifespan,
)

# The supported deployment is loopback-only. Reject arbitrary Host headers to
# reduce DNS-rebinding and host-header attack surface; "testserver" is for tests.
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"],
)


def _same_origin(source: str, request, *, is_referer: bool = False) -> bool:
    """Compare an Origin or Referer origin with the request's own origin."""
    try:
        supplied = urlsplit(source)
        expected = urlsplit(str(request.base_url))
        supplied_port = supplied.port
        expected_port = expected.port
    except ValueError:
        return False

    if (
        supplied.scheme not in {"http", "https"}
        or not supplied.hostname
        or supplied.username is not None
        or supplied.password is not None
    ):
        return False
    if not is_referer and (supplied.path not in {"", "/"} or supplied.query or supplied.fragment):
        return False

    def effective_port(parsed, port):
        return port or (443 if parsed.scheme == "https" else 80)

    return (
        supplied.scheme.lower() == expected.scheme.lower()
        and supplied.hostname.lower() == (expected.hostname or "").lower()
        and effective_port(supplied, supplied_port) == effective_port(expected, expected_port)
    )


@app.middleware("http")
async def enforce_request_origin(request, call_next):
    """Reject cross-origin browser signals on state-changing requests."""
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
            return JSONResponse(
                status_code=403, content={"detail": "Cross-origin request rejected."}
            )

        origin = request.headers.get("origin")
        is_referer = False
        if origin is None:
            origin = request.headers.get("referer")
            is_referer = origin is not None
        if origin is not None and not _same_origin(origin, request, is_referer=is_referer):
            return JSONResponse(
                status_code=403, content={"detail": "Cross-origin request rejected."}
            )

    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request, call_next):
    """Apply conservative browser security headers to every HTTP response."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response


def save_validated_model(model: ProjectModel) -> ProjectModel:
    """Revalidate mutable model state before persisting it."""
    try:
        validated = ProjectModel.model_validate(model.model_dump(mode="python"))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid model: {exc}") from exc
    return store.save_model(validated)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "application": "virtue-wise"}


@app.get("/api/model", response_model=ProjectModel)
def get_model() -> ProjectModel:
    return store.load_model()


@app.put("/api/model", response_model=ProjectModel)
def replace_model(model: ProjectModel) -> ProjectModel:
    return save_validated_model(model)


@app.put("/api/import", response_model=ProjectModel)
async def import_model(upload: UploadFile) -> ProjectModel:
    """Validate a versioned JSON upload before replacing the current local model."""
    if upload.content_type not in {"application/json", "text/json", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Upload a JSON file.")
    raw = await upload.read(2_000_001)
    if len(raw) > 2_000_000:
        raise HTTPException(status_code=413, detail="JSON import must be 2 MB or smaller.")
    try:
        payload = json.loads(raw)
        model = ProjectModel.model_validate(payload)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid VIRTUE WISE model: {exc}") from exc
    return save_validated_model(model)


@app.post("/api/statements", response_model=ProjectModel, status_code=201)
def add_statement(statement: Statement) -> ProjectModel:
    model = store.load_model()
    if any(item.id == statement.id for item in model.statements):
        raise HTTPException(status_code=409, detail="A statement with this ID already exists.")
    model.statements.append(statement)
    return save_validated_model(model)


@app.put("/api/statements/{statement_id}", response_model=ProjectModel)
def update_statement(statement_id: str, statement: Statement) -> ProjectModel:
    model = store.load_model()
    index = next((i for i, item in enumerate(model.statements) if item.id == statement_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Statement not found.")
    if statement.id != statement_id:
        raise HTTPException(status_code=422, detail="Statement ID cannot be changed.")
    previous = model.statements[index]
    statement.created_at = previous.created_at
    changed = any(
        getattr(previous, field) != getattr(statement, field)
        for field in ("text", "source_label", "source_excerpt")
    )
    model.statements[index] = statement
    if changed:
        for hypothesis in model.hypotheses:
            if statement_id in hypothesis.evidence_statement_ids:
                hypothesis.review_status = "proposed"
                hypothesis.review_note = ""
                hypothesis.reviewed_at = None
    return save_validated_model(model)


@app.delete("/api/statements/{statement_id}", status_code=204)
def delete_statement(statement_id: str) -> Response:
    model = store.load_model()
    if not any(item.id == statement_id for item in model.statements):
        raise HTTPException(status_code=404, detail="Statement not found.")
    if any(statement_id in item.evidence_statement_ids for item in model.hypotheses):
        raise HTTPException(
            status_code=409,
            detail=(
                "This statement is linked to a hypothesis. "
                "Remove its evidence links before deleting it."
            ),
        )
    model.statements = [item for item in model.statements if item.id != statement_id]
    save_validated_model(model)
    return Response(status_code=204)


@app.post("/api/hypotheses", response_model=ProjectModel, status_code=201)
def add_hypothesis(hypothesis: Hypothesis) -> ProjectModel:
    model = store.load_model()
    if any(item.id == hypothesis.id for item in model.hypotheses):
        raise HTTPException(status_code=409, detail="A hypothesis with this ID already exists.")
    known_ids = {statement.id for statement in model.statements}
    if set(hypothesis.evidence_statement_ids) - known_ids:
        raise HTTPException(status_code=422, detail="Evidence must reference existing statements.")
    if len(hypothesis.evidence_statement_ids) != len(set(hypothesis.evidence_statement_ids)):
        raise HTTPException(status_code=422, detail="Evidence links must be unique.")
    model.hypotheses.append(hypothesis)
    return save_validated_model(model)


@app.put("/api/hypotheses/{hypothesis_id}", response_model=ProjectModel)
def update_hypothesis(hypothesis_id: str, update: HypothesisUpdate) -> ProjectModel:
    model = store.load_model()
    hypothesis = next((item for item in model.hypotheses if item.id == hypothesis_id), None)
    if hypothesis is None:
        raise HTTPException(status_code=404, detail="Hypothesis not found.")
    if update.uncertainty not in {"unknown", "tentative", "supported"}:
        raise HTTPException(status_code=422, detail="Unknown uncertainty label.")
    known_ids = {statement.id for statement in model.statements}
    if set(update.evidence_statement_ids) - known_ids:
        raise HTTPException(status_code=422, detail="Evidence must reference existing statements.")
    if len(update.evidence_statement_ids) != len(set(update.evidence_statement_ids)):
        raise HTTPException(status_code=422, detail="Evidence links must be unique.")
    changed = any(
        (
            hypothesis.claim != update.claim,
            hypothesis.rationale != update.rationale,
            hypothesis.evidence_statement_ids != update.evidence_statement_ids,
            hypothesis.uncertainty != update.uncertainty,
        )
    )
    hypothesis.claim = update.claim
    hypothesis.rationale = update.rationale
    hypothesis.evidence_statement_ids = update.evidence_statement_ids
    hypothesis.uncertainty = update.uncertainty
    if changed:
        hypothesis.review_status = "proposed"
        hypothesis.review_note = ""
        hypothesis.reviewed_at = None
    return save_validated_model(model)


@app.patch("/api/hypotheses/{hypothesis_id}/review", response_model=ProjectModel)
def review_hypothesis(hypothesis_id: str, request: ReviewRequest) -> ProjectModel:
    allowed = {"accepted", "revised", "rejected"}
    if request.status not in allowed:
        raise HTTPException(
            status_code=422, detail=f"Status must be one of: {', '.join(sorted(allowed))}."
        )
    model = store.load_model()
    hypothesis = next((item for item in model.hypotheses if item.id == hypothesis_id), None)
    if hypothesis is None:
        raise HTTPException(status_code=404, detail="Hypothesis not found.")
    hypothesis.review_status = request.status
    hypothesis.review_note = request.note
    hypothesis.reviewed_at = now_utc()
    return save_validated_model(model)


@app.post("/api/scenarios", response_model=ProjectModel, status_code=201)
def add_scenario(scenario: Scenario) -> ProjectModel:
    model = store.load_model()
    if any(item.id == scenario.id for item in model.scenarios):
        raise HTTPException(status_code=409, detail="A scenario with this ID already exists.")
    model.scenarios.append(scenario)
    return save_validated_model(model)


@app.put("/api/scenarios/{scenario_id}", response_model=ProjectModel)
def update_scenario(scenario_id: str, update: ScenarioInput) -> ProjectModel:
    model = store.load_model()
    scenario = next((item for item in model.scenarios if item.id == scenario_id), None)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    scenario.name = update.name
    scenario.assumptions = update.assumptions
    scenario.expected_outcome = update.expected_outcome
    return save_validated_model(model)


@app.delete("/api/scenarios/{scenario_id}", status_code=204)
def delete_scenario(scenario_id: str) -> Response:
    model = store.load_model()
    if not any(item.id == scenario_id for item in model.scenarios):
        raise HTTPException(status_code=404, detail="Scenario not found.")
    model.scenarios = [item for item in model.scenarios if item.id != scenario_id]
    save_validated_model(model)
    return Response(status_code=204)


@app.get("/api/export")
def export_model() -> JSONResponse:
    model = store.load_model()
    return JSONResponse(
        content=model.model_dump(mode="json"),
        headers={"Content-Disposition": 'attachment; filename="virtue-wise-model.json"'},
    )


@app.delete("/api/model", status_code=204)
def remove_model() -> None:
    store.delete_model()
