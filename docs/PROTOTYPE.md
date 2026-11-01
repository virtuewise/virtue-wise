# First prototype: scope and technical decisions

## Objective

Validate a low-risk project-planning workflow in which a person can enter information, inspect provenance, review hypotheses, compare alternatives, and retain control over the local data.

## Implemented in this prototype

1. Create and edit a project goal.
2. Add, edit, and delete user-provided statements with source labels and optional excerpts.
3. Create and edit hypotheses with explicit uncertainty and links to evidence statements.
4. Accept, revise, or reject a hypothesis while retaining the original statements and review note.
5. Create, edit, delete, and compare at least two named scenarios using visible assumptions and expected outcomes.
6. Export a versioned JSON model, validate an imported JSON model before replacement, and delete local data.

## Technical choices

| Layer | Decision | Reason |
| --- | --- | --- |
| Runtime | Python 3.12 or newer | Readable core logic and broad tooling support |
| API | FastAPI | Small typed HTTP API and built-in local API documentation |
| Schema validation | Pydantic v2 | Validate input and serialized model boundaries |
| Storage | SQLite via Python's standard library | Local-first persistence without a separate database service |
| Interface | Server-served HTML, CSS, and vanilla JavaScript | Small UI without a separate frontend build system |
| Tests | pytest and FastAPI TestClient | Focused API and behavior tests |
| Style and lint | Ruff | One fast tool for Python linting and formatting checks |
| Data interchange | Versioned JSON | Human-inspectable and portable export format |

These are provisional engineering choices, not a promise of long-term API stability.

## Core data concepts

- **Project model:** goal, statements, hypotheses, scenarios, timestamps, and schema version.
- **Statement:** user-provided text, source label, optional excerpt, and timestamp.
- **Hypothesis:** candidate claim, rationale, evidence statement IDs, qualitative uncertainty, and explicit review state.
- **Scenario:** name, assumptions, and expected outcome/trade-offs.
- **Evidence link:** references an existing statement by stable ID.

A hypothesis must never silently become a verified fact after acceptance. The review decision is recorded explicitly. Duplicate IDs and dangling evidence references are rejected by model validation.

## Inference policy

The prototype uses user-created hypotheses and does not require an external language model. Qualitative labels—unknown, tentative, and supported—are not calibrated probabilities. Scenario comparison is descriptive and does not claim causal discovery or reliable prediction.

## Privacy and safety boundaries

- Run locally during initial development; no telemetry is included.
- Use fictional or non-sensitive sample data.
- Do not connect email, calendars, cloud drives, or external accounts in this milestone.
- Export and deletion are part of the interface.
- Imported data is validated before replacing the current model.
- The local database is not encrypted and the app has no authentication. Do not expose it to an untrusted network.
- Scenario results are exploratory, not predictions or professional advice.

## Acceptance criteria

- [x] Create and edit the project through the interface.
- [x] Keep statements separate from hypotheses.
- [x] Trace hypotheses to evidence or mark them as lacking evidence.
- [x] Accept, revise, or reject a hypothesis without rewriting source statements.
- [x] Compare alternatives with assumptions and expected outcomes visible.
- [x] Export and validate JSON imports, including evidence references.
- [x] Delete the local model.
- [x] Automated API tests cover provenance, review, scenarios, import validation, export, and deletion.
- [ ] Conduct a manual end-to-end acceptance walkthrough on a clean checkout.
- [ ] Complete a dedicated accessibility review with keyboard and screen-reader testing.

## Deliberately out of scope

- Foundation-model training or mandatory paid API calls
- Multi-user collaboration, accounts, or cloud synchronization
- External account integrations or autonomous actions
- Claims of causal discovery or reliable future prediction
- Stable public API guarantees before the data model has been evaluated
- Authentication, encryption at rest, and production deployment hardening
