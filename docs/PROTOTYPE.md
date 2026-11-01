# First prototype: scope and technical decisions

## Objective

Validate one complete, low-risk user journey before building a broad platform:

1. Enter a goal and a small set of user-authored facts or events.
2. Store an editable, structured representation with provenance.
3. Suggest or manually create a candidate relationship and show its evidence and uncertainty.
4. Accept, revise, or reject the candidate.
5. Compare two simple alternatives using explicit assumptions.
6. Export the model as portable JSON and delete the local data.

This prototype tests whether an inspectable model is useful. It is not a general-purpose personal assistant and should not make external changes on the user's behalf.

## Initial use case

Use a small project-planning scenario with fictional or non-sensitive data. It is concrete enough to model goals, events, evidence, relationships, and alternative actions without requiring access to private accounts or high-impact personal decisions.

## Proposed stack

| Layer | Decision | Reason |
| --- | --- | --- |
| Runtime | Python 3.12 or newer | Readable core logic and broad tooling support |
| API | FastAPI | Small typed HTTP API and built-in local API documentation |
| Schema validation | Pydantic v2 | Validate input and serialized model boundaries |
| Storage | SQLite via Python's standard library | Local-first persistence without a separate database service |
| Interface | Server-served HTML, CSS, and vanilla JavaScript | Keeps the first UI small and avoids a separate frontend build system |
| Tests | pytest | Focused unit and API-level tests |
| Style and lint | Ruff | One fast tool for Python linting and formatting checks |
| Data interchange | Versioned JSON | Human-inspectable and portable export format |

These are provisional engineering choices for the first prototype, not a promise of long-term API stability. Revisit them only when a concrete limitation or evaluation result justifies it.

## Core data model

The first version should support only the following concepts:

- **Entity:** stable identifier, label, type, created/updated timestamps.
- **Statement:** subject, predicate, object or value, status, and optional time context.
- **Source:** kind, human-readable reference, capture time, and optional excerpt supplied by the user.
- **Evidence link:** connects a statement or hypothesis to one or more sources.
- **Hypothesis:** proposed relationship, rationale, uncertainty label, and review status.
- **Scenario:** named assumptions and a small set of candidate actions or outcomes.

Keep observed or user-provided statements distinct from hypotheses. A hypothesis must never silently become a verified fact after acceptance; record the user's review decision explicitly.

## Inference policy

Start with transparent, deterministic suggestions and user-created relationships. Do not require an external language model for the first milestone. If model-assisted suggestions are added later, make them optional, identify them as generated, preserve the input references, and allow users to reject them.

Do not use a numeric confidence score until its meaning can be defined and evaluated. Use qualitative labels such as unknown, tentative, and supported, with documented criteria.

## Privacy and safety boundaries

- Run locally during initial development; do not add telemetry by default.
- Use fictional or non-sensitive sample data in tests and examples.
- Do not connect email, calendars, cloud drives, or external accounts in the first milestone.
- Make export and deletion part of the acceptance criteria.
- Keep secrets out of source control and logs.
- Treat scenario results as exploratory, not predictions or professional advice.

## Acceptance criteria

The prototype is ready for review when:

- A new model can be created and edited through the interface.
- Statements and hypotheses have distinct types and status.
- A displayed hypothesis can be traced to its input evidence or clearly marked as lacking evidence.
- A user can accept, revise, or reject a hypothesis without rewriting the source statements.
- Two alternatives can be compared with assumptions visible.
- JSON export round-trips through validation.
- A user can delete the local model.
- Automated tests cover schema validation, provenance, review-state transitions, export/import, and deletion.
- Setup instructions work from a clean checkout on a supported Python version.

## Deliberately out of scope

- Foundation-model training or mandatory paid API calls
- Multi-user collaboration, accounts, or cloud synchronization
- A plugin marketplace or broad adapter framework
- Complex autonomous agents or external actions
- Claims of causal discovery or reliable future prediction
- A stable public API before the data model has been evaluated

## Implementation sequence

1. Add a minimal Python package, dependency manifest, and reproducible local setup.
2. Implement schema types and validation tests.
3. Implement local SQLite persistence and JSON export/import.
4. Add a small API and accessible single-page interface.
5. Add hypothesis review and scenario comparison.
6. Run the acceptance checklist with a documented fictional example before expanding scope.
