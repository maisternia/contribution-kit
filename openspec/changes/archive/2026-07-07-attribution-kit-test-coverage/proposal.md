## Why

The `contribution` package (in `external/contribution-kit/`) computes the statistics we
report in the paper — Shapley feature attributions, contribution-regime shares, and 2x2
mismatch effect sizes (risk ratio / odds ratio with Koopman, Baptista–Pike, Katz, and
Haldane–Anscombe confidence intervals). Its current suite mixes unit-ish and end-to-end
tests, has no coverage gate, and never validates our numeric outputs against an
independent statistical reference. Two gaps therefore threaten reproducibility: (1) code
paths (e.g. sampled-Shapley, CLI subcommands, CI edge cases) execute in production but are
never intentionally exercised, and (2) the numbers we publish are self-referential — they
are only checked against previously-captured snapshots of our own code, not against an
established package such as R.

## What Changes

- **Add a 100% line-and-branch unit-test layer** for every module in
  `contribution` (`stats`, `expr`, `spec`, `hypothesis`, `estimator`, `results`,
  `contributor`, `cli`, `__init__`). Each unit is tested in isolation, with dependencies
  controlled (fixtures / small hand-built tables / fakes) so every covered line is reached
  deliberately — not incidentally through an end-to-end run. Use minimal synthetic inputs
  chosen for path coverage, not realism.
- **Add coverage tooling and a hard gate**: configure `pytest` + `coverage`
  (`[tool.coverage]` / `[tool.pytest.ini_options]` in `pyproject.toml`) with
  `--cov=contribution --cov-branch --cov-fail-under=100` scoped to the unit layer, plus a
  documented command to run it.
- **Add an accuracy-focused integration layer** that validates our reported statistics
  against independently-computed **reference baselines** (generated with R, e.g.
  `epitools`/`exact2x2`/`DescTools` for effect sizes and CIs; a reference Shapley/regime
  computation for attributions). Baselines are committed as data files with the R script
  that produced them; integration tests assert our outputs match within a documented
  numeric tolerance. Coverage is explicitly *not* a goal here — correctness is.
- **Add integration sample data as needed**: keep using the existing
  `sobel_combined_measurements.csv`-derived data, and add purpose-built small tables
  (sparse cells, zero cells, boundary support, single-group regimes) so the baseline
  comparison spans the numeric edge cases the CI methods must handle.
- **Reorganize the test tree** so that the **unit layer lives inside the submodule**
  (`external/contribution-kit/tests/unit/`) with the coverage gate, while the
  **integration/accuracy layer lives in the parent repo** (`ResearchData/tests/integration/`
  with baselines under `ResearchData/tests/reference/`). Unit and integration tests never
  share a directory or repository.

No production/source behavior of `contribution` changes; this is a test-and-tooling change.
The only non-test edits are additive tooling config in `pyproject.toml` (and, if a genuine
defect is uncovered while writing baselines, a separately-called-out fix).

## Capabilities

### New Capabilities
- `attribution-kit-unit-coverage`: Isolated unit tests achieving 100% line and branch
  coverage of every `contribution` module, with a coverage gate wired into the project's
  test tooling. Defines what "unit isolation" means here and which code paths must be
  intentionally covered.
- `attribution-kit-statistical-baselines`: Accuracy-focused integration tests that
  compare the kit's reported statistics against independently-generated reference baselines
  (R for effect sizes/CIs; reference computation for Shapley/regime shares), including the
  baseline data artifacts, the generating scripts, and the numeric-tolerance contract.

### Modified Capabilities
- (none — no existing OpenSpec spec's requirements change; `estimator-hypothesis-attribution`
  behavior is unaffected.)

## Impact

- **Affected code**: `external/contribution-kit/` — new `tests/unit/` tree and additive
  `pyproject.toml` tooling config (no changes to `src/contribution/*.py` unless a defect is
  found, called out separately); `ResearchData/tests/` — new `integration/` and `reference/`
  trees (baseline data + generator scripts).
- **Repo integration**: `tests/test_error_attribution_kit_integration.py` in the parent
  ResearchData repo continues to exercise the kit against the shared measurement CSV and
  must keep passing.
- **Dependencies**: adds dev/test tooling (`pytest`, `coverage`/`pytest-cov`) and a
  documented, offline R workflow to (re)generate baselines; committed baseline artifacts
  mean R is not required to run the test suite.
- **Submodule/versioning**: `contribution-kit` is a git submodule; test additions land on
  the change branch inside the submodule and the parent records the updated pointer.
