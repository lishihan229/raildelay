# NRW data source decision

Checked: 2026-09-07. September 2025 downloaded and audited; selected for initial
exploration. See `sample-audit.md` for the pinned release, verified station
coverage, reproducible audit, and remaining modeling limitations.

Update 2026-09-08: July, August, and October also downloaded and checksum-verified.
All four schemas match. Full journey keys and chronological event separation
were checked for the model cohorts. See `model-experiment.md` and
`../results/first-model.md`; collection-time provenance remains unavailable.

Update 2026-09-10: the [risk suitability audit](../results/risk-data-suitability.md)
quantifies 15-minute target sensitivity and input support on these same four
months. This source supports a retrospective proxy experiment conditionally;
it does not establish actual commuter-risk probabilities. Missing-update
provenance, cancellation-risk coverage, and historical feature availability
remain gates for practical reliability.

## Preferred historical archive

The second [risk experiment](risk-experiment.md) reserves November 2025 at the
same pinned revision. Directory metadata confirms a 587,317,041-byte file with
SHA-256 `1a44f225bed25e600d8a417cf07829951e3cf7d4fa23f5e4e3fb963efc38be7b`.
These are remote metadata, not a verified local download. Schema, selected-station
coverage and compatibility have not yet been established; the size increase
relative to October requires a label-blind preflight before model fitting.

[piebro/deutsche-bahn-data](https://github.com/piebro/deutsche-bahn-data) is a
community archive of DB API records, distributed through
[Hugging Face](https://huggingface.co/datasets/piebro/deutsche-bahn-data).
The maintainer documents monthly Parquet files, CC BY 4.0 data licensing,
German local timestamps, and collection gaps. Attribute Deutsche Bahn and
the archive maintainer; preserve the release's accompanying license information.

Documented fields include `eva`, `station_name`, `train_type`, `train_number`,
`line_number`, journey and stop identifiers, planned and changed arrival/departure
times, and separate arrival/departure cancellation flags. Treat these as an
expected schema until inspected. The archive documents schema revisions, so
pin a revision rather than relying on changing file names alone.

## Official source context

[DB's open-data page](https://data.deutschebahn.com/opendata) describes Timetables
as access to current schedules and deviations, and StaDa as station metadata.
For this historical project, prefer the archive; a live collection service would
require a separate scope decision.

## Acceptance gates before ingestion implementation

The sample and model audits resolve file sizes, checksums, schema consistency,
station presence, initial missing-value checks, adjacent-month cohorts, and full
journey identity. Remaining limitations concern hourly completeness, historical
availability, and reconstructed arrival labels. The original checklist follows.

- Inspect one monthly file's schema, size, and station inventory.
- Verify the four required stations and assess the proposed additional stations.
- Record revision, download URL, checksum, license, and actual time coverage.
- Select a month with useful coverage, then assess consecutive months for ML.
- Verify timestamp and changed-time semantics against collection/processing code.
- Determine whether missing changes indicate missing observations or punctuality.
- Quantify gaps and cancellations separately from completed arrivals.
- Confirm journey keys and whether any predictors have observation timestamps.
- If no reliable operator field exists, label results as DB-source station data,
  not a performance comparison restricted to DB-operated trains.

Update both core specs if inspection requires a different target or scope.
