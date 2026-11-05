"""Composite scoring monotonicity, uncertainty and falsification plans."""

from shennong.score import (
    DEFAULT_EXPONENTS,
    Factor,
    composite,
    falsification_plan,
    score_hypothesis,
    sensitivity,
)

F = Factor


def test_composite_monotone_in_each_factor():
    base = composite(0.5, 0.5, 0.5, 0.5)
    assert composite(0.6, 0.5, 0.5, 0.5) > base
    assert composite(0.5, 0.6, 0.5, 0.5) > base
    assert composite(0.5, 0.5, 0.6, 0.5) > base
    assert composite(0.5, 0.5, 0.5, 0.6) > base


def test_composite_is_bounded_and_symmetric_under_exponent_swap():
    product = composite(0.8, 0.6, 0.4, 0.2)
    swapped = composite(0.8, 0.6, 0.4, 0.2, exponents=(1, 1, 1, 1))
    assert 0.0 < product <= 1.0
    assert abs(product - swapped) < 1e-12
    # raising only the novelty exponent to 2 multiplies the product by novelty (0.8)
    assert abs(composite(0.8, 0.6, 0.4, 0.2, (2, 1, 1, 1)) - product * 0.8) < 1e-12


def test_uncertainty_interval_brackets_composite():
    score = score_hypothesis(F(0.7, 0.1, ""), F(0.6, 0.2, ""), F(0.8, 0.1, ""), F(0.5, 0.15, ""))
    lo, hi = score.composite_ci
    assert lo <= score.composite <= hi
    assert score.drivers


def test_sensitivity_rank_stability():
    scored = [
        {"id": "a", "factors": [0.9, 0.2, 0.9, 0.3]},
        {"id": "b", "factors": [0.2, 0.9, 0.5, 0.8]},
        {"id": "c", "factors": [0.5, 0.5, 0.5, 0.5]},
    ]
    result = sensitivity(scored)
    assert -1.0 <= result["mean_kendall_tau"] <= 1.0
    assert 0.0 <= result["mean_top5_overlap"] <= 1.0


def test_falsification_plans_are_safe_and_falsifiable():
    for klass in ("incompatibility", "processing", "name_collision", "formula_role",
                  "understudied", "endangered", "drug_candidate"):
        plan = falsification_plan(klass, {"drug": "x", "drug_modern": "X", "target_class": "t"})
        assert plan["experiment"] and plan["expected_if_true"] and plan["kill_criteria"]
        lowered = (plan["experiment"] + plan["kill_criteria"]).lower()
        for forbidden in ("mg/kg", " dose ", "administer to patients", "synthesise", "synthesize"):
            assert forbidden not in lowered
