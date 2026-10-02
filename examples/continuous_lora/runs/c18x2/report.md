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
| class (class_sf, class_bw) | Nominal class decision (BW and SF chosen together) | 0.048686 | 0.045690 | 396.500000 | 79.78 |
| measured_bw | Measured BW (box estimate vs GT BW) | 0.021722 | 0.011581 | 100.500000 | 20.22 |

**In short:** `class` (Nominal class decision (BW and SF chosen together)) carries the largest net contribution share at 79.78%.

## Error Regimes

How much each condition (regime) contributes to the total observed prediction error. Here, prediction is the value from `prediction`, and target is the reference value from `target`. Share (%) shows what fraction of the total error comes from rows in that condition.

### Inputs

- Target (`target`): `col('GT SF')`
- Observed prediction (`prediction`): `col('Measured SF')`

| Regime | Count | Mean contribution | Total contribution | Share (%) |
|---|---:|---:|---:|---:|
| class_sf_match | 8314 | 0.0449 | 373.00 | 75.05 |
| class_bw within tol & sf wrong | 9 | 1.0000 | 9.00 | 1.81 |
| class_unworkable | 379 | 0.7361 | 279.00 | 56.14 |
| class_ok & measured_ok | 6093 | 0.0033 | 20.00 | 4.02 |
| class_ok & measured_off | 29 | 0.5172 | 15.00 | 3.02 |
| upscale & measured_ok | 973 | 0.2425 | 236.00 | 47.48 |
| upscale & measured_off | 21 | 0.5714 | 12.00 | 2.41 |
| downscale & measured_ok | 1529 | 0.1282 | 196.00 | 39.44 |
| downscale & measured_off | 33 | 0.5455 | 18.00 | 3.62 |
| class_workable & bw_neutral | 8233 | 0.0216 | 178.00 | 35.81 |
| class_workable & bw_shifts | 66 | 0.6061 | 40.00 | 8.05 |
| class_unworkable & bw_neutral | 362 | 0.7569 | 274.00 | 55.13 |
| class_unworkable & bw_shifts | 17 | 0.2941 | 5.00 | 1.01 |

**In short:** the `class_sf_match` regime accounts for the largest share at 75.05%.

## Mismatch Risk

How much more often rows matching each condition have prediction different from target (`prediction != target`) compared with all other rows. A risk ratio above 1 means the condition is linked to more mismatches.

### Inputs

- Target (`target`): `col('GT SF')`
- Observed prediction (`prediction`): `col('Measured SF')`
- Mismatch definition: `prediction != target`

| Regime | Regime mismatch rate | Rest mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_sf_match | 4.49% (373:7941) | 34.07% (124:240) | 0.13 (0.11 to 0.16) | 0.09 (0.07 to 0.12) |
| class_bw within tol & sf wrong | 100.00% (9:0) | 5.63% (488:8181) | 17.76 (12.39 to 19.37) | inf (n/a) |
| class_unworkable | 73.61% (279:100) | 2.63% (218:8081) | 28.02 (24.25 to 32.35) | 103.42 (78.70 to 134.97) |
| class_ok & measured_ok | 0.33% (20:6073) | 18.45% (477:2108) | 0.02 (0.01 to 0.03) | 0.01 (0.01 to 0.02) |
| class_ok & measured_off | 51.72% (15:14) | 5.57% (482:8167) | 9.28 (6.13 to 12.52) | 18.15 (8.69 to 38.44) |
| upscale & measured_ok | 24.25% (236:737) | 3.39% (261:7444) | 7.16 (6.08 to 8.42) | 9.13 (7.53 to 11.11) |
| upscale & measured_off | 57.14% (12:9) | 5.60% (485:8172) | 10.20 (6.48 to 13.72) | 22.47 (9.15 to 56.01) |
| downscale & measured_ok | 12.82% (196:1333) | 4.21% (301:6848) | 3.04 (2.56 to 3.61) | 3.35 (2.77 to 4.06) |
| downscale & measured_off | 54.55% (18:15) | 5.54% (479:8166) | 9.84 (6.79 to 12.89) | 20.46 (10.21 to 42.83) |
| class_workable & bw_neutral | 2.16% (178:8055) | 71.69% (319:126) | 0.03 (0.03 to 0.04) | 0.01 (0.01 to 0.01) |
| class_workable & bw_shifts | 60.61% (40:26) | 5.31% (457:8155) | 11.42 (9.01 to 13.83) | 27.45 (16.47 to 46.71) |
| class_unworkable & bw_neutral | 75.69% (274:88) | 2.68% (223:8093) | 28.23 (24.47 to 32.51) | 113.00 (85.23 to 149.10) |
| class_unworkable & bw_shifts | 29.41% (5:12) | 5.68% (492:8169) | 5.18 (2.33 to 9.43) | 6.92 (2.34 to 19.73) |

**In short:** `class_unworkable & bw_neutral` carries the highest mismatch risk (risk ratio 28.23).

## Factorial Matrices

Each matrix cell reports row count, mismatch rate, and mismatch risk ratio versus the rest of the dataset. Row/column marginals are computed over unions of member cells.

### BW quality × scaling direction

Rows split by where the nominal class BW sits relative to GT BW, and so by which way the geometric correction has to scale: class_ok is within 10% of GT BW, upscale is at least 10% below it (the correction pushes SF up), downscale at least 10% above it (the correction pushes SF down). Columns split by the bounding-box BW measurement: measured_ok is within half an SF step of GT BW, measured_off at least half a step away. This crossing asks which way the detector misses, not which decision to fix.

| Row level | measured_ok | measured_off | Row marginal |
|---|---|---|---|
| class_ok | n=6093, mismatch=0.33%, RR=0.02 (0.01 to 0.03) | n=29, mismatch=51.72%, RR=9.28 (6.13 to 12.52) | n=6122, mismatch=0.57%, RR=0.03 (0.02 to 0.04) |
| upscale | n=973, mismatch=24.25%, RR=7.16 (6.08 to 8.42) | n=21, mismatch=57.14%, RR=10.20 (6.48 to 13.72) | n=994, mismatch=24.95%, RR=7.70 (6.54 to 9.05) |
| downscale | n=1529, mismatch=12.82%, RR=3.04 (2.56 to 3.61) | n=33, mismatch=54.55%, RR=9.84 (6.79 to 12.89) | n=1562, mismatch=13.70%, RR=3.44 (2.91 to 4.08) |
| Column marginal | n=8595, mismatch=5.26%, RR=0.10 (0.08 to 0.12) | n=83, mismatch=54.22%, RR=10.31 (8.15 to 12.57) | n/a |

### Class decision × BW measurement

Each axis holds one Shapley player at its observed value and every other player at its declared baseline — for measured_bw that baseline is col('GT BW'), i.e. an exact bandwidth measurement; for the class it is the ground-truth class. A level therefore says whether that player alone, with nothing else contributing error, is enough to miss GT SF. Rows: class_workable means the observed class decision reaches GT SF once the bandwidth is measured exactly, so measuring better rescues it; class_unworkable means it misses GT SF even with an exact measurement, so measuring better cannot rescue it. Note that class_unworkable does not mean the row is lost — a compensating measurement error can still cancel the class error, which is what the low mismatch rate of the class_unworkable & bw_shifts cell counts. Columns: bw_neutral means the observed bandwidth measurement still reaches GT SF when paired with the ground-truth class, its error fitting inside the rounding step so it moves nothing on its own; bw_shifts means that error alone moves the estimate by at least one SF step.

| Row level | bw_neutral | bw_shifts | Row marginal |
|---|---|---|---|
| class_workable | n=8233, mismatch=2.16%, RR=0.03 (0.03 to 0.04) | n=66, mismatch=60.61%, RR=11.42 (9.01 to 13.83) | n=8299, mismatch=2.63%, RR=0.04 (0.03 to 0.04) |
| class_unworkable | n=362, mismatch=75.69%, RR=28.23 (24.47 to 32.51) | n=17, mismatch=29.41%, RR=5.18 (2.33 to 9.43) | n=379, mismatch=73.61%, RR=28.02 (24.25 to 32.35) |
| Column marginal | n=8595, mismatch=5.26%, RR=0.10 (0.08 to 0.12) | n=83, mismatch=54.22%, RR=10.31 (8.15 to 12.57) | n/a |

## Within-stratum contrasts

Sibling-level contrasts within each stratum use the same risk-ratio and odds-ratio intervals as the mismatch-risk table.

### BW quality × scaling direction :: columns=measured_off

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_ok vs upscale | 51.72% (15:14) | 57.14% (12:9) | 0.91 (0.54 to 1.55) | 0.80 (0.23 to 2.56) |
| class_ok vs downscale | 51.72% (15:14) | 54.55% (18:15) | 0.95 (0.58 to 1.52) | 0.89 (0.31 to 2.56) |
| upscale vs downscale | 57.14% (12:9) | 54.55% (18:15) | 1.05 (0.62 to 1.68) | 1.11 (0.36 to 3.58) |

### BW quality × scaling direction :: columns=measured_ok

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_ok vs upscale | 0.33% (20:6073) | 24.25% (236:737) | 0.01 (0.01 to 0.02) | 0.01 (0.01 to 0.02) |
| class_ok vs downscale | 0.33% (20:6073) | 12.82% (196:1333) | 0.03 (0.02 to 0.04) | 0.02 (0.01 to 0.04) |
| upscale vs downscale | 24.25% (236:737) | 12.82% (196:1333) | 1.89 (1.59 to 2.25) | 2.18 (1.76 to 2.70) |

### BW quality × scaling direction :: rows=class_ok

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| measured_ok vs measured_off | 0.33% (20:6073) | 51.72% (15:14) | 0.01 (0.00 to 0.01) | 0.00 (0.00 to 0.01) |

### BW quality × scaling direction :: rows=downscale

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| measured_ok vs measured_off | 12.82% (196:1333) | 54.55% (18:15) | 0.24 (0.18 to 0.34) | 0.12 (0.06 to 0.25) |

### BW quality × scaling direction :: rows=upscale

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| measured_ok vs measured_off | 24.25% (236:737) | 57.14% (12:9) | 0.42 (0.31 to 0.67) | 0.24 (0.10 to 0.60) |

### Class decision × BW measurement :: columns=bw_neutral

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_workable vs class_unworkable | 2.16% (178:8055) | 75.69% (274:88) | 0.03 (0.02 to 0.03) | 0.01 (0.01 to 0.01) |

### Class decision × BW measurement :: columns=bw_shifts

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_workable vs class_unworkable | 60.61% (40:26) | 29.41% (5:12) | 2.06 (1.09 to 4.65) | 3.69 (1.06 to 11.90) |

### Class decision × BW measurement :: rows=class_unworkable

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| bw_neutral vs bw_shifts | 75.69% (274:88) | 29.41% (5:12) | 2.57 (1.42 to 5.71) | 7.47 (2.60 to 22.46) |

### Class decision × BW measurement :: rows=class_workable

| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| bw_neutral vs bw_shifts | 2.16% (178:8055) | 60.61% (40:26) | 0.04 (0.03 to 0.05) | 0.01 (0.01 to 0.02) |

## Attributable burden

Per baselined factorial crossing, rows are ranked by recoverable mismatches relative to the declared baseline cell.

### BW quality × scaling direction

Baseline cell: `class_ok & measured_ok`

| Rank | Cell | n | Mismatch rate | Baseline rate | Recoverable mismatches | Share of all mismatches | Risk difference (95% CI) | Accuracy if eliminated (accumulating) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | upscale & measured_ok | 973 | 24.25% | 0.33% | 232.81 | 46.84% | 0.239 (0.213 to 0.267) | 96.96% |
| 2 | downscale & measured_ok | 1529 | 12.82% | 0.33% | 190.98 | 38.43% | 0.125 (0.109 to 0.143) | 99.16% |
| 3 | downscale & measured_off | 33 | 54.55% | 0.33% | 17.89 | 3.60% | 0.542 (0.377 to 0.698) | 99.36% |
| 4 | class_ok & measured_off | 29 | 51.72% | 0.33% | 14.90 | 3.00% | 0.514 (0.341 to 0.683) | 99.53% |
| 5 | upscale & measured_off | 21 | 57.14% | 0.33% | 11.93 | 2.40% | 0.568 (0.362 to 0.752) | 99.67% |

Counterfactual caveat: recoverable mismatches assume rows in a fixed regime revert to the baseline mismatch rate.

Observed accuracy: 94.27% | Ceiling accuracy after ranked eliminations: 99.67% | Total observed mismatches: 497

### Class decision × BW measurement

Baseline cell: `class_workable & bw_neutral`

| Rank | Cell | n | Mismatch rate | Baseline rate | Recoverable mismatches | Share of all mismatches | Risk difference (95% CI) | Accuracy if eliminated (accumulating) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | class_unworkable & bw_neutral | 362 | 75.69% | 2.16% | 266.17 | 53.56% | 0.735 (0.688 to 0.777) | 97.34% |
| 2 | class_workable & bw_shifts | 66 | 60.61% | 2.16% | 38.57 | 7.76% | 0.584 (0.464 to 0.693) | 97.78% |
| 3 | class_unworkable & bw_shifts | 17 | 29.41% | 2.16% | 4.63 | 0.93% | 0.272 (0.111 to 0.510) | 97.84% |

Counterfactual caveat: recoverable mismatches assume rows in a fixed regime revert to the baseline mismatch rate.

Observed accuracy: 94.27% | Ceiling accuracy after ranked eliminations: 97.84% | Total observed mismatches: 497

Rows: 8678
Mean observed contribution: 0.057271

---
**References**
Shapley values: Shapley (1953) *A value for n-person games*, Princeton UP; Lundberg & Lee (2017) *A unified approach to interpreting model predictions*, NeurIPS 30. Explicit per-feature baselines: Sundararajan & Najmi (2020) *The many Shapley values for model explanation*, ICML, PMLR 119:9269-9278.
Grouped players (Shapley over the quotient game): Aumann & Drèze (1974) *Cooperative games with coalition structures*, Int. J. Game Theory 3(4):217-237; Owen (1977) *Values of games with a priori unions*, in Henn & Moeschlin (eds.), 76-88; Jullum, Redelmeier & Aas (2021) *groupShapley*, arXiv:2106.12228.
Risk ratio CI: Koopman (1984) *Biometrics* 40(2):513-517. Odds ratio CI: Baptista & Pike (1977) *J. Roy. Statist. Soc. C* 26(2):214-220. Small-sample recommendation: Fagerland, Lydersen & Laake (2015, 2017).
Risk difference CI: Miettinen & Nurminen (1985) *Statistics in Medicine* 4(2):213-226. Guardrail: Agresti & Caffo (2000) *Amer. Statist.* 54(4):280-288.