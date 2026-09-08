# Raildelay product specification

Status: July–October 2025 archives validated for ten NRW stations. First
chronological model experiment complete; see `model-experiment.md` and
`../results/first-model.md`.

Implementation checkpoint: September cleaning, quality accounting, four static
charts, and a reproducible report are implemented. The model checkpoint includes
a median baseline, Ridge regression, chronological validation, a reserved October
evaluation, and error reports. A live departure-time system is outside this
benchmark because historical feature-availability timestamps are not preserved.

## Purpose

Use Python to understand railway delays, predict arrival delay, and communicate
the findings through clear visualizations. Start with a reproducible local
analysis before adding a dashboard or deployment.

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

The initial user is the project author learning and demonstrating a complete
data analytics and machine learning workflow.

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

## Open decisions

- A fresh evaluation month for any subsequent model-selection cycle.
- Sources that retain collection times and historical feature availability.
- Minimum group sizes and uncertainty estimates for stronger comparisons.
- Whether a later visualization interface should use Streamlit.

Resolve dataset-dependent decisions before building the ingestion pipeline.
