# AI providers and model selection

VIRTUE WISE supports a free-first, multi-provider analysis layer. The user selects the provider and model for each run. No provider is contacted until the user checks the catalog, selects a model, explicitly consents, and clicks **Analyze with selected AI**.

## Providers

| Provider | What VIRTUE WISE uses | Cost and privacy |
|---|---|---|
| Ollama | Models installed on this computer | Local inference; no project content is sent to a hosted model provider. Ollama model downloads may use the internet. |
| OpenRouter | Models whose published input and output prices are both zero, plus the `openrouter/free` router | Hosted inference. Requires an OpenRouter API key. Free model availability and rate limits can change. |
| OpenCode | Models configured in the local OpenCode server whose configured input and output costs are both zero | VIRTUE WISE talks to OpenCode on loopback. OpenCode forwards the prompt to the configured inference provider. OpenCode's free chat models are intended to be used through OpenCode itself, so this integration uses its local server rather than calling its inference endpoint directly. |
| Custom OpenAI-compatible endpoint | Explicitly allowlisted model IDs at a configured endpoint | May be free or paid. VIRTUE WISE does not infer pricing; check the provider's terms and limits before configuring it. |

Only zero-priced OpenRouter models and zero-input/zero-output-cost OpenCode models are shown in their respective free lists. This is based on the provider's published catalog metadata, not a guarantee of future availability or unlimited use. Failed requests may count toward a provider's quota.

## Windows setup

### Option A: Ollama (fully local)

1. Install Ollama for Windows from the [official Ollama website](https://ollama.com/download).
2. Start Ollama.
3. In PowerShell, download a model that your computer can run, for example:

   ```powershell
   ollama pull qwen3:8b
   ollama list
   ```

4. Start VIRTUE WISE, open <http://127.0.0.1:8000>, and select **Find available AI models**.
5. Choose **Ollama on this computer**, select an installed model, read the consent notice, and run the analysis.

### Option B: OpenRouter free models

1. Create an account and an API key at [OpenRouter](https://openrouter.ai/).
2. In the same PowerShell window that you use to start VIRTUE WISE, set the key for that process:

   ```powershell
   $env:OPENROUTER_API_KEY = "paste-your-key-here"
   ```

3. Start VIRTUE WISE from that PowerShell window.
4. In the app, select **Find available AI models**, then choose **OpenRouter — free models**.

The key is read by the server process and is never returned to the browser or written to the VIRTUE WISE project database. This PowerShell environment variable lasts only for that terminal session. Do not paste the key into project notes, source code, screenshots, or support messages.

OpenRouter documents a free tier and free model variants, but the model catalog, request quotas, provider capacity, and availability change. The app filters by zero published input and output prices and also offers OpenRouter's automatic free-model router when the catalog is reachable. Review current limits on the [OpenRouter pricing page](https://openrouter.ai/pricing/) and [free model catalog](https://openrouter.ai/collections/free-models).

### Option C: OpenCode free models

1. Install and configure [OpenCode](https://opencode.ai/). Connect a provider/account inside OpenCode and select models that are marked free in its model catalog.
2. Start its local server from PowerShell:

   ```powershell
   opencode serve --hostname 127.0.0.1 --port 4096
   ```

3. Keep that server running while using VIRTUE WISE.
4. Select **Find available AI models**, then choose **OpenCode — configured free models**.

VIRTUE WISE reads the configured provider/model catalog from OpenCode's local `/config/providers` endpoint and lists only models whose reported input and output costs are both zero. It sends analysis through OpenCode's local session API with tools disabled, and attempts to delete the temporary session after the response. OpenCode may route the prompt to a hosted inference provider; it is not equivalent to Ollama-local inference.

If the OpenCode server uses Basic authentication, set the same credentials for the VIRTUE WISE process before starting it:

```powershell
$env:OPENCODE_SERVER_USERNAME = "opencode"
$env:OPENCODE_SERVER_PASSWORD = "your-local-server-password"
```

The default server URL is `http://127.0.0.1:4096`. An alternate URL can be set with `VIRTUE_WISE_OPENCODE_URL`, but it must remain plain HTTP on loopback. VIRTUE WISE does not connect to a remote OpenCode server.

### Option D: Other OpenAI-compatible providers

The optional generic adapter supports a provider that exposes an OpenAI-compatible `/chat/completions` endpoint. Configure the endpoint, API key, model allowlist, and display label in the environment of the VIRTUE WISE server process:

```powershell
$env:VIRTUE_WISE_COMPAT_BASE_URL = "https://api.groq.com/openai/v1"
$env:VIRTUE_WISE_COMPAT_API_KEY = "your-provider-key"
$env:VIRTUE_WISE_COMPAT_MODELS = "model-id-one,model-id-two"
$env:VIRTUE_WISE_COMPAT_LABEL = "Groq"
```

Groq is an example of an OpenAI-compatible provider; its free developer-plan quotas and model availability are account- and model-dependent. The generic adapter does not label these models free. It lists only the model IDs you explicitly configure. The base URL must use HTTPS, except for a service on this computer, which may use HTTP. Never expose a custom endpoint URL or key through the browser.

## What data is processed

- Provider discovery checks installed Ollama models, OpenRouter's model/pricing catalog when a key is configured, the OpenCode provider catalog on loopback, and any explicitly configured custom model allowlist. Discovery does not send project content.
- After explicit consent, analysis sends the intake text and a bounded snapshot of the current saved workspace to the selected model provider.
- Workspace context is limited to the project title and goal, up to 50 statements, 25 existing hypotheses, and 10 scenarios.
- For OpenRouter and custom hosted endpoints, the selected hosted provider receives the prompt and workspace context.
- For OpenCode, the local OpenCode server receives the prompt and forwards it to the configured inference provider. OpenCode may retain logs or session data according to its own behavior.
- For Ollama, content is sent only to the local service at `127.0.0.1:11434`.

The selected provider and model are included in the analysis provenance when the user saves a generated hypothesis or scenario. No API key is stored in the VIRTUE WISE database or returned by its API.

## How suggestions are handled

The model returns a bounded JSON structure. VIRTUE WISE validates it before showing results. Evidence references are checked against actual statement IDs; unknown references are removed and surfaced as a warning.

- Hypotheses are displayed as candidate explanations. If saved, they remain proposed with unknown uncertainty.
- Saved rationale identifies the selected provider and model and marks the suggestion unverified.
- Scenarios are labelled as AI-generated drafts and retain their assumptions and expected outcomes for human review.
- Questions, missing information, experiments, and the analysis summary remain in the transient review panel unless the user records them elsewhere.
- Nothing is automatically accepted, marked supported, treated as fact, or used to take an external action.
- Generated drafts are not persisted automatically and disappear when the browser page is reloaded.

The model is not given web-search or external action tools. It cannot verify claims, retrieve current sources, establish novelty, or independently discover unknown unknowns. Treat its output as brainstorming material that needs evidence and testing.

## Operational safeguards

- One analysis runs at a time per application process.
- Provider requests have bounded timeouts and response sizes; redirects are rejected.
- OpenRouter and custom-provider credentials are held in server environment variables and never returned to the browser.
- Custom provider model IDs are explicitly allowlisted; custom endpoint URLs are server-side configuration and must use HTTPS unless loopback.
- OpenCode is restricted to a local loopback server. Analysis sessions request no tools and are deleted after use where the server permits.
- Ollama remains restricted to HTTP on `127.0.0.1`.
- User-supplied content is treated as untrusted data; model output is rendered as text, not HTML.
- Multi-provider support does not change the single-user, loopback-only deployment boundary.

Local inference is not the same as encrypted storage. Hosted inference means data leaves the computer. The current application has no authentication or encryption at rest. Continue to use fictional or non-sensitive data during this prototype phase.

## API reference

- `GET /api/analysis/status` lists configured providers and available models without sending project content.
- `POST /api/analysis/draft` requires `consent: true`, a provider ID, model ID, and prompt.
- Ollama uses its [chat API](https://docs.ollama.com/api/chat).
- OpenRouter uses its [OpenAI-compatible API](https://openrouter.ai/docs/api-reference/overview).
- OpenCode uses its [local server API](https://opencode.ai/docs/server/).
