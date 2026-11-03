# Authentication and authorization design

**Status:** proposed architecture only. Authentication, sessions, authorization, and a complete CSRF-token mechanism are not implemented. This document does not authorize network deployment; issue #7 remains the release gate.

## Current boundary

The prototype remains a single-user, loopback-only application using fictional/non-sensitive data. The current code adds defense-in-depth checks for browser request origins and Host headers. It does not establish a user identity, authenticate API clients, distinguish owners, or protect against a malicious local process. Requests without browser Origin/Referer metadata remain possible for non-browser API clients; this is intentional compatibility for the current unauthenticated local API, not an authenticated security boundary.

## Confirmed workspace policy

The product decision is **private by default, with explicit, revocable sharing**:

- Every project has exactly one owning user identity.
- Only the owner can access a project until the owner explicitly grants access to identified users.
- A grant is scoped to a specific project and a named permission level; there are no implicit workspace-wide grants.
- Sharing must be explicit, visible to the owner, and revocable. Revocation must take effect on the next authorization check, including for already-open browser tabs and API clients.
- No anonymous/public links, discoverable project listings, or default organization-wide access.
- A recipient must authenticate as the identity to which the grant was issued; email address alone is not an authorization credential.
- The owner retains the ability to manage sharing and delete the project. The initial permission vocabulary and whether recipients may re-share must be specified before implementation.
- Read, edit, import, export, and delete operations must all enforce project-level authorization on the server. Export and backup flows must not bypass the same ownership/sharing policy.
- Authorization failures must not reveal whether another user's project or identifier exists.

This decision defines the intended product authorization policy. It does **not** implement multi-user identity, tenant isolation, or sharing in the current prototype.

## Deployment decisions still required

Before implementation, maintainers must explicitly settle:

- whether the first networked release is a multi-user service on one host or a multi-host/distributed service (multi-host remains unsupported by the current SQLite architecture);
- the user population, organization/tenant boundaries, data classification, and account recovery expectations;
- the trusted TLS-terminating reverse proxy and exact proxy-to-application trust boundary;
- the identity provider and its operator;
- the initial project permission levels, invitation/acceptance lifecycle, and audit requirements.

The selected private-by-default policy does not, by itself, settle these infrastructure and operational decisions. Do not add a home-grown password database or treat a shared API key as user authentication.

## Recommended networked identity and session model

For a networked deployment, prefer a maintained OpenID Connect identity provider using Authorization Code flow with PKCE. The application should validate issuer, audience, signature, nonce, state, redirect URI, expiry, and token claims using a maintained OIDC library. Require MFA through the identity provider for accounts that can access project data. Do not store provider access or refresh tokens in browser localStorage.

After successful login, create an opaque, cryptographically random server-side session identifier. Store only a hash of the session identifier server-side. Deliver it in a cookie with `HttpOnly`, `Secure`, and an appropriate `SameSite=Lax` (or stricter where compatible) attribute, a narrow Path, and no Domain attribute. Rotate the session identifier after login and privilege changes; enforce idle and absolute expiry; revoke sessions on logout and account disablement. Use HTTPS only. Trust forwarded scheme/client headers only from explicitly configured proxy addresses.

If maintainers choose a strictly offline, single-user deployment instead, keep the service bound to loopback and rely on the operating-system account boundary. Do not invent a local password flow without a concrete threat model and recovery plan.

## Authorization enforcement

Implement deny-by-default authorization on every protected route:

- Resolve a stable authenticated identity key (`issuer` + `subject`) from the validated server-side session.
- Load the project and its owner/grants from trusted persistence; never accept an owner ID or permission decision from a client payload.
- Permit the owner; otherwise require an active, project-scoped grant for the authenticated identity and the requested action.
- Apply the same checks to UI routes, API reads, mutations, imports, exports, deletion, and any future background jobs or integrations.
- Re-check authorization for each request. Do not rely on UI hiding, stale client state, cached grants, or a previously issued download URL.
- Make share creation, permission changes, and revocation owner-only operations. Record security-relevant grant changes in an audit trail without recording project content or secrets.
- Administrative functions, if ever added, require a separate explicit role and audit trail; administrative status must not silently grant project-content access unless that policy is deliberately specified.
- Health checks disclose only minimal liveness information and never project data.

## CSRF and request-origin controls

For cookie-authenticated browser sessions:

1. Require a synchronizer CSRF token bound to the server-side session on every state-changing request. Expose it to the same-origin UI through a protected bootstrap endpoint or rendered page data; send it in a custom request header.
2. Validate the token in constant time and reject missing, invalid, or expired tokens.
3. Validate the request Origin against a configured canonical public origin. Use Referer only as a carefully validated fallback; reject `Origin: null`.
4. Reject `Sec-Fetch-Site: cross-site` on state-changing requests as defense in depth.
5. Do not enable credentialed cross-origin CORS for the application UI. If cross-origin integrations become necessary, specify exact origins and a separate threat review.
6. Keep GET/HEAD/OPTIONS read-only. Never mutate state through a safe method.

The current prototype implements only steps 3–4 in a limited request-host comparison, plus a loopback Host allowlist. It does not have sessions or CSRF tokens. Missing Origin/Referer headers are allowed for non-browser API clients today. Once cookie sessions are introduced, require CSRF tokens and origin validation for every unsafe request; do not retain that unauthenticated compatibility exception.

## Session and account lifecycle

- Use the identity provider for password policy, MFA, recovery, and account disablement.
- Use short-lived application sessions with idle and absolute expiration, rotation, server-side revocation, and logout invalidation.
- Protect login initiation and callback with OIDC state and nonce; use PKCE.
- Rate-limit login initiation and callback failures at the edge and application.
- Avoid logging credentials, tokens, session identifiers, CSRF tokens, or project content.
- Define a secure account-recovery and incident-response procedure before launch.

## Required implementation and verification before network use

- Settle the deployment topology, identity provider, tenant boundaries, permission vocabulary, and invitation lifecycle.
- Implement OIDC callback validation and server-side sessions.
- Implement private-by-default project ownership and explicit project-scoped grants in persistent storage.
- Add route-level owner/grant authorization tests for every API operation, including import/export/delete, and prove cross-user isolation by default.
- Add tests for grant acceptance, least privilege, owner-only sharing, revocation against existing sessions/tabs, and non-disclosure of project existence.
- Add CSRF token lifecycle tests, missing/invalid-token tests, origin mismatch tests, Fetch Metadata tests, cookie-attribute tests, session rotation/expiry/revocation tests, and login rate-limit tests.
- Validate proxy/TLS configuration and trusted-host allowlists in a production-like environment.
- Obtain independent security review and update issue #7 with evidence of completion.

Passing ordinary CI, origin checks, or this design document alone does not satisfy the release gate.
