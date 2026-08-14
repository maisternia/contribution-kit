## Context

Contribution-kit currently rejects attribution specs that have no caller-authored regimes, even when factorial crossings are present and valid. Infer now supports a shared prefix-level config that can intentionally be factorial-focused, so this guard blocks a legitimate analysis mode and produces runtime warnings in the inference pipeline.

The existing estimator and report stack already supports factorial-generated cell regimes, and factorial sections are independently rendered when present. This means the hard validation requirement is stricter than the downstream execution model.

## Goals / Non-Goals

**Goals:**
- Allow factorial-only configs to pass validation and execute end-to-end.
- Preserve strict validation for underspecified specs by still rejecting configs that define neither regimes nor factorials.
- Keep output structure stable for existing callers that provide regimes.
- Add coverage so factorial-only acceptance does not regress.

**Non-Goals:**
- Redesign the scoring model or regime risk calculations.
- Change config file syntax or rename existing keys.
- Remove regimes from existing examples or enforce factorial usage.

## Decisions

1. Relax validator precondition from "regimes required" to "regimes or factorials required".
- Rationale: this matches real execution behavior where factorial analysis can stand alone.
- Alternative considered: keep strict validator and require placeholder regimes in configs. Rejected because it forces artificial config noise and weakens semantic clarity.

2. Preserve existing regime analysis pipeline unchanged.
- Rationale: when regimes are present, behavior remains exactly as-is; when caller-authored regimes are absent, factorial-generated cell regimes continue to populate regime/risk outputs.
- Alternative considered: synthesize an implicit "all rows" regime. Rejected because it adds unwanted output and obscures caller intent.

3. Cover both API and CLI paths with tests.
- Rationale: validate and run commands both call estimator.assess, so both need explicit acceptance checks for factorial-only specs.
- Alternative considered: test estimator only. Rejected because it can miss CLI spec-loading/validation behavior.

## Risks / Trade-offs

- Risk: Allowing empty regimes and empty factorials by mistake would accept meaningless specs.
  -> Mitigation: retain hard failure when both sets are empty.

- Risk: Existing tests may implicitly depend on a regime-required error message.
  -> Mitigation: update only tests tied to that exact precondition and add new factorial-only positive coverage.

- Risk: Users might assume factorial-only mode suppresses all regime-level output.
  -> Mitigation: document that factorial-generated cell regimes still appear, and no synthetic placeholder regime is introduced.

## Migration Plan

1. Update estimator validation logic to accept factorial-only specs.
2. Add/adjust tests for validator behavior matrix:
- regimes present, factorials absent -> valid
- regimes absent, factorials present -> valid
- regimes absent, factorials absent -> invalid
3. Run targeted contribution-kit tests.
4. Ship with no data migration required.

Rollback strategy:
- Revert validator condition to previous behavior if downstream tools unexpectedly depend on regime-required rejection.

## Open Questions

- Should CLI help text explicitly call out factorial-only support after this change?
- Should examples include one factorial-only config to make the supported mode obvious?