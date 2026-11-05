"""SHENNONG ontology — Tier 0 of the knowledge graph.

Defines the entity types, the two medical vocabularies the corpus actually uses
(Chinese TCM and Indian Āyurveda, plus the Unani/Persian layer), the two alchemical
pharmacies (Chinese 炮制 *paozhi* and Indian rasaśāstra), and a curated first-principles
prior that maps natural-product **compound classes** to plausible molecular targets,
pathways and indications.

Design rules:

1.  **Curated priors are priors, not evidence.**  ``COMPOUND_CLASSES`` encodes textbook
    pharmacology of a compound *class*; it generates a hypothesis, never asserts that a
    particular drug contains an active molecule.  Every consumer labels the resulting
    claim a prior and attaches corpus evidence.
2.  **Process words are translated, not decoded.**  ``CHINESE_PROCESSES`` and
    ``AYURVEDIC_PROCESSES`` map each historical operation onto the physical chemistry it
    plausibly implements (temperature, solvent, which classes are enriched/destroyed).
    This is the project's novel data product (brief §2, class 2).
3.  **Toxicology is data, not therapy.**  Heavy-metal and toxic-alkaloid drugs
    (丹砂/朱砂, 雄黃, 輕粉, 鉛丹, 砒霜, 水銀; bhasma; Aconitum, Veratrum) are modelled as
    *toxicological subjects* with an explicit safety tier.  Nothing here is a
    recommendation, a dose, or a preparation protocol for human use.

We do **not** make the Galenic four humours first-class: SHENNONG's domain is Asian
medicine.  The Galenic/Avicennian hot–cold–dry–moist qualities survive only as Unani
(Ṭibb) metadata on a source, never as a graph edge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

# ======================================================================================
# Entity types (brief §5 Tier 0)
# ======================================================================================


class EntityType(str, Enum):
    TAXON = "taxon"
    DRUG_NAME = "drug_name"
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
    MERIDIAN = "meridian"
    FORMULA = "formula"
    ROLE = "role"
    INCOMPATIBILITY = "incompatibility"
    OBSERVATION = "observation"
    TRADITION = "tradition"
    SOURCE = "source"
    DOSHA = "dosha"
    TASTE = "taste"
    PHASE = "phase"


class EvidenceGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class Tradition(str, Enum):
    TCM = "tcm"
    AYURVEDA = "ayurveda"
    UNANI = "unani"
    KAMPO = "kampo"
    KOREAN = "korean"
    TIBETAN = "tibetan"
    PERSIAN = "persian"
    ALCHEMY = "alchemy"
    ACUPUNCTURE = "acupuncture"
    COMPARATIVE_CONTROL = "comparative-control"
    FOUNDATIONAL = "foundational"
    UNKNOWN = "unknown"


class PlantPart(str, Enum):
    ROOT = "root"
    LATERAL_ROOT = "lateral_root"
    RHIZOME = "rhizome"
    BARK = "bark"
    LEAF = "leaf"
    FLOWER = "flower"
    SEED = "seed"
    FRUIT = "fruit"
    WHOLE_HERB = "whole_herb"
    STEM = "stem"
    RESIN = "resin"
    MINERAL = "mineral"
    ANIMAL = "animal"


class Role(str, Enum):
    """君臣佐使 — the hierarchical roles of a formula component (brief §2 class 4)."""

    JUN = "jun"   # 君 emperor: principal drug, defines the formula's action
    CHEN = "chen"  # 臣 minister: supports/amplifies the emperor
    ZUO = "zuo"   # 佐 assistant: moderates, treats secondary signs, or opposes toxicity
    SHI = "shi"   # 使 courier/envoy: guides the formula, often to a channel or tissue


class IncompatibilityRule(str, Enum):
    SHIBA_FAN = "shiba_fan"    # 十八反 — eighteen antagonisms
    SHIJIU_WEI = "shijiu_wei"  # 十九畏 — nineteen mutual fears
    VIRUDDHA = "viruddha"      # Āyurvedic incompatible combinations


class Dosha(str, Enum):
    VATA = "vata"
    PITTA = "pitta"
    KAPHA = "kapha"


class Taste(str, Enum):
    """Ṣaḍrasa — the six tastes of Āyurveda."""

    MADHURA = "madhura"    # sweet
    AMLA = "amla"          # sour
    LAVANA = "lavana"      # salt
    KATU = "katu"          # pungent
    TIKTA = "tikta"        # bitter
    KASHAYA = "kashaya"    # astringent


class Phase(str, Enum):
    """五行 wǔxíng — the five phases of Chinese correlative cosmology."""

    WOOD = "wood"
    FIRE = "fire"
    EARTH = "earth"
    METAL = "metal"
    WATER = "water"


# ======================================================================================
# Traditions
# ======================================================================================

TRADITIONS: Mapping[Tradition, dict[str, str]] = {
    Tradition.TCM: {"region": "China", "era": "c. 200 BCE – present", "languages": "zh-Hant, zh-Hans"},
    Tradition.AYURVEDA: {"region": "South Asia", "era": "c. 500 BCE – present", "languages": "sa, sa-Latn"},
    Tradition.UNANI: {"region": "Middle East / South Asia", "era": "c. 800 – present", "languages": "ar, fa"},
    Tradition.KAMPO: {"region": "Japan", "era": "c. 1600 – present", "languages": "ja, zh-Hant"},
    Tradition.KOREAN: {"region": "Korea", "era": "c. 1400 – present", "languages": "ko, zh-Hant"},
    Tradition.TIBETAN: {"region": "Tibet / Himalaya", "era": "c. 800 – present", "languages": "bo, sa-Latn"},
    Tradition.PERSIAN: {"region": "Persia", "era": "c. 900 – present", "languages": "fa, ar"},
    Tradition.ALCHEMY: {"region": "China / India", "era": "c. 300 BCE – 1600", "languages": "zh-Hant, sa, sa-Latn"},
    Tradition.ACUPUNCTURE: {"region": "East Asia", "era": "c. 200 BCE – present", "languages": "zh-Hant"},
    Tradition.COMPARATIVE_CONTROL: {"region": "Europe", "era": "c. 1500 – 1900", "languages": "en, la"},
    Tradition.FOUNDATIONAL: {"region": "global", "era": "1900 – present", "languages": "en"},
    Tradition.UNKNOWN: {"region": "unknown", "era": "unknown", "languages": "unknown"},
}

#: Traditions whose use-attestations represent living Asian medical practice.
ASIAN_TRADITIONS: frozenset[str] = frozenset(
    {
        Tradition.TCM.value,
        Tradition.AYURVEDA.value,
        Tradition.UNANI.value,
        Tradition.KAMPO.value,
        Tradition.KOREAN.value,
        Tradition.TIBETAN.value,
        Tradition.PERSIAN.value,
        Tradition.ACUPUNCTURE.value,
        Tradition.ALCHEMY.value,
    }
)

#: Evidence grades that require controlled modern human data.
MODERN_GRADES: frozenset[str] = frozenset({EvidenceGrade.A.value, EvidenceGrade.B.value})

EVIDENCE_GRADES: Mapping[EvidenceGrade, str] = {
    EvidenceGrade.A: (
        "Multiple RCTs, a systematic review, or an established pharmacopoeial/regulatory "
        "indication: modern controlled evidence exists."
    ),
    EvidenceGrade.B: (
        "At least one controlled clinical trial, or consistent results across several "
        "uncontrolled human studies."
    ),
    EvidenceGrade.C: (
        "Observational human data, or preclinical (in vivo/in vitro) evidence plus "
        "consistent traditional use."
    ),
    EvidenceGrade.D: (
        "Traditional use only: attested in the classical corpus, never demonstrated in "
        "controlled modern study."
    ),
}


def is_modern_evidence(tradition: str, grade: str) -> bool:
    """Whether a use row counts as modern *direct* evidence for its indication."""
    return tradition == Tradition.FOUNDATIONAL.value or grade in MODERN_GRADES


# ======================================================================================
# 君臣佐使 formula roles
# ======================================================================================

ROLES: Mapping[Role, dict[str, str]] = {
    Role.JUN: {
        "zh": "君",
        "gloss": "emperor / principal",
        "function": (
            "The principal drug; its action defines the formula. Usually the largest dose "
            "and the target of the formula's main indication."
        ),
    },
    Role.CHEN: {
        "zh": "臣",
        "gloss": "minister",
        "function": (
            "Supports and amplifies the emperor's action, or treats the principal "
            "accompanying pattern."
        ),
    },
    Role.ZUO: {
        "zh": "佐",
        "gloss": "assistant",
        "function": (
            "Moderates the formula (reduces toxicity/irritancy of the emperor) or treats "
            "secondary signs; may be a 'zuo-shi' assistant-courier."
        ),
    },
    Role.SHI: {
        "zh": "使",
        "gloss": "courier / envoy",
        "function": (
            "Guides the formula to a channel/tissue or harmonises the ingredients. "
            "Frequently a candidate pharmacokinetic enhancer (e.g. 甘草, 生薑, 胡椒)."
        ),
    },
}

#: Drugs whose courier (使) function has a plausible modern PK explanation.
COURIER_BIOENHANCERS: Mapping[str, str] = {
    "Glycyrrhiza uralensis": (
        "Glycyrrhizin/saponin fraction is a documented CYP3A4 and P-gp modulator at "
        "pharmacological exposure; classical 使 role may be partly pharmacokinetic."
    ),
    "Glycyrrhiza glabra": "As for Glycyrrhiza uralensis (glycyrrhizin).",
    "Zingiber officinale": (
        "Gingerols/6-shogaol modulate P-gp and CYP3A4 in vitro; classical 使 use in "
        "桂枝湯 and 理中丸 is consistent with an absorption-enhancing role."
    ),
    "Piper nigrum": (
        "Piperine is a canonical bioenhancer: inhibits CYP3A4 and P-gp and increases "
        "systemic exposure of co-administered drugs."
    ),
    "Piper longum": "Piperine/piperlongumine: as for Piper nigrum.",
    "Cinnamomum cassia": (
        "Cinnamaldehyde/eugenol are weak CYP2C9/3A4 inhibitors; role as courier is "
        "plausible but weaker than piperine."
    ),
}

# ======================================================================================
# 五行 five phases — and the 取象比類 analogy map (negative control)
# ======================================================================================

PHASES: Mapping[Phase, dict[str, str]] = {
    Phase.WOOD: {"colour": "green/blue 青", "organ": "liver", "taste": "sour", "direction": "east"},
    Phase.FIRE: {"colour": "red 赤", "organ": "heart", "taste": "bitter", "direction": "south"},
    Phase.EARTH: {"colour": "yellow 黃", "organ": "spleen", "taste": "sweet", "direction": "centre"},
    Phase.METAL: {"colour": "white 白", "organ": "lungs", "taste": "pungent", "direction": "west"},
    Phase.WATER: {"colour": "black 黑", "organ": "kidney", "taste": "salty", "direction": "north"},
}

#: Colour morpheme → organ predicted by wǔxíng.  Used ONLY by the 取象比類 negative
#: control; never used to boost a discovery score.
COLOUR_ORGAN: Mapping[str, str] = {
    "青": "liver",
    "綠": "liver",
    "绿": "liver",
    "赤": "heart",
    "紅": "heart",
    "红": "heart",
    "朱": "heart",
    "丹": "heart",
    "黃": "spleen",
    "黄": "spleen",
    "白": "lungs",
    "黑": "kidney",
    "玄": "kidney",
}

#: Shape/habitat analogies that classical 取象比類 actually invokes in the herbals.
SHAPE_ORGAN: Mapping[str, str] = {
    "brain": "brain",
    "bone": "bone",
    "heart": "heart",
    "eye": "eyes",
    "ear": "ears",
    "kidney": "kidney",
    "blood": "blood",
}

QUXIANGBILEI_DOCTRINE = (
    "取象比類 ('grasping the image and drawing the analogy') holds that a drug's colour, "
    "shape, habitat or growth habit predicts the organ or indication it treats — red "
    "drugs enter the heart, black drugs the kidney, bone-shaped drugs the bones, and so "
    "on. The five-phase colour–organ correspondences are canonical (素問 陰陽應象大論). "
    "This is treated as a testable statistical hypothesis, not an assumption."
)

# ======================================================================================
# Ṣaḍrasa — six tastes, and the Āyurvedic doctrine being tested
# ======================================================================================

RASA_DOCTRINE: Mapping[Taste, dict[str, object]] = {
    Taste.MADHURA: {
        "en": "sweet",
        "doctrine": "nourishing, anabolic, increases kapha; builds tissue and strength",
        "predicted_actions": ("metabolic", "musculoskeletal", "reproductive"),
        "predicted_dosha_effect": {"vata": -1, "pitta": -1, "kapha": +1},
    },
    Taste.AMLA: {
        "en": "sour",
        "doctrine": "kindles digestive fire, increases pitta; appetising, carminative",
        "predicted_actions": ("digestive", "cardiovascular"),
        "predicted_dosha_effect": {"vata": -1, "pitta": +1, "kapha": -1},
    },
    Taste.LAVANA: {
        "en": "salt",
        "doctrine": "laxative, diuretic, digestive; increases pitta and kapha",
        "predicted_actions": ("digestive", "cardiovascular"),
        "predicted_dosha_effect": {"vata": -1, "pitta": +1, "kapha": +1},
    },
    Taste.KATU: {
        "en": "pungent",
        "doctrine": "kindles digestion, expels kapha, clears channels",
        "predicted_actions": ("digestive", "respiratory", "neuro"),
        "predicted_dosha_effect": {"vata": +1, "pitta": +1, "kapha": -1},
    },
    Taste.TIKTA: {
        "en": "bitter",
        "doctrine": "detoxifying, anti-inflammatory, destroys kapha and pitta",
        "predicted_actions": ("dermatologic", "hepatobiliary", "infectious", "digestive"),
        "predicted_dosha_effect": {"vata": +1, "pitta": -1, "kapha": -1},
    },
    Taste.KASHAYA: {
        "en": "astringent",
        "doctrine": "binds, stops discharge, consolidates; increases vata",
        "predicted_actions": ("digestive", "haematologic", "dermatologic"),
        "predicted_dosha_effect": {"vata": +1, "pitta": -1, "kapha": -1},
    },
}

#: Curated rasa assignments (primary taste first).  Taken from classical nighaṇṭu
#: descriptions of each drug; independent of the use-attestations we test against.
RASA_BY_DRUG: Mapping[str, tuple[str, ...]] = {
    "Glycyrrhiza glabra": ("madhura", "tikta", "kashaya"),
    "Withania somnifera": ("madhura", "tikta", "kashaya"),
    "Tinospora cordifolia": ("tikta", "kashaya", "madhura"),
    "Azadirachta indica": ("tikta", "kashaya"),
    "Terminalia chebula": ("kashaya", "madhura", "amla", "katu", "tikta"),
    "Terminalia bellirica": ("kashaya", "madhura", "tikta"),
    "Phyllanthus emblica": ("amla", "madhura", "tikta", "kashaya", "katu"),
    "Piper longum": ("katu", "tikta", "madhura"),
    "Piper nigrum": ("katu", "tikta"),
    "Zingiber officinale": ("katu", "madhura"),
    "Curcuma longa": ("tikta", "katu", "madhura"),
    "Bacopa monnieri": ("tikta", "kashaya", "madhura"),
    "Centella asiatica": ("tikta", "kashaya", "madhura"),
    "Asparagus racemosus": ("madhura", "tikta"),
    "Boswellia serrata": ("tikta", "kashaya", "madhura"),
    "Commiphora mukul": ("tikta", "katu", "kashaya"),
    "Saussurea lappa": ("tikta", "katu", "kashaya"),
    "Holarrhena antidysenterica": ("tikta", "kashaya"),
    "Picrorhiza kurroa": ("tikta", "kashaya"),
    "Berberis aristata": ("tikta", "kashaya"),
    "Rubia cordifolia": ("madhura", "tikta", "kashaya"),
    "Nardostachys jatamansi": ("tikta", "kashaya", "madhura"),
    "Santalum album": ("madhura", "tikta", "kashaya"),
    "Aquilaria agallocha": ("tikta", "katu", "kashaya"),
    "Cannabis sativa": ("tikta", "katu"),
    "Datura metel": ("katu", "tikta"),
    "Papaver somniferum": ("tikta", "kashaya"),
    "Acorus calamus": ("katu", "tikta"),
    "Cyperus rotundus": ("katu", "tikta", "kashaya"),
    "Boerhavia diffusa": ("madhura", "tikta", "kashaya"),
    "Aconitum ferox": ("katu", "tikta"),
}

RASA_DOCTRINE_STATEMENT = (
    "Āyurveda holds that the six tastes (ṣaḍrasa) predict drug action: sweet builds "
    "tissue, sour and salt kindle digestion, pungent clears channels, bitter detoxifies "
    "and cools, astringent binds and stops discharge (Caraka Saṃhitā Sūtrasthāna 26). "
    "We test whether the primary taste predicts the recorded indication's action class "
    "more often than chance."
)

# ======================================================================================
# 炮制 paozhi — Chinese processing operations → modern chemistry
# ======================================================================================


@dataclass(frozen=True)
class ProcessSemantics:
    """Translation of one historical process operation into modern chemical terms.

    ``temperature_c`` is the intended operating window, not a guarantee.  ``enriches`` /
    ``depletes`` name compound classes (see ``COMPOUND_CLASSES``) the operation carries
    into or destroys in the preparation.  ``mechanism`` is the one-line chemical
    rationale; ``historical_usage`` names the text in which the operation is attested.
    """

    name: str
    name_zh: str
    pinyin: str
    modern: str
    solvent: str | None
    temperature_c: tuple[float, float] | None
    enriches: frozenset[str]
    depletes: frozenset[str]
    mechanism: str
    historical_usage: str
    citation: str


CHINESE_PROCESSES: Mapping[str, ProcessSemantics] = {
    "pao": ProcessSemantics(
        name="pao", name_zh="炮", pinyin="páo",
        modern="roast / steam treatment (often with 甘草 or 黑豆)",
        solvent="water/steam", temperature_c=(95.0, 120.0),
        enriches=frozenset({"monoester_alkaloid"}),
        depletes=frozenset({"diester_alkaloid", "protein"}),
        mechanism=(
            "Prolonged heating hydrolyses ester bonds. In Aconitum the C8-acetyl and "
            "C14-benzoyl esters of aconitine/mesaconitine/hypaconitine are cleaved to "
            "monoesters (benzoylaconine) and then lipo-alkaloids, which are far less "
            "potent at voltage-gated Na+ channels."
        ),
        historical_usage="炮製 is the generic Lei Gong processing verb; 炮 fuzi is the canonical example.",
        citation="雷公炮炙論 (Lei Gong, c. 500 CE); 本草綱目 (1596)",
    ),
    "duan": ProcessSemantics(
        name="duan", name_zh="煅", pinyin="duàn",
        modern="calcination of mineral/animal drugs",
        solvent=None, temperature_c=(300.0, 800.0),
        enriches=frozenset({"mineral_salt", "heavy_metal"}),
        depletes=frozenset({"tannin", "alkaloid", "glycoside"}),
        mechanism=(
            "Carbonates and sulfides decompose to oxides; crystal water is lost; the "
            "product becomes more reactive/alkaline. Heavy metals remain heavy metals."
        ),
        historical_usage="煅 is standard for 牡蠣, 石膏, 赭石 and for 煅淬 of minerals.",
        citation="雷公炮炙論; later 炮製 compendia",
    ),
    "wei": ProcessSemantics(
        name="wei", name_zh="煨", pinyin="wēi",
        modern="slow enclosed roasting (paper, dough or ash)",
        solvent=None, temperature_c=(120.0, 200.0),
        enriches=frozenset({"resin"}),
        depletes=frozenset({"monoterpenoid", "phenylpropanoid"}),
        mechanism=(
            "Enclosed gentle heat volatilises irritant essential-oil fractions without "
            "charting the drug — e.g. 煨肉豆蔻 reduces myristicin/oil irritancy."
        ),
        historical_usage="煨 is used for aromatic seeds (肉豆蔻, 木香).",
        citation="炮製 texts; 本草綱目",
    ),
    "cui": ProcessSemantics(
        name="cui", name_zh="淬", pinyin="cuì",
        modern="quench red-hot mineral into vinegar/water/urine",
        solvent="vinegar/water", temperature_c=(20.0, 300.0),
        enriches=frozenset({"mineral_salt"}),
        depletes=frozenset({"heavy_metal"}),
        mechanism=(
            "Thermal shock cracks the solid; the quench liquid dissolves and surface-"
            "oxidises it, and vinegar can form acetates. Does not necessarily remove "
            "the toxic metal."
        ),
        historical_usage="煅淬 is paired with 煅 for mineral drugs.",
        citation="雷公炮炙論",
    ),
    "zheng": ProcessSemantics(
        name="zheng", name_zh="蒸", pinyin="zhēng",
        modern="steam heating",
        solvent="steam", temperature_c=(95.0, 105.0),
        enriches=frozenset({"aglycone"}),
        depletes=frozenset({"glycoside", "polysaccharide", "protein", "diester_alkaloid"}),
        mechanism=(
            "Glycoside hydrolysis and starch gelatinisation; ester hydrolysis for "
            "Aconitum; Maillard chemistry for 熟地黃 (nine蒸nine曬 → 5-HMF)."
        ),
        historical_usage="九蒸九曬 of 地黃/何首烏; 蒸半夏 with ginger juice.",
        citation="雷公炮炙論; 本草綱目",
    ),
    "zhu": ProcessSemantics(
        name="zhu", name_zh="煮", pinyin="zhǔ",
        modern="boiling in water or an auxiliary decoction",
        solvent="water", temperature_c=(95.0, 100.0),
        enriches=frozenset({"polysaccharide", "glycoside", "tannin"}),
        depletes=frozenset({"monoterpenoid", "diester_alkaloid"}),
        mechanism=(
            "Aqueous hydrolysis/extraction; the classical 甘草+黑豆 co-decoction of "
            "Aconitum adds a pH/co-solvent effect and further ester hydrolysis."
        ),
        historical_usage="煮 fuzi with 甘草/黑豆; the 先煎 rule in 傷寒論.",
        citation="傷寒論 (220 CE); 本草綱目",
    ),
    "chao": ProcessSemantics(
        name="chao", name_zh="炒", pinyin="chǎo",
        modern="dry-fry",
        solvent=None, temperature_c=(120.0, 200.0),
        enriches=frozenset({"resin"}),
        depletes=frozenset({"monoterpenoid", "protein"}),
        mechanism=(
            "Volatilisation and partial thermal decomposition; enzyme inactivation; "
            "short dry-fry does NOT hydrolyse diterpene diesters — a testable limitation."
        ),
        historical_usage="炒 is the commonest dry operation; 炒炭 for haemostatics.",
        citation="雷公炮炙論; 炮製 compendia",
    ),
    "vinegar_fry": ProcessSemantics(
        name="vinegar_fry", name_zh="醋炙", pinyin="cù zhì",
        modern="vinegar-frying",
        solvent="vinegar (acetic acid)", temperature_c=(100.0, 150.0),
        enriches=frozenset({"alkaloid", "mineral_salt"}),
        depletes=frozenset({"tannin"}),
        mechanism=(
            "Acetic acid forms salts/acetates with alkaloids and modifies their "
            "protonation, improving extraction and altering irritancy."
        ),
        historical_usage="醋炙 is canonical for 延胡索 (enhancing alkaloid extraction) and 甘遂 (reducing toxicity).",
        citation="雷公炮炙論; 炮製 compendia",
    ),
    "honey_fry": ProcessSemantics(
        name="honey_fry", name_zh="蜜炙", pinyin="mì zhì",
        modern="honey-frying",
        solvent="honey (sugar)", temperature_c=(100.0, 150.0),
        enriches=frozenset({"glycoside"}),
        depletes=frozenset({"protein"}),
        mechanism=(
            "Sugars complex/modify phenolics and saponins, reduce surface irritation, "
            "and produce Maillard products; classical 'tonifying' claims are not "
            "mechanistically established."
        ),
        historical_usage="蜜炙 甘草/黃芪/款冬花; standard in 炮製.",
        citation="雷公炮炙論; 炮製 compendia",
    ),
    "wine_fry": ProcessSemantics(
        name="wine_fry", name_zh="酒炙", pinyin="jiǔ zhì",
        modern="wine-frying",
        solvent="ethanol/water", temperature_c=(80.0, 150.0),
        enriches=frozenset({"alkaloid", "phenylpropanoid"}),
        depletes=frozenset({"tannin"}),
        mechanism=(
            "Ethanol improves extraction of medium-polar alkaloids and alters the "
            "anthraquinone/tannin balance (酒大黃 softer purgation)."
        ),
        historical_usage="酒炙 大黃/當歸/白芍.",
        citation="雷公炮炙論; 本草綱目",
    ),
    "bran_fry": ProcessSemantics(
        name="bran_fry", name_zh="麩炒", pinyin="fū chǎo",
        modern="bran-frying",
        solvent=None, temperature_c=(120.0, 180.0),
        enriches=frozenset({"sesquiterpene_lactone"}),
        depletes=frozenset({"protein"}),
        mechanism="Mild heat absorption and partial volatilisation; mostly a dose/irritancy control.",
        historical_usage="麩炒 貝母/白朮/枳殼.",
        citation="雷公炮炙論",
    ),
    "fermentation": ProcessSemantics(
        name="fermentation", name_zh="發酵", pinyin="fā jiào",
        modern="fermentation / 麴 (qu) preparation",
        solvent="aqueous", temperature_c=(15.0, 37.0),
        enriches=frozenset({"aglycone", "alcohol"}),
        depletes=frozenset({"glycoside", "polysaccharide"}),
        mechanism=(
            "Microbial hydrolysis, decarboxylation and reduction; 紅麴 produces "
            "monacolins (HMG-CoA reductase inhibitors), 神麴 changes the matrix."
        ),
        historical_usage="神麴, 半夏麴, 紅麴.",
        citation="炮製 compendia; 本草綱目",
    ),
    "water_flying": ProcessSemantics(
        name="water_flying", name_zh="水飛", pinyin="shuǐ fēi",
        modern="levigation / water grinding and settling",
        solvent="water", temperature_c=(15.0, 30.0),
        enriches=frozenset({"mineral_salt", "heavy_metal"}),
        depletes=frozenset({"polysaccharide"}),
        mechanism=(
            "Particle-size fractionation of insoluble minerals. It reduces particle size "
            "but does NOT remove arsenic or mercury — a critical distinction."
        ),
        historical_usage="水飛 朱砂/雄黃/爐甘石.",
        citation="雷公炮炙論",
    ),
    "sublimation": ProcessSemantics(
        name="sublimation", name_zh="昇", pinyin="shēng",
        modern="sublimation (昇/飛)",
        solvent=None, temperature_c=(100.0, 400.0),
        enriches=frozenset({"heavy_metal"}),
        depletes=frozenset({"polysaccharide", "protein"}),
        mechanism=(
            "Volatile solids (sal ammoniac, calomel, sulphur) vaporise and re-condense. "
            "In mercury pharmacy this concentrates the toxic species."
        ),
        historical_usage="昇 輕粉 (calomel); 昇/飛 in alchemical 丹方.",
        citation="抱朴子; 丹方 texts",
    ),
    "fu": ProcessSemantics(
        name="fu", name_zh="伏", pinyin="fú",
        modern="'subdue' — stabilise or complex a reactive mineral",
        solvent="water/other", temperature_c=(100.0, 600.0),
        enriches=frozenset({"mineral_salt"}),
        depletes=frozenset({"heavy_metal"}),
        mechanism=(
            "In alchemical 伏火, reactive substances are heated with partners (e.g. salt, "
            "sulphur) to form more stable compounds. The toxic metal is often still present."
        ),
        historical_usage="伏火/伏 in 丹方; 伏龍肝 named for it.",
        citation="抱朴子; 周易參同契 commentary",
    ),
    "xianjian": ProcessSemantics(
        name="xianjian", name_zh="先煎", pinyin="xiān jiān",
        modern="decoct-first instruction",
        solvent="water", temperature_c=(95.0, 100.0),
        enriches=frozenset({"monoester_alkaloid"}),
        depletes=frozenset({"diester_alkaloid"}),
        mechanism=(
            "Extended boiling of the dangerous drug before the rest are added: an "
            "operational hydrolysis protocol for diterpene diesters."
        ),
        historical_usage="先煎 麻黃/附子 in 傷寒論.",
        citation="傷寒論 (220 CE)",
    ),
    "washed": ProcessSemantics(
        name="washed", name_zh="湯洗", pinyin="tāng xǐ",
        modern="hot-water washing",
        solvent="hot water", temperature_c=(60.0, 100.0),
        enriches=frozenset({"polysaccharide"}),
        depletes=frozenset({"protein", "glycoside"}),
        mechanism=(
            "Removes surface mucilage, calcium-oxalate raphides and irritant lectins "
            "(Pinellia); a physical purification, not a chemical detox."
        ),
        historical_usage="湯洗 ten times for 半夏.",
        citation="雷公炮炙論",
    ),
    "remove_nodes": ProcessSemantics(
        name="remove_nodes", name_zh="去節", pinyin="qù jié",
        modern="removal of stem nodes",
        solvent=None, temperature_c=None,
        enriches=frozenset({"alkaloid"}),
        depletes=frozenset({"tannin"}),
        mechanism="Standardises ephedrine content across stem segments.",
        historical_usage="去節 麻黃.",
        citation="炮製 compendia",
    ),
    "honey_pill": ProcessSemantics(
        name="honey_pill", name_zh="蜜丸", pinyin="mì wán",
        modern="honeyed pill",
        solvent="honey", temperature_c=(60.0, 100.0),
        enriches=frozenset({"glycoside", "polysaccharide"}),
        depletes=frozenset({"monoterpenoid"}),
        mechanism="Slow-release sugar matrix; masks irritancy.",
        historical_usage="蜜丸 in 傷寒論/東醫寶鑑.",
        citation="傷寒論; 東醫寶鑑",
    ),
}

# --------------------------------------------------------------------------------------
# Rasaśāstra — Indian alchemical pharmacy
# --------------------------------------------------------------------------------------

AYURVEDIC_PROCESSES: Mapping[str, ProcessSemantics] = {
    "bhasma": ProcessSemantics(
        name="bhasma", name_zh="bhasma", pinyin="bhasma",
        modern="calcination of a metal/mineral to an oxide powder",
        solvent=None, temperature_c=(400.0, 800.0),
        enriches=frozenset({"mineral_salt"}),
        depletes=frozenset({"heavy_metal"}),
        mechanism=(
            "Repeated incineration converts metals to oxides (Fe2O3, CaO, HgO, As2O3 "
            "depending on the metal) and to nanoparticle form. Particle size falls; "
            "elemental toxicity does not disappear."
        ),
        historical_usage="bhasma is the defining product of rasaśāstra.",
        citation="Rasa Ratna Samuccaya (c. 1200 CE); Rasaśāstra texts",
    ),
    "shodhana": ProcessSemantics(
        name="shodhana", name_zh="śodhana", pinyin="shodhana",
        modern="purification / detoxification procedure (grinding with herbal juices)",
        solvent="herbal juices/water", temperature_c=(20.0, 100.0),
        enriches=frozenset({"aglycone"}),
        depletes=frozenset({"protein"}),
        mechanism=(
            "Wet grinding/complexation partially oxidises the metal surface and forms "
            "organometallic complexes. Claims of complete detoxification are not "
            "supported for mercury; this is a measured, open question."
        ),
        historical_usage="śodhana precedes māraṇa for nearly every metal.",
        citation="Rasa Ratna Samuccaya; Rasaśāstra texts",
    ),
    "marana": ProcessSemantics(
        name="marana", name_zh="māraṇa", pinyin="māraṇa",
        modern="'killing' — incineration to bhasma",
        solvent=None, temperature_c=(400.0, 900.0),
        enriches=frozenset({"mineral_salt"}),
        depletes=frozenset({"heavy_metal"}),
        mechanism="High-temperature oxidation; often repeated with herbal media.",
        historical_usage="māraṇa paired with śodhana.",
        citation="Rasa Ratna Samuccaya",
    ),
    "jarana": ProcessSemantics(
        name="jarana", name_zh="jāraṇa", pinyin="jāraṇa",
        modern="'ripening' — fusion with a reagent to convert a mineral",
        solvent=None, temperature_c=(300.0, 700.0),
        enriches=frozenset({"mineral_salt"}),
        depletes=frozenset({"heavy_metal"}),
        mechanism="Reagent fusion (e.g. with sulphur/borax) changes the mineral phase.",
        historical_usage="jāraṇa in mercurial processing.",
        citation="Rasaśāstra texts",
    ),
    "murchana": ProcessSemantics(
        name="murchana", name_zh="mūrchana", pinyin="mūrchana",
        modern="'fainting' — trituration of mercury with herbs",
        solvent="herbal juices", temperature_c=(20.0, 60.0),
        enriches=frozenset({"aglycone"}),
        depletes=frozenset({"heavy_metal"}),
        mechanism="Mechanical/chemical trituration of mercury with organic matter.",
        historical_usage="mūrchana is an early mercury-processing step.",
        citation="Rasaśāstra texts",
    ),
}

#: Every process, keyed by canonical name (Chinese + Ayurvedic).
ALL_PROCESSES: Mapping[str, ProcessSemantics] = {**CHINESE_PROCESSES, **AYURVEDIC_PROCESSES}

#: Historical process surface forms (zh, pinyin, sa, IAST, en) → canonical key.
PROCESS_SYNONYMS: Mapping[str, str] = {
    "炮": "pao", "炮製": "pao", "炮制": "pao", "炮炙": "pao",
    "煅": "duan", "煆": "duan", "煨": "wei", "淬": "cui", "煅淬": "cui",
    "蒸": "zheng", "煮": "zhu", "炒": "chao", "炒炭": "chao",
    "醋炙": "vinegar_fry", "醋炒": "vinegar_fry", "醋製": "vinegar_fry", "醋制": "vinegar_fry",
    "蜜炙": "honey_fry", "蜜製": "honey_fry", "蜜制": "honey_fry", "蜜丸": "honey_pill",
    "酒炙": "wine_fry", "酒炒": "wine_fry", "酒浸": "wine_fry", "酒製": "wine_fry",
    "麩炒": "bran_fry", "麸炒": "bran_fry",
    "發酵": "fermentation", "发酵": "fermentation", "麴": "fermentation", "麯": "fermentation", "神麴": "fermentation",
    "水飛": "water_flying", "水飞": "water_flying",
    "昇": "sublimation", "升": "sublimation", "飛": "sublimation", "飞": "sublimation",
    "伏": "fu", "伏火": "fu",
    "先煎": "xianjian", "湯洗": "washed", "汤洗": "washed", "去節": "remove_nodes", "去节": "remove_nodes",
    "去蘆頭": "remove_nodes", "去芦头": "remove_nodes", "去皮臍": "remove_nodes", "去皮脐": "remove_nodes",
    "切焙": "chao", "曬乾": "chao", "晒干": "chao",
    "燒": "duan", "烧": "duan", "鍊": "duan", "炼": "duan", "煆": "duan",
    "roast": "pao", "steam": "zheng", "boil": "zhu", "decoct": "zhu", "fry": "chao",
    "calcine": "duan", "calcination": "duan", "quench": "cui", "sublime": "sublimation",
    "ferment": "fermentation", "wash": "washed",
    "bhasma": "bhasma", "śodhana": "shodhana", "shodhana": "shodhana",
    "māraṇa": "marana", "marana": "marana", "jāraṇa": "jarana", "jarana": "jarana",
    "mūrchana": "murchana", "murchana": "murchana",
}

# ======================================================================================
# Compound-class prior
# ======================================================================================


@dataclass(frozen=True)
class CompoundClassProfile:
    """Engineering + pharmacological prior for one natural-product class.

    polarity / volatility / thermolability ∈ [0,1].  ``targets``/``pathways``/
    ``indications`` are hypothesis-generating priors, never assertions about a plant.
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


def _p(*args, **kwargs) -> CompoundClassProfile:  # compact constructor
    return CompoundClassProfile(*args, **kwargs)


COMPOUND_CLASSES: Mapping[str, CompoundClassProfile] = {
    "sesquiterpene_lactone": _p(
        "sesquiterpene_lactone", 0.60, 0.10, 0.60,
        ("NF-kB", "IL-6", "Na+/K+-ATPase"),
        ("inflammatory signalling (NF-kB)", "antimalarial haem detoxification"),
        ("inflammation", "tumour", "malaria", "cough"),
        "Electrophilic alpha-methylene-butyrolactones alkylate NF-kB proteins "
        "(parthenolide is the prototype). Artemisinin is the antimalarial outlier: its "
        "endoperoxide is activated by haem iron.",
        "canonical natural-products pharmacology; artemisinin (Tu Youyou 1972)",
    ),
    "monoterpenoid": _p(
        "monoterpenoid", 0.15, 0.90, 0.75,
        ("GABA_A", "TRPA1", "TRPV1", "AChE"),
        ("neurotransmission", "gastrointestinal motility"),
        ("anxiety", "pain", "cough", "dyspepsia", "insomnia"),
        "Volatile, steam-distillable, lipophilic. Menthol/thymol act on TRP channels; "
        "many are weak GABA_A modulators.",
        "canonical natural-products pharmacology",
    ),
    "monoterpenoid_glycoside": _p(
        "monoterpenoid_glycoside", 0.75, 0.02, 0.55,
        ("TRPA1", "COX-1/2"),
        ("inflammatory signalling (NF-kB)", "neurotransmission"),
        ("pain", "inflammation", "abdominal_pain"),
        "Paeoniflorin is a polar, poorly volatile monoterpene glycoside; activity is "
        "modest and bioavailability-limited.",
        "canonical natural-products pharmacology (paeoniflorin)",
    ),
    "sesquiterpenoid": _p(
        "sesquiterpenoid", 0.25, 0.70, 0.60,
        ("TRPA1", "COX-1/2"),
        ("inflammatory signalling (NF-kB)",),
        ("inflammation", "skin_disease", "abdominal_pain"),
        "Bisabolol, santalol, costunolide relatives: anti-inflammatory and skin-soothing; "
        "some are volatile (sandalwood) and distillation-enriched.",
        "canonical natural-products pharmacology",
    ),
    "diterpenoid": _p(
        "diterpenoid", 0.40, 0.03, 0.45,
        ("protein kinase C", "Na+ channel", "NF-kB"),
        ("inflammatory signalling (NF-kB)", "neurotransmission"),
        ("inflammation", "tumour", "pain"),
        "A broad class: tanshinones (anti-inflammatory), phorbol esters (potent PKC "
        "activators and tumour promoters, very toxic), ingenol derivatives.",
        "canonical natural-products pharmacology",
    ),
    "triterpenoid": _p(
        "triterpenoid", 0.35, 0.01, 0.40,
        ("NF-kB", "Nrf2", "glycogen metabolism"),
        ("inflammatory signalling (NF-kB)", "oxidative stress (Nrf2/ARE)"),
        ("inflammation", "tumour", "dyspepsia"),
        "Boswellic acids, pachymic acid, azadirachtin: multi-target, mostly "
        "anti-inflammatory.",
        "canonical natural-products pharmacology",
    ),
    "triterpenoid_saponin": _p(
        "triterpenoid_saponin", 0.65, 0.01, 0.50,
        ("membrane sterols", "11beta-HSD2", "H+/K+-ATPase", "NF-kB"),
        ("mucosal protection", "inflammatory signalling (NF-kB)", "immune modulation"),
        ("cough", "dyspepsia", "inflammation", "fatigue"),
        "Surface-active glycosides. Glycyrrhizin inhibits 11beta-HSD2 (mineralocorticoid "
        "effect: hypertension/oedema risk); ginsenosides have low oral bioavailability.",
        "canonical natural-products pharmacology (glycyrrhizin, ginsenosides)",
    ),
    "steroidal_saponin": _p(
        "steroidal_saponin", 0.65, 0.01, 0.50,
        ("membrane sterols", "oestrogen receptor"),
        ("endocrine modulation", "mucosal protection"),
        ("cough", "lactation", "menstrual_disorders"),
        "Diosgenin, shatavarin, ophiopogonin: membrane-active; several are used as "
        "hormonal and expectorant drugs.",
        "canonical natural-products pharmacology",
    ),
    "steroidal": _p(
        "steroidal", 0.30, 0.01, 0.40,
        ("steroid receptors", "NF-kB"),
        ("endocrine modulation",),
        ("inflammation", "menstrual_disorders"),
        "Guggulsterones are steroid-like; endocrine claims are weakly supported.",
        "canonical natural-products pharmacology",
    ),
    "steroidal_lactone": _p(
        "steroidal_lactone", 0.45, 0.01, 0.45,
        ("NF-kB", "Hsp90", "GABA_A"),
        ("inflammatory signalling (NF-kB)", "neurotransmission"),
        ("anxiety", "inflammation", "fatigue"),
        "Withanolides (Ashwagandha): adaptogen claims are popular; human evidence is "
        "modest and product-variable.",
        "canonical natural-products pharmacology (withanolides)",
    ),
    "flavonoid": _p(
        "flavonoid", 0.60, 0.02, 0.30,
        ("COX-1/2", "LOX", "Nrf2", "GABA_A"),
        ("oxidative stress (Nrf2/ARE)", "inflammatory signalling (NF-kB)"),
        ("inflammation", "anxiety", "hypertension", "eye_disorders"),
        "Broad, weak polypharmacology; low oral bioavailability for many aglycones.",
        "canonical natural-products pharmacology",
    ),
    "chromone": _p(
        "chromone", 0.50, 0.02, 0.30,
        ("COX-1/2", "Nrf2"),
        ("inflammatory signalling (NF-kB)",),
        ("inflammation", "pain"),
        "Saposhnikovia chromones (cimifugin, prim-O-glucosylcimifugin): anti-inflammatory.",
        "canonical natural-products pharmacology",
    ),
    "coumarin": _p(
        "coumarin", 0.45, 0.05, 0.30,
        ("vitamin K epoxide reductase", "CYP450"),
        ("coagulation",),
        ("inflammation", "swelling", "pain"),
        "Imperatorin and relatives are phototoxic and CYP-modulating; some coumarins are "
        "anticoagulant precursors.",
        "canonical natural-products pharmacology",
    ),
    "lignan": _p(
        "lignan", 0.50, 0.01, 0.30,
        ("oestrogen receptor", "Nrf2"),
        ("endocrine modulation", "oxidative stress (Nrf2/ARE)"),
        ("menstrual_disorders", "inflammation", "insomnia"),
        "Schisandrin, honokiol, eleutheroside E: phytoestrogenic/antioxidant.",
        "canonical natural-products pharmacology",
    ),
    "phenolic_acid": _p(
        "phenolic_acid", 0.70, 0.02, 0.30,
        ("COX-1/2", "Nrf2"),
        ("oxidative stress (Nrf2/ARE)",),
        ("inflammation", "wound_healing", "skin_disease"),
        "Ferulic, salvianolic, paeonol: antioxidants and weak enzyme inhibitors.",
        "canonical natural-products pharmacology",
    ),
    "phenylpropanoid": _p(
        "phenylpropanoid", 0.30, 0.80, 0.65,
        ("TRPA1", "CYP450"),
        ("neurotransmission", "gastrointestinal motility"),
        ("dyspepsia", "cough", "pain", "diarrhoea"),
        "Cinnamaldehyde, eugenol, asarone: volatile aromatics; asarone is genotoxic at "
        "high dose (beta-asarone).",
        "canonical natural-products pharmacology",
    ),
    "tannin": _p(
        "tannin", 0.75, 0.01, 0.40,
        ("protein binding",),
        ("mucosal protection",),
        ("diarrhoea", "wound_healing", "inflammation"),
        "Polyphenols that cross-link proteins: astringent, antimicrobial, "
        "anti-diarrhoeal. High doses are hepatotoxic and antinutritive.",
        "canonical natural-products pharmacology",
    ),
    "alkaloid": _p(
        "alkaloid", 0.50, 0.15, 0.45,
        ("opioid receptor", "AChE", "Na+ channel", "5-HT2A", "dopamine D2", "Na+/K+-ATPase"),
        ("neurotransmission", "cholinergic", "opioidergic", "cardiac contractility"),
        ("pain", "insomnia", "fever", "malaria", "diarrhoea", "cough"),
        "A heterogeneous class — receptor prediction is class-level only. Many are "
        "potently toxic (Aconitum, Veratrum, Datura, Papaver) and dose-critical; this "
        "system never proposes dosing.",
        "canonical natural-products pharmacology",
    ),
    "diester_alkaloid": _p(
        "diester_alkaloid", 0.50, 0.05, 0.85,
        ("Na+ channel (open state)",),
        ("neurotransmission",),
        (),
        "Aconitine/mesaconitine/hypaconitine: voltage-gated Na+ channel activators; "
        "raw Aconitum is lethal. Hydrolysed to monoesters by 炮.",
        "canonical toxicology of Aconitum diterpene alkaloids",
    ),
    "monoester_alkaloid": _p(
        "monoester_alkaloid", 0.50, 0.05, 0.70,
        ("Na+ channel (weak)",),
        ("neurotransmission",),
        (),
        "Benzoylaconine-type monoesters: ~100-fold weaker Na+ channel activity than the "
        "diesters; the product of classical processing.",
        "canonical toxicology of Aconitum diterpene alkaloids",
    ),
    "aristolochic_acid": _p(
        "aristolochic_acid", 0.55, 0.01, 0.40,
        ("DNA adduct formation", "OAT1/OAT3 uptake"),
        ("nephrotoxicity", "mutagenesis"),
        (),
        "Aristolochic acids form covalent DNA adducts and cause aristolochic-acid "
        "nephropathy and urothelial cancer. Never a therapeutic mechanism; the basis of "
        "the name-collision safety class.",
        "IARC Group 1 (aristolochic acid); Debelle et al. 2008",
    ),
    "pyrrolizidine_alkaloid": _p(
        "pyrrolizidine_alkaloid", 0.50, 0.01, 0.50,
        ("hepatic CYP activation",),
        ("hepatotoxicity",),
        (),
        "Metabolised to pyrrole esters that alkylate hepatic DNA: veno-occlusive "
        "disease risk. A safety signal, never a therapeutic mechanism.",
        "canonical toxicology of pyrrolizidine alkaloids",
    ),
    "cyanogenic_glycoside": _p(
        "cyanogenic_glycoside", 0.70, 0.01, 0.50,
        ("cytochrome c oxidase (via HCN)",),
        ("cellular respiration inhibition",),
        (),
        "Amygdalin releases hydrogen cyanide on hydrolysis. Toxicity is the point; "
        "laetrile claims are not evidence.",
        "canonical toxicology of cyanogenic glycosides",
    ),
    "cardiac_glycoside": _p(
        "cardiac_glycoside", 0.60, 0.01, 0.40,
        ("Na+/K+-ATPase",),
        ("cardiac contractility",),
        ("heart_failure",),
        "Narrow therapeutic index. Periplocoside from 香加皮 is a cardenolide and the "
        "basis of its toxicity; this system flags, never doses.",
        "canonical pharmacology of cardiac glycosides",
    ),
    "anthraquinone": _p(
        "anthraquinone", 0.50, 0.01, 0.40,
        ("bacterial membrane", "Na+/K+-ATPase"),
        ("gastrointestinal motility",),
        ("constipation", "diarrhoea", "skin_disease"),
        "Emodin, rhein, alizarin: laxative or antimicrobial depending on structure; "
        "chronic anthraquinone use causes melanosis coli.",
        "canonical natural-products pharmacology",
    ),
    "curcuminoid": _p(
        "curcuminoid", 0.50, 0.01, 0.45,
        ("NF-kB", "Nrf2", "EGFR"),
        ("inflammatory signalling (NF-kB)",),
        ("arthritis", "inflammation"),
        "Curcumin has very low oral bioavailability; the class prior is strong, the "
        "pharmacokinetics are the failure mode.",
        "canonical natural-products pharmacology (curcumin)",
    ),
    "gingerol": _p(
        "gingerol", 0.40, 0.10, 0.50,
        ("TRPV1", "5-HT3"),
        ("gastrointestinal motility",),
        ("nausea", "vomiting", "dyspepsia"),
        "Gingerols are TRPV1 agonists; antiemetic evidence is moderate.",
        "canonical natural-products pharmacology (gingerols)",
    ),
    "cannabinoid": _p(
        "cannabinoid", 0.20, 0.10, 0.55,
        ("CNR1", "CNR2", "TRPV1"),
        ("endocannabinoid", "neurotransmission"),
        ("pain", "nausea", "epilepsy", "anxiety"),
        "Phytocannabinoids are lipophilic; THC is psychoactive and controlled. "
        "Research claims only.",
        "canonical natural-products pharmacology",
    ),
    "organosulfur": _p(
        "organosulfur", 0.30, 0.70, 0.50,
        ("thiol groups", "H2S", "bacterial membrane"),
        ("oxidative stress (Nrf2/ARE)", "vascular tone (ACE/NO)"),
        ("hypertension", "common_cold"),
        "Allicin/ajoene: thiol-reactive, antimicrobial.",
        "canonical natural-products pharmacology",
    ),
    "polysaccharide": _p(
        "polysaccharide", 0.95, 0.00, 0.20,
        ("immune receptors (dectin-1, TLR)",),
        ("immune modulation", "mucosal protection"),
        ("fatigue", "cough", "wound_healing"),
        "Non-digestible polysaccharides are immunomodulatory and demulcent; activity is "
        "largely local/topical.",
        "canonical natural-products pharmacology",
    ),
    "mucilage": _p(
        "mucilage", 0.95, 0.00, 0.20,
        ("mucosal surface",),
        ("mucosal protection",),
        ("cough", "dyspepsia", "wound_healing"),
        "Physical demulcent; heat and ethanol degrade it.",
        "canonical natural-products pharmacology",
    ),
    "resin": _p(
        "resin", 0.10, 0.02, 0.40,
        ("bacterial membrane",),
        ("mucosal protection",),
        ("wound_healing", "pain"),
        "Lipophilic mixtures; antimicrobial and occlusive.",
        "canonical natural-products pharmacology",
    ),
    "fatty_acid": _p(
        "fatty_acid", 0.10, 0.01, 0.40,
        ("membrane lipids",),
        ("tissue repair",),
        ("wound_healing", "skin_disease"),
        "Pinellic acid and other fatty acids are emollient/anti-inflammatory.",
        "canonical natural-products pharmacology",
    ),
    "protein": _p(
        "protein", 0.90, 0.00, 0.75,
        ("immune receptors", "ribosome (toxins)"),
        ("immune modulation", "toxicity"),
        ("wound_healing", "immune modulation"),
        "Includes keratin/collagen (horn, bone, scale: largely indigestible), "
        "trichosanthin (ribosome-inactivating, toxic) and Pinellia lectins (irritant). "
        "Protein identity drives both mechanism and toxicity.",
        "canonical biochemistry",
    ),
    "glycoside": _p(
        "glycoside", 0.75, 0.01, 0.50,
        ("variable",),
        ("variable",),
        ("cough", "dyspepsia", "diarrhoea"),
        "Generic category when the aglycone class is unresolved; hydrolysis by gut "
        "microbiota or processing is often required for activity.",
        "canonical natural-products chemistry",
    ),
    "iridoid_glycoside": _p(
        "iridoid_glycoside", 0.80, 0.01, 0.55,
        ("NF-kB", "Nrf2"),
        ("inflammatory signalling (NF-kB)", "hepatobiliary function"),
        ("jaundice", "inflammation", "diarrhoea"),
        "Catalpol, geniposide, aucubin, picroside: bitter, polar, heat-sensitive; some "
        "are hepatoprotective and some are nephrotoxic.",
        "canonical natural-products pharmacology",
    ),
    "phthalide": _p(
        "phthalide", 0.30, 0.40, 0.55,
        ("TRPA1", "GABA_A", "COX"),
        ("neurotransmission", "inflammatory signalling (NF-kB)"),
        ("pain", "menstrual_disorders", "headache"),
        "Ligustilide (當歸/川芎): volatile, lipophilic; a plausible vasoactive/"
        "antinociceptive constituent.",
        "canonical natural-products pharmacology (ligustilide)",
    ),
    "ketone": _p(
        "ketone", 0.20, 0.50, 0.40,
        ("olfactory/TRP",),
        ("neurotransmission",),
        ("pain", "inflammation"),
        "Muscone (musk): macrocyclic ketone, mostly a scent/fixative; pharmacological "
        "claims are weak.",
        "canonical natural-products chemistry",
    ),
    "bile_acid": _p(
        "bile_acid", 0.60, 0.00, 0.35,
        ("FXR", "TGR5"),
        ("bile acid signalling",),
        ("jaundice", "dyspepsia"),
        "Ursodeoxycholic acid is a real drug for cholestasis; bear-bile use is a "
        "conservation and safety problem, not a necessity.",
        "canonical pharmacology of bile acids",
    ),
    "heavy_metal": _p(
        "heavy_metal", 1.00, 0.00, 0.30,
        ("thiol enzymes", "DNA", "nephron transport"),
        ("nephrotoxicity", "neurotoxicity", "mutagenesis"),
        (),
        "Hg, As, Pb compounds: cumulative toxicants. Modelled as toxicology data with a "
        "high safety tier; never a therapy recommendation.",
        "canonical toxicology (IARC; WHO)",
    ),
    "mineral_salt": _p(
        "mineral_salt", 0.90, 0.00, 0.30,
        ("electrolyte balance", "gastric acid"),
        ("acid-base balance",),
        ("dyspepsia", "constipation"),
        "Ash-derived salts and sulfates: antacid, osmotic, electrolyte effects.",
        "canonical inorganic pharmacology",
    ),
}


# ======================================================================================
# Indications, organs and action classes
# ======================================================================================

ACTION_CLASSES: Mapping[str, tuple[str, ...]] = {
    "digestive": ("dyspepsia", "nausea", "vomiting", "diarrhoea", "constipation", "abdominal_pain", "intestinal_worms", "haemorrhoids"),
    "respiratory": ("cough", "dyspnoea", "sore_throat"),
    "neuro": ("headache", "epilepsy", "insanity", "insomnia", "anxiety", "depression", "memory_impairment", "pain"),
    "cardiovascular": ("palpitations", "hypertension", "oedema", "chest_pain"),
    "hepatobiliary": ("jaundice",),
    "dermatologic": ("skin_disease", "wound_healing", "abscess", "burns"),
    "musculoskeletal": ("arthritis", "low_back_pain", "muscle_pain", "bone_fracture"),
    "metabolic": ("diabetes", "fatigue", "anaemia"),
    "infectious": ("fever", "malaria"),
    "reproductive": ("menstrual_disorders", "lactation", "infertility"),
    "toxicological": ("snakebite", "poisoning"),
    "sensory": ("eye_disorders", "toothache"),
    "oncologic": ("tumour", "swelling"),
    "haematologic": ("bleeding",),
}

ACTION_CLASS_OF: Mapping[str, str] = {
    ind: action for action, inds in ACTION_CLASSES.items() for ind in inds
}


@dataclass(frozen=True)
class IndicationSpec:
    indication: str
    organ: str
    action_class: str
    symptom: str
    pathways: tuple[str, ...]
    zh: tuple[str, ...] = field(default_factory=tuple)
    sa: tuple[str, ...] = field(default_factory=tuple)
    ar: tuple[str, ...] = field(default_factory=tuple)
    en: tuple[str, ...] = field(default_factory=tuple)


INDICATIONS: Mapping[str, IndicationSpec] = {
    "dyspepsia": IndicationSpec("dyspepsia", "stomach", "digestive", "indigestion", ("gastrointestinal motility", "mucosal protection"), ("脾胃虛弱", "消化", "飲食積聚", "胃寒", "脘腹冷痛"), ("agni", "grahaṇī"), ("هضم", "ضعف الهضم"), ("indigestion",)),
    "nausea": IndicationSpec("nausea", "stomach", "digestive", "nausea", ("gastrointestinal motility",), ("噁心",), ("chardi",), (), ("nausea",)),
    "vomiting": IndicationSpec("vomiting", "stomach", "digestive", "vomiting", ("gastrointestinal motility",), ("嘔吐", "胃寒嘔吐"), ("chardi",), (), ("vomiting",)),
    "diarrhoea": IndicationSpec("diarrhoea", "intestine", "digestive", "diarrhoea", ("gastrointestinal motility", "mucosal protection"), ("泄瀉", "下痢", "泄痢", "澀腸止瀉"), ("atisāra",), (), ("diarrhoea", "dysentery")),
    "constipation": IndicationSpec("constipation", "intestine", "digestive", "constipation", ("gastrointestinal motility",), ("腸胃積滯", "便秘"), ("vibandha",), (), ("constipation",)),
    "abdominal_pain": IndicationSpec("abdominal_pain", "intestine", "digestive", "abdominal pain", ("gastrointestinal motility", "inflammatory signalling (NF-kB)"), ("腹痛", "腹脹", "胸腹脹痛"), ("gulma", "śūla"), (), ("abdominal pain",)),
    "intestinal_worms": IndicationSpec("intestinal_worms", "intestine", "digestive", "worm infestation", ("gastrointestinal motility",), ("蟲",), ("krimi",), (), ("worms",)),
    "haemorrhoids": IndicationSpec("haemorrhoids", "intestine", "digestive", "haemorrhoids", ("inflammatory signalling (NF-kB)",), ("痔",), ("arśas",), (), ("haemorrhoids",)),
    "cough": IndicationSpec("cough", "lungs", "respiratory", "cough", ("mucosal protection", "inflammatory signalling (NF-kB)"), ("咳嗽", "咳逆"), ("kāsa",), ("سعال",), ("cough",)),
    "dyspnoea": IndicationSpec("dyspnoea", "lungs", "respiratory", "breathlessness", ("mucosal protection",), ("咳逆上氣", "短氣"), ("śvāsa",), (), ("dyspnoea", "asthma")),
    "sore_throat": IndicationSpec("sore_throat", "throat", "respiratory", "sore throat", ("inflammatory signalling (NF-kB)",), ("咽喉腫痛", "喉痺"), ("kaṇṭha roga",), (), ("sore throat",)),
    "headache": IndicationSpec("headache", "head", "neuro", "head pain", ("neurotransmission", "vascular tone (ACE/NO)"), ("頭痛", "眩暈"), ("śiroroga",), ("صداع",), ("headache",)),
    "epilepsy": IndicationSpec("epilepsy", "brain", "neuro", "seizure", ("neurotransmission",), ("癲癇", "驚癇"), ("apasmāra",), (), ("epilepsy",)),
    "insanity": IndicationSpec("insanity", "brain", "neuro", "psychosis", ("neurotransmission",), ("癲狂", "中風"), ("unmāda",), (), ("psychosis", "insanity")),
    "insomnia": IndicationSpec("insomnia", "brain", "neuro", "sleeplessness", ("neurotransmission",), ("失眠", "不寐"), ("anidrā",), (), ("insomnia",)),
    "anxiety": IndicationSpec("anxiety", "brain", "neuro", "anxiety", ("neurotransmission",), ("驚悸",), (), (), ("anxiety",)),
    "depression": IndicationSpec("depression", "brain", "neuro", "low mood", ("neurotransmission",), ("鬱證",), ("unmāda",), (), ("depression",)),
    "memory_impairment": IndicationSpec("memory_impairment", "brain", "neuro", "memory loss", ("neurotransmission", "cerebral blood flow"), ("健忘",), ("smṛti",), (), ("memory",)),
    "pain": IndicationSpec("pain", "systemic", "neuro", "pain", ("inflammatory signalling (NF-kB)", "neurotransmission", "endocannabinoid"), ("疼痛", "止痛"), ("śūla", "vedanā"), ("ألم",), ("pain",)),
    "chest_pain": IndicationSpec("chest_pain", "heart", "cardiovascular", "chest pain", ("inflammatory signalling (NF-kB)", "vascular tone (ACE/NO)"), ("胸痹", "結胸"), ("hṛdraṅga",), (), ("chest pain",)),
    "palpitations": IndicationSpec("palpitations", "heart", "cardiovascular", "palpitation", ("cardiac contractility", "neurotransmission"), ("心悸", "驚悸"), ("hṛd",), (), ("palpitations",)),
    "hypertension": IndicationSpec("hypertension", "heart", "cardiovascular", "high blood pressure", ("vascular tone (ACE/NO)",), (), (), (), ("high blood pressure",)),
    "oedema": IndicationSpec("oedema", "systemic", "cardiovascular", "swelling", ("vascular tone (ACE/NO)",), ("水腫",), ("śotha",), (), ("oedema", "dropsy")),
    "diabetes": IndicationSpec("diabetes", "systemic", "metabolic", "thirst and wasting", ("glucose metabolism",), ("消渴",), ("prameha",), (), ("diabetes",)),
    "malaria": IndicationSpec("malaria", "blood", "infectious", "malarial fever", ("haem detoxification", "inflammatory signalling (NF-kB)"), ("瘧疾",), ("viṣama jvara",), (), ("malaria",)),
    "fever": IndicationSpec("fever", "systemic", "infectious", "fever", ("inflammatory signalling (NF-kB)",), ("發熱", "寒熱", "溫瘧"), ("jvara",), (), ("fever",)),
    "bleeding": IndicationSpec("bleeding", "systemic", "haematologic", "haemorrhage", ("coagulation",), ("下瘀血", "吐血", "活血"), ("raktapitta",), (), ("bleeding",)),
    "skin_disease": IndicationSpec("skin_disease", "skin", "dermatologic", "skin lesion", ("inflammatory signalling (NF-kB)", "oxidative stress (Nrf2/ARE)"), ("疥癬", "瘡", "癬"), ("kuṣṭha", "kandu"), (), ("skin disease",)),
    "wound_healing": IndicationSpec("wound_healing", "skin", "dermatologic", "wound", ("tissue repair", "inflammatory signalling (NF-kB)"), ("金瘡", "跌打損傷", "續筋骨"), ("vraṇa",), (), ("wound",)),
    "abscess": IndicationSpec("abscess", "skin", "dermatologic", "abscess", ("inflammatory signalling (NF-kB)",), ("癰腫", "惡瘡", "疽"), ("vidradhi",), (), ("abscess",)),
    "burns": IndicationSpec("burns", "skin", "dermatologic", "burn", ("tissue repair",), ("燙火傷",), ("dagdha",), (), ("burn",)),
    "arthritis": IndicationSpec("arthritis", "joints", "musculoskeletal", "joint pain", ("inflammatory signalling (NF-kB)",), ("風濕", "痺證"), ("amavata", "vāta"), ("وجع المفاصل",), ("arthritis",)),
    "low_back_pain": IndicationSpec("low_back_pain", "back", "musculoskeletal", "back pain", ("inflammatory signalling (NF-kB)",), ("腰痛",), ("kati śūla",), (), ("back pain",)),
    "muscle_pain": IndicationSpec("muscle_pain", "muscle", "musculoskeletal", "muscle pain", ("inflammatory signalling (NF-kB)",), ("身痛",), ("māṃsa śūla",), (), ("muscle pain",)),
    "bone_fracture": IndicationSpec("bone_fracture", "bone", "musculoskeletal", "broken bone", ("tissue repair",), ("續筋骨", "骨折"), ("asthi bhaṅga",), (), ("fracture",)),
    "snakebite": IndicationSpec("snakebite", "systemic", "toxicological", "snake envenomation", ("venom neutralisation",), ("蛇咬",), ("sarpa viṣa",), (), ("snakebite",)),
    "poisoning": IndicationSpec("poisoning", "systemic", "toxicological", "poisoning", ("chelation/adsorption", "hepatic detoxification"), ("解毒", "解百藥毒"), ("viṣa",), ("سم",), ("poisoning",)),
    "fatigue": IndicationSpec("fatigue", "systemic", "metabolic", "fatigue", ("metabolic energy", "immune modulation"), ("補氣", "補五臟", "虛勞"), ("balya", "rasāyana"), (), ("fatigue",)),
    "anaemia": IndicationSpec("anaemia", "blood", "metabolic", "anaemia", ("erythropoiesis",), ("補血",), ("pāṇḍu",), (), ("anaemia",)),
    "menstrual_disorders": IndicationSpec("menstrual_disorders", "reproductive", "reproductive", "menstrual irregularity", ("endocrine modulation", "vascular tone (ACE/NO)"), ("月經不調",), ("ārtava",), (), ("menstrual",)),
    "lactation": IndicationSpec("lactation", "reproductive", "reproductive", "lactation", ("endocrine modulation",), ("乳汁不通",), ("stanya",), (), ("lactation",)),
    "infertility": IndicationSpec("infertility", "reproductive", "reproductive", "infertility", ("endocrine modulation",), ("不孕",), ("vandhyatva",), (), ("infertility",)),
    "eye_disorders": IndicationSpec("eye_disorders", "eyes", "sensory", "eye disease", ("oxidative stress (Nrf2/ARE)",), ("目痛", "明目", "目赤"), ("netra",), (), ("eye",)),
    "toothache": IndicationSpec("toothache", "mouth", "sensory", "tooth pain", ("inflammatory signalling (NF-kB)",), ("牙痛",), ("danta",), (), ("toothache",)),
    "tumour": IndicationSpec("tumour", "systemic", "oncologic", "mass", ("apoptosis/proliferation",), ("癥瘕", "積聚", "癭瘤"), ("gulma", "arbuda"), (), ("tumour",)),
    "swelling": IndicationSpec("swelling", "systemic", "oncologic", "swelling", ("inflammatory signalling (NF-kB)",), ("腫",), ("śotha",), (), ("swelling",)),
}


def indication_spec(value: str) -> IndicationSpec | None:
    key = value.strip().lower()
    if key in INDICATIONS:
        return INDICATIONS[key]
    for spec in INDICATIONS.values():
        if key in spec.zh or key in spec.sa or key in spec.ar or key in spec.en or key == spec.symptom:
            return spec
    return None


def canonical_indication(value: str) -> str | None:
    spec = indication_spec(value)
    return spec.indication if spec else None


def organ_for_indication(indication: str) -> str | None:
    spec = indication_spec(indication)
    return spec.organ if spec else None


def action_class_for_indication(indication: str) -> str | None:
    spec = indication_spec(indication)
    return spec.action_class if spec else ACTION_CLASS_OF.get(indication)


def classes_for_indication(indication: str) -> frozenset[str]:
    """Compound classes whose textbook prior touches an indication's pathway/organ."""
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


def compound_class_profile(name: str) -> CompoundClassProfile | None:
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    return COMPOUND_CLASSES.get(key)


def canonical_process(value: str) -> str | None:
    """Resolve a process surface form (zh/pinyin/sa/en) to a canonical process key."""
    key = value.strip()
    if key in ALL_PROCESSES:
        return key
    if key in PROCESS_SYNONYMS:
        return PROCESS_SYNONYMS[key]
    low = key.lower()
    if low in PROCESS_SYNONYMS:
        return PROCESS_SYNONYMS[low]
    for prefix, proc in PROCESS_SYNONYMS.items():
        if low.startswith(prefix.lower()):
            return proc
    return None


# ======================================================================================
# Conservation status (endangered class) — curated, CITES-based
# ======================================================================================

CONSERVATION_STATUS: Mapping[str, dict[str, str]] = {
    "Rhinoceros": {"cites": "Appendix I", "status": "Critically Endangered", "note": "rhino horn is keratin; no pharmacological need"},
    "Panthera tigris": {"cites": "Appendix I", "status": "Endangered", "note": "tiger bone is collagen/keratin; no pharmacological need"},
    "Manis": {"cites": "Appendix I", "status": "Critically Endangered", "note": "pangolin scales are keratin; no pharmacological need"},
    "Moschus": {"cites": "Appendix I/II", "status": "Endangered", "note": "musk can be synthesised (muscone) or substituted"},
    "Ursus": {"cites": "Appendix I/II", "status": "Vulnerable", "note": "ursodeoxycholic acid is synthesised; bear farming is a welfare issue"},
    "Aquilaria agallocha": {"cites": "Appendix II", "status": "Vulnerable", "note": "agarwood over-harvested; plantation and substitute oils exist"},
    "Panax ginseng": {"cites": "Appendix II", "status": "Endangered in the wild", "note": "cultivated supply dominates"},
    "Dendrobium nobile": {"cites": "Appendix II", "status": "Vulnerable", "note": "wild orchid collection pressure"},
    "Gastrodia elata": {"cites": "Appendix II", "status": "Vulnerable", "note": "cultivated"},
    "Bletilla striata": {"cites": "Appendix II", "status": "Vulnerable", "note": "cultivated supply possible"},
    "Cibotium barometz": {"cites": "Appendix II", "status": "Vulnerable", "note": "wild fern harvest pressure"},
    "Paris polyphylla": {"cites": "Appendix II", "status": "Vulnerable", "note": "slow-growing; over-harvested"},
}

#: Text-attested substitution pairs (drug → substitute), used by the endangered class.
#: These are attested in the corpus and in open regulatory guidance; the hypothesis is
#: about chemical plausibility, not about endorsing a substitution for clinical use.
ATTESTED_SUBSTITUTES: Mapping[str, tuple[str, ...]] = {
    "Rhinoceros": ("Bubalus bubalis (water buffalo horn)", "Saiga tatarica (saiga horn)"),
    "Panthera tigris": ("Canis familiaris (dog bone)", "Sus scrofa (pig bone)"),
    "Moschus": ("synthetic muscone", "farmed Moschus (regulated)"),
    "Ursus": ("synthetic ursodeoxycholic acid", "Sus scrofa bile"),
    "Manis": ("Vaccaria segetalis (王不留行)", "Liquidambar formosana (路路通)"),
    "Aquilaria agallocha": ("Aquilaria plantation agarwood", "Santalum album (sandalwood)"),
    "Panax ginseng": ("Panax quinquefolius", "Codonopsis pilosula (黨參)"),
    "Dendrobium nobile": ("Dendrobium officinale (cultivated)",),
    "Gastrodia elata": ("cultivated Gastrodia",),
    "Bletilla striata": ("cultivated Bletilla",),
    "Cibotium barometz": ("cultivated Cibotium",),
    "Paris polyphylla": ("Paris fargesii (cultivated)", "Trillium species"),
}


# ======================================================================================
# Incompatibility mechanism bridging (配伍禁忌 class 1)
# ======================================================================================


@dataclass(frozen=True)
class InteractionMechanism:
    """A plausible modern mechanism linking two co-administered drugs.

    ``kind`` ∈ {"pk", "pd", "chemical", "toxic", "implausible"}:
      pk      — absorption/metabolism/transport changed (CYP, P-gp, chelation, adsorption)
      pd      — additive or opposing pharmacodynamics
      chemical— a reaction in the preparation (precipitation, gas, complex)
      toxic   — additive toxicity of shared toxic constituents
      implausible — no defensible modern mechanism found (an honest negative)
    ``prior`` ∈ [0,1] is our confidence that a *real* interaction exists; it is a
    prior, not a measurement.  ``evidence`` is a one-line rationale.
    """

    kind: str
    prior: float
    evidence: str


def _pair(a: str, b: str) -> frozenset[str]:
    return frozenset({a, b})


#: Pair-keyed mechanisms override the generic class-based inference below.
PAIR_MECHANISMS: Mapping[frozenset[str], InteractionMechanism] = {
    _pair("水銀", "砒霜"): InteractionMechanism(
        "toxic", 0.95,
        "Co-administration of mercury and arsenic: additive nephrotoxicity, "
        "neurotoxicity and carcinogenicity. Both are IARC Group 1/2A carcinogens.",
    ),
    _pair("硫黃", "朴硝"): InteractionMechanism(
        "chemical", 0.80,
        "Sulfur plus sodium sulfate in a heated preparation can generate reduced sulfur "
        "species (H2S/SO2); at minimum the pair is chemically incompatible and the "
        "laxative load is additive.",
    ),
    _pair("甘草", "甘遂"): InteractionMechanism(
        "toxic", 0.75,
        "Glycyrrhizin inhibits 11beta-HSD2, causing sodium retention and hypokalaemia; "
        "the diterpene/ingenol purgatives of 甘遂 cause fluid and potassium loss. The "
        "combination is a plausible route to severe hypokalaemia and arrhythmia.",
    ),
    _pair("甘草", "大戟"): InteractionMechanism(
        "toxic", 0.70,
        "As 甘草–甘遂: glycyrrhizin-induced hypokalaemia plus irritant diterpene "
        "purgation (大戟) compounds electrolyte loss.",
    ),
    _pair("甘草", "海藻"): InteractionMechanism(
        "chemical", 0.55,
        "Sargassum is iodine- and polysaccharide-rich; glycyrrhizin is surface-active. "
        "A physicochemical interaction in decoction is plausible, a pharmacological "
        "one is not established.",
    ),
    _pair("甘草", "芫花"): InteractionMechanism(
        "toxic", 0.65,
        "Glycyrrhizin hypokalaemia plus daphnetoxin/irritant diterpene purgation "
        "(芫花) — additive electrolyte and cardiac risk.",
    ),
    _pair("烏頭", "半夏"): InteractionMechanism(
        "pd", 0.45,
        "Aconitine (Na+ channel opener) plus Pinellia lectins/oxalates: additive "
        "arrhythmogenic and gastrointestinal effects are plausible; no clean CYP/P-gp "
        "mechanism is documented. The rule is historically strong but mechanistically "
        "unresolved — a genuine open question.",
    ),
    _pair("烏頭", "瓜蔞"): InteractionMechanism(
        "pd", 0.35,
        "Trichosanthes triterpenes plus aconitine: possible additive cardiac "
        "sensitisation; mechanism undocumented.",
    ),
    _pair("烏頭", "貝母"): InteractionMechanism(
        "pd", 0.35,
        "Fritillaria alkaloids (peimine) plus aconitine: both alkaloid fractions; "
        "possible additive cardiac effects, undocumented.",
    ),
    _pair("烏頭", "白蘞"): InteractionMechanism(
        "pd", 0.30,
        "Ampelopsis flavonoids plus aconitine: no established mechanism; the 十八反 "
        "rule may reflect empirical avoidance rather than a defined interaction.",
    ),
    _pair("烏頭", "白及"): InteractionMechanism(
        "chemical", 0.40,
        "Bletilla mucilage/polysaccharide could alter aconitine dissolution and "
        "absorption (a matrix effect), which would change the toxicokinetics of a "
        "narrow-margin drug.",
    ),
    _pair("藜蘆", "人參"): InteractionMechanism(
        "pd", 0.50,
        "Veratridine (persistent Na+ channel activation) plus ginsenosides; both alter "
        "cardiac/neuronal excitability. Veratrum is itself strongly emetic and toxic.",
    ),
    _pair("藜蘆", "沙參"): InteractionMechanism("pd", 0.35, "Additive cardiac/neuro activity is plausible; undocumented."),
    _pair("藜蘆", "丹參"): InteractionMechanism("pd", 0.35, "Tanshinones are vasoactive; veratridine is arrhythmogenic — a plausible cardiac interaction."),
    _pair("藜蘆", "玄參"): InteractionMechanism("pd", 0.30, "Undocumented; possible additive cardiac effect."),
    _pair("藜蘆", "苦參"): InteractionMechanism("pd", 0.35, "Matrine (Na+/K+ channel effects) plus veratridine: plausible additive cardiac toxicity."),
    _pair("藜蘆", "細辛"): InteractionMechanism("pd", 0.30, "Asarum constituents (including trace aristolochic acid) plus veratridine: undocumented."),
    _pair("藜蘆", "芍藥"): InteractionMechanism("pd", 0.30, "Paeoniflorin plus veratridine: undocumented."),
    _pair("狼毒", "密陀僧"): InteractionMechanism(
        "toxic", 0.80,
        "Lead (密陀僧/litharge) plus Euphorbia diterpenes: additive gastrointestinal "
        "mucosal injury and lead absorption.",
    ),
    _pair("巴豆", "牽牛"): InteractionMechanism(
        "toxic", 0.85,
        "Croton phorbol esters and Pharbitis resin glycosides are both violent purgatives: "
        "additive dehydration, electrolyte loss and mucosal damage.",
    ),
    _pair("丁香", "鬱金"): InteractionMechanism(
        "pk", 0.40,
        "Eugenol and curcuminoids both inhibit CYP3A4 in vitro; a metabolic interaction "
        "is plausible at high exposure but not established in vivo.",
    ),
    _pair("牙硝", "三稜"): InteractionMechanism("chemical", 0.35, "Osmotic sulfate load plus Sparganium saponins; a physicochemical/anticoagulant interaction is speculative."),
    _pair("川烏", "犀角"): InteractionMechanism(
        "implausible", 0.05,
        "Rhinoceros horn is keratin, essentially indigestible and pharmacologically "
        "inert. No PK or PD interaction with aconitine is defensible: the 十九畏 pair is "
        "not supported by modern chemistry, and the horn has no established efficacy.",
    ),
    _pair("人參", "五靈脂"): InteractionMechanism(
        "pk", 0.35,
        "Trogopterus dung resin/uric acid could alter gastric emptying and ginsenoside "
        "absorption; undocumented.",
    ),
    _pair("官桂", "赤石脂"): InteractionMechanism(
        "pk", 0.55,
        "Halloysite clay (赤石脂) adsorbs volatile cinnamaldehyde and other organics, "
        "plausibly reducing absorption — a classic adsorption interaction.",
    ),
    _pair("kṣīra", "matsya"): InteractionMechanism(
        "pd", 0.30,
        "Milk and fish: classical viruddha. Proposed modern mechanisms (biogenic amine "
        "formation, altered protein digestion) are speculative and poorly tested.",
    ),
    _pair("madhu", "ghṛta"): InteractionMechanism(
        "chemical", 0.25,
        "Honey and ghee in equal parts: possible 5-HMF/advanced-glycation chemistry on "
        "storage; the classical rule is not mechanistically established.",
    ),
    _pair("lavaṇa", "kṣīra"): InteractionMechanism(
        "chemical", 0.40,
        "Salt plus milk: electrolyte-driven protein destabilisation; a real "
        "physicochemical effect whose clinical relevance is unclear.",
    ),
    _pair("vatsanābha", "viṣa"): InteractionMechanism(
        "toxic", 0.90,
        "Aconitum ferox plus another poison: additive cardiotoxicity. This is a "
        "toxicological warning, not a therapeutic combination.",
    ),
}

#: Generic class-pair → mechanism inference used when no explicit pair is listed.
CLASS_PAIR_MECHANISMS: tuple[tuple[frozenset[str], InteractionMechanism], ...] = (
    (
        frozenset({"heavy_metal"}),
        InteractionMechanism("toxic", 0.85, "At least one partner is a cumulative heavy-metal toxicant; additive organ toxicity is expected."),
    ),
    (
        frozenset({"diterpenoid", "anthraquinone"}),
        InteractionMechanism("toxic", 0.70, "Two irritant/purgative classes: additive fluid and electrolyte loss."),
    ),
    (
        frozenset({"diterpenoid", "triterpenoid_saponin"}),
        InteractionMechanism("toxic", 0.65, "Surface-active saponin plus irritant diterpene: additive gastrointestinal injury and electrolyte loss."),
    ),
    (
        frozenset({"alkaloid", "triterpenoid_saponin"}),
        InteractionMechanism("pk", 0.40, "Saponins can alter membrane permeability and absorption of co-administered alkaloids."),
    ),
    (
        frozenset({"mineral_salt", "phenylpropanoid"}),
        InteractionMechanism("pk", 0.50, "Adsorbent mineral salts/clays can bind volatile aromatics and reduce absorption."),
    ),
    (
        frozenset({"protein"}),
        InteractionMechanism("implausible", 0.10, "Keratin/collagen-rich animal drugs are largely indigestible and have no plausible PK/PD interaction."),
    ),
)


def infer_pair_mechanism(
    drug_a: str, drug_b: str, classes_a: set[str], classes_b: set[str]
) -> InteractionMechanism:
    """Infer a mechanism for an incompatibility pair.

    Explicit curated pairs win; otherwise class-based inference applies.  Pairs with no
    defensible mechanism return ``kind="implausible"`` — an honest negative that the
    discovery ranking de-prioritises.
    """
    key = _pair(drug_a, drug_b)
    if key in PAIR_MECHANISMS:
        return PAIR_MECHANISMS[key]
    union = set(classes_a) | set(classes_b)
    best: InteractionMechanism | None = None
    for required, mech in CLASS_PAIR_MECHANISMS:
        if required <= union and (best is None or mech.prior > best.prior):
            best = mech
    return best or InteractionMechanism(
        "implausible", 0.10, "No defensible modern interaction mechanism found from the available constituent data."
    )


# ======================================================================================
# Helpers
# ======================================================================================

_INDICATION_LOOKUP: dict[str, str] = {}
for _spec in INDICATIONS.values():
    _INDICATION_LOOKUP[_spec.indication] = _spec.indication
    for _term in _spec.zh + _spec.sa + _spec.ar + _spec.en:
        _INDICATION_LOOKUP.setdefault(_term.lower(), _spec.indication)


def match_indication_term(term: str) -> str | None:
    """Fast lookup of an indication surface term (zh/sa/ar/en) → canonical key."""
    return _INDICATION_LOOKUP.get(term.strip().lower())


def all_indications() -> tuple[str, ...]:
    return tuple(INDICATIONS)


def tradition_metadata(tradition: str) -> dict[str, str]:
    try:
        return TRADITIONS[Tradition(tradition)]
    except ValueError:
        return TRADITIONS[Tradition.UNKNOWN]
