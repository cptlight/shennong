"""SHENNONG — a first-principles ethnopharmacology discovery engine for the Asian canon.

Package layout (brief §4):

``ontology``   Tier-0 entity types, TCM/Āyurvedic/alchemical vocabularies, curated priors
``normalize``  orthography folding for zh-Hant/zh-Hans, IAST, Sanskrit, Arabic, English
``extract``    span-faithful entity/relation extraction
``kg``         knowledge graph build + queries
``theory``     Asian theoretical systems as feature vectors + predictivity tests
``discover``   six hypothesis classes + the drug-candidate shortlist
``score``      composite ranking with uncertainty and sensitivity analysis
``rag``        pure-python BM25 with grounded, refusal-first answers
``safety``     dual-use / medical-safety screening
``learn``      eval-gated continuous-learning loop and active learning
``eval``       benchmark harness, theory experiments, report writer
``cli``        cai | zhi | pei | shi | ask | report
"""

from __future__ import annotations

__version__ = "0.3.0"
