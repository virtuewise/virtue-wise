"""Validated domain models for the first VIRTUE WISE prototype."""

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def now_utc() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class StrictModel(BaseModel):
    """Shared validation settings for API and persisted data."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Statement(StrictModel):
    """A user-entered statement kept separate from hypotheses."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str = Field(min_length=1, max_length=2000)
    source_label: str = Field(default="User provided", min_length=1, max_length=300)
    source_excerpt: str | None = Field(default=None, max_length=2000)
    status: Literal["user_provided"] = "user_provided"
    created_at: datetime = Field(default_factory=now_utc)


class Hypothesis(StrictModel):
    """A reviewable candidate relationship, never silently converted to a fact."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    claim: str = Field(min_length=1, max_length=2000)
    rationale: str = Field(default="", max_length=2000)
    evidence_statement_ids: list[str] = Field(default_factory=list, max_length=100)
    uncertainty: Literal["unknown", "tentative", "supported"] = "unknown"
    review_status: Literal["proposed", "accepted", "revised", "rejected"] = "proposed"
    review_note: str = Field(default="", max_length=2000)
    created_at: datetime = Field(default_factory=now_utc)
    reviewed_at: datetime | None = None


class Scenario(StrictModel):
    """A simple alternative with explicit assumptions for later comparison."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(min_length=1, max_length=200)
    assumptions: list[str] = Field(default_factory=list, max_length=100)
    expected_outcome: str = Field(default="", max_length=2000)


class ProjectModel(StrictModel):
    """The locally stored, versioned project model."""

    schema_version: Literal[1] = 1
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(default="Untitled project", min_length=1, max_length=200)
    goal: str = Field(default="", max_length=2000)
    statements: list[Statement] = Field(default_factory=list, max_length=5000)
    hypotheses: list[Hypothesis] = Field(default_factory=list, max_length=2000)
    scenarios: list[Scenario] = Field(default_factory=list, max_length=100)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
