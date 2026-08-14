## Why

The mismatch-risk tables report a risk ratio and odds ratio with 95% confidence
intervals, but the current CI methods — Katz log-transform for the risk ratio and
Haldane-Anscombe continuity correction for the odds ratio — are Wald-type
intervals that under-cover on the small, sparse 2×2 mismatch tables this kit
produces, and the Katz interval collapses to `n/a` on any zero cell. A
peer-reviewed coverage evaluation (Fagerland, Lydersen & Laake 2015; and their
2017 contingency-tables text) recommends the asymptotic-score (Koopman) interval
for the ratio of proportions and the Baptista-Pike interval for the odds ratio as
better-calibrated choices for small samples. Adopting those as the defaults gives
more trustworthy intervals for the sparse tables that dominate this analysis
(these also happen to be GraphPad Prism's default methods).

## What Changes

- Adopt the Koopman asymptotic-score confidence interval as the risk-ratio CI
  method used in all reporting output.
- Adopt the Baptista-Pike exact confidence interval as the odds-ratio CI method
  used in all reporting output.
- Retain the previous Katz and Haldane-Anscombe intervals in the code as opt-in
  fallbacks, reachable only through a single method-selection option and not part
  of the default output.
- Cite Koopman (1984) and Baptista-Pike (1977) in the mismatch-risk footnotes
  (with the small-sample recommendation from Fagerland, Lydersen & Laake
  2015/2017), and mention the opt-in fallbacks exactly once in the README.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `estimator-hypothesis-attribution`: the condition-vs-rest mismatch-risk output
  uses the Koopman (risk ratio) and Baptista-Pike (odds ratio) confidence-interval
  methods, and the reported references change accordingly; the previous methods
  remain in the code as opt-in fallbacks surfaced only through a single option.

## Impact

- `external/contribution-kit/src/contribution/stats.py`: add Koopman risk-ratio CI
  and Baptista-Pike odds-ratio CI functions; keep existing functions.
- `external/contribution-kit/src/contribution/hypothesis.py`: default the binary
  evaluation to the new methods and thread a method-selection option through.
- `external/contribution-kit/src/contribution/results.py`: update reference
  footnotes to cite the Koopman and Baptista-Pike methods.
- `external/contribution-kit/src/contribution/__init__.py`: export the new CI
  functions.
- `external/contribution-kit/README.md`: document the Koopman and Baptista-Pike CI
  methods, with a single mention that the previous methods remain selectable.
- `external/contribution-kit/tests/test_stats.py`: add tests for the new methods.
- No dataset or model artifacts are affected.
