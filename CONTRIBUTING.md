# Contributing to VIRTUE WISE

Thank you for helping shape VIRTUE WISE. We value careful engineering, clear thinking, respectful collaboration, and honest communication about limitations.

## Before you start

1. Read the [README](README.md), [vision](docs/VISION.md), [prototype plan](docs/PROTOTYPE.md), and [roadmap](ROADMAP.md).
2. Search existing issues and pull requests before starting work.
3. For a substantial change, open an issue first to discuss scope and design.
4. Do not submit secrets, personal data, private user content, or credentials.

## Ways to contribute

- Implementation, testing, and performance work
- Research summaries and prior-art comparisons
- UX, accessibility, and visual explanations
- Documentation, examples, and onboarding
- Security, privacy, and threat modeling
- Reproducible bug reports and safe-to-share evaluation data

## Technical direction

The first prototype's provisional stack and acceptance criteria are in [docs/PROTOTYPE.md](docs/PROTOTYPE.md). Please discuss material deviations before adding dependencies or infrastructure. Until an application and test suite are implemented, do not imply that application-level checks have passed. The current automated workflow checks required documentation and Markdown style.

## Pull request expectations

- Keep changes focused and explain the problem they solve.
- Describe important design choices and alternatives considered.
- Include tests for behavior changes as the relevant code and test suite are introduced.
- Update documentation when interfaces or expected behavior change.
- Identify assumptions, limitations, and any user-facing risks.
- Avoid adding dependencies without explaining why they are needed.
- Never present generated or inferred information as verified fact without provenance.

## Commit messages

Use concise, imperative messages where practical, for example:

- `docs: clarify evidence model`
- `feat: add temporal relation type`
- `fix: preserve source references`
- `test: cover hypothesis revision`

Conventional Commit prefixes are encouraged, not yet enforced.

## Design principles for contributions

- Keep observations separate from inferences and recommendations.
- Make uncertainty explicit where relevant; do not treat an unexplained score as a calibrated probability.
- Make important state changes auditable and reversible where practical.
- Prefer portable formats and provider-neutral interfaces.
- Design for user consent, data minimization, and accessibility.
- Do not introduce covert tracking or undisclosed data collection.

## Review process

Maintainers may request changes, ask for evidence, or defer a proposal until its scope is clearer. A pull request is not accepted until maintainers have reviewed it and required checks pass. Be respectful; disagreement about ideas is welcome, personal attacks are not.

## Code of conduct

By participating, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
