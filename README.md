# Raildelay

Python data analysis of railway arrivals at ten selected stations in
Nordrhein-Westfalen. The current slice cleans September 2025 historical
DB-source records and generates four charts, a quality summary, and a report.
A second command compares a median baseline and Ridge regression on July–October
2025 with chronological, journey-separated evaluation.

## Run locally

Use Python 3.12. Run these commands from the project directory. A virtual
environment keeps dependencies isolated; the lock file records tested versions,
and editable installation makes the local `raildelay` package available to Python.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps -e .
```

The September sample is already present in this workspace. On a fresh checkout,
download the pinned 103 MB file. `curl` downloads the file; `sha256sum` computes
its fingerprint so we can check that its contents have not changed.

```bash
mkdir -p data/raw
curl --fail --location --output data/raw/data-2025-09.parquet \
  https://huggingface.co/datasets/piebro/deutsche-bahn-data/resolve/3e9e69149f4008d0c24348c51d1ec79b552adaa5/monthly_processed_data/data-2025-09.parquet
sha256sum data/raw/data-2025-09.parquet
.venv/bin/python -m raildelay
```

Expected SHA-256: `b0a8ff188b26cd22dca7c477c50f3eb7e9b4a0fd918fc5cd56e37e1cd646ccef`.
The workflow verifies this before processing and fails for other releases.
It does not download data automatically. The input stays unchanged; rerunning
replaces only generated outputs at the paths below.

## Outputs

- `data/processed/nrw-arrivals-2025-09.parquet`: 143,734 retained arrival records.
- `reports/generated/2025-09/report.md`: findings, provenance, and limitations.
- Four PNG charts in that report directory: delay distribution, station medians,
  hourly delays with counts, and daily station coverage.
- `quality.json` and three CSV summaries provide the counts behind the charts.

Raw and processed data, generated reports, and environments are excluded from
Git. The report and PNGs can be shared together with their attribution intact.

## Run the model experiment

July, August, and October archives are already downloaded in this workspace.
On a fresh checkout, fetch these three additional pinned files (about 315 MB
combined). The shell loop repeats the same download for each month:

```bash
for raildelay_month in 07 08 10; do
  curl --fail --location --output "data/raw/data-2025-${raildelay_month}.parquet" \
    "https://huggingface.co/datasets/piebro/deutsche-bahn-data/resolve/3e9e69149f4008d0c24348c51d1ec79b552adaa5/monthly_processed_data/data-2025-${raildelay_month}.parquet"
done
.venv/bin/python -m raildelay.experiment
```

The experiment verifies every checksum, parses full journey identifiers,
excludes month-edge journeys, fits on July, and selects on August. September is
development data because it was previously explored. October was held out until
selection was saved. Rerunning reproduces the fixed experiment; it does not make
October unseen again. A future model-selection cycle needs a new test period.

Outputs are in `reports/generated/model/`: `report.md`, three charts, monthly
audits and coverage CSVs, model metrics, and station/hour/category error tables.
Fitted models are excluded from Git in `models/timetable-baselines.joblib`.

The validation-selected baseline had October MAE **7.682 minutes** and RMSE
**15.131 minutes**; Ridge had MAE **7.659** and RMSE **13.097**. The small test MAE
difference is not a reason to change the method selected on validation data.
See [first experiment results](docs/results/first-model.md) and the
[fixed protocol](docs/specs/model-experiment.md).

## Interpretation

The archive contains trains reported through DB's data sources, not exclusively
DB-operated trains. The workflow excludes records labeled Bus, canceled arrivals,
absent arrival pairs, and scheduled arrivals outside September; see the quality
summary for the full sequential accounting.

Arrival delay is computed from arrival timestamps. Missing updates were filled
with planned times upstream, so the 22,686 zero-delay rows are ambiguous.
Negative delays are preserved. The resulting median is 3 minutes and the 90th
percentile is 22 minutes for this retained subset.

Bochum has retained arrivals on 22 days, while the other nine stations have
records on all 30. Collection completeness and changing service patterns must
be investigated before drawing station performance conclusions. Monthly file
boundaries also limit recovery of scheduled arrivals stored in adjacent files.
The model report documents construction-related service changes consistent with
Bochum's pattern. Missing zero-delay provenance and unusual early arrivals remain
limitations of the monthly archive, not values silently corrected by the model.

## Checks

pytest checks cleaning rules and generated outputs using synthetic data. Ruff
checks Python code quality and formatting. The analysis command verifies the
complete workflow on the real input.

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests scripts
.venv/bin/ruff format --check src tests scripts
.venv/bin/python -m pip check
.venv/bin/python -m raildelay
.venv/bin/python -m raildelay.experiment
```

## Specifications and source

Read [product](docs/specs/product.md), [technical](docs/specs/technical.md),
[source decision](docs/specs/data-source.md), and
[sample audit](docs/specs/sample-audit.md) before extending the workflow.

Underlying data: Deutsche Bahn, CC BY 4.0. Archive and processing: Piet Brömmel /
[piebro/deutsche-bahn-data](https://github.com/piebro/deutsche-bahn-data).
The source revision and checksum are recorded in every generated report.

Attach to the project terminal with `tmux attach -t raildelay`.
Detach with `Ctrl-b`, then `d`.
