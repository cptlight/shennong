"""Path and configuration resolution for SHENNONG.

Library code never hardcodes the fixture path: callers pass ``--corpus-dir`` (CLI) or
set ``SHENNONG_CORPUS_DIR``; otherwise the default is the real processed corpus at
``<repo>/corpus/processed``.  Tests and the eval harness pass the fixture path
explicitly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Where derived artefacts live.  This directory is owned by discovery-engine and is
#: meant to be disposable/regenerable; the real data contract stays corpus/processed.
BUILD_ROOT = REPO_ROOT / "shennong" / "_build"


def default_corpus_dir() -> Path:
    env = os.environ.get("SHENNONG_CORPUS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return REPO_ROOT / "corpus" / "processed"


@dataclass(frozen=True)
class CorpusPaths:
    """Resolved paths to the processed-corpus data contracts (brief §10)."""

    root: Path

    @classmethod
    def resolve(cls, corpus_dir: str | Path | None = None) -> "CorpusPaths":
        if corpus_dir is None:
            return cls(default_corpus_dir())
        return cls(Path(corpus_dir).expanduser().resolve())

    # ---- raw text -------------------------------------------------------------------
    @property
    def corpus_jsonl(self) -> Path:
        return self.root / "corpus.jsonl"

    @property
    def registry_yaml(self) -> Path:
        return self.root.parent / "registry" / "sources.yaml"

    # ---- lexicons -------------------------------------------------------------------
    @property
    def lexicon_drugs(self) -> Path:
        return self.root / "lexicon_drugs.json"

    # ---- structured data ------------------------------------------------------------
    @property
    def structured_dir(self) -> Path:
        return self.root / "structured"

    @property
    def plants_csv(self) -> Path:
        return self.structured_dir / "plants.csv"

    @property
    def compounds_csv(self) -> Path:
        return self.structured_dir / "compounds.csv"

    @property
    def uses_csv(self) -> Path:
        return self.structured_dir / "uses.csv"

    @property
    def formulas_csv(self) -> Path:
        return self.structured_dir / "formulas.csv"

    @property
    def formula_ingredients_csv(self) -> Path:
        return self.structured_dir / "formula_ingredients.csv"

    @property
    def incompatibilities_csv(self) -> Path:
        return self.structured_dir / "incompatibilities.csv"

    @property
    def processing_csv(self) -> Path:
        return self.structured_dir / "processing.csv"

    # ---- derived --------------------------------------------------------------------
    @property
    def build_dir(self) -> Path:
        return BUILD_ROOT / "kg"

    def is_fixture(self) -> bool:
        """True when running on the test-fixture corpus, so outputs can be labelled."""
        return "fixtures" in str(self.root)

    def missing_required(self) -> list[str]:
        """Files a real corpus must provide for the pipeline to run meaningfully."""
        required = [self.corpus_jsonl, self.plants_csv, self.compounds_csv, self.uses_csv]
        return [str(p) for p in required if not p.exists()]

    def require(self) -> "CorpusPaths":
        missing = self.missing_required()
        if missing:
            raise FileNotFoundError(
                "processed corpus incomplete; missing: " + ", ".join(missing) +
                "\nPass --corpus-dir /path/to/corpus/processed (or set SHENNONG_CORPUS_DIR)."
            )
        return self
