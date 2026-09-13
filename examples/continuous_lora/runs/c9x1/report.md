# Factor-Contribution Analysis Report

## Shapley Value Contributions

How much each feature contributes to the gap between the formula output (`prediction_expr`) and the target (`target`). Bigger values mean that feature has a stronger influence on the final result.

### Inputs

- Target (`target`): `col('GT SF')`
- Shapley formula (`prediction_expr`): `class_sf + round(2 * log2(measured_bw / class_bw))`
- Scoring mode (`score_mode`): `absolute`
- Formula apportioned across features: `outcome = |(class_sf + round(2 * log2(measured_bw / class_bw))) - (col('GT SF'))|`

| Feature | Description | Mean absolute | Mean signed | Total signed | Net share (%) |
|---|---|---:|---:|---:|---:|
| class (class_sf, class_bw) | Nominal class decision (BW and SF chosen together) | 0.190323 | 0.184096 | 1862.500000 | 92.29 |
| measured_bw | Measured BW (box estimate vs GT BW) | 0.048285 | 0.015370 | 155.500000 | 7.71 |

**In short:** `class` (Nominal class decision (BW and SF chosen together)) carries the largest net contribution share at 92.29%.

## Error Regimes

How much each condition (regime) contributes to the total observed prediction error. Here, prediction is the value from `prediction`, and target is the reference value from `target`. Share (%) shows what fraction of the total error comes from rows in that condition.

### Inputs

- Target (`target`): `col('GT SF')`
- Observed prediction (`prediction`): `col('Measured SF')`

| Regime | Count | Mean contribution | Total contribution | Share (%) |
|---|---:|---:|---:|---:|
| class_sf_match | 5993 | 0.1877 | 1125.00 | 55.75 |
| class_bw within tol & sf wrong | 264 | 0.9924 | 262.00 | 12.98 |
| class_unworkable | 2205 | 0.7211 | 1590.00 | 78.79 |
| class_ok & measured_ok | 3075 | 0.0881 | 271.00 | 13.43 |
| class_ok & measured_off | 21 | 0.6667 | 14.00 | 0.69 |
| upscale & measured_ok | 4431 | 0.2458 | 1089.00 | 53.96 |
| upscale & measured_off | 385 | 0.2571 | 99.00 | 4.91 |
| downscale & measured_ok | 2120 | 0.2377 | 504.00 | 24.98 |
| downscale & measured_off | 85 | 0.4824 | 41.00 | 2.03 |
| class_workable & bw_neutral | 7743 | 0.0406 | 314.00 | 15.56 |
| class_workable & bw_shifts | 169 | 0.6746 | 114.00 | 5.65 |
| class_unworkable & bw_neutral | 1883 | 0.8232 | 1550.00 | 76.81 |
| class_unworkable & bw_shifts | 322 | 0.1242 | 40.00 | 1.98 |

**In short:** the `class_unworkable` regime accounts for the largest share at 78.79%.

## Mismatch Risk

How much more often rows matching each condition have prediction different from target (`prediction != target`) compared with all other rows. A risk ratio above 1 means the condition is linked to more mismatches.

### Inputs

- Target (`target`): `col('GT SF')`
- Observed prediction (`prediction`): `col('Measured SF')`
- Mismatch definition: `prediction != target`

| Regime | Regime mismatch rate | Rest mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_sf_match | 18.77% (1125:4868) | 21.53% (888:3236) | 0.87 (0.75 to 1.07) | 0.84 (0.76 to 0.93) |
| class_bw within tol & sf wrong | 98.86% (261:3) | 17.78% (1752:8101) | 5.56 (5.32 to 5.81) | 402.28 (135.80 to 1964.55) |
| class_unworkable | 72.02% (1588:617) | 5.37% (425:7487) | 13.41 (12.18 to 14.76) | 45.34 (39.53 to 52.01) |
| class_ok & measured_ok | 8.81% (271:2804) | 24.74% (1742:5300) | 0.36 (0.31 to 0.41) | 0.29 (0.26 to 0.34) |
| class_ok & measured_off | 61.90% (13:8) | 19.81% (2000:8096) | 3.12 (2.05 to 4.04) | 6.58 (2.52 to 18.33) |
| upscale & measured_ok | 24.58% (1089:3342) | 16.25% (924:4762) | 1.51 (1.29 to 1.87) | 1.68 (1.52 to 1.85) |
| upscale & measured_off | 25.71% (99:286) | 19.67% (1914:7818) | 1.31 (1.08 to 1.57) | 1.41 (1.11 to 1.79) |
| downscale & measured_ok | 23.77% (504:1616) | 18.87% (1509:6488) | 1.26 (1.12 to 1.43) | 1.34 (1.19 to 1.51) |
| downscale & measured_off | 43.53% (37:48) | 19.70% (1976:8056) | 2.21 (1.69 to 2.78) | 3.14 (1.98 to 4.94) |
| class_workable & bw_neutral | 4.06% (314:7429) | 71.57% (1699:675) | 0.06 (0.05 to 0.06) | 0.02 (0.01 to 0.02) |
| class_workable & bw_shifts | 65.68% (111:58) | 19.12% (1902:8046) | 3.44 (2.99 to 3.89) | 8.10 (5.81 to 11.37) |
| class_unworkable & bw_neutral | 82.32% (1550:333) | 5.62% (463:7771) | 14.64 (13.37 to 16.03) | 78.12 (66.98 to 91.13) |
| class_unworkable & bw_shifts | 11.80% (38:284) | 20.16% (1975:7820) | 0.59 (0.43 to 0.79) | 0.53 (0.37 to 0.75) |

**In short:** `class_unworkable & bw_neutral` carries the highest mismatch risk (risk ratio 14.64).

## Factorial Matrices

Each matrix cell reports row count, mismatch rate, and mismatch risk ratio versus the rest of the dataset. Row/column marginals are computed over unions of member cells.

### BW quality × scaling direction

Rows split by where the nominal class BW sits relative to GT BW, and so by which way the geometric correction has to scale: class_ok is within 10% of GT BW, upscale is at least 10% below it (the correction pushes SF up), downscale at least 10% above it (the correction pushes SF down). Columns split by the bounding-box BW measurement: measured_ok is within half an SF step of GT BW, measured_off at least half a step away. This crossing asks which way the detector misses, not which decision to fix.

| Row level | measured_ok | measured_off | Row marginal |
|---|---|---|---|
| class_ok | n=3075, mismatch=8.81%, RR=0.36 (0.31 to 0.41) | n=21, mismatch=61.90%, RR=3.12 (2.05 to 4.04) | n=3096, mismatch=9.17%, RR=0.37 (0.33 to 0.43) |
| upscale | n=4431, mismatch=24.58%, RR=1.51 (1.29 to 1.87) | n=385, mismatch=25.71%, RR=1.31 (1.08 to 1.57) | n=4816, mismatch=24.67%, RR=1.59 (1.32 to 2.05) |
| downscale | n=2120, mismatch=23.77%, RR=1.26 (1.12 to 1.43) | n=85, mismatch=43.53%, RR=2.21 (1.69 to 2.78) | n=2205, mismatch=24.54%, RR=1.32 (1.17 to 1.50) |
| Column marginal | n=9626, mismatch=19.36%, RR=0.64 (0.55 to 0.73) | n=491, mismatch=30.35%, RR=1.57 (1.34 to 1.82) | n/a |

### Class decision × BW measurement

Each axis holds one Shapley player at its observed value and every other player at its declared baseline — for measured_bw that baseline is col('GT BW'), i.e. an exact bandwidth measurement; for the class it is the ground-truth class. A level therefore says whether that player alone, with nothing else contributing error, is enough to miss GT SF. Rows: class_workable means the observed class decision reaches GT SF once the bandwidth is measured exactly, so measuring better rescues it; class_unworkable means it misses GT SF even with an exact measurement, so measuring better cannot rescue it. Note that class_unworkable does not mean the row is lost — a compensating measurement error can still cancel the class error, which is what the low mismatch rate of the class_unworkable & bw_shifts cell counts. Columns: bw_neutral means the observed bandwidth measurement still reaches GT SF when paired with the ground-truth class, its error fitting inside the rounding step so it moves nothing on its own; bw_shifts means that error alone moves the estimate by at least one SF step.

| Row level | bw_neutral | bw_shifts | Row marginal |
|---|---|---|---|
| class_workable | n=7743, mismatch=4.06%, RR=0.06 (0.05 to 0.06) | n=169, mismatch=65.68%, RR=3.44 (2.99 to 3.89) | n=7912, mismatch=5.37%, RR=0.07 (0.07 to 0.08) |
| class_unworkable | n=1883, mismatch=82.32%, RR=14.64 (13.37 to 16.03) | n=322, mismatch=11.80%, RR=0.59 (0.43 to 0.79) | n=2205, mismatch=72.02%, RR=13.41 (12.18 to 14.76) |
| Column marginal | n=9626, mismatch=19.36%, RR=0.64 (0.55 to 0.73) | n=491, mismatch=30.35%, RR=1.57 (1.34 to 1.82) | n/a |

## Within-stratum contrasts

Sibling-level contrasts within each stratum reuse Koopman risk-ratio and Baptista-Pike odds-ratio intervals.

### BW quality × scaling direction :: columns=measured_off

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_ok vs upscale | 61.90% (13:8) | 25.71% (99:286) | 2.41 (1.47 to 4.56) | 4.69 (1.74 to 13.42) |
| class_ok vs downscale | 61.90% (13:8) | 43.53% (37:48) | 1.42 (0.94 to 2.15) | 2.11 (0.72 to 6.48) |
| upscale vs downscale | 25.71% (99:286) | 43.53% (37:48) | 0.59 (0.44 to 0.79) | 0.45 (0.27 to 0.76) |

### BW quality × scaling direction :: columns=measured_ok

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_ok vs upscale | 8.81% (271:2804) | 24.58% (1089:3342) | 0.36 (0.31 to 0.42) | 0.30 (0.26 to 0.34) |
| class_ok vs downscale | 8.81% (271:2804) | 23.77% (504:1616) | 0.37 (0.31 to 0.46) | 0.31 (0.26 to 0.36) |
| upscale vs downscale | 24.58% (1089:3342) | 23.77% (504:1616) | 1.03 (0.82 to 1.64) | 1.04 (0.92 to 1.18) |

### BW quality × scaling direction :: rows=class_ok

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| measured_ok vs measured_off | 8.81% (271:2804) | 61.90% (13:8) | 0.14 (0.10 to 0.20) | 0.06 (0.02 to 0.16) |

### BW quality × scaling direction :: rows=downscale

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| measured_ok vs measured_off | 23.77% (504:1616) | 43.53% (37:48) | 0.55 (0.42 to 0.70) | 0.40 (0.25 to 0.65) |

### BW quality × scaling direction :: rows=upscale

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| measured_ok vs measured_off | 24.58% (1089:3342) | 25.71% (99:286) | 0.96 (0.80 to 1.14) | 0.94 (0.74 to 1.21) |

### Class decision × BW measurement :: columns=bw_neutral

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_workable vs class_unworkable | 4.06% (314:7429) | 82.32% (1550:333) | 0.05 (0.04 to 0.06) | 0.01 (0.01 to 0.01) |

### Class decision × BW measurement :: columns=bw_shifts

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_workable vs class_unworkable | 65.68% (111:58) | 11.80% (38:284) | 5.57 (4.05 to 7.65) | 14.30 (8.77 to 23.40) |

### Class decision × BW measurement :: rows=class_unworkable

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| bw_neutral vs bw_shifts | 82.32% (1550:333) | 11.80% (38:284) | 6.98 (5.17 to 9.41) | 34.79 (24.12 to 51.11) |

### Class decision × BW measurement :: rows=class_workable

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| bw_neutral vs bw_shifts | 4.06% (314:7429) | 65.68% (111:58) | 0.06 (0.05 to 0.07) | 0.02 (0.02 to 0.03) |

## Attributable burden

Per baselined factorial crossing, rows are ranked by recoverable mismatches relative to the declared baseline cell.

### BW quality × scaling direction

Baseline cell: `class_ok & measured_ok`

| Rank | Cell | n | Mismatch rate | Baseline rate | Recoverable mismatches | Share of all mismatches | Risk difference (95% CI) | Accuracy if eliminated (accumulating) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | upscale & measured_ok | 4431 | 24.58% | 8.81% | 698.50 | 34.70% | 0.158 (0.141 to 0.174) | 87.01% |
| 2 | downscale & measured_ok | 2120 | 23.77% | 8.81% | 317.16 | 15.76% | 0.150 (0.129 to 0.171) | 90.14% |
| 3 | upscale & measured_off | 385 | 25.71% | 8.81% | 65.07 | 3.23% | 0.169 (0.127 to 0.216) | 90.79% |
| 4 | downscale & measured_off | 85 | 43.53% | 8.81% | 29.51 | 1.47% | 0.347 (0.246 to 0.454) | 91.08% |
| 5 | class_ok & measured_off | 21 | 61.90% | 8.81% | 11.15 | 0.55% | 0.531 (0.320 to 0.705) | 91.19% |

Counterfactual caveat: recoverable mismatches assume rows in a fixed regime revert to the baseline mismatch rate.

Observed accuracy: 80.10% | Ceiling accuracy after ranked eliminations: 91.19% | Total observed mismatches: 2013

### Class decision × BW measurement

Baseline cell: `class_workable & bw_neutral`

| Rank | Cell | n | Mismatch rate | Baseline rate | Recoverable mismatches | Share of all mismatches | Risk difference (95% CI) | Accuracy if eliminated (accumulating) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | class_unworkable & bw_neutral | 1883 | 82.32% | 4.06% | 1473.64 | 73.21% | 0.783 (0.764 to 0.800) | 94.67% |
| 2 | class_workable & bw_shifts | 169 | 65.68% | 4.06% | 104.15 | 5.17% | 0.616 (0.542 to 0.684) | 95.70% |
| 3 | class_unworkable & bw_shifts | 322 | 11.80% | 4.06% | 24.94 | 1.24% | 0.077 (0.046 to 0.117) | 95.94% |

Counterfactual caveat: recoverable mismatches assume rows in a fixed regime revert to the baseline mismatch rate.

Observed accuracy: 80.10% | Ceiling accuracy after ranked eliminations: 95.94% | Total observed mismatches: 2013

Rows: 10117
Mean observed contribution: 0.199466

---
**References**
Shapley values: Shapley (1953) *A value for n-person games*, Princeton UP; Lundberg & Lee (2017) *A unified approach to interpreting model predictions*, NeurIPS 30. Explicit per-feature baselines: Sundararajan & Najmi (2020) *The many Shapley values for model explanation*, ICML, PMLR 119:9269-9278.
Grouped players (Shapley over the quotient game): Aumann & Drèze (1974) *Cooperative games with coalition structures*, Int. J. Game Theory 3(4):217-237; Owen (1977) *Values of games with a priori unions*, in Henn & Moeschlin (eds.), 76-88; Jullum, Redelmeier & Aas (2021) *groupShapley*, arXiv:2106.12228.
Risk ratio CI: Koopman (1984) *Biometrics* 40(2):513-517. Odds ratio CI: Baptista & Pike (1977) *J. Roy. Statist. Soc. C* 26(2):214-220. Small-sample recommendation: Fagerland, Lydersen & Laake (2015, 2017).
Risk difference CI: Miettinen & Nurminen (1985) *Statistics in Medicine* 4(2):213-226. Guardrail: Agresti & Caffo (2000) *Amer. Statist.* 54(4):280-288.