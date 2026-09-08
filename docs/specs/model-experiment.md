# First chronological model experiment

Protocol fixed on 2026-09-08 before inspecting July, August, or October targets.

## Acceptance criteria

Validate pinned July–October 2025 archives, report monthly cleaning and schema
checks, validate full journey keys, and prevent journey overlap across periods.
Train a median baseline and regularized linear regression; choose regression
strength only on August. Report September as previously explored development
data and evaluate October only after saving the chosen configuration. Deliver
MAE/RMSE, station/hour/category errors with counts, charts, and a reproducible
report. Run focused tests and the real experiment, then publish review branches
and pull requests when GitHub authentication is available.

## Data and prediction contract

Use the existing pinned archive revision and ten station IDs. Preserve the
September exploratory command. Extend the same cleaning rules to each month;
do not filter the target using observed delay severity. Inspect negative tails,
ambiguous zero counts, cancellations, and coverage separately. Exclude ambiguous
October daylight-saving timestamps rather than guessing their UTC offset.

The output is an archive-reported arrival-delay estimate for planning a journey.
Use only station, scheduled arrival hour, scheduled weekday, and published train
category. These are timetable fields intended to be available before departure;
the archive retains final plans, not historical plan snapshots, so this is a
retrospective timetable-only benchmark, not a verified live departure-time model.
Do not use upstream final delays, changed times, destination changes, journey IDs,
or cancellation flags as predictors. Changed arrival is used only for target
construction and boundary checks.

## Journey identity and boundaries

Parse full stop IDs from the right into a signed journey prefix, ten-digit
journey-start timestamp, and stop sequence. Preserve the timestamp in the journey
key; the archive's `train_line_ride_id` alone strips it and may repeat on different
days. Cross-check parsed parts against the supplied prefix/sequence columns.
Check uniqueness of full journey/sequence keys and report collisions.

Use the interior of each calendar month (days 2 through the penultimate day),
leaving at least a day between evaluation cohorts. Require parsed journey start,
planned arrival, and changed arrival to all lie inside the same cohort. This
reduces cross-file boundary and cross-period journey problems. Assert disjoint
full journey keys and strict event chronology. The latest observed label event
must precede the following cohort's first planned event; collection availability
cannot be proven from processed files and remains a disclosed limitation.

## Fixed experiment

- July: training.
- August: choose Ridge alpha from 1, 10, 100 using MAE; deterministic tie order.
- September: already explored; development-period report, no tuning.
- October: final held-out period; no model selection based on its metrics.
- Baseline: training-median DummyRegressor.
- Regression: one-hot encode the four categorical inputs with unseen categories
  ignored, then Ridge. Fit all preprocessing on July only; retain that training
  set for final comparisons so both methods have identical information.
- Select baseline versus the best Ridge using August MAE, reporting both later.
- Primary metric: MAE in minutes. Secondary: RMSE in minutes. Report counts and
  error by station, scheduled hour, and category; no inference of causal effects.
- Report diagnostic metrics for nonzero labels and labels >= -30 minutes using
  the already fitted predictions, without changing the training population.
  These are sensitivity views, not alternative model-selection criteria.

Save the frozen configuration before computing final-period metrics. Save fitted
models locally, metrics and provenance as JSON, and a Markdown report with PNGs.
Dataset sizes are around 100 MB each; no raw national history collection needed.
