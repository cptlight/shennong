"""Shared pytest fixtures.

Tests run against the fixture corpus under ``tests/fixtures/corpus/processed``; the
library itself never hardcodes that path (it takes ``--corpus-dir`` / ``CorpusPaths``).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURE_CORPUS = ROOT / "tests" / "fixtures" / "corpus" / "processed"

from shennong.config import CorpusPaths  # noqa: E402
from shennong.discover.common import SpanIndex  # noqa: E402
from shennong.extract.extract import load_corpus  # noqa: E402
from shennong.extract.lexicons import build_lexicons  # noqa: E402
from shennong.kg.build import build_graph  # noqa: E402


@pytest.fixture(scope="session")
def paths() -> CorpusPaths:
    return CorpusPaths.resolve(FIXTURE_CORPUS)


@pytest.fixture(scope="session")
def docs(paths):
    return load_corpus(paths.corpus_jsonl)


@pytest.fixture(scope="session")
def lex(paths):
    return build_lexicons(paths)


@pytest.fixture(scope="session")
def graph(paths, lex):
    return build_graph(paths, lex)


@pytest.fixture(scope="session")
def spans(docs):
    return SpanIndex(docs)


@pytest.fixture(scope="session")
def discovery(paths):
    from shennong.discover.ranking import run_discovery

    return run_discovery(paths)
