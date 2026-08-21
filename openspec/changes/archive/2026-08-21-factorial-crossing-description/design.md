## Context

A crossing today declares `rows`, `columns`, an optional `label`, and an
optional `baseline`. `label` titles the crossing's matrix and contrast sections;
it is a name, and it is used as one. Nothing in the schema holds an explanation.

The obvious alternative — a `label` per axis level, mirroring `Regime` — was
considered and rejected: it would push prose into the axis maps, which are the
most readable part of a crossing precisely because each line is one name and one
condition. The explanation belongs beside the crossing, not inside its grid.

Constraints: the field is optional and additive; axis declarations are untouched;
a crossing without a description renders byte-identically to today.

## Goals / Non-Goals

**Goals:**

- One place per crossing to record what its levels mean, in the config the
  author is already reading.
- That prose reaches the report next to the table that uses the level names.
- The axis maps stay one line per level.

**Non-Goals:**

- Per-level labels, aliases, or any change to how a level is named or matched.
- Structured description (per-axis or per-level sub-fields). It is one prose
  string; imposing structure would recreate the per-level form this change
  declined.
- Any use of the description in conditions, cell names, or statistics.
- Rendering the description in the contrast or burden sections.

## Decisions

### One optional prose field on the crossing

`FactorialCrossing` gains `description: str | None = None`, and the config
accepts `description` as a fourth crossing key alongside `rows`, `columns`,
`label`, and `baseline`. It is validated exactly as `label` is: a non-empty
string when provided, rejected otherwise, with the error identifying the
crossing by `factorials[<i>]`.

*Why a free string over a structured map:* a map of level name to gloss is the
per-level form wearing a different hat — it re-introduces the drift and
subset-validation problems (a gloss for a level that does not exist) and splits
one explanation into fragments that each have to stand alone. A single paragraph
can say what the axes are, what distinguishes their levels, and why the crossing
is worth running, which is what the reader who forgot `bw_neutral` actually
needs.

### Rendered once, under the matrix

The description renders as a prose line directly beneath the crossing's matrix
section heading, before the table. The matrix is where every level name of the
crossing appears together, so it is the one place the explanation covers the
whole grid at once.

It is deliberately not repeated in the within-stratum contrast sections or the
burden-ranking section. Those are titled by the same crossing label, so a reader
has an unambiguous anchor back to the matrix, and repeating a paragraph three
times per crossing would cost more than it explains.

*Why below the heading rather than in it:* the heading is the crossing's label
and the join key a reader uses to line up the matrix, contrast, and burden
sections; appending prose to it would break that.

### JSON carries it on the matrix record

`FactorialMatrixResult` gains `description: str | None`, defaulting to `None`
and serialized with the rest of the record. Consumers that ignore it are
unaffected.

*Why not a top-level `factorials` metadata block:* the matrix record is already
the per-crossing object in the payload, keyed by the same effective label; a
parallel block would be a second thing to keep in sync.

### The stale spec scenario is corrected in the same delta

`factorial-regime-declaration`'s unknown-crossing-key scenario still lists only
`rows`, `columns`, and `label` as allowed keys, but `baseline` has been accepted
since the burden-ranking work. This change touches the allowed-key set anyway,
so the scenario is corrected here rather than left to drift further.

## Risks / Trade-offs

- **Prose can go stale when levels are renamed.** Nothing validates that a
  description still describes the axes. → Accepted: this is the cost of the
  compactness the per-level form would have bought back. The description sits
  directly above the axis maps it describes, so a renaming edit has it on
  screen.

- **A long description bloats the report.** → It renders once per crossing, as
  one paragraph, in a section that already carries a full matrix table.

- **A reader in the burden section has to scroll back to the matrix.** → The
  crossing label anchors both sections; duplicating the paragraph was judged the
  worse trade.

## Migration Plan

No data migration. Existing configs parse and render unchanged; adding a
description is opt-in per crossing. Rollback is reverting the commit — no
persisted artifact records a description.

## Open Questions

None. The example's description text is fixed by the level semantics recorded in
the proposal.
