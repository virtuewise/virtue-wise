# VIRTUE WISE

**An open foundation for evidence-aware, human-directed intelligence.**

VIRTUE WISE explores ways to help people connect information, understand the basis of an inference, represent uncertainty, and compare possible decisions—while keeping the underlying model inspectable and under the user's control.

> **Core idea:** move beyond answers alone toward understanding that can be examined, corrected, and used.

[Vision](docs/VISION.md) · [Prototype plan](docs/PROTOTYPE.md) · [Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

---

## Why this project

Information is abundant, but context is fragmented. A useful system should do more than produce a plausible response: it should help people see what is known, where it came from, what is inferred, what remains uncertain, and how different choices could lead to different outcomes.

VIRTUE WISE is an open-source effort to investigate that foundation. It is not tied to one AI model or provider, and it does not assume that a system should make decisions on a person's behalf.

## What we are exploring

- **Evidence and provenance** — connect claims to sources, observations, and revisions.
- **A structured world model** — represent entities, events, relationships, goals, and context.
- **Explicit uncertainty** — distinguish observed information from hypotheses, inferences, and unknowns.
- **Scenario exploration** — make assumptions and trade-offs visible when comparing possible actions.
- **Human correction** — allow people to challenge, revise, or reject the model's suggestions.
- **Portability and control** — work toward inspectable data and flexible integrations rather than avoidable lock-in.

These are research and development goals, not a claim that all capabilities are already implemented.

## Design principles

1. **Human agency:** support judgment; do not replace ownership of decisions.
2. **Traceability:** make important claims and inferences inspectable.
3. **Intellectual honesty:** communicate uncertainty, limitations, and competing explanations.
4. **User control:** make correction and data portability first-class concerns.
5. **Modularity:** avoid unnecessary dependence on a single model or provider.
6. **Evidence-led development:** test small, useful workflows before expanding scope.
7. **Open collaboration:** document assumptions, evaluate prior work, and publish limitations clearly.

## First prototype

The initial proof is a small, local-first project-planning scenario using fictional or non-sensitive data. It will focus on one end-to-end workflow:

1. Enter a goal and a few facts or events.
2. Build an editable representation with source references.
3. Inspect a candidate connection and its evidence and uncertainty.
4. Accept, revise, or reject the hypothesis without overwriting source statements.
5. Compare alternatives under explicit assumptions.
6. Export the model as JSON and delete local data.

The proposed technical choices are Python, FastAPI, Pydantic, SQLite, a small HTML/CSS/JavaScript interface, pytest, and Ruff. The stack and acceptance criteria are documented in [the prototype plan](docs/PROTOTYPE.md). This is a plan; the application is not yet implemented.

## Current status

**Stage: prototype specification.**

The project has a documented vision, proposed initial scope, contribution process, and repository checks. The architecture and data format remain provisional until validated through implementation and evaluation. See the [roadmap](ROADMAP.md) for sequencing.

## Project identity

The connected-node mark and usage guidance are maintained in [docs/BRAND.md](docs/BRAND.md) and [assets/virtue-wise-mark.svg](assets/virtue-wise-mark.svg). The identity emphasizes clarity, evidence, and human agency rather than unsupported AI claims.

## Contributing

Contributions are welcome across engineering, research, product design, accessibility, testing, documentation, and security.

- Start with [CONTRIBUTING.md](CONTRIBUTING.md).
- Read the [prototype plan](docs/PROTOTYPE.md) before proposing implementation choices.
- Check the [roadmap](ROADMAP.md) before proposing substantial work.
- Use the repository's issue templates to report a bug or suggest an improvement.
- For security-sensitive reports, follow [SECURITY.md](SECURITY.md).

For significant architectural changes, please open an issue for discussion before beginning a large implementation.

## Project documents

| Document | Purpose |
| --- | --- |
| [Vision](docs/VISION.md) | Motivation, intended direction, and foundational ideas |
| [Prototype plan](docs/PROTOTYPE.md) | Initial scope, technical choices, and acceptance criteria |
| [Brand guide](docs/BRAND.md) | Visual identity and documentation standards |
| [Roadmap](ROADMAP.md) | Proposed milestones and sequencing |
| [Contributing](CONTRIBUTING.md) | Contribution workflow and expectations |
| [Code of Conduct](CODE_OF_CONDUCT.md) | Community standards |
| [Security](SECURITY.md) | Responsible security reporting |
| [Repository setup](REPOSITORY_SETUP.md) | Maintainer setup checklist |
| [License](LICENSE) | Project license |

## License

Unless otherwise stated in a specific file or directory, this project is distributed under the [MIT License](LICENSE).

---

*Understand the evidence. Make uncertainty visible. Keep people in control.*
