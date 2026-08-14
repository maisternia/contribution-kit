## Context

`Estimator` currently supports feature-level attribution driven by `AttributionSpec`, while regime-based contribution accounting is handled separately in integration logic. This split makes hypothesis estimation behavior harder to discover, duplicates logic, and weakens API clarity for users who need to combine feature and regime analyses in one estimator-driven flow.

## Goals / Non-Goals

**Goals:**
- Make `Estimator` the single source for hypothesis estimation outputs.
- Support both expression-based feature hypotheses and predicate-based regime hypotheses through a coherent estimator API.
- Ensure the four class BW regimes can be represented and assessed through estimator-managed hypothesis structures.
- Enable a unified, single-door estimator workflow for arbitrary user-provided hypotheses.

**Non-Goals:**
- Rewriting unrelated reporting pipelines or changing dataset artifacts.
- Introducing broad architectural refactors outside `error_attribution` hypothesis and estimator pathways.
- Changing domain semantics for mismatch definitions in downstream scripts.
- Modifying existing legacy scripts under `scripts/`, which remain historical reference implementations.

## Decisions

1. Declare all hypotheses through one flat list of conditions.
- Decision: `AttributionSpec.hypotheses` is a single list of `Hypothesis` objects, each with one boolean `condition` DSL string. The estimator privately classifies each condition: a top-level equality (`actual == baseline`) is a formula feature (its operands are the Shapley actual/baseline), and any other condition is an error regime. There are no caller-facing `regimes`, `binary_tests`, `RegimeHypothesis`, `BinaryHypothesis`, or `actual_expr`/`baseline_expr` inputs.
- Rationale: Callers think in terms of "what may contribute to the formula error", not in terms of regimes/binary tables. Collapsing the three parallel input lists into one condition list keeps the public surface minimal and lets the private API decide how to analyse each hypothesis and render human-readable output.
- Alternative considered: Keep three declarative lists (`hypotheses`/`regimes`/`binary_tests`). Rejected because it leaks internal analysis machinery into the public API.

2. Return one unified per-hypothesis assessment, with derived views.
- Decision: `assess` returns `AssessmentResult.hypotheses`, one `HypothesisAssessment` per declared hypothesis (carrying an optional `feature`, `regime`, and `risk`). `feature_attributions`, `regime_summaries`, and `binary_results` are derived read-only views for reporting and snapshot parity.
- Rationale: A single 1:1 result list is the most human-readable output and keeps declaration order, while the derived views preserve the legacy table shapes.
- Alternative considered: Three separate result lists as primary outputs. Rejected because it re-introduces the multi-concept model on the output side.

3. Mismatch risk is condition-vs-rest.
- Decision: For each regime hypothesis the estimator compares the rows matching the condition against the rest of the population using the spec-level `mismatch_expr`, producing risk-ratio and odds-ratio results. No per-hypothesis baseline pairing is required.
- Rationale: A condition only needs itself; comparing against the complement is the simplest polarity-agnostic contrast and needs no extra caller input.
- Alternative considered: Caller-designated baseline pairings (the legacy regime-vs-baseline tests). Rejected because it re-introduces per-test configuration the user wants gone.

4. Prioritize a single unified estimator API over backward compatibility.
- Decision: Allow API changes needed to make condition-driven hypothesis evaluation the only supported path for this new component.
- Rationale: This component is new and not consumed elsewhere, so unification and clarity are more important than compatibility constraints.
- Alternative considered: Preserve old and new paths in parallel. Rejected because dual paths would keep ambiguity and split logic.

5. Make estimator outputs explicit for regime contribution analysis.
- Decision: Define estimator output fields and ordering guarantees needed by tests (name, count, mean error, total error, error share).
- Rationale: Integration tests and snapshot parity require deterministic, inspectable results.
- Alternative considered: Return opaque structures and leave formatting to callers. Rejected because it reduces testability.

## Risks / Trade-offs

- Risk: API surface expansion introduces ambiguity between feature and regime hypothesis evaluation paths. -> Mitigation: define clear parameter types and validation errors for mixed/invalid inputs.
- Risk: Numeric parity regressions in legacy snapshots. -> Mitigation: retain existing formulas and add focused integration assertions for known regime outputs.
- Risk: Existing internal assumptions around old entrypoints may break during consolidation. -> Mitigation: update integration tests to target the unified estimator interface directly.
