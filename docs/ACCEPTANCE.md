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

## Accessibility and browser checks

- [ ] Complete the workflow using only the keyboard.
- [ ] Verify focus is always visible and moves in a logical order.
- [ ] Verify labels and status announcements with a screen reader.
- [ ] Check at narrow mobile width and at 200% zoom.
- [ ] Confirm long user-provided text wraps without horizontal page scrolling.
- [ ] Confirm native edit dialogs expose clear labels and validation errors, move focus appropriately, and cancel safely.

## Sign-off

Record browser/OS, Python version, date, issues found, and whether each unchecked item is blocked or failed. Do not mark this walkthrough complete until a person has actually performed it. Automated tests are not a substitute for this manual review.
