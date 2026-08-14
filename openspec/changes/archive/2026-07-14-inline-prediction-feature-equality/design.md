## Context

`contribution-kit` currently treats `prediction_features` as an explicit map of
feature name to `{actual, baseline, label?}` and rejects any string-valued
entry during `_load_spec`. That is consistent with the current README and
example configs, but it removed a concise way to express the common exact-match
boolean feature `lhs == rhs`. The user request is not to reopen generic boolean
conditions in features; it is to restore only the equality shorthand while
keeping the explicit object form as the canonical internal representation.

The relevant control path is narrow:

- `cli._load_spec` owns config parsing and validation.
- `expr.py` already parses the DSL through Python AST validation.
- `Estimator` consumes only normalized `PredictionFeature(actual, baseline,
  label)` objects and should not need branching by source syntax.

This change must avoid reintroducing the older, broader routing rule where
equality conditions declared elsewhere are inferred as features. The shorthand
belongs only to `prediction_features`.

## Goals / Non-Goals

**Goals:**

- Accept a `prediction_features` mapping value as either the current explicit
  object form or a shorthand string whose top-level expression is exactly one
  equality `lhs == rhs`.
- Normalize both forms into the same internal `PredictionFeature` object so the
  estimator, reports, and downstream validations stay unchanged.
- Reject every non-equality shorthand form, including `!=`, `<`, `>`, `<=`,
  `>=`, chained comparisons, and compound boolean expressions.
- Document when callers should use the shorthand versus the object form.

**Non-Goals:**

- No change to the Python API shape of `PredictionFeature` or
  `AttributionSpec.prediction_features`; direct code construction remains the
  explicit object form.
- No revival of hypothesis-condition auto-classification into Shapley features.
- No shorthand support for arbitrary boolean predicates or derived formulas in
  `prediction_features`.
- No change to Shapley math, feature naming, or report layout.

## Decisions

### D1: Shorthand support lives only in config loading

`cli._load_spec` will accept either:

- `{ "actual": "...", "baseline": "...", "label": "..." }`, or
- `"<actual_expr> == <baseline_expr>"`

Both forms normalize immediately into `PredictionFeature(actual=..., baseline=...,
label=...)`. This keeps runtime logic unchanged and confines the compatibility
surface to JSON/YAML loading.

*Alternative considered*: broadening `PredictionFeature` itself to accept a
single string. Rejected because the dataclass is already the normalized runtime
type; moving syntax polymorphism into the public type would leak config parsing
concerns into the Python API.

### D2: Valid shorthand is recognized structurally, not by string splitting

The parser should inspect the DSL AST and accept shorthand only when the parsed
expression body is a single `Compare` node with exactly one operator and that
operator is `Eq`. This allows parentheses and nontrivial subexpressions on each
side while rejecting:

- `a != b`
- `a < b`
- `a == b == c`
- `a == b and c == d`

The accepted left and right operands should be converted back into source text
for `PredictionFeature.actual` and `.baseline` using a deterministic AST-based
representation.

*Alternative considered*: splitting the source string on `==`. Rejected because
it is brittle in the presence of nested expressions and does not distinguish a
top-level equality from a compound boolean expression.

### D3: The shorthand omits label support by design

A string-valued feature entry carries only the equality expression. If a caller
needs a custom label, they must use the explicit object form. This keeps the
shorthand unambiguous and preserves one obvious escape hatch.

*Alternative considered*: inventing a secondary object wrapper such as
`{"condition": "a == b", "label": "..."}` for features. Rejected because it
creates a third feature shape and weakens the goal of keeping the shorthand
strict and narrow.

### D4: Documentation will present the object form as canonical and shorthand as convenience

README and example docs should show both forms, but describe the object form as
the general mechanism and the equality string as a compatibility convenience for
exact-match boolean features.

## Risks / Trade-offs

- [AST round-tripping normalizes formatting] → Acceptable; internal
  `PredictionFeature` strings are semantic inputs, not user-facing preserved
  formatting.
- [Users may expect other boolean conditions to work once strings are accepted]
  → Mitigate with explicit validation errors that mention only top-level `==`
  is allowed.
- [Spec drift with the older hypothesis-classification requirement] → Mitigate
  by updating the affected OpenSpec requirement blocks in the same change.

## Migration Plan

1. Update the OpenSpec delta spec to state the new `prediction_features`
   shorthand rule and the unchanged hypothesis/regime routing rule.
2. Implement a parsing helper plus `_load_spec` support, with targeted loader
   tests for accepted and rejected forms.
3. Update README and example configs to show at least one shorthand feature and
   the object form for labeled features.
4. Rollback is straightforward: remove the shorthand loader path and revert the
   docs/tests. Existing explicit-object configs remain valid throughout.

## Open Questions

- None blocking. The only implementation choice is whether to place the AST
  helper in `expr.py` for reuse or keep it private to `cli.py`; both satisfy
  the requirements.