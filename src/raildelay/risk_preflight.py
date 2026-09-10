"""Check the reserved archive using schema and planned fields only."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from raildelay.analysis import COLUMNS, SOURCE_REVISION, STATIONS, local_times
from raildelay.experiment import ARCHIVES, EXTRA_COLUMNS

TEST_MONTH = "2025-11"
TEST_SHA256 = "1a44f225bed25e600d8a417cf07829951e3cf7d4fa23f5e4e3fb963efc38be7b"
TEST_BYTES = 587317041
PLANNED_COLUMNS = ["eva", "id", "train_type", "arrival_planned_time"]
PROTOCOL = Path("docs/specs/risk-experiment.md")


def digest(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def planned_coverage(frame):
    """Only retained planned dates; never infer completed arrivals or punctuality."""
    planned = local_times(frame["arrival_planned_time"])
    low = pd.Timestamp("2025-11-01", tz="Europe/Berlin")
    high = pd.Timestamp("2025-12-01", tz="Europe/Berlin")
    selected = frame.loc[planned.ge(low) & planned.lt(high)].copy()
    selected["date"] = planned.loc[selected.index].dt.strftime("%Y-%m-%d")
    days = pd.date_range(low, high, inclusive="left").strftime("%Y-%m-%d")
    return pd.crosstab(selected.eva, selected.date).reindex(
        index=list(STATIONS), columns=days, fill_value=0
    )


def run(root=Path("data/raw"), output=Path("reports/generated/risk-preflight")):
    output.mkdir(parents=True, exist_ok=True)
    path = root / f"data-{TEST_MONTH}.parquet"
    report = {
        "month": TEST_MONTH,
        "source_revision": SOURCE_REVISION,
        "source_sha256": digest(path),
        "bytes": path.stat().st_size,
        "protocol_sha256": digest(PROTOCOL),
        "read_columns": PLANNED_COLUMNS,
        "passed": False,
    }

    def fail(message):
        report["failure"] = message
        (output / "preflight.json").write_text(json.dumps(report, indent=2) + "\n")
        raise ValueError(message)

    if report["source_sha256"] != TEST_SHA256 or report["bytes"] != TEST_BYTES:
        fail("November size/checksum differs from the reserved archive")
    reference = root / "data-2025-10.parquet"
    if digest(reference) != ARCHIVES["2025-10"]:
        fail("Reference October checksum mismatch")
    expected = pq.read_schema(reference)
    actual = pq.read_schema(path)
    report["schema"] = str(actual)
    differences = {
        name: str(actual.field(name).type) if name in actual.names else "missing"
        for name in COLUMNS + EXTRA_COLUMNS
        if name not in actual.names or actual.field(name).type != expected.field(name).type
    }
    if differences:
        report["schema_differences"] = differences
        fail("Required November fields differ from the audited schema")
    frame = pd.read_parquet(path, columns=PLANNED_COLUMNS, filters=[("eva", "in", list(STATIONS))])
    coverage = planned_coverage(frame)
    coverage.to_csv(output / "planned-coverage.csv")
    report["selected_planned_field_rows"] = len(frame)
    report["planned_days_per_station"] = {
        STATIONS[eva]: int(count) for eva, count in coverage.gt(0).sum(axis=1).items()
    }
    report["planned_rows_per_station"] = {
        STATIONS[eva]: int(count) for eva, count in coverage.sum(axis=1).items()
    }
    if min(report["planned_days_per_station"].values()) < 20:
        fail("At least one station has fewer than 20 planned-arrival dates")
    report["passed"] = True
    (output / "preflight.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    run()
