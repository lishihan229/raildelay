"""Synthetic planned-only fixtures protect the held-out outcome boundary."""

import pandas as pd

from raildelay.analysis import STATIONS
from raildelay.risk_preflight import PLANNED_COLUMNS, planned_coverage


def test_preflight_whitelist_has_no_outcomes():
    assert set(PLANNED_COLUMNS) == {"eva", "id", "train_type", "arrival_planned_time"}


def test_planned_coverage_counts_only_november_and_keeps_absent_stations():
    eva = next(iter(STATIONS))
    frame = pd.DataFrame(
        {
            "eva": [eva] * 4,
            "arrival_planned_time": [
                "2025-11-01 00:00:00",
                "2025-11-01 12:00:00",
                "2025-12-01 00:00:00",
                None,
            ],
        }
    )
    result = planned_coverage(frame)
    assert result.shape == (10, 30)
    assert result.loc[eva, "2025-11-01"] == 2
    assert result.to_numpy().sum() == 2
    assert result.gt(0).sum(axis=1).tolist() == [1] + [0] * 9
