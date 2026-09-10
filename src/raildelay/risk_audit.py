"""Audit historical 15-minute delay labels and input support; fit no models."""

import json
from pathlib import Path

import pandas as pd

from raildelay.experiment import ARCHIVES, assert_separation, cohort, load_month

SUPPORT_THRESHOLD = 100
GROUPINGS = {
    "station_category": ["station_name", "train_type"],
    "station_category_hour_weekday": [
        "station_name",
        "train_type",
        "planned_hour",
        "planned_weekday",
    ],
}


def summarize_labels(frame):
    """Keep ambiguity scenarios separate from the observed archive proxy rate."""
    delay = frame["arrival_delay_minutes"]
    if delay.isna().any():
        raise ValueError("Risk summaries require cleaned, nonmissing delays")
    n = len(delay)
    late, zeros = int(delay.ge(15).sum()), int(delay.eq(0).sum())
    return {
        "rows": n,
        "late_15_rows": late,
        "ambiguous_zero_rows": zeros,
        "early_below_minus_30_rows": int(delay.lt(-30).sum()),
        "proxy_rate": late / n if n else None,
        "zero_share": zeros / n if n else None,
        "nonzero_only_rate": late / (n - zeros) if n > zeros else None,
        "all_zeros_late_scenario": (late + zeros) / n if n else None,
    }


def group_summary(frame, keys):
    rows = []
    for values, group in frame.groupby(keys, observed=True, dropna=False):
        rows.append(
            {
                **dict(zip(keys, values, strict=True)),
                **summarize_labels(group),
                "journeys": int(group["journey_key"].nunique()),
                "days": int(group["planned_date"].nunique()),
            }
        )
    return pd.DataFrame(rows)


def input_support(train, later, keys):
    """Count only earlier records; later labels cannot improve historical support."""
    counts = train.groupby(keys, observed=True).size().rename("training_rows")
    matched = later[keys].join(counts, on=keys)["training_rows"].fillna(0)
    n = len(matched)
    return {
        "rows": n,
        "unseen_rows": int(matched.eq(0).sum()),
        "below_threshold_rows": int(matched.lt(SUPPORT_THRESHOLD).sum()),
        "supported_share": float(matched.ge(SUPPORT_THRESHOLD).mean()) if n else None,
        "threshold": SUPPORT_THRESHOLD,
    }


def write_report(audit, output):
    lines = [
        "# Historical delay-risk data audit",
        "",
        "Decision: conditional go for a retrospective archive-proxy experiment; "
        "no-go for claims of verified live commuter risk.",
        "",
        "## Full cleaned months",
        "",
        "Rates condition on retained noncanceled arrivals. Exclusions are separate.",
        "",
        "| Month | Arrivals | >=15 min | Proxy rate | Ambiguous zeros | "
        "Nonzero-only rate | All zeros late scenario |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for month, data in audit["months"].items():
        s = data["clean_labels"]
        lines.append(
            f"| {month} | {s['rows']:,} | {s['late_15_rows']:,} | "
            f"{s['proxy_rate']:.2%} | {s['zero_share']:.2%} | "
            f"{s['nonzero_only_rate']:.2%} | {s['all_zeros_late_scenario']:.2%} |"
        )
    lines += [
        "",
        "The nonzero-only rate changes the population and is not a correction. "
        "The all-zeros-late scenario changes only ambiguous zeros. Neither is a "
        "confidence interval or a bound on actual travel risk.",
        "",
        "## Sequential exclusions",
        "",
        "Counts follow the existing cleaning order, before cohort boundary removal. "
        "Canceled rows are counted before arrival-pair/month checks; these are not "
        "cancellation rates among scheduled monthly arrivals. Missing pairs can "
        "include origin-only stops, not just collection failures.",
        "",
        "| Month | Selected source rows | Canceled | Missing/invalid pair | "
        "Unknown cancellation | Bus |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for month, data in audit["months"].items():
        q = data["quality"]
        e = q["exclusions"]
        lines.append(
            f"| {month} | {q['selected_rows']:,} | {e['arrival_canceled']:,} | "
            f"{e['missing_or_invalid_arrival_pair']:,} | "
            f"{e['unknown_cancellation_status']:,} | {e['bus']:,} |"
        )
    lines += [
        "",
        "## Support from July for later cohort inputs",
        "",
        "The 100-record cutoff screens sparsity; it does not establish reliability. "
        "Rows below the cutoff include unseen groups. Only July counts are used.",
        "",
        "| Month | Grouping | Later rows | Unseen | Below 100 July rows |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for month, groupings in audit["input_support_from_july"].items():
        for name, s in groupings.items():
            lines.append(
                f"| {month} | {name} | {s['rows']:,} | {s['unseen_rows']:,} | "
                f"{s['below_threshold_rows']:,} |"
            )
    lines += [
        "",
        "## Interpretation and next gate",
        "",
        "Station/category and detailed input CSVs include event counts, zero-label "
        "sensitivity, days and distinct journey counts for each cohort. Coverage "
        "CSVs include zero-count station days. Daily presence does not prove "
        "hourly completeness or capture of all scheduled services.",
        "",
        "Use pooled models or historical fallback rules for sparse inputs; "
        "do not display precise standalone frequencies for every input combination. "
        "Freeze these rules in the next experiment protocol and use a fresh final "
        "test period. All four audited months are now development evidence.",
        "",
        "The monthly schema lacks observation provenance and historical plan "
        "snapshots. More rows or higher model complexity cannot restore that "
        "information. A historical demo must disclose schedule fallback, exclude "
        "cancellation risk from its claim, show its data period and support, and "
        "avoid live or connection-success claims. Verified practical reliability "
        "requires a source/prospective evaluation with observation timestamps "
        "and explicit missing-update and cancellation handling.",
        "",
        "## Reproduction and provenance",
        "",
        "Run `.venv/bin/python -m raildelay.risk_audit`. No model is fitted and no "
        "new test period is opened. `audit.json` records checksums, schemas, all "
        "exclusions, cohort counts, and sensitivity summaries. Raw files stay unchanged.",
        "",
        "Source: Deutsche Bahn data (CC BY 4.0), archived/processed by Piet Brömmel "
        "/ piebro. Pinned revision and source URLs are in `audit.json`. "
        "Protocol: `docs/specs/risk-data-audit.md`.",
        "",
    ]
    (output / "report.md").write_text("\n".join(lines))


def run(root=Path("data/raw"), output=Path("reports/generated/risk-audit")):
    output.mkdir(parents=True, exist_ok=True)
    audit = {"months": {}, "input_support_from_july": {}}
    frames = []
    for month in ARCHIVES:
        clean, quality, coverage = load_month(month, root)
        frame, cohort_quality = cohort(clean, month)
        frames.append(frame)
        revision = quality["source_revision"]
        quality["source_url"] = (
            "https://huggingface.co/datasets/piebro/deutsche-bahn-data/resolve/"
            f"{revision}/monthly_processed_data/data-{month}.parquet"
        )
        audit["months"][month] = {
            "quality": quality,
            "cohort": cohort_quality,
            "clean_labels": summarize_labels(clean),
            "cohort_labels": summarize_labels(frame),
        }
        coverage.to_csv(output / f"coverage-{month}.csv")
        for name, keys in GROUPINGS.items():
            group_summary(frame, keys).to_csv(output / f"{name}-{month}.csv", index=False)
        if month != "2025-07":
            audit["input_support_from_july"][month] = {
                name: input_support(frames[0], frame, keys) for name, keys in GROUPINGS.items()
            }
    assert_separation(frames)
    if len({data["quality"]["schema"] for data in audit["months"].values()}) != 1:
        raise ValueError("Monthly archive schemas differ")
    (output / "audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
    write_report(audit, output)
    print(f"Risk suitability audit: {output / 'report.md'}")


if __name__ == "__main__":
    run()
