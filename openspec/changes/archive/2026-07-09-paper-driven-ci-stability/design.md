## Context

The contribution-kit default mismatch-risk path uses Koopman (risk ratio CI) and Baptista-Pike (odds ratio CI) for small-sample behavior, and exposes Katz/Haldane-Anscombe as an explicit fallback mode. In sparse 2x2 tables with finite point estimates, numerical inversion instability can still produce open-ended CI bounds in default outputs (for example `to inf`), which is hard to interpret in paper-facing reports.

The change must remain paper-driven and source-independent, preserve existing public method names and defaults, and keep behavior stable for non-pathological tables.

## Goals / Non-Goals

**Goals:**
- Ensure default mismatch-risk reporting returns finite, ordered CI bounds for finite point estimates whenever a finite interval is expected.
- Preserve Koopman and Baptista-Pike as the primary default methods.
- Apply Katz/Haldane-Anscombe only as a numerical guardrail when the primary inversion output is non-finite or unordered.
- Add explicit input validation for confidence-level z inputs (finite and positive).
- Add targeted regression tests for sparse finite-point cases.

**Non-Goals:**
- Replacing default score/exact methods with alternative methods globally.
- Introducing dependency on external statistical runtimes or generators.
- Changing risk-ratio or odds-ratio point-estimate formulas.
- Reworking report schema or adding new user-facing CI method flags.

## Decisions

- Decision: Keep score/exact as primary and add guarded automatic fallback.
  Rationale: This preserves current paper method intent while preventing numerically unstable outputs from leaking into reports.
  Alternatives considered:
  - Always switch to Katz/Haldane for all sparse tables: rejected because it weakens the default method contract.
  - Leave open-ended bounds unchanged: rejected because it degrades report quality and comparability for finite-point rows.

- Decision: Trigger fallback only for finite-point estimates with non-finite or unordered CI outputs.
  Rationale: This minimizes behavioral change and applies correction only where the primary inversion fails the output contract.
  Alternatives considered:
  - Trigger on simple cell-count heuristics: rejected because sparse tables can still be well-behaved and should keep primary intervals.

- Decision: Validate z centrally across all CI methods.
  Rationale: Inconsistent z handling creates avoidable runtime ambiguity and edge-case failures.
  Alternatives considered:
  - Validate only in score/exact paths: rejected because fallback and explicit wald path should enforce the same contract.

- Decision: Add regression tests at known failure rows rather than broad fixture rewrites.
  Rationale: Keeps test signal focused, stable, and low-maintenance while covering the concrete bug.

## Risks / Trade-offs

- [Risk] Fallback can produce tighter/wider intervals than prior default outputs in edge cases. → Mitigation: document fallback condition in spec and assert point estimates remain unchanged.
- [Risk] Hidden numerical issues may still exist in untested table regions. → Mitigation: add focused sparse regression tests now and extend with additional edge tables in follow-up if needed.
- [Risk] Users may assume all default intervals are always pure Koopman/Baptista-Pike. → Mitigation: specify guardrail semantics in requirement text and keep fallback constrained to invalid inversion outcomes.
