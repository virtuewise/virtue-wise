"""HTTP API and static interface for the VIRTUE WISE prototype."""

import asyncio
import json
import sqlite3
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Header, HTTPException, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import analysis, store
from app.models import Hypothesis, ProjectModel, Scenario, Statement, now_utc

STATIC_DIR = Path(__file__).parent / "static"
MAX_IMPORT_BYTES = 2_000_000
MAX_IMPORT_REQUEST_BYTES = 2_100_000
IMPORT_BODY_TIMEOUT_SECONDS = 30
IMPORT_SLOT_WAIT_SECONDS = 1
MAX_CONCURRENT_IMPORTS = 2
MUTATION_LOCK_TIMEOUT_SECONDS = 10
_MUTATION_LOCK = threading.Lock()
_IMPORT_LOCK = threading.BoundedSemaphore(MAX_CONCURRENT_IMPORTS)
_ANALYSIS_LOCK = threading.BoundedSemaphore(1)


def _unique_json_object(pairs):
    """Reject ambiguous JSON objects containing duplicate member names."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key.")
        result[key] = value
    return result


def _reject_json_constant(value):
    """Reject non-standard NaN and Infinity tokens accepted by Python's JSON parser."""
    raise ValueError(f"Invalid JSON numeric constant: {value}")


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


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=2000)
    model: str = Field(min_length=1, max_length=100)
    consent: bool = False


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
async def serialize_mutations(request, call_next):
    """Serialize state-changing requests within this single application process."""
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"} or request.url.path == "/api/analysis/draft":
        return await call_next(request)

    acquired = await asyncio.to_thread(_MUTATION_LOCK.acquire, True, MUTATION_LOCK_TIMEOUT_SECONDS)
    if not acquired:
        return JSONResponse(
            status_code=503,
            content={"detail": "Another update is in progress. Retry the request."},
        )
    try:
        return await call_next(request)
    finally:
        _MUTATION_LOCK.release()


@app.middleware("http")
async def limit_import_request_size(request: Request, call_next):
    """Bound import bytes, upload duration, and in-process concurrent imports."""
    if request.method != "PUT" or request.url.path != "/api/import":
        return await call_next(request)

    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            size = int(declared)
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid request size."})
        if size < 0:
            return JSONResponse(status_code=400, content={"detail": "Invalid request size."})
        if size > MAX_IMPORT_REQUEST_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Import request must be 2.1 MB or smaller."},
            )

    acquired = await asyncio.to_thread(_IMPORT_LOCK.acquire, True, IMPORT_SLOT_WAIT_SECONDS)
    if not acquired:
        return JSONResponse(
            status_code=503,
            content={"detail": "Import capacity is busy. Retry the request."},
            headers={"Retry-After": "1"},
        )

    try:
        chunks: list[dict] = []
        total = 0
        try:
            async with asyncio.timeout(IMPORT_BODY_TIMEOUT_SECONDS):
                while True:
                    message = await request.receive()
                    if message["type"] == "http.disconnect":
                        return Response(status_code=400)
                    chunk = message.get("body", b"")
                    total += len(chunk)
                    if total > MAX_IMPORT_REQUEST_BYTES:
                        return JSONResponse(
                            status_code=413,
                            content={"detail": "Import request must be 2.1 MB or smaller."},
                        )
                    chunks.append(message)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            return JSONResponse(
                status_code=408,
                content={"detail": "Import upload timed out. Retry the request."},
            )

        index = 0

        async def replay():
            nonlocal index
            if index < len(chunks):
                message = chunks[index]
                index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        request._receive = replay
        return await call_next(request)
    finally:
        _IMPORT_LOCK.release()


@app.middleware("http")
async def limit_analysis_request_size(request: Request, call_next):
    """Bound the small user-supplied body for optional local model analysis."""
    if request.method != "POST" or request.url.path != "/api/analysis/draft":
        return await call_next(request)

    max_bytes = 16_384
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            size = int(declared)
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid request size."})
        if size < 0:
            return JSONResponse(status_code=400, content={"detail": "Invalid request size."})
        if size > max_bytes:
            return JSONResponse(status_code=413, content={"detail": "Analysis request is too large."})

    chunks: list[dict] = []
    total = 0
    try:
        async with asyncio.timeout(10):
            while True:
                message = await request.receive()
                if message["type"] == "http.disconnect":
                    return Response(status_code=400)
                total += len(message.get("body", b""))
                if total > max_bytes:
                    return JSONResponse(status_code=413, content={"detail": "Analysis request is too large."})
                chunks.append(message)
                if not message.get("more_body", False):
                    break
    except TimeoutError:
        return JSONResponse(status_code=408, content={"detail": "Analysis request timed out."})

    index = 0

    async def replay():
        nonlocal index
        if index < len(chunks):
            message = chunks[index]
            index += 1
            return message
        return {"type": "http.request", "body": b"", "more_body": False}

    request._receive = replay
    return await call_next(request)


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
    if request.url.path.startswith("/api/") or request.url.path == "/ready":
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def sanitized_validation_error(request: Request, exc: RequestValidationError):
    """Return validation locations and messages without echoing submitted values."""
    errors = [
        {
            "loc": error.get("loc", ()),
            "msg": error.get("msg", "Invalid value."),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


def _set_model_etag(response: Response, model: ProjectModel) -> None:
    """Expose the exact persisted model revision to browser/API clients."""
    response.headers["ETag"] = f'"{store.revision_for_model(model)}"'


def save_validated_model(model: ProjectModel, response: Response | None = None) -> ProjectModel:
    """Revalidate mutable model state before persisting it."""
    try:
        validated = ProjectModel.model_validate(model.model_dump(mode="python"))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Model failed integrity validation.") from exc
    try:
        saved = store.save_model(validated)
        if response is not None:
            _set_model_etag(response, saved)
        return saved
    except store.StoreBusyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def save_validated_model_if_current(
    model: ProjectModel, if_match: str | None, response: Response | None = None
) -> ProjectModel:
    """Validate and atomically replace only the revision the caller observed."""
    if if_match is None:
        raise HTTPException(
            status_code=428, detail="If-Match is required. Reload the project first."
        )
    entity_tag = if_match.strip()
    if not (entity_tag.startswith('"') and entity_tag.endswith('"')):
        raise HTTPException(
            status_code=400, detail="A single strong If-Match revision is required."
        )
    revision = entity_tag[1:-1]
    if revision != "empty" and (
        len(revision) != 64 or any(character not in "0123456789abcdef" for character in revision)
    ):
        raise HTTPException(
            status_code=400, detail="A single strong If-Match revision is required."
        )
    try:
        validated = ProjectModel.model_validate(model.model_dump(mode="python"))
        saved = store.save_model_if_current(validated, revision)
        if response is not None:
            _set_model_etag(response, saved)
        return saved
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Model failed integrity validation.") from exc
    except store.StoreConflictError as exc:
        raise HTTPException(status_code=412, detail=str(exc)) from exc
    except store.StoreBusyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def mutate_validated_model(mutator, response: Response | None = None) -> ProjectModel:
    """Apply a model change inside a database-backed write transaction."""
    try:
        saved = store.mutate_model(mutator)
        if response is not None:
            _set_model_etag(response, saved)
        return saved
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Model failed integrity validation.") from exc
    except store.StoreBusyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "application": "virtue-wise"}


@app.get("/ready")
def readiness() -> dict[str, str]:
    """Report readiness only when SQLite and the persisted model can be read."""
    try:
        store.check_database()
    except store.StoreBusyError as exc:
        raise HTTPException(status_code=503, detail="Project storage is busy.") from exc
    except (sqlite3.Error, OSError, ValidationError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Project storage is not ready.") from exc
    return {"status": "ready", "storage": "ok"}


@app.get("/api/analysis/status")
def analysis_status() -> dict:
    """Check only the local Ollama model list; no project content is transmitted."""
    try:
        models = analysis.list_models()
    except analysis.AnalysisError:
        return {
            "available": False,
            "models": [],
            "message": "Local Ollama was not detected. Start Ollama on this computer to enable local analysis.",
        }
    return {"available": True, "models": models, "message": "Local Ollama is available."}


@app.post("/api/analysis/draft")
def create_analysis_draft(request: AnalysisRequest) -> dict:
    """Generate review-only suggestions using a user-confirmed local model."""
    if not request.consent:
        raise HTTPException(
            status_code=400,
            detail="Confirm that this text and the current workspace may be processed by your local Ollama model.",
        )
    acquired = _ANALYSIS_LOCK.acquire(timeout=1)
    if not acquired:
        raise HTTPException(status_code=503, detail="A local analysis is already running. Retry shortly.")
    try:
        model = store.load_model()
        draft = analysis.create_analysis_draft(request.text, request.model, model)
        return draft.model_dump(mode="json")
    except analysis.AnalysisUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except analysis.AnalysisTimeout as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except analysis.AnalysisInvalidResponse as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        _ANALYSIS_LOCK.release()


@app.get("/api/model", response_model=ProjectModel)
def get_model(response: Response) -> ProjectModel:
    model, revision = store.load_model_with_revision()
    response.headers["ETag"] = f'"{revision}"'
    return model


@app.put("/api/model", response_model=ProjectModel)
def replace_model(
    model: ProjectModel,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> ProjectModel:
    return save_validated_model_if_current(model, if_match, response)


@app.put("/api/import", response_model=ProjectModel)
async def import_model(
    upload: UploadFile,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> ProjectModel:
    """Validate a versioned JSON upload before replacing the current local model."""
    if upload.content_type not in {"application/json", "text/json", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Upload a JSON file.")
    raw = await upload.read(MAX_IMPORT_BYTES + 1)
    if len(raw) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="JSON import must be 2 MB or smaller.")
    try:
        text = raw.decode("utf-8")
        payload = json.loads(
            text,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise HTTPException(
            status_code=422,
            detail="Upload must contain valid UTF-8 JSON without duplicate object keys.",
        ) from exc
    try:
        model = ProjectModel.model_validate(payload)
    except (ValidationError, RecursionError) as exc:
        raise HTTPException(
            status_code=422,
            detail="JSON does not match the supported VIRTUE WISE model schema.",
        ) from exc
    return save_validated_model_if_current(model, if_match, response)


@app.post("/api/statements", response_model=ProjectModel, status_code=201)
def add_statement(statement: Statement, response: Response) -> ProjectModel:
    def mutate(model: ProjectModel) -> None:
        if any(item.id == statement.id for item in model.statements):
            raise HTTPException(status_code=409, detail="A statement with this ID already exists.")
        model.statements.append(statement)

    return mutate_validated_model(mutate, response)


@app.put("/api/statements/{statement_id}", response_model=ProjectModel)
def update_statement(statement_id: str, statement: Statement, response: Response) -> ProjectModel:
    def mutate(model: ProjectModel) -> None:
        index = next(
            (i for i, item in enumerate(model.statements) if item.id == statement_id), None
        )
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

    return mutate_validated_model(mutate, response)


@app.delete("/api/statements/{statement_id}", status_code=204)
def delete_statement(statement_id: str, response: Response) -> Response:
    def mutate(model: ProjectModel) -> None:
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

    mutate_validated_model(mutate, response)
    response.status_code = 204
    return response


@app.post("/api/hypotheses", response_model=ProjectModel, status_code=201)
def add_hypothesis(hypothesis: Hypothesis, response: Response) -> ProjectModel:
    def mutate(model: ProjectModel) -> None:
        if any(item.id == hypothesis.id for item in model.hypotheses):
            raise HTTPException(status_code=409, detail="A hypothesis with this ID already exists.")
        known_ids = {statement.id for statement in model.statements}
        if set(hypothesis.evidence_statement_ids) - known_ids:
            raise HTTPException(
                status_code=422, detail="Evidence must reference existing statements."
            )
        if len(hypothesis.evidence_statement_ids) != len(set(hypothesis.evidence_statement_ids)):
            raise HTTPException(status_code=422, detail="Evidence links must be unique.")
        model.hypotheses.append(hypothesis)

    return mutate_validated_model(mutate, response)


@app.put("/api/hypotheses/{hypothesis_id}", response_model=ProjectModel)
def update_hypothesis(
    hypothesis_id: str, update: HypothesisUpdate, response: Response
) -> ProjectModel:
    def mutate(model: ProjectModel) -> None:
        hypothesis = next((item for item in model.hypotheses if item.id == hypothesis_id), None)
        if hypothesis is None:
            raise HTTPException(status_code=404, detail="Hypothesis not found.")
        if update.uncertainty not in {"unknown", "tentative", "supported"}:
            raise HTTPException(status_code=422, detail="Unknown uncertainty label.")
        known_ids = {statement.id for statement in model.statements}
        if set(update.evidence_statement_ids) - known_ids:
            raise HTTPException(
                status_code=422, detail="Evidence must reference existing statements."
            )
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

    return mutate_validated_model(mutate, response)


@app.patch("/api/hypotheses/{hypothesis_id}/review", response_model=ProjectModel)
def review_hypothesis(
    hypothesis_id: str, request: ReviewRequest, response: Response
) -> ProjectModel:
    allowed = {"accepted", "revised", "rejected"}
    if request.status not in allowed:
        raise HTTPException(
            status_code=422, detail=f"Status must be one of: {', '.join(sorted(allowed))}."
        )

    def mutate(model: ProjectModel) -> None:
        hypothesis = next((item for item in model.hypotheses if item.id == hypothesis_id), None)
        if hypothesis is None:
            raise HTTPException(status_code=404, detail="Hypothesis not found.")
        hypothesis.review_status = request.status
        hypothesis.review_note = request.note
        hypothesis.reviewed_at = now_utc()

    return mutate_validated_model(mutate, response)


@app.post("/api/scenarios", response_model=ProjectModel, status_code=201)
def add_scenario(scenario: Scenario, response: Response) -> ProjectModel:
    def mutate(model: ProjectModel) -> None:
        if any(item.id == scenario.id for item in model.scenarios):
            raise HTTPException(status_code=409, detail="A scenario with this ID already exists.")
        model.scenarios.append(scenario)

    return mutate_validated_model(mutate, response)


@app.put("/api/scenarios/{scenario_id}", response_model=ProjectModel)
def update_scenario(scenario_id: str, update: ScenarioInput, response: Response) -> ProjectModel:
    def mutate(model: ProjectModel) -> None:
        scenario = next((item for item in model.scenarios if item.id == scenario_id), None)
        if scenario is None:
            raise HTTPException(status_code=404, detail="Scenario not found.")
        scenario.name = update.name
        scenario.assumptions = update.assumptions
        scenario.expected_outcome = update.expected_outcome

    return mutate_validated_model(mutate, response)


@app.delete("/api/scenarios/{scenario_id}", status_code=204)
def delete_scenario(scenario_id: str, response: Response) -> Response:
    def mutate(model: ProjectModel) -> None:
        if not any(item.id == scenario_id for item in model.scenarios):
            raise HTTPException(status_code=404, detail="Scenario not found.")
        model.scenarios = [item for item in model.scenarios if item.id != scenario_id]

    mutate_validated_model(mutate, response)
    response.status_code = 204
    return response


@app.get("/api/export")
def export_model() -> JSONResponse:
    model = store.load_model()
    return JSONResponse(
        content=model.model_dump(mode="json"),
        headers={"Content-Disposition": 'attachment; filename="virtue-wise-model.json"'},
    )


@app.delete("/api/model", status_code=204)
def remove_model(response: Response) -> None:
    try:
        store.delete_model()
        response.headers["ETag"] = '"empty"'
    except store.StoreBusyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
