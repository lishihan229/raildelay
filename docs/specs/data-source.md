# NRW data source decision

Checked: 2026-09-07. Preferred source identified; no data downloaded or validated yet.

## Preferred historical archive

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
