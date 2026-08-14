## Why

Current default mismatch-risk reporting can emit open-ended risk-ratio confidence intervals such as `to inf` for finite point estimates in sparse but valid 2x2 tables. This weakens interpretability in paper-facing outputs and creates avoidable instability in downstream reporting.

We need a paper-grounded, source-independent fix that preserves Koopman and Baptista-Pike as defaults while ensuring finite, ordered intervals are reported whenever a finite interval is expected.

## What Changes

- Add a robustness guardrail to default score/exact interval computation so sparse-table numerical pathologies do not surface as infinite or invalid CI bounds for finite point estimates.
- Keep default methods unchanged in intent (Koopman RR CI, Baptista-Pike OR CI), but apply paper-cited fallback methods (Katz RR CI, Haldane-Anscombe OR CI) only when the primary inversion output is non-finite or unordered.
- Validate CI method inputs consistently by rejecting non-finite or non-positive z values across all four interval implementations.
- Add targeted regression coverage for known sparse finite-point cases that previously produced `to inf` in report rows.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `estimator-hypothesis-attribution`: tighten mismatch-risk CI behavior so finite-point default outputs avoid non-finite bounds due to numerical inversion instability, with explicit fallback semantics and input validation expectations.

## Impact

- Affected code: `external/contribution-kit/src/contribution/stats.py` and related hypothesis/report call paths.
- Affected tests: `external/contribution-kit/tests/unit/test_stats.py`.
- User-visible impact: markdown and JSON reports for sparse regimes will no longer show `to inf` in finite-point RR CI rows when fallback applies.
- API compatibility: no public API break; method names and defaults remain unchanged.
- Dependencies/licensing: no new external dependency and no source-copied implementation required.
