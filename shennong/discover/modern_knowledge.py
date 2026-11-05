"""Curated modern-knowledge reference used to compute novelty — and its limits.

This module exists so that "novel" is a *defined, auditable* claim rather than a boast.
It is a small hand-curated exclusion list, not a ChEMBL-scale annotation search.  The
honest statement (repeated in every dossier and in ``eval/report.json``) is:

    novelty_method = "curated modern exclusion list: approved-drug compounds (n=…),
    extensively-studied natural-product leads (n=…), and graph-level modern evidence
    (grade A/B or modern-tradition use); no offline ChEMBL target-annotation check."

That means novelty scores are **upper bounds** on true novelty.  A candidate that passes
this filter is "not obviously known", not "provably new".
"""

from __future__ import annotations

#: Compounds that are approved drugs or active pharmaceutical ingredients somewhere.
APPROVED_DRUG_COMPOUNDS: frozenset[str] = frozenset(
    {
        "morphine", "codeine", "quinine", "artemisinin", "digoxin", "atropine",
        "scopolamine", "ephedrine", "pseudoephedrine", "berberine", "caffeine",
        "theophylline", "glycyrrhizin", "ursodeoxycholic_acid", "colchicine",
        "paclitaxel", "vinblastine", "reserpine", "emetine", "santonin",
        "salicin", "salicylic_acid", "allantoin", "menthol", "thymol", "camphor",
        "eugenol", "cinnamaldehyde", "capsaicin", "tetrahydrocannabinol",
    }
)

#: Natural-product compounds with extensive modern literature but no broad approval.
KNOWN_LEAD_COMPOUNDS: frozenset[str] = frozenset(
    {
        "curcumin", "resveratrol", "piperine", "gingerol", "ginsenoside_Rb1",
        "ginsenoside_Rg1", "withanolide", "bacoside", "boswellic_acid",
        "cannabidiol", "quercetin", "apigenin", "baicalin", "emodin", "rhein",
        "tanshinone", "paeoniflorin", "safranal", "crocin", "hypericin",
        "hyperforin", "capsaicin", "alliin", "allicin", "sulforaphane",
        "genistein", "daidzein", "betulinic_acid", "oleanolic_acid",
        "honokiol", "magnolol", "schisandrin", "gastrodin", "ligustilide",
        "paeonol", "ferulic_acid", "rosmarinic_acid", "chlorogenic_acid",
    }
)

#: Curated 0–1 estimate of how heavily the species is studied in modern science.
#: 0.0 = essentially unstudied, 1.0 = blockbuster-level literature.  Used only to
#: discount novelty, never to boost any score.
LITERATURE_PRIOR: dict[str, float] = {
    "Panax ginseng": 0.95,
    "Curcuma longa": 0.95,
    "Withania somnifera": 0.90,
    "Artemisia annua": 0.95,
    "Ginkgo biloba": 0.95,
    "Glycyrrhiza uralensis": 0.90,
    "Glycyrrhiza glabra": 0.90,
    "Zingiber officinale": 0.90,
    "Cannabis sativa": 0.95,
    "Hypericum perforatum": 0.90,
    "Papaver somniferum": 0.95,
    "Cinchona officinalis": 0.90,
    "Digitalis purpurea": 0.90,
    "Atropa belladonna": 0.85,
    "Berberis aristata": 0.70,
    "Tinospora cordifolia": 0.70,
    "Bacopa monnieri": 0.75,
    "Boswellia serrata": 0.70,
    "Commiphora mukul": 0.60,
    "Terminalia chebula": 0.65,
    "Phyllanthus emblica": 0.65,
    "Piper nigrum": 0.75,
    "Piper longum": 0.60,
    "Azadirachta indica": 0.75,
    "Centella asiatica": 0.65,
    "Asparagus racemosus": 0.55,
    "Saussurea lappa": 0.45,
    "Holarrhena antidysenterica": 0.40,
    "Picrorhiza kurroa": 0.45,
    "Rubia cordifolia": 0.45,
    "Nardostachys jatamansi": 0.40,
    "Santalum album": 0.45,
    "Aquilaria agallocha": 0.40,
    "Aconitum carmichaelii": 0.75,
    "Rheum palmatum": 0.70,
    "Coptis chinensis": 0.70,
    "Salvia miltiorrhiza": 0.80,
    "Astragalus membranaceus": 0.75,
    "Rehmannia glutinosa": 0.60,
    "Angelica sinensis": 0.65,
    "Paeonia lactiflora": 0.60,
    "Scutellaria baicalensis": 0.70,
    "Poria cocos": 0.55,
    "Pinellia ternata": 0.50,
    "Ephedra sinica": 0.80,
    "Cannabis sativa": 0.95,
    "Datura metel": 0.65,
    "Acorus calamus": 0.55,
    "Cyperus rotundus": 0.50,
    "Boerhavia diffusa": 0.40,
    "Paris polyphylla": 0.45,
    "Dendrobium nobile": 0.40,
    "Gastrodia elata": 0.50,
    "Bletilla striata": 0.40,
    "Cibotium barometz": 0.20,
    "Euphorbia kansui": 0.35,
    "Euphorbia pekinensis": 0.35,
    "Croton tiglium": 0.45,
    "Pharbitis nil": 0.35,
    "Sparganium stoloniferum": 0.30,
    "Aristolochia manshuriensis": 0.60,
    "Aristolochia fangchi": 0.60,
    "Gynura segetum": 0.35,
    "Periploca sepium": 0.30,
    "Eleutherococcus gracilistylus": 0.45,
    "Sophora tonkinensis": 0.45,
    "Menispermum dauricum": 0.30,
    "Asarum heterotropoides": 0.50,
    "Veratrum nigrum": 0.40,
    "Sargassum fusiforme": 0.35,
    "Daphne genkwa": 0.30,
    "Lilium brownii": 0.30,
    "Dioscorea opposita": 0.40,
    "Cornus officinalis": 0.40,
    "Alisma plantago-aquatica": 0.35,
    "Paeonia suffruticosa": 0.45,
    "Mentha haplocalyx": 0.55,
    "Schisandra chinensis": 0.50,
    "Ophiopogon japonicus": 0.35,
    "Eucommia ulmoides": 0.45,
    "Dipsacus asper": 0.30,
    "Lycium barbarum": 0.55,
    "Atractylodes macrocephala": 0.45,
    "Bupleurum chinense": 0.55,
    "Phellodendron amurense": 0.50,
    "Gardenia jasminoides": 0.45,
    "Platycodon grandiflorus": 0.40,
    "Cimicifuga foetida": 0.35,
    "Citrus aurantium": 0.55,
    "Magnolia officinalis": 0.55,
    "Anemarrhena asphodeloides": 0.40,
    "Oryza sativa": 0.60,
    "Laurus nobilis": 0.40,
    "Cinnamomum verum": 0.55,
    "Terminalia bellirica": 0.45,
    "Saposhnikovia divaricata": 0.40,
    "Angelica dahurica": 0.40,
    "Moschus": 0.60,
    "Ursus": 0.55,
    "Manis": 0.45,
    "Panthera tigris": 0.40,
    "Rhinoceros": 0.45,
    "sulfur": 0.40,
    "sodium sulfate": 0.35,
    "mercury": 0.60,
    "arsenic trioxide": 0.70,
    "realgar": 0.40,
    "cinnabar": 0.40,
    "calomel": 0.40,
    "lead oxide": 0.40,
    "alum": 0.35,
    "halloysite": 0.30,
    "litharge": 0.35,
    "Euphorbia fischeriana": 0.25,
}


def literature_prior(binomial: str) -> float:
    """Curated familiarity prior in [0, 1]; default 0.20 for unlisted species."""
    return LITERATURE_PRIOR.get(binomial, 0.20)


def is_known_compound(name: str) -> bool:
    return name in APPROVED_DRUG_COMPOUNDS or name in KNOWN_LEAD_COMPOUNDS


NOVELTY_METHOD = (
    "curated modern exclusion list: approved-drug compounds "
    f"(n={len(APPROVED_DRUG_COMPOUNDS)}), extensively-studied natural-product leads "
    f"(n={len(KNOWN_LEAD_COMPOUNDS)}), graph-level modern evidence (grade A/B or "
    "modern-tradition use), and a curated literature-familiarity prior "
    f"(n={len(LITERATURE_PRIOR)} species). No offline ChEMBL target-annotation check is "
    "available, so novelty scores are upper bounds."
)
