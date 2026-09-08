"""Check month boundaries, journey isolation, and predictor availability rules."""

import pandas as pd
import pytest

from raildelay.experiment import FEATURES, assert_separation, choose_models, cohort, inputs


def rows(month="2025-07"):
    dates = pd.date_range(f"{month}-02 12:00", periods=4, freq="D", tz="Europe/Berlin")
    frame = pd.DataFrame(
        {
            "id": [f"-123-{date.strftime('%y%m%d%H%M')}-1" for date in dates],
            "train_line_ride_id": "-123",
            "train_line_station_num": 1,
            "planned_arrival_utc": dates.tz_convert("UTC") + pd.Timedelta(minutes=10),
            "changed_arrival_utc": dates.tz_convert("UTC") + pd.Timedelta(minutes=15),
            "eva": "08000001",
            "planned_hour": 12,
            "train_type": "RE",
            "arrival_delay_minutes": [5.0, 0.0, 10.0, 3.0],
        }
    )
    return frame


def test_full_journey_keys_keep_timestamp_and_signed_prefix():
    clean, audit = cohort(rows(), "2025-07")
    assert clean.journey_key.nunique() == 4
    assert clean.journey_key.iloc[0] == "-123-2507021200"
    assert audit["repeated_prefixes_with_multiple_starts"] == 1


def test_boundary_failure_removes_whole_journey():
    frame = rows()
    extra = frame.iloc[[0]].copy()
    extra["id"] = "-123-2507021200-2"
    extra["train_line_station_num"] = 2
    extra["changed_arrival_utc"] = pd.Timestamp("2025-08-01", tz="UTC")
    clean, audit = cohort(pd.concat([frame, extra], ignore_index=True), "2025-07")
    assert not clean.journey_key.eq("-123-2507021200").any()
    assert audit["boundary_or_invalid_start_excluded"] == 2


def test_bad_identifier_or_sequence_fails():
    frame = rows()
    frame.loc[0, "train_line_station_num"] = 9
    with pytest.raises(ValueError, match="cross-check"):
        cohort(frame, "2025-07")


def test_split_overlap_and_event_chronology_fail():
    july, _ = cohort(rows(), "2025-07")
    august, _ = cohort(rows("2025-08"), "2025-08")
    assert_separation([july, august])
    duplicate = august.copy()
    duplicate.loc[0, "journey_key"] = july.journey_key.iloc[0]
    with pytest.raises(ValueError, match="Journey overlap"):
        assert_separation([july, duplicate])
    july.loc[0, "changed_arrival_utc"] = pd.Timestamp("2025-09-01", tz="UTC")
    with pytest.raises(ValueError, match="events overlap"):
        assert_separation([july, august])


def test_predictors_ignore_future_values_and_unknown_categories_work():
    train, _ = cohort(rows(), "2025-07")
    validation, _ = cohort(rows("2025-08"), "2025-08")
    validation["train_type"] = "UNSEEN"
    assert list(inputs(train).columns) == FEATURES
    modified = train.copy()
    modified["arrival_delay_minutes"] = 9999
    modified["changed_arrival_utc"] = pd.Timestamp("2030-01-01", tz="UTC")
    pd.testing.assert_frame_equal(inputs(train), inputs(modified))
    models, frozen = choose_models(train, validation)
    assert len(models["ridge"].predict(inputs(validation))) == 4
    encoder = models["ridge"].steps[0][1]
    assert "UNSEEN" not in encoder.categories_[-1]
    assert frozen["held_out_month"] == "2025-10"
