# VIRTUE WISE: Vision and Research Questions

## Vision

Explore an open, user-controlled layer that helps people connect information, understand the basis of inferences, compare possible actions, and turn understanding into deliberate action.

The long-term ambition is to make a shared set of primitives available to many applications. A research tool, planning application, learning environment, or developer tool could represent relevant facts and relationships in a portable form without depending on one model vendor.

## The central hypothesis

A system can become more useful when it maintains an explicit, evolving model of relevant context—and makes the evidence, assumptions, uncertainty, and revisions in that model inspectable.

This is a hypothesis to test, not a settled claim. In some cases, a document, search query, spreadsheet, or simple checklist will be more effective. VIRTUE WISE should earn complexity by demonstrating practical value.

## Questions to answer

1. What is the smallest useful representation of a changing world?
2. How should the system distinguish direct observations, user statements, imported sources, inferences, and recommendations?
3. How can relationships be suggested without making unsupported or overly confident claims?
4. How should time, contradiction, correction, and provenance be represented?
5. Which scenario comparisons can be grounded in explicit calculations, and which are speculative?
6. How can users inspect, export, correct, and delete the information about them?
7. What should be standardized so independent applications can interoperate, and what should remain application-specific?
8. How do we evaluate whether an insight is useful, accurate, calibrated, and worth the complexity?

## Design commitments

### Evidence is first-class

Every important claim should be traceable to an input, source, or explicit inference process. When provenance is unavailable, the system should say so.

### Facts and hypotheses are different

An inferred connection must not silently become a verified fact. Users should be able to challenge a hypothesis and understand what changed after correction.

### Uncertainty should be legible

Confidence scores are not automatically meaningful probabilities. Any confidence measure should be defined, evaluated, and explained; otherwise use qualitative uncertainty labels.

### The user remains in control

The system should ask permission before accessing new sources or taking external actions. High-impact actions require appropriate review and confirmation.

### Models are replaceable components

Language models may help interpret or explain data, but the core representation and validation rules should not depend on a single provider.

### Privacy is architectural

Collect only what is needed, keep access scoped, document retention, and support data export and deletion. Sensitive personal inferences require particular caution.

## How we will approach novelty

We will compare the proposed design with adjacent fields and existing projects before claiming novelty. Potential differentiation may come from the integration of temporal context, provenance, uncertainty, scenario exploration, user correction, and a portable protocol—but only implementation and evaluation can show whether that combination is meaningfully better.

## First proof

The first proof should demonstrate one end-to-end journey: enter a goal and a few facts, inspect a suggested connection with its evidence, correct that connection, and compare a small number of explicitly qualified alternatives. The user should be able to export the data and understand what the system did.
