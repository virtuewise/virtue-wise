# Security threat model — local prototype

**Status:** design baseline only; this document does not certify the application as secure. The production/network-deployment gate remains open in [issue #7](https://github.com/virtuewise/virtue-wise/issues/7).

## Scope and supported deployment

The current supported boundary is one trusted user running the FastAPI application on their own machine, bound to loopback (for example, `127.0.0.1`). Use fictional/non-sensitive data. Do not expose the service to a LAN, public interface, reverse proxy, or untrusted user. There is no multi-user identity or authorization model.

The application has a static browser UI, JSON API, Pydantic validation, and one SQLite row containing the project model. It currently has no authentication, session security, CSRF protection, encryption-at-rest layer, concurrency coordination, or backup manager. These are gaps, not assumed controls.

## Assets and security goals

- **Project content:** titles, goals, statements, source excerpts, hypotheses, review notes, scenarios, and assumptions in the SQLite database and JSON exports.
- **Integrity:** unique record IDs, valid evidence references, unique evidence links, and the rule that edits to reviewed claims/evidence reopen review.
- **Availability:** ability to read, edit, export, and recover the local project.
- **User control:** deliberate import, export, and deletion; invalid imports must not replace valid saved data.
- **Software supply chain:** source code, dependencies, build/test workflows, and any future deployment secrets.

Security goals are confidentiality from other local users/processes where the operating system can enforce it, model integrity, bounded resource use for untrusted input, and recoverability. The application cannot guarantee confidentiality against a compromised host or a user/process that can read the database file.

## Trust boundaries and data flows

1. **Browser to local API:** the browser sends user input to the FastAPI server. If another website or local process can reach the API, requests may be forged unless origin/CSRF and access controls are added.
2. **Import boundary:** uploaded bytes are parsed as JSON, validated against schema version 1 and cross-record invariants, then persisted. Content type and a 2 MB body limit are checked in the current endpoint; malformed payloads should fail without replacing the saved model.
3. **Persistence boundary:** validated project state is serialized to one SQLite row. Filesystem permissions and host security currently provide the main access boundary.
4. **Export boundary:** the API emits the complete project as downloadable JSON. Anyone able to call it can obtain all stored project content.
5. **Deployment boundary:** a reverse proxy, container, LAN interface, or public endpoint changes the threat model and is unsupported until issue #7 is satisfied.

## Threat actors and abuse cases

| Threat | Impact | Current mitigation / gap |
|---|---|---|
| Untrusted website or local process sends state-changing requests | Unauthorized edits or deletion | No authentication/CSRF defense; loopback-only is a deployment restriction, not sufficient protection against every local process or browser attack |
| Another local OS user reads the SQLite file or an exported JSON file | Disclosure of project content | Rely on OS account and file permissions; no application-level encryption |
| Malformed or oversized import | Crash, resource exhaustion, or accidental data loss | 2 MB import limit and Pydantic validation exist; test malformed encodings, parser failures, and replacement atomicity |
| Duplicate IDs or invalid evidence links | Ambiguous records or broken provenance | Domain model validation rejects duplicate IDs, duplicate evidence links, and dangling references |
| Storage write failure during a mutation | UI/API error or uncertain save result | SQLite transaction should preserve the previous committed row; failure-path tests and clear UI feedback are required |
| Concurrent requests or multiple server workers | Lost updates from last-writer-wins replacement | No optimistic concurrency/version check or multi-worker coordination; single trusted process only |
| Database loss, corruption, accidental deletion, or ransomware | Irrecoverable project loss | Manual JSON export is available; no automated backup, restore verification, or recovery procedure |
| Vulnerable dependency or compromised build workflow | Code execution or data disclosure | CI checks are not a security review; dependency and workflow review are required before network deployment |

## Concrete controls and release gate

### Present in the prototype (verify continuously)

- Strict Pydantic models reject extra fields and validate schema version, unique record IDs, and evidence references.
- Import rejects unsupported content types, limits the body to 2 MB, validates before save, and returns an error for invalid models.
- Statement deletion is blocked while a hypothesis references it.
- Editing linked statements or materially changing hypotheses resets their review state.
- SQLite parameter binding is used for model writes; a single-row upsert keeps each save within a transaction.
- The app is documented for loopback-only use and warns against sensitive data.

These controls reduce specific risks; they do not replace authentication, authorization, CSRF protection, secure deployment, or independent review.

### Required before network deployment

1. Choose and document the supported deployment architecture, user population, data classification, and trust boundaries.
2. Implement authentication and authorization for every protected UI/API operation, including export and deletion.
3. Add CSRF and origin protections appropriate to the selected authentication model; review CORS, host validation, cookies, TLS termination, and security headers.
4. Decide whether encryption at rest is required. If it is, specify key storage, rotation, backups, and recovery independently of the encrypted data.
5. Add automated tests for access control, forged requests, import edge cases, persistence failures, deletion, concurrency, and error leakage.
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
