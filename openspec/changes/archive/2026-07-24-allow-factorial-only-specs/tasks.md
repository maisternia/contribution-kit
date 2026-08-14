## 1. Validation Policy Update

- [x] 1.1 Update estimator spec validation to accept specs when either regimes or factorials are present.
- [x] 1.2 Preserve rejection for specs that declare neither regimes nor factorials, with a clear error message.
- [x] 1.3 Confirm no behavioral changes for existing regime-based specs.

## 2. Factorial-Only Execution Integrity

- [x] 2.1 Verify factorial expansion and downstream matrix/contrast/burden generation run when regimes are empty.
- [x] 2.2 Verify no synthetic placeholder regime is introduced when caller-authored regimes are empty.
- [x] 2.3 Verify mixed specs (regimes + factorials) continue to produce both output families.

## 3. Test Coverage and Verification

- [x] 3.1 Add/adjust tests for validation matrix: regimes-only valid, factorial-only valid, neither invalid.
- [x] 3.2 Add a factorial-only assessment test that asserts factorial outputs are produced with generated cell-regime rows (no placeholders).
- [x] 3.3 Run targeted contribution-kit tests and record pass results for this change.
