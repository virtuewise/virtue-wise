# Roadmap

This roadmap records hypotheses and intended milestones. Dates and feature commitments will be added only after scope and capacity are understood. The [prototype specification](docs/PROTOTYPE.md) defines the proposed first implementation; the application itself is not yet implemented.

## Phase 0 — Define the problem

- [x] Write a concise first user journey and prototype acceptance criteria
- [ ] Review adjacent work in knowledge graphs, personal knowledge management, provenance, and scenario planning
- [ ] Define terminology: observation, user statement, inference, hypothesis, recommendation, scenario
- [ ] Document privacy and threat-model assumptions
- [x] Establish project license, governance guidance, and contribution process
- [x] Propose an initial stack and keep it documented in the prototype specification

## Phase 1 — Build a minimal world model

- [ ] Implement a small, versioned schema for entities, statements, hypotheses, and sources
- [ ] Support provenance and timestamps
- [ ] Separate user-provided statements from inferred relationships
- [ ] Add schema validation and serialization tests
- [ ] Provide import/export for a documented portable JSON format
- [ ] Add local SQLite persistence and deletion

## Phase 2 — Make it understandable

- [ ] Build a small local interface for editing a world model
- [ ] Display evidence and uncertainty for candidate relationships
- [ ] Allow users to correct, reject, and remove information
- [ ] Record review decisions without silently overwriting source statements
- [ ] Test accessibility and keyboard navigation

## Phase 3 — Test useful inference

- [ ] Start with transparent, deterministic suggestions and user-created relationships
- [ ] Evaluate usefulness, false connections, and explanation quality
- [ ] Consider optional model-assisted suggestions only after the core workflow works
- [ ] Make every generated hypothesis traceable to its inputs
- [ ] Publish evaluation examples and known failure modes

## Phase 4 — Explore scenarios

- [ ] Represent explicit assumptions and proposed actions
- [ ] Compare alternatives without presenting speculative outcomes as certainty
- [ ] Distinguish deterministic calculations from model-generated estimates
- [ ] Test with a narrow, low-risk use case

## Phase 5 — Build an ecosystem

- [ ] Stabilize the core data format and compatibility policy
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
