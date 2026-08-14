## 1. Carry spec inputs into metadata

- [x] 1.1 In `estimator.py`, extend the `metadata` dict built in `assess()` to include `target_expr`, `prediction_expr`, `mismatch_expr`, and `score_mode` from `self.spec`.
- [x] 1.2 Verify the new metadata keys appear in `run.json` after a `contrib run`.

## 2. Accessible markdown rendering

- [x] 2.1 In `results.py`, add a title heading and a one-line plain-language description above the Shapley, regime, and mismatch-risk tables in `to_markdown()`.
- [x] 2.2 Add an inputs section that renders the prediction-versus-target formula and echoes `prediction_expr`, `target_expr`, and `mismatch_expr` from `metadata`, omitting any line whose key is absent.
- [x] 2.3 Add a raw-field-to-human-label column mapping and render Shapley columns as "Mean absolute", "Mean signed", "Total signed", and a net-share percentage column.
- [x] 2.4 Render regime columns with human-readable labels (mean contribution, total contribution, share percentage) while keeping counts and names.
- [x] 2.5 Add a one-sentence descriptive conclusion below each table (top feature by net share, largest-share regime, highest-risk-ratio condition).
- [x] 2.6 Preserve the `risk ratio (95% CI)` / `odds ratio (95% CI)` labels, `value (low to high)` formatting, and the existing reference footnotes.

## 3. CLI report parity

- [x] 3.1 Update the `report` command in `cli.py` to regenerate the accessible layout from `run.json` using the same rendering as `to_markdown()` (reconstruct an `AssessmentResult` or call shared rendering helpers).
- [x] 3.2 Confirm `contrib report` output matches the `report.md` written by `contrib run` for the same run.

## 4. Validation

- [x] 4.1 Update any existing tests that assert raw column headers or exact report text to match the new accessible layout.
- [x] 4.2 Add/extend a test asserting section titles, echoed inputs, human-readable Shapley columns, and per-table conclusions in `to_markdown()`.
- [x] 4.3 Add a test asserting `to_csv()` / `to_json()` retain the original raw field names.
- [x] 4.4 Run the contribution-kit test suite (method-level selectors) and regenerate the continuous_lora example report to visually confirm the new layout.

## 5. Framework split: observed prediction vs Shapley formula

- [x] 5.1 Replace `AttributionSpec` inputs with non-backward-compatible `target`, `prediction`, and `prediction_expr`; remove `mismatch_expr` from the attribution schema and config loader.
- [x] 5.2 Update estimator internals so regimes/risk use observed `prediction` vs `target`, while Shapley decomposition continues to use `prediction_expr`.
- [x] 5.3 Derive mismatch risk automatically from `prediction != target` in estimator code.
- [x] 5.4 Update report rendering copy and input echoes so regimes/risk describe observed `prediction`/`target`, and Shapley describes `prediction_expr`.
- [x] 5.5 Migrate bundled example configs to the new keys (`target`, `prediction`, `prediction_expr`) and remove explicit `mismatch_expr`.
- [x] 5.6 Update unit/smoke tests and README examples to the new framework contract.
