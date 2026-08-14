## 1. CI Guardrail Implementation

- [x] 1.1 Add shared interval-validity helper(s) for finite and ordered bound checks in stats utilities.
- [x] 1.2 Add z-input validation helper and enforce it in Koopman, Baptista-Pike, Katz, and Haldane-Anscombe CI entry points.
- [x] 1.3 Update Koopman RR CI path to apply Katz fallback only when finite-point primary output is non-finite or unordered.
- [x] 1.4 Update Baptista-Pike OR CI path to apply Haldane-Anscombe fallback only when finite-point primary output is non-finite or unordered.

## 2. Regression and Contract Tests

- [x] 2.1 Add sparse finite-point regression tests that assert finite ordered RR CI bounds for known problematic tables.
- [x] 2.2 Add tests that confirm invalid z inputs are rejected across all four CI methods.
- [x] 2.3 Add or update assertions that point estimates are unchanged when fallback affects only interval bounds.

## 3. Reporting and Documentation Alignment

- [x] 3.1 Verify markdown mismatch-risk output renders finite `value (low to high)` for affected sparse finite-point rows.
- [x] 3.2 Ensure README fallback documentation remains a single section and still describes explicit fallback selection.
- [x] 3.3 Confirm mismatch-risk references remain Koopman/Baptista-Pike with Fagerland guidance in report footnotes.

## 4. Focused Verification

- [x] 4.1 Run targeted unit tests for sparse CI regression and z-validation paths (method-level selectors only).
- [x] 4.2 Run focused behavior checks for representative default score/exact and explicit fallback (wald) paths.
- [x] 4.3 Generate one representative report artifact and confirm no `to inf` RR CI appears for finite-point affected rows.
