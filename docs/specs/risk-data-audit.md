# Delay-risk data suitability audit

Protocol set on 2026-09-10 before computing risk-specific summaries. This is a
data suitability check, not model selection or a new final evaluation.

## Scope and acceptance criteria

- Reuse checksum-verified July–October 2025 files, cleaning and journey cohorts.
  No new held-out file is inspected, no model is fitted, and raw data is unchanged.
- Define the proxy event as arrival delay >= 15 minutes, conditional on retained
  noncanceled arrival records. Report full cleaned months and model cohorts
  separately; never use all source records as the event-rate denominator.
- Report sequential cleaning exclusions, missing pairs, ambiguous zeros, negative
  tails, station/day coverage, and monthly station/category risk summaries.
- Quantify zero-label sensitivity: L/N is the archive proxy frequency, L/(N-Z)
  is a selection-biased nonzero-only diagnostic, and (L+Z)/N is the scenario in
  which every ambiguous zero hides a >=15-minute delay. These are not confidence
  intervals or bounds on real travel risk: nonzero labels, unrecorded services,
  cancellations, and source coverage may also be wrong or missing.
- Measure July sample support for later inputs using station/category and
  station/category/hour/weekday groups. Report unseen groups and rows backed by
  fewer than 100 July records. The threshold is a descriptive screening choice,
  not a validated reliability cutoff. Include distinct journey counts in group
  summaries; repeated stops and nearby services are not independent samples.
- Deliver a reproducible module, machine-readable summaries, a generated report,
  a checked-in decision, synthetic tests for denominators/thresholds/support,
  and a successful run on the real pinned files.

## Decision rules

The retrospective proxy experiment can proceed if integrity checks pass and
both target classes have meaningful sample support. Sparse groups require
fallbacks or abstention rules in the subsequent model protocol.

A validated commuter-risk claim additionally requires trustworthy observation
and feature-availability provenance, suitable coverage, a separate treatment
of cancellation risk, and prospective or independently verified evaluation.
Monthly volume alone cannot satisfy these requirements. If these gates fail,
record a conditional go for a historical demo and a no-go for live reliability.
