# Raildelay working instructions

## Scope and specifications

- This is a Python railway delay analytics, machine learning, and visualization project.
- Read `docs/specs/product.md` and `docs/specs/technical.md` before significant
  implementation. Give a short plan and concrete acceptance criteria first.
- Keep project requirements in those specs and update them when scope changes.
- Start with a small, complete, reproducible slice. Add folders and tools only
  when required; do not build dashboard or deployment infrastructure prematurely.
- Select and document a real dataset before implementing source-specific ingestion.
- The selected region is Nordrhein-Westfalen, initially Aachen Hbf, Düsseldorf
  Hbf, Köln Hbf, and Essen Hbf plus the stations proposed in the product spec.
  Read `docs/specs/data-source.md` before data work; validate the preferred
  historical archive before treating its schema or coverage as established.

## Collaboration and verification

- Explain unfamiliar tools and commands in plain language before relying on them.
- Use Python modules for reusable logic and notebooks only where exploration helps.
- Before declaring a code change complete, run relevant tests and checks and
  summarize what changed, what passed, and any unresolved limitations.
- Preserve existing user changes. Never commit secrets, tokens, real `.env`
  files, downloaded datasets, or private data.
- Use GitHub as the source of truth once configured: one feature per branch
  and pull request, with `main` kept stable.

## Data and modeling rules

- Preserve raw data and document source, license, schema, and time coverage.
- Make timezone handling, missing values, cancellations, and exclusions explicit.
- Keep features restricted to information available at prediction time.
- Use chronological evaluation, keep journey records together, and fit
  preprocessing on training data only.
- Compare against a naive baseline and report metric units and sample counts.
- Clearly distinguish synthetic test fixtures from real analysis data.

## Session and reuse

- Use the named tmux session `raildelay`, rooted in this project directory.
- Attach with `tmux attach -t raildelay`. Prefix: `Ctrl-b`; detach with
  `Ctrl-b`, then `d`.
- Treat repeated corrections and repository-wide rules as candidates for this file.
- Put reusable project procedures in `.agents/skills/` when needed; personal
  cross-project procedures belong in `~/.agents/skills/`.
