## 1. Fix

- [x] 1.1 In `_build_burden_rankings` (`src/contribution/estimator.py`), skip zero-row non-baseline cells instead of computing their risk difference, and collect their names in declaration order
- [x] 1.2 Exclude empty cells from the baseline-sanity rate comparison
- [x] 1.3 Add `empty_cells: list[str]` to `BurdenRankingResult` (`src/contribution/results.py`) and fill it, including on overlap-suppressed rankings
- [x] 1.4 Render a note listing the empty cells under the burden table in `to_markdown`
- [x] 1.5 Round-trip `empty_cells` in `_result_from_payload` (`src/contribution/cli.py`), defaulting to an empty list

## 2. Tests

- [x] 2.1 Estimator test: a baselined crossing with an empty non-baseline cell completes, ranks only the non-empty cells, and records the empty one
- [x] 2.2 Estimator test: an empty cell does not trigger the baseline-sanity warning
- [x] 2.3 Report test: the empty-cell note renders, and is absent when there are no empty cells
- [x] 2.4 Run the full suite

## 3. Example

- [x] 3.1 Add `examples/continuous_lora/measurements_standard.csv` (2,382 C18x2 detections on the standard set)
- [x] 3.2 Run the shipped `config.json` on it into `runs/standard/`, and regenerate `runs/c18x2` and `runs/c9x1`, confirming that only the new `empty_cells` field changes there (confirmed: two added lines per run.json)
- [x] 3.3 Mention the standard sample in `README.md` where the bundled measurements are listed

## 4. Release

- [x] 4.1 Bump the package version to 0.3.1 (bug fix with an additive output field)
