## Context

`contribution` (in `external/contribution-kit/`, a git submodule) is a dependency-free
Python package computing the statistics we publish:

- **Effect sizes / CIs** (`stats.py`): `katz_risk_ratio`, `haldane_anscombe_odds_ratio`,
  `koopman_risk_ratio` (asymptotic-score RR CI), `baptista_pike_odds_ratio` (exact OR CI),
  plus private root-finding/tail-probability helpers (`_bisect_root`,
  `_invert_monotone_tail`, `_tail_probability`, `_rr_score_statistic`, …).
- **Expression DSL** (`expr.py`): a whitelisted-AST evaluator (`compile_expression`,
  `evaluate_expression`, `split_equality`, `build_row_context`).
- **Attribution engine** (`estimator.py`): Shapley feature attribution (exact +
  Monte-Carlo `_sample_shapley`), regime shares, mismatch-risk routing.
- **Hypothesis / results / contributor / cli / spec** supporting modules.

Current tests (`tests/test_*.py`) are a flat mix of unit-ish and end-to-end checks against
committed fixtures, with **no coverage gate** and **no independent numeric validation** —
outputs are only compared to earlier snapshots of our own code. The parent repo's
`tests/test_error_attribution_kit_integration.py` further pins kit outputs to the shared
`sobel_combined_measurements.csv`.

Constraints: package must stay runtime-dependency-free (test/dev tooling only); the test
suite must run **offline** (R not required at test time); `src/contribution/*.py` behavior
must not change except for a separately-flagged fix if a real defect surfaces.

## Goals / Non-Goals

**Goals:**
- 100% line **and** branch coverage of every `contribution` module from an isolated unit
  layer where each covered line is reached deliberately.
- A hard coverage gate (`--cov-fail-under=100`, branch on) wired into project tooling,
  scoped to the unit layer.
- An accuracy-focused integration layer validating our reported statistics against
  **independently generated reference baselines** (R for effect sizes/CIs; an independent
  brute-force reference for Shapley/regime), within a documented numeric tolerance.
- Committed baseline artifacts + their generating scripts, so the suite runs without R.
- A test tree that lets the two workstreams proceed independently (parallel subagents),
  with a clear placement boundary: **unit tests live inside the submodule
  (`external/contribution-kit/tests/`) and integration tests live in the parent repo
  (`ResearchData/tests/`).**

**Non-Goals:**
- Changing any `contribution` production behavior or public API.
- Achieving coverage from the integration layer (its purpose is accuracy, not coverage).
- Requiring R (or network) to *run* the tests; R is only needed to *regenerate* baselines.
- Reworking the parent-repo integration test beyond keeping it green.

## Decisions

### D1 — Unit tests in the submodule, integration tests in the parent repo
Placement boundary (**required**):
- **Unit layer** lives *inside the submodule* at
  `external/contribution-kit/tests/unit/` — one `test_<module>.py` per source module. This
  keeps the kit self-testing and self-contained (it ships with its own 100%-covered unit
  suite and coverage gate).
- **Integration layer** lives *in the parent repo* at `ResearchData/tests/integration/`,
  alongside the existing `tests/test_error_attribution_kit_integration.py`, with committed
  reference baselines under `ResearchData/tests/reference/` (baseline data + `*.R`/generator
  scripts). Integration tests import the installed/`sys.path`-added kit and compare its
  outputs to the baselines.

The coverage gate targets **only** the submodule unit layer, so parent-repo integration
runs never inflate/deflate the "every line intentional" guarantee.
*Alternative rejected:* keep one flat `tests/` or co-locate integration tests in the
submodule — violates the required boundary and blurs unit vs. integration intent.

### D2 — Coverage tooling via `pytest` + `coverage`, configured in `pyproject.toml`
Add `[tool.pytest.ini_options]` and `[tool.coverage.run]`/`[report]` sections; declare
`pytest`, `coverage`/`pytest-cov` under an optional `[project.optional-dependencies].test`
group (keeps the package's runtime deps empty). Unit run:
`pytest tests/unit --cov=contribution --cov-branch --cov-fail-under=100`. Use
`# pragma: no cover` only for the `if __name__ == "__main__"` guard and other genuinely
unreachable lines, each justified. *Alternative rejected:* a separate `coverage`-only
config file — `pyproject.toml` keeps config discoverable and canonical.

### D3 — Definition of "unit isolation" for this package
Each unit is exercised through its own public surface with controlled, minimal inputs:
- Pure math/DSL units (`stats`, `expr`, `spec`, `contributor`, `hypothesis`) get
  hand-built tables/contexts chosen purely for path coverage (each branch, each
  `raise`, each zero/sparse/boundary cell, each `ci_method`, exact vs. sampled Shapley).
- I/O units (`Estimator.from_csv`, `results.to_csv/to_json/save`, `cli.main`) use
  `tmp_path` and tiny in-memory inputs; no reliance on the real fixtures or the parent
  CSV. Private helpers are covered via the public callers that reach them; a helper only
  reachable through an impractical public path is tested directly and noted.
*Alternative rejected:* driving coverage through end-to-end `assess()` runs — that reaches
lines incidentally rather than intentionally, defeating the purpose.

### D4 — Reference baselines from established packages, per statistic
Map each reported quantity to an independent authority and record the exact
package/function/version in the generator script:
- Katz RR + log CI → `epitools`/`fmsb` (Wald log RR).
- Haldane–Anscombe OR + CI → `DescTools::OddsRatio` / `epitools` (0.5-corrected Wald).
- Koopman score RR CI → `PropCIs::riskscoreci` (Koopman/Nam score interval).
- Baptista–Pike exact OR CI → `exact2x2` (Baptista–Pike method).
- Shapley feature shares + regime shares → an **independent brute-force reference**
  (separate small implementation, not the kit's code) since these are not "off-the-shelf"
  R routines; documented as such.
Baselines are emitted as CSV/JSON into `ResearchData/tests/reference/` (parent repo)
alongside the `*.R`/generator and a README noting package versions. *Alternative rejected:*
re-deriving CIs by hand in the test — that just re-implements the kit and isn't independent.

### D5 — Explicit numeric-tolerance contract
Integration tests assert closeness with documented tolerances per statistic (e.g. tight
`abs_tol`/`rel_tol` for point estimates; slightly looser for iterative score/exact CIs
whose root-finding differs from R's). Tolerances live next to the assertions with a one-line
rationale, and infinite/zero/`None` CI cases are asserted structurally (not numerically).

### D6 — Purpose-built integration edge-case tables
Beyond the existing `sobel`-derived data, add small committed tables spanning: sparse
cells, single/double zero cells, boundary support (`lower_support == upper_support`),
single-group regimes (risk returns `None`), and `ci_method in {score-exact, wald}` — so the
baseline comparison covers the numeric corners the CI methods must handle.

### D7 — Independent, parallelizable workstreams
The unit-coverage capability and the statistical-baselines capability share no files and
live in **different repositories**: unit tests + coverage tooling in the submodule
(`external/contribution-kit/`), integration tests + baselines in the parent
(`ResearchData/tests/`). Implementation can fan out to two parallel subagents with no
serialization point — the only shared edit (`pyproject.toml`) belongs entirely to the
unit-coverage stream inside the submodule.

## Risks / Trade-offs

- **[R method name ≠ our method name]** e.g. "Koopman" vs. "Nam score", or exact2x2's
  Baptista–Pike parameterization → Mitigation: pin the exact R function + version in the
  generator, and cross-check one worked example against the published formula/paper cited
  in `stats.py` docstrings before trusting the baseline.
- **[Root-finder disagreement inflates CI diffs]** our bisection tolerances differ from R's
  → Mitigation: per-CI tolerance in D5; if a gap exceeds tolerance, treat as a finding and
  investigate rather than loosening blindly.
- **[100% gate becomes brittle]** unreachable defensive branches force awkward tests →
  Mitigation: justified `# pragma: no cover` for truly dead/guard lines; prefer refactor-free
  targeted tests otherwise (no source behavior change).
- **[Shapley has no off-the-shelf R baseline]** → Mitigation: independent brute-force
  reference (D4), explicitly documented as second-implementation cross-validation, not an
  external authority.
- **[Submodule/pointer drift]** unit-test work lands in the submodule while integration
  work lands in the parent repo → Mitigation: commit the unit suite + tooling inside the
  submodule on the change branch first, record the updated parent pointer, then commit the
  parent-repo integration tests/baselines; follow the OpenSpec git branch policy.

## Migration Plan

Additive and reversible — no production code path changes. Steps: (1) add tooling config to
the submodule `pyproject.toml`; (2) introduce `external/contribution-kit/tests/unit/` and
migrate/replace the kit's existing flat tests; (3) add `ResearchData/tests/integration/` and
`ResearchData/tests/reference/`, generate + commit baselines; (4) wire the unit coverage
gate into the documented test command / CI. Rollback = revert the test-tree and
`pyproject.toml` additions; source is untouched.

## Open Questions

- Do we adopt `pytest-cov` or invoke `coverage run -m pytest` directly? (Leaning
  `pytest-cov` for the inline `--cov-fail-under`.)
- Resolved: the parent-repo `tests/test_error_attribution_kit_integration.py` **stays in
  the parent** and new integration/accuracy tests join it under `ResearchData/tests/`;
  integration tests are never placed in the submodule.
- Exact R package pinning for Baptista–Pike (`exact2x2` method flag) and Koopman
  (`PropCIs::riskscoreci`) — confirm on the baseline-generation machine.
