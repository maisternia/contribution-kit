# Tasks: hypotheses-mapping-config

## 1. Loader change

- [x] 1.1 In `external/contribution-kit/src/contribution/cli.py._load_spec`, parse `hypotheses` as a mapping: iterate `items()`, dispatch `str` → `Hypothesis(name=key, condition=value)` and `dict` → `Hypothesis(name=key, **value)`, and raise a clear error for any other value type
- [x] 1.2 Add the "object missing `condition`" guard with an error naming the offending hypothesis key
- [x] 1.3 Add the "redundant `name` key" guard with an error naming the offending hypothesis key
- [x] 1.4 Confirm declared mapping order is preserved into `AttributionSpec.hypotheses` (no sorting)

## 2. Example migration (all configs)

- [x] 2.1 Rewrite `examples/continuous_lora/config.json` `hypotheses` list → mapping (string shorthand where label equals name)
- [x] 2.2 Rewrite `examples/continuous_lora/config_factorial.json` `hypotheses` list → mapping
- [x] 2.3 Rewrite `examples/grocery_shelf_count/config.json` `hypotheses` list → mapping
- [x] 2.4 Rewrite `examples/household_temperature/config.json` `hypotheses` list → mapping
- [x] 2.5 Rewrite `examples/rainy_walkway/config.json` `hypotheses` list → mapping
- [x] 2.6 Rewrite `examples/ungated_sf_config.json` `hypotheses` list → mapping
- [x] 2.7 Confirm `examples/continuous_lora/idea.json` already conforms (reference sketch; no change beyond consistency)
- [x] 2.8 Verify each migrated config produces `run.json`/`report.md` identical to the pre-change run for the same input CSV

## 3. Tests

- [x] 3.1 Add a loader test: mapping with a string-shorthand entry materializes `Hypothesis(name, condition, label=name-default)`
- [x] 3.2 Add a loader test: mapping with an object entry `{condition, label}` materializes the explicit label
- [x] 3.3 Add a loader test: object value missing `condition` raises an error naming the key
- [x] 3.4 Add a loader test: object value with a `name` key raises an error naming the key
- [x] 3.5 Add a loader test: declared mapping order is preserved in `spec.hypotheses`
- [x] 3.6 Add a regression test: a migrated example config yields the same `AttributionSpec.hypotheses` (names, conditions, labels, order) as the equivalent old list config

## 4. Docs

- [x] 4.1 Update `external/contribution-kit/README.md`: document the `hypotheses` mapping form, the string shorthand, and the two validation errors
- [x] 4.2 Note in the README that the list form is no longer accepted (breaking change)
