"""Asian property vectors and the predictivity tests."""

from shennong.theory.features import CHANNEL_ORGAN, load_features
from shennong.theory.predictivity import (
    control_ayurveda_rasa,
    control_quxiangbilei,
    theory_predictivity,
)


def test_features_load_from_structured_contracts(paths, lex):
    features = load_features(paths, lex)
    assert len(features.tcm) > 50
    assert len(features.ayurveda) > 20
    assert features.seven_relations


def test_compound_nature_terms_parse(paths, lex):
    features = load_features(paths, lex)
    ginseng = features.tcm.get("Panax ginseng")
    assert ginseng is not None
    assert ginseng.warmth == 0.0  # 平
    warm = features.tcm.get("Aconitum carmichaelii")
    assert warm is not None and warm.warmth is not None and warm.warmth > 1.0


def test_channel_organ_mapping():
    assert CHANNEL_ORGAN["肝"] == "liver"
    assert CHANNEL_ORGAN["腎"] == "kidney"


def test_virya_hot_cold_parsing(paths, lex):
    features = load_features(paths, lex)
    assert any(props.is_hot_virya is True for props in features.ayurveda.values())
    assert any(props.is_hot_virya is False for props in features.ayurveda.values())


def test_theory_predictivity_report_shape(graph, paths, lex):
    features = load_features(paths, lex)
    results = theory_predictivity(graph, features)
    for key in ("tcm_nature", "tcm_flavor", "tcm_channel", "ayurveda_virya", "tridosha"):
        block = results[key]
        assert block["metric"] in {"auc", "hit_rate", "rho", "overlap"}
        assert 0.0 <= block["p"] <= 1.0
        assert block["n"] >= 0


def test_negative_controls_are_reported(graph, paths, lex):
    features = load_features(paths, lex)
    quxiang = control_quxiangbilei(graph, features)
    rasa = control_ayurveda_rasa(graph, features)
    assert "n" in quxiang and "p" in quxiang
    assert "n" in rasa and "p" in rasa
    assert 0.0 <= quxiang["p"] <= 1.0
