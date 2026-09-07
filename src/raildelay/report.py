"""Static charts and a shareable Markdown report for the exploratory slice."""

import json
import platform
from importlib.metadata import version
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from raildelay.analysis import STATIONS

NOTE = "DB-source archive • September 2025 • zeros may include missing updates"


def save_chart(fig, path):
    fig.text(0.02, 0.015, NOTE, fontsize=8, color="#475569")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)


def write_report(clean: pd.DataFrame, quality: dict, coverage: pd.DataFrame, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    delay = clean["arrival_delay_minutes"]
    station = (
        clean.groupby("station_name")["arrival_delay_minutes"]
        .agg(records="size", median="median", mean="mean", p90=lambda values: values.quantile(0.9))
        .reindex(list(STATIONS.values()))
    )
    hours = (
        clean.groupby("planned_hour")["arrival_delay_minutes"]
        .agg(records="size", median="median")
        .reindex(range(24))
    )
    quality["summary_minutes"] = {
        "median": float(delay.median()),
        "mean": float(delay.mean()),
        "p90": float(delay.quantile(0.9)),
        "min": float(delay.min()),
        "max": float(delay.max()),
    }
    quality["environment"] = {"python": platform.python_version()}
    quality["environment"].update(
        {name: version(name) for name in ("raildelay", "pandas", "pyarrow", "matplotlib")}
    )
    quality["retained_categories"] = {
        str(name): int(count) for name, count in clean["train_type"].value_counts().items()
    }
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    central = delay.between(-10, 120, inclusive="both")
    ax.hist(delay.loc[central], bins=np.arange(-10, 122, 2), color="#2563eb")
    ax.set(
        xlabel="Archive-reported arrival delay (minutes)",
        ylabel="Arrival records",
        title=f"Delay distribution · {len(clean):,} retained arrivals",
    )
    ax.text(
        0.98,
        0.95,
        f"Shown: −10 to 120 min\nOutside view: {(~central).sum():,} records",
        transform=ax.transAxes,
        ha="right",
        va="top",
    )
    save_chart(fig, output / "delay-distribution.png")

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.barh(station.index, station["median"], color="#0f766e")
    ax.invert_yaxis()
    for index, row in enumerate(station.itertuples()):
        if pd.notna(row.median):
            ax.text(
                row.median + 0.2,
                index,
                f"{row.median:.1f} min · n={row.records:,.0f}",
                va="center",
                fontsize=9,
            )
    ax.set_xlim(min(0, station["median"].min() - 1), max(1, station["median"].max()) + 8)
    ax.set(
        xlabel="Median archive-reported arrival delay (minutes)",
        title="Station comparison · fixed order, different service mixes and coverage",
    )
    save_chart(fig, output / "station-delays.png")

    fig, (ax, counts) = plt.subplots(
        2, 1, figsize=(11, 6), sharex=True, gridspec_kw={"height_ratios": [2, 1]}
    )
    ax.plot(hours.index, hours["median"], marker="o", color="#7c3aed")
    ax.set(ylabel="Median delay (minutes)", title="Arrival delay by scheduled local hour")
    counts.bar(hours.index, hours["records"].fillna(0), color="#c4b5fd")
    counts.set(xlabel="Scheduled arrival hour (Europe/Berlin)", ylabel="Records", xticks=range(24))
    save_chart(fig, output / "hourly-delays.png")

    fig, ax = plt.subplots(figsize=(13, 6))
    chart = ax.imshow(coverage.to_numpy(), aspect="auto", cmap="Blues", vmin=0)
    ax.set_yticks(range(len(coverage)), coverage.index)
    ax.set_xticks(range(30), range(1, 31))
    ax.set(
        xlabel="Scheduled arrival day in September 2025",
        title="Retained arrivals by station and day · presence does not prove complete coverage",
    )
    fig.colorbar(chart, ax=ax, label="Retained arrival records")
    save_chart(fig, output / "daily-coverage.png")

    station.to_csv(output / "station-summary.csv", float_format="%.3f")
    coverage.to_csv(output / "daily-coverage.csv")
    hours.to_csv(output / "hourly-summary.csv", float_format="%.3f")
    (output / "quality.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    exclusions = "\n".join(
        f"| {reason.replace('_', ' ')} | {count:,} |"
        for reason, count in quality["exclusions"].items()
    )
    station_rows = "\n".join(
        f"| {name} | {row['records']:,.0f} | {row['median']:.1f} | {row['p90']:.1f} |"
        if pd.notna(row["records"])
        else f"| {name} | 0 | — | — |"
        for name, row in station.iterrows()
    )
    zero_percent = 100 * quality["ambiguous_zero_rows"] / len(clean)
    coverage_text = (
        "; ".join(
            f"{name}: {days}/30 days"
            for name, days in quality["retained_days_per_station"].items()
            if days < 30
        )
        or "All ten stations have retained arrivals on all 30 days."
    )
    report = f"""# NRW railway arrivals — September 2025

The cleaned subset contains **{len(clean):,} arrival records** from ten selected
stations. Median archive-reported delay is **{delay.median():.1f} minutes**;
the 90th percentile is **{delay.quantile(0.9):.1f} minutes**. These describe this
archive subset, not verified DB punctuality or all NRW services.

## Data and exclusions

Source: Deutsche Bahn data, archived and processed by Piet Brömmel / piebro,
CC BY 4.0. [Pinned download]({quality["source_url"]}).
Source SHA-256: `{quality["source_sha256"]}`.
The file contains {quality["source_rows"]:,} records; {quality["selected_rows"]:,}
belong to the ten selected station identifiers. Remaining source records are
outside the selected station scope. The raw file is preserved.

Exclusions below are sequential and mutually exclusive; their sum plus retained
records equals the selected input. Cancellation counts here follow earlier
exclusions and are not cancellation rates for all services.

| Exclusion | Records |
| --- | ---: |
{exclusions}

Retained scheduled dates: {quality["planned_date_min"]} to {quality["planned_date_max"]}.
Missing-value counts before cleaning, category counts, software versions, and
days represented per station are in [quality.json](quality.json).

## Arrival delays

![Distribution of archive-reported arrival delay](delay-distribution.png)

All statistics retain early arrivals and extreme delays. The histogram shows
−10 to 120 minutes and labels the number outside that range. There are
{quality["early_arrival_rows"]:,} negative delays and
{quality["absolute_delay_above_24h_rows"]:,} delays with absolute magnitude above
24 hours, flagged for review. The observed range is {delay.min():.1f} to
{delay.max():.1f} minutes.

{quality["ambiguous_zero_rows"]:,} records ({zero_percent:.1f}%) have equal planned
and changed arrival times. Missing updates were filled with scheduled times
upstream, so zero is ambiguous. Removing all zeros would introduce another bias.

## Stations

![Station median delays with sample counts](station-delays.png)

| Station | Retained arrivals | Median minutes | 90th percentile minutes |
| --- | ---: | ---: | ---: |
{station_rows}

These are descriptive comparisons in fixed station order. Service mix and
coverage differ; the chart is not a station performance ranking. Source train
categories are preserved without inferring operator ownership. Bus records are
excluded; other observed categories remain separate in the cleaned data.

## Time of day and coverage

![Delay and sample counts by scheduled local hour](hourly-delays.png)

![Daily retained arrival counts](daily-coverage.png)

Hourly differences may reflect different trains and stations serving each hour.
The coverage grid includes all 30 scheduled arrival dates, including zero-count
cells. Daily presence does not prove complete hourly collection. The earlier
source audit found a sharp change in Bochum counts after September 5; investigate
service changes and collection gaps before interpreting this as a delay effect.

Coverage after cleaning: {coverage_text}

## Limits and next checkpoint

- Arrival delay is changed minus planned arrival, not the archive's mixed
  departure/arrival `delay_in_min` field. It is a proxy with schedule fallback.
- The archive contains DB-source records and does not identify all operators.
- Missing arrival pairs can include origin-only stops. Cancellations are
  separate outcomes, not zero-delay arrivals.
- Timestamps are interpreted as Europe/Berlin; invalid or ambiguous local times
  are excluded. Source timestamps remain in the cleaned file alongside UTC values.
- Source monthly membership uses changed departure/arrival time. Filtering by
  planned arrival date cannot recover records stored in adjacent monthly files.
- This is one historical month with selected stations and retrospective records.
  It does not establish causality, current performance, or annual patterns.
- No prediction model has been trained. Next validate adjacent months and
  journey keys, then compare schedule-based predictions with a naive baseline.

Reproduce from the project root with `.venv/bin/python -m raildelay`.
Numeric chart data: [station summary](station-summary.csv),
[hourly summary](hourly-summary.csv), [daily coverage](daily-coverage.csv).
"""
    (output / "report.md").write_text(report, encoding="utf-8")
