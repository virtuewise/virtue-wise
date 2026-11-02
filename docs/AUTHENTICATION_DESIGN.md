# Authentication and authorization design

**Status:** proposed architecture only. Authentication, sessions, authorization, and a complete CSRF-token mechanism are not implemented. This document does not authorize network deployment; issue #7 remains the release gate.

## Current boundary

The prototype remains a single-user, loopback-only application using fictional/non-sensitive data. The current code adds defense-in-depth checks for browser request origins and Host headers. It does not establish a user identity, authenticate API clients, distinguish owners, or protect against a malicious local process. Requests without browser Origin/Referer metadata remain possible for non-browser API clients; this is intentional compatibility for the current unauthenticated local API, not an authenticated security boundary.

## Deployment decision required

Before implementation, maintainers must choose and record:
- whether the application remains a local single-user tool or becomes a networked multi-user service;
- the user population, tenant model, data classification, and account recovery expectations;
- the trusted TLS-terminating reverse proxy and the exact proxy-to-application trust boundary;
- whether external identity infrastructure is available and who operates it.

Do not add a home-grown password database or treat a shared API key as user authentication.

## Recommended networked model

For a networked deployment, prefer a maintained OpenID Connect identity provider using Authorization Code flow with PKCE. The application should validate issuer, audience, signature, nonce, state, redirect URI, expiry, and token claims using a maintained OIDC library. Require MFA through the identity provider for accounts that can access project data. Do not store provider access or refresh tokens in browser localStorage.

After successful login, create an opaque, cryptographically random server-side session identifier. Store only a hash of the session identifier server-side. Deliver it in a cookie with `HttpOnly`, `Secure`, and an appropriate `SameSite=Lax` (or stricter where compatible) attribute, a narrow Path, and no Domain attribute. Rotate the session identifier after login and privilege changes; enforce idle and absolute expiry; revoke sessions on logout and account disablement. Use HTTPS only. Trust forwarded scheme/client headers only from explicitly configured proxy addresses.

If maintainers choose a strictly offline, single-user deployment instead, keep the service bound to loopback and rely on the operating-system account boundary. Do not invent a local password flow without a concrete threat model and recovery plan.

## Authorization model

Start with deny-by-default, single-owner authorization:
- every authenticated session maps to one stable identity key (`issuer` + `subject`);
- each project has one owner identity;
- read, create, update, import, export, and delete operations require ownership;
- administrative functions, if ever added, require a separate explicit role and audit trail;
- health checks disclose only minimal liveness information and never project data.

Authorization must be enforced server-side on every route, not by hiding UI controls. Import, export, and model deletion are sensitive operations and must use the same policy. API documentation and static UI exposure must be considered separately in the deployment configuration.

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

- Select the deployment model and identity provider.
- Implement OIDC callback validation and server-side sessions.
- Add route-level authentication and project-owner authorization tests for every API operation, including import/export/delete.
- Add CSRF token lifecycle tests, missing/invalid-token tests, origin mismatch tests, Fetch Metadata tests, cookie-attribute tests, session rotation/expiry/revocation tests, and login rate-limit tests.
- Validate proxy/TLS configuration and trusted-host allowlists in a production-like environment.
- Obtain independent security review and update issue #7 with evidence of completion.

Passing ordinary CI, origin checks, or this design document alone does not satisfy the release gate.
