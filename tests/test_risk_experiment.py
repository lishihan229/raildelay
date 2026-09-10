"""Frozen-state checks must fail before any final outcome read."""

import pandas as pd
import pytest

from raildelay import risk_experiment as experiment
from raildelay.risk_preflight import digest


def test_selection_rejects_changed_artifact_protocol_and_sources(tmp_path, monkeypatch):
    artifact = tmp_path / "model"
    artifact.write_bytes(b"synthetic local artifact, not a model")
    protocol = tmp_path / "protocol.md"
    protocol.write_text("synthetic protocol")
    monkeypatch.setattr(experiment, "PROTOCOL", protocol)
    state = {
        "protocol_sha256": digest(protocol),
        "code_sha256": experiment.source_hashes(),
        "versions": experiment.versions(),
        "source_checksums": experiment.ARCHIVES,
        "test_sha256": experiment.TEST_SHA256,
        "artifact_sha256": digest(artifact),
    }
    experiment.verify_selection(state, artifact)
    for field in ("protocol_sha256", "code_sha256", "source_checksums", "test_sha256"):
        with pytest.raises(ValueError, match="inconsistent"):
            experiment.verify_selection({**state, field: "tampered"}, artifact)
    artifact.write_bytes(b"changed model")
    with pytest.raises(ValueError, match="inconsistent"):
        experiment.verify_selection(state, artifact)


def test_no_selection_and_already_opened_test_stop_before_data_read(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("No final outcome or training data should be read")

    monkeypatch.setattr(experiment.pd, "read_parquet", forbidden)
    monkeypatch.setattr(experiment, "load_month", forbidden)
    with pytest.raises(FileNotFoundError):
        experiment.evaluate(tmp_path, tmp_path)
    (tmp_path / "test-opened.json").write_text("{}")
    with pytest.raises(ValueError, match="already opened"):
        experiment.develop(tmp_path, tmp_path)


def test_synthetic_development_final_report_and_frozen_rerun(tmp_path, monkeypatch):
    from raildelay import experiment as original
    from raildelay.analysis import STATIONS

    root = tmp_path / "raw"
    root.mkdir()
    checksums = {}
    for month in [*original.ARCHIVES, "2025-11"]:
        rows = []
        for day in range(2, 30):
            for number, (eva, station) in enumerate(STATIONS.items()):
                planned = pd.Timestamp(f"{month}-{day:02d} 12:00:00")
                rows.append(
                    {
                        "eva": eva,
                        "station_name": station,
                        "train_type": "RE",
                        "id": f"{number}-{planned.strftime('%y%m%d%H%M')}-1",
                        "train_line_ride_id": str(number),
                        "train_line_station_num": 1,
                        "arrival_planned_time": planned,
                        "arrival_change_time": planned
                        + pd.Timedelta(minutes=20 if day % 5 == 0 else 0),
                        "arrival_is_canceled": False,
                    }
                )
        path = root / f"data-{month}.parquet"
        pd.DataFrame(rows).to_parquet(path, index=False)
        checksums[month] = digest(path)
    monkeypatch.setattr(experiment, "TEST_SHA256", checksums.pop("2025-11"))
    monkeypatch.setattr(original, "ARCHIVES", checksums)
    monkeypatch.setattr(experiment, "ARCHIVES", checksums)
    monkeypatch.setattr(experiment, "ARTIFACT", tmp_path / "models" / "risk.joblib")
    preflight = tmp_path / "synthetic-preflight.json"
    preflight.write_text('{"synthetic": true}')
    monkeypatch.setattr(experiment, "verify_preflight", lambda root: preflight)
    monkeypatch.setattr(
        experiment,
        "CANDIDATES",
        {
            "global": ("global", None),
            "hierarchical": ("hierarchical", None),
            "logistic_1": ("logistic", 1.0),
        },
    )
    # Keep meaningful bootstrap behavior while shortening this small integration run.
    original_bootstrap = experiment.bootstrap_difference
    monkeypatch.setattr(
        experiment, "bootstrap_difference", lambda *args: original_bootstrap(*args, repeats=20)
    )
    output = tmp_path / "reports"
    state = experiment.develop(root, output)
    assert not (output / "test-opened.json").exists()
    result = experiment.evaluate(root, output)
    assert result["selected"] == state["selected"]
    assert len(list(output.glob("*.png"))) == 3
    assert (output / "report.md").is_file()
    assert result == experiment.evaluate(root, output)
    with pytest.raises(ValueError, match="already opened"):
        experiment.develop(root, output)
