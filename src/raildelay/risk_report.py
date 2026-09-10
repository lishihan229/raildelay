"""Export probability reliability, group errors and a self-contained model card."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from raildelay.analysis import SOURCE_REVISION
from raildelay.risk_model import labels, scores


def reliability(y, p):
    bins = np.minimum((np.asarray(p) * 10).astype(int), 9)
    rows = []
    for index in range(10):
        mask = bins == index
        rows.append(
            {
                "bin_low": index / 10,
                "bin_high": (index + 1) / 10,
                "rows": int(mask.sum()),
                "mean_prediction": float(np.mean(np.asarray(p)[mask])) if mask.any() else None,
                "event_rate": float(np.mean(np.asarray(y)[mask])) if mask.any() else None,
            }
        )
    return pd.DataFrame(rows)


def write_report(state, result, frame, predictions, output):
    reliability_rows, breakdowns = [], []
    fig, ax = plt.subplots(figsize=(7, 5))
    for name, pred in predictions.items():
        table = reliability(labels(frame), pred.probability)
        reliability_rows.append(table.assign(model=name))
        supported = table.loc[table.rows.gt(0)]
        ax.plot(supported.mean_prediction, supported.event_rate, marker="o", label=name)
        for dimension in ("eva", "planned_hour", "train_type", "fallback_level"):
            values = (
                pred.fallback_level.to_numpy()
                if dimension == "fallback_level"
                else frame[dimension].to_numpy()
            )
            for group in pd.unique(values):
                mask = values == group
                metrics = scores(frame.loc[mask], pred.probability.to_numpy()[mask])
                breakdowns.append(
                    {
                        "model": name,
                        "dimension": dimension,
                        "group": str(group),
                        **metrics,
                        "sparse": metrics["rows"] < 1000,
                    }
                )
    ax.plot([0, 1], [0, 1], "--", color="gray", label="Perfect calibration")
    ax.set(
        xlabel="Mean predicted probability",
        ylabel="Observed archive event frequency",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "reliability.png", dpi=150)
    plt.close(fig)
    pd.concat(reliability_rows).to_csv(output / "reliability.csv", index=False)
    errors = pd.DataFrame(breakdowns)
    errors.to_csv(output / "group-errors.csv", index=False)
    selected = predictions[state["selected"]]
    selected.to_parquet(output / "prediction-context.parquet", index=False)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(result["metrics"].keys(), [v["brier"] for v in result["metrics"].values()])
    ax.set(
        ylabel="Brier score (squared probability; lower is better)",
        title="Reserved November evaluation",
    )
    fig.tight_layout()
    fig.savefig(output / "model-comparison.png", dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 5))
    for name in predictions:
        subset = errors.loc[errors.model.eq(name) & errors.dimension.eq("eva")]
        ax.plot(subset.group, subset.brier, marker="o", label=name)
    ax.set(xlabel="Station EVA identifier (counts in group-errors.csv)", ylabel="Brier score")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "station-errors.png", dpi=150)
    plt.close(fig)
    lines = [
        "# Historical delay-risk model card",
        "",
        f"Frozen selection: **{state['selected']}**. Confirmed classifier improvement: "
        f"**{result['classifier_improvement_confirmed']}**.",
        "",
        "## Intended use and limits",
        "",
        "Historical >=15-minute arrival-delay probability for ten NRW stations, "
        "conditional on retained noncanceled archive arrivals. For a historical "
        "planning demo; not verified live risk, cancellation risk or connection advice. "
        "Missing updates can appear as punctual arrivals. Historical plans do not "
        "prove departure-time feature availability. No causal or year-round claim.",
        "",
        "Inputs: station, planned local hour/weekday, train category. Training: "
        "July–August 2025; selection: September; confirmation: October; final: November. "
        "Month-edge journeys are excluded. Encoders and support references fit training only.",
        "",
        "## Final metrics",
        "",
        "| Method | Rows | Journeys | Brier | Log loss | Event rate | Mean prediction |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, s in result["metrics"].items():
        lines.append(
            f"| {name} | {s['rows']:,} | {s['journeys']:,} | {s['brier']:.6f} | "
            f"{s['log_loss']:.6f} | {s['event_rate']:.2%} | {s['mean_prediction']:.2%} |"
        )
    interval = result["paired_brier_uncertainty"]["seven_day"]["interval_95"]
    lines += [
        "",
        f"Paired seven-day bootstrap 95% interval, classifier minus selected baseline "
        f"Brier: [{interval[0]:.6f}, {interval[1]:.6f}]. Negative favors classifier. "
        "2,000 replicates, seed 42. One month has few independent weeks; intervals "
        "do not account for label bias. Whole-journey sensitivity is in final.json.",
        "",
        "![Model comparison](model-comparison.png)",
        "",
        "![Probability reliability](reliability.png)",
        "",
        "Reliability uses ten fixed bins; reliability.csv includes counts and empty "
        "bins. Overall calibration alone does not establish subgroup reliability.",
        "",
        "![Station errors](station-errors.png)",
        "",
        "## Data quality and support",
        "",
        f"Selected November source rows: {result['quality']['selected_rows']:,}; "
        f"clean arrivals: {result['quality']['retained_rows']:,}; "
        f"ambiguous zeros among clean arrivals: {result['quality']['ambiguous_zero_rows']:,}. "
        "Full sequential exclusions and cohort removal are in final.json. "
        "Cancellations/missing pairs are excluded, not counted as punctual. "
        "Daily retained coverage is in final-coverage.csv.",
        "",
        "Groups with fewer than 100 training station/category records fall back "
        "to a smoothed station reference or global frequency. The global baseline "
        "always uses the global reference. The threshold is an engineering choice, "
        "not a confidence guarantee. Prediction context records rows, journeys, "
        "days, late labels, reference level and training period; a demo must abstain "
        "for absent station support. Group errors with <1,000 rows are descriptive.",
        "",
        "## Reproduction and provenance",
        "",
        "Run `python -m raildelay.risk_preflight`, then "
        "`python -m raildelay.risk_experiment develop`, then "
        "`python -m raildelay.risk_experiment evaluate`. Development refuses to "
        "reselect after test-opened.json exists. Evaluation can reproduce the same "
        "frozen selection after checking code, protocol, packages, data and model hashes. "
        "November is now used; another selection cycle needs a fresh final period.",
        "",
        "Source: Deutsche Bahn data (CC BY 4.0), archived/processed by Piet Brömmel / "
        f"piebro, revision {SOURCE_REVISION}. Source SHA-256 values, package versions "
        "and artifact/code hashes are in selection.json and preflight.json. "
        "Model parameters, support rules and acceptance gates are fixed in "
        "docs/specs/risk-experiment.md.",
        "",
    ]
    (output / "report.md").write_text("\n".join(lines))
