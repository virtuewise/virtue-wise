# Data-model evaluation protocol

## Purpose

Decide from observed workflow needs—not architectural enthusiasm—whether VIRTUE WISE should add richer first-class entities, normalized source records, relation types, or schema migrations. This document defines an evaluation plan; it does not claim that the evaluation has happened or that a schema redesign is justified.

Use fictional or otherwise non-sensitive data. Keep the prototype local and do not use it for consequential decisions.

## Questions to answer

1. Can people represent the target problem using project, sourced statement, hypothesis, evidence links, and qualitative scenario records without losing important meaning?
2. Do users repeatedly need to cite one source for multiple statements, preserve source metadata, or distinguish a source document from a quoted excerpt?
3. Do recurring real-world objects (for example, projects, organizations, people, or events) need stable identity across multiple statements and scenarios?
4. Are relationships beyond hypothesis-to-statement evidence links necessary to complete a task, and can their meaning be described consistently?
5. Would any added structure materially improve traceability, correction, comprehension, or portability enough to justify its UI, validation, documentation, and migration cost?

## Evaluation procedure

### 1. Establish a baseline

Use a clean checkout and follow [the manual acceptance walkthrough](ACCEPTANCE.md). Record the exact commit, environment, browser, and date. Do not count CI results as evidence of usability or schema adequacy.

### 2. Run representative tasks

Using the fictional demo model and at least two additional fictional examples, attempt to:

- Record multiple claims drawn from one source.
- Update a source excerpt and identify which claims depend on it.
- Represent an entity mentioned in several statements without accidentally conflating two similarly named entities.
- Connect a hypothesis to its supporting and contradicting evidence, noting any unsupported relationship the current schema cannot express.
- Export and re-import the model and verify that evidence links and distinctions survive.
- Compare scenarios where assumptions refer to the same entity or event.

For each task, record whether it was completed, workarounds used, meaning lost, user confusion, and any validation or import/export failure. Separate observed issues from proposed solutions.

### 3. Record evidence consistently

Use a short issue log with these fields:

| Field | What to record |
| --- | --- |
| Task and example | Which fictional task was attempted |
| Current-model limitation | Concrete missing or ambiguous behavior, not a proposed feature |
| Frequency | One-off, repeated within a session, or repeated across independent sessions |
| Impact | Cosmetic, extra manual work, traceability loss, incorrect conflation, or blocked task |
| Workaround | Whether a simple convention reliably solves it |
| Candidate change | Source record, first-class entity, relation type, migration, or no change |
| Regression risk | Effects on editing, evidence links, JSON portability, and user understanding |

Do not record sensitive personal data. Do not infer that a limitation is common from one maintainer's experience; label that evidence as exploratory.

## Decision rules

### Add first-class source records only when

- One source is repeatedly referenced by multiple statements, **and**
- users need shared source-level metadata or lifecycle (such as title, locator, publication date, or retrieval date) that cannot be maintained reliably as a statement label/excerpt, **and**
- the benefit is demonstrated in task observations and can be represented without pretending that a source proves a claim.

A source record should describe where information came from; it must not silently convert a sourced statement into a verified fact.

### Add first-class entities or richer relations only when

- repeated tasks require stable identity or a relation that the current schema cannot express;
- a documented naming convention or existing evidence link is insufficient;
- the semantics can be explained in plain language and validated; and
- a prototype demonstrates that the added structure improves a user task rather than merely increasing expressiveness.

Avoid a generic knowledge-graph layer until specific entity and relation types have a demonstrated use case.

### Add migrations only when

- an approved schema change is necessary;
- version-1 import/export compatibility requirements are written down;
- migration behavior is tested against representative version-1 fixtures, including invalid and partially populated data;
- failure is safe and does not silently discard user data; and
- backup, rollback/recovery, and release notes are defined.

Until then, keep schema version 1 stable and defer migration machinery. Do not bundle speculative entities, relationships, and migrations into one change.

## Exit criteria and reporting

Publish a short evaluation note that includes the tasks attempted, number and type of sessions, environment, issues observed, workarounds, limitations of the sample, decision for each candidate change, and next experiment. State clearly if the evidence is only from maintainers.

A decision may be **defer**. If no repeated, consequential limitation is observed, retain the current model and revisit after new use cases appear. If a change is justified, implement the smallest slice and evaluate it before expanding further.

## Current status

- [ ] Clean-checkout manual walkthrough performed and recorded.
- [ ] Keyboard-only, screen-reader, mobile-width, and 200% zoom checks performed and recorded.
- [ ] Representative model-adequacy tasks performed and findings recorded.
- [ ] Decision documented on source records, first-class entities, relation types, and migrations.

This checklist is intentionally unchecked. Creating this protocol is preparation for evaluation, not completion of evaluation.
