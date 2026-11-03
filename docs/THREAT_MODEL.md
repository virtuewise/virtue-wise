# Security threat model — local prototype

**Status:** design baseline only; this document does not certify the application as secure. The production/network-deployment gate remains open in [issue #7](https://github.com/virtuewise/virtue-wise/issues/7).

## Scope and supported deployment

The current supported boundary is one trusted user running the FastAPI application on their own machine, bound to loopback (for example, `127.0.0.1`). Use fictional/non-sensitive data. Do not expose the service to a LAN, public interface, reverse proxy, or untrusted user. There is no multi-user identity or authorization model.

The application has a static browser UI, JSON API, Pydantic validation, and one SQLite row containing the project model. It has no authentication, session security, CSRF-token mechanism, or encryption-at-rest layer. The default data directory is created with POSIX mode `0700` and the live SQLite file with `0600`; existing database files have their mode tightened on open. Existing custom parent directories are not changed, and Windows relies on inherited filesystem ACLs. Operators must protect custom database directories, journal/temporary files, exports, and backups at the host level. A CLI tool can create, verify, retain, and restore SQLite snapshots, and a sample systemd timer is supplied; the operator must install the timer, and backups are not encrypted by the application. Record-level edits use SQLite `BEGIN IMMEDIATE` transactions to serialize independent local processes sharing one database file, with a 10-second busy timeout and HTTP 503 on lock exhaustion. A process-local request lock remains. Full-model replacement/import require an `If-Match` revision and reject stale writes with HTTP 412; missing preconditions return HTTP 428. It also has limited browser-origin/Fetch Metadata checks and a loopback Host allowlist; these are defense-in-depth controls, not authentication or a complete CSRF mechanism.

## Assets and security goals

- **Project content:** titles, goals, statements, source excerpts, hypotheses, review notes, scenarios, and assumptions in the SQLite database and JSON exports.
- **Integrity:** unique record IDs, valid evidence references, unique evidence links, and the rule that edits to reviewed claims/evidence reopen review.
- **Availability:** ability to read, edit, export, and recover the local project.
- **User control:** deliberate import, export, and deletion; invalid imports must not replace valid saved data.
- **Software supply chain:** source code, dependencies, build/test workflows, and any future deployment secrets.

Security goals are confidentiality from other local users/processes where the operating system can enforce it, model integrity, bounded resource use for untrusted input, and recoverability. The application cannot guarantee confidentiality against a compromised host or a user/process that can read the database file.

## Trust boundaries and data flows

1. **Browser to local API:** the browser sends user input to the FastAPI server. State-changing requests with cross-origin Origin/Referer or `Sec-Fetch-Site: cross-site` signals are rejected, and unapproved Host headers are blocked. Requests with no browser origin metadata are still accepted for non-browser API clients; a malicious local process remains outside this protection. There is no session-bound CSRF token or authenticated identity.
   All `/api/` responses, including model reads, mutations, and JSON exports, carry `Cache-Control: no-store` to discourage browser and intermediary storage of project content. This is a cache-control defense in depth, not access control or secure deletion of previously saved copies.
2. **Import boundary:** uploaded bytes are parsed as JSON, validated against schema version 1 and cross-record invariants, then persisted. Content type and a 2 MB file limit are checked in the endpoint. An application middleware rejects request bodies above 2.1 MB before multipart parsing, both when Content-Length is declared and when it is absent (including chunked transfer), by counting incoming ASGI body chunks. UTF-8, duplicate-key, non-standard numeric, and schema validation failures are rejected without replacing the saved model. The middleware also applies a 30-second overall body-read timeout and limits imports to two concurrent requests per application process, with a one-second slot wait before HTTP 503. These controls are process-local. The server may allocate an individual ASGI chunk before the application counts it, and upstream ingress/connection limits remain necessary.
3. **Persistence boundary:** validated project state is serialized to one SQLite row. Filesystem permissions and host security currently provide the main access boundary.
4. **Export boundary:** the API emits the complete project as downloadable JSON. Anyone able to call it can obtain all stored project content.
5. **Deployment boundary:** a reverse proxy, container, LAN interface, or public endpoint changes the threat model and is unsupported until issue #7 is satisfied.

## Threat actors and abuse cases

| Threat | Impact | Current mitigation / gap |
|---|---|---|
| Untrusted website or local process sends state-changing requests | Unauthorized edits or deletion | Cross-origin browser signals and unapproved Host headers are rejected; no authentication, session-bound CSRF token, or defense against a malicious local process; missing origin metadata is allowed for API clients |
| Another local OS user reads the SQLite file or an exported JSON file | Disclosure of project content | Rely on OS account and file permissions; no application-level encryption |
| Malformed or oversized import | Crash, resource exhaustion, or accidental data loss | 2 MB file limit, 2.1 MB application-level request-body limit for both declared and absent Content-Length (including chunked transfer), 30-second body-read timeout, two concurrent imports per process, strict UTF-8/JSON parsing, duplicate-key rejection, schema validation, and generic validation errors; upstream ingress and connection limits remain required |
| Duplicate IDs or invalid evidence links | Ambiguous records or broken provenance | Domain model validation rejects duplicate IDs, duplicate evidence links, and dangling references |
| Storage write failure during a mutation | UI/API error or uncertain save result | SQLite transaction should preserve the previous committed row; failure-path tests and clear UI feedback are required |
| Concurrent record edits or explicit full-model replacement | Lost updates from last-writer-wins replacement | Record-level mutations use SQLite write transactions across local processes sharing one local file; lock waits are bounded at 10 seconds and return HTTP 503. Full-model replacement/import require ETag/If-Match and reject stale revisions; multi-host/network-filesystem operation is unsupported |
| Database loss, corruption, accidental deletion, or ransomware | Irrecoverable project loss | A verified SQLite backup CLI, explicit local snapshot purge, and sample daily systemd timer are available; the timer must be installed and monitored, backups are not encrypted by the app, and restore drills remain an operator responsibility. Backup snapshots retain deleted project data until expiry or explicit purge. |
| Vulnerable dependency or compromised build workflow | Code execution or data disclosure | CI checks are not a security review; dependency and workflow review are required before network deployment |

## Concrete controls and release gate

### Present in the prototype (verify continuously)

- Strict Pydantic models reject extra fields and validate schema version, unique record IDs, and evidence references. Request-validation responses omit submitted input values.
- Import rejects unsupported content types, limits file bytes to 2 MB, and rejects request bodies above 2.1 MB before multipart parsing whether Content-Length is declared or absent (including chunked transfer). It validates before save and returns generic errors for malformed or invalid models. The application also enforces a 30-second body-read timeout and two concurrent imports per process; upstream ingress limits, connection limits, and global concurrency controls remain necessary.
- Statement deletion is blocked while a hypothesis references it.
- Editing linked statements or materially changing hypotheses resets their review state.
- SQLite parameter binding is used for model writes; a single-row upsert keeps each save within a transaction.
- Record-level model mutations acquire a SQLite `BEGIN IMMEDIATE` transaction before reading, then validate and commit or roll back the model atomically. Independent processes sharing the same local database file serialize through SQLite; lock acquisition is bounded at 10 seconds and returns HTTP 503 on exhaustion. Explicit full-model replacement/import require ETag/If-Match revision checks and reject stale writes.
- A regression test exports, deletes, and restores a model through JSON import, checking project identity and representative linked content.
- State-changing requests reject mismatched Origin/Referer and `Sec-Fetch-Site: cross-site`; Host headers are restricted to loopback names and the test host. Requests without Origin/Referer remain accepted for non-browser API clients.
- The app is documented for loopback-only use and warns against sensitive data.
- The live SQLite file and newly created default data directory use restrictive POSIX permissions; backup snapshots and SQLite staging files are created with owner-only permissions, and newly created backup directories use mode `0700`. Existing custom directories and Windows ACLs remain operator responsibilities; this is not encryption.

These controls reduce specific risks; they do not replace authentication, authorization, a session-bound CSRF token, secure deployment, or independent review. See [the authentication design](AUTHENTICATION_DESIGN.md) for the proposed networked model.

### Required before network deployment

1. Choose and document the supported deployment architecture, user population, data classification, and trust boundaries.
2. Implement authentication and authorization for every protected UI/API operation, including export and deletion.
3. Implement session-bound CSRF tokens and strict canonical-origin validation for the selected authentication model; review CORS, Host validation, cookie attributes, TLS termination, and security headers. The current origin middleware is only a baseline.
4. Decide whether encryption at rest is required. If it is, specify key storage, rotation, backups, and recovery independently of the encrypted data.
5. Add automated tests for access control, forged requests, import edge cases, persistence failures, deletion, concurrency, and error leakage. Full-model replacement/import now use transactional ETag/If-Match checks; verify them on the exact supported host/filesystem topology before broader deployment.
6. Define least-privilege file permissions, secrets handling, dependency patching/scanning, logging that avoids sensitive content, and incident response.
7. Install and monitor the OS backup scheduler, use encrypted storage and a separate protected copy, perform periodic restore drills, and define data-deletion and schema-migration procedures.
8. Review the real deployment configuration and obtain independent security approval. Passing unit tests or CI is not sufficient.

## Explicit non-goals and residual risks

This threat model does not claim resistance to a compromised operating system, malicious code running as the same user, physical access, filesystem backup exposure, or denial of service by a sufficiently privileged local process. No security certification or production readiness is implied.

## Review checklist

- [ ] Confirm the supported deployment model and data classification with maintainers.
- [ ] Validate each “present” control against current code and tests.
- [ ] Track each required control to an implementation, test, or explicit risk acceptance in issue #7.
- [ ] Revisit this model whenever authentication, integrations, network deployment, multi-user support, or sensitive data handling is introduced.

## Future multi-user authorization policy (decision recorded)

The selected product policy is **private by default, with explicit, revocable sharing**. This does not change the current supported deployment or security boundary described above: the application still has no authenticated identity, project ownership, sharing grants, or multi-user authorization.

Before a multi-user implementation can be considered, the threat model must be expanded to cover cross-user and cross-tenant access, identity-provider compromise, session theft, invitation abuse, grant escalation, revocation races, export/download leakage, backup access, and administrative access. Authorization must be deny-by-default and enforced server-side for every project read and mutation, including import, export, and deletion. A project must be inaccessible to every identity other than its owner unless an explicit project-scoped grant exists. Revocation must take effect on the next authorization check, not merely hide UI controls.

The first networked deployment topology (single host versus multi-host), tenant boundaries, role/permission vocabulary, identity provider, invitation lifecycle, audit retention, and encryption/key-management requirements remain unsettled. Do not infer those decisions from the private-by-default product policy, and do not implement network authentication or sharing until the deployment architecture is explicitly approved. See [the authentication and authorization design](AUTHENTICATION_DESIGN.md).
