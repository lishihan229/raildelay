"""Audit a local monthly archive in batches, retaining selected stop keys."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow
import pyarrow.compute as pc
import pyarrow.parquet as pq

STATIONS = (
    "Aachen Hbf",
    "Düsseldorf Hbf",
    "Köln Hbf",
    "Essen Hbf",
    "Duisburg Hbf",
    "Dortmund Hbf",
    "Bochum Hbf",
    "Wuppertal Hbf",
    "Bonn Hbf",
    "Mönchengladbach Hbf",
)


def inspect(path):
    with path.open("rb") as source:
        checksum = hashlib.file_digest(source, "sha256").hexdigest()
    parquet = pq.ParquetFile(path)
    columns = [
        "station_name",
        "eva",
        "time",
        "id",
        "train_type",
        "arrival_planned_time",
        "arrival_change_time",
        "arrival_is_canceled",
    ]
    missing = set(columns) - set(parquet.schema_arrow.names)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    counts = {name: Counter() for name in STATIONS}
    days = {name: Counter() for name in STATIONS}
    identifiers = defaultdict(set)
    categories = Counter()
    seen = set()
    duplicates = 0
    all_stations = set()
    for batch in parquet.iter_batches(batch_size=65536, columns=columns):
        names = batch.column("station_name")
        all_stations.update(pc.unique(names).to_pylist())
        selected = batch.filter(pc.is_in(names, value_set=pyarrow.array(STATIONS)))
        for row in selected.to_pylist():
            name = row["station_name"]
            count = counts[name]
            count["rows"] += 1
            identifiers[name].add(row["eva"])
            categories[row["train_type"]] += 1
            if row["time"] is not None:
                days[name][row["time"].date().isoformat()] += 1
            else:
                count["missing_time"] += 1
            key = (row["eva"], row["id"])
            duplicates += key in seen
            seen.add(key)
            planned = row["arrival_planned_time"]
            changed = row["arrival_change_time"]
            if row["arrival_is_canceled"]:
                count["arrival_canceled"] += 1
            elif planned is None or changed is None:
                count["missing_arrival_pair"] += 1
            else:
                count["noncanceled_arrival_pairs"] += 1
                if planned == changed:
                    count["equal_arrival_times"] += 1
    return {
        "file": str(path),
        "bytes": path.stat().st_size,
        "sha256": checksum,
        "pyarrow_version": pyarrow.__version__,
        "total_rows": parquet.metadata.num_rows,
        "total_station_names": len(all_stations),
        "schema": str(parquet.schema_arrow),
        "selected_duplicate_station_stop_keys": duplicates,
        "selected_train_types": dict(categories),
        "stations": {
            name: {
                "eva": sorted(identifiers[name]),
                **counts[name],
                "days_present": len(days[name]),
                "daily_rows_by_archive_time": dict(sorted(days[name].items())),
            }
            for name in STATIONS
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(inspect(arguments.path), ensure_ascii=False, indent=2))
