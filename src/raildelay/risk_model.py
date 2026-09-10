"""Historical probability models with training-only support and fixed promotion rules."""

import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits

from raildelay.analysis import STATIONS
from raildelay.experiment import FEATURES


def features(frame):
    x = frame[FEATURES].reset_index(drop=True).copy()
    if x.isna().any().any() or not x.eva.isin(STATIONS).all():
        raise ValueError("Missing predictor or unsupported station")
    for name, upper in (("planned_hour", 23), ("planned_weekday", 6)):
        if not x[name].isin(range(upper + 1)).all():
            raise ValueError(f"Invalid {name}")
    if not x.train_type.map(lambda value: isinstance(value, str) and bool(value.strip())).all():
        raise ValueError("Invalid train category")
    return x.astype(str)


def labels(frame):
    delay = frame.arrival_delay_minutes.to_numpy(dtype=float)
    if not np.isfinite(delay).all():
        raise ValueError("Labels require finite cleaned delays")
    return (delay >= 15).astype(int)


def probabilities(values):
    p = np.asarray(values, dtype=float)
    if p.ndim != 1 or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Invalid probabilities")
    return p


def scores(frame, predicted):
    y, p = labels(frame), probabilities(predicted)
    if not len(y) or len(y) != len(p):
        raise ValueError("Empty or mismatched evaluation population")
    clipped = np.clip(p, 1e-6, 1 - 1e-6)
    return {
        "rows": len(y),
        "journeys": int(frame.journey_key.nunique()),
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": float(-np.mean(y * np.log(clipped) + (1 - y) * np.log(1 - clipped))),
        "event_rate": float(y.mean()),
        "mean_prediction": float(p.mean()),
        "calibration_gap": float(abs(y.mean() - p.mean())),
    }


class RiskPredictor:
    """A fitted estimator plus auditable hierarchical fallback references."""

    def __init__(self, kind="hierarchical", parameter=None):
        self.kind = kind
        self.parameter = parameter

    def fit(self, frame):
        x, y = features(frame), labels(frame)
        if len(np.unique(y)) != 2:
            raise ValueError("Training requires both target classes")
        self.global_rate = float(y.mean())
        self.period = [str(frame.planned_date.min()), str(frame.planned_date.max())]
        reference = x.assign(
            late=y, journey=frame.journey_key.to_numpy(), date=frame.planned_date.to_numpy()
        )
        self.global_stats = {
            "rows": len(frame),
            "late": int(y.sum()),
            "journeys": int(frame.journey_key.nunique()),
            "days": int(frame.planned_date.nunique()),
        }
        self.references = {}
        for name, keys in (("pair", ["eva", "train_type"]), ("station", ["eva"])):
            self.references[name] = reference.groupby(keys).agg(
                rows=("late", "size"),
                late=("late", "sum"),
                journeys=("journey", "nunique"),
                days=("date", "nunique"),
            )
        self.estimator = None
        if self.kind == "logistic":
            estimator = LogisticRegression(C=self.parameter, solver="lbfgs", max_iter=2000)
        elif self.kind == "histogram":
            estimator = HistGradientBoostingClassifier(
                loss="log_loss",
                learning_rate=0.1,
                max_iter=100,
                max_leaf_nodes=self.parameter,
                min_samples_leaf=100,
                l2_regularization=1.0,
                early_stopping=False,
                random_state=42,
            )
        elif self.kind not in ("global", "hierarchical"):
            raise ValueError(f"Unknown model kind: {self.kind}")
        if self.kind in ("logistic", "histogram"):
            self.estimator = make_pipeline(
                OneHotEncoder(handle_unknown="ignore", sparse_output=False), estimator
            )
            with warnings.catch_warnings(), threadpool_limits(limits=2):
                warnings.simplefilter("error", ConvergenceWarning)
                self.estimator.fit(x, y)
        return self

    def predict(self, frame):
        x = features(frame)
        pair = x.join(self.references["pair"], on=["eva", "train_type"])
        station = x.join(self.references["station"], on="eva")
        pair_ok = pair.rows.fillna(0).ge(100).to_numpy()
        station_ok = station.rows.fillna(0).ge(100).to_numpy()
        level = np.where(pair_ok, "station_category", np.where(station_ok, "station", "global"))
        result = pd.DataFrame(index=x.index)
        for field in ("rows", "late", "journeys", "days"):
            result[f"reference_{field}"] = np.where(
                pair_ok, pair[field], np.where(station_ok, station[field], self.global_stats[field])
            ).astype(int)
        p = (result.reference_late.to_numpy() + 100 * self.global_rate) / (
            result.reference_rows.to_numpy() + 100
        )
        if self.kind == "global":
            p = np.full(len(x), self.global_rate)
            level = np.full(len(x), "global")
            for field, value in self.global_stats.items():
                result[f"reference_{field}"] = value
        elif self.estimator is not None:
            with threadpool_limits(limits=2):
                learned = self.estimator.predict_proba(x)[:, 1]
            probabilities(learned)
            p = np.where(pair_ok, learned, p)
            level = np.where(pair_ok, "model", level)
        result["probability"] = probabilities(p)
        result["fallback_level"] = level
        result["station_supported"] = station.rows.fillna(0).ge(100).to_numpy()
        result["training_start"], result["training_end"] = self.period
        return result


CANDIDATES = {
    "global": ("global", None),
    "hierarchical": ("hierarchical", None),
    "logistic_0.1": ("logistic", 0.1),
    "logistic_1": ("logistic", 1.0),
    "logistic_10": ("logistic", 10.0),
    "histogram_7": ("histogram", 7),
    "histogram_15": ("histogram", 15),
}


def choose(score_map, names):
    """Stable insertion order provides the protocol's tie priority."""
    winner = names[0]
    for name in names[1:]:
        if score_map[name]["brier"] < score_map[winner]["brier"] - 1e-12:
            winner = name
    return winner


def promotion(frame, baseline, classifier):
    b, c = scores(frame, baseline), scores(frame, classifier)
    relative = (b["brier"] - c["brier"]) / b["brier"] if b["brier"] > 0 else None
    y = labels(frame)
    delta = (probabilities(classifier) - y) ** 2 - (probabilities(baseline) - y) ** 2
    groups = pd.DataFrame({"eva": frame.eva.to_numpy(), "delta": delta}).groupby("eva")
    stations = groups.delta.agg(["size", "mean"])
    failures = stations.loc[stations["size"].ge(1000) & stations["mean"].gt(0.01)]
    return {
        "relative_brier_reduction": relative,
        "calibration_gap": c["calibration_gap"],
        "station_failures": failures.index.tolist(),
        "passed": bool(
            relative is not None
            and relative >= 0.02
            and c["calibration_gap"] <= 0.03
            and failures.empty
        ),
    }


def bootstrap_difference(frame, baseline, classifier, repeats=2000):
    """Paired seven-day and whole-journey resampling via grouped loss sums."""
    y = labels(frame)
    delta = (probabilities(classifier) - y) ** 2 - (probabilities(baseline) - y) ** 2
    parts = frame.journey_key.str.rsplit("-", n=1).str[-1]
    dates = pd.to_datetime(parts, format="%y%m%d%H%M", errors="raise").dt.normalize()
    values = pd.DataFrame(
        {"date": dates.to_numpy(), "journey": frame.journey_key.to_numpy(), "delta": delta}
    )
    day = values.groupby("date").delta.agg(["sum", "size"])
    low = day.index.min().replace(day=2)
    high = low + pd.offsets.MonthEnd(0)
    day = day.reindex(pd.date_range(low, high, inclusive="left"), fill_value=0)
    if len(day) < 7:
        raise ValueError("Seven-day bootstrap requires at least seven calendar dates")
    journey = values.groupby("journey").delta.agg(["sum", "size"])
    results = {}
    for mode, table in (("seven_day", day), ("journey", journey)):
        rng = np.random.default_rng(42)
        totals, counts = table["sum"].to_numpy(), table["size"].to_numpy()
        samples = []
        for _ in range(repeats):
            if mode == "seven_day":
                starts = rng.integers(0, len(day) - 6, size=int(np.ceil(len(day) / 7)))
                indices = (starts[:, None] + np.arange(7)).ravel()[: len(day)]
            else:
                indices = rng.integers(0, len(journey), size=len(journey))
            denominator = counts[indices].sum()
            if denominator:
                samples.append(float(totals[indices].sum() / denominator))
        if not samples:
            raise ValueError("Bootstrap has no nonempty replicates")
        results[mode] = {
            "interval_95": np.quantile(samples, [0.025, 0.975]).tolist(),
            "replicates": len(samples),
            "groups": len(table),
            "seed": 42,
        }
    return results
