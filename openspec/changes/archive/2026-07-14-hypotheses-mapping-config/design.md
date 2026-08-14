# Design: hypotheses-mapping-config

## Context

`contribution-kit` loads its analysis config in `cli.py._load_spec`. Today the `hypotheses` block is a JSON **list** of objects, each parsed with `Hypothesis(**item)` and each repeating a `name` field. The sibling `factors` block is already a name-keyed **mapping** (`axis_name -> {level_name -> condition}`), and `factorials` is a list of `{rows, columns}` crossings. Downstream, `estimator.py` treats the caller-authored hypotheses and the factorial-generated cells identically as `Hypothesis` objects; nothing below the loader cares whether the config spelled hypotheses as a list or a map.

The asymmetry (list-of-objects vs. mapping) is purely at the config surface. This change aligns `hypotheses` with `factors` by making it a mapping and adds a string shorthand, without touching the in-memory `Hypothesis`/`AttributionSpec` types or any analysis code.

Key existing structures:

- `spec.py`: `Hypothesis(name, condition, label)`, `AttributionSpec(target, prediction, prediction_expr, hypotheses: list[Hypothesis], factors, factorials, scope, score_mode)`.
- `cli.py._load_spec`: builds `hypotheses` via `for item in payload.get("hypotheses", []): Hypothesis(**item)`.
- `estimator.py`: consumes `spec.hypotheses` as a list of `Hypothesis`; order-sensitive for report rows.

## Goals / Non-Goals

**Goals:**

- `hypotheses` config becomes a name-keyed mapping; the key is the name.
- Value accepts a condition string (shorthand) or an object `{condition, label?}`.
- Clear loader errors for an object missing `condition` and for a redundant `name` key.
- Preserve declared order for rendering.
- Keep engine, rendering, and all outputs byte-stable for equivalent inputs.

**Non-Goals:**

- Merging `factors` into `hypotheses` (namespaced hypotheses) — deferred.
- Any backward compatibility with the list form — hard cutover.
- Changing `Hypothesis`/`AttributionSpec` in-memory shapes.
- Changing `factors` (already a mapping) or `factorials` (stays a list).

## Decisions

### D1: `hypotheses` is a mapping; value type dispatched at load

`_load_spec` iterates `payload["hypotheses"].items()`. For each `(key, value)`:

- `value` is a `str` → `Hypothesis(name=key, condition=value)` (label defaults to `None`, and the engine already renders `label or name`).
- `value` is a `dict` → `Hypothesis(name=key, **value)` after the guards below.
- anything else → configuration error.

Insertion order of the mapping is preserved because `json.loads` builds an insertion-ordered `dict` and the resulting `hypotheses` list keeps that order.

*Alternative considered*: accept both list and mapping. Rejected — the proposal mandates a hard cutover with no backward compatibility, and dual acceptance would keep the redundant `name` field alive.

### D2: Two validation guards with named errors

- **Missing `condition`**: an object value without a `condition` key raises `ValueError("hypothesis '<key>' must declare a 'condition' string")`. This also disambiguates from a factor-style level map, which is not valid under `hypotheses`.
- **Redundant `name`**: an object value containing a `name` key raises `ValueError("hypothesis '<key>' must not redeclare 'name'; the mapping key is the name")`.

Both errors name the offending key so misconfigurations are localized.

### D3: No disambiguation footgun

Because `hypotheses` and `factors` are separate top-level blocks, the string/object dispatch under `hypotheses` cannot be confused with a factor level map. `condition` is only "reserved" in the trivial sense that an object value is required to contain it; there is no shape-sniffing across blocks.

### D4: Loader-only blast radius

`spec.py`, `estimator.py`, and `results.py` are untouched. The only Python change is in `cli.py._load_spec`. Example configs are migrated to the mapping form (adopting the shorthand where no custom label is needed). This keeps a clean equivalence: a migrated config produces the same `AttributionSpec.hypotheses` (same names, conditions, labels, order) as the pre-change list config, so `run.json`/`report.md` are unchanged.

## Risks / Trade-offs

- **Breaking change**: any external config using the list form stops loading. Accepted per proposal (no backward compatibility). Mitigation: migrate the bundled examples and document the new form in the README.
- **Duplicate names impossible**: a mapping cannot hold two entries with the same key. This is a feature — hypothesis names must be unique anyway.

## Migration

- Rewrite the `hypotheses` block from list → mapping in every example config; use string shorthand for entries whose label equals the name, and the object form only where a distinct `label` is present:
  - `examples/continuous_lora/config.json`
  - `examples/continuous_lora/config_factorial.json`
  - `examples/grocery_shelf_count/config.json`
  - `examples/household_temperature/config.json`
  - `examples/rainy_walkway/config.json`
  - `examples/ungated_sf_config.json`
- `examples/continuous_lora/idea.json` already uses the mapping form (it motivated this change); leave it as the reference sketch.
- Update `README.md` schema docs and any inline examples.

## Open Questions

- None. The one prior decision (backward compatibility) is resolved: hard cutover, no list-form support.
