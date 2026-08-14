# Tasks: Inline Factorial Axes

## 1. Schema and loader

- [x] 1.1 Reshape `FactorialCrossing` in `src/contribution/spec.py`: `rows: dict[str, str]`, `columns: dict[str, str]`, `label: str | None = None`; delete `Factor` and `AttributionSpec.factors`; update module exports in `src/contribution/__init__.py`
- [x] 1.2 Rewrite factorial parsing in `_load_spec` (`src/contribution/cli.py`): parse inline `rows`/`columns` level maps with per-level non-empty-string validation, optional non-empty `label`, reject unknown crossing keys and empty axes; delete `factors` parsing
- [x] 1.3 Update `Estimator._validate_spec` (`src/contribution/estimator.py`): validate levels on the crossing itself; remove unknown-axis error and unused-factor warning

## 2. Expansion and results

- [x] 2.1 Update `_expand_factorials` to read level maps from the crossing; replace `_FactorialPlan.rows_axis`/`columns_axis` with the effective label (declared or `Factorial <n>` fallback) and axis-role handling
- [x] 2.2 Emit partition warnings identified by `"<effective label>: rows"` / `"<effective label>: columns"` in warning text and `PartitionWarning.axis`
- [x] 2.3 Reshape `FactorialMatrixResult` (`src/contribution/results.py`) to carry `label` instead of `rows_axis`/`columns_axis`; render matrix header as `### <label>`
- [x] 2.4 Set `ContrastResult.factorial` to the effective label and `ContrastResult.stratum` to `rows=<level>` / `columns=<level>`; render contrast headers as `### <label> :: <stratum>`
- [x] 2.5 Update `_result_from_run` in `cli.py` to rebuild factorial matrices from the `label` payload for `contrib report` regeneration

## 3. Tests

- [x] 3.1 Update `tests/unit/test_spec.py` for the reshaped `FactorialCrossing` and removed `Factor`/`factors`
- [x] 3.2 Update `tests/unit/test_cli.py`: inline-axes loading, label parsing, empty-axis rejection, unknown-key rejection, positional fallback label; remove unknown-axis-reference test
- [x] 3.3 Update `tests/unit/test_estimator.py`: expansion from inline crossings, partition warning identity strings, matrix/contrast label plumbing, cell-name collision still rejected
- [x] 3.4 Update `tests/smoke/test_api_smoke.py` and verify factor-free configs remain byte-stable (report and run.json unchanged)
- [x] 3.5 Run the ResearchData integration tests that consume factorial payloads (`tests/test_error_attribution_kit_integration.py`, `tests/integration/test_contribution_baseline_accuracy.py`) and update fixtures if payload shape assertions exist

## 4. Examples and docs

- [x] 4.1 Migrate `examples/continuous_lora/config_factorial.json` to inline axes with a `label`; reconcile with `examples/continuous_lora/idea.json` (decide which file is canonical per design open question)
- [x] 4.2 Update README schema documentation: replace the `factors` + axis-reference section with the inline crossing shape and `label` semantics
- [x] 4.3 Regenerate factorial run outputs under `build/` used for comparison and spot-check the new report headers end-to-end via `contrib validate` + `contrib run`
