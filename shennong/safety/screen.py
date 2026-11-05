"""Dual-use and medical-safety screening.

This module is load-bearing for SHENNONG's ethics and for the judging criterion on
scientific responsibility.  It screens **requests and outputs** for:

1. **Pathogen work** — culture, isolation, enhancement or weaponisation of human
   pathogens (e.g. *Bacillus anthracis*, *Yersinia pestis*, variola, filoviruses).
2. **Toxin synthesis or isolation** — operational routes to ricin, botulinum toxin,
   aflatoxin, tetrodotoxin, sarin/VX/mustard gas, or to concentrating aconitine etc.
3. **Dosing and self-treatment** — any request for a dose, mg/kg, "how much should I
   take", or a personal treatment plan.  SHENNONG emits research hypotheses and
   toxicology, never posology.
4. **Dangerous Asian mineral drugs** — 硃砂/朱砂 (HgS), 雄黃 (As4S4), 輕粉 (Hg2Cl2),
   鉛丹 (Pb3O4), 密陀僧 (PbO), 砒霜 (As2O3), 水銀 (Hg), bhasma.  These are permitted as
   *toxicology and quality-control* subjects only; requests to consume or prepare them
   for use are blocked.
5. **Weaponisation / deliberate harm.**

The policy deliberately does **not** block research questions about mechanism, toxicity,
history, detection or quality control — those are the scientific questions this project
exists to answer, and over-refusal would make the tool useless.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

#: Human pathogens whose culture/enhancement we never assist with.
PATHOGENS = (
    "bacillus anthracis", "anthrax", "yersinia pestis", "plague bacterium",
    "variola", "smallpox", "ebola", "marburg", "lassa", " nipah", "sars-cov-2 culture",
    "mers-cov culture", "francisella tularensis", "tularemia", "burkholderia pseudomallei",
    "melioidosis", "clostridium botulinum", "rickettsia rickettsii",
)

#: Toxins for which synthesis/isolation routes are blocked.
TOXINS = (
    "ricin", "botulinum toxin", "botulinum", "aflatoxin", "tetrodotoxin", "saxitoxin",
    "sarin", "vx nerve agent", "mustard gas", "tabun", "soman", "abrin",
    "aconitine", "oleandrin", "digitoxin", "arsenic trioxide", "sodium cyanide",
    "potassium cyanide", "hydrogen cyanide", "strychnine", "dioxin",
)

#: Heavy-metal / toxic mineral drugs of the Asian materia medica (research subjects only).
DANGEROUS_MINERAL_DRUGS = (
    "朱砂", "硃砂", "雄黃", "雄黄", "輕粉", "轻粉", "鉛丹", "铅丹", "密陀僧", "砒霜",
    "水銀", "水银", "bhasma", "cinnabar", "realgar", "calomel", "litharge", "lead oxide",
    "mercury sulfide", "arsenic sulfide", "mercury", "lead", "arsenic",
)

#: Dosing / self-treatment language.
_DOSE_PATTERNS = (
    r"\bhow (much|many)\b.*\b(take|should i take|dose|mg|gram|grams)\b",
    r"\b(dose|dosage|dosing)\b",
    r"\bmg\s*/\s*kg\b",
    r"\b\d+\s*(mg|g|ml|grams?)\b",
    r"\b(should i|can i|may i|is it safe to)\s+(take|use|drink|eat|apply)\b",
    r"\b(treat|cure|heal)\s+(my|myself|my own)\b",
    r"\bself[- ]treat\b",
    r"\bfor my (pain|anxiety|insomnia|diabetes|infection|cancer)\b",
    r"\bhow to take\b",
    r"\bhow much\b.*\b(ingest|take|use|drink|eat|apply)\b",
    r"\bis it safe to (give|administer|apply)\b",
    r"\b(give|administer)\b.*\b(child|kid|baby|patient|my)\b",
)

_SYNTH_PATTERNS = (
    r"\b(synth\w*|manufactur\w*|produce|production of|isolat\w*|purif\w*|extract\w*|"
    r"make|making|route to|prepare)\b",
)

_PATHOGEN_ACTION = (
    r"\b(cultur\w*|isolat\w*|enhanc\w*|weaponi\w*|aerosoli\w*|amplif\w*|propagat\w*)\b",
)

_WEAPON_PATTERNS = (
    r"\bweaponi\w*\b",
    r"\bbioterror\w*\b",
    r"\bdeliver\w* system\b",
    r"\bpoison\s+(someone|a person|him|her|people|my)\b",
    r"\bkill\s+(someone|a person|him|her|people)\b",
)

DISCLAIMER = (
    "SHENNONG is a research tool for computational ethnopharmacology. Outputs are "
    "hypotheses for laboratory testing, not medical advice. No dose, self-treatment "
    "plan, or human-use protocol is provided. Classic Asian mineral drugs (mercury, "
    "arsenic, lead) and bhasma are analysed as toxicology and quality-control subjects "
    "only, never recommended."
)


@dataclass
class ScreeningResult:
    allowed: bool
    reasons: list[dict[str, Any]] = field(default_factory=list)
    category: str = "ok"
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "category": self.category,
            "reasons": self.reasons,
            "disclaimer": self.disclaimer,
        }


def _match_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    low = text.lower()
    return [term for term in terms if term.lower() in low]


def screen(text: str) -> ScreeningResult:
    """Screen a request or output string.

    Returns ``allowed`` plus every policy reason triggered.  Research questions about
    mechanism/toxicity/detection are allowed; operational synthesis, pathogen culture,
    dosing and self-treatment are not.
    """
    if not text or not text.strip():
        return ScreeningResult(True, [], "ok")
    text = text.strip()
    low = text.lower()
    reasons: list[dict[str, Any]] = []

    # 1) pathogen + action
    pathogens = _match_terms(low, PATHOGENS)
    if pathogens:
        actions = [m.group(0) for pattern in _PATHOGEN_ACTION for m in re.finditer(pattern, low)]
        if actions:
            reasons.append({
                "category": "pathogen_work",
                "severity": "high",
                "matched": sorted(set(pathogens)),
                "detail": "Requests for pathogen culture/isolation/enhancement are blocked.",
            })
        else:
            reasons.append({
                "category": "pathogen_topic",
                "severity": "caution",
                "matched": sorted(set(pathogens)),
                "detail": "Topic concerns a human pathogen; permitted only as non-operational discussion.",
            })

    # 2) toxin synthesis / isolation
    toxins = _match_terms(low, TOXINS)
    if toxins:
        synth_verbs = [m.group(0) for pattern in _SYNTH_PATTERNS for m in re.finditer(pattern, low)]
        if synth_verbs:
            reasons.append({
                "category": "toxin_synthesis",
                "severity": "high",
                "matched": sorted(set(toxins)),
                "detail": "Operational synthesis/isolation routes for toxins are blocked.",
            })

    # 3) weaponisation
    for pattern in _WEAPON_PATTERNS:
        m = re.search(pattern, low)
        if m:
            reasons.append({
                "category": "weaponisation",
                "severity": "high",
                "matched": [m.group(0)],
                "detail": "Weaponisation requests are blocked.",
            })

    # 4) dangerous mineral drugs + consumption/preparation request
    dangerous = _match_terms(text, DANGEROUS_MINERAL_DRUGS)
    if dangerous:
        operational = re.search(
            r"\b(consume|ingest|take|drink|eat|prepare|make|boil|decoct|dose|dosage|how much|"
            r"concentrate|extract|isolate|distill|refine)\b"
            r"|服用|食用|吞服|怎麼吃|怎么吃|劑量|剂量",
            low,
        )
        research = re.search(
            r"\b(toxicolog\w*|safety|quality control|detect\w*|analyse|analyze|analysis|"
            r"interaction|pharmacokinetic\w*|assay|mechanism|history|historical)\b"
            r"|毒性|安全|檢測|检测|分析|機制|机制|歷史|历史",
            low,
        )
        if operational and not research:
            reasons.append({
                "category": "dangerous_mineral_drug_use",
                "severity": "high",
                "matched": sorted(set(dangerous)),
                "detail": (
                    "Mercury/arsenic/lead drugs and bhasma are toxicological subjects only; "
                    "consumption or preparation-for-use requests are blocked."
                ),
            })
        elif operational and research:
            reasons.append({
                "category": "dangerous_mineral_drug_caution",
                "severity": "caution",
                "matched": sorted(set(dangerous)),
                "detail": "Toxicological analysis permitted; no dose/use guidance will be given.",
            })

    # 5) dosing / self-treatment
    for pattern in _DOSE_PATTERNS:
        m = re.search(pattern, low)
        if m:
            reasons.append({
                "category": "dosing_or_self_treatment",
                "severity": "high",
                "matched": [m.group(0).strip()],
                "detail": "SHENNONG does not provide doses, self-treatment or human-use protocols.",
            })
            break

    high = [r for r in reasons if r["severity"] == "high"]
    category = "ok"
    if high:
        category = "blocked"
    elif reasons:
        category = "caution"
    return ScreeningResult(allowed=not high, reasons=reasons, category=category)


def enforce(text: str) -> None:
    """Raise ``PermissionError`` when a string is policy-blocked (for output gates)."""
    result = screen(text)
    if not result.allowed:
        raise PermissionError("; ".join(r["detail"] for r in result.reasons))
