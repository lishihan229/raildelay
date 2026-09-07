"""Synthetic fixtures verify exclusions, signed delays, and timezone semantics."""

from pathlib import Path

import pandas as pd
import pytest

from raildelay.analysis import STATIONS, load_sample, local_times, prepare


def sample():
    return pd.DataFrame(
        [
            {
                "eva": eva,
                "station_name": name,
                "id": f"stop-{index}",
                "train_type": "RE",
                "arrival_is_canceled": False,
                "arrival_planned_time": "2025-09-01 12:00:00",
                "arrival_change_time": "2025-09-01 12:05:00",
            }
            for index, (eva, name) in enumerate(STATIONS.items())
        ]
    )


def test_signed_delay_zero_and_utc():
    frame = sample()
    frame.loc[0, "arrival_change_time"] = "2025-09-01 11:57:00"
    frame.loc[1, "arrival_change_time"] = "2025-09-01 12:00:00"
    clean, quality, coverage = prepare(frame)
    assert clean["arrival_delay_minutes"].tolist()[:3] == [-3, 0, 5]
    assert str(clean.iloc[0]["planned_arrival_utc"]) == "2025-09-01 10:00:00+00:00"
    assert quality["ambiguous_zero_rows"] == 1
    assert quality["early_arrival_rows"] == 1
    assert coverage.shape == (10, 30)
    assert coverage["2025-09-02"].sum() == 0


def test_exclusions_are_disjoint_and_complete():
    frame = sample()
    frame.loc[0, ["train_type", "arrival_is_canceled"]] = ["Bus", True]
    frame.loc[1, "arrival_is_canceled"] = True
    frame.loc[2, "arrival_change_time"] = None
    frame.loc[3, "arrival_planned_time"] = "2025-08-31 23:59:00"
    frame.loc[4, "train_type"] = None
    frame.loc[5, "id"] = None
    clean, quality, _ = prepare(frame)
    assert len(clean) == 4
    assert quality["exclusions"]["bus"] == 1
    assert quality["exclusions"]["arrival_canceled"] == 1
    assert quality["exclusions"]["planned_arrival_outside_september"] == 1
    assert sum(quality["exclusions"].values()) + len(clean) == len(frame)


def test_duplicates_exclude_all_copies_not_arbitrary_winner():
    frame = sample()
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    clean, quality, _ = prepare(frame)
    assert quality["exclusions"]["duplicate_station_stop_key"] == 2
    assert "stop-0" not in set(clean["id"])


def test_dst_gaps_and_ambiguity_are_not_guessed():
    result = local_times(
        pd.Series(
            [
                "2025-03-30 02:30:00",
                "2025-10-26 02:30:00",
                "2025-09-01 12:00:00",
                "invalid",
            ]
        )
    )
    assert result.isna().tolist() == [True, True, False, True]


def test_extreme_values_flagged_without_clipping():
    frame = sample()
    frame.loc[0, "arrival_change_time"] = "2025-09-03 12:00:00"
    clean, quality, _ = prepare(frame)
    assert clean.iloc[0]["arrival_delay_minutes"] == 2880
    assert quality["absolute_delay_above_24h_rows"] == 1


def test_invalid_input_is_actionable():
    with pytest.raises(ValueError, match="Missing required columns"):
        prepare(sample().drop(columns="eva"))
    with pytest.raises(ValueError, match="Selected stations absent"):
        prepare(sample().iloc[1:])
    frame = sample()
    frame["arrival_is_canceled"] = True
    with pytest.raises(ValueError, match="No usable arrivals"):
        prepare(frame)


def test_unrecognized_source_rejected():
    with pytest.raises(ValueError, match="checksum"):
        load_sample(Path(__file__))


def test_report_outputs_with_synthetic_data(tmp_path):
    from raildelay.report import write_report

    clean, quality, coverage = prepare(sample())
    quality.update(
        source_url="https://example.org/synthetic", source_sha256="synthetic", source_rows=10
    )
    write_report(clean, quality, coverage, tmp_path)
    assert len(list(tmp_path.glob("*.png"))) == 4
    assert (tmp_path / "quality.json").is_file()
    assert "**10 arrival records**" in (tmp_path / "report.md").read_text()
