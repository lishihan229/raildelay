# Second experiment: measured improvement, unresolved probability bias

Completed on 2026-09-10 under the frozen
[risk experiment protocol](../specs/risk-experiment.md). The protocol retains
its pre-implementation status text as a historical record; this document records
completion. November outcomes have now been evaluated and are no longer unseen.

## Outcome

The selected method remains the smoothed station/category historical baseline
with station/global fallbacks. The best classifier is histogram gradient boosting
with 15 leaves per tree. It reduces Brier error consistently, but fails the
predeclared probability-calibration gate. No method is validated for live use.

On September, the best tree model reduced Brier by 2.65% against the hierarchical
baseline and had a 2.45-percentage-point mean calibration gap, passing the gate.
On October, it reduced Brier by 2.99% but underestimated the event frequency by
4.03 points, above the fixed three-point limit. The baseline also underestimated
October risk (4.18 points). Baseline retention is an experimental selection rule,
not proof that the baseline is reliable enough for travel decisions.

The frozen November evaluation contains **140,950 arrivals from 77,372 journeys**:

| Method | Brier (lower is better) | Log loss | Mean predicted risk |
| --- | ---: | ---: | ---: |
| Global frequency | 0.153993 | 0.489041 | 14.44% |
| Selected hierarchical frequency | 0.142756 | 0.452565 | 13.93% |
| Best classifier: histogram, 15 leaves | 0.138817 | 0.441591 | 14.06% |

The observed archive event frequency is **18.72%**. The classifier's November
Brier is **2.76% lower** than the selected baseline, but its mean risk is too
low by **4.66 percentage points**; the baseline's gap is 4.79 points.
No station with at least 1,000 test rows exceeds the permitted 0.01 Brier
degradation for the classifier. The calibration criterion still fails.

The paired seven-day block bootstrap gives a 95% interval of
**[-0.004678, -0.003121]** for classifier-minus-baseline Brier; the whole-journey
sensitivity interval is [-0.004374, -0.003460]. Both use 2,000 replicates and seed
42. This supports an error reduction within this dataset under the resampling
assumptions, but does not override the failed gate. One month has few independent
weeks and these intervals do not address label bias or live generalization.

## Data and separation

November's pinned checksum and required field types match the preflight
contract. The preflight read only station/stop IDs, train categories and planned
arrival times. All ten stations have planned-arrival records on all 30 days.
The 587,317,041-byte file yields 215,849 selected source records, comparable in
order of magnitude to the existing station subset despite the larger full file.
The audit does not establish why the overall archive grew.

Cleaning retains 150,857 November arrivals, including 24,597 ambiguous zeros.
Sequential exclusions: 11,713 Bus rows, 9,515 canceled arrivals, 43,726
missing/invalid arrival pairs and 38 scheduled outside November. There are no
other exclusions. The established journey-boundary rule removes another 9,907
rows, leaving the 140,950 evaluation records. All ten stations have clean arrivals
on every day. Counts do not establish hourly completeness or cancellation rates.

All seven candidates fit on July–August only (286,047 cohort arrival rows), with
no candidate failures. September selects candidates; October confirms or rejects
promotion. Full journey/event separation holds across all five months. November
labels were first read after the selected method, source/code/protocol/package
hashes and fitted artifacts were saved. Frozen state and data checks passed.

## Interpretation for the application and portfolio

There is useful predictive structure beyond a coarse historical frequency rule.
However, both baseline and classifier are biased low in later months. The next
research question is whether more recent training and a separately fitted
probability calibration step reduce this bias without leakage. Changing event
frequency and ambiguous-zero prevalence are plausible contributors, not proven
causes. Simply showing the present scores in a commuter UI would hide the gap.

A subsequent experiment should predeclare a rolling training/calibration
design, compare against a recent-frequency baseline, and reserve a new final
period before looking at its labels. Do not tune on November while continuing
to describe November as held out. Practical reliability also still requires
observation provenance and feature-availability validation from the source audit.

For a portfolio, this result demonstrates a full probability-model workflow:
data-quality gates, chronological evaluation, simple and learned comparisons,
calibration diagnostics, dependent-data uncertainty, reproducible artifacts and
an explicit decision not to promote an inadequately calibrated model.

## Reproduction and artifacts

See the [README](../../README.md) for downloads and commands. The entrypoints are
`raildelay.risk_preflight`, `raildelay.risk_experiment develop`, and
`raildelay.risk_experiment evaluate`. Development refuses to reselect after the
test-opened marker is written; evaluation can reproduce an unchanged frozen run.

Generated `reports/generated/risk-model/report.md` is the model card with three
charts. Its directory also contains the frozen selection, final metrics and
uncertainty, reliability bins, station/hour/category/fallback errors, daily
coverage and prediction support context. Fitted models reside locally in
`models/risk-models.joblib`. These artifacts and raw data are excluded from Git.

31 synthetic tests pass, including prediction support, training-only encoding,
input validation, selection gates, whole-journey resampling and a complete
development/evaluation/report/frozen-rerun integration test. Ruff code/format and
dependency checks pass. The real preflight, all seven development fits and final
evaluation completed; reliability and station-error charts were visually checked.

Source: Deutsche Bahn data, CC BY 4.0, archived/processed by Piet Brömmel / piebro,
revision `3e9e69149f4008d0c24348c51d1ec79b552adaa5`. November SHA-256:
`1a44f225bed25e600d8a417cf07829951e3cf7d4fa23f5e4e3fb963efc38be7b`.
