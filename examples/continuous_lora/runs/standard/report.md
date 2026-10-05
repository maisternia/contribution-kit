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
| measured_bw | Measured BW (box estimate vs GT BW) | 0.006941 | 0.006941 | 62.000000 | 82.67 |
| class (class_sf, class_bw) | Nominal class decision (BW and SF chosen together) | 0.001903 | 0.001455 | 13.000000 | 17.33 |

**In short:** `measured_bw` (Measured BW (box estimate vs GT BW)) carries the largest net contribution share at 82.67%.

## Error Regimes

How much each condition (regime) contributes to the total observed prediction error. Here, prediction is the value from `prediction`, and target is the reference value from `target`. Share (%) shows what fraction of the total error comes from rows in that condition.

### Inputs

- Target (`target`): `col('GT SF')`
- Observed prediction (`prediction`): `col('Measured SF')`

| Regime | Count | Mean contribution | Total contribution | Share (%) |
|---|---:|---:|---:|---:|
| class_sf_match | 8875 | 0.0060 | 53.00 | 70.67 |
| class_bw within tol & sf wrong | 5 | 1.0000 | 5.00 | 6.67 |
| class_unworkable | 25 | 0.7200 | 18.00 | 24.00 |
| class_bw_under | 6 | 0.1667 | 1.00 | 1.33 |
| class_bw_over | 57 | 0.2982 | 17.00 | 22.67 |
| class_sf_wrong | 57 | 0.3860 | 22.00 | 29.33 |
| measured_bw_off | 361 | 0.1939 | 70.00 | 93.33 |
| clean | 8533 | 0.0000 | 0.00 | 0.00 |
| class_ok & measured_ok | 8817 | 0.0006 | 5.00 | 6.67 |
| class_ok & measured_off | 52 | 1.0000 | 52.00 | 69.33 |
| upscale & measured_ok | 5 | 0.0000 | 0.00 | 0.00 |
| upscale & measured_off | 1 | 1.0000 | 1.00 | 1.33 |
| downscale & measured_ok | 34 | 0.0882 | 3.00 | 4.00 |
| downscale & measured_off | 23 | 0.6087 | 14.00 | 18.67 |
| class_workable & bw_neutral | 8849 | 0.0000 | 0.00 | 0.00 |
| class_workable & bw_shifts | 58 | 0.9828 | 57.00 | 76.00 |
| class_unworkable & bw_neutral | 7 | 1.1429 | 8.00 | 10.67 |
| class_unworkable & bw_shifts | 18 | 0.5556 | 10.00 | 13.33 |

**In short:** the `measured_bw_off` regime accounts for the largest share at 93.33%.

## Mismatch Risk

How much more often rows matching each condition have prediction different from target (`prediction != target`) compared with all other rows. A risk ratio above 1 means the condition is linked to more mismatches.

### Inputs

- Target (`target`): `col('GT SF')`
- Observed prediction (`prediction`): `col('Measured SF')`
- Mismatch definition: `prediction != target`

| Regime | Regime mismatch rate | Rest mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_sf_match | 0.60% (53:8822) | 28.07% (16:41) | 0.02 (0.01 to 0.04) | 0.02 (0.01 to 0.03) |
| class_bw within tol & sf wrong | 100.00% (5:0) | 0.72% (64:8863) | 139.48 (76.31 to 177.98) | inf (n/a) |
| class_unworkable | 52.00% (13:12) | 0.63% (56:8851) | 82.71 (49.93 to 124.71) | 171.22 (74.37 to 402.23) |
| class_bw_under | 16.67% (1:5) | 0.76% (68:8858) | 21.88 (3.90 to 77.06) | 26.05 (1.10 to 192.16) |
| class_bw_over | 19.30% (11:46) | 0.65% (58:8817) | 29.53 (16.16 to 51.33) | 36.35 (17.76 to 75.19) |
| class_sf_wrong | 28.07% (16:41) | 0.60% (53:8822) | 47.00 (28.20 to 74.98) | 64.96 (33.57 to 122.88) |
| measured_bw_off | 18.01% (65:296) | 0.05% (4:8567) | 385.81 (146.81 to 1013.83) | 470.32 (170.06 to 1419.41) |
| class_ok & measured_ok | 0.06% (5:8812) | 55.65% (64:51) | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |
| class_ok & measured_off | 100.00% (52:0) | 0.19% (17:8863) | 522.35 (326.38 to 836.36) | inf (n/a) |
| upscale & measured_off | 100.00% (1:0) | 0.76% (68:8863) | 131.34 (26.82 to 166.37) | inf (n/a) |
| downscale & measured_ok | 5.88% (2:32) | 0.75% (67:8831) | 7.81 (2.13 to 26.01) | 8.24 (1.38 to 32.59) |
| downscale & measured_off | 39.13% (9:14) | 0.67% (60:8849) | 58.10 (31.35 to 95.66) | 94.81 (37.04 to 225.60) |
| class_workable & bw_shifts | 96.55% (56:2) | 0.15% (13:8861) | 659.08 (384.48 to 1129.63) | 19085.23 (3989.40 to 112937.11) |
| class_unworkable & bw_neutral | 100.00% (7:0) | 0.69% (62:8863) | 143.95 (89.40 to 184.40) | inf (n/a) |
| class_unworkable & bw_shifts | 33.33% (6:12) | 0.71% (63:8851) | 47.16 (22.21 to 85.27) | 70.25 (25.17 to 192.20) |

**In short:** `class_workable & bw_shifts` carries the highest mismatch risk (risk ratio 659.08).

## Factorial Matrices

Each matrix cell reports row count, mismatch rate, and mismatch risk ratio versus the rest of the dataset. Row/column marginals are computed over unions of member cells.

### BW quality × scaling direction

Rows split by where the nominal class BW sits relative to GT BW, and so by which way the geometric correction has to scale: class_ok is within 10% of GT BW, upscale is at least 10% below it (the correction pushes SF up), downscale at least 10% above it (the correction pushes SF down). Columns split by the bounding-box BW measurement: measured_ok is within half an SF step of GT BW, measured_off at least half a step away. This crossing asks which way the detector misses, not which decision to fix.

| Row level | measured_ok | measured_off | Row marginal |
|---|---|---|---|
| class_ok | n=8817, mismatch=0.06%, RR=0.00 (0.00 to 0.00) | n=52, mismatch=100.00%, RR=522.35 (326.38 to 836.36) | n=8869, mismatch=0.64%, RR=0.03 (0.02 to 0.06) |
| upscale | n=5, mismatch=0.00%, RR=0.00 (n/a) | n=1, mismatch=100.00%, RR=131.34 (26.82 to 166.37) | n=6, mismatch=16.67%, RR=21.88 (3.90 to 77.06) |
| downscale | n=34, mismatch=5.88%, RR=7.81 (2.13 to 26.01) | n=23, mismatch=39.13%, RR=58.10 (31.35 to 95.66) | n=57, mismatch=19.30%, RR=29.53 (16.16 to 51.33) |
| Column marginal | n=8856, mismatch=0.08%, RR=0.00 (0.00 to 0.00) | n=76, mismatch=81.58%, RR=1032.09 (496.28 to 2145.00) | n/a |

### Class decision × BW measurement

Each axis holds one Shapley player at its observed value and every other player at its declared baseline — for measured_bw that baseline is col('GT BW'), i.e. an exact bandwidth measurement; for the class it is the ground-truth class. A level therefore says whether that player alone, with nothing else contributing error, is enough to miss GT SF. Rows: class_workable means the observed class decision reaches GT SF once the bandwidth is measured exactly, so measuring better rescues it; class_unworkable means it misses GT SF even with an exact measurement, so measuring better cannot rescue it. Note that class_unworkable does not mean the row is lost — a compensating measurement error can still cancel the class error, which is what the low mismatch rate of the class_unworkable & bw_shifts cell counts. Columns: bw_neutral means the observed bandwidth measurement still reaches GT SF when paired with the ground-truth class, its error fitting inside the rounding step so it moves nothing on its own; bw_shifts means that error alone moves the estimate by at least one SF step.

| Row level | bw_neutral | bw_shifts | Row marginal |
|---|---|---|---|
| class_workable | n=8849, mismatch=0.00%, RR=0.00 (n/a) | n=58, mismatch=96.55%, RR=659.08 (384.48 to 1129.63) | n=8907, mismatch=0.63%, RR=0.01 (0.01 to 0.02) |
| class_unworkable | n=7, mismatch=100.00%, RR=143.95 (89.40 to 184.40) | n=18, mismatch=33.33%, RR=47.16 (22.21 to 85.27) | n=25, mismatch=52.00%, RR=82.71 (49.93 to 124.71) |
| Column marginal | n=8856, mismatch=0.08%, RR=0.00 (0.00 to 0.00) | n=76, mismatch=81.58%, RR=1032.09 (496.28 to 2145.00) | n/a |

## Within-stratum contrasts

Sibling-level contrasts within each stratum use the same risk-ratio and odds-ratio intervals as the mismatch-risk table.

### BW quality × scaling direction :: columns=measured_off

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_ok vs upscale | 100.00% (52:0) | 100.00% (1:0) | 1.00 (0.93 to 4.84) | inf (n/a) |
| class_ok vs downscale | 100.00% (52:0) | 39.13% (9:14) | 2.56 (1.69 to 4.51) | inf (n/a) |
| upscale vs downscale | 100.00% (1:0) | 39.13% (9:14) | 2.56 (0.50 to 4.51) | inf (n/a) |

### BW quality × scaling direction :: columns=measured_ok

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_ok vs upscale | 0.06% (5:8812) | 0.00% (0:5) | inf (n/a) | inf (n/a) |
| class_ok vs downscale | 0.06% (5:8812) | 5.88% (2:32) | 0.01 (0.00 to 0.04) | 0.01 (0.00 to 0.07) |
| upscale vs downscale | 0.00% (0:5) | 5.88% (2:32) | 0.00 (n/a) | 1.18 (0.00 to 25.24) |

### BW quality × scaling direction :: rows=class_ok

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| measured_ok vs measured_off | 0.06% (5:8812) | 100.00% (52:0) | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |

### BW quality × scaling direction :: rows=downscale

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| measured_ok vs measured_off | 5.88% (2:32) | 39.13% (9:14) | 0.15 (0.04 to 0.55) | 0.10 (0.01 to 0.50) |

### BW quality × scaling direction :: rows=upscale

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| measured_ok vs measured_off | 0.00% (0:5) | 100.00% (1:0) | 0.00 (n/a) | 0.03 (0.00 to 3.80) |

### Class decision × BW measurement :: columns=bw_neutral

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_workable vs class_unworkable | 0.00% (0:8849) | 100.00% (7:0) | 0.00 (n/a) | 0.00 (0.00 to 0.00) |

### Class decision × BW measurement :: columns=bw_shifts

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_workable vs class_unworkable | 96.55% (56:2) | 33.33% (6:12) | 2.90 (1.71 to 5.94) | 56.00 (9.31 to 381.33) |

### Class decision × BW measurement :: rows=class_unworkable

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| bw_neutral vs bw_shifts | 100.00% (7:0) | 33.33% (6:12) | 3.00 (1.62 to 6.14) | inf (n/a) |

### Class decision × BW measurement :: rows=class_workable

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| bw_neutral vs bw_shifts | 0.00% (0:8849) | 96.55% (56:2) | 0.00 (n/a) | 0.00 (0.00 to 0.00) |

## Attributable burden

Per baselined factorial crossing, rows are ranked by recoverable mismatches relative to the declared baseline cell.

### BW quality × scaling direction

Baseline cell: `class_ok & measured_ok`

| Rank | Cell | n | Mismatch rate | Baseline rate | Recoverable mismatches | Share of all mismatches | Risk difference (95% CI) | Accuracy if eliminated (accumulating) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | class_ok & measured_off | 52 | 100.00% | 0.06% | 51.97 | 75.32% | 0.999 (0.931 to 1.000) | 99.81% |
| 2 | downscale & measured_off | 23 | 39.13% | 0.06% | 8.99 | 13.02% | 0.391 (0.221 to 0.592) | 99.91% |
| 3 | downscale & measured_ok | 34 | 5.88% | 0.06% | 1.98 | 2.87% | 0.058 (0.016 to 0.190) | 99.93% |
| 4 | upscale & measured_off | 1 | 100.00% | 0.06% | 1.00 | 1.45% | 0.999 (0.206 to 1.000) | 99.94% |
| 5 | upscale & measured_ok | 5 | 0.00% | 0.06% | - | - | -0.001 (-0.001 to 0.434) | 99.94% |

Baseline sanity warning: Declared baseline 'class_ok & measured_ok' is not the lowest mismatch-rate cell in 'BW quality × scaling direction'.

Counterfactual caveat: recoverable mismatches assume rows in a fixed regime revert to the baseline mismatch rate.

Observed accuracy: 99.23% | Ceiling accuracy after ranked eliminations: 99.94% | Total observed mismatches: 69

### Class decision × BW measurement

Baseline cell: `class_workable & bw_neutral`

| Rank | Cell | n | Mismatch rate | Baseline rate | Recoverable mismatches | Share of all mismatches | Risk difference (95% CI) | Accuracy if eliminated (accumulating) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | class_workable & bw_shifts | 58 | 96.55% | 0.00% | 56.00 | 81.16% | 0.966 (0.883 to 0.990) | 99.85% |
| 2 | class_unworkable & bw_neutral | 7 | 100.00% | 0.00% | 7.00 | 10.14% | 1.000 (0.646 to 1.000) | 99.93% |
| 3 | class_unworkable & bw_shifts | 18 | 33.33% | 0.00% | 6.00 | 8.70% | 0.333 (0.163 to 0.563) | 100.00% |

Counterfactual caveat: recoverable mismatches assume rows in a fixed regime revert to the baseline mismatch rate.

Observed accuracy: 99.23% | Ceiling accuracy after ranked eliminations: 100.00% | Total observed mismatches: 69

Rows: 8932
Mean observed contribution: 0.008397

---
**References**
Shapley values: Shapley (1953) *A value for n-person games*, Princeton UP; Lundberg & Lee (2017) *A unified approach to interpreting model predictions*, NeurIPS 30. Explicit per-feature baselines: Sundararajan & Najmi (2020) *The many Shapley values for model explanation*, ICML, PMLR 119:9269-9278.
Grouped players (Shapley over the quotient game): Aumann & Drèze (1974) *Cooperative games with coalition structures*, Int. J. Game Theory 3(4):217-237; Owen (1977) *Values of games with a priori unions*, in Henn & Moeschlin (eds.), 76-88; Jullum, Redelmeier & Aas (2021) *groupShapley*, arXiv:2106.12228.
Risk ratio CI: Koopman (1984) *Biometrics* 40(2):513-517. Odds ratio CI: Baptista & Pike (1977) *J. Roy. Statist. Soc. C* 26(2):214-220. Small-sample recommendation: Fagerland, Lydersen & Laake (2015, 2017).
Risk difference CI: Miettinen & Nurminen (1985) *Statistics in Medicine* 4(2):213-226. Guardrail: Agresti & Caffo (2000) *Amer. Statist.* 54(4):280-288.