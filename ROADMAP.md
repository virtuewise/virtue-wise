# Roadmap

This roadmap records hypotheses and intended milestones. Dates and feature commitments will be added only after scope and capacity are understood.

## Phase 0 — Define the problem

- [ ] Write a concise problem statement and target first user journey
- [ ] Review adjacent work in knowledge graphs, personal knowledge management, digital twins, agent memory, provenance, and scenario planning
- [ ] Define terminology: observation, user statement, inference, hypothesis, recommendation, scenario
- [ ] Document privacy and threat-model assumptions
- [ ] Agree on project license, governance, and contribution process

## Phase 1 — Build a minimal world model

- [ ] Define a small, versioned schema for entities, relations, events, and sources
- [ ] Support provenance and timestamps
- [ ] Separate asserted facts from inferred relationships
- [ ] Add validation and serialization tests
- [ ] Provide import/export for a documented portable format

## Phase 2 — Make it understandable

- [ ] Build an interactive playground for editing a small world model
- [ ] Display evidence and uncertainty for candidate relationships
- [ ] Allow users to correct, reject, and remove information
- [ ] Record model revisions without silently overwriting source facts
- [ ] Test accessibility and keyboard navigation

## Phase 3 — Test useful inference

- [ ] Add a replaceable inference interface
- [ ] Compare deterministic rules with optional model-assisted suggestions
- [ ] Evaluate usefulness, false connections, calibration, and explanation quality
- [ ] Make every generated hypothesis traceable to its inputs
- [ ] Publish evaluation examples and known failure modes

## Phase 4 — Explore scenarios

- [ ] Represent explicit assumptions and proposed actions
- [ ] Compare alternatives without presenting speculative outcomes as certainty
- [ ] Distinguish deterministic calculations from model-generated estimates
- [ ] Test with a narrow, low-risk use case

## Phase 5 — Build an ecosystem

- [ ] Stabilize the core data format and compatibility policy
- [ ] Document adapter interfaces
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
