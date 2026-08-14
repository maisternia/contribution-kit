## 1. Preflight (shared)

- [x] 1.1 Confirm work is on branch `opsx/change/attribution-kit-test-coverage`; ensure the `external/contribution-kit` submodule is on its own change branch off its trunk before editing inside it.
- [x] 1.2 Establish a baseline coverage reading for `contribution` (`coverage run -m pytest` over the current suite) and record the starting line/branch percentages so the gap to 100% is known.
- [x] 1.3 Note the two workstreams are independent (Section 2 in the submodule, Section 3 in the parent repo) and may be run by parallel subagents; the only shared file is the submodule `pyproject.toml` (owned by Section 2).

## 2. Workstream A — Unit coverage in the submodule

- [x] 2.1 Add test tooling to `external/contribution-kit/pyproject.toml`: declare `pytest` and `coverage`/`pytest-cov` under `[project.optional-dependencies].test`, keep runtime `dependencies` empty, and add `[tool.pytest.ini_options]` + `[tool.coverage.run]`/`[tool.coverage.report]` (branch = true, source = `contribution`, `fail_under = 100`).
- [x] 2.2 Create the `external/contribution-kit/tests/unit/` tree (with the `sys.path` shim from the existing `conftest.py`) and decide the migration/replacement of the existing flat `tests/test_*.py` into the unit layer.
- [x] 2.3 `tests/unit/test_stats.py` — cover `stats.py` fully: `_validate_2x2_counts` raises (negative, empty exposed, empty baseline); `katz_risk_ratio` (normal, zero-baseline `inf`/None CI, any-zero-cell None CI); `haldane_anscombe_odds_ratio`; `koopman_risk_ratio` and `baptista_pike_odds_ratio` across point-estimate == 0, `inf`, finite, and collapsed-support branches; and the private helpers (`_bisect_root` root/bracket paths, `_invert_monotone_tail` increasing/decreasing + limit hits, `_tail_probability` lower/upper/`theta<=0`/`theta=inf`/invalid tail, `_rr_score_statistic` ratio==1 / ratio!=0 / ratio<=0 raise) reached deliberately.
- [x] 2.4 `tests/unit/test_expr.py` — cover `expr.py` fully: every allowed AST node in `_validate_node` and `_eval_node` (BinOp ops incl. FloorDiv/Mod/Pow, UnaryOp incl. Not, BoolOp And/Or, all Compare ops, Call incl. `col()` arity error, IfExp, Tuple/List), each `raise` (unsupported function, unsupported node, non-Name call, unknown variable), `split_equality` (equality vs. non-equality → None), and `build_row_context` with/without `extra`.
- [x] 2.5 `tests/unit/test_spec.py` — cover `spec.py`: `Hypothesis` and `AttributionSpec` construction incl. defaults (`label` None, `mismatch_expr` None, `scope`, `score_mode`).
- [x] 2.6 `tests/unit/test_hypothesis.py` — cover `hypothesis.py`: `_raw_risk_ratio`/`_raw_odds_ratio` zero-denominator branches, `evaluate_binary_hypothesis` for both `ci_method` values and the invalid-method raise, and `evaluate_binary_hypotheses` including the empty-group skip path.
- [x] 2.7 `tests/unit/test_estimator.py` — cover `estimator.py`: `_parse_scalar` (empty→None, bool, int, float, string, int-parse fallback), `from_csv`/`from_dataframe` (df-with-`to_dict`, sequence, unsupported→TypeError), `_validate_spec` raises (no spec, no hypotheses, duplicate names), `_score` signed vs. absolute, exact vs. sampled Shapley (`_exact_shapley` and `_sample_shapley` via `max_exact_features`), feature vs. regime routing, and the `_regime_risk` `None` paths (no mismatch_fn, single-group).
- [x] 2.8 `tests/unit/test_results.py` — cover `results.py`: `_format_effect_ci` (finite, `inf`, None-bound branches), `feature_attributions` sorting, `regime_summaries`/`binary_results` filters, `to_markdown` with and without regimes/risks, and `to_csv`/`to_json`/`save` using `tmp_path` (including the empty-records fieldnames fallback).
- [x] 2.9 `tests/unit/test_contributor.py` — cover `contributor.py`: `rank_contributors` (min_count filter, zero global mismatch-rate branch, sorting) and `combine_contributors` merge/sort.
- [x] 2.10 `tests/unit/test_cli.py` — cover `cli.py`: `build_parser`, `_load_spec` (JSON and YAML branches), `_load_rows`, and `main` for every subcommand (`init-config`, `validate`, `run`, `report`, `contributor` incl. the `:`-missing raise, `hypothesis`) plus the `__main__` guard via `# pragma: no cover`, all using `tmp_path`.
- [x] 2.11 `tests/unit/test_init.py` — cover `__init__.py` public re-exports (import each name in `__all__`).
- [x] 2.12 Run `pytest tests/unit --cov=contribution --cov-branch --cov-fail-under=100`; if any line/branch is missed, add a targeted test (or a justified `# pragma: no cover` for genuinely unreachable/guard lines) until the gate passes at 100%.
- [x] 2.13 If a genuine defect in `contribution` source is uncovered while testing, stop and surface it as a separately-described fix (do not bundle silently); otherwise confirm no source behavior changed.

## 3. Workstream B — Statistical baselines in the parent repo

- [x] 3.1 Create `ResearchData/tests/integration/` and `ResearchData/tests/reference/` (baseline data + generator scripts).
- [x] 3.2 Assemble integration input tables under `tests/reference/`: reuse the existing `sobel_combined_measurements.csv`-derived data and add purpose-built small tables spanning sparse cells, single/double zero cells, boundary support (collapsed exact interval), single-group regimes (undefined risk), and both `ci_method` values.
- [x] 3.3 Write the R generator script(s) in `tests/reference/` producing effect-size + CI baselines, pinning exact package/function/version: Katz RR (`epitools`/`fmsb`), Haldane–Anscombe OR (`DescTools`/`epitools`), Koopman score RR CI (`PropCIs::riskscoreci`), Baptista–Pike exact OR CI (`exact2x2`); cross-check one worked example against the paper formula cited in `stats.py`.
- [x] 3.4 Write an independent brute-force reference (separate from the kit's code) for the Shapley feature shares and regime-contribution shares; emit as committed CSV/JSON with a README noting method + versions.
- [x] 3.5 Commit all generated baselines (CSV/JSON) alongside their generator scripts so the integration suite runs offline (no R, no network) at test time.
- [x] 3.6 `tests/integration/` effect-size accuracy tests: compare kit `koopman_risk_ratio`, `baptista_pike_odds_ratio`, `katz_risk_ratio`, `haldane_anscombe_odds_ratio` (point + CI, both `ci_method` paths) to the committed baselines within a documented per-statistic tolerance; assert infinite/zero/None CI bounds structurally.
- [x] 3.7 `tests/integration/` attribution accuracy tests: compare kit feature-attribution and regime-contribution shares to the independent brute-force reference within a documented tolerance.
- [x] 3.8 Document the tolerance contract inline next to each assertion (one-line rationale per statistic), tightest for point estimates and looser where iterative score/exact CI root-finding legitimately differs from R.
- [x] 3.9 Confirm the existing `ResearchData/tests/test_error_attribution_kit_integration.py` still passes unchanged.

## 4. Verification & finalization

- [x] 4.1 Run the submodule unit gate (`pytest tests/unit --cov=contribution --cov-branch --cov-fail-under=100`) and confirm 100% line + branch, exit 0.
- [x] 4.2 Run the parent-repo integration suite (`tests/integration` + existing kit integration test) offline and confirm all pass.
- [x] 4.3 Verify placement invariants: no unit tests under `ResearchData/tests/`, no integration tests inside `external/contribution-kit/`.
- [x] 4.4 Update the submodule README test section (and any parent `AGENTS.md`/docs) with the documented unit-gate command and the baseline-regeneration command.
- [x] 4.5 Commit unit-suite + tooling inside the submodule on its change branch, record the updated submodule pointer in the parent, then commit the parent-repo integration tests/baselines — per the OpenSpec git branch policy.
