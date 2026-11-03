# Optional local AI analysis

VIRTUE WISE can optionally use an Ollama model running on the same computer to draft hypotheses, counterpoints, missing-information prompts, questions, experiments, and alternative scenarios.

This integration is **off until the user checks for a local model, selects an installed model, explicitly consents to local processing, and clicks Analyze with local AI**. It does not use a hosted AI API.

## Windows setup

1. Install Ollama for Windows from the [official Ollama website](https://ollama.com/download).
2. Start Ollama and keep its local service running.
3. In PowerShell, confirm the command is available:
   ```powershell
   ollama --version
   ```
4. Download a model of your choice using Ollama. For example:
   ```powershell
   ollama pull <model-name>
   ollama list
   ```
5. Start VIRTUE WISE on its normal loopback address, open <http://127.0.0.1:8000>, and select **Check local AI**.
6. Select one of the models listed by Ollama, review the local-processing disclosure, tick the consent box, and click **Analyze with local AI**.

Choose a model that your computer can run. Model size, memory requirements, quality, speed, and output reliability vary. VIRTUE WISE does not automatically download a model or choose one on your behalf.

## What data is processed

- The status check calls Ollama's local `/api/tags` endpoint to list installed models. It does not send project content.
- After explicit consent, the analysis request sends the text in the intake prompt and a bounded snapshot of the current saved workspace to the local Ollama service at `127.0.0.1:11434`.
- Workspace context is limited to the project title and goal, up to 50 statements, 25 existing hypotheses, and 10 scenarios.
- The application does not send this content to a cloud AI provider.
- Model downloads are handled by Ollama and may use the internet. VIRTUE WISE does not download model weights.

The service URL can be changed with `VIRTUE_WISE_OLLAMA_URL`, but the application accepts only plain HTTP on `127.0.0.1`. Remote hosts, HTTPS proxies, redirects, and non-loopback destinations are rejected. The default is `http://127.0.0.1:11434`.

## How suggestions are handled

The local model returns a bounded JSON structure. VIRTUE WISE validates it before showing results. Evidence references are checked against actual statement IDs; unknown references are removed and surfaced as a warning.

- Hypotheses are displayed as model-generated candidates. They remain proposed and have unknown uncertainty if the user chooses to add them.
- The rationale records that the hypothesis came from a local model and remains unverified.
- Scenarios are labelled as AI-generated drafts and retain their assumptions and expected outcomes for human review.
- Questions, missing information, experiments, and the analysis summary remain in the transient review panel unless the user copies or records them elsewhere.
- Nothing is automatically accepted, marked supported, treated as fact, or used to take an external action.
- Generated drafts are not persisted automatically and will disappear when the browser page is reloaded.

The model is not given web-search tools or external action tools. It cannot verify claims, retrieve current sources, establish novelty, or independently discover unknown unknowns. Treat its output as brainstorming material that needs evidence and testing.

## Operational safeguards

- One local analysis runs at a time per application process.
- The model request has a 90-second timeout and the response is capped at 1 MB.
- The app uses non-streaming structured output and rejects malformed responses.
- Redirects are rejected and the configured endpoint must be loopback.
- User-supplied content is treated as untrusted data in the analysis prompt; model output is still untrusted and rendered as text, not HTML.
- The integration does not change the single-user, loopback-only deployment boundary.

Local processing is not the same as encrypted storage. The current application has no authentication or encryption at rest. Ollama and the operating system may have their own logs and operational behavior; review their settings separately. Continue to use fictional or non-sensitive data during this prototype phase.

## API reference

- `GET /api/analysis/status` checks the local model list.
- `POST /api/analysis/draft` requires `consent: true`, a prompt, and an installed model name.
- The Ollama chat endpoint supports non-streaming responses and structured JSON output; see the [official Ollama API documentation](https://docs.ollama.com/api/chat).
