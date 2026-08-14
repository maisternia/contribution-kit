# Design: Inline Factorial Axes

## Context

A factorial crossing is currently declared in two places: `factors` (named
axes, each a map of level name → boolean condition DSL string) and
`factorials` (a list of `{rows: <axis-name>, columns: <axis-name>}`
references). `Estimator._validate_spec` rejects unknown axis references and
warns on unused factors; `_expand_factorials` resolves the referenced
`Factor` objects, evaluates level membership, checks partitions, and expands
cells into generated regime hypotheses named `<row_level> & <column_level>`.

Axis names propagate into three result surfaces:

- `FactorialMatrixResult.rows_axis` / `columns_axis` → report header
  `### <rows_axis> x <columns_axis>` and `run.json` payload
- `ContrastResult.factorial` (`"<rows_axis> x <columns_axis>"`) and
  `.stratum` (`"<axis>=<level>"`) → contrast section headers
- `PartitionWarning.axis` → warning text and `run.json` payload

Inspection of generated reports (`build/new_fac/report.md`) shows axis names
appear only in headers; all table rows, generated hypothesis names, and
comparisons use level names exclusively. In practice configs declare one
crossing and never reuse an axis, so the reference indirection provides no
value.

The `explicit-prediction-features` change is in flight and touches the same
loader and example configs; this change is schema-orthogonal but shares
files.

## Goals / Non-Goals

**Goals:**

- Declare each factorial crossing as a self-contained object: inline
  `rows`/`columns` level maps plus an optional human-readable `label`.
- Remove the `factors` block and its reference-resolution machinery.
- Keep all factorial statistics byte-identical: cell expansion, generated
  cell names, partition checks, marginals, contrasts, and CI math are
  untouched.
- Keep reports readable without config knowledge (label as matrix title).

**Non-Goals:**

- No axis reuse across crossings (dropped deliberately; duplicate inline if
  ever needed).
- No backward compatibility for the old `factors` + reference config shape
  or for pre-change `run.json` factorial payloads (kit is pre-1.0; both
  in-tree examples migrate in this change).
- No changes to hypothesis routing, Shapley features, or regime analysis.
- No support for >2 axes per crossing.

## Decisions

### D1: `FactorialCrossing` carries inline level maps and an optional label

```python
@dataclass(slots=True)
class FactorialCrossing:
    rows: dict[str, str]      # level name -> condition DSL
    columns: dict[str, str]   # level name -> condition DSL
    label: str | None = None
```

`Factor` and `AttributionSpec.factors` are deleted. Rationale: the estimator
only ever needs the level maps; a separate named-axis type exists solely to
serve the reference indirection being removed.

*Alternative considered*: polymorphic `rows`/`columns` (string reference OR
inline dict) keeping `factors` optional. Rejected — keeps two code paths and
two error classes alive to preserve a reuse feature no config uses.

### D2: Display identity is `label` with positional fallback, no `name` field

Effective label = `crossing.label` if set, else `"Factorial <n>"` (1-based
position in the `factorials` list). Nothing machine-consumes crossing
identity: generated cell hypotheses are named from level names, and cell
name collisions are already rejected. A `name` field would be schema weight
with no consumer.

### D3: Axis roles are the fixed words `rows` and `columns`

Wherever an axis (not a whole crossing) must be identified — partition
warnings, contrast stratum keys — use the structural role name:

- `PartitionWarning.axis` value becomes `"<effective label>: rows"` (or
  `": columns"`). Field name and payload shape are unchanged.
- `ContrastResult.stratum` becomes `"rows=<level>"` / `"columns=<level>"`.

Level names alone are not guaranteed unique across the two axes of a
crossing (only combined cell names are collision-checked), so the role
prefix stays.

### D4: `FactorialMatrixResult` replaces axis names with `label`

```python
@dataclass(slots=True)
class FactorialMatrixResult:
    label: str                # effective label (declared or fallback)
    cells: list[FactorialCellResult] = ...
    row_marginals: list[FactorialMarginalResult] = ...
    column_marginals: list[FactorialMarginalResult] = ...
```

Report header becomes `### <label>`; contrast section headers become
`### <label> :: rows=<level>`. `ContrastResult.factorial` carries the same
effective label. `_result_from_run` in `cli.py` reads `label` instead of
`rows_axis`/`columns_axis`; old `run.json` files stop round-tripping (accepted
per Non-Goals).

### D5: Loader validation moves from reference checks to shape checks

`_load_spec` parses each `factorials[i]` as:

- `rows` and `columns`: required non-empty dicts of non-empty string
  conditions (same per-level validation `factors` had).
- `label`: optional non-empty string.
- Unknown keys rejected (mirrors the strictness added for
  `prediction_features`).

`Estimator._validate_spec` keeps the "at least one level per axis" check on
the crossing itself; the unknown-axis error and unused-factor warning are
deleted. `_FactorialPlan.rows_axis`/`columns_axis` collapse into a single
`label` field.

### D6: Example configs migrate; `idea.json` is the reference shape

`examples/continuous_lora/config_factorial.json` and the README schema
section move to the inline form. `idea.json` already models the target
shape (modulo coordination with `explicit-prediction-features` for the
`prediction_features` block).

## Risks / Trade-offs

- [Old `run.json` artifacts under `build/` no longer feed `contrib report`]
  → Accepted: regenerate with `contrib run`; document in README changelog
  note. No external consumers exist.
- [Merge friction with in-flight `explicit-prediction-features` in
  `cli.py`, `spec.py`, tests, and shared examples] → Implement this change
  on its own branch after the other change's work is committed; rebase the
  loader edits on top of the new `_load_spec` shape.
- [Losing axis reuse] → If a future config needs the same axis in two
  crossings, conditions are duplicated; acceptable for a diagnostic-config
  DSL where crossings are few and explicit.
- [`"Factorial <n>"` fallback is positional] → Reordering the `factorials`
  list renames unlabeled matrices in reports. Mitigation: examples and docs
  always set `label`.

## Migration Plan

1. Land `spec.py` + `cli.py` + `estimator.py` + `results.py` changes with
   updated unit tests in one commit (schema is atomic; no dual-shape
   support).
2. Migrate `examples/continuous_lora/config_factorial.json`, README schema
   docs, and smoke tests in the same change.
3. Regenerate any `build/` factorial run outputs used for comparison.
4. Rollback = revert the change; configs in the old shape were not deleted
   from git history.

## Open Questions

- None blocking. Coordination point: if `explicit-prediction-features`
  archives first, `idea.json` becomes the canonical example for both shapes
  at once — confirm final example file naming (`config_factorial.json` vs
  promoting `idea.json`) during implementation.
