"""Synthetic fixtures: risk denominators, ambiguity and historical input support."""

import pandas as pd
import pytest

from raildelay.risk_audit import group_summary, input_support, summarize_labels


def test_threshold_signed_labels_and_ambiguity_denominators():
    frame = pd.DataFrame({"arrival_delay_minutes": [-31, 0, 0, 14.99, 15, 40]})
    result = summarize_labels(frame)
    assert result["late_15_rows"] == 2
    assert result["early_below_minus_30_rows"] == 1
    assert result["proxy_rate"] == pytest.approx(2 / 6)
    assert result["nonzero_only_rate"] == 0.5
    assert result["all_zeros_late_scenario"] == pytest.approx(4 / 6)


def test_empty_all_zero_and_missing_targets():
    assert summarize_labels(pd.DataFrame({"arrival_delay_minutes": []}))["proxy_rate"] is None
    result = summarize_labels(pd.DataFrame({"arrival_delay_minutes": [0, 0]}))
    assert result["proxy_rate"] == 0
    assert result["nonzero_only_rate"] is None
    assert result["all_zeros_late_scenario"] == 1
    with pytest.raises(ValueError, match="nonmissing"):
        summarize_labels(pd.DataFrame({"arrival_delay_minutes": [None]}))


def test_support_uses_only_training_counts_and_includes_unseen():
    train = pd.DataFrame({"station": ["A"] * 100 + ["B"] * 99})
    later = pd.DataFrame({"station": ["A", "B", "C", "B"]}, index=[9, 9, 2, 7])
    result = input_support(train, later, ["station"])
    assert result["rows"] == 4
    assert result["unseen_rows"] == 1
    assert result["below_threshold_rows"] == 3
    assert result["supported_share"] == 0.25


def test_group_summaries_preserve_counts_and_distinct_journeys():
    frame = pd.DataFrame(
        {
            "station": ["A", "A", "B"],
            "category": ["RE", "RE", "ICE"],
            "arrival_delay_minutes": [0, 15, 40],
            "journey_key": ["one", "one", "two"],
            "planned_date": ["2025-07-02"] * 3,
        }
    )
    result = group_summary(frame, ["station", "category"])
    assert result["rows"].sum() == 3
    assert result["late_15_rows"].sum() == 2
    assert result.loc[result.station.eq("A"), "journeys"].item() == 1
