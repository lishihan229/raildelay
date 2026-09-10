# Raildelay technical specification

Status: Exploratory analysis and first chronological model checkpoint implemented.
The concrete experiment is specified in `model-experiment.md`.
The second risk experiment is also implemented and evaluated on November;
see `../results/risk-model.md` for results and the failed calibration gate.

## Approach

Build a small local Python pipeline: ingest, validate, prepare, analyze, train,
evaluate, and report. Keep reusable logic in Python modules. Notebooks may
support exploration, but the final workflow must run without manual notebook edits.

## NRW source integration

Use the historical archive described in `data-source.md`. The September sample
is inspected in `sample-audit.md`; `requirements-inspection.txt` pins its reader.
Parquet is a compressed tabular format. Pin the source
revision and file checksum so later upstream reprocessing cannot silently change
results. Start with one month; expand after measuring memory and disk usage.

Resolve the stations listed in the product spec to source station identifiers
from actual metadata. Match names during discovery, then filter by identifiers;
preserve accents and distinguish Köln Hbf from Köln Messe/Deutz. Do not invent
station IDs. Record a coverage table by station and day before choosing periods.

Treat source-local timestamps as Europe/Berlin and explicitly handle ambiguous
or nonexistent daylight saving times. Use normalized timestamps for chronology
and local time for hour-of-day features. Keep source values for auditing.

The target is archive-reported arrival delay with schedule fallback, as documented
in `sample-audit.md`. Missing updates have already been replaced by planned times
upstream; zeros cannot be treated as verified punctuality. Never mix arrival and
departure delay into one target. Historical final records do not prove when a feature became available:
omit upstream departure-delay features unless availability can be established.
Schedule-only features provide an initial alternative within the chosen
departure-time prediction task.

## Proposed tools

- Python with a project-local virtual environment for isolated dependencies.
- pandas for tabular data preparation and aggregation.
- matplotlib and seaborn for static charts.
- scikit-learn for preprocessing, baseline prediction, and an initial model.
- pytest for meaningful validation and pipeline checks; Ruff for code checks.

Choose a supported Python version and record dependency versions when the first
implementation begins. The source-selection environment currently uses Python
3.12 and the minimal dependencies in `requirements-inspection.txt`.

## Lean structure

Initial files:

```text
AGENTS.md
docs/specs/product.md
docs/specs/technical.md
```

Add `pyproject.toml`, `src/raildelay/`, `tests/`, `data/`, and `reports/` only
when the first implementation needs them. Add notebooks only for actual
exploration. Ignore downloaded datasets, virtual environments, secrets, and
generated model artifacts before staging any code or data.

## Candidate data contract

The intended observation is a train journey's arrival at a specified stop,
uniquely identified by service date, trip identifier, and stop sequence.

- Required for the proxy target: planned and archive changed arrival timestamps.
- Required for meaningful grouping: station identifier and service date.
- Candidate predictors: scheduled arrival hour, weekday, route, station, and
  departure delay where it is known at the chosen prediction time.
- Preserve source identifiers and document timezone handling, daylight saving
  transitions, and journeys crossing midnight.

Compute signed proxy delay in minutes as archive changed minus planned arrival;
negative values indicate early arrivals. Do not silently clip them. Count missing
arrival pairs and cancellations separately; they are not zero-delay records.
Document how duplicates, implausible timestamps, and missing fields are handled.
If source data cannot support this target, revise both specs before implementation.

## Validation and preparation

Keep raw inputs immutable. Record source location, retrieval date, license,
schema, and row counts. Validate required columns, timestamp parsing, identifiers,
duplicates, and target availability. Produce a quality summary of every exclusion.
Fail with actionable messages when required fields are absent or no usable rows
remain. Never silently download a different dataset as a fallback.

## Modeling and evaluation

### First implementation checkpoint: exploratory analysis

Before modeling, deliver `python -m raildelay` for the pinned September 2025
sample. Verify its checksum, load only the ten audited EVA identifiers, and
account for exclusions in this order: missing stop identifiers, all occurrences
of duplicate station/stop keys, Bus records, missing category, canceled arrivals,
unknown cancellation status, missing/invalid arrival timestamps, and scheduled
arrivals outside September. Reject ambiguous/nonexistent Europe/Berlin local
times rather than guessing an offset. Keep signed delays, flag equal timestamps
as ambiguous zeros, and flag absolute delays above 24 hours without removing them.

Export the retained rows to Parquet and a quality summary to JSON. Produce four
PNG charts: delay distribution, station medians with counts, local-hour medians
with counts, and station-by-day retained arrival counts. Station comparisons
remain in fixed geographic-list order, not a performance ranking. Plot full
coverage including zero-count days. Show a central histogram with the excluded
tail count explicitly stated; all statistics retain the tails.

The generated Markdown report must include exclusions, missing values, coverage,
summary metrics, chart links, provenance, and limitations. Cover cleaning and
time handling with synthetic tests and verify a complete run on the pinned input.
Modeling, multi-month evaluation, and causal investigation of coverage changes
remain subsequent checkpoints.

The intended use is planning before departure. The implemented benchmark uses
only station, planned arrival hour/weekday, and published train category.
Historical plan snapshots are unavailable, so exact departure-time availability
cannot be verified. Changed arrival is exclusively a target or boundary-check
input. See `model-experiment.md` for the fixed periods and permitted features.

Split chronologically into training, validation, and final test periods. Keep
records from the same train journey in one partition and ensure training labels
would have been available before the next partition begins. Choose split dates
after examining coverage, then freeze them before comparing models.

Fit imputation and categorical encoding on training data through a scikit-learn
pipeline. Handle unseen categories explicitly. Begin with a training-median
DummyRegressor and a simple regularized regression model. Use validation data
for model choices, then evaluate the final choice on the untouched test period.

Report mean absolute error in minutes as the primary metric, root mean squared
error as a secondary metric, and sample counts alongside error breakdowns by
time and station or route. Record random seeds where applicable. Do not claim
causality from correlations or generalization beyond the dataset's coverage.

## Outputs and verification

The first implementation should produce a data quality summary, at least three
saved charts, baseline and model metrics, and a readable report of conclusions
and limitations. Document commands and dependencies in a README when code exists.

Test delay calculations, timezone and missing-value handling, invalid input,
chronological and journey separation, and a small end-to-end run using synthetic
fixtures. Run relevant tests and code checks before declaring implementation
complete. Synthetic fixtures support tests; analytical claims require real data.

## Next application checkpoint (direction set 2026-09-10)

Data-suitability command: `python -m raildelay.risk_audit`, specified in
`risk-data-audit.md`. It reuses the existing cleaning and journey cohorts, reports
15-minute proxy-label sensitivity, and checks July-only input support for later
months. Outputs are isolated in `reports/generated/risk-audit/`; it fits no models.
The decision and next data gates are in `../results/risk-data-suitability.md`.

Keep the completed regression experiment and its frozen results reproducible.
The proposed next target is the probability of archive-reported arrival delay
of at least 15 minutes for a planned station/time/category. Before implementation,
follow the fixed [risk experiment protocol](risk-experiment.md), which covers
label quality, cancellations, prediction-time feature availability, split dates,
baseline fallbacks, sample support and the practical improvement threshold.
Its label-blind preflight, development selection and final evaluation must be
separate entrypoints. Implemented commands are `raildelay.risk_preflight` and
`raildelay.risk_experiment develop|evaluate`. November compatibility passed and
final evaluation is complete; no further selection may treat it as unseen.

`risk_model.py` provides the training-only hierarchical references, classifiers,
probability/support prediction API, promotion gate and paired bootstrap.
`risk_report.py` exports probability reliability and group errors. Numerical
training uses two threads through the directly declared `threadpoolctl` dependency.

Use a fresh final test period and fit preprocessing, historical aggregates,
model selection, and any probability calibration without final-test data.
Compare probability predictions with training-only frequency baselines. Specify
Brier score (mean squared probability error) as the proposed primary metric,
with calibration plots, event rates, sample counts, and uncertainty estimates
that respect journey/time dependence. Classification accuracy alone is not
adequate. Report subgroup and later-period behavior, and separately disclose
that the noncanceled-arrival target omits cancellation risk.

Once the data and evaluation gates pass, expose the selected predictor through
a reusable Python function and a thin local interface. Validate inputs, handle
unsupported categories or insufficient coverage explicitly, and display data
period and archive-proxy limitations. Choose the UI tool at that checkpoint.
Test the prediction contract and a representative end-to-end user flow. Add
GitHub CI for synthetic tests and code checks when the remote is configured;
do not require downloaded datasets or private credentials for these checks.

Deliver a concise model card, reproducible commands, and a portfolio case study
with measured results and demo evidence. New infrastructure must serve this
application; live ingestion and public deployment require their own scope.

## Implementation sequence

1. Choose and document the dataset; settle the data contract and prediction time.
2. Implement ingestion and validation with a small representative sample.
3. Add reproducible exploratory analysis and static charts.
4. Add the baseline, initial model, and chronological evaluation.
5. Assemble the report and verify the documented workflow from start to finish.

Use one feature branch and pull request per complete slice. Keep `main` stable;
configure the GitHub remote once the repository destination is known.
