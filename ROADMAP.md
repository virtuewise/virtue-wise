# Roadmap

This roadmap separates the **first local prototype** from the broader research vision. The first prototype is now implemented in `main`; completion of that small milestone does not mean the wider VIRTUE WISE world-model concept is complete or production-ready.

## Phase 0 — Define the problem

- [x] Write a concise first user journey and prototype acceptance criteria
- [ ] Review adjacent work in knowledge graphs, personal knowledge management, provenance, and scenario planning
- [ ] Define terminology: observation, user statement, inference, hypothesis, recommendation, scenario
- [x] Document initial privacy and threat-model assumptions
- [x] Establish project license, governance guidance, and contribution process
- [x] Select and document an initial stack

## Phase 1 — Implement the scoped local model

- [x] Implement a versioned Pydantic schema for the first project, statement, hypothesis, and scenario records
- [x] Keep user-provided statements distinct from hypotheses
- [x] Validate unique record identifiers and evidence references
- [x] Add local SQLite persistence and deletion
- [x] Provide JSON export and validated import for schema version 1
- [ ] Design richer first-class entities, source records, temporal context, and relation types
- [ ] Define schema migration and compatibility policy

## Phase 2 — Make the model understandable

- [x] Build a local browser interface for project and record editing
- [x] Display source labels, evidence links, and qualitative uncertainty
- [x] Allow users to correct hypotheses and unlink evidence
- [x] Record accept/revise/reject decisions without rewriting source statements
- [ ] Complete a manual end-to-end walkthrough from a clean checkout
- [ ] Complete keyboard-only, screen-reader, and accessibility testing

## Phase 3 — Evaluate useful inference

- [x] Keep hypotheses user-created; do not require an external model
- [ ] Define deterministic suggestion rules and evaluate usefulness and false connections
- [ ] Publish evaluation examples, limitations, and known failure modes
- [ ] Consider optional model-assisted suggestions only after the core workflow has been evaluated

## Phase 4 — Explore scenarios

- [x] Represent alternatives with explicit assumptions and expected outcomes
- [x] Compare scenarios descriptively without fabricated scores or certainty
- [x] Add a documented fictional project-planning example and automated import test
- [ ] Manually test the workflow using the example
- [ ] Evaluate whether the comparison helps users make better-informed choices

## Phase 5 — Broader platform and ecosystem

- [ ] Stabilize the core data format after evaluation
- [ ] Document adapter interfaces only when a real integration requires them
- [ ] Add integration examples and contributor guides
- [ ] Establish release, deprecation, and governance processes
- [ ] Consider a stable API only after real-world validation

## What success means

Early success is not measured only by stars. We will look for:

- People completing the core user journey without maintainer help
- Insights that users find useful and can verify or correct
- Reproducible tests and transparent failure analysis
- External developers building independent integrations
- Evidence that the core solves a problem better than simpler alternatives

## Non-goals for the first prototype

- Training a foundation model
- Replacing every personal productivity or knowledge tool
- Claiming to predict a person's future with certainty
- Making consequential decisions without meaningful human control
- Building a broad feature set before validating the core loop
- Requiring cloud services, third-party accounts, or paid model APIs

## Current completion boundary

The runnable local prototype supports project editing, sourced statements, hypothesis review, qualitative scenario comparison, JSON import/export, local deletion, API tests, and CI. It is not a complete general-purpose world model, and it is not production-hardened: authentication, encryption at rest, multi-user operation, migrations, and a completed manual accessibility review remain out of scope or unfinished.
