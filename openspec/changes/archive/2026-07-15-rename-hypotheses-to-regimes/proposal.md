# Proposal: rename-hypotheses-to-regimes

## Why

"Hypothesis" is the meta-term: the human claim that motivates an analysis (e.g. "upscale augmentation drives the SF aliases"). What the `hypotheses` config key actually declares is the mechanical object that *tests* such a claim — a row subset selected by a boolean condition. The rest of the kit already calls that object a regime: report headings say "Regimes", the result type is `RegimeSummary`, the factorial capability is named `factorial-regime-declaration`, and the README describes `hypotheses` entries as regimes in every sentence. The config key is the last place the meta-word names the mechanical thing. Renaming now, while the kit has a single known user and before the vocabulary is frozen by publication, is the cheapest it will ever be.

## What Changes

- The config key `hypotheses` becomes `regimes` (same name-keyed mapping semantics: value is a condition string or `{condition, label?}` object). A config containing the old `hypotheses` key is rejected with an error that names the replacement key.
- The public declaration type `Hypothesis` becomes `Regime` (same fields: `name`, `condition`, `label`). `Hypothesis`, `CategoricalHypothesis`, and `ContinuousHypothesis` remain importable as backward-compatible aliases of `Regime`.
- `AttributionSpec.hypotheses` becomes `AttributionSpec.regimes` (clean rename, no field alias).
- `AssessmentResult.hypotheses` becomes `AssessmentResult.regimes`; the per-entry type `HypothesisAssessment` becomes `RegimeAssessment` (alias retained). The `run.json` payload key `hypotheses` becomes `regimes`; `contrib report` additionally accepts the legacy key when *reading* older `run.json` files.
- Report wording: the mismatch-risk table's first column header changes from `Hypothesis` to `Regime`; validation and error messages say "regime" (e.g. "At least one regime is required"). The required accessible-reports column labels (`Regime mismatch rate`, `Rest mismatch rate`) and effect-size labels are unchanged.
- Example configs, README, and docstrings are updated to the new vocabulary.

Explicitly kept (correct uses of "hypothesis" — genuine statistical tests, not regime declarations):

- the `contrib hypothesis` CLI subcommand and its flags;
- the `hypothesis.py` module, `BinaryHypothesisTest`, `BinaryHypothesisResult`, and `evaluate_binary_hypothesis/-es`;
- `binary_results` on `AssessmentResult`.

Out of scope:

- Nesting `factorials` under `regimes` (considered and rejected: reserved-key collision in an open namespace, heterogeneous value types).
- Renaming the `estimator-hypothesis-attribution` capability ID (spec folder names stay stable).
- An optional `rationale` free-text field for recording the motivating hypothesis per regime (possible future change).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `estimator-hypothesis-attribution`: the declaration requirement, unified-result requirement, regime-share requirement, integration-test requirement, and documentation requirement all speak `regimes`/`Regime` instead of `hypotheses`/`Hypothesis`.
- `factorial-regime-declaration`: generated cells are "generated regimes" rather than "generated regime hypotheses"; factor-free scenario references a `regimes` mapping.
- `accessible-reports`: the zero-mismatch omission rule speaks of regimes rather than hypotheses; mismatch-risk first column is `Regime`.

## Impact

- `external/contribution-kit/src/contribution/spec.py`: `Regime` type (aliases kept), `AttributionSpec.regimes`.
- `external/contribution-kit/src/contribution/cli.py`: `regimes` key parsing, rejection of `hypotheses` with migration error, legacy-key acceptance when reading `run.json`.
- `external/contribution-kit/src/contribution/estimator.py`: field access, validation messages.
- `external/contribution-kit/src/contribution/results.py`: `RegimeAssessment`, `AssessmentResult.regimes`, JSON key, report column header.
- `external/contribution-kit/src/contribution/__init__.py`: exports and aliases.
- `external/contribution-kit/examples/*/config.json` (and factorial example configs), `external/contribution-kit/README.md`, tests.
- Breaking change for config files and the Python keyword `hypotheses=`; type imports remain compatible through aliases.
- Prerequisite: archive `add-attributable-burden-ranking` first — its deltas touch the same factorial requirement this change modifies, and this change's delta text assumes the post-archive spec state.
