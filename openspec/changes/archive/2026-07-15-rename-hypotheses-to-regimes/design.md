# Design: rename-hypotheses-to-regimes

## Context

The kit's vocabulary grew in layers: `hypotheses` was chosen when the config was a flat list of assumptions, but the analysis pipeline, report headings, and result types all converged on "regime" (a row subset selected by a boolean condition). The conceptual ladder is now: **hypothesis** (human claim, meta) → **regime** (mechanical row subset) → **factorial crossing** (partition-validated system of regimes) → **analyses** (Shapley, share/risk, burden). Only the declaration surface still says "hypothesis".

Prior related decisions: the hypotheses list→mapping change (2026-07-14) and the equality-routing removal both favored explicit flat declarations with closed key sets and hard breaks over compatibility shims — this change follows the same style.

## Goals / Non-Goals

**Goals:**

- One consistent word for the mechanical object across config, Python API, results, JSON, and report.
- Hard, loud break for the config key (clear migration error), soft break for Python type imports (aliases).
- Preserve the legitimate statistical-test uses of "hypothesis".

**Non-Goals:**

- No structural changes (no nesting of factorials under regimes; considered and rejected — reserved-key collision in an open namespace, heterogeneous value types, and the kit's precedent of flat explicit declarations).
- No capability-ID renames in openspec/specs.
- No new fields (a `rationale` field for recording the motivating hypothesis is a possible follow-up, not part of the rename).

## Decisions

### D1: `Regime` is the canonical type; old names remain as aliases

`spec.py` renames the dataclass `Hypothesis` → `Regime` (fields unchanged: `name`, `condition`, `label`). `Hypothesis`, `CategoricalHypothesis`, and `ContinuousHypothesis` become aliases of `Regime`, staying importable from the package root. Precedent: `CategoricalHypothesis`/`ContinuousHypothesis` already exist purely as back-compat aliases.

*Alternative considered*: deleting `Hypothesis` outright — rejected; aliases are one line each and keep old notebooks running.

### D2: Config key is a clean break with a migration error

The loader accepts only `regimes`. If a config contains `hypotheses`, loading fails with an error stating the key was renamed to `regimes`. Silently accepting both would leave the old vocabulary alive in the wild; the kit's own history (list form rejection) sets the precedent for hard breaks with clear errors.

### D3: Python field renames are clean; only type names get aliases

`AttributionSpec.regimes` and `AssessmentResult.regimes` replace the `hypotheses` fields with no property shims — both dataclasses use `slots`, and a shim would silently freeze the old vocabulary into the API. `HypothesisAssessment` → `RegimeAssessment` with an alias, matching D1.

### D4: `run.json` writes `regimes`; `contrib report` reads both

The serialized payload key becomes `regimes`. `contrib report` (which regenerates markdown from a saved `run.json`) additionally accepts the legacy `hypotheses` key on read so existing saved runs remain renderable. Write path never emits the old key.

### D5: Where "hypothesis" survives

`contrib hypothesis`, `hypothesis.py`, `BinaryHypothesisTest`, `BinaryHypothesisResult`, `evaluate_binary_hypothesis/-es`, and `binary_results` keep their names: they denote genuine statistical hypothesis tests (an explicit A-vs-B contrast with effect-size CIs), which is the correct use of the word. The report's mismatch-risk *column header* `Hypothesis` becomes `Regime` because its rows are regimes, not tests.

### D6: Report and message wording

- Mismatch-risk table header: `| Hypothesis | Regime mismatch rate | ...` → `| Regime | Regime mismatch rate | ...`. The accessible-reports-mandated labels (`Regime mismatch rate`, `Rest mismatch rate`, effect-size columns, footnotes) are untouched.
- Estimator validation: "At least one hypothesis is required" → "At least one regime is required"; other messages that name the config key follow the key rename.

### D7: Sequencing against the pending burden change

`add-attributable-burden-ranking` (complete, verified) must be archived before this change is applied: both changes modify `factorial-regime-declaration`, and this change's delta text for the inline-axes requirement is written against the post-archive state (allowed crossing keys including `baseline`).

## Risks / Trade-offs

- [Old configs break] → intentional; the migration error names the new key, and the fix is a one-word edit.
- [Delta conflicts with the un-archived burden change] → D7 sequencing; tasks include an explicit archive-first step.
- [Renamed JSON key breaks external consumers of run.json] → only known consumer is `contrib report`, which reads both (D4).
- [Test suite churn] → mechanical; the 100% unit-coverage gate catches any missed access path.

## Open Questions

- None blocking.
