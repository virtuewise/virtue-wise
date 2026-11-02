# Import and error-handling security notes

**Status:** current prototype behavior and known limits. The application remains loopback-only; this document does not approve network deployment.

## Accepted upload

- The import endpoint accepts `application/json`, `text/json`, and `application/octet-stream`.
- The uploaded file is read to a maximum of 2,000,001 bytes; files larger than 2,000,000 bytes receive HTTP 413.
- Import request bodies above 2,100,000 bytes are rejected before FastAPI parses the multipart upload, whether or not `Content-Length` is supplied.
- The filename is not used as a filesystem path.
- The content must decode as UTF-8 JSON. Duplicate object member names and non-standard `NaN` / `Infinity` constants are rejected.
- The parsed value must validate against schema version 1 and the project model's record and evidence-reference invariants.
- Validation and parsing complete before persistence. Invalid imports do not replace the previously saved model.

## Error responses

- Malformed UTF-8, malformed JSON, duplicate keys, and non-standard numeric constants return a generic 422 message rather than parser exception details.
- Schema validation failures return a generic 422 message rather than echoing submitted field values.
- FastAPI request-validation responses include error locations, messages, and error types, but omit Pydantic's submitted `input` values.
- Oversized files and declared oversized requests return 413. Unsupported media types return 415.
- Unexpected server failures return a generic server error to the client; operational logs and deployment error handling still require review.

## Explicit residual limits

The application middleware checks a declared `Content-Length` and also counts incoming ASGI request-body chunks when the header is absent (including chunked transfer). It buffers at most 2,100,000 request-body bytes and rejects an over-limit request before Starlette's multipart parser receives the body. This is an application-level bound, not a complete ingress resource-control policy: a server may already have allocated an individual incoming ASGI chunk, and slow clients or many simultaneous uploads can still consume connections and memory. A production reverse proxy or ASGI server must additionally enforce a hard request-body limit, upload/read timeout, and concurrency limit before any network deployment.

The application has no malware scanning, quarantine workflow, rate limiting, global concurrent-upload budget, or independent parser sandbox. It must remain local-only and use fictional/non-sensitive data. See [issue #7](https://github.com/virtuewise/virtue-wise/issues/7) for the release gate.
