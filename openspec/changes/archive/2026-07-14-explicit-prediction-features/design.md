# Design: Explicit Prediction Features

## Context

Shapley features in the contribution-kit are currently derived from hypothesis
condition syntax. `Estimator._formula_features` runs `split_equality` over
every hypothesis condition; any top-level `ast.Eq` comparison becomes a
`_Feature(actual=left, baseline=right)` and joins the Shapley decomposition of
`prediction_expr`. Everything else is a regime. This implicit routing has
known traps:

- `a == b` reads commutative but the operand split is directional (left =
  model-produced, right = ground-truth baseline). Swapped operands silently
  flip attribution.
- Misrouting is silent: a non-`==` condition intended as a feature becomes a
  regime; an `==` condition intended as a regime becomes a feature. A feature
  whose name is not referenced by `prediction_expr` contributes exactly zero
  with no diagnostic.
- The `spec.py` docstring claims feature routing also requires the name to
  appear in `prediction_expr`; the code never checks this.

The `estimator-hypothesis-attribution` spec currently mandates the
condition-shape classification rule, so this change modifies that spec.
The kit lives in `external/contribution-kit` (its own repo, currently
consumed only by this workspace and its examples/tests), so a breaking
config change is acceptable without a deprecation cycle.

## Goals / Non-Goals

**Goals:**

- Make Shapley feature declaration explicit, ordered, and self-documenting:
  `prediction_features: {name: {actual, baseline}}` on `AttributionSpec` and
  in the JSON config.
- Make `hypotheses` uniformly regimes — one declaration kind, one analysis
  path, no syntax-shape routing.
- Fail fast on every previously-silent inconsistency between
  `prediction_expr` and the declared features.
- Keep result types, report shapes, and downstream views unchanged.

**Non-Goals:**

- No change to Shapley math (`_assess_row`, `_coalition_score`, exact/sampling
  paths) — only to how `_Feature` instances are constructed and validated.
- No change to regimes, factors/factorials, mismatch-risk statistics, or CI
  methods.
- No backward-compatibility shim that keeps accepting `==` hypotheses as
  features (breaking change by design; silent dual-meaning is the problem
  being removed).
- No renaming of internal/result types (`_Feature`, `FeatureAttribution`,
  `analysis="feature"`).

## Decisions

### D1: Name the declaration `prediction_features`

Chosen over `features` (ambiguous — could be read as dataset/model input
columns), `players` (game-theoretically correct but obscure), and
`prediction_parameters` / `shapley_impacts` (vague or output-naming). The
`prediction_` prefix creates a coherent family with existing keys:
`prediction` (observed), `prediction_expr` (formula), `prediction_features`
(the formula's variables). SHAP literature also uses "feature" with
"actual/baseline" values, matching the existing `FeatureAttribution` result
type.

### D2: Pairs are objects with required `actual` and `baseline` keys

Chosen over a two-element array `[actual, baseline]` and over keeping the
`==` sugar. Named keys make the directional split impossible to get wrong —
the core trap being fixed. Spec-side this is a small
`PredictionFeature(actual: str, baseline: str, label: str | None)` dataclass;
`AttributionSpec.prediction_features` is `dict[str, PredictionFeature]`
(insertion-ordered, preserving report ordering). JSON config mirrors it:

```json
"prediction_features": {
  "class_sf": { "actual": "col('Class SF')", "baseline": "col('GT SF')" }
}
```

`label` remains optional, defaulting to the feature name, same as hypotheses.

### D3: Bidirectional validation between `prediction_expr` and features

`_validate_spec` gains two checks, both hard errors:

1. Every free variable of `prediction_expr` must be a declared
   `prediction_features` name. Free variables are the `ast.Name` nodes of the
   compiled expression minus `_ALLOWED_FUNCTIONS` keys and `col`. This is a
   small helper in `expr.py` (e.g. `free_variables(expression)`).
2. Every declared feature name must appear among those free variables
   (eliminates the silent zero-effect feature).

Feature names must also not collide with hypothesis names, since both appear
in the unified `hypotheses` result list.

Rationale: validation stated in terms of the expression's own variables is
exactly the invariant the old docstring promised but never enforced, and it
covers the user-facing "error if there is no `==`" requirement more strongly.

### D4: `hypotheses` are always regimes; equality conditions stay legal

`_formula_features` stops scanning hypothesis conditions and instead builds
`_Feature` objects directly from `spec.prediction_features` by compiling the
`actual`/`baseline` sources. A hypothesis condition containing `==` is now an
ordinary regime predicate (useful, e.g. "rows where class SF is correct" as a
subgroup). This also restores regime/risk analysis for equality statements,
which the old routing withheld.

`split_equality` in `expr.py` loses its only production caller; remove it
(tests referencing it migrate), keeping `expr.py` minimal.

### D5: Result assembly keys features by declaration source, not name lookup

`assess()` currently emits a `HypothesisAssessment(analysis="feature")` when a
hypothesis name is found in the computed feature attributions. With features
declared separately, `assess()` emits feature assessments directly from
`prediction_features` (in declaration order, before or after regime entries —
keep current report ordering: features first, matching existing
`feature_attributions` ranking behavior), and every `hypotheses` entry emits a
regime assessment. `AssessmentResult` shape is unchanged.

### D6: Migrate examples and docs in the same change

`examples/continuous_lora/config*.json`, README classification-rule section,
and `spec.py` docstrings all describe the `==` rule; leaving any of them
stale would recreate the confusion this change removes. The example
`config_factorial.json` moves its three `==` hypotheses (`class_sf`,
`class_bw`, `measured_bw`) into `prediction_features` with explicit
actual/baseline pairs.

## Risks / Trade-offs

- [Breaking configs] Existing JSON configs with `==` feature-hypotheses stop
  producing Shapley output. → Mitigation: validation error message explains
  the migration ("variable 'class_sf' in prediction_expr has no
  prediction_features entry; declare {actual, baseline}"), README shows a
  before/after example.
- [Config verbosity] Explicit pairs are longer than one `==` string. →
  Accepted: self-documenting order beats terseness; typical configs declare
  ≤ 3 features.
- [Strict bidirectional validation may be too rigid] A user experimenting
  with a reduced `prediction_expr` must also trim `prediction_features`. →
  Accepted: silent zero-attribution was the worse failure; the error message
  names the offending feature.
- [Hidden dependents] Scripts or notebooks outside the kit's tests that build
  `AttributionSpec` with equality hypotheses would silently lose features
  (they become regimes) if they bypass validation paths. → Mitigation: the
  `prediction_expr` free-variable check makes such specs fail loudly, since
  the expression's variables will have no feature declarations.

## Migration Plan

1. Add `PredictionFeature` + `prediction_features` to `AttributionSpec`
   alongside new validation (kit still routes `==` at this point; tests keep
   passing).
2. Switch `_formula_features` to `prediction_features`, drop `==` routing,
   remove `split_equality`.
3. Update CLI config loader, README, docstrings, examples, and kit tests in
   the same commit series on the kit repo.
4. Update ResearchData integration tests/fixtures that declare equality
   hypotheses.

Rollback: revert the kit commits; configs are forward-only (new key is
ignored by old code, but old `==` behavior returns on revert).

## Open Questions

- Should feature assessments also report the implied `actual == baseline`
  regime share/risk (features get both analyses)? Deferred — out of scope
  here to keep result shape unchanged; can be a follow-up capability.
