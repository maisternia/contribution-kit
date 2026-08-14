# Tasks: rename-hypotheses-to-regimes

## 0. Sequencing

- [x] 0.1 Archive `add-attributable-burden-ranking` (complete and verified) so its factorial-spec deltas land before this change's deltas are applied

## 1. Types and spec surface

- [x] 1.1 Rename `Hypothesis` → `Regime` in `external/contribution-kit/src/contribution/spec.py`; keep `Hypothesis`, `CategoricalHypothesis`, and `ContinuousHypothesis` as aliases of `Regime`; update the docstring to state the routing rule in regime vocabulary
- [x] 1.2 Rename `AttributionSpec.hypotheses` → `AttributionSpec.regimes` (no field alias) and update the class docstring
- [x] 1.3 Update `external/contribution-kit/src/contribution/__init__.py` exports: `Regime` and `RegimeAssessment` canonical, legacy names re-exported as aliases

## 2. Config loading and CLI

- [x] 2.1 Parse the `regimes` mapping key in `external/contribution-kit/src/contribution/cli.py` (same string/object value semantics); reject a top-level `hypotheses` key with a configuration error stating it was renamed to `regimes`
- [x] 2.2 Update loader validation messages to say "regime" where they name declared entries
- [x] 2.3 `contrib report`: read per-regime entries from the `regimes` payload key, falling back to the legacy `hypotheses` key for older `run.json` files

## 3. Estimator and results

- [x] 3.1 Rename field access and validation messages in `external/contribution-kit/src/contribution/estimator.py` (e.g. "At least one regime is required")
- [x] 3.2 Rename `HypothesisAssessment` → `RegimeAssessment` and `AssessmentResult.hypotheses` → `AssessmentResult.regimes` in `external/contribution-kit/src/contribution/results.py`; keep `HypothesisAssessment` as an alias
- [x] 3.3 Write the JSON payload key `regimes` in `to_json`; change the mismatch-risk table's first column header from `Hypothesis` to `Regime`; leave `Regime mismatch rate` / `Rest mismatch rate` / effect-size labels and footnotes untouched

## 4. Examples, docs, tests

- [x] 4.1 Rename the `hypotheses` key to `regimes` in every bundled example config (`examples/continuous_lora/config.json` and its factorial variants, `household_temperature`, `rainy_walkway`, `grocery_shelf_count`)
- [x] 4.2 Update `external/contribution-kit/README.md`: config schema docs, quick start (`Regime` import), How-it-works bullets, and CLI section to the `regimes` vocabulary; note that `contrib hypothesis` remains the explicit A-vs-B statistical test
- [x] 4.3 Update unit and smoke tests for the renamed key, types, fields, JSON key, and report header; add tests for the `hypotheses`-key migration error, the alias imports, and the `contrib report` legacy-key fallback
- [x] 4.4 Run the unit-coverage gate (`pytest tests/unit --cov=contribution --cov-branch --cov-fail-under=100`) and the smoke suite to confirm no missed access path

## 5. Verification

- [x] 5.1 Re-run the README quick-start snippet and `contrib run` on `examples/continuous_lora` to confirm identical numeric output (burden table 164.66 / 78.06, accuracy 97.64% → 99.80%) under the new vocabulary
- [x] 5.2 Confirm a config still using `hypotheses` fails with the migration error naming `regimes`
