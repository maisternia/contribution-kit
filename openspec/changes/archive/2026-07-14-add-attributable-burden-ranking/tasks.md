# Tasks: add-attributable-burden-ranking

## 1. Schema and config surface

- [x] 1.1 Add optional `baseline` field to the crossing type in `external/contribution-kit/src/contribution/spec.py` with validation that both named levels exist on their axes
- [x] 1.2 Parse the `baseline` key in `external/contribution-kit/src/contribution/cli.py`, extending the allowed crossing keys (`rows`, `columns`, `label`, `baseline`) and erroring clearly on unknown baseline levels
- [x] 1.3 Print a one-line stderr hint from the CLI when a run contains a factorial crossing without a `baseline`, naming the crossing; never write the hint into `report.md` or `run.json`

## 2. Statistics

- [x] 2.1 Implement the Miettinen–Nurminen asymptotic score interval for a difference of two proportions in `external/contribution-kit/src/contribution/stats.py`, with a docstring `Reference:` block citing Miettinen & Nurminen (1985) *Statistics in Medicine* 4(2), 213–226 and inline `@cite:` comments, matching the existing stats.py convention
- [x] 2.2 Implement the Agresti–Caffo interval and the per-result guardrail dispatch (fallback only on non-finite/unordered primary with finite point estimate), with a docstring `Reference:` block citing Agresti & Caffo (2000) *The American Statistician* 54(4), 280–288
- [x] 2.3 Unit-test both intervals against published reference values, including a degenerate table that exercises the fallback

## 3. Burden computation

- [x] 3.1 Compute per non-baseline cell excess mismatches, share of total mismatches, and ranking in `external/contribution-kit/src/contribution/estimator.py`, reusing cell membership masks from the matrix pass; break ties in excess by declaration order (rows axis, then columns axis); raise an error naming the crossing when the baseline cell matches zero rows
- [x] 3.2 Compute the cumulative accuracy-if-eliminated trajectory over the ranking with all dataset rows as the denominator (coverage-gap rows keep observed outcomes); place non-positive-excess cells last as non-recoverable
- [x] 3.3 Implement guards: suppress ranking on overlap partition warnings, note coverage-gap exclusions, emit baseline-sanity warning into result metadata

## 4. Rendering and serialization

- [x] 4.1 Add a burden result type and `burden_rankings` on `AssessmentResult` in `external/contribution-kit/src/contribution/results.py`
- [x] 4.2 Render the "Attributable burden" section per baselined crossing (rank, cell, n, rates, recoverable, share, risk difference CI, cumulative accuracy) plus the fixed counterfactual caveat and any guard notes, following the accessible-reports conventions (plain-language labels, `value (low to high)` CI format)
- [x] 4.3 Serialize `burden_rankings` (baseline cell, entries, guard outcomes) into `run.json`; keep baseline-free output byte-identical
- [x] 4.4 Extend the report references footnote with `Risk difference CI: Miettinen & Nurminen (1985) *Statistics in Medicine* 4(2):213-226. Guardrail: Agresti & Caffo (2000) *Amer. Statist.* 54(4):280-288.` rendered only when a burden table is present, in the same style as the existing Koopman/Baptista-Pike footnote lines

## 5. Example, tests, docs

- [x] 5.1 Declare `baseline` on the crossing in `examples/continuous_lora/config.json` and verify the ranked table matches the manually computed prioritization (~165 then ~78 recoverable on the log-domain measured axis)
- [x] 5.2 Add unit tests for burden math (excess, share, cumulative trajectory, non-positive excess ordering) on a small fixture
- [x] 5.3 Add tests for the guards: overlap suppression, gap exclusion note, baseline-sanity warning, missing-baseline-level config error, empty-baseline-cell assessment error, and deterministic tie-breaking by declaration order
- [x] 5.4 Add a regression test that baseline-free configs produce unchanged `report.md`/`run.json`, and a CLI test that the stderr hint appears for unbaselined crossings and is absent when all crossings are baselined
- [x] 5.5 Document the `baseline` key, burden table semantics, and the counterfactual caveat in `external/contribution-kit/README.md`, adding anchored entries `[Miettinen & Nurminen 1985]` (`ref-miettinen85`) and `[Agresti & Caffo 2000]` (`ref-agresti00`) to the `## References` section and bracketed inline citations where the burden table is described
