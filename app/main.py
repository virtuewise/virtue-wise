"""HTTP API and static interface for the VIRTUE WISE prototype."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from app import store
from app.models import Hypothesis, ProjectModel, Statement, now_utc

STATIC_DIR = Path(__file__).parent / "static"


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    status: str
    note: str = Field(default="", max_length=2000)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application lifecycle hook; storage initializes lazily."""
    yield


app = FastAPI(
    title="VIRTUE WISE",
    description="A local-first, evidence-aware project model prototype.",
    version="0.1.0",
    lifespan=lifespan,
)
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
    return store.save_model(model)


@app.post("/api/statements", response_model=ProjectModel, status_code=201)
def add_statement(statement: Statement) -> ProjectModel:
    model = store.load_model()
    model.statements.append(statement)
    return store.save_model(model)


@app.post("/api/hypotheses", response_model=ProjectModel, status_code=201)
def add_hypothesis(hypothesis: Hypothesis) -> ProjectModel:
    model = store.load_model()
    known_ids = {statement.id for statement in model.statements}
    if set(hypothesis.evidence_statement_ids) - known_ids:
        raise HTTPException(status_code=422, detail="Evidence must reference existing statements.")
    model.hypotheses.append(hypothesis)
    return store.save_model(model)


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
    return store.save_model(model)


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
