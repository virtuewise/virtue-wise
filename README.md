# VIRTUE WISE

**An open foundation for evidence-aware, human-directed intelligence.**

VIRTUE WISE explores ways to help people connect information, understand the basis of an inference, represent uncertainty, and compare possible decisions—while keeping the underlying model inspectable and under the user's control.

> **Core idea:** move beyond answers alone toward understanding that can be examined, corrected, and used.

[Vision](docs/VISION.md) · [Prototype plan](docs/PROTOTYPE.md) · [Architecture](docs/ARCHITECTURE.md) · [Acceptance walkthrough](docs/ACCEPTANCE.md) · [Model evaluation protocol](docs/MODEL_EVALUATION.md) · [Threat model](docs/THREAT_MODEL.md) · [Authentication design](docs/AUTHENTICATION_DESIGN.md) · [Import security](docs/IMPORT_SECURITY.md) · [Release and recovery](docs/RELEASE_READINESS.md) · [Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

## Why this project

Information is abundant, but context is fragmented. A useful system should help people see what is known, where it came from, what is inferred, what remains uncertain, and how different choices could lead to different outcomes.

VIRTUE WISE is an open-source effort to investigate that foundation. It is not tied to one AI model or provider, and it does not assume a system should make decisions on a person's behalf.

## What is implemented

The current local-first prototype includes:

- **Project workspace:** edit a project title and goal.
- **Statements and provenance:** create, edit, and delete user-provided statements with source labels and optional excerpts.
- **Hypothesis review:** create and edit hypotheses, link them to statements, set qualitative uncertainty, and accept, revise, or reject with a review note.
- **Scenario comparison:** create, edit, and delete alternatives with explicit assumptions and expected outcomes; compare them side by side without artificial scores.
- **Portable data:** export JSON, import a validated model, and delete the saved local model.
- **Quality checks:** automated API tests and CI for Python 3.12/3.13, Ruff, and Markdown linting.

These are prototype capabilities, not claims of validated prediction or professional advice.

## Run locally

Requirements: Python 3.12 or newer.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. API documentation is available at <http://127.0.0.1:8000/docs>.

By default, SQLite data is stored at `data/virtue-wise.sqlite3`. Set `VIRTUE_WISE_DB` to use another path. The application has no authentication or encryption at rest: keep it bound to localhost and do not enter sensitive data.

Run quality checks:

```bash
ruff check app tests
ruff format --check app tests
pytest
```

## Known limitations

- Single local model in SQLite; record-level edits use database write transactions across independent local processes. Full-model replacement and import require an `If-Match` revision from the latest model read and reject stale clients with HTTP 412. Keep the database on a local filesystem; multi-host operation is unsupported. Imports have a 2.1 MB request-body cap, 30-second body-read timeout, and two-request per-process concurrency limit; upstream ingress limits are still required.
- No authentication, authorization, sessions, encryption at rest, or session-bound CSRF tokens. Basic request-origin and Host checks are defense in depth, not production hardening.
- JSON import supports the current schema version only; migrations are not implemented.
- Scenario comparison is qualitative, not a prediction engine.
- Editing uses native HTML dialog forms with labels, validation, save/cancel controls, and visible error feedback.
- Manual accessibility and end-to-end acceptance reviews remain to be completed.
- Richer entities, source records, and migrations are deferred pending the evidence-gathering process in [the model evaluation protocol](docs/MODEL_EVALUATION.md).

Try the fictional [demo model](examples/demo-project.json) and follow the [manual acceptance walkthrough](docs/ACCEPTANCE.md). Automated checks do not replace keyboard-only, screen-reader, mobile-width, zoom, and clean-checkout manual verification. See [architecture notes](docs/ARCHITECTURE.md), the [prototype specification](docs/PROTOTYPE.md), and [roadmap](ROADMAP.md) for detail.

## Project identity

The connected-node mark and usage guidance are maintained in [docs/BRAND.md](docs/BRAND.md) and [assets/virtue-wise-mark.svg](assets/virtue-wise-mark.svg).

## Contributing

Contributions are welcome across engineering, research, product design, accessibility, testing, documentation, and security.

- Start with [CONTRIBUTING.md](CONTRIBUTING.md).
- Read the [prototype plan](docs/PROTOTYPE.md) before proposing implementation choices.
- Check the [roadmap](ROADMAP.md) before proposing substantial work.
- Use the repository's issue templates to report a bug or suggest an improvement.
- For security-sensitive reports, follow [SECURITY.md](SECURITY.md).

## Project documents

| Document | Purpose |
| --- | --- |
| [Vision](docs/VISION.md) | Motivation and foundational ideas |
| [Prototype plan](docs/PROTOTYPE.md) | Scope, technical choices, acceptance criteria |
| [Architecture](docs/ARCHITECTURE.md) | Implementation, boundaries, and known limitations |
| [Acceptance walkthrough](docs/ACCEPTANCE.md) | Manual workflow and accessibility checklist |
| [Model evaluation protocol](docs/MODEL_EVALUATION.md) | Evidence-based criteria for deciding whether to expand the data model |
| [Brand guide](docs/BRAND.md) | Visual identity and documentation standards |
| [Roadmap](ROADMAP.md) | Proposed milestones |
| [Contributing](CONTRIBUTING.md) | Contribution workflow |
| [Code of Conduct](CODE_OF_CONDUCT.md) | Community standards |
| [Security](SECURITY.md) | Responsible security reporting |
| [Repository setup](REPOSITORY_SETUP.md) | Maintainer checklist |
| [License](LICENSE) | Project license |

## License

Unless otherwise stated in a specific file or directory, this project is distributed under the [MIT License](LICENSE).

---

*Understand the evidence. Make uncertainty visible. Keep people in control.*
