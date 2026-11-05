# DATA SOURCES — the canonical choices, and why

The question this answers: **if you can only pull from a few places, which ones?** Not a survey —
a decision. Every choice below is justified by three criteria: coverage, licence (can it ship in a
public repo), and access (API vs bulk dump).

---

## 1. The single best herbal data source for **both Western and Asian plants**

### → Dr. Duke's Phytochemical and Ethnobotanical Databases (USDA ARS)

**Why it is the single best:** it is the only public-domain dataset that puts **phytochemistry,
ethnobotanical use, biological activity and LD toxicity for the global flora — including Asian
species — in one place, with literature references**. Nothing else covers western and Asian plants in
the same schema.

| | |
|---|---|
| Publisher | USDA Agricultural Research Service (Economic Botany Laboratory legacy) |
| Licence | **Public domain** (US Government work) — shippable |
| Access | **Bulk CSV** (`Duke-Source-CSV.zip`) from data.gov; interactive at phytochem.nal.usda.gov |
| Content | plant × chemical × activity × ethnobotanical use × LD toxicity, with references |
| Weakness | 1990s-era curation; taxonomy is dated (must be reconciled to POWO); uneven Asian coverage |

- Dataset: https://catalog.data.gov/dataset/dr-dukes-phytochemical-and-ethnobotanical-databases
- Interactive: https://phytochem.nal.usda.gov/phytochem/search

**The catch that matters:** the taxonomy is old. Duke names plants under synonyms that modern
databases no longer use. Reconciling Duke → **Kew POWO** is therefore not optional; it is the first
join in any serious pipeline, and it is exactly the step that, done badly, produced the
*Phycodurus eques* (seahorse) false joins in an earlier version of this repo.

---

## 2. The single best **Asian-tradition** structured source

### Chinese: HERB — and TCMSP for a smaller, cleaner core

| | HERB | TCMSP |
|---|---|---|
| Scale | **7,263 herbs · 51,555 compounds · 12,933 targets · 1,241 diseases** | 499 herbs · ~29 k compounds · 3,312 targets |
| Curation | high-throughput + reference-guided, includes experimental evidence | expert-curated, ADME-filtered |
| Access | bulk download (herb.ac.cn) | bulk download, web query |
| Best for | coverage | precision / interpretability |

- HERB: https://herb.ac.cn/ · paper: https://pubmed.ncbi.nlm.nih.gov/33264402/
- TCMSP: https://tcmsp-e.com/

**Rule:** use **TCMSP as the curated core** (you can defend every row) and **HERB as the coverage
net** (you find things TCMSP never curated). Never mix them without recording which is which — they
disagree, and a silent merge destroys provenance.

### Indian / Ayurveda: **IMPPAT 3.0**

The FAIR counterpart for Indian medicinal plants: plants, phytochemicals, formulations and
therapeutic uses, built explicitly for computational use.
Paper: https://arxiv.org/abs/2610.07478

### Cross-tradition bridge: **SymMap**

Links TCM herbs → symptoms → modern targets, which is the only one of these designed to sit *between*
the traditional and the modern vocabulary.

---

## 3. The single best source of **Asian scientific data retrievable on demand**

**Honest answer: there is no single API.** Every Asian-tradition database above is a *bulk download*
(HERB, TCMSP, IMPPAT, SymMap), not a query service. Anyone claiming "one API for Asian medicine" is
either scraping or reselling.

The best **on-demand** stack, all free and keyless, is four endpoints that each answer one question:

| Question | Source | Endpoint | Why |
|---|---|---|---|
| What does the classical text actually say? | **Chinese Text Project** | `ctext.org` API (URN → passage) | on-demand retrieval of the original classical text, with edition |
| What molecule is this? | **PubChem PUG-REST** | `pubchem.ncbi.nlm.nih.gov/rest/pug/…` | structure, properties, synonyms; no key |
| What is its measured bioactivity? | **ChEMBL** | `www.ebi.ac.uk/chembl/api/data/…` | measured assays, not predicted |
| Does the target matter for the disease? | **Open Targets Platform** | GraphQL `api.platform.opentargets.org/api/v4/graphql` | target–disease association scores + evidence |
| Is the species correct? | **Kew POWO / WFO** | POWO API | accepted name + synonyms (the join that saves you) |

So the operational answer is: **texts from ctext, chemistry from PubChem, bioactivity from ChEMBL,
genetics from Open Targets, taxonomy from POWO.** Everything Asian-specific arrives as bulk tables and
is joined locally.

Our corpus already holds the *text* side offline (106 sources, 45.6 M chars). The missing on-demand
pieces are the four APIs above — and they are what turn "we read the texts" into "we can check what
the world knows about the molecule the text implies".

---

## 4. What this changes about the design

The earlier design derived hypotheses **within** one corpus. The user's ask — interpolate between
domains — requires the opposite shape: **independent experts, each grounded in a different data
source, that never see each other's evidence**, and a fusion layer that rewards *agreement between
domains that had no way to agree*.

That is the point: a claim supported by the classical text **and** by measured ChEMBL bioactivity
**and** by target–disease genetics is a genuine cross-domain interpolation. A claim supported by one
domain is an assertion. The fusion layer must be able to tell the difference, and must report which
domains disagree, because disagreement is the uncertainty that matters.

Implemented in `shennong/experts/` — see `docs/EXPERTS.md`.
