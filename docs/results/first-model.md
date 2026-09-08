# First model experiment results

Run on 2026-09-08. This checked-in summary accompanies reproducible generated
reports in `reports/generated/model/`. Code: `python -m raildelay.experiment`.
The [protocol](../specs/model-experiment.md) was specified before model fitting
and before October target inspection. October is now used and must not be treated
as an untouched test set for another experiment.

## Outcome

August selected the training-median baseline on mean absolute error (MAE).
The best validation Ridge used alpha 100. Both remained trained only on July;
neither was retuned using September or October. The final October comparison:

| Method | MAE, minutes | RMSE, minutes | Arrival records |
| --- | ---: | ---: | ---: |
| July-median baseline | 7.682 | 15.131 | 137,974 |
| Ridge, alpha 100 | 7.659 | 13.097 | 137,974 |

Ridge's October MAE is only about 1.38 seconds lower. Keep the validation-selected
baseline as the result of this experiment. Ridge's lower RMSE suggests different
behavior on large errors; this is not evidence of reliable improvement in MAE.
No claim of statistical significance is made.

## Validated data

| Month | Selected rows | Clean arrivals | Experiment cohort | Role |
| --- | ---: | ---: | ---: | --- |
| July | 230,267 | 151,886 | 142,453 | Train |
| August | 227,976 | 152,667 | 143,594 | Validation |
| September | 216,926 | 143,734 | 133,642 | Previously explored development |
| October | 222,470 | 148,106 | 137,974 | Final evaluation |

Every pinned checksum matched, schemas were identical, and all ten stations were
present. Full journey IDs preserve the start timestamp; the archive's shortened
prefix repeats between services. Parsed prefix/sequence cross-checks and
journey/stop uniqueness checks passed. Cohorts share no full journey keys, and
events in each cohort precede the next cohort. Month-edge days and journeys are
excluded under the predeclared rule, with counts in the generated audit.

## Findings and limits

DB's [construction notice](https://assets-ri.extranet.deutschebahn.com/db_fernverkehr/2025-08-08/5f48c4cf-1c1f-4ec4-b001-41ae65e5cc01Detailinformationen%2BBauarbeiten%2Bzwischen%2BEssen%2Bund%2BDortmund_SepOkt.pdf)
documents diversions beginning September 5 and ending October 31, including
removal of long-distance stops at Bochum. September's missing cleaned Bochum
days are weekends whose raw records consist of buses, except one ICE record
that also fails cleaning. This explains the chart's missing days in terms of
observed records and exclusions, without proving hourly collection completeness.

Ambiguous zeros account for 18.5%, 17.9%, 15.8%, and 13.8% of clean arrivals in
July–October. Their observation provenance cannot be recovered from the monthly
files. The first three months have 16, 28, and 36 delays below −30 minutes.
These remain in the primary experiment, with diagnostic error views that exclude
zeros or very negative labels without refitting the models.

Features are restricted to station, scheduled arrival hour, weekday, and train
category. Final changed timestamps, journey IDs, and cancellation flags never
enter the predictor matrix. However, final archive plans do not establish exact
historical feature availability. This is a retrospective timetable-only benchmark;
the archive cannot support a claim of verified live departure-time performance.

Generated outputs include three PNG charts and MAE/RMSE/counts by station, hour,
and train category. Thirteen synthetic tests plus code/format checks passed;
both the original September workflow and the model workflow ran on real inputs.

Source: Deutsche Bahn data (CC BY 4.0), archived/processed by Piet Brömmel / piebro.
All files use [revision 3e9e691](https://huggingface.co/datasets/piebro/deutsche-bahn-data/tree/3e9e69149f4008d0c24348c51d1ec79b552adaa5).
Checksums and installed package versions are retained in the generated JSON files.
