"""Prepare and summarize the audited September 2025 NRW archive."""

import hashlib
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

SOURCE_REVISION = "3e9e69149f4008d0c24348c51d1ec79b552adaa5"
SOURCE_SHA256 = "b0a8ff188b26cd22dca7c477c50f3eb7e9b4a0fd918fc5cd56e37e1cd646ccef"
SOURCE_URL = (
    "https://huggingface.co/datasets/piebro/deutsche-bahn-data/resolve/"
    f"{SOURCE_REVISION}/monthly_processed_data/data-2025-09.parquet"
)
STATIONS = {
    "08000001": "Aachen Hbf",
    "08000085": "Düsseldorf Hbf",
    "08000207": "Köln Hbf",
    "08000098": "Essen Hbf",
    "08000086": "Duisburg Hbf",
    "08000080": "Dortmund Hbf",
    "08000041": "Bochum Hbf",
    "08000266": "Wuppertal Hbf",
    "08000044": "Bonn Hbf",
    "08000253": "Mönchengladbach Hbf",
}
COLUMNS = [
    "eva",
    "station_name",
    "id",
    "train_type",
    "arrival_planned_time",
    "arrival_change_time",
    "arrival_is_canceled",
]
DAYS = pd.date_range("2025-09-01", "2025-09-30").strftime("%Y-%m-%d").tolist()


def load_sample(path: Path) -> tuple[pd.DataFrame, dict]:
    """Verify the exact source bytes before reading only selected station rows."""
    with path.open("rb") as source:
        checksum = hashlib.file_digest(source, "sha256").hexdigest()
    if checksum != SOURCE_SHA256:
        raise ValueError("Input checksum differs from the audited September 2025 release.")
    parquet = pq.ParquetFile(path)
    missing = set(COLUMNS) - set(parquet.schema_arrow.names)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    frame = pd.read_parquet(path, columns=COLUMNS, filters=[("eva", "in", list(STATIONS))])
    return frame, {
        "source_url": SOURCE_URL,
        "source_revision": SOURCE_REVISION,
        "source_sha256": checksum,
        "source_bytes": path.stat().st_size,
        "source_rows": parquet.metadata.num_rows,
    }


def local_times(values: pd.Series) -> pd.Series:
    """Parse source wall-clock times; do not invent DST offsets."""
    parsed = pd.to_datetime(values, errors="coerce")
    if parsed.dt.tz is not None:
        raise ValueError("Expected naive Europe/Berlin source timestamps.")
    return parsed.dt.tz_localize("Europe/Berlin", ambiguous="NaT", nonexistent="NaT")


def prepare(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    missing = set(COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    frame = frame.loc[frame["eva"].isin(STATIONS)].copy()
    absent = set(STATIONS) - set(frame["eva"])
    if absent:
        raise ValueError(f"Selected stations absent: {[STATIONS[eva] for eva in sorted(absent)]}")
    frame["source_station_name"] = frame["station_name"]
    frame["station_name"] = frame["eva"].map(STATIONS)
    quality = {
        "selected_rows": len(frame),
        "missing_values_before_cleaning": {
            column: int(frame[column].isna().sum()) for column in COLUMNS
        },
        "source_category_counts": {
            str(key): int(value)
            for key, value in frame["train_type"].fillna("<missing>").value_counts().items()
        },
        "exclusions": {},
    }
    excluded = pd.Series("", index=frame.index)

    def exclude(reason, mask):
        selected = excluded.eq("") & mask.fillna(False)
        quality["exclusions"][reason] = int(selected.sum())
        excluded.loc[selected] = reason

    exclude("missing_stop_id", frame["id"].isna() | frame["id"].eq(""))
    exclude("duplicate_station_stop_key", frame.duplicated(["eva", "id"], keep=False))
    exclude("bus", frame["train_type"].eq("Bus"))
    exclude("missing_train_category", frame["train_type"].isna() | frame["train_type"].eq(""))
    exclude("arrival_canceled", frame["arrival_is_canceled"].eq(True))
    exclude("unknown_cancellation_status", ~frame["arrival_is_canceled"].isin([True, False]))
    planned = local_times(frame["arrival_planned_time"])
    changed = local_times(frame["arrival_change_time"])
    exclude("missing_or_invalid_arrival_pair", planned.isna() | changed.isna())
    in_month = planned.ge(pd.Timestamp("2025-09-01", tz="Europe/Berlin")) & planned.lt(
        pd.Timestamp("2025-10-01", tz="Europe/Berlin")
    )
    exclude("planned_arrival_outside_september", ~in_month)
    frame["planned_arrival_utc"] = planned.dt.tz_convert("UTC")
    frame["changed_arrival_utc"] = changed.dt.tz_convert("UTC")
    frame["planned_date"] = planned.dt.strftime("%Y-%m-%d")
    frame["planned_hour"] = planned.dt.hour.astype("Int64")
    frame["arrival_delay_minutes"] = (changed - planned).dt.total_seconds() / 60
    frame["ambiguous_zero"] = frame["arrival_delay_minutes"].eq(0)
    frame["extreme_delay"] = frame["arrival_delay_minutes"].abs().gt(1440)
    clean = frame.loc[excluded.eq("")].copy()
    if clean.empty:
        raise ValueError("No usable arrivals remain after cleaning.")
    quality.update(
        {
            "retained_rows": len(clean),
            "ambiguous_zero_rows": int(clean["ambiguous_zero"].sum()),
            "early_arrival_rows": int(clean["arrival_delay_minutes"].lt(0).sum()),
            "absolute_delay_above_24h_rows": int(clean["extreme_delay"].sum()),
            "planned_date_min": clean["planned_date"].min(),
            "planned_date_max": clean["planned_date"].max(),
        }
    )
    if len(clean) + sum(quality["exclusions"].values()) != len(frame):
        raise AssertionError("Exclusion accounting does not reconcile.")
    coverage = pd.crosstab(clean["station_name"], clean["planned_date"]).reindex(
        index=list(STATIONS.values()), columns=DAYS, fill_value=0
    )
    quality["retained_days_per_station"] = {
        str(name): int(count) for name, count in coverage.gt(0).sum(axis=1).items()
    }
    return clean, quality, coverage
