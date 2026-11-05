"""Asian theoretical systems as first-class feature vectors (brief §11.1–11.3).

Reads the structured property contracts:

* ``properties.csv`` — 四氣 (nature), 五味 (flavors), 歸經 (channels), 升降浮沉
  (direction), toxicity, 三品 grade;
* ``ayurveda_properties.csv`` — rasa, guṇa, vīrya, vipāka, prabhāva, doṣa effect;
* ``relations_seven.csv`` — the 七情 combination relations.

Nothing here asserts that the theory is true.  The point is to make it *computable*, so
:mod:`shennong.theory.predictivity` can test whether it predicts chemistry and target
biology above chance.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from shennong.config import CorpusPaths
from shennong.normalize import fold_iast, normalise

#: 四氣 → ordinal "warmth" used only as a feature for a correlation test.
NATURE_WARMTH: dict[str, int] = {"寒": -2, "凉": -1, "涼": -1, "平": 0, "温": 1, "溫": 1, "热": 2, "熱": 2}

#: 歸經 channel → organ (for the channel-tropism test).
CHANNEL_ORGAN: dict[str, str] = {
    "心": "heart", "肝": "liver", "脾": "spleen", "肺": "lungs", "肾": "kidney", "腎": "kidney",
    "胃": "stomach", "大肠": "intestine", "大腸": "intestine", "小肠": "intestine", "小腸": "intestine",
    "胆": "gallbladder", "膽": "gallbladder", "膀胱": "bladder", "三焦": "systemic", "心包": "heart",
    "脑": "brain", "腦": "brain", "胞宫": "reproductive", "胞宮": "reproductive",
}

#: 五味 → the compound-class family the flavour is classically expected to track.
FLAVOR_CLASS_FAMILIES: dict[str, frozenset[str]] = {
    "辛": frozenset({"monoterpenoid", "phenylpropanoid", "sesquiterpenoid", "phthalide", "ketone", "monoterpenoid_ester"}),
    "苦": frozenset({"alkaloid", "diester_alkaloid", "monoester_alkaloid", "flavonoid", "iridoid_glycoside", "glycoside", "coumarin", "anthraquinone", "aristolochic_acid"}),
    "甘": frozenset({"triterpenoid_saponin", "steroidal_saponin", "polysaccharide", "mucilage", "triterpenoid", "glycoside", "phenolic_glycoside"}),
    "酸": frozenset({"phenolic_acid", "tannin", "curcuminoid", "flavonoid"}),
    "涩": frozenset({"tannin", "flavonoid"}),
    "澀": frozenset({"tannin", "flavonoid"}),
    "咸": frozenset({"mineral_salt", "heavy_metal"}),
    "鹹": frozenset({"mineral_salt", "heavy_metal"}),
    "淡": frozenset({"polysaccharide", "mucilage"}),
}

#: Āyurvedic primary rasa → predicted action class(es) (from the classical doctrine).
RASA_ACTION_CLASSES: dict[str, tuple[str, ...]] = {
    "madhura": ("metabolic", "musculoskeletal", "reproductive"),
    "amla": ("digestive", "cardiovascular"),
    "lavana": ("digestive", "cardiovascular"),
    "katu": ("digestive", "respiratory", "neuro"),
    "tikta": ("dermatologic", "hepatobiliary", "infectious", "digestive"),
    "kashaya": ("digestive", "haematologic", "dermatologic"),
}

#: Doṣa effect → action classes it is classically expected to address.
DOSHA_ACTION_CLASSES: dict[str, tuple[str, ...]] = {
    "vata": ("neuro", "musculoskeletal"),
    "pitta": ("dermatologic", "hepatobiliary", "oncologic", "infectious"),
    "kapha": ("respiratory", "metabolic", "digestive"),
}


@dataclass(frozen=True)
class TCMProperties:
    drug_name: str
    binomial: str
    nature: str
    flavors: tuple[str, ...]
    channels: tuple[str, ...]
    direction: str
    toxicity: str
    grade: str
    source_id: str

    @property
    def warmth(self) -> float | None:
        """Ordinal warmth, handling the compound nature terms 微溫/微寒/大熱."""
        text = (self.nature or "").strip()
        multiplier = 1.0
        if text.startswith("微"):
            multiplier, text = 0.5, text[1:]
        elif text.startswith("大"):
            multiplier, text = 1.5, text[1:]
        base = NATURE_WARMTH.get(text)
        return None if base is None else base * multiplier

    def to_dict(self) -> dict:
        return {
            "drug_name": self.drug_name,
            "binomial": self.binomial,
            "nature": self.nature,
            "flavors": list(self.flavors),
            "channels": list(self.channels),
            "direction": self.direction,
            "toxicity": self.toxicity,
            "grade": self.grade,
        }


@dataclass(frozen=True)
class AyurvedaProperties:
    drug_name: str
    binomial: str
    rasa: tuple[str, ...]
    guna: tuple[str, ...]
    virya: str
    vipaka: str
    prabhava: str
    dosha_effect: dict[str, int]
    source_id: str

    @property
    def primary_rasa(self) -> str | None:
        return self.rasa[0] if self.rasa else None

    @property
    def is_hot_virya(self) -> bool | None:
        if self.virya in {"usna", "uṣṇa", "ushna", "hot", "garam"}:
            return True
        if self.virya in {"sita", "śīta", "shita", "cold"}:
            return False
        return None

    def to_dict(self) -> dict:
        return {
            "drug_name": self.drug_name,
            "binomial": self.binomial,
            "rasa": list(self.rasa),
            "guna": list(self.guna),
            "virya": self.virya,
            "vipaka": self.vipaka,
            "prabhava": self.prabhava,
            "dosha_effect": dict(self.dosha_effect),
        }


@dataclass(frozen=True)
class SevenRelation:
    drug_a: str
    drug_b: str
    relation: str
    source_id: str


@dataclass
class TheoryFeatures:
    tcm: dict[str, TCMProperties] = field(default_factory=dict)
    ayurveda: dict[str, AyurvedaProperties] = field(default_factory=dict)
    seven_relations: list[SevenRelation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return bool(self.tcm or self.ayurveda)


def _get(row: dict[str, str], *keys: str) -> str:
    """Tolerant column lookup (the contract uses some diacritics in header names)."""
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return ""


def _split_multi(value: str) -> tuple[str, ...]:
    if not value:
        return ()
    for sep in (";", "、", ",", "|"):
        value = value.replace(sep, " ")
    return tuple(part.strip() for part in value.split() if part.strip())


def _parse_dosha(value: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for token in _split_multi(value):
        tok = token.strip().lower()
        if tok.endswith("+") or tok.endswith("-"):
            out[tok[:-1]] = 1 if tok[-1] == "+" else -1
        elif tok in {"vata", "pitta", "kapha"}:
            out[tok] = 1
    return out


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [row for row in csv.DictReader(fh)]


def load_features(paths: CorpusPaths | None = None, lex=None) -> TheoryFeatures:
    """Load the Asian property vectors; missing files yield an empty (honest) feature set.

    Where ``plant_binomial`` is blank (a real-data join gap) the Chinese/IAST drug name is
    resolved through ``lexicon_drugs.json``.  Unresolvable rows are skipped and counted.
    """
    paths = (paths or CorpusPaths.resolve())
    features = TheoryFeatures()
    if lex is None:
        try:
            from shennong.extract.lexicons import build_lexicons

            lex = build_lexicons(paths)
        except Exception:
            lex = None
    name_to_binomial: dict[str, str] = {}
    if lex is not None:
        for entry in lex.drugs:
            name_to_binomial.setdefault(entry.surface, entry.canonical)

    def _resolve(row_binomial: str, drug_name: str) -> str:
        if row_binomial:
            return row_binomial
        return name_to_binomial.get(normalise(drug_name), "")
    unresolved = 0
    for row in _read_csv(paths.structured_dir / "properties.csv"):
        binomial = _resolve((row.get("plant_binomial") or "").strip(), (row.get("drug_name") or "").strip())
        if not binomial:
            unresolved += 1
            continue
        features.tcm[binomial] = TCMProperties(
            drug_name=(row.get("drug_name") or "").strip(),
            binomial=binomial,
            nature=(row.get("nature") or "").strip(),
            flavors=_split_multi(row.get("flavors") or ""),
            channels=_split_multi(row.get("channels") or ""),
            direction=(row.get("direction") or "").strip(),
            toxicity=(row.get("toxicity") or "").strip(),
            grade=(row.get("grade") or "").strip(),
            source_id=(row.get("source_id") or "").strip(),
        )
    for row in _read_csv(paths.structured_dir / "ayurveda_properties.csv"):
        binomial = _resolve((row.get("plant_binomial") or "").strip(), (row.get("drug_name") or "").strip())
        if not binomial:
            unresolved += 1
            continue
        features.ayurveda[binomial] = AyurvedaProperties(
            drug_name=(row.get("drug_name") or "").strip(),
            binomial=binomial,
            rasa=tuple(fold_iast(r).lower() for r in _split_multi(_get(row, "rasa"))),
            guna=_split_multi(fold_iast(_get(row, "guna", "guṇa"))),
            virya=fold_iast(_get(row, "virya", "vīrya")).strip().lower(),
            vipaka=fold_iast(_get(row, "vipaka", "vipāka")).strip().lower(),
            prabhava=_get(row, "prabhava", "prabhāva").strip(),
            dosha_effect=_parse_dosha(fold_iast(_get(row, "dosha_effect", "doṣa_effect"))),
            source_id=(row.get("source_id") or "").strip(),
        )
    for row in _read_csv(paths.structured_dir / "relations_seven.csv"):
        drug_a = (row.get("drug_a") or "").strip()
        drug_b = (row.get("drug_b") or "").strip()
        relation = (row.get("relation") or "").strip()
        if drug_a and drug_b and relation:
            features.seven_relations.append(
                SevenRelation(drug_a, drug_b, relation, (row.get("source_id") or "").strip())
            )
    if unresolved:
        features.warnings.append(
            f"{unresolved} property row(s) could not be resolved to a modern binomial "
            "(blank plant_binomial and drug name absent from lexicon_drugs.json)"
        )
    if not features.tcm:
        features.warnings.append("properties.csv missing or empty: TCM theory tests will report n=0")
    if not features.ayurveda:
        features.warnings.append("ayurveda_properties.csv missing or empty: Āyurveda tests will report n=0")
    return features
