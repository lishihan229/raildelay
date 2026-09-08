"""Render model evaluation without tuning from the held-out results."""

import json
import platform
from importlib.metadata import version

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from raildelay.analysis import SOURCE_REVISION, STATIONS

CONSTRUCTION_URL = (
    "https://assets-ri.extranet.deutschebahn.com/db_fernverkehr/2025-08-08/"
    "5f48c4cf-1c1f-4ec4-b001-41ae65e5cc01Detailinformationen%2BBauarbeiten%2B"
    "zwischen%2BEssen%2Bund%2BDortmund_SepOkt.pdf"
)


def write_model_report(scores, audits, frozen, breakdowns, output):
    environment = {"python": platform.python_version()}
    environment.update(
        {
            name: version(name)
            for name in (
                "pandas",
                "pyarrow",
                "numpy",
                "scikit-learn",
                "scipy",
                "matplotlib",
                "joblib",
            )
        }
    )
    (output / "environment.json").write_text(json.dumps(environment, indent=2) + "\n")
    months = list(scores)
    fig, ax = plt.subplots(figsize=(9, 5))
    for index, name in enumerate(("baseline", "ridge")):
        ax.bar(
            np.arange(3) + (index - 0.5) * 0.35,
            [scores[m][name]["mae_minutes"] for m in months],
            width=0.35,
            label=name,
            color=("#0f766e", "#7c3aed")[index],
        )
    ax.set_xticks(
        range(3), ["August\nvalidation", "September\nexplored development", "October\nheld-out"]
    )
    ax.set(
        ylabel="Mean absolute error (minutes)", title="Timetable-only prediction · trained on July"
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "model-comparison.png", dpi=160)
    plt.close(fig)

    station = breakdowns[(breakdowns.month == "2025-10") & (breakdowns.dimension == "station_name")]
    pivot = station.pivot(index="group", columns="model", values="mae_minutes").reindex(
        list(STATIONS.values())
    )
    counts = station[station.model == "baseline"].set_index("group")["rows"]
    fig, ax = plt.subplots(figsize=(11, 7))
    for name, marker in (("baseline", "o"), ("ridge", "x")):
        ax.plot(pivot[name], range(len(pivot)), marker=marker, linestyle="none", label=name)
    ax.set_yticks(range(len(pivot)), [f"{n} (n={int(counts.get(n, 0)):,})" for n in pivot.index])
    ax.invert_yaxis()
    ax.set(
        xlabel="Mean absolute error (minutes)",
        title="October station errors · differing service mixes",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "station-errors.png", dpi=160)
    plt.close(fig)

    hour = breakdowns[(breakdowns.month == "2025-10") & (breakdowns.dimension == "planned_hour")]
    fig, (ax, sizes) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    for name in ("baseline", "ridge"):
        data = (
            hour[hour.model == name].assign(hour=lambda f: f.group.astype(int)).sort_values("hour")
        )
        ax.plot(data.hour, data.mae_minutes, marker=".", label=name)
        if name == "baseline":
            sizes.bar(data.hour, data.rows, color="#c4b5fd")
    ax.set(ylabel="MAE (minutes)", title="October error by scheduled local arrival hour")
    ax.legend()
    sizes.set(ylabel="Records", xlabel="Hour (Europe/Berlin)", xticks=range(24))
    fig.tight_layout()
    fig.savefig(output / "hourly-errors.png", dpi=160)
    plt.close(fig)

    score_rows = "\n".join(
        f"| {month} | {name} | {value['rows']:,} | "
        f"{value['mae_minutes']:.3f} | {value['rmse_minutes']:.3f} |"
        for month, models in scores.items()
        for name, value in models.items()
    )
    audit_rows = "\n".join(
        f"| {month} | {audit['selected_rows']:,} | {audit['retained_rows']:,} | "
        f"{audit['cohort']['cohort_rows']:,} | {audit['cohort']['journeys']:,} | "
        f"{100 * audit['zero_share']:.1f}% |"
        for month, audit in audits.items()
    )
    coverage_rows = "\n".join(
        f"| {station} | "
        + " | ".join(str(a["retained_days_per_station"][station]) for a in audits.values())
        + " |"
        for station in STATIONS.values()
    )
    test = scores["2025-10"]
    delta = test["ridge"]["mae_minutes"] - test["baseline"]["mae_minutes"]
    comparison = f"{'higher' if delta > 0 else 'lower'} by {abs(delta):.3f} minutes"
    sensitivity = "\n".join(
        f"| {name} | {label} | {values[label]['rows']:,} | {values[label]['mae_minutes']:.3f} |"
        for name, values in test.items()
        for label in ("nonzero_only", "excluding_below_minus_30")
    )
    report = f"""# Raildelay: first chronological prediction experiment

The August validation comparison selected **{frozen["recommended_by_validation"]}**.
On the reserved October period, Ridge's MAE was **{comparison}** than the baseline.
Both use July training data. These results concern archive-reported delay with
schedule fallback, not independently verified physical arrival times.

## Experiment and results

July trained the models; August selected Ridge strength (`{frozen["ridge_selected"]}`)
and the preferred method. September was already explored and is reported as
development data. The selection was written to `frozen-selection.json` before
October was opened by the experiment. No October result was used for selection.

Predictors: station, scheduled arrival hour, scheduled weekday, and train category.
One-hot encoding learns categories only from training data and handles unseen
values. Ridge strengths 1, 10, and 100 were compared on August MAE. The baseline
always predicts the July training median. No random row split or future-delay
predictor is used. MAE is the mean absolute prediction error; RMSE gives larger
errors more weight. Both are measured in minutes.

| Period | Model | Records | MAE minutes | RMSE minutes |
| --- | --- | ---: | ---: | ---: |
{score_rows}

![Chronological model comparison](model-comparison.png)

Ridge minimizes squared error, whereas the median baseline targets absolute
error. A difference between their MAE and RMSE rankings is therefore plausible.
Any next model is a new experiment and must use a new held-out period; October
is now consumed by this evaluation. No confidence interval is claimed for these
dependent train-stop observations.

## Data validation and journey separation

All four files passed their pinned SHA-256 checks and have identical schemas.

| Month | Selected records | Clean arrivals | Interior cohort | Journeys | Ambiguous zeros (clean) |
| --- | ---: | ---: | ---: | ---: | ---: |
{audit_rows}

Full journey keys include the ten-digit timestamp embedded in each stop ID.
The supplied prefix alone repeats across different starts. Parsed prefixes and
stop sequences matched the source fields, and journey/stop-sequence keys were
unique. Complete keys were disjoint between cohorts. The first and last calendar
days are excluded; journeys with any retained stop outside the interior interval
are removed. Planned arrivals, changed arrivals, and parsed starts must fall
inside the same interval. Label events precede the next cohort's first planned
event. This checks event chronology, not unrecorded collection availability.

Daily presence after cleaning, before the interior-cohort restriction:

| Station | July (31 days) | August (31) | September (30) | October (31) |
| --- | ---: | ---: | ---: | ---: |
{coverage_rows}

`data-audit.json` contains every month's mutually exclusive cleaning exclusions,
null counts, source metadata, timestamp range, label tails, and boundary losses.
`coverage-YYYY-MM.csv` preserves daily station counts including zeros.

## Data-quality investigation

DB's [construction notice]({CONSTRUCTION_URL}) announced diversions from
September 5 at 21:00 to October 31 at 21:00, including removal of long-distance
stops at Bochum. In September's raw selected records, September 1–5 include
multiple regional and long-distance categories. September 6–30 contain 2,124
S records, 423 Bus records, and one ICE record. This supports a changed service
pattern; it does not prove complete collection or explain each individual gap.
The eight September days without retained Bochum arrivals are weekends after
September 5. Their raw records are Bus entries, except one ICE entry on September
27 that also fails arrival cleaning. The absence in the train-arrival chart is
therefore explained by the observed service mix and explicit exclusions, not
eight entirely absent daily downloads.

Missing changes are replaced with planned times upstream. The monthly file
cannot distinguish a missing update from a punctual report. Zeros are retained,
explicitly labeled as ambiguous, and shown separately in sensitivity diagnostics.
No official punctuality rate is inferred.

The cleaned July, August, and September files contain respectively 16, 28, and
36 arrivals below −30 minutes. Some September examples differ by exactly 60 or
120 minutes; a monthly snapshot cannot establish whether this reflects schedule
revisions or erroneous updates. They remain in the primary experiment. October
tail counts are in the audit. No target clipping was introduced after evaluation.

October diagnostic views use the already fitted models and predictions:

| Model | Diagnostic subset | Records | MAE minutes |
| --- | --- | ---: | ---: |
{sensitivity}

## Where errors differ

![October station errors with counts](station-errors.png)

![October hourly errors and counts](hourly-errors.png)

`error-breakdowns.csv` contains station, local-hour, and train-category MAE/RMSE
with counts for August, September, and October. Small groups are descriptive;
service mix and construction differ by station and month.

## Limits, provenance, and reproduction

- This is a retrospective timetable-only planning benchmark. The archive keeps
  final timetable records, so their exact availability before a real departure
  is not established. Final upstream delay, changed timestamps, cancellation
  flags, and journey identifiers are excluded from model inputs.
- Labels inherit schedule fallback and collection gaps. Cancelled and missing
  arrivals are separate from the regression population. Their exclusion can
  change the mix of difficult journeys being evaluated.
- Ambiguous or nonexistent Europe/Berlin timestamps are excluded, including the
  October clock change. Source monthly boundaries use mixed changed event times;
  interior cohorts reduce but do not prove elimination of boundary omissions.
- Whole-journey filtering is based on selected retained stops, not every stop in
  Germany. A start timestamp is part of the source identifier, not a collection
  timestamp. No claim of a reconstructed live feed is made.
- The source is DB data, not a verified DB-only operator population. Construction
  and seasonality limit generalization from these four historical months.

Underlying data: Deutsche Bahn (CC BY 4.0); archive/processing: Piet Brömmel / piebro.
[Pinned source revision](https://huggingface.co/datasets/piebro/deutsche-bahn-data/tree/{SOURCE_REVISION}).
Individual checksums are in `data-audit.json`; software versions in `environment.json`.
Run `.venv/bin/python -m raildelay.experiment` from the project root after the
documented downloads. Models are local in `models/timetable-baselines.joblib`;
load only model files you trust.
"""
    (output / "report.md").write_text(report, encoding="utf-8")
