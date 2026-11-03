# ADR 0001: Local-first single-user deployment for the first release

- **Status:** Accepted for the first release boundary
- **Date:** 2026-11-03
- **Decision owner:** Virtue Wise project maintainer

## Context

Virtue Wise is being developed as a local-first thinking and decision-support workspace. Its first usable release should keep the project model and SQLite database on the user's computer, allow optional local model inference, and make hosted AI processing an explicit user choice.

The current application does not provide user accounts, authentication, session-bound authorization, tenant isolation, or a production multi-user deployment model. Loopback binding and same-origin protections reduce exposure, but they are not user authentication and do not protect against every process or account on the same computer.

Implementing login before deciding whether the product is a local single-user application, a self-hosted network service, or a hosted multi-user service would create security complexity without a settled trust model.

## Decision

For the first release, Virtue Wise is a **single-user, local-first application running on a trusted personal computer**.

1. The supported HTTP listener is loopback only (127.0.0.1 or localhost). It must not bind to 0.0.0.0, a LAN interface, or a public interface.
2. The supported data store is a local SQLite database on a local filesystem. Network filesystems and shared multi-user database access are unsupported.
3. The application assumes one trusted local user. It does not claim to isolate multiple operating-system users or local processes that can reach the loopback listener.
4. Authentication and per-user authorization are intentionally out of scope for this release. Do not add a cosmetic login screen as a substitute for an actual identity and authorization design.
5. Project data remains local unless the user explicitly initiates an operation that sends selected content to a configured AI provider. The provider smoke test sends only its fixed fictional sample; full analysis requires separate consent for the prompt and selected saved workspace context.
6. Provider credentials remain in the server process environment. They must not be written into browser storage, project JSON, or the SQLite model.
7. The operator is responsible for host-level disk protection and encrypted backups. Application-level backup files are not represented as encrypted by this decision.
8. The application is a prototype and must not be used for sensitive personal, regulated, or production-critical data until the release-readiness and independent security-review gates are satisfied.

## Consequences

### Accepted for the first release

- No application login or multi-user account management.
- Local SQLite is appropriate for one local user and a local filesystem only.
- Local OS account security and device protection are part of the trust boundary.
- Remote AI remains opt-in and provider-specific privacy, retention, pricing, and rate limits must be reviewed by the user.
- Loopback and origin protections remain necessary defence-in-depth; they do not turn the application into a network-safe service.

### Explicitly unsupported

- LAN access, reverse-proxy exposure, tunnels, public hosting, shared workstations with untrusted local users, and multi-user/team access.
- Shared or network-mounted SQLite databases.
- Treating loopback binding as authentication or authorization.
- Storing API keys in browser code, browser storage, project exports, or the project database.

## Reopening this decision

Any proposal for LAN, self-hosted network, team, or cloud deployment requires a new architecture decision and threat model before implementation. That decision must specify:

- Identity provider and authentication/session lifecycle.
- User, role, project, and resource authorization boundaries.
- Session-bound CSRF protection and origin/host policy.
- Tenant isolation and data ownership.
- TLS termination, reverse-proxy trust, CORS, ingress size/time/concurrency limits.
- Encryption at rest, key management, backup encryption, restore and deletion guarantees.
- Logging, secrets handling, dependency patching, monitoring, incident response, and operational ownership.
- Independent security review and production-like acceptance.

Until a replacement decision is accepted and its controls are implemented and independently reviewed, the loopback-only restriction remains in force.

## Related controls and acceptance

- [Release readiness](../RELEASE_READINESS.md)
- [Import and resource limits](../IMPORT_SECURITY.md)
- [Browser and manual acceptance](../ACCEPTANCE.md)
- [Local AI provider configuration](../LOCAL_AI.md)
- [Security deployment gate](https://github.com/virtuewise/virtue-wise/issues/7)
