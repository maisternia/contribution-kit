## Why

Prefix-level contribution runs in infer now use a shared config that can be factorial-focused. The current estimator validator rejects configs with empty regimes, which blocks legitimate factorial-only analyses and forces users to add placeholder regimes that they do not want.

## What Changes

- Allow contribution-kit attribution specs to run when regimes are empty, as long as at least one factorial crossing is declared.
- Keep existing validation strictness for truly incomplete specs by continuing to reject configs that define neither regimes nor factorials.
- Preserve report/output behavior so factorial analyses render normally without requiring synthetic regime rows.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- estimator-hypothesis-attribution: Relax spec validation policy so regime declarations are optional when factorial declarations are present.
- factorial-regime-declaration: Clarify factorial-only execution semantics and expected outputs when no caller-authored regimes exist.

## Impact

- Affected code: contribution-kit estimator validation and related tests.
- Affected behavior: factorial-only configs become valid inputs for validate/run flows.
- Backward compatibility: existing configs with regimes remain unchanged; empty-regime + no-factorial configs remain invalid.
