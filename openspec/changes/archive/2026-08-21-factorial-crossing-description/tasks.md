## 1. Schema

- [x] 1.1 Add `description: str | None = None` to `FactorialCrossing` in `src/contribution/spec.py`, documenting in the docstring that it explains the crossing's levels and is display-only
- [x] 1.2 Add `description` to the allowed crossing keys in `_load_spec` in `src/contribution/cli.py` and validate it as a non-empty string when provided, with the error identifying the crossing as `factorials[<i>]`
- [x] 1.3 Pass the parsed description through to the `FactorialCrossing` constructed in `src/contribution/cli.py`

## 2. Result plumbing

- [x] 2.1 Add `description: str | None = None` to `FactorialMatrixResult` in `src/contribution/results.py`
- [x] 2.2 Carry the crossing's description onto its `_FactorialPlan` in `_expand_factorials` and onto the `FactorialMatrixResult` built in `_build_factorial_matrices` in `src/contribution/estimator.py`
- [x] 2.3 Confirm the description reaches `to_json`/`run.json` through the existing `asdict` serialization of `factorial_matrices`, and round-trips back in `_result_from_payload` in `src/contribution/cli.py`

## 3. Rendering

- [x] 3.1 In `to_markdown` in `src/contribution/results.py`, render the description as a prose line beneath the matrix section heading and before the table, emitting nothing when it is absent
- [x] 3.2 Verify the contrast and attributable-burden sections are untouched

## 4. Tests

- [x] 4.1 Unit test: `FactorialCrossing` defaults `description` to `None` and accepts a declared value (`tests/unit/test_spec.py`)
- [x] 4.2 Config test: a crossing parses with a description; a non-string and an empty-string description each raise a configuration error naming the crossing
- [x] 4.3 Config test: an unknown crossing key is still rejected, and `description` is not treated as unknown
- [x] 4.4 Report test: a described crossing renders its prose between heading and matrix table; a description-free crossing renders no prose and its section is unchanged
- [x] 4.5 Invariance test: adding a description to an existing crossing leaves cell names, partition warnings, matrix statistics, contrasts, and burden entries identical

## 5. Example and docs

- [x] 5.1 Add a `description` to the `BW quality × scaling direction` crossing in `examples/continuous_lora/config.json` explaining `class_ok`/`upscale`/`downscale` and `measured_ok`/`measured_off`
- [x] 5.2 Add a `description` to the `Class decision × BW measurement` crossing explaining `class_workable`/`class_unworkable` and `bw_neutral`/`bw_shifts` in terms of the coalition each level scores
- [x] 5.3 Convert the example's `class_sf_match` regime from the bare-string form to the `{label, condition}` object form, matching its two siblings
- [x] 5.4 Document `description` in `README.md` where the factorial crossing keys are introduced
- [x] 5.5 Regenerate any checked-in example report/JSON artifacts affected by the new prose — none exist; example output is written to the gitignored `build/`

## 6. Verification

- [x] 6.1 Run `pytest` and confirm the full suite passes
- [x] 6.2 Run the continuous_lora example end to end and confirm the descriptions render and the reported statistics are unchanged
