---
name: raildelay-efficient-work
description: Continue the Raildelay project in a small, complete, token-efficient slice when the user says to continue or requests routine project work. Use for implementation, analysis, documentation, verification, and commits within this repository.
---

# Raildelay efficient work

Advance the current Raildelay objective without making the user repeat workflow preferences.

- Read `AGENTS.md` and the relevant specification before a significant change.
- Infer the smallest useful next slice from the active objective and completed work. State its acceptance criteria in one or two short sentences before editing.
- Keep the slice narrow. Do not simultaneously add a new data source, retrain a model, build a UI, expand infrastructure, and rewrite documentation unless the user specifically requests that scope.
- Prefer repository files and existing generated evidence. Do not browse, download large archives, rerun expensive real-data workflows, or inspect a reserved test period unless the current slice requires it and the user asked for that outcome.
- Use focused reads and checks. Avoid dumping whole specifications, histories, reports, generated JSON, or repeated status unless it directly resolves the task.
- Give brief progress updates: what changed or was learned, the relevant check, and the immediate next action. Keep the final handoff short unless the user asks for explanation.
- Preserve the experiment protocol and data boundaries. Never repurpose a used final test month as unseen data; write a new protocol before a new model-selection cycle.
- When project files changed, run proportionate checks and commit the completed slice before handing back. Include the commit hash. Do not create an empty commit for a question-only turn.
- Do not create GitHub releases, pull requests, merges, deployments, external messages, or destructive actions without explicit user authorization.

For the current risk-model direction, consult `docs/results/risk-model.md` and
`docs/specs/risk-experiment.md`. The next research step is a fresh protocol for
recent training plus time-separated probability calibration, with a new final
period; it is not an instruction to start that work unless the user asks to continue.
