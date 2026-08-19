"""Coalition scores in regime and factorial-axis conditions.

`coalition_score('<player>')` exposes the Shapley game's characteristic
function ``v(S)`` to conditions: the error a row would still carry if only the
named players were as observed and every other player were ideal. These tests
pin its semantics, its static validation, and the fact that a condition and the
attribution never disagree about what a coalition costs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from contribution import Estimator, cli
from contribution.spec import (
    AttributionSpec,
    FactorialCrossing,
    FeatureGroup,
    PredictionFeature,
    Regime,
)

_FORMULA = "class_sf + round(2 * log2(measured_bw / class_bw))"


def _rows() -> list[dict[str, object]]:
    """Four rows, each isolating a different coalition outcome.

    Rows 0-2 use the manuscript's worked example (true signal 812 kHz, SF 8).
    Row 3 is drawn from the bundled dataset and is the interesting one: the
    class is 23% too wide and the measurement 24% too wide, so each player
    alone shifts the estimate by one SF step in opposite directions and the two
    cancel exactly.
    """
    return [
        # class alone is wrong (7, not 8); the bandwidth is measured perfectly
        {"GT SF": 8, "GT BW": 812.0, "Class SF": 8, "Class BW": 1000.0, "Measured BW": 812.0, "Measured SF": 7},
        # class is nominally wrong but the regression rescues it
        {"GT SF": 8, "GT BW": 812.0, "Class SF": 9, "Class BW": 1000.0, "Measured BW": 812.0, "Measured SF": 8},
        # the measurement alone is wrong; the class is perfect
        {"GT SF": 8, "GT BW": 812.0, "Class SF": 8, "Class BW": 812.0, "Measured BW": 1150.0, "Measured SF": 9},
        # both are wrong and cancel: 11 from the class, 13 from the measurement, 12 together
        {"GT SF": 12, "GT BW": 101562.0, "Class SF": 12, "Class BW": 125000.0, "Measured BW": 125865.46, "Measured SF": 12},
    ]


def _spec(
    *,
    regimes: dict[str, str] | None = None,
    grouped: bool = True,
    score_mode: str = "absolute",
    factorials: list[FactorialCrossing] | None = None,
) -> AttributionSpec:
    spec = AttributionSpec(
        target="col('GT SF')",
        prediction="col('Measured SF')",
        prediction_expr=_FORMULA,
        prediction_features={
            "class_sf": PredictionFeature(actual="col('Class SF')", baseline="col('GT SF')"),
            "class_bw": PredictionFeature(actual="col('Class BW')", baseline="col('GT BW')"),
            "measured_bw": PredictionFeature(actual="col('Measured BW')", baseline="col('GT BW')"),
        },
        regimes=[
            Regime(name=name, condition=condition)
            for name, condition in (regimes or {"all": "1 == 1"}).items()
        ],
        factorials=factorials or [],
        score_mode=score_mode,
    )
    if grouped:
        spec.feature_groups = {"class": FeatureGroup(members=("class_sf", "class_bw"))}
    return spec


def _table(spec: AttributionSpec, rows: list[dict[str, object]] | None = None):
    """Build the coalition-score table the way ``assess`` does."""
    estimator = Estimator.from_dataframe(rows if rows is not None else _rows(), spec)
    estimator._validate_spec()
    features = estimator._formula_features()
    players = estimator._build_players(features)
    feature_player = {
        name: player.name for player in players for name in player.feature_names
    }
    coalitions = estimator._referenced_coalitions(players)
    return estimator, features, feature_player, estimator._coalition_score_table(
        features, feature_player, coalitions
    )


def _counts(spec: AttributionSpec) -> dict[str, int]:
    result = Estimator.from_dataframe(_rows(), spec).assess()
    return {item.name: item.regime.count for item in result.regimes if item.analysis == "regime"}


# --- semantics ---------------------------------------------------------------


def test_single_player_coalition_isolates_one_decision() -> None:
    _, _, _, table = _table(
        _spec(regimes={"cls": "coalition_score('class') != 0", "bw": "coalition_score('measured_bw') != 0"})
    )
    assert table[frozenset({"class"})] == [1.0, 0.0, 0.0, 1.0]
    assert table[frozenset({"measured_bw"})] == [0.0, 0.0, 1.0, 1.0]


def test_multi_player_coalition_sees_two_errors_cancel() -> None:
    """Row 3 scores 1 for each player alone but 0 for the two together."""
    _, _, _, table = _table(_spec(regimes={"both": "coalition_score('class', 'measured_bw') == 0"}))
    assert table[frozenset({"class", "measured_bw"})] == [1.0, 0.0, 1.0, 0.0]


def test_full_coalition_equals_the_observed_error() -> None:
    estimator, features, _, table = _table(
        _spec(regimes={"both": "coalition_score('class', 'measured_bw') != 0"})
    )
    observed = [estimator._observed_contribution(row, features) for row in estimator.rows]
    assert table[frozenset({"class", "measured_bw"})] == observed


def test_empty_coalition_is_expressible_and_scores_zero() -> None:
    _, _, _, table = _table(_spec(regimes={"broken": "coalition_score() != 0"}))
    assert table[frozenset()] == [0.0, 0.0, 0.0, 0.0]
    assert _counts(_spec(regimes={"broken": "coalition_score() != 0"}))["broken"] == 0


def test_empty_coalition_exposes_a_baseline_that_misses_the_target() -> None:
    """A baseline pinned to an observed column shifts the origin of every score."""
    spec = _spec(regimes={"broken": "coalition_score() != 0"})
    spec.prediction_features["class_bw"] = PredictionFeature(
        actual="col('Class BW')", baseline="col('Class BW')"
    )
    _, _, _, table = _table(spec)
    assert any(value != 0.0 for value in table[frozenset()])


def test_condition_sees_the_same_score_as_the_estimators_own_scorer() -> None:
    spec = _spec(
        regimes={"cls": "coalition_score('class') != 0", "bw": "coalition_score('measured_bw') != 0"}
    )
    estimator, features, feature_player, table = _table(spec)
    for coalition, values in table.items():
        for row_index, row in enumerate(estimator.rows):
            score = estimator._row_scorer(row, features, feature_player)
            assert values[row_index] == score(coalition)


def test_regimes_select_the_rows_the_scores_identify() -> None:
    counts = _counts(
        _spec(
            regimes={
                "class_unworkable": "coalition_score('class') != 0",
                "bw_shifts": "coalition_score('measured_bw') != 0",
                "cancelling": "coalition_score('class') != 0 and coalition_score('class', 'measured_bw') == 0",
            }
        )
    )
    assert counts["class_unworkable"] == 2
    assert counts["bw_shifts"] == 2
    assert counts["cancelling"] == 1


def test_a_declared_regime_and_a_factorial_level_agree() -> None:
    condition = "coalition_score('class') != 0"
    counts = _counts(
        _spec(
            regimes={"declared": condition},
            factorials=[
                FactorialCrossing(
                    label="Decision",
                    rows={"workable": "coalition_score('class') == 0", "unworkable": condition},
                    columns={"any": "1 == 1"},
                )
            ],
        )
    )
    assert counts["declared"] == counts["unworkable & any"] == 2


def test_a_coalition_scored_axis_partitions_without_warning() -> None:
    spec = _spec(
        factorials=[
            FactorialCrossing(
                label="Decision",
                rows={
                    "workable": "coalition_score('class') == 0",
                    "unworkable": "coalition_score('class') != 0",
                },
                columns={
                    "neutral": "coalition_score('measured_bw') == 0",
                    "shifts": "coalition_score('measured_bw') != 0",
                },
            )
        ]
    )
    result = Estimator.from_dataframe(_rows(), spec).assess()
    assert result.partition_warnings == []
    counts = {item.name: item.regime.count for item in result.regimes if item.analysis == "regime"}
    assert counts["workable & neutral"] == 1
    assert counts["workable & shifts"] == 1
    assert counts["unworkable & neutral"] == 1
    assert counts["unworkable & shifts"] == 1


# --- score mode --------------------------------------------------------------


def test_signed_mode_yields_a_directional_axis() -> None:
    _, _, _, table = _table(
        _spec(
            regimes={
                "over": "coalition_score('measured_bw') > 0",
                "under": "coalition_score('class') < 0",
            },
            score_mode="signed",
        )
    )
    # Row 0's class drags the estimate down one step; row 2's measurement
    # pushes it up one step.
    assert table[frozenset({"class"})] == [-1.0, 0.0, 0.0, -1.0]
    assert table[frozenset({"measured_bw"})] == [0.0, 0.0, 1.0, 1.0]


def test_absolute_mode_never_yields_a_negative_score() -> None:
    spec = _spec(regimes={"under": "coalition_score('class') < 0"})
    _, _, _, table = _table(spec)
    assert all(value >= 0.0 for values in table.values() for value in values)
    assert _counts(spec)["under"] == 0


# --- cost bound --------------------------------------------------------------


def test_only_referenced_coalitions_are_scored(monkeypatch: pytest.MonkeyPatch) -> None:
    """Three players, two referenced coalitions: two resolutions per row."""
    spec = _spec(
        grouped=False,
        regimes={
            "sf": "coalition_score('class_sf') != 0",
            "bw": "coalition_score('measured_bw') != 0",
        },
    )
    estimator = Estimator.from_dataframe(_rows(), spec)
    estimator._validate_spec()
    features = estimator._formula_features()
    players = estimator._build_players(features)
    assert len(players) == 3

    coalitions = estimator._referenced_coalitions(players)
    assert coalitions == {frozenset({"class_sf"}), frozenset({"measured_bw"})}

    calls: list[frozenset[str]] = []
    original = Estimator._resolve_coalition_values

    def counting(self, row, feats, subset, actual_values, feature_player=None):
        calls.append(subset)
        return original(self, row, feats, subset, actual_values, feature_player)

    monkeypatch.setattr(Estimator, "_resolve_coalition_values", counting)
    estimator._coalition_score_table(features, {name: name for name in ("class_sf", "class_bw", "measured_bw")}, coalitions)
    assert len(calls) == 2 * len(estimator.rows)


def test_a_coalition_repeated_across_conditions_is_scored_once_per_row() -> None:
    spec = _spec(
        regimes={"a": "coalition_score('class') != 0", "b": "coalition_score('class') == 0"},
        factorials=[
            FactorialCrossing(
                label="Decision",
                rows={
                    "workable": "coalition_score('class') == 0",
                    "unworkable": "coalition_score('class') != 0",
                },
                columns={"any": "1 == 1"},
            )
        ],
    )
    _, _, _, table = _table(spec)
    assert set(table) == {frozenset({"class"})}


# --- static validation -------------------------------------------------------


def _assess(spec: AttributionSpec):
    return Estimator.from_dataframe(_rows(), spec).assess()


def test_unknown_player_names_the_condition_and_the_valid_players() -> None:
    with pytest.raises(ValueError) as excinfo:
        _assess(_spec(regimes={"bad": "coalition_score('clas') != 0"}))
    message = str(excinfo.value)
    assert "regime 'bad'" in message
    assert "'clas'" in message
    assert "Valid players: class, measured_bw" in message


def test_unknown_player_in_a_factorial_level_names_the_axis_and_level() -> None:
    spec = _spec(
        factorials=[
            FactorialCrossing(
                label="Decision",
                rows={"a": "coalition_score('nope') == 0", "b": "1 == 0"},
                columns={"any": "1 == 1"},
            )
        ]
    )
    with pytest.raises(ValueError, match=r"factorial 'Decision' rows level 'a' names unknown player 'nope'"):
        _assess(spec)


def test_group_member_is_rejected_in_favour_of_the_group() -> None:
    with pytest.raises(ValueError) as excinfo:
        _assess(_spec(regimes={"bad": "coalition_score('class_sf') != 0"}))
    message = str(excinfo.value)
    assert "member of feature group 'class'" in message
    assert "Name the group instead" in message


def test_ungrouped_feature_is_addressable_by_its_own_name() -> None:
    counts = _counts(_spec(grouped=False, regimes={"sf": "coalition_score('class_sf') != 0"}))
    assert counts["sf"] == 1


def test_repeated_player_in_one_call_is_rejected() -> None:
    with pytest.raises(ValueError, match="names player 'class' more than once"):
        _assess(_spec(regimes={"bad": "coalition_score('class', 'class') != 0"}))


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("target", "col('GT SF') + coalition_score('class')", "target expression"),
        ("prediction", "col('Measured SF') + coalition_score('class')", "prediction expression"),
        (
            "prediction_expr",
            "class_sf + round(2 * log2(measured_bw / class_bw)) + coalition_score('class')",
            "prediction_expr",
        ),
    ],
)
def test_coalition_score_is_rejected_in_the_expressions_that_define_the_game(
    field: str, value: str, expected: str
) -> None:
    spec = _spec()
    setattr(spec, field, value)
    with pytest.raises(ValueError) as excinfo:
        _assess(spec)
    message = str(excinfo.value)
    assert expected in message
    assert "not permitted there" in message


@pytest.mark.parametrize("part", ["actual", "baseline"])
def test_coalition_score_is_rejected_in_a_feature_expression(part: str) -> None:
    spec = _spec()
    replacement = {"actual": "col('Class SF')", "baseline": "col('GT SF')"}
    replacement[part] = f"{replacement[part]} + coalition_score('measured_bw')"
    spec.prediction_features["class_sf"] = PredictionFeature(**replacement)
    with pytest.raises(ValueError) as excinfo:
        _assess(spec)
    assert f"prediction feature 'class_sf' {part} expression" in str(excinfo.value)
    assert "not permitted there" in str(excinfo.value)


def test_validation_runs_before_any_row_is_read() -> None:
    """An empty dataset still rejects a misspelled player."""
    with pytest.raises(ValueError, match="unknown player 'nope'"):
        Estimator(rows=[], spec=_spec(regimes={"bad": "coalition_score('nope') != 0"})).assess()


# --- the shipped example -----------------------------------------------------
#
# The bundled config's decision crossing is pinned so its numbers are
# regression-protected the way the pre-change goldens protect the originals.

_ROOT = Path(__file__).resolve().parents[2]
_GOLDEN_DECISION = _ROOT / "tests" / "fixtures" / "golden_continuous_lora_decision_crossing.json"
_LIVE_CONFIG = _ROOT / "examples" / "continuous_lora" / "config.json"
_MEASUREMENTS = _ROOT / "examples" / "continuous_lora" / "measurements.csv"
_DECISION_CROSSING = "Class decision"


@pytest.fixture(scope="module")
def example_result():
    return Estimator.from_csv(_MEASUREMENTS, cli._load_spec(_LIVE_CONFIG)).assess()


@pytest.fixture(scope="module")
def decision_golden() -> dict:
    return json.loads(_GOLDEN_DECISION.read_text(encoding="utf-8"))


def test_example_decision_crossing_matrix_matches_its_golden(example_result, decision_golden) -> None:
    matrix = next(m for m in example_result.factorial_matrices if _DECISION_CROSSING in m.label)
    actual = {
        cell.name: {
            "count": cell.count,
            "mismatch_rate_pct": cell.mismatch_rate_pct,
            "risk_ratio": cell.risk_ratio,
        }
        for cell in matrix.cells
    }
    assert actual == decision_golden["cells"]


def test_example_decision_crossing_burden_matches_its_golden(example_result, decision_golden) -> None:
    ranking = next(r for r in example_result.burden_rankings if _DECISION_CROSSING in r.crossing_label)
    assert ranking.baseline_cell == decision_golden["baseline_cell"]
    assert ranking.ceiling_accuracy_pct == decision_golden["ceiling_accuracy_pct"]
    actual = [
        {
            "rank": entry.rank,
            "cell": entry.cell,
            "count": entry.count,
            "mismatch_rate_pct": entry.mismatch_rate_pct,
            "recoverable_mismatches": entry.recoverable_mismatches,
            "cumulative_accuracy_if_eliminated_pct": entry.cumulative_accuracy_if_eliminated_pct,
        }
        for entry in ranking.entries
    ]
    assert actual == decision_golden["ranking"]


def test_example_coalition_scored_regime_counts_the_unworkable_rows(example_result) -> None:
    """The two unworkable cells partition the rows the regime selects."""
    counts = {
        item.name: item.regime.count
        for item in example_result.regimes
        if item.analysis == "regime" and item.regime is not None
    }
    assert counts["class_unworkable"] == 95
    assert counts["class_unworkable & bw_neutral"] + counts["class_unworkable & bw_shifts"] == 95
