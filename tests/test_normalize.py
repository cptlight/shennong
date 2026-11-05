"""Orthography normalisation: long-s, 繁/简, IAST, Arabic, offsets."""

from shennong.normalize import (
    fold_arabic,
    fold_iast,
    fold_zh,
    jaccard,
    normalise,
    normalise_offsets,
    tokenize,
)


def test_long_s_is_folded_and_offsets_preserved():
    text = "The ſeeds of the plant"
    out = normalise_offsets(text)
    assert "ſ" not in out
    assert "seeds" in out
    assert len(out) == len(text)


def test_traditional_folds_to_simplified_length_preserving():
    assert fold_zh("大黃") == "大黄"
    assert fold_zh("炮製") == "炮制"
    text = "甘草，味甘平。大黃，味苦寒"
    out = normalise_offsets(text)
    assert len(out) == len(text)
    assert "大黄" in out


def test_iast_diacritics_are_stripped_for_matching():
    assert fold_iast("śodhanaṃ") == "sodhanam"
    assert "sodhana" in normalise("śodhanaṃ doṣa-nāśanam")


def test_arabic_letter_folding():
    assert fold_arabic("\u0623\u0644\u0633\u0648\u0633") == "\u0627\u0644\u0633\u0648\u0633"
    assert len(normalise_offsets("السوس")) == len("السوس")


def test_tokenize_handles_cjk_and_latin():
    tokens = tokenize("甘草 ginseng")
    assert "甘" in tokens and "草" in tokens
    assert "ginseng" in tokens


def test_jaccard_similarity_bounds():
    assert jaccard("甘草", "甘草") == 1.0
    assert jaccard("甘草", "大黃") < 0.5


def test_normalise_offsets_rejects_removal():
    # ḥarakāt are removed by full normalise() but kept by the offset-preserving path
    text = "حارّ"
    assert len(normalise_offsets(text)) == len(text)
