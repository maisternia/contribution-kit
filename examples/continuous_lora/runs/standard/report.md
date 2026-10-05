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
| measured_bw | Measured BW (box estimate vs GT BW) | 0.002729 | 0.002729 | 6.500000 | 72.22 |
| class (class_sf, class_bw) | Nominal class decision (BW and SF chosen together) | 0.001469 | 0.001050 | 2.500000 | 27.78 |

**In short:** `measured_bw` (Measured BW (box estimate vs GT BW)) carries the largest net contribution share at 72.22%.

## Error Regimes

How much each condition (regime) contributes to the total observed prediction error. Here, prediction is the value from `prediction`, and target is the reference value from `target`. Share (%) shows what fraction of the total error comes from rows in that condition.

### Inputs

- Target (`target`): `col('GT SF')`
- Observed prediction (`prediction`): `col('Measured SF')`

| Regime | Count | Mean contribution | Total contribution | Share (%) |
|---|---:|---:|---:|---:|
| class_sf_match | 2370 | 0.0021 | 5.00 | 55.56 |
| class_bw within tol & sf wrong | 3 | 1.0000 | 3.00 | 33.33 |
| class_unworkable | 3 | 1.0000 | 3.00 | 33.33 |
| class_bw_under | 6 | 0.1667 | 1.00 | 11.11 |
| class_bw_over | 3 | 0.0000 | 0.00 | 0.00 |
| class_sf_wrong | 12 | 0.3333 | 4.00 | 44.44 |
| measured_bw_off | 46 | 0.1739 | 8.00 | 88.89 |
| clean | 2328 | 0.0000 | 0.00 | 0.00 |
| class_ok & measured_ok | 2368 | 0.0013 | 3.00 | 33.33 |
| class_ok & measured_off | 5 | 1.0000 | 5.00 | 55.56 |
| upscale & measured_ok | 5 | 0.0000 | 0.00 | 0.00 |
| upscale & measured_off | 1 | 1.0000 | 1.00 | 11.11 |
| downscale & measured_ok | 2 | 0.0000 | 0.00 | 0.00 |
| downscale & measured_off | 1 | 0.0000 | 0.00 | 0.00 |
| class_workable & bw_neutral | 2372 | 0.0000 | 0.00 | 0.00 |
| class_workable & bw_shifts | 7 | 0.8571 | 6.00 | 66.67 |
| class_unworkable & bw_neutral | 3 | 1.0000 | 3.00 | 33.33 |
| class_unworkable & bw_shifts | 0 | 0.0000 | 0.00 | 0.00 |

**In short:** the `measured_bw_off` regime accounts for the largest share at 88.89%.

## Mismatch Risk

How much more often rows matching each condition have prediction different from target (`prediction != target`) compared with all other rows. A risk ratio above 1 means the condition is linked to more mismatches.

### Inputs

- Target (`target`): `col('GT SF')`
- Observed prediction (`prediction`): `col('Measured SF')`
- Mismatch definition: `prediction != target`

| Regime | Regime mismatch rate | Rest mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_sf_match | 0.21% (5:2365) | 33.33% (4:8) | 0.01 (0.00 to 0.02) | 0.00 (0.00 to 0.02) |
| class_bw within tol & sf wrong | 100.00% (3:0) | 0.25% (6:2373) | 396.50 (135.87 to 864.77) | inf (n/a) |
| class_unworkable | 100.00% (3:0) | 0.25% (6:2373) | 396.50 (135.87 to 864.77) | inf (n/a) |
| class_bw_under | 16.67% (1:5) | 0.34% (8:2368) | 49.50 (8.20 to 216.18) | 59.20 (2.26 to 582.22) |
| class_sf_wrong | 33.33% (4:8) | 0.21% (5:2365) | 158.00 (48.27 to 466.39) | 236.50 (49.18 to 1069.01) |
| measured_bw_off | 17.39% (8:38) | 0.04% (1:2335) | 406.26 (66.65 to 2464.39) | 491.58 (70.87 to 10749.19) |
| class_ok & measured_ok | 0.13% (3:2365) | 42.86% (6:8) | 0.00 (0.00 to 0.01) | 0.00 (0.00 to 0.01) |
| class_ok & measured_off | 100.00% (5:0) | 0.17% (4:2373) | 594.25 (218.07 to 1527.66) | inf (n/a) |
| upscale & measured_off | 100.00% (1:0) | 0.34% (8:2373) | 297.62 (55.95 to 587.02) | inf (n/a) |
| class_workable & bw_shifts | 85.71% (6:1) | 0.13% (3:2372) | 678.57 (212.60 to 2049.42) | 4744.00 (406.70 to 106965.66) |
| class_unworkable & bw_neutral | 100.00% (3:0) | 0.25% (6:2373) | 396.50 (135.87 to 864.77) | inf (n/a) |

**In short:** `class_workable & bw_shifts` carries the highest mismatch risk (risk ratio 678.57).

## Factorial Matrices

Each matrix cell reports row count, mismatch rate, and mismatch risk ratio versus the rest of the dataset. Row/column marginals are computed over unions of member cells.

### BW quality × scaling direction

Rows split by where the nominal class BW sits relative to GT BW, and so by which way the geometric correction has to scale: class_ok is within 10% of GT BW, upscale is at least 10% below it (the correction pushes SF up), downscale at least 10% above it (the correction pushes SF down). Columns split by the bounding-box BW measurement: measured_ok is within half an SF step of GT BW, measured_off at least half a step away. This crossing asks which way the detector misses, not which decision to fix.

| Row level | measured_ok | measured_off | Row marginal |
|---|---|---|---|
| class_ok | n=2368, mismatch=0.13%, RR=0.00 (0.00 to 0.01) | n=5, mismatch=100.00%, RR=594.25 (218.07 to 1527.66) | n=2373, mismatch=0.34%, RR=0.03 (0.01 to 0.18) |
| upscale | n=5, mismatch=0.00%, RR=0.00 (n/a) | n=1, mismatch=100.00%, RR=297.62 (55.95 to 587.02) | n=6, mismatch=16.67%, RR=49.50 (8.20 to 216.18) |
| downscale | n=2, mismatch=0.00%, RR=0.00 (n/a) | n=1, mismatch=0.00%, RR=0.00 (n/a) | n=3, mismatch=0.00%, RR=0.00 (n/a) |
| Column marginal | n=2375, mismatch=0.13%, RR=0.00 (0.00 to 0.00) | n=7, mismatch=85.71%, RR=678.57 (212.60 to 2049.42) | n/a |

### Class decision × BW measurement

Each axis holds one Shapley player at its observed value and every other player at its declared baseline — for measured_bw that baseline is col('GT BW'), i.e. an exact bandwidth measurement; for the class it is the ground-truth class. A level therefore says whether that player alone, with nothing else contributing error, is enough to miss GT SF. Rows: class_workable means the observed class decision reaches GT SF once the bandwidth is measured exactly, so measuring better rescues it; class_unworkable means it misses GT SF even with an exact measurement, so measuring better cannot rescue it. Note that class_unworkable does not mean the row is lost — a compensating measurement error can still cancel the class error, which is what the low mismatch rate of the class_unworkable & bw_shifts cell counts. Columns: bw_neutral means the observed bandwidth measurement still reaches GT SF when paired with the ground-truth class, its error fitting inside the rounding step so it moves nothing on its own; bw_shifts means that error alone moves the estimate by at least one SF step.

| Row level | bw_neutral | bw_shifts | Row marginal |
|---|---|---|---|
| class_workable | n=2372, mismatch=0.00%, RR=0.00 (n/a) | n=7, mismatch=85.71%, RR=678.57 (212.60 to 2049.42) | n=2379, mismatch=0.25%, RR=0.00 (0.00 to 0.01) |
| class_unworkable | n=3, mismatch=100.00%, RR=396.50 (135.87 to 864.77) | n=0, mismatch=0.00%, RR=n/a | n=3, mismatch=100.00%, RR=396.50 (135.87 to 864.77) |
| Column marginal | n=2375, mismatch=0.13%, RR=0.00 (0.00 to 0.00) | n=7, mismatch=85.71%, RR=678.57 (212.60 to 2049.42) | n/a |

## Within-stratum contrasts

Sibling-level contrasts within each stratum use the same risk-ratio and odds-ratio intervals as the mismatch-risk table.

### BW quality × scaling direction :: columns=measured_off

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_ok vs upscale | 100.00% (5:0) | 100.00% (1:0) | 1.00 (0.57 to 4.84) | inf (n/a) |
| class_ok vs downscale | 100.00% (5:0) | 0.00% (0:1) | inf (n/a) | inf (n/a) |
| upscale vs downscale | 100.00% (1:0) | 0.00% (0:1) | inf (n/a) | inf (n/a) |

### BW quality × scaling direction :: columns=measured_ok

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_ok vs upscale | 0.13% (3:2365) | 0.00% (0:5) | inf (n/a) | inf (n/a) |
| class_ok vs downscale | 0.13% (3:2365) | 0.00% (0:2) | inf (n/a) | inf (n/a) |
| upscale vs downscale | 0.00% (0:5) | 0.00% (0:2) | inf (n/a) | inf (n/a) |

### BW quality × scaling direction :: rows=class_ok

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| measured_ok vs measured_off | 0.13% (3:2365) | 100.00% (5:0) | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) |

### BW quality × scaling direction :: rows=downscale

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| measured_ok vs measured_off | 0.00% (0:2) | 0.00% (0:1) | inf (n/a) | inf (n/a) |

### BW quality × scaling direction :: rows=upscale

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| measured_ok vs measured_off | 0.00% (0:5) | 100.00% (1:0) | 0.00 (n/a) | 0.03 (0.00 to 3.80) |

### Class decision × BW measurement :: columns=bw_neutral

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_workable vs class_unworkable | 0.00% (0:2372) | 100.00% (3:0) | 0.00 (n/a) | 0.00 (0.00 to 0.00) |

### Class decision × BW measurement :: rows=class_workable

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| bw_neutral vs bw_shifts | 0.00% (0:2372) | 85.71% (6:1) | 0.00 (n/a) | 0.00 (0.00 to 0.00) |

## Attributable burden

Per baselined factorial crossing, rows are ranked by recoverable mismatches relative to the declared baseline cell.

### BW quality × scaling direction

Baseline cell: `class_ok & measured_ok`

| Rank | Cell | n | Mismatch rate | Baseline rate | Recoverable mismatches | Share of all mismatches | Risk difference (95% CI) | Accuracy if eliminated (accumulating) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | class_ok & measured_off | 5 | 100.00% | 0.13% | 4.99 | 55.49% | 0.999 (0.564 to 1.000) | 99.83% |
| 2 | upscale & measured_off | 1 | 100.00% | 0.13% | 1.00 | 11.10% | 0.999 (0.205 to 1.000) | 99.87% |
| 3 | upscale & measured_ok | 5 | 0.00% | 0.13% | - | - | -0.001 (-0.004 to 0.433) | 99.87% |
| 4 | downscale & measured_ok | 2 | 0.00% | 0.13% | - | - | -0.001 (-0.004 to 0.656) | 99.87% |
| 5 | downscale & measured_off | 1 | 0.00% | 0.13% | - | - | -0.001 (-0.004 to 0.792) | 99.87% |

Baseline sanity warning: Declared baseline 'class_ok & measured_ok' is not the lowest mismatch-rate cell in 'BW quality × scaling direction'.

Counterfactual caveat: recoverable mismatches assume rows in a fixed regime revert to the baseline mismatch rate.

Observed accuracy: 99.62% | Ceiling accuracy after ranked eliminations: 99.87% | Total observed mismatches: 9

### Class decision × BW measurement

Baseline cell: `class_workable & bw_neutral`

| Rank | Cell | n | Mismatch rate | Baseline rate | Recoverable mismatches | Share of all mismatches | Risk difference (95% CI) | Accuracy if eliminated (accumulating) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | class_workable & bw_shifts | 7 | 85.71% | 0.00% | 6.00 | 66.67% | 0.857 (0.487 to 0.974) | 99.87% |
| 2 | class_unworkable & bw_neutral | 3 | 100.00% | 0.00% | 3.00 | 33.33% | 1.000 (0.438 to 1.000) | 100.00% |

Empty cells note: left out of the ranking because they matched no rows: `class_unworkable & bw_shifts`.

Counterfactual caveat: recoverable mismatches assume rows in a fixed regime revert to the baseline mismatch rate.

Observed accuracy: 99.62% | Ceiling accuracy after ranked eliminations: 100.00% | Total observed mismatches: 9

Rows: 2382
Mean observed contribution: 0.003778

---
**References**
Shapley values: Shapley (1953) *A value for n-person games*, Princeton UP; Lundberg & Lee (2017) *A unified approach to interpreting model predictions*, NeurIPS 30. Explicit per-feature baselines: Sundararajan & Najmi (2020) *The many Shapley values for model explanation*, ICML, PMLR 119:9269-9278.
Grouped players (Shapley over the quotient game): Aumann & Drèze (1974) *Cooperative games with coalition structures*, Int. J. Game Theory 3(4):217-237; Owen (1977) *Values of games with a priori unions*, in Henn & Moeschlin (eds.), 76-88; Jullum, Redelmeier & Aas (2021) *groupShapley*, arXiv:2106.12228.
Risk ratio CI: Koopman (1984) *Biometrics* 40(2):513-517. Odds ratio CI: Baptista & Pike (1977) *J. Roy. Statist. Soc. C* 26(2):214-220. Small-sample recommendation: Fagerland, Lydersen & Laake (2015, 2017).
Risk difference CI: Miettinen & Nurminen (1985) *Statistics in Medicine* 4(2):213-226. Guardrail: Agresti & Caffo (2000) *Amer. Statist.* 54(4):280-288.