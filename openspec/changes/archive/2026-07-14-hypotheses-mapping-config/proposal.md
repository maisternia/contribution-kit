# Proposal: hypotheses-mapping-config

## Why

The config `hypotheses` block is a list of objects that each repeat a `name` field, while the sibling `factors` block is already a name-keyed mapping. This asymmetry makes the two condition-bearing blocks look structurally unrelated even though a factor axis is just a namespaced group of conditions, and it forces every hypothesis — even a bare equality — to be written as a three-field object.

## What Changes

- **BREAKING**: The config `hypotheses` block becomes a name-keyed **mapping** (`{name -> value}`) instead of a list of `{name, condition, label}` objects. The map key is the hypothesis name; the redundant `name` field is removed.
- Each `hypotheses` value accepts two forms:
  - a **condition string** shorthand — e.g. `"class_bw": "col('Class BW') == col('GT BW')"` — where `label` defaults to the key;
  - an **object** `{ "condition": ..., "label"?: ... }` for when a distinct label is wanted.
- The loader rejects two malformed shapes with clear errors: an object value missing `condition`, and an object value that redeclares `name` (the key is the name).
- Insertion order of the mapping is preserved for report ordering (Python dicts / `json.loads` are insertion-ordered).
- **BREAKING**: The list form of `hypotheses` is removed — **no backward compatibility**. **All** bundled example configs are migrated to the mapping form.
- No change to `factors` (already a mapping), `factorials` (stays a list — a crossing has no natural key), the estimator, or any report/JSON output.

Out of scope:

- Merging `factors` into `hypotheses` (the "namespaced hypotheses" idea) — explicitly deferred; this change keeps `hypotheses`, `factors`, and `factorials` as distinct top-level blocks.
- Any change to hypothesis routing, Shapley features, regimes, factorial expansion, partition validation, or report rendering.
- A shared-constants/`params` block.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `estimator-hypothesis-attribution`: the requirement "Hypotheses SHALL Be Declared As A Flat List Of Conditions" changes to a **name-keyed mapping** with string-or-object values; the private routing rule, the single public `Hypothesis` type, and all downstream analysis are unchanged.

## Impact

- `external/contribution-kit/src/contribution/cli.py`: `_load_spec` parses `hypotheses` as a mapping with str/object dispatch and the two validation guards.
- **All** example configs migrate `hypotheses` list → mapping (adopting the string shorthand where no custom label is needed):
  - `external/contribution-kit/examples/continuous_lora/config.json`
  - `external/contribution-kit/examples/continuous_lora/config_factorial.json`
  - `external/contribution-kit/examples/grocery_shelf_count/config.json`
  - `external/contribution-kit/examples/household_temperature/config.json`
  - `external/contribution-kit/examples/rainy_walkway/config.json`
  - `external/contribution-kit/examples/ungated_sf_config.json`
  - (`examples/continuous_lora/idea.json` is the sketch that motivated this change and already uses the mapping form.)
- `external/contribution-kit/README.md`: document the mapping form and the string shorthand.
- `external/contribution-kit/src/contribution/spec.py`: unchanged (`Hypothesis`/`AttributionSpec` in-memory shapes stay as-is; only the loader that builds them changes).
- Engine (`estimator.py`), rendering (`results.py`), and all report/JSON outputs: unchanged and byte-stable for equivalent inputs.
