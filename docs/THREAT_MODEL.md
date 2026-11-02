# Security threat model — local prototype

**Status:** design baseline only; this document does not certify the application as secure. The production/network-deployment gate remains open in [issue #7](https://github.com/virtuewise/virtue-wise/issues/7).

## Scope and supported deployment

The current supported boundary is one trusted user running the FastAPI application on their own machine, bound to loopback (for example, `127.0.0.1`). Use fictional/non-sensitive data. Do not expose the service to a LAN, public interface, reverse proxy, or untrusted user. There is no multi-user identity or authorization model.

The application has a static browser UI, JSON API, Pydantic validation, and one SQLite row containing the project model. It has no authentication, session security, CSRF-token mechanism, encryption-at-rest layer, or backup manager. It serializes state-changing requests with a process-local lock, but has no cross-process/multi-worker coordination or stale-write version checks. It also has limited browser-origin/Fetch Metadata checks and a loopback Host allowlist; these are defense-in-depth controls, not authentication or a complete CSRF mechanism.

## Assets and security goals

- **Project content:** titles, goals, statements, source excerpts, hypotheses, review notes, scenarios, and assumptions in the SQLite database and JSON exports.
- **Integrity:** unique record IDs, valid evidence references, unique evidence links, and the rule that edits to reviewed claims/evidence reopen review.
- **Availability:** ability to read, edit, export, and recover the local project.
- **User control:** deliberate import, export, and deletion; invalid imports must not replace valid saved data.
- **Software supply chain:** source code, dependencies, build/test workflows, and any future deployment secrets.

Security goals are confidentiality from other local users/processes where the operating system can enforce it, model integrity, bounded resource use for untrusted input, and recoverability. The application cannot guarantee confidentiality against a compromised host or a user/process that can read the database file.

## Trust boundaries and data flows

1. **Browser to local API:** the browser sends user input to the FastAPI server. State-changing requests with cross-origin Origin/Referer or `Sec-Fetch-Site: cross-site` signals are rejected, and unapproved Host headers are blocked. Requests with no browser origin metadata are still accepted for non-browser API clients; a malicious local process remains outside this protection. There is no session-bound CSRF token or authenticated identity.
2. **Import boundary:** uploaded bytes are parsed as JSON, validated against schema version 1 and cross-record invariants, then persisted. Content type and a 2 MB file limit are checked in the endpoint. An application middleware rejects request bodies above 2.1 MB before multipart parsing, both when Content-Length is declared and when it is absent (including chunked transfer), by counting incoming ASGI body chunks. UTF-8, duplicate-key, non-standard numeric, and schema validation failures are rejected without replacing the saved model. This application-level buffer does not prevent the ASGI server from allocating an individual incoming chunk, and it does not impose upload timeouts or a global concurrent-upload budget.
3. **Persistence boundary:** validated project state is serialized to one SQLite row. Filesystem permissions and host security currently provide the main access boundary.
4. **Export boundary:** the API emits the complete project as downloadable JSON. Anyone able to call it can obtain all stored project content.
5. **Deployment boundary:** a reverse proxy, container, LAN interface, or public endpoint changes the threat model and is unsupported until issue #7 is satisfied.

## Threat actors and abuse cases

| Threat | Impact | Current mitigation / gap |
|---|---|---|
| Untrusted website or local process sends state-changing requests | Unauthorized edits or deletion | Cross-origin browser signals and unapproved Host headers are rejected; no authentication, session-bound CSRF token, or defense against a malicious local process; missing origin metadata is allowed for API clients |
| Another local OS user reads the SQLite file or an exported JSON file | Disclosure of project content | Rely on OS account and file permissions; no application-level encryption |
| Malformed or oversized import | Crash, resource exhaustion, or accidental data loss | 2 MB file limit, 2.1 MB application-level request-body limit for both declared and absent Content-Length (including chunked transfer), strict UTF-8/JSON parsing, duplicate-key rejection, schema validation, and generic validation errors; server/proxy timeouts, ingress limits, and concurrent-upload controls remain required |
| Duplicate IDs or invalid evidence links | Ambiguous records or broken provenance | Domain model validation rejects duplicate IDs, duplicate evidence links, and dangling references |
| Storage write failure during a mutation | UI/API error or uncertain save result | SQLite transaction should preserve the previous committed row; failure-path tests and clear UI feedback are required |
| Concurrent requests or multiple server workers | Lost updates from last-writer-wins replacement | A process-local lock serializes state-changing requests for one app process; no cross-process/multi-worker lock or optimistic version check; single worker only |
| Database loss, corruption, accidental deletion, or ransomware | Irrecoverable project loss | Manual JSON export is available; no automated backup, restore verification, or recovery procedure |
| Vulnerable dependency or compromised build workflow | Code execution or data disclosure | CI checks are not a security review; dependency and workflow review are required before network deployment |

## Concrete controls and release gate

### Present in the prototype (verify continuously)

- Strict Pydantic models reject extra fields and validate schema version, unique record IDs, and evidence references. Request-validation responses omit submitted input values.
- Import rejects unsupported content types, limits file bytes to 2 MB, and rejects request bodies above 2.1 MB before multipart parsing whether Content-Length is declared or absent (including chunked transfer). It validates before save and returns generic errors for malformed or invalid models. This application-level limit still requires ingress-level limits, upload/read timeouts, and global concurrency controls at the server or reverse proxy.
- Statement deletion is blocked while a hypothesis references it.
- Editing linked statements or materially changing hypotheses resets their review state.
- SQLite parameter binding is used for model writes; a single-row upsert keeps each save within a transaction.
- State-changing requests are serialized within one application process; lock acquisition times out after 10 seconds with HTTP 503. This does not coordinate multiple processes or workers.
- A regression test exports, deletes, and restores a model through JSON import, checking project identity and representative linked content.
- State-changing requests reject mismatched Origin/Referer and `Sec-Fetch-Site: cross-site`; Host headers are restricted to loopback names and the test host. Requests without Origin/Referer remain accepted for non-browser API clients.
- The app is documented for loopback-only use and warns against sensitive data.

These controls reduce specific risks; they do not replace authentication, authorization, a session-bound CSRF token, secure deployment, or independent review. See [the authentication design](AUTHENTICATION_DESIGN.md) for the proposed networked model.

### Required before network deployment

1. Choose and document the supported deployment architecture, user population, data classification, and trust boundaries.
2. Implement authentication and authorization for every protected UI/API operation, including export and deletion.
3. Implement session-bound CSRF tokens and strict canonical-origin validation for the selected authentication model; review CORS, Host validation, cookie attributes, TLS termination, and security headers. The current origin middleware is only a baseline.
4. Decide whether encryption at rest is required. If it is, specify key storage, rotation, backups, and recovery independently of the encrypted data.
5. Add automated tests for access control, forged requests, import edge cases, persistence failures, deletion, concurrency, and error leakage. Before multi-worker deployment, replace the process-local lock with database-backed concurrency control and test cross-process stale-write behavior.
6. Define least-privilege file permissions, secrets handling, dependency patching/scanning, logging that avoids sensitive content, and incident response.
7. Define and test backup/restore, data deletion, schema migration, and recovery procedures.
8. Review the real deployment configuration and obtain independent security approval. Passing unit tests or CI is not sufficient.

## Explicit non-goals and residual risks

This threat model does not claim resistance to a compromised operating system, malicious code running as the same user, physical access, filesystem backup exposure, or denial of service by a sufficiently privileged local process. No security certification or production readiness is implied.

## Review checklist

- [ ] Confirm the supported deployment model and data classification with maintainers.
- [ ] Validate each “present” control against current code and tests.
- [ ] Track each required control to an implementation, test, or explicit risk acceptance in issue #7.
- [ ] Revisit this model whenever authentication, integrations, network deployment, multi-user support, or sensitive data handling is introduced.
