"""End-to-end CLI on the fixture corpus."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "corpus" / "processed"
PYTHON = sys.executable


def run_cli(*args, env_extra=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    result = subprocess.run(
        [PYTHON, "-m", "shennong.cli", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )
    return result


def test_cai_json(paths=None):
    result = run_cli("cai", "--corpus-dir", str(FIXTURE), "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["documents"] >= 20


def test_zhi_extracts_entities():
    result = run_cli("zhi", "--corpus-dir", str(FIXTURE), "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["entities"] > 50


def test_pei_writes_workbench_kg(tmp_path):
    out = tmp_path / "kg.json"
    result = run_cli("pei", "--corpus-dir", str(FIXTURE), "--out-kg", str(out), "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["nodes"] and data["edges"]
    assert {"id", "label", "type", "weight"} <= set(data["nodes"][0])


def test_shi_writes_hypotheses(tmp_path):
    out = tmp_path / "hyp.json"
    env = {"SHENNONG_ARTIFACTS_DIR": str(tmp_path / "artifacts")}
    result = run_cli("shi", "--corpus-dir", str(FIXTURE), "--n", "10", "--out", str(out), "--json", env_extra=env)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["n"] >= 10
    assert data["corpus_hash"]
    assert data["hypotheses"][0]["scores"]["composite"] >= 0


def test_ask_json_refuses_unanswerable():
    result = run_cli("ask", "What did Culpeper write about rosemary?", "--corpus-dir", str(FIXTURE), "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["refused"] is True
    assert payload["refusal_reason"]


def test_report_writes_schema(tmp_path):
    out = tmp_path / "report.json"
    env = {"SHENNONG_ARTIFACTS_DIR": str(tmp_path / "artifacts")}
    result = run_cli("report", "--corpus-dir", str(FIXTURE), "--out", str(out), "--json", env_extra=env)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    report = json.loads(out.read_text(encoding="utf-8"))
    for key in ("generated_at", "corpus", "resolution", "benchmarks", "hypotheses",
                "drug_discovery", "negative_controls", "ablations", "refusal_benchmark", "rules"):
        assert key in report, key
    assert report["fixture"] is True
    assert "theory_predictivity" in report["drug_discovery"]
