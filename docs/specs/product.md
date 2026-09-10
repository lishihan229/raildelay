# Raildelay product specification

Status: July–November 2025 validated for ten NRW stations. Both regression and
risk-classification experiments are complete; see `../results/first-model.md`
and `../results/risk-model.md`. The risk classifier improves Brier error but
fails the predeclared calibration gate; live application reliability is unresolved.

Implementation checkpoint: September cleaning, quality accounting, four static
charts, and a reproducible report are implemented. The model checkpoint includes
a median baseline, Ridge regression, chronological validation, a reserved October
evaluation, and error reports. A live departure-time system is outside this
benchmark because historical feature-availability timestamps are not preserved.

## Purpose

Build a credible machine learning portfolio project for the author's CV that
also supports a practical travel-planning decision. Use Python to understand
railway delays, evaluate predictions honestly, and deliver a small usable
application backed by reproducible evidence. Prefer demonstrated user value and
sound engineering over adding algorithms or infrastructure for appearance.

Direction updated on 2026-09-10. The completed first experiment remains a
retrospective benchmark; the following application is the next proposed slice,
not an already validated capability.

The [risk data audit](../results/risk-data-suitability.md) gives a conditional go
for a historical proxy-risk experiment, not verified live commuter risk.
Observation provenance is unavailable in the monthly files. The next experiment
must use sparse-group fallbacks and a fresh final test period; a practical
reliability claim additionally needs better observation/availability evidence.

For this archive, “arrival delay” means archive-reported arrival delay with
schedule fallback when updates are absent. It is a proxy for actual delay;
the report must explain that apparent punctuality can include missing updates.

## Geographic scope and data source

Focus on Deutsche Bahn timetable data for Nordrhein-Westfalen (NRW), Germany.
The initial required stations are Aachen Hbf, Düsseldorf Hbf, Köln Hbf, and
Essen Hbf. Proposed additional stations are Duisburg Hbf, Dortmund Hbf,
Bochum Hbf, Wuppertal Hbf, Bonn Hbf, and Mönchengladbach Hbf, subject to coverage.
This is a selected-station study, not a claim of complete NRW coverage.

Use the historical archive `piebro/deutsche-bahn-data` as the preferred dataset;
see `data-source.md` for provenance and validation gates. Start with one month
for ingestion and charts, then expand to at least three consecutive months for
the first model evaluation if coverage and local resources permit.

Interpret “Deutsche Bahn data” as the source of the records. Do not assume every
train in the source is operated by DB. Preserve train categories for separate
regional, suburban, and long-distance comparisons where supported. A DB-only
operator analysis requires reliable operator metadata first.

## Intended user and questions

The intended application user is an NRW commuter planning an arrival before
departure. The author also uses the project to demonstrate a complete data and
machine learning workflow to potential employers.

The proposed first application answers: "For this station, planned arrival
time, and train category, what is the risk of at least 15 minutes of arrival
delay?" Its purpose is to inform a commuter's choice of an earlier service when
arrival time matters. Initially this is a historical risk estimate for a group
of services, not a live prediction for an identified train. Show sample support,
data period, and limitations alongside the estimate. Do not infer connection
success, recommend an exact safety buffer, or treat cancellations as punctual
arrivals; those require separate targets and evidence.

- How do arrival delays vary by station, route, time of day, and day of week?
- Where are delays frequent or severe, and how much data supports each finding?
- Can information available at departure improve predictions over a simple baseline?

The implemented approximation uses timetable features intended to be available
before departure. It is explicitly retrospective: final plans in the archive
cannot prove what was displayed at a particular historical departure time.

## First complete slice

1. Validate an NRW subset of the preferred historical archive and document its
   source, license, time coverage, timestamp semantics, and limitations.
2. Validate and clean a local dataset while keeping the original unchanged.
3. Produce a data quality summary and exploratory charts showing delay
   distributions, variation over time, and station or route comparisons.
4. Predict arrival delay in minutes using only inputs available at departure.
5. Compare a simple model against a naive baseline on a later, held-out period.
6. Publish a reproducible written report with charts, metrics, and limitations.

## Acceptance criteria for the first slice

- A documented command sequence reproduces the report from the selected data.
- The report states row counts, missing values, exclusions, and time coverage.
- Coverage is checked for all four required stations; missing coverage is
  reported explicitly and resolved before calling the first slice complete.
- At least three labeled charts answer the exploratory questions; comparisons
  include sample counts and do not imply that sparse groups are representative.
- Baseline and model are evaluated on the same chronological test period with
  mean absolute error in minutes and an explanation of errors and limitations.
- No information recorded after the prediction time is used as a model input.
- An improvement over baseline is investigated, not required or promised.
- Relevant validation and automated checks pass.

## Outside the first slice

Live feeds, production deployment, alerts, deep learning, multi-network support,
and an interactive dashboard. A dashboard can follow once the analysis works.

## Next slice: practical delay-risk application

The second experiment is now specified in [risk-experiment.md](risk-experiment.md):
train on July–August, select on September, confirm on October, and reserve
November 2025 for final evaluation. This experiment is complete: preflight and
integrity checks passed, and November is now used. The historical baseline
remains selected because the classifier failed the calibration gate. See
[results and next research question](../results/risk-model.md). A new experiment
needs a fresh final period and a predeclared training/calibration design.

1. Validate the application data contract before modeling. Investigate how
   missing updates, cancellations, and changing station coverage affect the
   15-minute risk target. If observation provenance cannot be established,
   retain explicit archive-proxy wording and assess whether a better source or
   prospective collection is needed before claiming practical reliability.
2. Specify a second experiment before fitting: usable inputs, prediction time,
   chronological periods, baseline rules, primary metric, and success criteria.
   Select and validate a fresh final test period; October 2025 is already used.
3. Compare a simple historical frequency baseline, including supported groups,
   with a small number of justified classifiers. Assess probability accuracy,
   calibration, temporal stability, and performance across stations/categories.
   Calibration means that events predicted at roughly 20% risk should occur
   roughly 20% of the time. Keep records from one journey in one partition.
4. Build a small local interface after the data and evaluation gates pass. Let
   a user enter station, planned arrival date/time, and train category and see
   estimated risk, supporting context, and an explicit warning or no estimate
   for unsupported inputs. No live-feed claim without live validation.
5. Package a portfolio release: reproducible setup, tests and GitHub CI,
   documented model/data limitations, screenshots or a short demo, and a case
   study explaining the user problem, baselines, results, and design decisions.
   Public hosting is a later delivery choice, not a prerequisite for this slice.

Acceptance: reproduce evaluation on a fresh chronological test period, document
whether the model adds useful value over simple rules, and demonstrate the full
input-to-estimate flow with limitations visible. Predeclare the practical
improvement threshold in the experiment protocol. If ML does not beat the
baseline, retain the baseline and explain the result; do not present complexity
as success. A usable historical demo alone does not establish live reliability.

## Open decisions

- How to obtain observation/availability evidence for practical reliability,
  and how representative-user feedback will validate the historical demo's usefulness.
- A fresh final period and temporal calibration design for the next experiment.
- Sources that retain collection times and historical feature availability.
- Minimum group sizes and uncertainty estimates for stronger comparisons.
- Whether a later visualization interface should use Streamlit.

Resolve dataset-dependent decisions before building the ingestion pipeline.
