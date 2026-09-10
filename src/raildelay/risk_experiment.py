"""Separate development selection from integrity-guarded final evaluation."""

import argparse
import importlib.metadata
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from raildelay.analysis import COLUMNS, STATIONS, prepare
from raildelay.experiment import ARCHIVES, EXTRA_COLUMNS, assert_separation, cohort, load_month
from raildelay.risk_model import (
    CANDIDATES,
    RiskPredictor,
    bootstrap_difference,
    choose,
    labels,
    promotion,
    scores,
)
from raildelay.risk_preflight import PROTOCOL, TEST_MONTH, TEST_SHA256, digest

OUTPUT = Path("reports/generated/risk-model")
ARTIFACT = Path("models/risk-models.joblib")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def versions():
    return {
        name: importlib.metadata.version(name)
        for name in ("numpy", "pandas", "pyarrow", "scikit-learn", "joblib", "threadpoolctl")
    }


def source_hashes():
    paths = sorted(Path("src/raildelay").glob("risk_*.py"))
    paths += [Path("src/raildelay/analysis.py"), Path("src/raildelay/experiment.py")]
    return {str(path): digest(path) for path in paths}


def verify_preflight(root):
    path = Path("reports/generated/risk-preflight/preflight.json")
    report = json.loads(path.read_text())
    if (
        report.get("passed") is not True
        or report.get("source_sha256") != TEST_SHA256
        or report.get("protocol_sha256") != digest(PROTOCOL)
        or digest(root / f"data-{TEST_MONTH}.parquet") != TEST_SHA256
    ):
        raise ValueError("Missing, stale or inconsistent November preflight")
    return path


def develop(root=Path("data/raw"), output=OUTPUT):
    if (output / "test-opened.json").exists():
        raise ValueError("November outcomes already opened: do not rerun model selection")
    preflight = verify_preflight(root)
    output.mkdir(parents=True, exist_ok=True)
    frames, audits = [], {}
    for month in ARCHIVES:
        print(f"Preparing development month {month}", flush=True)
        clean, quality, _ = load_month(month, root)
        frame, quality["cohort"] = cohort(clean, month)
        frames.append(frame)
        audits[month] = quality
    assert_separation(frames)
    train = pd.concat(frames[:2], ignore_index=True)
    validation, confirmation = frames[2:]
    models, validation_scores, failures = {}, {}, {}
    for name, (kind, parameter) in CANDIDATES.items():
        print(f"Fitting {name}", flush=True)
        try:
            model = RiskPredictor(kind, parameter).fit(train)
            validation_scores[name] = scores(validation, model.predict(validation).probability)
            models[name] = model
        except (ValueError, Warning) as error:
            failures[name] = str(error)
    if not all(name in models for name in ("global", "hierarchical")):
        raise ValueError(f"Baseline fitting failed: {failures}")
    classifier_names = [name for name in models if name not in ("global", "hierarchical")]
    if not classifier_names:
        raise ValueError(f"All classifiers failed: {failures}")
    baseline = choose(validation_scores, ["global", "hierarchical"])
    classifier = choose(validation_scores, classifier_names)
    gates, confirmation_scores = {}, {}
    for month, frame in (("2025-09", validation), ("2025-10", confirmation)):
        b = models[baseline].predict(frame).probability
        c = models[classifier].predict(frame).probability
        gates[month] = promotion(frame, b, c)
        if month == "2025-10":
            confirmation_scores = {baseline: scores(frame, b), classifier: scores(frame, c)}
    selected = classifier if all(gate["passed"] for gate in gates.values()) else baseline
    bundle = {
        "decision": {"selected": selected, "baseline": baseline, "classifier": classifier},
        "models": {
            name: models[name] for name in dict.fromkeys(["global", "hierarchical", classifier])
        },
        "development_journeys": set().union(*(set(frame.journey_key) for frame in frames)),
        "latest_development_event": max(
            frames[-1].planned_arrival_utc.max(), frames[-1].changed_arrival_utc.max()
        ),
    }
    ARTIFACT.parent.mkdir(exist_ok=True)
    joblib.dump(bundle, ARTIFACT)
    write_json(output / "development-audit.json", audits)
    state = {
        "selected": selected,
        "baseline": baseline,
        "classifier": classifier,
        "validation_scores": validation_scores,
        "confirmation_scores": confirmation_scores,
        "promotion_gates": gates,
        "failed_candidates": failures,
        "training_months": ["2025-07", "2025-08"],
        "source_checksums": ARCHIVES,
        "test_sha256": TEST_SHA256,
        "protocol_sha256": digest(PROTOCOL),
        "code_sha256": source_hashes(),
        "versions": versions(),
        "preflight_sha256": digest(preflight),
        "artifact_sha256": digest(ARTIFACT),
        "support": {"minimum_rows": 100, "pseudo_rows": 100},
    }
    write_json(output / "selection.json", state)
    print(json.dumps({"selected": selected, "gates": gates}, indent=2), flush=True)
    return state


def verify_selection(state, artifact=None):
    """Fail before model deserialization or any test-outcome read."""
    artifact = ARTIFACT if artifact is None else artifact
    if (
        state.get("protocol_sha256") != digest(PROTOCOL)
        or state.get("code_sha256") != source_hashes()
        or state.get("versions") != versions()
        or state.get("source_checksums") != ARCHIVES
        or state.get("test_sha256") != TEST_SHA256
        or state.get("artifact_sha256") != digest(artifact)
    ):
        raise ValueError("Frozen selection is inconsistent with code, protocol, data or artifact")


def evaluate(root=Path("data/raw"), output=OUTPUT):
    state = json.loads((output / "selection.json").read_text())
    verify_selection(state)
    preflight = verify_preflight(root)
    if digest(preflight) != state["preflight_sha256"]:
        raise ValueError("Preflight changed after selection")
    for month, expected in ARCHIVES.items():
        if digest(root / f"data-{month}.parquet") != expected:
            raise ValueError("Development source changed after selection")
    marker = {"selection_sha256": digest(output / "selection.json"), "test_sha256": TEST_SHA256}
    marker_path = output / "test-opened.json"
    if marker_path.exists() and json.loads(marker_path.read_text()) != marker:
        raise ValueError("Test already opened under a different selection")
    # Joblib is only loaded from this locally created, checksum-verified artifact.
    bundle = joblib.load(ARTIFACT)
    if bundle["decision"] != {name: state[name] for name in ("selected", "baseline", "classifier")}:
        raise ValueError("Frozen decision differs from fitted artifact")
    write_json(marker_path, marker)
    raw = pd.read_parquet(
        root / f"data-{TEST_MONTH}.parquet",
        columns=COLUMNS + EXTRA_COLUMNS,
        filters=[("eva", "in", list(STATIONS))],
    )
    clean, quality, coverage = prepare(raw, TEST_MONTH)
    frame, quality["cohort"] = cohort(clean, TEST_MONTH)
    if set(frame.eva) != set(STATIONS) or len(np.unique(labels(frame))) != 2:
        raise ValueError("Final cohort must retain all ten stations and both target classes")
    if set(frame.journey_key) & bundle["development_journeys"]:
        raise ValueError("Final journey overlaps development")
    if frame.planned_arrival_utc.min() <= bundle["latest_development_event"]:
        raise ValueError("Final events overlap development chronology")
    predictions = {name: model.predict(frame) for name, model in bundle["models"].items()}
    metrics = {name: scores(frame, pred.probability) for name, pred in predictions.items()}
    b, c = (predictions[state[name]].probability for name in ("baseline", "classifier"))
    gate = promotion(frame, b, c)
    uncertainty = bootstrap_difference(frame, b, c)
    confirmed = bool(
        state["selected"] == state["classifier"]
        and gate["passed"]
        and uncertainty["seven_day"]["interval_95"][1] < 0
    )
    result = {
        "month": TEST_MONTH,
        "selected": state["selected"],
        "metrics": metrics,
        "promotion_gate": gate,
        "paired_brier_uncertainty": uncertainty,
        "classifier_improvement_confirmed": confirmed,
        "selection_sha256": marker["selection_sha256"],
        "quality": quality,
        "diagnostics": {},
    }
    for label, mask in {
        "nonzero_only": frame.arrival_delay_minutes.ne(0),
        "excluding_below_minus_30": frame.arrival_delay_minutes.ge(-30),
    }.items():
        result["diagnostics"][label] = (
            {
                name: scores(frame.loc[mask], pred.probability.to_numpy()[mask.to_numpy()])
                for name, pred in predictions.items()
            }
            if mask.any()
            else {}
        )
    coverage.to_csv(output / "final-coverage.csv")
    write_json(output / "final.json", result)
    from raildelay.risk_report import write_report

    write_report(state, result, frame, predictions, output)
    print(
        json.dumps(
            {"selected": state["selected"], "confirmed": confirmed, "metrics": metrics}, indent=2
        )
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["develop", "evaluate"])
    args = parser.parse_args()
    (develop if args.stage == "develop" else evaluate)()
