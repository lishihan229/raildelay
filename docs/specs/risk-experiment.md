# Second experiment: historical arrival-delay risk

Status: protocol fixed on 2026-09-10 before fitting classifiers. Implementation
and final evaluation are pending. This protocol supersedes tentative modeling
choices for the second experiment only; preserve the first regression experiment.

## User decision and hypothesis

For an NRW commuter considering a planned arrival, estimate the historical
probability of archive-reported delay >=15 minutes, conditional on an eligible,
noncanceled arrival. Test whether shared time-of-day and weekday patterns improve
probabilities beyond supported station/category historical frequencies.

This is a retrospective proxy benchmark. Neither good scores nor a usable demo
prove live reliability, cancellation risk, connection success, or an appropriate
safety buffer. Keep the [suitability audit](../results/risk-data-suitability.md)
visible in the eventual model card and application.

## Inputs, labels and exclusions

- Reuse the ten audited EVA station identifiers, `prepare`, `cohort`, and
  `assert_separation`. No source-specific cleaning changes based on model scores.
- Binary target: `arrival_delay_minutes >= 15`, including exactly 15 minutes.
  Retain ambiguous zeros as proxy negatives. Preserve negative/extreme delays;
  report diagnostics without changing the primary population or refitting.
- Predictors: station, scheduled local arrival hour, scheduled local weekday,
  and train category. Treat these as categorical. No journey identifiers,
  changed times, final departure delays, cancellation flags, or target aggregates
  computed on validation/test rows may enter the feature matrix.
- Final archive plans do not prove historical availability before departure.
  All observations from a full journey remain in one partition. Retain the
  established exclusion of whole journeys failing the month-interior event rule.
- Report cancellations and missing pairs through existing sequential accounting;
  do not present exclusion counts as cancellation probabilities.

## Chronological periods

| Period | Role | Permitted use |
| --- | --- | --- |
| July + August 2025 | Training | Fit all encoders, reference counts and candidates |
| September 2025 | Selection | Select baseline and classifier configuration |
| October 2025 | Development confirmation | Apply the fixed promotion gate below |
| November 2025 | Reserved final test | Evaluate after saving the frozen selection |

Use the existing cohort rule in every month: journey start, planned arrival,
and changed arrival must fall from local day 2 inclusive to the last calendar
day exclusive; reject the full journey if any retained stop fails. For November
this means November 2 00:00 through November 30 00:00 Europe/Berlin, exclusive
at the end. Check strict event chronology and disjoint journey keys across all
months, including the two training months. Combine training only after checks.

July–October have already been inspected; selection and confirmation scores
are development evidence. November is the only new final test. Do not refit
on September or October in this experiment: all methods keep identical July–August
training information, and October/November shifts stay interpretable.

## Reserved archive and preflight gate

Metadata checked on 2026-09-10 using the pinned
[Hugging Face directory API](https://huggingface.co/api/datasets/piebro/deutsche-bahn-data/tree/3e9e69149f4008d0c24348c51d1ec79b552adaa5/monthly_processed_data?limit=100).

- Revision: `3e9e69149f4008d0c24348c51d1ec79b552adaa5`.
- Path: `monthly_processed_data/data-2025-11.parquet`.
- Size: 587,317,041 bytes (587 MB decimal).
- Expected SHA-256 from the LFS object metadata:
  `1a44f225bed25e600d8a417cf07829951e3cf7d4fa23f5e4e3fb963efc38be7b`.
- [Pinned download](https://huggingface.co/datasets/piebro/deutsche-bahn-data/resolve/3e9e69149f4008d0c24348c51d1ec79b552adaa5/monthly_processed_data/data-2025-11.parquet).

Only directory metadata has been read at protocol creation. November has not
been downloaded or scanned for labels, schema or coverage. Its larger size than
October (105,028,797 bytes) is a reason to check comparability, not proof of a
particular collection change.

Before training, download with the pinned URL and verify checksum/size. A
restricted preflight may inspect Parquet schema and only identifiers, category,
and planned-time columns for station/date coverage. Do not request or summarize
changed times or cancellation outcomes. Record source schema and planned counts
by station/day. Require compatible types/semantics for all existing required
columns and planned-arrival records on at least 20 distinct November dates for
each of the ten stations. This is a minimum coverage screen, not completeness.
Filter to the existing station IDs even if nationwide source coverage expanded.

If preflight fails, pause final evaluation and document the incompatibility.
Do not silently choose a favorable replacement month. A replacement requires a
dated protocol amendment before its labels are opened. If final cleaning leaves
any selected station empty or only one class overall, report the failed gate
and withhold a complete-ten-station success claim.

## Historical baselines and sample support

Fit two baseline candidates on July–August:

1. Global training event frequency, identical for every row.
2. Hierarchical frequency: station/category if >=100 training rows, otherwise
   station if >=100 rows, otherwise global. At each supported local level use
   `(late_count + 100 * global_rate) / (row_count + 100)` to shrink unstable
   estimates toward the global rate. No validation or test counts update this.

The 100-record and 100-pseudo-record choices are fixed engineering defaults,
not reliability guarantees. Report distinct journeys, represented dates, and
event counts alongside row counts. Do not make detailed hour/weekday lookup
groups the minimum support requirement: the audit found these very sparse.

Every classifier uses the same support wrapper: for station/category pairs with
<100 training rows, return the hierarchical baseline and record the fallback
level. Unknown categories follow this rule. Reject invalid hours/weekdays and
stations outside the ten-station scope at the prediction API. Preserve a numeric
prediction for all eligible benchmark rows to allow identical-population scoring.
The later demo must mark fallback estimates as broader historical references,
and must abstain on unsupported station scope or absent station support.

## Small, fixed classifier search

Fit each encoder on training only; one-hot encode the four categorical inputs
with unknown categories ignored. Do not use class weighting, oversampling, or
a hard 0.5 decision threshold for probability evaluation.

- Logistic regression: L2 penalty, C in `[0.1, 1.0, 10.0]`, solver `lbfgs`,
  maximum 2,000 iterations. This learns additive effects shared across groups.
- Histogram gradient boosting classifier: dense one-hot inputs, log loss,
  learning rate 0.1, 100 iterations, max leaf nodes in `[7, 15]`, minimum 100
  samples per leaf, L2 regularization 1.0, no early stopping, random seed 42.
  This tests whether interactions add value with a small bounded search.

Convergence warnings/nonfinite probabilities fail that candidate and must be
reported. Do not expand the search based on disappointing scores. No separate
post-hoc probability calibrator is fitted in this first risk experiment;
calibration is measured. Any later calibration experiment needs its own temporal
fit/selection arrangement and fresh final evaluation.

## Deterministic selection and useful-improvement gate

The primary metric is Brier score: the mean of `(predicted_probability - label)^2`.
Lower is better; units are squared probability, not minutes. Select the better
baseline on September Brier, ties within 1e-12 favor global. Select the best
classifier on September Brier, ties favor logistic regression, then ascending
C or leaf count. Score all methods after applying the fixed support wrapper.

Promote that one classifier for final evaluation only if all conditions hold
on both September and October against the September-selected baseline:

- Relative Brier reduction >=2%: `(baseline - classifier) / baseline >= 0.02`.
- Absolute difference between mean predicted probability and event frequency
  <=0.03 (three percentage points).
- No station with >=1,000 evaluation rows has a Brier increase >0.01.

Otherwise retain the selected baseline. The thresholds are predeclared project
criteria, not an industry standard or proof of improved travel decisions. Do not
switch to another classifier after seeing October. Save all candidate September
scores, the two finalists' October scores, chosen method, training checksums,
protocol hash, package versions, support rules and fitted artifact checksums
before permitting any November outcome read. Treat a zero baseline Brier as a
failed meaningful-relative-comparison gate rather than dividing by zero.

## Final evaluation and uncertainty

On November, report the frozen selection, both baselines and the September-best
classifier on identical eligible rows. No selection, retraining, or parameter
changes follow final outcomes. If the classifier was selected, a confirmed
improvement requires the same three promotion conditions on November and a
paired 95% bootstrap interval for classifier-minus-baseline Brier wholly below
zero. If it fails, report improvement as unconfirmed and do not deploy it as
superior; do not retrospectively change the frozen winner. If baseline was
selected, a better November classifier score remains a diagnostic result only.

Report Brier, relative reduction, log loss (clip probabilities to [1e-6, 1-1e-6]
for this metric only), event frequency, mean prediction, and row/journey counts.
Plot reliability in ten fixed probability bins [0,0.1), ..., [0.9,1], with bin
counts and empty bins explicit. Report scores by station, hour, category and
fallback level; flag groups below 1,000 rows as descriptive and sparse. Do not
claim subgroup statistical significance from multiple unadjusted comparisons.

For paired uncertainty use 2,000 bootstrap replicates, seed 42. Assign every
row of a journey to its parsed local journey-start date. For the ordered dates
inside the test cohort, form all consecutive seven-day windows; sample windows
with replacement, concatenate and truncate to the original number of dates.
Repeated dates duplicate their entire journey groups. Recompute row-weighted
paired score differences using the same sampled rows for both methods and take
2.5/97.5 percentiles. Also report a whole-journey bootstrap as a sensitivity view.
The day blocks retain nearby temporal dependence and never split a journey;
one month contains few effectively independent weeks, so interval precision
and generalization remain limited. Intervals describe sampling variation of
archive labels, not bias from missing observations or schedule fallback.

Use already-fitted predictions for nonzero-only and >=-30-minute label views;
report their changed counts and do not use these views to change the winner.
Include daily coverage and cleaning exclusions alongside final metrics.

## Implementation acceptance criteria

- Keep the existing analysis, regression experiment, and risk audit reproducible.
- Separate label-blind preflight, development selection, and final evaluation
  commands. Final evaluation must refuse missing/inconsistent frozen state.
- Unit/integration tests use synthetic data and verify target boundary, support
  fallback, training-only preprocessing, journey/time separation, deterministic
  promotion rules, probability validity and whole-journey bootstrap membership.
- Run real development and final workflows only after checks pass. Store models,
  downloaded data and generated reports outside Git; keep protocol, source
  metadata, code and a concise final result summary in Git.
- Deliver monthly metrics, reliability/error plots, model card and a reusable
  prediction function returning probability, reference count, fallback level
  and data period. A GUI follows this evaluated slice.

Completion means a reproducible, honestly evaluated comparison, even when the
baseline wins. A claim of practical live usefulness additionally needs the
observation/availability and user-validation work identified by the data audit.
