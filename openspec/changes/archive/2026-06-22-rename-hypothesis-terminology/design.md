## Context

The current API exposes `ContinuousHypothesis` and `CategoricalHypothesis`, but the runtime behavior is not based on continuous-vs-categorical data semantics. The estimator already routes hypotheses by condition shape: non-equality expressions are treated as regimes, while top-level equality expressions are treated as formula features.

This change renames the public hypothesis terminology to match that behavior and reduces confusion in the README, examples, and public API surface.

## Goals / Non-Goals

**Goals:**
- Expose role-based names: `RegimeHypothesis` and `FeatureHypothesis`.
- Keep existing imports working through compatibility aliases during migration.
- Update docs and examples so the new terminology is the default language.
- Preserve all existing analysis behavior and result shapes.

**Non-Goals:**
- No change to the underlying estimator routing logic.
- No change to the feature attribution math or the regime risk calculations.
- No change to CSV schema, DSL syntax, or CLI behavior beyond naming/documentation.

## Decisions

1. Keep the classification logic unchanged and only rename the public types.
   - Rationale: the behavior is already correct; the mismatch is in nomenclature. Rewriting the routing logic would add risk without changing user-visible results.
   - Alternatives considered: infer meaning from `kind` alone, or introduce a separate enum-based API. Both would broaden the change unnecessarily.

2. Preserve `ContinuousHypothesis` and `CategoricalHypothesis` as aliases during migration.
   - Rationale: this avoids a hard break for existing scripts and notebooks while still allowing the new names to become the preferred API.
   - Alternatives considered: remove the old names immediately, or keep both names indefinitely without documentation changes. Immediate removal is too disruptive; indefinite dual naming would keep the confusion.

3. Treat the README as the primary migration surface.
   - Rationale: the docs currently teach the misleading terminology, so the examples need to be updated alongside the public classes.
   - Alternatives considered: update only code and leave docs for later. That would preserve the current confusion.

4. Add or update tests to assert both the new names and the aliases behave identically.
   - Rationale: this prevents regressions during the rename and documents the compatibility policy.
   - Alternatives considered: rely on manual review only. That would not protect the migration path.

## Risks / Trade-offs

- [Risk] Users may be unsure which name to use during the transition. → Mitigation: document the new names first, keep the legacy aliases, and avoid introducing new examples with the old terminology.
- [Risk] A rename can break downstream import checks or style tools that look for exact symbol names. → Mitigation: preserve aliases and update examples/tests together so the migration path is explicit.
- [Risk] The public API may still appear to support both naming schemes. → Mitigation: make the README and spec consistently prefer the role-based names so the old terminology becomes clearly transitional.

## Migration Plan

1. Introduce `RegimeHypothesis` and `FeatureHypothesis` in the public API.
2. Keep `ContinuousHypothesis` and `CategoricalHypothesis` as aliases pointing to the new names.
3. Update README examples, docs, and any snippets in the repository to use the new names.
4. Add tests covering new-name imports, alias imports, and identical estimator behavior.
5. If needed, later remove the aliases in a separate breaking change after downstream consumers have migrated.

Rollback would be straightforward: restore the old names as the primary exports and keep the compatibility aliases in place until the rename is ready again.

## Open Questions

- Should the legacy names be formally deprecated in code comments or warnings, or remain silent aliases for this change?
- Should the public base type remain `Hypothesis`, or should the new role-based names become the primary user-facing classes with the base type emphasized less in docs?