"""Synthetic model-contract, leakage, selection and dependent-resampling tests."""

import numpy as np
import pandas as pd
import pytest

from raildelay.analysis import STATIONS
from raildelay.risk_model import (
    RiskPredictor,
    bootstrap_difference,
    choose,
    features,
    labels,
    probabilities,
    promotion,
    scores,
)
from raildelay.risk_report import reliability


def fixture(rows=240):
    return pd.DataFrame(
        {
            "eva": [next(iter(STATIONS))] * rows,
            "station_name": ["Aachen Hbf"] * rows,
            "train_type": ["RE"] * 120 + ["ICE"] * (rows - 120),
            "planned_hour": np.arange(rows) % 24,
            "planned_weekday": np.arange(rows) % 7,
            "arrival_delay_minutes": np.where(np.arange(rows) % 5 == 0, 15, 0),
            "journey_key": [f"{i // 2}-2507{2 + (i // 2) % 28:02d}1200" for i in range(rows)],
            "planned_date": [f"2025-07-{2 + (i // 2) % 28:02d}" for i in range(rows)],
        }
    )


def test_target_boundary_and_probability_validation():
    frame = fixture().iloc[:4].copy()
    frame["arrival_delay_minutes"] = [-10, 0, 14.99, 15]
    assert labels(frame).tolist() == [0, 0, 0, 1]
    for values in ([np.nan], [-0.01], [1.01], [[0.2]]):
        with pytest.raises(ValueError, match="probabilities"):
            probabilities(values)
    assert scores(frame, [0, 0, 0, 1])["brier"] == 0


def test_hierarchy_smoothing_and_unknown_category_fallback():
    train = fixture(219)  # RE has 120 rows, ICE has 99: fixed threshold matters.
    model = RiskPredictor().fit(train)
    request = train.iloc[[0, 120]].copy()
    extra = request.iloc[[0]].assign(train_type="NEW")
    result = model.predict(pd.concat([request, extra]))
    assert result.fallback_level.tolist() == ["station_category", "station", "station"]
    assert result.reference_rows.tolist() == [120, 219, 219]
    expected = (24 + 100 * labels(train).mean()) / 220
    assert result.probability.iloc[0] == pytest.approx(expected)
    assert result.reference_journeys.iloc[0] == 60
    assert RiskPredictor("global").fit(train).predict(request).probability.nunique() == 1


@pytest.mark.parametrize("kind,parameter", [("logistic", 1.0), ("histogram", 7)])
def test_classifier_encodes_training_only_and_wraps_sparse_inputs(kind, parameter):
    train = fixture(219)
    model = RiskPredictor(kind, parameter).fit(train)
    request = train.iloc[[0, 120]].assign(train_type=["NEW", "ICE"])
    result = model.predict(request)
    reference = RiskPredictor().fit(train).predict(request)
    np.testing.assert_allclose(result.probability, reference.probability)
    assert "NEW" not in model.estimator.steps[0][1].categories_[-1]
    assert result.fallback_level.tolist() == ["station", "station"]
    assert model.predict(train.iloc[[0]]).fallback_level.item() == "model"


def test_prediction_whitelist_and_invalid_inputs():
    frame = fixture()
    assert "arrival_delay_minutes" not in features(frame)
    for field, value in (
        ("eva", "outside"),
        ("planned_hour", 24),
        ("planned_weekday", 7),
        ("train_type", ""),
    ):
        broken = frame.copy()
        broken.loc[0, field] = value
        with pytest.raises(ValueError):
            features(broken)
    model = RiskPredictor().fit(frame)
    missing_station = frame.iloc[[0]].assign(eva=list(STATIONS)[1])
    result = model.predict(missing_station)
    assert not result.station_supported.item()
    assert result.fallback_level.item() == "global"


def test_fixed_tie_order_and_promotion_gate():
    assert choose({"a": {"brier": 0.1}, "b": {"brier": 0.1 - 1e-13}}, ["a", "b"]) == "a"
    frame = fixture()
    y = labels(frame)
    assert promotion(frame, np.full(len(frame), 0.2), y)["passed"]
    assert not promotion(frame, y, y)["passed"]  # zero denominator
    assert not promotion(frame, np.full(len(frame), 0.2), np.full(len(frame), 0.3))["passed"]


def test_station_regression_blocks_otherwise_good_classifier():
    frame = pd.concat([fixture()] * 10, ignore_index=True)
    frame.loc[:1199, "eva"] = list(STATIONS)[1]
    y = labels(frame)
    baseline = np.full(len(frame), 0.2)
    classifier = y.astype(float)
    # Balanced inversion in the first station keeps overall calibration good.
    classifier[:1200] = 1 - y[:1200]
    result = promotion(frame, baseline, classifier)
    assert list(STATIONS)[1] in result["station_failures"]
    assert not result["passed"]


def test_bootstrap_keeps_journey_groups_and_is_reproducible():
    frame = fixture()
    frame["arrival_delay_minutes"] = 0
    b, c = np.full(len(frame), 0.4), np.full(len(frame), 0.2)
    result = bootstrap_difference(frame, b, c, repeats=100)
    assert result == bootstrap_difference(frame, b, c, repeats=100)
    assert result["journey"]["groups"] == 120  # two stop records per journey
    assert result["seven_day"]["groups"] == 29  # July 2–30, including empty July 30.
    for mode in result.values():
        np.testing.assert_allclose(mode["interval_95"], [-0.12, -0.12])
    # Planned date changes cannot split the journey-start-date bootstrap grouping.
    frame.loc[::2, "planned_date"] = "2025-07-30"
    assert result == bootstrap_difference(frame, b, c, repeats=100)


def test_reliability_retains_empty_bins_and_probability_one():
    table = reliability(np.array([0, 1, 1]), np.array([0, 0.1, 1]))
    assert table.rows.sum() == 3
    assert table.rows.iloc[[0, 1, 9]].tolist() == [1, 1, 1]
    assert pd.isna(table.event_rate.iloc[2])
