"""Run the first exploratory slice using the pinned local dataset."""

import argparse
from pathlib import Path

from raildelay.analysis import load_sample, prepare
from raildelay.report import write_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/raw/data-2025-09.parquet"))
    args = parser.parse_args()
    try:
        frame, provenance = load_sample(args.input)
        clean, quality, coverage = prepare(frame)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Unable to analyze sample: {error}\n")
    quality.update(provenance)
    processed = Path("data/processed/nrw-arrivals-2025-09.parquet")
    output = Path("reports/generated/2025-09")
    processed.parent.mkdir(parents=True, exist_ok=True)
    clean.to_parquet(processed, index=False)
    write_report(clean, quality, coverage, output)
    print(f"Retained {len(clean):,} of {len(frame):,} selected records.")
    print(f"Cleaned data: {processed}")
    print(f"Report: {output / 'report.md'}")


if __name__ == "__main__":
    main()
