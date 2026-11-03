# Prototype acceptance walkthrough

This is a manual review checklist for the first local prototype. Use fictional data only.

## Start from a clean checkout

1. Follow the [README setup instructions](../README.md#run-locally).
2. Run `ruff format --check app tests`, `ruff check app tests`, and `pytest`.
3. Start the server and open <http://127.0.0.1:8000>.
4. Confirm the workspace loads and the status message announces readiness.

## Core workflow

- [ ] Save a project title and goal, then reload and confirm they persist.
- [ ] Add a statement with a source label and excerpt; confirm all fields are visible.
- [ ] Edit the statement and verify its text and source update.
- [ ] Create a hypothesis linked to the statement; confirm the evidence is displayed separately from the claim.
- [ ] Try deleting the linked statement; confirm deletion is blocked with a useful explanation.
- [ ] Unlink the evidence from the hypothesis, then delete the statement.
- [ ] Accept, revise, and reject hypotheses; confirm the review note and status are visible and source statements are unchanged.
- [ ] Create two scenarios with different assumptions and expected outcomes; confirm both are visible side by side.
- [ ] Edit and delete a scenario; confirm the comparison updates.
- [ ] Export JSON and retain a backup.
- [ ] Import `examples/demo-project.json`; confirm the project, statements, hypothesis, evidence links, and scenarios are loaded.
- [ ] Attempt to import malformed JSON or a model with dangling evidence; confirm the current model is not replaced.
- [ ] Delete the local model and confirm an empty model is ready.

## Optional local AI analysis

This section requires Ollama and at least one locally installed model. It is optional; the rest of the application must remain usable when Ollama is absent.

- [ ] With Ollama stopped, select Check local AI; confirm the app reports that local AI is unavailable without breaking the workspace.
- [ ] Start Ollama on loopback and install a model; confirm the app lists installed model names.
- [ ] Confirm no analysis starts until the consent checkbox is selected and Analyze with local AI is clicked.
- [ ] Run an analysis with fictional project data; confirm the output is clearly labelled as unverified model suggestions.
- [ ] Confirm evidence links refer only to existing statement IDs and unknown IDs are removed with a warning.
- [ ] Add one hypothesis and confirm it remains proposed with unknown uncertainty and a local-model provenance note.
- [ ] Save one scenario and confirm its assumptions and generated-draft status remain visible.
- [ ] Reload the browser and confirm generated analysis drafts were not silently persisted; only explicitly saved hypotheses/scenarios remain.
- [ ] Inspect local network activity and confirm the app contacts only the loopback Ollama service, not a hosted AI provider.

## Accessibility and browser checks

- [ ] On first Tab, confirm the skip link is visible and moves focus to the workspace.
- [ ] Use the section navigation at desktop and mobile widths; confirm anchor targets are not hidden under the sticky header.
- [ ] Complete the workflow using only the keyboard.
- [ ] Verify focus is always visible and moves in a logical order.
- [ ] Verify labels and status announcements with a screen reader.
- [ ] Check at narrow mobile width and at 200% zoom.
- [ ] Confirm long user-provided text wraps without horizontal page scrolling.
- [ ] Open the same workspace in two tabs, save in one, then attempt a stale edit in the other; confirm no overwrite occurs and the one-click reload action restores the latest saved state.
- [ ] Close the browser completely, reopen it against the same local instance, and verify the saved project title, statements, evidence links, review state, and scenarios are still present.
- [ ] Stop and restart the local application process against the same database; verify the same records and links recover without relying on browser cache.
- [ ] Simulate provider rate limits and an unavailable provider; confirm errors remain distinct from local database contention and the saved workspace remains usable.
- [ ] Complete the real-provider checklist in [AI_PROVIDER_ACCEPTANCE.md](AI_PROVIDER_ACCEPTANCE.md) separately for each configured provider.
- [ ] Run the independent-process SQLite recovery and concurrent-writer regression tests before release.
- [ ] Confirm native edit dialogs expose clear labels and validation errors, move focus appropriately, and cancel safely.

## Sign-off

Record browser/OS, Python version, date, issues found, and whether each unchecked item is blocked or failed. Do not mark this walkthrough complete until a person has actually performed it. Automated tests are not a substitute for this manual review.
