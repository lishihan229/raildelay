# Suitability for a practical delay-risk application

Audited on 2026-09-10 under [the predeclared protocol](../specs/risk-data-audit.md).
Reproduce with `.venv/bin/python -m raildelay.risk_audit`.

## Decision

Conditional go for a retrospective ML experiment and historical demo; no-go for
a claim of verified live commuter-risk probabilities using these monthly files
alone. Both target classes have substantial overall support, and integrity
checks pass. However, observation provenance, historical feature availability,
complete service coverage, and cancellation risk remain unresolved.

The project can demonstrate a useful engineering workflow and historical risk
patterns now. Real-world reliability must be validated separately before a user
is encouraged to rely on estimates for a particular current journey.

## Measured evidence

These are full cleaned months, before the model cohort's month-edge exclusions.
The denominator contains retained noncanceled arrival pairs, not all scheduled
services, passengers, or unique journeys.

| Month (2025) | Retained arrivals | >=15-minute labels | Proxy frequency | Ambiguous zeros |
| --- | ---: | ---: | ---: | ---: |
| July | 151,886 | 23,336 | 15.36% | 18.53% |
| August | 152,667 | 21,649 | 14.18% | 17.88% |
| September | 143,734 | 24,006 | 16.70% | 15.78% |
| October | 148,106 | 27,339 | 18.46% | 13.78% |

The frequency varies by 4.28 percentage points across these months. That is
descriptive evidence for evaluating temporal stability, not a causal trend.

For September, excluding all zero labels changes the frequency from 16.70% to
19.83%, but changes the population and is not a valid correction. If every zero
instead hid a >=15-minute delay, the scenario frequency would be 32.49%.
This scenario is not an estimate or confidence interval for actual risk; it
illustrates the importance of missing-update provenance. The existing schema
and source audit cannot recover that provenance from monthly files.

Sequential cleaning excludes 12,319 / 8,589 / 9,417 / 8,897 canceled records in
July–October. These are not cancellation rates: cancellation is checked before
arrival-pair and scheduled-month filtering. Missing/invalid arrival-pair
exclusions number 44,826 / 44,498 / 43,429 / 45,240; origin-only stops may be
included, so these are not counts of failed data collection. No unknown
cancellation statuses survive earlier exclusions in any of the four files.

All ten stations are present. Nine have retained arrivals on every day of all
four months. Bochum has 22 retained days in September and 23 in October, versus
31 in July and August. Daily presence alone does not prove full service capture.
The prior experiment's service-change investigation remains relevant; do not
interpret these counts as a station performance ranking.

## Input granularity matters

Using July's journey-separated cohort as the historical reference, the shares
of later arrival rows with at least 100 reference records are:

| Group definition | August | September | October |
| --- | ---: | ---: | ---: |
| Station + category | 99.29% | 99.32% | 99.23% |
| Station + category + hour + weekday | 2.91% | 3.00% | 3.27% |

Later cohort sizes are 143,594 / 133,642 / 137,974. Detailed combinations unseen
in July affect 709 / 1,200 / 1,474 of those rows. The main problem is sparse
combinations, not just completely new combinations. The 100-record threshold
is an audit screen, not an established minimum for reliable probabilities.
Observations also share journeys and service conditions; raw row counts are
not independent sample counts. Group CSVs additionally report distinct journeys.

Therefore the next protocol should compare a global frequency baseline and
supported station/category estimates with a model that learns shared patterns
across inputs. Specify fallback/abstention rules before validation. Avoid a
standalone lookup probability for every hour/weekday combination.

## Next concrete checkpoint

Write the second experiment protocol: conditional >=15-minute proxy target,
training-only grouped baselines, a small classifier comparison, calibration,
chronological evaluation, uncertainty, subgroup support, and a predeclared
practical improvement criterion. Reserve a fresh final test period; July–October
are now all development evidence for this new experiment.

Before claiming practical reliability, validate a source or prospective sample
that preserves collection times, observed-vs-fallback labels, and historical
prediction inputs. Define cancellation treatment and measure coverage against
the services the application purports to support. This audit has not evaluated
an alternative source or started live collection. A historical demo must show
the data period and limitations and avoid connection-success or exact-buffer advice.

## Artifacts and verification

The generated report, `audit.json`, and twelve CSVs are in
`reports/generated/risk-audit/`. JSON contains source checksums/URLs/schema,
all cleaning exclusions, separate full-month and cohort label summaries, and
July-only support counts. Every pinned checksum matched, schemas matched, and
journey/event separation checks passed in the real run. No models were fitted
or existing model outputs overwritten.

All 17 synthetic tests passed, including four new tests covering the threshold,
signed labels, sensitivity denominators, empty/all-zero inputs, sparse/unseen
groups, and distinct-journey counts. Ruff code and format checks and dependency
consistency checks passed. Downloaded data and generated outputs remain outside Git.

Source: Deutsche Bahn data, CC BY 4.0; archive/processing by Piet Brömmel / piebro,
revision `3e9e69149f4008d0c24348c51d1ec79b552adaa5`. See
[source documentation](../specs/data-source.md) and
[the initial provenance audit](../specs/sample-audit.md).
