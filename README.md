# VIRTUE WISE

**An open foundation for evidence-aware, human-directed intelligence.**

VIRTUE WISE explores ways to help people connect information, understand the basis of an inference, represent uncertainty, and compare possible decisions—while keeping the underlying model inspectable and under the user's control.

> **Core idea:** move beyond answers alone toward understanding that can be examined, corrected, and used.

[Vision](docs/VISION.md) · [Prototype plan](docs/PROTOTYPE.md) · [Architecture](docs/ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

## Why this project

Information is abundant, but context is fragmented. A useful system should help people see what is known, where it came from, what is inferred, what remains uncertain, and how different choices could lead to different outcomes.

VIRTUE WISE is an open-source effort to investigate that foundation. It is not tied to one AI model or provider, and it does not assume a system should make decisions on a person's behalf.

## What we are exploring

- **Evidence and provenance** — connect claims to sources, observations, and revisions.
- **A structured world model** — represent entities, events, relationships, goals, and context.
- **Explicit uncertainty** — distinguish observed information from hypotheses, inferences, and unknowns.
- **Scenario exploration** — make assumptions and trade-offs visible when comparing possible actions.
- **Human correction** — allow people to challenge, revise, or reject the model's suggestions.
- **Portability and control** — prioritize inspectable data and flexible integrations.

These are development goals, not a claim that all capabilities are implemented.

## First prototype

The first scaffold provides a runnable FastAPI application with a browser interface, a versioned Pydantic model, local SQLite persistence, statement provenance, hypothesis review, JSON export, and deletion.

Initial workflow:
1. Enter a goal and user-provided statements.
2. Record source labels and optional excerpts.
3. Create a hypothesis and link it to evidence statements.
4. Review it as accepted, revised, or rejected without overwriting source statements.
5. Export the model as JSON or delete the local model.

Scenarios have a schema representation but are not yet editable in the interface. JSON import, migrations, authentication, and multi-user operation are not implemented. See the [prototype plan](docs/PROTOTYPE.md) and [architecture notes](docs/ARCHITECTURE.md).

## Run locally

Requirements: Python 3.12 or newer.

Create a virtual environment, activate it, then run:

    python -m pip install -e ".[dev]"
    uvicorn app.main:app --reload

Open http://127.0.0.1:8000. API documentation is available at http://127.0.0.1:8000/docs.

By default, SQLite data is stored at data/virtue-wise.sqlite3. Set VIRTUE_WISE_DB to use another path. Keep the server bound to localhost and do not enter sensitive data; the prototype does not provide authentication or encryption at rest.

Run quality checks:

    ruff check app tests
    ruff format --check app tests
    pytest

## Current status

**Stage: early runnable prototype scaffold.** Core model, local persistence, a small UI, API endpoints, and initial tests are in place. The architecture and data format remain provisional until evaluated through real use. Scenario comparison, JSON import, migrations, and broader evaluation remain future work.

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
| [Architecture](docs/ARCHITECTURE.md) | Implemented structure and known limitations |
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
