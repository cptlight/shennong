# SHENNONG — drug candidate shortlist

Generated 2026-11-05T13:24:22+00:00. **5 candidates** from classical Asian leads with real SMILES.

> Research use only. Not medical advice. No dose or human-use protocol is given. Toxicological drugs (heavy metals, aristolochic acid, pyrrolizidine alkaloids, cyanogenic glycosides, cardiac glycosides, Aconitum diesters) are excluded by design.

**Novelty method.** curated modern exclusion list: approved-drug compounds (n=30), extensively-studied natural-product leads (n=38), graph-level modern evidence (grade A/B or modern-tradition use), and a curated literature-familiarity prior (n=113 species). No offline ChEMBL target-annotation check is available, so novelty scores are upper bounds.

| # | Lead (drug) | Candidate | Class | MW | logP* | TPSA* | Target | Indication | Composite (raw) | Percentile |
|---|---|---|---|---|---|---|---|---|---|---|
| C-2026-0001 | Mentha haplocalyx | menthol | monoterpenoid | 156.3 | 3.60 | 20.2 | GABA_A | headache | 0.0341 | 1.00 |
| C-2026-0002 | Rheum palmatum | emodin | anthraquinone | 270.2 | 1.05 | 79.2 | bacterial membrane | dyspepsia | 0.0295 | 0.50 |
| C-2026-0003 | Rheum palmatum | rhein | anthraquinone | 284.2 | 0.40 | 88.4 | bacterial membrane | dyspepsia | 0.0295 | 0.50 |
| C-2026-0004 | Zingiber officinale | gingerol | gingerol | 294.4 | 4.30 | 58.9 | TRPV1 | vomiting | 0.0250 | 0.25 |
| C-2026-0005 | Coptis chinensis | berberine | alkaloid | 331.4 | 3.75 | 40.6 | opioid receptor | diarrhoea | 0.0095 | 0.00 |

\* `logP` and `TPSA` are transparent fragment approximations from `shennong.chem`, not validated Crippen/Ertl calculations. MW, HBD/HBA, rings and rotatable bonds are exact given the SMILES parse.

Excluded toxicological leads: 14; compounds with null structure: 19 (never invented). Full detail in `drug_candidates.json`.
