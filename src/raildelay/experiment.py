"""Pinned, chronological timetable-only delay prediction experiment."""

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

from raildelay.analysis import COLUMNS, SOURCE_REVISION, STATIONS, local_times, prepare

ARCHIVES = {
    "2025-07": "bc910d30f2c323134fb7b7328a866ea227ae6ea542ebc5da3fa6352677d0f884",
    "2025-08": "209d35345fe95a8270257ebe5df29ed6d4cc4f5eceb5e4fa0c9389cd6a4a1b22",
    "2025-09": "b0a8ff188b26cd22dca7c477c50f3eb7e9b4a0fd918fc5cd56e37e1cd646ccef",
    "2025-10": "54fe2301509dfdd13bac3652d55b991497456576b546b6b52e08c6bd354d8383",
}
EXTRA_COLUMNS = ["train_line_ride_id", "train_line_station_num"]
FEATURES = ["eva", "planned_hour", "planned_weekday", "train_type"]
TARGET = "arrival_delay_minutes"


def load_month(month: str, root: Path):
    path = root / f"data-{month}.parquet"
    with path.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    if checksum != ARCHIVES[month]:
        raise ValueError(f"Checksum mismatch for {month}")
    parquet = pq.ParquetFile(path)
    frame = pd.read_parquet(
        path, columns=COLUMNS + EXTRA_COLUMNS, filters=[("eva", "in", list(STATIONS))]
    )
    clean, quality, coverage = prepare(frame, month)
    quality.update(
        month=month,
        checksum=checksum,
        source_revision=SOURCE_REVISION,
        source_rows=parquet.metadata.num_rows,
        bytes=path.stat().st_size,
        schema=str(parquet.schema_arrow),
    )
    quality["early_below_minus_30_minutes"] = int(clean[TARGET].lt(-30).sum())
    quality["delay_min"] = float(clean[TARGET].min())
    quality["delay_max"] = float(clean[TARGET].max())
    quality["zero_share"] = float(clean[TARGET].eq(0).mean())
    return clean, quality, coverage


def cohort(frame: pd.DataFrame, month: str):
    """Validate supplied ID parts and confine complete journey keys to a cohort."""
    parts = frame["id"].str.extract(r"^(?P<prefix>-?\d+)-(?P<start>\d{10})-(?P<stop>\d+)$")
    invalid = parts.isna().any(axis=1)
    prefix_mismatch = parts["prefix"].ne(frame["train_line_ride_id"].astype(str))
    sequence = pd.to_numeric(parts["stop"], errors="coerce")
    sequence_mismatch = sequence.ne(frame["train_line_station_num"])
    if (invalid | prefix_mismatch | sequence_mismatch).any():
        raise ValueError("Journey ID parsing or supplied prefix/sequence cross-check failed")
    frame = frame.copy()
    frame["journey_key"] = parts["prefix"] + "-" + parts["start"]
    collision = frame.duplicated(["journey_key", "train_line_station_num"], keep=False)
    if collision.any():
        raise ValueError("Multiple stations share a journey/stop-sequence key")
    start = pd.to_datetime(parts["start"], format="%y%m%d%H%M", errors="coerce")
    journey_start = local_times(start).dt.tz_convert("UTC")
    low = pd.Timestamp(f"{month}-02", tz="Europe/Berlin").tz_convert("UTC")
    high = (pd.Timestamp(f"{month}-01", tz="Europe/Berlin") + pd.offsets.MonthEnd(0)).tz_convert(
        "UTC"
    )
    keep = (
        journey_start.ge(low)
        & journey_start.lt(high)
        & frame["planned_arrival_utc"].ge(low)
        & frame["planned_arrival_utc"].lt(high)
        & frame["changed_arrival_utc"].ge(low)
        & frame["changed_arrival_utc"].lt(high)
    )
    # If any retained stop fails the boundary check, remove its entire journey.
    rejected = set(frame.loc[~keep, "journey_key"])
    keep &= ~frame["journey_key"].isin(rejected)
    result = frame.loc[keep].copy()
    if result.empty:
        raise ValueError(f"Empty experiment cohort: {month}")
    result["planned_weekday"] = (
        result["planned_arrival_utc"].dt.tz_convert("Europe/Berlin").dt.dayofweek
    )
    starts_per_prefix = parts.groupby("prefix")["start"].nunique()
    return result, {
        "clean_rows": len(frame),
        "cohort_rows": len(result),
        "boundary_or_invalid_start_excluded": int((~keep).sum()),
        "journeys": result["journey_key"].nunique(),
        "repeated_prefixes_with_multiple_starts": int(starts_per_prefix.gt(1).sum()),
        "planned_min": str(result["planned_arrival_utc"].min()),
        "planned_max": str(result["planned_arrival_utc"].max()),
        "latest_label_event": str(result["changed_arrival_utc"].max()),
    }


def assert_separation(frames):
    seen = set()
    latest_event = None
    for frame in frames:
        keys = set(frame["journey_key"])
        if seen & keys:
            raise ValueError("Journey overlap between chronological partitions")
        earliest = frame["planned_arrival_utc"].min()
        if latest_event is not None and latest_event >= earliest:
            raise ValueError("Previous cohort events overlap the next partition")
        latest_event = max(frame["planned_arrival_utc"].max(), frame["changed_arrival_utc"].max())
        seen |= keys


def inputs(frame):
    # Explicit whitelist prevents accidental inclusion of target-derived columns.
    return frame[FEATURES].astype(str)


def metrics(target, predictions):
    return {
        "rows": len(target),
        "mae_minutes": float(mean_absolute_error(target, predictions)),
        "rmse_minutes": float(root_mean_squared_error(target, predictions)),
    }


def choose_models(train, validation):
    x, y = inputs(train), train[TARGET]
    baseline = DummyRegressor(strategy="median").fit(x, y)
    candidates = {}
    fitted = {}
    for alpha in (1.0, 10.0, 100.0):
        model = make_pipeline(
            OneHotEncoder(handle_unknown="ignore"), Ridge(alpha=alpha, solver="lsqr")
        )
        model.fit(x, y)
        name = f"ridge_alpha_{alpha:g}"
        fitted[name] = model
        candidates[name] = metrics(validation[TARGET], model.predict(inputs(validation)))
    best = min(candidates, key=lambda name: candidates[name]["mae_minutes"])
    baseline_score = metrics(validation[TARGET], baseline.predict(inputs(validation)))
    winner = (
        "baseline" if baseline_score["mae_minutes"] <= candidates[best]["mae_minutes"] else "ridge"
    )
    return {"baseline": baseline, "ridge": fitted[best]}, {
        "features": FEATURES,
        "ridge_selected": best,
        "validation_ridge_candidates": candidates,
        "validation_baseline": baseline_score,
        "recommended_by_validation": winner,
        "training_month": "2025-07",
        "validation_month": "2025-08",
        "development_month": "2025-09",
        "held_out_month": "2025-10",
        "protocol": "docs/specs/model-experiment.md",
    }


def evaluate(models, frame):
    scores, breakdowns = {}, []
    for name, model in models.items():
        predictions = model.predict(inputs(frame))
        scores[name] = metrics(frame[TARGET], predictions)
        for label, mask in {
            "nonzero_only": frame[TARGET].ne(0),
            "excluding_below_minus_30": frame[TARGET].ge(-30),
        }.items():
            if mask.any():
                scores[name][label] = metrics(frame.loc[mask, TARGET], predictions[mask])
        errors = frame[["station_name", "planned_hour", "train_type"]].copy()
        errors["absolute_error"] = np.abs(frame[TARGET].to_numpy() - predictions)
        errors["squared_error"] = (frame[TARGET].to_numpy() - predictions) ** 2
        for dimension in ("station_name", "planned_hour", "train_type"):
            for group, rows in errors.groupby(dimension):
                breakdowns.append(
                    {
                        "model": name,
                        "dimension": dimension,
                        "group": str(group),
                        "rows": len(rows),
                        "mae_minutes": rows.absolute_error.mean(),
                        "rmse_minutes": np.sqrt(rows.squared_error.mean()),
                    }
                )
    return scores, breakdowns


def run(root=Path("data/raw"), output=Path("reports/generated/model")):
    from raildelay.model_report import write_model_report

    output.mkdir(parents=True, exist_ok=True)
    frames, audits, coverage_tables = {}, {}, {}
    # October remains unopened until the model-selection configuration is saved.
    for month in ("2025-07", "2025-08", "2025-09"):
        clean, quality, coverage = load_month(month, root)
        frames[month], quality["cohort"] = cohort(clean, month)
        audits[month], coverage_tables[month] = quality, coverage
    assert_separation(list(frames.values()))
    models, frozen = choose_models(frames["2025-07"], frames["2025-08"])
    (output / "frozen-selection.json").write_text(json.dumps(frozen, indent=2) + "\n")
    Path("models").mkdir(exist_ok=True)
    joblib.dump(models, "models/timetable-baselines.joblib")
    clean, quality, coverage = load_month("2025-10", root)
    frames["2025-10"], quality["cohort"] = cohort(clean, "2025-10")
    audits["2025-10"], coverage_tables["2025-10"] = quality, coverage
    if len({audit["schema"] for audit in audits.values()}) != 1:
        raise ValueError("Monthly archive schemas differ")
    assert_separation(list(frames.values()))
    scores, breakdowns = {}, []
    for month in ("2025-08", "2025-09", "2025-10"):
        scores[month], rows = evaluate(models, frames[month])
        breakdowns.extend({"month": month, **row} for row in rows)
    for month, table in coverage_tables.items():
        table.to_csv(output / f"coverage-{month}.csv")
    (output / "data-audit.json").write_text(json.dumps(audits, indent=2, ensure_ascii=False) + "\n")
    (output / "metrics.json").write_text(json.dumps(scores, indent=2) + "\n")
    pd.DataFrame(breakdowns).to_csv(output / "error-breakdowns.csv", index=False)
    write_model_report(scores, audits, frozen, pd.DataFrame(breakdowns), output)
    print(
        json.dumps(
            {
                "selection": frozen["recommended_by_validation"],
                "October": scores["2025-10"],
                "report": str(output / "report.md"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    run()
