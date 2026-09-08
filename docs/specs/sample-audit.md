# September 2025 source-selection audit

Inspected locally on 2026-09-07 with Python 3.12 and PyArrow 25.0.1.

Follow-up on 2026-09-08: July, August, and October have now been inspected and
used in the first model experiment. See `../results/first-model.md` for that
decision and the investigation of Bochum's September gaps. The audit below
records the initial source-selection state.

## Decision

Use September 2025 from `piebro/deutsche-bahn-data` for the first exploratory
slice. It covers our required stations and is manageable locally. Treat model
labels as archive-reported arrival delay with schedule fallback, not verified
physical arrival measurements. Do not train until the limitations below are
incorporated into the preprocessing and report.

For a later three-month experiment, July–September 2025 is a candidate
(approximately 313 MB total). Only September has been downloaded and inspected;
validate July and August before selecting chronological partitions. This period
does not establish year-round or current performance.

## Pinned input

- Dataset revision: `3e9e69149f4008d0c24348c51d1ec79b552adaa5`.
- File: `monthly_processed_data/data-2025-09.parquet`.
- Download: [pinned monthly file](https://huggingface.co/datasets/piebro/deutsche-bahn-data/resolve/3e9e69149f4008d0c24348c51d1ec79b552adaa5/monthly_processed_data/data-2025-09.parquet).
- Size: 102,785,054 bytes (102.8 MB).
- SHA-256: `b0a8ff188b26cd22dca7c477c50f3eb7e9b4a0fd918fc5cd56e37e1cd646ccef`.
- Local checksum matches the pinned Hugging Face file metadata.
- Local path: `data/raw/data-2025-09.parquet`, excluded from Git.
- Attribution: Deutsche Bahn (underlying data), Piet Brömmel / piebro
  (archive and processing). Dataset metadata states CC BY 4.0; see
  [dataset card](https://huggingface.co/datasets/piebro/deutsche-bahn-data/tree/3e9e69149f4008d0c24348c51d1ec79b552adaa5).

## Observed coverage

The file has 1,952,591 records, 107 distinct station names, and 18 columns.
The ten selected stations contain 216,926 records with no duplicate `(eva, id)`
keys. Each has records on all 30 days using the archive's `time` field.
Daily presence does not establish complete hourly coverage or complete service capture.

| Station | Source EVA identifier | All records | Noncanceled arrival pairs | Arrival canceled |
| --- | --- | ---: | ---: | ---: |
| Aachen Hbf | `08000001` | 12,255 | 6,940 | 613 |
| Düsseldorf Hbf | `08000085` | 44,763 | 29,731 | 1,653 |
| Köln Hbf | `08000207` | 37,470 | 32,037 | 2,330 |
| Essen Hbf | `08000098` | 24,209 | 18,659 | 864 |
| Duisburg Hbf | `08000086` | 22,244 | 18,571 | 1,229 |
| Dortmund Hbf | `08000080` | 31,466 | 17,642 | 987 |
| Bochum Hbf | `08000041` | 4,982 | 4,356 | 373 |
| Wuppertal Hbf | `08000266` | 17,537 | 13,374 | 826 |
| Bonn Hbf | `08000044` | 10,029 | 7,062 | 234 |
| Mönchengladbach Hbf | `08000253` | 11,971 | 7,155 | 403 |

Counts precede train-category filtering. A noncanceled arrival pair means both
arrival fields are populated, not that the arrival was independently observed.
Remaining records lack an arrival pair, including possible origin-only stops;
do not classify every such record as a collection failure.

## Data decisions and outstanding checks

The [upstream processor inspected at revision b52121d](https://github.com/piebro/deutsche-bahn-data/blob/b52121da513bda3b8a2cc8b5cd43eb23c36a5534/scripts/create_monthly_data_release.py)
prefers departure values for `delay_in_min` and `time`. It substitutes planned
times when changes are absent and retains the latest collected change per stop.
Collection timestamps are not retained in the monthly output. This is inspected
current processing logic, not proof of the exact code that built this release.

- Derive the arrival target from `arrival_change_time - arrival_planned_time`.
  Among selected noncanceled arrival pairs, 32,257 have equal timestamps;
  the monthly file cannot distinguish an absent update from an on-time report.
  Keep these labeled as ambiguous zeros and explain the limitation. Excluding
  all zeros would also bias the target population; raw records are needed to
  study observation provenance more closely.
- Exclude arrival cancellations and absent arrival pairs from arrival regression;
  report them separately. Cancellation flags are archive classifications.
- There are 20,332 `Bus` records in the selected subset. Exclude them from
  train-only analysis and report the exclusion. Review other categories before
  grouping them; no explicit operator column is present.
- Bochum has 469–511 records per day on September 1–5, then 43–136 thereafter.
  Investigate service changes versus collection coverage before ranking stations;
  this audit does not establish a cause.
- Timestamp columns have no timezone metadata. Apply the documented Europe/Berlin
  interpretation explicitly; September avoids a daylight saving clock change.
- Use planned arrival dates for analytical cohorts. File membership uses the
  archive's mixed arrival/departure `time`, so inspect adjacent-month boundaries.
- Validate journey identifiers and their service-date component before splitting
  data. Do not use final upstream delay or destination changes as departure-time
  predictors without evidence they were known then. Initially use calendar and
  station features; schedule fields still need a retrospective-data limitation.

## Reproduce the audit

From the project directory, create a virtual environment if absent, then install
the inspection dependency. This isolates it from system Python:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-inspection.txt
```

Download the pinned file above into `data/raw/`, then run:

```bash
sha256sum data/raw/data-2025-09.parquet
.venv/bin/python scripts/inspect_sample.py data/raw/data-2025-09.parquet
```

The script prints schema, checksum, station identifiers, daily counts,
cancellation counts, missing arrival pairs, and duplicate-key counts as JSON.
It reads batches and keeps selected stop keys in memory for duplicate detection.
