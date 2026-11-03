# Independent security review brief

**Purpose:** prepare an independent reviewer to assess the first-release local-only boundary. This document is a review request and evidence index, not a security assessment or approval.

## Review target

- **Repository:** virtuewise/virtue-wise
- **Target architecture:** single-user, local-first application on a trusted personal computer
- **Network boundary:** loopback listener only; LAN, reverse proxy, tunnel, public, team, and cloud deployment are unsupported
- **Storage:** local SQLite file on a local filesystem
- **AI processing:** local Ollama where configured; optional remote providers only after explicit user consent
- **Identity:** no application authentication or per-user authorization in the first-release boundary
- **Required review target:** record the exact commit SHA and review the actual deployment configuration used for acceptance

See [ADR 0001](decisions/0001-local-first-deployment.md). A future network or multi-user deployment requires a separate architecture decision and security review.

## Reviewer independence

The reviewer should be independent of the implementation author and should have authority to report findings without being asked to approve the release. The reviewer must not treat CI success, this brief, or the author's own tests as evidence that a control is secure.

The review outcome must be recorded as one of:

- Approved for the explicitly scoped local-only use, with any residual risks stated.
- Approved with conditions, listing required fixes and verification evidence.
- Not approved, listing blocking findings.
- Unable to assess, listing missing access or evidence.

## Review scope

### Application and browser boundary

- Verify the app binds only to loopback by default and rejects unexpected Host/Origin/Referer values.
- Review trusted-host and same-origin protections; do not mistake them for user authentication or complete CSRF protection.
- Inspect every state-changing API route for origin checks, validation, concurrency control, and error disclosure.
- Review browser rendering for DOM injection, unsafe HTML, script injection, and unsafe handling of model-generated content.
- Verify that AI suggestions remain drafts and cannot silently mutate saved facts or project state.

### Import, persistence, and recovery

- Review import size limits, request-body limits, read timeouts, concurrency limits, strict JSON parsing, duplicate-key rejection, and validation error handling.
- Review SQLite transaction boundaries, ETag/If-Match conflict handling, multi-process writer behaviour, rollback, and data deletion.
- Review backup creation, verification, restore, retention, purge, permissions, and host-level encryption responsibilities.
- Verify the documented local-filesystem-only SQLite constraint and reject network/shared storage assumptions.

### AI providers and secrets

- Verify provider keys are read server-side and never exposed to the browser or persisted in project data.
- Verify the fictional provider smoke test cannot read or accept user workspace content.
- Verify full analysis requires separate explicit consent before selected workspace context is sent.
- Review free-model filtering and configured model allowlists; do not assume every OpenAI-compatible endpoint is free.
- Review timeouts, rate limits, unavailable-provider handling, malformed output handling, OpenCode temporary-session cleanup, and logging.
- Review provider retention, pricing, and privacy disclosures for accuracy and clarity.

### Runtime and dependencies

- Review dependency vulnerability reports, dependency pinning/update process, Python and browser runtime support, security headers, logging, error responses, and local process permissions.
- Verify no production or network listener is enabled by the documented run instructions.
- Review backup scheduling and restore drills on the actual target host; a timer template alone is not an installed backup service.

## Evidence index

The reviewer should inspect the source at the exact review commit and the current versions of:

- [Threat model](THREAT_MODEL.md)
- [Authentication design (proposal only)](AUTHENTICATION_DESIGN.md)
- [Import security](IMPORT_SECURITY.md)
- [Backup operations](BACKUP_OPERATIONS.md)
- [Local operations runbook](OPERATIONS_RUNBOOK.md)
- [Release readiness](RELEASE_READINESS.md)
- [Local deployment ADR](decisions/0001-local-first-deployment.md)
- [Browser acceptance](ACCEPTANCE.md)
- [AI provider acceptance](AI_PROVIDER_ACCEPTANCE.md), when present on the reviewed base revision
- [Network-deployment security gate](https://github.com/virtuewise/virtue-wise/issues/7)

## Reproducible checks

Run from a clean checkout using the documented supported Python versions:

```bash
ruff check app tests
ruff format --check app tests
pytest
python -m pytest -q browser_tests
```

Also inspect the exact CI runs for Python 3.12/3.13 on Linux and Windows, Chromium acceptance on Linux and Windows, documentation checks, and static analysis. Automated checks are supporting evidence only.

## Known limitations that must remain visible

- The first release has no application login, user accounts, or per-user authorization.
- Loopback is not an authentication boundary and does not isolate untrusted local processes or operating-system users.
- No network, LAN, reverse-proxy, tunnel, team, or cloud deployment is approved.
- SQLite is supported only on a local filesystem.
- Application-created backups are not encrypted by the app; host-level encryption and a separate protected copy remain operator responsibilities.
- Backup scheduler templates are not proof that a scheduler is installed or monitored.
- Manual screen-reader, keyboard-only, mobile-device, 200% zoom, and clean-install walkthroughs require human acceptance.
- Real Ollama, OpenRouter, and OpenCode success/failure tests require configured live services and must be recorded separately.

## Review record template

The reviewer should attach a report containing:

- Reviewer and independence statement.
- Review date and exact commit SHA.
- Environment and deployment configuration reviewed.
- Areas reviewed and tests independently repeated.
- Findings with severity, affected component, reproduction steps, and recommended remediation.
- Residual risks and explicit scope limitations.
- Final outcome and any conditions for approval.

**Release gate:** do not mark the security review complete until an independent reviewer has produced and signed off on this record. Keep issue #7 open until every applicable network-deployment requirement is satisfied or formally excluded by the accepted local-only deployment boundary.
