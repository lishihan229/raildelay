# Raildelay technical specification

Status: Initial design; confirm the data contract against the selected source.

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

The prediction time is departure from the selected upstream stop. Only use
features known at that moment; changed arrival is exclusively a target input.

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

## Implementation sequence

1. Choose and document the dataset; settle the data contract and prediction time.
2. Implement ingestion and validation with a small representative sample.
3. Add reproducible exploratory analysis and static charts.
4. Add the baseline, initial model, and chronological evaluation.
5. Assemble the report and verify the documented workflow from start to finish.

Use one feature branch and pull request per complete slice. Keep `main` stable;
configure the GitHub remote once the repository destination is known.
