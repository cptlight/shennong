"""Continuous-learning round and active-learning selector."""

import json

from shennong.learn import loop
from shennong.learn.active import rank_documents


def test_round_records_before_after(paths, tmp_path, monkeypatch):
    monkeypatch.setattr(loop, "ROUNDS_DIR", tmp_path)
    payload = loop.round(paths, round_number=1)
    assert payload["artifact"]
    data = json.loads((tmp_path / "round-001.json").read_text(encoding="utf-8"))
    assert "baseline" in data and "candidates" in data
    assert data["candidates"]
    assert len(data["accepted"]) + len(data["rejected"]) == len(data["candidates"])
    for record in data["candidates"]:
        assert {"name", "target_metric", "scores", "decision", "reason"} <= set(record)
    assert data["outcome"]


def test_active_learning_ranking_is_sorted(paths):
    ranked = rank_documents(paths, limit=20)
    assert ranked
    values = [item.information_gain for item in ranked]
    assert values == sorted(values, reverse=True)
    for item in ranked:
        assert 0.0 <= item.novelty <= 1.0
        assert item.n_doc if hasattr(item, "n_doc") else True
