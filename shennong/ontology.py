"""ATHANOR ontology — controlled vocabularies for ethnopharmacology.

This module is the project's Tier 0: the *structure of the domain*.  It defines the
entity types, the Galenic humoral system, the Paracelsian/spagyric process vocabulary
translated into modern extraction chemistry, and a curated first-principles prior that
maps natural-product **compound classes** to plausible molecular targets, pathways and
indications.

Two design rules matter for scientific honesty:

1.  **Curated priors are priors, not evidence.**  ``COMPOUND_CLASSES`` encodes the
    textbook pharmacology of a compound *class* (e.g. "sesquiterpene lactones are
    electrophilic NF-kB inhibitors").  It is used to *generate* a mechanistic
    hypothesis, never to assert that a particular plant contains an active molecule.
    Every consumer must label the resulting claim as a prior and attach the corpus
    evidence that triggered it.

2.  **Historical vocabulary is mapped, not decoded.**  ``ALCHEMICAL_PROCESSES`` maps
    process words onto the physical chemistry they plausibly implement (solvent
    polarity, temperature window, which compound classes are enriched or destroyed).
    The mappings are necessarily approximate and are documented as such.  They are
    the project's novel data product (see docs/FIRST_PRINCIPLES.md, brief §2).

No historical source is quoted verbatim here; citations name the text in which the
operation is attested so a human can check the claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping

# --------------------------------------------------------------------------------------
# Entity types (brief §6, Tier 0)
# --------------------------------------------------------------------------------------


class EntityType(str, Enum):
    """Node kinds in the knowledge graph."""

    TAXON = "taxon"
    PLANT_PART = "plant_part"
    PREPARATION = "preparation"
    PROCESS = "process"
    COMPOUND = "compound"
    COMPOUND_CLASS = "compound_class"
    TARGET = "target"
    PATHWAY = "pathway"
    INDICATION = "indication"
    SYMPTOM = "symptom"
    ORGAN = "organ"
    OBSERVATION = "observation"
    TRADITION = "tradition"
    SOURCE = "source"
    HUMOUR = "humour"
    QUALITY = "quality"


class EvidenceGrade(str, Enum):
    """Evidence strength, aligned with GRADE-style reasoning (see ``EVIDENCE_GRADES``)."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"


class Tradition(str, Enum):
    """Medical traditions represented in the corpus.

    Only systems the brief explicitly lists (§6 Tier 2) are enumerated; ``UNKNOWN``
    exists so extraction never has to guess.
    """

    GRAECO_ROMAN = "graeco_roman"
    EUROPEAN_HERBAL = "european_herbal"
    PARACELSIAN = "paracelsian"
    GRAECO_ARABIC = "graeco_arabic"
    UNANI = "unani"
    TCM = "tcm"
    AYURVEDA = "ayurveda"
    NATIVE_AMERICAN = "native_american"
    AFRICAN = "african"
    MESOAMERICAN = "mesoamerican"
    OCEANIA = "oceania"
    MODERN = "modern"
    UNKNOWN = "unknown"


class PlantPart(str, Enum):
    WHOLE_HERB = "whole_herb"
    LEAF = "leaf"
    ROOT = "root"
    RHIZOME = "rhizome"
    SEED = "seed"
    FRUIT = "fruit"
    FLOWER = "flower"
    BARK = "bark"
    WOOD = "wood"
    STEM = "stem"
    RESIN = "resin"
    JUICE = "juice"


class Humour(str, Enum):
    BLOOD = "blood"
    PHLEGM = "phlegm"
    YELLOW_BILE = "yellow_bile"
    BLACK_BILE = "black_bile"


class Quality(str, Enum):
    HOT = "hot"
    COLD = "cold"
    DRY = "dry"
    MOIST = "moist"


# --------------------------------------------------------------------------------------
# Galenic humoral system
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class HumourSpec:
    """A Galenic humour with its qualities, element and classical clinical reading.

    The four-humour system is the organising theory of European materia medica from
    Hippocratic texts through Galen to Culpeper (1653).  A plant's ``hot/cold/dry/moist``
    assignment is a *theoretical* claim; the discovery engine can test it, not assume it.

    Attested in: Hippocratic Corpus, *On the Nature of Man* (humours & qualities);
    Galen, *On Temperaments* (degrees of qualities); Culpeper, *Complete Herbal* (1653)
    (planet + degree assignments for individual simples).
    """

    name: Humour
    qualities: frozenset[Quality]
    element: str
    temperament: str
    classical_reading: str


HUMOURS: Mapping[Humour, HumourSpec] = {
    Humour.BLOOD: HumourSpec(
        Humour.BLOOD,
        frozenset({Quality.HOT, Quality.MOIST}),
        "air",
        "sanguine",
        "nutritive humour; excess read as fever, plethora, inflammation of the whole body",
    ),
    Humour.PHLEGM: HumourSpec(
        Humour.PHLEGM,
        frozenset({Quality.COLD, Quality.MOIST}),
        "water",
        "phlegmatic",
        "mucoid humour; excess read as catarrh, oedema, lethargy, cold swellings",
    ),
    Humour.YELLOW_BILE: HumourSpec(
        Humour.YELLOW_BILE,
        frozenset({Quality.HOT, Quality.DRY}),
        "fire",
        "choleric",
        "hot dry humour; excess read as fever, jaundice, bilious vomiting, anger",
    ),
    Humour.BLACK_BILE: HumourSpec(
        Humour.BLACK_BILE,
        frozenset({Quality.COLD, Quality.DRY}),
        "earth",
        "melancholic",
        "cold dry humour; excess read as melancholy, cachexia, chronic 'cancerous' disease",
    ),
}

QUALITY_DEGREES = {
    "note": (
        "Galenic simples were graded in four degrees of intensity for each quality "
        "(e.g. 'hot and dry in the second degree'). The degree is a comparative claim, "
        "not a measurement; we keep it as metadata and never convert it to a number."
    ),
    "max_degree": 4,
}


@dataclass(frozen=True)
class ProcessSemantics:
    """Translation of one historical process word into modern extraction semantics.

    ``polarity`` is a *ranked* descriptor of the solvent/mobile phase: 0.0 = non-polar
    (fixed oils, resins), 1.0 = highly polar (water, ash lye).  ``enriches`` lists
    compound classes the operation preferentially carries into the preparation;
    ``depletes`` lists classes it destroys or removes.  These are engineering priors
    used by ``athanor.discover.process`` to ask whether a documented preparation is
    chemically plausible for the plant's chemotype.
    """

    name: str
    modern: str
    solvent: str | None
    polarity: float
    temp_c: tuple[float, float] | None
    duration: str
    enriches: frozenset[str]
    depletes: frozenset[str]
    historical_usage: str
    citation: str


ALCHEMICAL_PROCESSES: Mapping[str, ProcessSemantics] = {
    "calcination": ProcessSemantics(
        name="calcination",
        modern="oxidation / ashing to a mineral residue (calx)",
        solvent=None,
        polarity=1.0,
        temp_c=(300.0, 900.0),
        duration="hours to days",
        enriches=frozenset({"mineral_salt", "ash"}),
        depletes=frozenset({"monoterpenoid", "sesquiterpenoid", "alkaloid", "flavonoid"}),
        historical_usage=(
            "First of the twelve operations in Ripley's Compound of Alchymy (1471) and "
            "in the Turba Philosophorum: reduction of a body to ash/calx by fire."
        ),
        citation="Ripley, Compound of Alchymy (1471); Turba Philosophorum (12th c. Lat.)",
    ),
    "dissolution": ProcessSemantics(
        name="dissolution",
        modern="solvent extraction with a menstruum (water, vinegar, wine, alcohol)",
        solvent="water | vinegar | wine | ethanol",
        polarity=0.75,
        temp_c=(15.0, 60.0),
        duration="hours to weeks",
        enriches=frozenset(
            {"flavonoid", "phenolic_acid", "alkaloid", "glycoside", "mineral_salt"}
        ),
        depletes=frozenset({"resin", "fatty_acid"}),
        historical_usage=(
            "The 'menstruum' of Paracelsus and van Helmont; Geber describes solution of "
            "the body after calcination. Choice of menstruum (water, vinegar, wine, "
            "spirit of wine) selects polarity."
        ),
        citation="Paracelsus, De renovatione et restauratione; van Helmont, Ortus Medicinae (1648)",
    ),
    "digestion": ProcessSemantics(
        name="digestion",
        modern="controlled gentle heating / warm maceration (dung bed or water bath)",
        solvent="water | wine | ethanol",
        polarity=0.7,
        temp_c=(35.0, 60.0),
        duration="days to a month",
        enriches=frozenset({"alkaloid", "glycoside", "flavonoid"}),
        depletes=frozenset({"monoterpenoid"}),
        historical_usage=(
            "Gentle putrefactive digestion in horse dung or a balneum (water bath), "
            "attested throughout the Paracelsian corpus. 'Digestion' means sustained "
            "warmth, not gastrointestinal digestion."
        ),
        citation="Paracelsian process lists; Basil Valentine, Triumphant Chariot of Antimony (1604)",
    ),
    "distillation": ProcessSemantics(
        name="distillation",
        modern="hydro/steam distillation → volatile fraction / essential oil",
        solvent="water (steam)",
        polarity=0.15,
        temp_c=(78.0, 100.0),
        duration="hours",
        enriches=frozenset({"monoterpenoid", "monoterpenoid_ester", "phenylpropanoid"}),
        depletes=frozenset({"tannin", "polysaccharide", "mucilage", "mineral_salt"}),
        historical_usage=(
            "The alembic still is the central apparatus of the alchemical corpus "
            "(Ripley, Rosarium, Libavius, Porta); it concentrates the 'spirit' of a plant."
        ),
        citation="Ripley, Compound of Alchymy; Rosarium Philosophorum; della Porta, Natural Magick (1558)",
    ),
    "sublimation": ProcessSemantics(
        name="sublimation",
        modern="selective volatilisation and re-condensation of volatile solids",
        solvent=None,
        polarity=0.1,
        temp_c=(100.0, 400.0),
        duration="hours",
        enriches=frozenset({"volatile_solid", "mineral_salt"}),
        depletes=frozenset({"polysaccharide", "protein"}),
        historical_usage=(
            "Volatilisation of a solid to a 'flower' (e.g. sal ammoniac, sulphur); a "
            "standard operation of the twelve in Ripley and the Turba."
        ),
        citation="Ripley, Compound of Alchymy (1471); Turba Philosophorum",
    ),
    "fermentation": ProcessSemantics(
        name="fermentation",
        modern="microbial transformation, including glycoside hydrolysis and decarboxylation",
        solvent="aqueous",
        polarity=0.85,
        temp_c=(15.0, 37.0),
        duration="days to weeks",
        enriches=frozenset(
            {"alkaloid", "phenolic_acid", "alcohol", "aglycone"}
        ),
        depletes=frozenset({"glycoside", "polysaccharide", "mucilage"}),
        historical_usage=(
            "Putrefaction/fermentation as the first stage of the Great Work; in pharmacy, "
            "wine and beer 'menstrua' are fermented vehicles."
        ),
        citation="Ripley, Compound of Alchymy; Turba Philosophorum",
    ),
    "tincture": ProcessSemantics(
        name="tincture",
        modern="ethanol/water maceration",
        solvent="ethanol/water",
        polarity=0.55,
        temp_c=(15.0, 25.0),
        duration="days to weeks",
        enriches=frozenset(
            {"alkaloid", "flavonoid", "sesquiterpene_lactone", "cannabinoid", "resin"}
        ),
        depletes=frozenset({"polysaccharide", "mucilage", "protein"}),
        historical_usage=(
            "A 'tincture' is a coloured solution drawn by a menstruum; the term is "
            "standard in Paracelsian and later pharmacopoeial pharmacy."
        ),
        citation="Paracelsus; London Pharmacopoeia (1618 ff.) tincturae",
    ),
    "decoction": ProcessSemantics(
        name="decoction",
        modern="aqueous decoction, 15–60 min near 100 °C",
        solvent="water",
        polarity=0.95,
        temp_c=(95.0, 100.0),
        duration="15–60 min",
        enriches=frozenset(
            {"polysaccharide", "mucilage", "tannin", "glycoside", "phenolic_acid", "mineral_salt"}
        ),
        depletes=frozenset(
            {"monoterpenoid", "monoterpenoid_ester", "carotenoid", "pyrrolizidine_alkaloid"}
        ),
        historical_usage=(
            "Boiling simples in water is the commonest preparation in the European "
            "herbals (Culpeper, Gerard) and in Dioscorides."
        ),
        citation="Dioscorides, De Materia Medica; Culpeper, Complete Herbal (1653)",
    ),
    "infusion": ProcessSemantics(
        name="infusion",
        modern="aqueous infusion (tea), short contact at ~90–100 °C",
        solvent="water",
        polarity=0.95,
        temp_c=(85.0, 100.0),
        duration="5–15 min",
        enriches=frozenset(
            {"flavonoid", "phenolic_acid", "glycoside", "mucilage", "monoterpenoid"}
        ),
        depletes=frozenset({"tannin", "resin"}),
        historical_usage=(
            "Short steeping of leaves/flowers; distinguished from decoction by heat and "
            "time (Culpeper's 'water of ...' and 'infusion')."
        ),
        citation="Culpeper, Complete Herbal (1653); Gerard, Herball (1597)",
    ),
    "maceration": ProcessSemantics(
        name="maceration",
        modern="cold soak in solvent",
        solvent="water | wine | vinegar | ethanol",
        polarity=0.7,
        temp_c=(15.0, 25.0),
        duration="hours to days",
        enriches=frozenset({"mucilage", "polysaccharide", "glycoside", "alkaloid", "protein"}),
        depletes=frozenset({"volatile_solid"}),
        historical_usage=(
            "Cold or tepid steeping ('maceration') is the gentle alternative to boiling "
            "for heat-labile simples."
        ),
        citation="Dioscorides, De Materia Medica; Galenic pharmacy",
    ),
    "spagyria": ProcessSemantics(
        name="spagyria",
        modern=(
            "separation into three principles: mineral salt (ash/lye), resin/oil "
            "(sulphur), volatile alcohol/spirit (mercury)"
        ),
        solvent="water + ethanol (sequential)",
        polarity=0.8,
        temp_c=(25.0, 100.0),
        duration="multi-stage, days",
        enriches=frozenset(
            {"mineral_salt", "resin", "monoterpenoid", "alkaloid", "flavonoid"}
        ),
        depletes=frozenset({"polysaccharide", "protein"}),
        historical_usage=(
            "Paracelsus's tria prima — salt, sulphur, mercury — separated by calcination, "
            "dissolution, distillation and lixiviation; the defining operation of "
            "spagyric (Paracelsian) pharmacy."
        ),
        citation="Paracelsus; Basil Valentine, Triumphant Chariot of Antimony (1604)",
    ),
    "lixiviation": ProcessSemantics(
        name="lixiviation",
        modern="leaching of soluble salts from ash with water (ash lye)",
        solvent="water (lye)",
        polarity=1.0,
        temp_c=(20.0, 100.0),
        duration="hours",
        enriches=frozenset({"mineral_salt"}),
        depletes=frozenset({"resin", "fatty_acid", "monoterpenoid"}),
        historical_usage=(
            "Washing the calcined ash to obtain the 'salt' of a plant; paired with "
            "calcination in spagyric practice."
        ),
        citation="Basil Valentine; Paracelsian spagyric texts",
    ),
    "expression": ProcessSemantics(
        name="expression",
        modern="mechanical pressing of fresh material",
        solvent=None,
        polarity=0.8,
        temp_c=(15.0, 25.0),
        duration="minutes",
        enriches=frozenset({"juice", "polysaccharide", "phenolic_acid", "vitamin"}),
        depletes=frozenset({"resin", "tannin"}),
        historical_usage="Pressing the juice of fresh herbs, ubiquitous in the herbals.",
        citation="Culpeper, Complete Herbal (1653)",
    ),
    "milling": ProcessSemantics(
        name="milling",
        modern="mechanical comminution to powder",
        solvent=None,
        polarity=0.5,
        temp_c=(15.0, 30.0),
        duration="minutes",
        enriches=frozenset({"tannin", "resin", "polysaccharide"}),
        depletes=frozenset({"monoterpenoid"}),
        historical_usage="Reduction of dried simples to powder for dosing by weight.",
        citation="Galenic and later pharmacy",
    ),
}


# ``Preparation`` → process pipeline.  A preparation may implement several operations
# in sequence (e.g. a syrup is a decoction plus sugar; an essential oil is a distillation).
PREPARATION_PROCESSES: Mapping[str, tuple[str, ...]] = {
    "decoction": ("decoction",),
    "infusion": ("infusion",),
    "tincture": ("tincture",),
    "distillation": ("distillation",),
    "distilled_water": ("distillation",),
    "essential_oil": ("distillation",),
    "maceration": ("maceration",),
    "extract": ("maceration", "tincture"),
    "syrup": ("decoction",),
    "powder": ("milling",),
    "poultice": ("maceration", "expression"),
    "juice": ("expression",),
    "calcination": ("calcination", "lixiviation"),
    "fermentation": ("fermentation",),
    "spagyria": ("calcination", "dissolution", "digestion", "distillation", "lixiviation"),
    "sublimation": ("sublimation",),
    "balneum": ("digestion",),
    "menstruum": ("dissolution",),
}

# Historical process words → canonical process key (extraction lexicon).
PROCESS_SYNONYMS: Mapping[str, str] = {
    "calcin": "calcination",
    "calcination": "calcination",
    "calcined": "calcination",
    "dissolution": "dissolution",
    "dissolve": "dissolution",
    "dissolved": "dissolution",
    "menstruum": "dissolution",
    "digestion": "digestion",
    "digest": "digestion",
    "digested": "digestion",
    "dung": "digestion",
    "balneum": "digestion",
    "distillation": "distillation",
    "distill": "distillation",
    "distilled": "distillation",
    "alembic": "distillation",
    "sublimation": "sublimation",
    "sublime": "sublimation",
    "sublimed": "sublimation",
    "fermentation": "fermentation",
    "ferment": "fermentation",
    "putrefaction": "fermentation",
    "tincture": "tincture",
    "decoction": "decoction",
    "decoct": "decoction",
    "decocted": "decoction",
    "boiled": "decoction",
    "infusion": "infusion",
    "infuse": "infusion",
    "infused": "infusion",
    "macerat": "maceration",
    "macerate": "maceration",
    "spagyri": "spagyria",
    "spagyric": "spagyria",
    "lixiviation": "lixiviation",
    "lixiviate": "lixiviation",
    "expression": "expression",
    "pressed": "expression",
    "juice": "expression",
    "powder": "milling",
    "pulveris": "milling",
}


# --------------------------------------------------------------------------------------
# Compound-class prior: polarity, volatility, thermolability and textbook pharmacology
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CompoundClassProfile:
    """Engineering + pharmacological prior for a natural-product class.

    ``polarity`` ∈ [0, 1]: 0 = lipophilic (fixed oil), 1 = highly hydrophilic (salt).
    ``volatility`` ∈ [0, 1]: 1 = steam-distillable at ~100 °C.
    ``thermolability`` ∈ [0, 1]: 1 = destroyed by prolonged boiling.
    ``targets``/``pathways``/``indications`` are *hypothesis-generating* priors: a
    compound class that plausibly acts on the pathway underlying indication X is a
    bridge candidate, not proof.
    """

    name: str
    polarity: float
    volatility: float
    thermolability: float
    targets: tuple[str, ...]
    pathways: tuple[str, ...]
    indications: tuple[str, ...]
    notes: str
    citation: str


COMPOUND_CLASSES: Mapping[str, CompoundClassProfile] = {
    "sesquiterpene_lactone": CompoundClassProfile(
        "sesquiterpene_lactone", 0.50, 0.10, 0.55,
        ("NF-kB", "IL-6", "TNF-alpha"),
        ("inflammatory signalling (NF-kB)",),
        ("inflammation", "osteoarthritis", "pain"),
        "Electrophilic alpha-methylene-butyrolactones alkylate NF-kB pathway proteins; "
        "parthenolide is the prototype. Gastro-irritant; contact sensitisation possible.",
        "Hehner et al., J. Biol. Chem. 273:1288 (1998) — parthenolide inhibits NF-kB",
    ),
    "monoterpenoid": CompoundClassProfile(
        "monoterpenoid", 0.15, 0.90, 0.70,
        ("GABA_A", "TRPA1", "TRPV1", "AChE"),
        ("neurotransmission",),
        ("anxiety", "pain", "cough", "insomnia", "dyspepsia"),
        "Volatile, steam-distillable, often lipophilic. Thujone is proconvulsant; "
        "menthol/thymol act on TRP channels; many are mild GABA_A modulators.",
        "canonical natural-products pharmacology (monoterpenoid class)",
    ),
    "monoterpenoid_ester": CompoundClassProfile(
        "monoterpenoid_ester", 0.20, 0.85, 0.70,
        ("GABA_A", "TRPA1"),
        ("neurotransmission",),
        ("anxiety", "pain", "insomnia"),
        "Linalyl acetate and similar esters: volatile, lipophilic, sedative-leaning.",
        "canonical natural-products pharmacology",
    ),
    "sesquiterpenoid": CompoundClassProfile(
        "sesquiterpenoid", 0.25, 0.70, 0.60,
        ("TRPA1", "COX-1/2"),
        ("inflammatory signalling (NF-kB)",),
        ("inflammation", "wound_healing", "skin"),
        "Bisabolol, chamazulene: anti-inflammatory and skin-soothing; azulenes are "
        "distillation artefacts (chamazulene forms during steam distillation).",
        "canonical natural-products pharmacology",
    ),
    "diterpenoid_lactone": CompoundClassProfile(
        "diterpenoid_lactone", 0.40, 0.05, 0.40,
        ("PAF receptor",),
        ("inflammatory signalling (NF-kB)", "cerebral blood flow"),
        ("inflammation", "cognitive_impairment", "asthma"),
        "Ginkgolides are PAF-receptor antagonists; non-volatile, only mildly heat-labile.",
        "canonical natural-products pharmacology (ginkgolide B)",
    ),
    "triterpenoid_saponin": CompoundClassProfile(
        "triterpenoid_saponin", 0.60, 0.01, 0.50,
        ("membrane sterols", "11beta-HSD2", "H+/K+-ATPase"),
        ("mucosal protection", "inflammatory signalling (NF-kB)"),
        ("peptic_ulcer", "cough", "inflammation"),
        "Surface-active glycosides; glycyrrhizin inhibits 11beta-HSD2 (mineralocorticoid "
        "effect — hypertension/oedema risk). Many saponins are gastro-irritant.",
        "canonical natural-products pharmacology (glycyrrhizin)",
    ),
    "flavonoid": CompoundClassProfile(
        "flavonoid", 0.55, 0.02, 0.30,
        ("COX-1/2", "LOX", "Nrf2", "GABA_A"),
        ("oxidative stress (Nrf2/ARE)", "inflammatory signalling (NF-kB)"),
        ("inflammation", "anxiety", "cardiovascular"),
        "Broad, weak polypharmacology; low oral bioavailability for many aglycones. "
        "Apigenin is a weak GABA_A ligand.",
        "canonical natural-products pharmacology (flavonoid class)",
    ),
    "phenolic_acid": CompoundClassProfile(
        "phenolic_acid", 0.65, 0.02, 0.30,
        ("COX-1/2", "Nrf2"),
        ("oxidative stress (Nrf2/ARE)",),
        ("inflammation", "wound_healing", "skin"),
        "Rosmarinic, caffeic, gallic acids: antioxidants, weak enzyme inhibitors.",
        "canonical natural-products pharmacology",
    ),
    "tannin": CompoundClassProfile(
        "tannin", 0.70, 0.01, 0.40,
        ("protein binding",),
        ("mucosal protection",),
        ("wound_healing", "flux", "inflammation"),
        "Polyphenols that cross-link proteins: astringent, antimicrobial, anti-diarrhoeal. "
        "High doses are hepatotoxic and antinutritive.",
        "canonical natural-products pharmacology",
    ),
    "coumarin": CompoundClassProfile(
        "coumarin", 0.45, 0.05, 0.30,
        ("vitamin K epoxide reductase",),
        ("coagulation",),
        ("inflammation", "swelling"),
        "Simple coumarins are weak; 4-hydroxycoumarin derivatives are anticoagulants. "
        "Interacts with warfarin and vitamin K.",
        "canonical natural-products pharmacology",
    ),
    "lignan": CompoundClassProfile(
        "lignan", 0.50, 0.01, 0.30,
        ("oestrogen receptor", "Nrf2"),
        ("endocrine modulation", "oxidative stress (Nrf2/ARE)"),
        ("menstrual_disorders", "inflammation"),
        "Phytoestrogenic or antioxidant depending on structure.",
        "canonical natural-products pharmacology",
    ),
    "alkaloid": CompoundClassProfile(
        "alkaloid", 0.50, 0.15, 0.45,
        ("opioid receptor", "AChE", "Na+ channel", "5-HT2A", "dopamine D2"),
        ("neurotransmission", "cholinergic", "opioidergic"),
        ("pain", "insomnia", "motion_sickness", "malaria", "hypertension", "cough"),
        "A heterogeneous class — receptor prediction is class-level only. Many are "
        "potently toxic (Atropa, Digitalis-adjacent, aconite) and dose-critical; this "
        "system never proposes dosing.",
        "canonical natural-products pharmacology",
    ),
    "phenolic_glycoside": CompoundClassProfile(
        "phenolic_glycoside", 0.75, 0.01, 0.50,
        ("COX-1/2",),
        ("inflammatory signalling (NF-kB)",),
        ("pain", "fever", "inflammation"),
        "Salicin is a prodrug hydrolysed to saligenin then oxidised to salicylate — a "
        "COX inhibitor. Glycosides are polar and moderately heat-labile.",
        "canonical natural-products pharmacology (salicin → salicylate)",
    ),
    "cardiac_glycoside": CompoundClassProfile(
        "cardiac_glycoside", 0.60, 0.01, 0.40,
        ("Na+/K+-ATPase",),
        ("cardiac contractility",),
        ("heart_failure",),
        "Narrow therapeutic index; digoxin is a prescription drug. Any dietary exposure "
        "is a poisoning risk; this system flags, never doses.",
        "canonical pharmacology of cardiac glycosides",
    ),
    "anthraquinone": CompoundClassProfile(
        "anthraquinone", 0.50, 0.01, 0.40,
        ("bacterial membrane", "Na+/K+-ATPase"),
        ("gastrointestinal motility",),
        ("constipation", "wound_healing"),
        "Anthraquinone laxatives (sennosides, aloin) stimulate colonic motility; chronic "
        "use causes melanosis coli. Mutagenicity data are mixed.",
        "canonical natural-products pharmacology",
    ),
    "purine": CompoundClassProfile(
        "purine", 0.90, 0.01, 0.50,
        ("cell proliferation",),
        ("tissue repair",),
        ("wound_healing", "skin"),
        "Allantoin promotes cell proliferation and is used topically.",
        "canonical natural-products pharmacology (allantoin)",
    ),
    "organosulfur": CompoundClassProfile(
        "organosulfur", 0.30, 0.70, 0.50,
        ("thiol groups", "H2S", "bacterial membrane"),
        ("vascular tone (ACE/NO)", "oxidative stress (Nrf2/ARE)"),
        ("hypertension", "common_cold"),
        "Allicin is unstable and hydrophobic; it reacts with thiols and releases H2S. "
        "Antimicrobial and modestly hypotensive.",
        "canonical natural-products pharmacology (allicin)",
    ),
    "phenylpropanoid": CompoundClassProfile(
        "phenylpropanoid", 0.30, 0.80, 0.60,
        ("TRPA1", "5-HT3"),
        ("neurotransmission", "gastrointestinal motility"),
        ("dyspepsia", "cough", "nausea"),
        "Anethole, estragole: volatile carminatives; some are genotoxic at high dose "
        "(estragole).",
        "canonical natural-products pharmacology (anethole)",
    ),
    "carotenoid": CompoundClassProfile(
        "carotenoid", 0.35, 0.01, 0.55,
        ("NF-kB", "Nrf2"),
        ("oxidative stress (Nrf2/ARE)", "inflammatory signalling (NF-kB)"),
        ("depression", "eye_disorders", "inflammation"),
        "Crocin (saffron) is water-soluble and heat-sensitive; saffron depression trials "
        "are small but positive.",
        "canonical natural-products pharmacology (crocins)",
    ),
    "curcuminoid": CompoundClassProfile(
        "curcuminoid", 0.45, 0.01, 0.45,
        ("NF-kB", "Nrf2", "EGFR"),
        ("inflammatory signalling (NF-kB)",),
        ("osteoarthritis", "inflammation"),
        "Curcumin has very low oral bioavailability; adjunct studies use bioavailability "
        "enhancers. The class prior is strong, the pharmacokinetics are the failure mode.",
        "canonical natural-products pharmacology (curcumin)",
    ),
    "gingerol": CompoundClassProfile(
        "gingerol", 0.40, 0.10, 0.50,
        ("TRPV1", "5-HT3"),
        ("gastrointestinal motility",),
        ("nausea", "dyspepsia"),
        "Gingerols are TRPV1 agonists; antiemetic evidence in pregnancy and chemotherapy "
        "is moderate.",
        "canonical natural-products pharmacology (gingerols)",
    ),
    "cannabinoid": CompoundClassProfile(
        "cannabinoid", 0.20, 0.10, 0.55,
        ("CNR1", "CNR2", "TRPV1"),
        ("endocannabinoid", "neurotransmission"),
        ("chronic_pain", "nausea", "epilepsy", "anxiety"),
        "Phytocannabinoids are lipophilic; THC is psychoactive and controlled, CBD is not. "
        "This system makes research claims only.",
        "canonical natural-products pharmacology (cannabinoid class)",
    ),
    "naphthodianthrone": CompoundClassProfile(
        "naphthodianthrone", 0.50, 0.01, 0.40,
        ("protein kinase C", "MAO"),
        ("neurotransmission",),
        ("depression",),
        "Hypericin is a photosensitiser; St John's wort has clinically important "
        "CYP3A4/P-gp interactions. Not a substitute for care.",
        "canonical natural-products pharmacology (hypericin)",
    ),
    "phloroglucinol": CompoundClassProfile(
        "phloroglucinol", 0.30, 0.02, 0.50,
        ("5-HT reuptake", "PXR"),
        ("neurotransmission",),
        ("depression",),
        "Hyperforin drives reuptake inhibition and PXR induction; major interaction risk.",
        "canonical natural-products pharmacology (hyperforin)",
    ),
    "pyrrolizidine_alkaloid": CompoundClassProfile(
        "pyrrolizidine_alkaloid", 0.50, 0.01, 0.50,
        ("hepatic CYP activation",),
        ("hepatotoxicity",),
        (),
        "Metabolised to pyrrole esters that alkylate hepatic DNA: veno-occlusive disease "
        "risk. Treated here as a safety signal, never as a therapeutic mechanism.",
        "canonical toxicology of pyrrolizidine alkaloids",
    ),
    "polyacetylene": CompoundClassProfile(
        "polyacetylene", 0.25, 0.05, 0.60,
        ("bacterial membrane", "fungal membrane"),
        ("oxidative stress (Nrf2/ARE)",),
        ("common_cold", "wound_healing"),
        "Highly reactive conjugated alkynes; antimicrobial but unstable.",
        "canonical natural-products pharmacology",
    ),
    "polysaccharide": CompoundClassProfile(
        "polysaccharide", 0.95, 0.00, 0.20,
        ("immune receptors (dectin-1, TLR)",),
        ("immune modulation", "mucosal protection"),
        ("wound_healing", "cough", "flux"),
        "Non-digestible polysaccharides are immunomodulatory and demulcent; activity is "
        "largely local/topical.",
        "canonical natural-products pharmacology",
    ),
    "mucilage": CompoundClassProfile(
        "mucilage", 0.95, 0.00, 0.20,
        ("mucosal surface",),
        ("mucosal protection",),
        ("cough", "dyspepsia", "wound_healing"),
        "Physical demulcent; no receptor pharmacology. Heat and ethanol degrade it.",
        "canonical natural-products pharmacology (mucilage)",
    ),
    "resin": CompoundClassProfile(
        "resin", 0.10, 0.02, 0.40,
        ("bacterial membrane",),
        ("mucosal protection",),
        ("wound_healing", "common_cold"),
        "Lipophilic mixtures; antimicrobial and occlusive. Poor water solubility.",
        "canonical natural-products pharmacology",
    ),
    "fatty_acid": CompoundClassProfile(
        "fatty_acid", 0.10, 0.01, 0.40,
        ("membrane lipids",),
        ("tissue repair",),
        ("wound_healing", "skin"),
        "Emollient and barrier-repair activity.",
        "canonical natural-products pharmacology",
    ),
    "mineral_salt": CompoundClassProfile(
        "mineral_salt", 0.90, 0.00, 0.30,
        ("electrolyte balance", "gastric acid"),
        ("acid-base balance",),
        ("dyspepsia",),
        "Ash-derived salts: antacid and electrolyte effects; the alchemical 'salt' "
        "principle of spagyria.",
        "canonical inorganic pharmacology",
    ),
}


# --------------------------------------------------------------------------------------
# Organs and indications
# --------------------------------------------------------------------------------------


ORGAN_SYSTEMS: Mapping[str, tuple[str, ...]] = {
    "head": ("nervous",),
    "brain": ("nervous",),
    "eyes": ("sensory",),
    "ears": ("sensory",),
    "nose": ("respiratory",),
    "mouth": ("digestive",),
    "throat": ("respiratory",),
    "lungs": ("respiratory",),
    "heart": ("cardiovascular",),
    "stomach": ("digestive",),
    "intestine": ("digestive",),
    "liver": ("hepatobiliary",),
    "gallbladder": ("hepatobiliary",),
    "kidneys": ("urinary",),
    "bladder": ("urinary",),
    "skin": ("integumentary",),
    "bone": ("musculoskeletal",),
    "joints": ("musculoskeletal",),
    "back": ("musculoskeletal",),
    "blood": ("haematologic",),
    "reproductive": ("reproductive",),
    "systemic": ("systemic",),
    "spleen": ("lymphatic",),
}

ORGANS: tuple[str, ...] = tuple(ORGAN_SYSTEMS)


@dataclass(frozen=True)
class IndicationSpec:
    """Canonical indication with its organ, symptom family and mechanism priors."""

    indication: str
    organ: str
    symptom: str
    pathways: tuple[str, ...]
    synonyms: tuple[str, ...] = field(default_factory=tuple)


INDICATIONS: Mapping[str, IndicationSpec] = {
    "dyspepsia": IndicationSpec(
        "dyspepsia", "stomach", "indigestion",
        ("gastrointestinal motility", "mucosal protection"),
        ("indigestion", "weak stomach", "sour stomach", "wind", "flatulence"),
    ),
    "intestinal_worms": IndicationSpec(
        "intestinal_worms", "intestine", "worm infestation",
        ("gastrointestinal motility",), ("worms", "wormes", "belly worms"),
    ),
    "jaundice": IndicationSpec(
        "jaundice", "liver", "yellowing",
        ("hepatobiliary function",), ("yellow jaundice", "the jaundice"),
    ),
    "cough": IndicationSpec(
        "cough", "lungs", "cough",
        ("mucosal protection", "inflammatory signalling (NF-kB)"),
        ("coughs", "the cough", "hoarseness"),
    ),
    "phthisis": IndicationSpec(
        "phthisis", "lungs", "wasting lung disease",
        ("mucosal protection",), ("phthisic", "phthisick", "consumption"),
    ),
    "bone_fracture": IndicationSpec(
        "bone_fracture", "bone", "broken bone",
        ("tissue repair",), ("broken bones", "fractures", "knit bones"),
    ),
    "wound_healing": IndicationSpec(
        "wound_healing", "skin", "wound",
        ("tissue repair", "inflammatory signalling (NF-kB)"),
        ("wounds", "wound", "sores", "ulcers", "cuts"),
    ),
    "headache": IndicationSpec(
        "headache", "head", "head pain",
        ("neurotransmission", "vascular tone (ACE/NO)"),
        ("head ache", "megrim", "migraine"),
    ),
    "epilepsy": IndicationSpec(
        "epilepsy", "brain", "seizure",
        ("neurotransmission",), ("falling sickness", "falling evil", "convulsions"),
    ),
    "eye_disorders": IndicationSpec(
        "eye_disorders", "eyes", "dimness of sight",
        ("oxidative stress (Nrf2/ARE)",),
        ("dimness of sight", "eyesight", "sore eyes", "eyes"),
    ),
    "low_back_pain": IndicationSpec(
        "low_back_pain", "back", "back pain",
        ("inflammatory signalling (NF-kB)",), ("pains of the back", "back pain"),
    ),
    "sciatica": IndicationSpec(
        "sciatica", "back", "nerve pain",
        ("inflammatory signalling (NF-kB)", "neurotransmission"), ("sciatica",),
    ),
    "pain": IndicationSpec(
        "pain", "systemic", "pain",
        ("inflammatory signalling (NF-kB)", "neurotransmission"),
        ("pains", "ache", "aches"),
    ),
    "fever": IndicationSpec(
        "fever", "systemic", "fever",
        ("inflammatory signalling (NF-kB)",), ("fevers", "ague", "hot fits"),
    ),
    "insomnia": IndicationSpec(
        "insomnia", "brain", "sleeplessness",
        ("neurotransmission",), ("sleep", "sleeplessness", "watchfulness"),
    ),
    "hypertension": IndicationSpec(
        "hypertension", "heart", "high blood pressure",
        ("vascular tone (ACE/NO)",), ("high blood pressure",),
    ),
    "common_cold": IndicationSpec(
        "common_cold", "nose", "cold",
        ("immune modulation", "mucosal protection"), ("cold", "catarrh", "rheum"),
    ),
    "irritable_bowel_syndrome": IndicationSpec(
        "irritable_bowel_syndrome", "intestine", "abdominal pain",
        ("gastrointestinal motility",), ("irritable bowel", "spastic colon"),
    ),
    "peptic_ulcer": IndicationSpec(
        "peptic_ulcer", "stomach", "gastric ulcer",
        ("mucosal protection",), ("ulcer of the stomach", "stomach ulcer"),
    ),
    "anxiety": IndicationSpec(
        "anxiety", "brain", "anxiety",
        ("neurotransmission",), ("anxiousness", "fear", "palpitations of the heart"),
    ),
    "osteoarthritis": IndicationSpec(
        "osteoarthritis", "joints", "joint pain",
        ("inflammatory signalling (NF-kB)",), ("joint pain", "gout", "arthritis"),
    ),
    "nausea": IndicationSpec(
        "nausea", "stomach", "nausea",
        ("gastrointestinal motility",), ("vomiting", "sickness of the stomach"),
    ),
    "vomiting": IndicationSpec(
        "vomiting", "stomach", "vomiting",
        ("gastrointestinal motility",), ("vomiting", "casting"),
    ),
    "cognitive_impairment": IndicationSpec(
        "cognitive_impairment", "brain", "memory loss",
        ("cerebral blood flow", "neurotransmission"),
        ("memory", "forgetfulness", "dullness of wit"),
    ),
    "fatigue": IndicationSpec(
        "fatigue", "systemic", "fatigue",
        ("metabolic energy",), ("weariness", "lassitude"),
    ),
    "malaria": IndicationSpec(
        "malaria", "blood", "malarial fever",
        ("inflammatory signalling (NF-kB)",), ("ague", "marsh fever"),
    ),
    "heart_failure": IndicationSpec(
        "heart_failure", "heart", "dropsy",
        ("cardiac contractility",), ("dropsy", "dropsy of the heart"),
    ),
    "motion_sickness": IndicationSpec(
        "motion_sickness", "brain", "vertigo",
        ("cholinergic",), ("sea sickness", "vertigo"),
    ),
    "chronic_pain": IndicationSpec(
        "chronic_pain", "systemic", "chronic pain",
        ("endocannabinoid", "neurotransmission"), ("chronic pain",),
    ),
    "depression": IndicationSpec(
        "depression", "brain", "low mood",
        ("neurotransmission",), ("melancholy", "sadness"),
    ),
    "burns": IndicationSpec(
        "burns", "skin", "burn",
        ("tissue repair",), ("burn", "scald"),
    ),
    "plague": IndicationSpec(
        "plague", "systemic", "epidemic fever",
        ("immune modulation",), ("the plague", "pestilence"),
    ),
    "palpitations": IndicationSpec(
        "palpitations", "heart", "palpitation",
        ("cardiac contractility", "neurotransmission"), ("palpitation",),
    ),
    "bleeding": IndicationSpec(
        "bleeding", "systemic", "haemorrhage",
        ("coagulation",), ("bleeding", "bloody flux"),
    ),
    "dropsy": IndicationSpec(
        "dropsy", "systemic", "oedema",
        ("vascular tone (ACE/NO)",), ("dropsy", "dropsie"),
    ),
    "swelling": IndicationSpec(
        "swelling", "systemic", "swelling",
        ("inflammatory signalling (NF-kB)",), ("swellings", "tumours"),
    ),
    "flux": IndicationSpec(
        "flux", "intestine", "diarrhoea",
        ("gastrointestinal motility",), ("the flux", "bloody flux", "looseness"),
    ),
    "constipation": IndicationSpec(
        "constipation", "intestine", "constipation",
        ("gastrointestinal motility",), ("costiveness",),
    ),
    "shortness_of_breath": IndicationSpec(
        "shortness_of_breath", "lungs", "breathlessness",
        ("mucosal protection",), ("shortness of breath", "short winded"),
    ),
    "menstrual_disorders": IndicationSpec(
        "menstrual_disorders", "reproductive", "menstrual irregularity",
        ("endocrine modulation",), ("courses", "flowers", "menstrual"),
    ),
    "lactation": IndicationSpec(
        "lactation", "reproductive", "lactation",
        ("endocrine modulation",), ("milk", "nursing"),
    ),
}


# --------------------------------------------------------------------------------------
# Evidence grades and traditions
# --------------------------------------------------------------------------------------

EVIDENCE_GRADES: Mapping[EvidenceGrade, str] = {
    EvidenceGrade.A: (
        "Multiple RCTs or a systematic review, or an established pharmacopoeial/regulatory "
        "indication. Modern controlled evidence exists."
    ),
    EvidenceGrade.B: (
        "At least one controlled clinical trial, or consistent results from more than one "
        "uncontrolled human study."
    ),
    EvidenceGrade.C: (
        "Observational human data, or preclinical (in vivo/in vitro) evidence plus "
        "consistent traditional use."
    ),
    EvidenceGrade.D: (
        "Traditional use only: attested in the historical corpus but not demonstrated in "
        "controlled modern study."
    ),
}

TRADITIONS: Mapping[Tradition, dict[str, str]] = {
    Tradition.GRAECO_ROMAN: {"region": "Mediterranean", "era": "c. 50 BCE – 400 CE"},
    Tradition.EUROPEAN_HERBAL: {"region": "Europe", "era": "c. 1500 – 1900"},
    Tradition.PARACELSIAN: {"region": "Europe", "era": "c. 1500 – 1700"},
    Tradition.GRAECO_ARABIC: {"region": "Middle East", "era": "c. 800 – 1300"},
    Tradition.UNANI: {"region": "Middle East / South Asia", "era": "c. 1000 – 1900"},
    Tradition.TCM: {"region": "China", "era": "c. 200 BCE – 1900"},
    Tradition.AYURVEDA: {"region": "South Asia", "era": "c. 500 BCE – 1900"},
    Tradition.NATIVE_AMERICAN: {"region": "North America", "era": "pre-colonial – present"},
    Tradition.AFRICAN: {"region": "Africa", "era": "pre-colonial – present"},
    Tradition.MESOAMERICAN: {"region": "Mesoamerica", "era": "pre-colonial – 1600"},
    Tradition.OCEANIA: {"region": "Pacific", "era": "pre-colonial – present"},
    Tradition.MODERN: {"region": "Global", "era": "1900 – present"},
    Tradition.UNKNOWN: {"region": "unknown", "era": "unknown"},
}

MODERN_TRADITIONS: frozenset[Tradition] = frozenset({Tradition.MODERN})


def is_modern_evidence(tradition: str, grade: str) -> bool:
    """Whether a use row counts as *modern direct evidence* for its indication.

    Two independent signals: an explicitly modern tradition, or an evidence grade of
    A/B (which by definition requires controlled human data).  Historical uses graded
    C/D never count as modern direct evidence.
    """
    return tradition == Tradition.MODERN.value or grade in {
        EvidenceGrade.A.value,
        EvidenceGrade.B.value,
    }


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------


def canonical_process(value: str) -> str | None:
    """Map a historical process token to a canonical process key, or ``None``."""
    key = value.strip().lower()
    if key in ALCHEMICAL_PROCESSES:
        return key
    for prefix, proc in PROCESS_SYNONYMS.items():
        if key.startswith(prefix):
            return proc
    return None


def processes_for_preparation(preparation: str) -> tuple[ProcessSemantics, ...]:
    """Return the ordered process pipeline a preparation implements."""
    keys = PREPARATION_PROCESSES.get(preparation.strip().lower(), ())
    return tuple(ALCHEMICAL_PROCESSES[k] for k in keys if k in ALCHEMICAL_PROCESSES)


def indication_spec(value: str) -> IndicationSpec | None:
    """Resolve an indication string (canonical or synonym) to an ``IndicationSpec``."""
    key = value.strip().lower()
    if key in INDICATIONS:
        return INDICATIONS[key]
    for spec in INDICATIONS.values():
        if key in spec.synonyms:
            return spec
    return None


def canonical_indication(value: str) -> str | None:
    spec = indication_spec(value)
    return spec.indication if spec else None


def compound_class_profile(name: str) -> CompoundClassProfile | None:
    """Look up a compound-class prior, normalising whitespace/hyphens to underscores."""
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    return COMPOUND_CLASSES.get(key)


def classes_for_indication(indication: str) -> frozenset[str]:
    """Compound classes whose textbook prior touches an indication's organ/pathway.

    Used by the chemotype-bridge discovery mode: a class is a *candidate* bridge when
    it is annotated with the indication itself, with the indication's organ system, or
    with one of the indication's mechanisms.
    """
    spec = indication_spec(indication)
    if spec is None:
        return frozenset()
    want_ind = {spec.indication, spec.symptom}
    want_path = set(spec.pathways)
    out: set[str] = set()
    for cls, prof in COMPOUND_CLASSES.items():
        if want_ind & set(prof.indications) or want_path & set(prof.pathways):
            out.add(cls)
    return frozenset(out)


def organ_for_indication(indication: str) -> str | None:
    spec = indication_spec(indication)
    return spec.organ if spec else None


def all_indications() -> tuple[str, ...]:
    return tuple(INDICATIONS)


def tradition_metadata(tradition: str) -> dict[str, str]:
    try:
        return TRADITIONS[Tradition(tradition)]
    except ValueError:
        return TRADITIONS[Tradition.UNKNOWN]
