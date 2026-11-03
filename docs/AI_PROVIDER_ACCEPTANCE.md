# Live AI provider acceptance matrix

This checklist supplements deterministic adapter tests. It is a manual operator test because it requires real provider installations, accounts, and credentials. Do not use personal, confidential, or production project data during this prototype phase.

## Before testing

1. Use a clean local checkout and a dedicated test database.
2. Keep VIRTUE WISE bound to 127.0.0.1; do not expose it to a LAN, reverse proxy, tunnel, or public host.
3. Use a fictional project with a few clearly labelled statements and one tentative hypothesis.
4. Export the model before testing import, restore, or deletion.
5. Confirm the provider's current price, retention policy, rate limits, and data handling independently. A zero-price catalog entry is not a promise of unlimited access or privacy.
6. Record the application commit, OS, Python version, provider version, model ID, test date, and outcome. Never record API keys or private prompts in the report.

## Provider verification

| Provider | Setup and successful run | Failure and recovery |
|---|---|---|
| Ollama | Install Ollama locally, pull a supported model, verify the installed model list, discover models in VIRTUE WISE, consent, and run the fictional prompt. Confirm inference traffic remains on loopback. | Stop Ollama before discovery and analysis. The workspace must remain usable; discovery should report no local model, and analysis should explain how to restart Ollama. Test a model that is not installed. |
| OpenRouter | Configure OPENROUTER_API_KEY only in the server process environment. Discover the free-model list, select a currently zero-priced model, consent, and run the fictional prompt. | Test an invalid/revoked key, a model no longer listed as free, and provider quota exhaustion if the account permits. Confirm errors are actionable and another provider can be selected. |
| OpenCode | Start the OpenCode server on loopback, configure a provider/model whose reported input and output costs are zero, discover it, consent, and run the fictional prompt. | Stop the OpenCode server, then simulate a model failure. Verify the workspace remains available and temporary analysis sessions are deleted after both successful and failed analysis where the server allows deletion. |
| OpenAI-compatible endpoint | Configure a test endpoint using HTTPS (or loopback HTTP), a test key, and an explicit model allowlist. Confirm only allowlisted model IDs appear. | Test invalid credentials, unreachable endpoint, malformed model output, timeout, and a model outside the allowlist. Confirm the key never appears in browser responses or saved project data. |

## Cross-provider safety checks

- [ ] No model discovery or analysis starts automatically on page load.
- [ ] No analysis request is sent until the user selects a provider/model, checks consent, and clicks Analyze.
- [ ] Hosted-provider consent text clearly states that the prompt and selected saved workspace context leave the computer.
- [ ] A provider failure never changes a statement or automatically saves a hypothesis or scenario.
- [ ] Saved AI suggestions remain proposed, unverified, and marked with provider/model provenance.
- [ ] Model-supplied evidence IDs are checked against existing statement IDs; unknown IDs are removed and a warning is shown.
- [ ] Rate limits, timeouts, unavailable providers, malformed output, and server contention produce distinct actionable messages.
- [ ] Switching to another provider after a failure does not require rebuilding the saved workspace.
- [ ] Browser reload preserves explicitly saved project data but discards transient AI analysis drafts.
- [ ] No API key appears in browser network responses, HTML, JavaScript, logs intended for users, or the SQLite project model.

## Deterministic automated coverage

Run:

```bash
ruff check app tests
ruff format --check app tests
pytest
python -m pytest -q browser_tests
```

The automated adapter tests use controlled fake HTTP responses; they verify request construction, free-model filtering, structured-output validation, rate-limit/HTTP error handling, timeouts, and OpenCode temporary-session cleanup. They do not prove that a third-party provider is currently reachable or that a particular free model remains available.

## Sign-off

Do not mark a provider as live-verified until a person has completed both a successful real-provider run and at least one failure/recovery test. Record each provider separately; an Ollama pass does not imply OpenRouter or OpenCode has passed.
