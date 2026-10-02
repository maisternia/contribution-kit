"""Merge the R reference values with the high-precision odds-ratio reference.

Run from the repository root after the R generator:

    Rscript tests/reference/generate_effect_size_baselines.R
    python tests/reference/generate_effect_size_baselines.py

Writes tests/reference/effect_size_baselines.json. Imports nothing from the
kit: every value comes from R or from hp_exact_or.py, and each high-precision
odds-ratio interval carries its agreement with an unrelated implementation.
"""

from __future__ import annotations

import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import mpmath
import numpy
import scipy
from scipy.stats.contingency import odds_ratio

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from hp_exact_or import exact_or_interval  # noqa: E402

ALPHA = 0.05
# Agreement each cross-check must reach with the high-precision value: exact2x2
# and SciPy solve to ~1e-8 relative; contingencytables uses uniroot with an
# absolute tolerance of 1e-7, so its small bounds are only good to ~1e-4.
CROSS_CHECK_TOLERANCES = {
    "exact2x2_minlike": 1e-6,
    "scipy_conditional": 1e-6,
    "contingencytables_midp": 1e-4,
}
HP_AUTHORITY = "tests/reference/hp_exact_or.py (mpmath, 60 digits)"


def _number(value):
    if value is None:
        return None
    if isinstance(value, str):
        return math.inf if value == "inf" else -math.inf
    return float(value)


def _encode(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, float) and math.isinf(value):
        return "inf" if value > 0 else "-inf"
    return value


def _rel_diff(expected: float, actual: float) -> float:
    if math.isinf(expected) or math.isinf(actual) or expected == 0 or actual == 0:
        return 0.0 if expected == actual else math.inf
    return abs(actual - expected) / abs(expected)


def _odds_ratio_value(a: int, b: int, c: int, d: int) -> float | None:
    numerator, denominator = a * d, b * c
    if denominator == 0:
        return None if numerator == 0 else math.inf
    return numerator / denominator


def _cross_check(source: str, low: float, high: float, other_low, other_high, has_gaps: bool) -> dict | None:
    if other_low is None or other_high is None:
        return None
    other_low, other_high = _number(other_low), _number(other_high)
    check = {"source": source, "ci_low": _encode(other_low), "ci_high": _encode(other_high)}
    if has_gaps and source == "contingencytables_midp":
        # contingencytables brackets one root with uniroot, which on a set with
        # gaps can land on an inner end instead of the hull's.
        check["skipped"] = "confidence set has gaps; contingencytables reports an inner end, not the hull"
        return check
    check["max_rel_diff"] = _encode(max(_rel_diff(low, other_low), _rel_diff(high, other_high)))
    check["tolerance"] = CROSS_CHECK_TOLERANCES[source]
    return check


def _scipy_conditional(a: int, b: int, c: int, d: int) -> tuple[float, float] | None:
    if a + c == 0 or b + d == 0:
        return None
    interval = odds_ratio([[a, b], [c, d]], kind="conditional").confidence_interval(1 - ALPHA)
    return float(interval.low), float(interval.high)


def _r_interval(entry: dict, authority: str) -> dict:
    return {
        "value": entry["value"],
        "ci_low": entry["ci_low"],
        "ci_high": entry["ci_high"],
        "authority": authority,
    }


def build() -> dict:
    r_values = json.loads((HERE / "r_effect_size_values.json").read_text())
    r_calls = r_values["provenance"]["calls"]
    cases = []
    for case in r_values["cases"]:
        a, b, c, d = (int(case[key]) for key in "abcd")
        value = _encode(_odds_ratio_value(a, b, c, d))
        out = {key: case[key] for key in ("set", "label", "a", "b", "c", "d")}
        out["koopman"] = _r_interval(case["koopman"], r_calls["koopman"])
        out["katz"] = _r_interval(case["katz"], r_calls["katz"])
        out["haldane_anscombe"] = _r_interval(case["haldane_anscombe"], r_calls["haldane_anscombe"])

        cross_sources = {
            "baptista-pike": ("exact2x2_minlike", case["exact2x2_minlike"]),
            "baptista-pike-midp": ("contingencytables_midp", case["contingencytables_midp"]),
        }
        scipy_interval = _scipy_conditional(a, b, c, d)
        for method, key in (
            ("baptista-pike", "baptista_pike"),
            ("baptista-pike-midp", "baptista_pike_midp"),
            ("cornfield", "cornfield"),
        ):
            low, high, has_gaps = exact_or_interval(a, b, c, d, method, alpha=ALPHA)
            if method == "cornfield":
                other = None if scipy_interval is None else {"ci_low": scipy_interval[0], "ci_high": scipy_interval[1]}
                source = "scipy_conditional"
            else:
                source, other = cross_sources[method]
            check = None if other is None else _cross_check(source, low, high, other["ci_low"], other["ci_high"], has_gaps)
            out[key] = {
                "value": value,
                "ci_low": _encode(low),
                "ci_high": _encode(high),
                "set_has_gaps": has_gaps,
                "authority": HP_AUTHORITY,
                "cross_check": check,
            }
        cases.append(out)

    provenance = {
        "generators": [
            "tests/reference/generate_effect_size_baselines.R",
            "tests/reference/generate_effect_size_baselines.py",
            "tests/reference/hp_exact_or.py",
        ],
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "conf_level": 1 - ALPHA,
        "r": r_values["provenance"],
        "python": {
            "python": platform.python_version(),
            "mpmath": mpmath.__version__,
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
        },
        "high_precision_or": {
            "module": "tests/reference/hp_exact_or.py",
            "digits": mpmath.mp.dps,
            "tie_tolerance": 1e-7,
            "interval": "hull of the confidence set",
        },
        "cross_check_tolerances": CROSS_CHECK_TOLERANCES,
    }
    return {"provenance": provenance, "cases": cases}


def main() -> None:
    baselines = build()
    failures = [
        (case["a"], case["b"], case["c"], case["d"], key, check["source"], check["max_rel_diff"])
        for case in baselines["cases"]
        for key in ("baptista_pike", "baptista_pike_midp", "cornfield")
        if (check := case[key]["cross_check"]) is not None
        and "skipped" not in check
        and (check["max_rel_diff"] is None or _number(check["max_rel_diff"]) > check["tolerance"])
    ]
    out_path = HERE / "effect_size_baselines.json"
    out_path.write_text(json.dumps(baselines, indent=2) + "\n")
    print(f"Wrote {out_path}")
    for failure in failures:
        print("cross-check outside tolerance:", failure)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
