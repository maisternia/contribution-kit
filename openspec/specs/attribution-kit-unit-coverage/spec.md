# attribution-kit-unit-coverage Specification

## Purpose

Define requirements for contribution-kit unit-test location, isolation, and strict 100% line and branch coverage gating.

## Requirements

### Requirement: Unit tests reside in the contribution-kit submodule

The unit-test layer for the `contribution` package SHALL live inside the submodule at
`external/contribution-kit/tests/unit/`, and MUST NOT be placed in the parent
`ResearchData/tests/` tree. Integration/accuracy tests MUST NOT be placed in the submodule
unit tree.

#### Scenario: Unit tests are located in the submodule

- **WHEN** the repository is inspected after this change
- **THEN** every unit test for a `contribution` module exists under
  `external/contribution-kit/tests/unit/`
- **AND** no unit test for a `contribution` module exists under `ResearchData/tests/`

### Requirement: Complete line and branch coverage of the contribution package

The unit-test layer SHALL achieve 100% line coverage and 100% branch coverage of every
module in `external/contribution-kit/src/contribution/` (`__init__`, `stats`, `expr`,
`spec`, `hypothesis`, `estimator`, `results`, `contributor`, `cli`). Any line excluded from
coverage MUST carry an explicit, justified `# pragma: no cover` and MUST be limited to
genuinely unreachable or environment-guard code (for example the `__main__` guard).

#### Scenario: Coverage gate passes at 100%

- **WHEN** the unit suite is run with branch coverage over the `contribution` package
- **THEN** the measured line coverage is 100% and the measured branch coverage is 100%
- **AND** the run exits successfully under a `--cov-fail-under=100` threshold

#### Scenario: Coverage gate fails when a line becomes uncovered

- **WHEN** a reachable source line in `contribution` is not exercised by any unit test
- **THEN** the coverage run reports below 100% and exits non-zero

#### Scenario: Only justified exclusions are permitted

- **WHEN** a `# pragma: no cover` marker appears in `contribution` source
- **THEN** it annotates only unreachable or environment-guard code and is accompanied by a
  justification

### Requirement: Unit tests exercise units in isolation

Each unit test SHALL exercise a single unit through its own public surface with controlled,
minimal inputs so that every covered line is reached deliberately. Unit tests MUST NOT
depend on the project's realistic fixtures or on the parent repository's measurement CSVs to
obtain coverage, and units performing file I/O MUST be driven with temporary paths and small
in-memory inputs.

#### Scenario: Coverage is reached intentionally, not incidentally

- **WHEN** a source branch, `raise`, or edge case (zero cell, sparse cell, boundary support,
  exact vs. sampled Shapley, each `ci_method`) is covered
- **THEN** a specific unit test targets that path directly rather than reaching it only
  through an unrelated end-to-end run

#### Scenario: I/O units use temporary paths

- **WHEN** a unit that reads or writes files (for example `Estimator.from_csv`,
  `AssessmentResult.to_csv`/`to_json`/`save`, or `cli.main`) is tested
- **THEN** the test uses a temporary directory and small in-memory input
- **AND** the test does not read the parent repository's measurement CSVs

### Requirement: Coverage tooling and gate are configured in the submodule

The submodule SHALL declare its test tooling (`pytest` and a coverage tool such as
`coverage`/`pytest-cov`) and its coverage gate in `external/contribution-kit/pyproject.toml`
without adding any runtime dependency to the `contribution` package. A single documented
command SHALL run the unit suite with the branch-coverage gate.

#### Scenario: Runtime dependencies remain empty

- **WHEN** the submodule `pyproject.toml` is inspected after this change
- **THEN** test tooling is declared under an optional/dev dependency group
- **AND** the package's runtime `dependencies` list remains empty

#### Scenario: Documented command runs the gated unit suite

- **WHEN** the documented unit-test command is executed from the submodule
- **THEN** it runs `tests/unit` with branch coverage over `contribution` and enforces the
  100% threshold

### Requirement: Production source behavior is unchanged

This change SHALL NOT alter the runtime behavior or public API of any
`contribution` source module. If achieving coverage reveals a genuine defect, the fix MUST
be called out separately rather than bundled silently into test work.

#### Scenario: No source behavior change

- **WHEN** the change is reviewed
- **THEN** `contribution` source files contain only additive coverage-neutral edits (such as
  justified `# pragma: no cover`) or a separately-documented defect fix
- **AND** no public function signature or documented behavior is modified without an explicit
  note
