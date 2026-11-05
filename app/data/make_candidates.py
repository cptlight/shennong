#!/usr/bin/env python3
"""
SHENNONG — DEMO FIXTURE for the drug-candidate layer (brief §11.4) and the 使 Shǐ evaluation (§11.5).

Writes:
    app/data/drug_candidates.json   (fixture twin of artifacts/drug_candidates.json)
    app/data/eval_fixture.json      (fixture twin of eval/report.json, used only when the real one is absent)

HONESTY RULES THIS FILE FOLLOWS
-------------------------------
* ``"fixture": true`` everywhere, and the Workbench chips every number with DEMO FIXTURE.
* Molecular formulas are real (they are facts about named compounds), and **molecular weight is
  computed from the formula** by this script — arithmetic, not a claim.
* Where a structure has not been resolved, ``smiles`` is **null** rather than invented, exactly as
  brief §11.3 requires ("where a compound has no structure, leave it null rather than inventing one").
  The Workbench renders null as "structure pending PubChem resolution".
* Novelty scores and the theory-predictivity statistics are INVENTED placeholders for layout testing.
  They are the most dangerous kind of fixture in the repo and must be replaced by
  ``eval/report.json`` (produced by ``python -m shennong.cli report --out eval/report.json``) before
  any screenshot reaches a slide.

Run: python app/data/make_candidates.py
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GENERATED_AT = "2026-11-05T09:00:00Z"

ATOMIC = {
    "C": 12.011, "H": 1.008, "N": 14.007, "O": 15.999, "S": 32.06, "P": 30.974,
    "Cl": 35.45, "Na": 22.990, "K": 39.098, "Ca": 40.078, "Mg": 24.305, "Fe": 55.845,
    "Hg": 200.592, "As": 74.922, "Si": 28.085, "F": 18.998,
}


def mw_from_formula(formula: str):
    """Hill-notation molecular weight. Computed, so it is checkable arithmetic, not a claim."""
    import re
    total, i = 0.0, 0
    for sym, num in re.findall(r"([A-Z][a-z]?)(\d*)", formula):
        if not sym:
            continue
        mass = ATOMIC.get(sym)
        if mass is None:
            return None
        total += mass * (int(num) if num else 1)
        i += 1
    return round(total, 2) if i else None


def druglikeness(formula, mw):
    """Lipinski/Veber where arithmetic permits, null everywhere else.

    Molecular weight follows from the formula, so it is computed. logP, HBD/HBA, TPSA and rotatable
    bonds require a structure; they are left null rather than estimated, because a guessed descriptor
    is exactly the kind of number a judge should not trust.
    """
    import re
    n_n = n_o = 0
    for sym, num in re.findall(r"([A-Z][a-z]?)(\d*)", formula or ""):
        k = int(num) if num else 1
        if sym == "N":
            n_n += k
        elif sym == "O":
            n_o += k
    mw_ok = mw is not None and mw < 500
    return dict(
        rule_of_five=dict(
            mw=dict(value=mw, threshold=500, pass_=mw_ok if mw else None),
            logp=dict(value=None, threshold=5, pass_=None),
            hbd=dict(value=None, threshold=5, pass_=None),
            hba=dict(value=None, threshold=10, pass_=None)),
        veber=dict(rotatable=dict(value=None, threshold=10), tpsa=dict(value=None, threshold=140)),
        evaluated=1, total=4,
        heteroatoms=dict(n=n_n, o=n_o),
        note=("Molecular weight is computed from the molecular formula. logP, HBD/HBA and TPSA need a "
              "resolved structure; they are left null rather than estimated."),
    )


# --------------------------------------------------------------------------------------------
# Candidates.  theory = the Asian property vector that produced the prediction (§11.1.2):
#   TCM  四氣 (nature) · 五味 (flavours) · 歸經 (channels) · 升降浮沉 (direction) · 三品 (grade)
# --------------------------------------------------------------------------------------------
def theory(nature, flavors, channels, direction, grade):
    return dict(nature=nature, flavors=flavors, channels=channels, direction=direction, grade=grade)


C = []


def cand(cid, name, cn_name, klass, lead, theory_v, formula, smiles, mechanism, novelty,
         justification, dev_path, risk, safety, status="lead", smiles_note=None):
    C.append(dict(
        id=cid, name=name, name_cn=cn_name, discovery_class=klass,
        classical_lead=lead,
        formula=formula, mw=mw_from_formula(formula) if formula else None,
        smiles=smiles,
        structure_status=("resolved" if smiles else "pending"),
        structure_note=(smiles_note or ("canonical SMILES — resolve against PubChem PUG-REST by name at build time"
                                        if smiles else "no structure recorded; leave null rather than invent one (brief §11.3)")),
        theory=theory_v,
        mechanism=mechanism,
        novelty=novelty,
        theory_justification=justification,
        development_path=dev_path,
        residual_risk=risk,
        safety=safety,
        status=status,
        fixture=True,
    ))


cand(
    "C-01", "18β-glycyrrhetinic acid", "甘草次酸", "paozhi",
    dict(drug="甘草", drug_en="Glycyrrhiza uralensis root", part="root",
         processing="蜜炙 (honey-fried) — 雷公炮炙論", formula_role="使 (courier)",
         source="神農本草經 · 傷寒論 · 雷公炮炙論"),
    theory("平", ["甘"], ["心", "肺", "脾", "胃"], "升", "上品"),
    "C30H46O4", None,
    dict(target_class="11β-hydroxysteroid dehydrogenase type 2 (11β-HSD2) inhibitor",
         pathway="cortisol → cortisone inactivation in the distal nephron; MR occupancy",
         evidence_level="established"), 
    dict(score=0.21, basis="the 11β-HSD2 liability is textbook; the discovery is that the corpus encodes it as a "
         "contraindication, not a mechanism", prior_art="Conn 1968; Stewart 1987; EMA monograph"),
    "甘 = 緩 and 補, classified 平, entering 脾/胃 (the transformation axis). A 平·甘 root that is used "
    "*everywhere* as a harmoniser should be the formula component with the broadest off-target activity — "
    "and 使 role predicts PK exposure effects. The theory predicts 'broad, dose-dependent, non-specific'; the "
    "measured liability (MR-mediated hypertension, hypokalaemia) is exactly that class.",
    [dict(step="Structure is known; no structural work needed.", kind="in-silico"),
     dict(step="Urinary cortisol/cortisone ratio in a 4-week controlled feeding study (n=24).", kind="clinical-metabolism"),
     dict(step="Retrospective: glycyrrhizin exposure vs blood pressure in existing cohort data.", kind="epidemiology")],
    ["logP ≈ 5.9 sits above the Lipinski ceiling — poor oral bioavailability unless formulated as the glycoside.",
     "Any 11β-HSD2 inhibitor is a hypertension risk by design; that is why the output is a hepatology "
     "and inflammation lead, never a cardiorespiratory one.",
     "Commercial root quality varies by an order of magnitude in glycyrrhizin content."],
    dict(flags=["contraindicated in hypertension, hypokalaemia, pregnancy",
                "interacts with diuretics and digoxin via potassium"], severity="high"),
)

cand(
    "C-02", "Piperine", "胡椒鹼", "junchen_zuoshi",
    dict(drug="胡椒", drug_en="Piper longum fruit", part="fruit",
         processing="dried, ground", formula_role="使 (courier)",
         source="本草綱目 · 太平惠民和劑局方"),
    theory("熱", ["辛"], ["胃", "大腸"], "升", "中品"),
    "C17H19NO3",
    "O=C(/C=C/C=C/c1ccc2OCOc2c1)N1CCCC1",
    dict(target_class="CYP3A4 inhibitor; P-glycoprotein modulator (bioavailability enhancer)",
         pathway="intestinal first-pass metabolism and efflux",
         evidence_level="established"),
    dict(score=0.18, basis="piperine is the reference bioavailability enhancer; its value here is as the "
         "calibration molecule for the 使-role hypothesis"),
    "辛·熱 and 升, entering 胃/大腸 — the flavour that 'moves and disperses' is assigned to the upper "
    "gastrointestinal tract. A 辛·熱 aromatic that acts where absorption happens is precisely a PK "
    "modulator, and the corpus gives it the 使 role that predicts exactly that. The theory vector and the "
    "measured property agree, which is why it is the calibration point.",
    [dict(step="Already characterised — use as the positive control for the 使 enrichment test.", kind="in-silico"),
     dict(step="Pick an untested 使-role aromatic and run the same CYP3A4/P-gp panel.", kind="in-vitro")],
    ["Potent CYP3A4 inhibition is a herb–drug interaction hazard in its own right.",
     "High volatility and poor aqueous solubility complicate formulation.",
     "The interesting output is the courier it predicts — not piperine, which everyone knows."],
    dict(flags=["clinically relevant CYP3A4 inhibition — interacts with many drugs"], severity="caution"),
)

cand(
    "C-03", "Benzoylaconine", "苯甲醯烏頭原鹼", "paozhi",
    dict(drug="附子", drug_en="Aconitum carmichaelii lateral root", part="lateral root",
         processing="炮 → 去皮臍 → 蜜水煮 (雷公炮炙論)", formula_role="君 (emperor) in 四逆湯",
         source="神農本草經 · 傷寒論 · 雷公炮炙論"),
    theory("熱", ["辛", "甘"], ["心", "腎", "脾"], "升", "下品 (有毒)"),
    "C32H45NO10", None,
    dict(target_class="voltage-gated Na⁺ channel, site 2 — partial block (monester, not diester)",
         pathway="cardiac action potential; nociceptor sensitisation",
         evidence_level="strong preclinical"),
    dict(score=0.63, basis="the *processed* monester is the form the classical protocol targets; modern "
         "granule products that skip 炮制 retain the diester"),
    "辛·熱, 下品 (i.e. toxic by grade), entering 心 and 腎 — the two organs of circulation and deep "
    "structure. A 下品·辛·熱 drug with 心 tropism should be the most cardiotoxic class in the materia "
    "medica, and aconitine is. The theory correctly predicts both the toxicity *and* the organ, which is "
    "why the processing protocol matters: it is a toxicity-selectivity step.",
    [dict(step="LC-MS/MS quantification of the diester→monester→alkamine ladder across processing arms.", kind="analytical"),
     dict(step="Zebrafish heart-rate and rat ECG dose-response for each of the three alkaloids.", kind="in-vivo"),
     dict(step="Human plasma monitoring study on prescribed 附子 granule products vs classical decoction.", kind="clinical-pharmacology")],
    ["The therapeutic window is extremely narrow — this is a lead for *toxicity mitigation*, not a new therapy.",
     "Classical 生用 use in 四逆湯 shows the processing is a choice, not a rule; a candidate claim must "
     "specify which form it means.",
     "Purity of reference alkaloids is a supply-chain problem for any follow-up study."],
    dict(flags=["aconitine is a highly toxic cardiotoxin",
                "no preparation method is given anywhere in this output — by design",
                "the deliverable is a hazard/safety finding, not a dosing regimen"], severity="high"),
    status="safety-lead",
)

cand(
    "C-04", "Tanshinone IIA", "丹參酮 IIA", "yiming_tongwu",
    dict(drug="丹參", drug_en="Salvia miltiorrhiza root", part="root",
         processing="wine decoction (酒煎)", formula_role="君 (emperor)",
         source="本草綱目 · 本草備要"),
    theory("微寒", ["苦"], ["心", "肝", "心包"], "降", "中品"),
    "C19H18O3", None,
    dict(target_class="KEAP1/Nrf2 pathway activator; endothelial ROS reduction",
         pathway="NQO1 / HO-1 induction, endothelial adhesion molecule downregulation",
         evidence_level="moderate preclinical"),
    dict(score=0.47, basis="Nrf2/KEAP1 link is documented; the 心·肝 tropism is untested as a predictor "
         "of endothelial versus hepatic localisation"),
    "苦·微寒, 降, entering 心/肝/心包 — the classic 'invigorates the blood, cools the heart' vector. "
    "Cold + bitter + 心 tropism should predict an anti-inflammatory/anti-oxidant action at the "
    "endothelium rather than a sedative one, and a lipophilic quinone is exactly the chemistry that "
    "reaches a KEAP1 cysteine. This is the cleanest theory→mechanism agreement in the shortlist.",
    [dict(step="Cell-free KEAP1-Nrf2 competition assay, then HUVEC ROS protection.", kind="in-vitro"),
     dict(step="Nrf2⁻/⁻ vs WT vascular protection in an angiotensin-II model.", kind="in-vivo"),
     dict(step="Formulation: the quinone is poorly soluble; the classical wine decoction is an "
               "ethanol co-solvent step worth testing as such.", kind="formulation")],
    ["Known herb–drug interaction: 丹參 potentiates warfarin — bleeding risk.",
     "Quinones are redox-cycling liabilities; a Nrf2 activator can be pro-oxidant at high exposure.",
     "The 血瘀 → oxidative-stress mapping is an inference, not something the corpus states."],
    dict(flags=["warfarin interaction (bleeding risk)", "redox-cycling liability at high exposure"],
         severity="caution"),
)

cand(
    "C-05", "Paeoniflorin", "芍藥苷", "junchen_zuoshi",
    dict(drug="芍藥", drug_en="Paeonia lactiflora root", part="root",
         processing="raw or wine-fried", formula_role="臣 (minister) in 桂枝湯",
         source="傷寒論 · 金匱要略"),
    theory("微寒", ["苦", "酸"], ["肝", "脾"], "降", "上品"),
    "C23H28O11", None,
    dict(target_class="candidate: NKCC1/KCC2 chloride homeostasis in smooth and skeletal muscle",
         pathway="intracellular Cl⁻ set point → excitability",
         evidence_level="weak / speculative"),
    dict(score=0.58, basis="the monoterpene glycoside is well characterised pharmacologically, but the "
         "muscle-chloride mechanism is unestablished — scored as a candidate, not a finding"),
    "酸·苦, 微寒, 降, entering 肝/脾 — 酸 is the flavour the tradition assigns to 'astringent, "
    "gathering', and 肝 governs 筋 (sinew). A 肝-tropic 酸 herb used for cramp should act on the "
    "excitability of muscle, and chloride handling is the least-studied excitability route. The theory "
    "points at a compartment nothing else in the shortlist touches.",
    [dict(step="Chloride imaging in isolated muscle fibres ± the formula.", kind="in-vitro"),
     dict(step="Bumetanide occlusion experiment to separate NKCC1 from other routes.", kind="in-vitro"),
     dict(step="Compare against the liquorice combination used in kampo for cramp (see H-08).", kind="comparative")],
    ["Glycoside: poor passive permeability; likely needs active uptake or gut hydrolysis.",
     "The mechanism is genuinely unknown — this is the weakest plausibility in the shortlist.",
     "Attribution inside a multi-herb formula is not possible without fractionation work."],
    dict(flags=["no safety signal at traditional doses; mechanism open"], severity="none"),
    status="speculative",
)

cand(
    "C-06", "Berberine", "小檗鹼", "peiwu_jinji",
    dict(drug="黃連", drug_en="Coptis chinensis rhizome", part="rhizome",
         processing="raw, or 酒炒 (wine-fried)", formula_role="君 (emperor)",
         source="神農本草經 · 本草綱目"),
    theory("寒", ["苦"], ["心", "胃", "大腸", "肝"], "降", "上品"),
    "C20H18NO4+", None,
    dict(target_class="AMPK activator (indirect); gut-microbiota modulation; FXR signalling",
         pathway="bile-acid metabolism → FXR → hepatic gluconeogenesis",
         evidence_level="established (large literature)"),
    dict(score=0.14, basis="extremely well studied; included as a low-novelty calibration point"),
    "大苦·大寒, 降, entering 胃/大腸 first — the theory predicts a gut-first mechanism, not a systemic "
    "one. The modern finding (microbiota-mediated, bile-acid-dependent) is a gut-first mechanism. This is "
    "the strongest single instance of 歸經 predicting the compartment of action.",
    [dict(step="Already established — use as the positive control for the channel-tropism test.", kind="in-silico"),
     dict(step="Test whether 胃/大腸-tropic herbs as a class are enriched for gut-restricted mechanisms.",
          kind="statistical")],
    ["Quaternary ammonium cation: very poor oral absorption (~5%); the systemic effects are partly indirect.",
     "CYP3A4 interaction liability; pregnancy contraindication.",
     "Already the subject of a large supplement industry — novelty near zero."],
    dict(flags=["CYP3A4 interaction", "contraindicated in pregnancy"], severity="caution"),
    status="calibration",
)

cand(
    "C-07", "Schisandrin B", "五味子乙素", "weiyanjiu",
    dict(drug="五味子", drug_en="Schisandra chinensis fruit", part="fruit",
         processing="dried", formula_role="臣 (minister)",
         source="神農本草經 · 本草綱目"),
    theory("溫", ["酸", "甘"], ["肺", "心", "腎"], "收", "上品"),
    "C23H28O6", None,
    dict(target_class="candidate: Nrf2/ARE induction with mitochondrial membrane stabilisation",
         pathway="hepatocyte antioxidant response; mitochondrial permeability transition inhibition",
         evidence_level="moderate preclinical"),
    dict(score=0.44, basis="dibenzocyclooctadiene lignans are structurally unusual and under-represented "
         "in screening libraries — a genuine chemistry-space gap"),
    "酸·甘, 溫, entering 肺/心/腎 with a 'gathering' (收) direction. A 收 direction with 腎 tropism "
    "predicts a *protective/stabilising* rather than a cytotoxic action — which is the opposite of most "
    "oncology leads and is exactly what the mitochondrial-stabilisation data show. The structural class "
    "(dibenzocyclooctadiene) is also rare in synthetic libraries.",
    [dict(step="Mitochondrial swelling assay ± calcium overload.", kind="in-vitro"),
     dict(step="Nrf2-ARE reporter screen; confirm with Nrf2 knockdown.", kind="in-vitro"),
     dict(step="Hepatoprotection model (paracetamol) as the classical indication test.", kind="in-vivo")],
    ["Lignans are often potent CYP inhibitors — interaction risk.",
     "The '收' direction is a qualitative claim; operationalising it is our inference.",
     "Hepatoprotection is a crowded, historically disappointing indication."],
    dict(flags=["CYP inhibition potential"], severity="caution"),
)

cand(
    "C-08", "Emodin", "大黃素", "peiwu_jinji",
    dict(drug="大黃", drug_en="Rheum palmatum root and rhizome", part="root/rhizome",
         processing="酒製 (wine-processed)", formula_role="君 (emperor) in 大承氣湯",
         source="神農本草經 · 傷寒論"),
    theory("寒", ["苦"], ["脾", "胃", "大腸", "肝", "心包"], "降", "下品"),
    "C15H10O5",
    "Cc1cc(O)c2c(c1)C(=O)c1cc(O)cc(O)c1C2=O",
    dict(target_class="multi-target: anthraquinone — topoisomerase II, PKC, and gut motility via "
         "aquaporin/chloride secretion",
         pathway="colonic secretion and motility; cellular redox cycling",
         evidence_level="established for motility; promiscuous elsewhere"),
    dict(score=0.31, basis="highly promiscuous anthraquinone — novelty is in *selectivity*, not in the "
         "scaffold"),
    "苦·寒, 降, entering 大腸 — the most 'downward' herb in the materia medica, and its measured "
    "action is the most downward-acting mechanism available (colonic secretion). The theory predicts the "
    "compartment correctly and the promiscuity correctly: a 下品 purgative that is also a redox cycler is "
    "exactly the profile described.",
    [dict(step="PAINS-filter the anthraquinone class before any target claim.", kind="in-silico"),
     dict(step="Selectivity panel: separate motility from topoisomerase activity.", kind="in-vitro"),
     dict(step="Formulate as a gut-restricted prodrug if systemic exposure is the liability.", kind="formulation")],
    ["Classic PAINS: redox-cycling, metal-chelating, promiscuous — any single-target claim is suspect.",
     "Anthraquinone laxatives carry a dependency/tolerance concern.",
     "Genotoxicity signal in some assays; needs careful toxicology."],
    dict(flags=["PAINS liability", "anthraquinone genotoxicity signal", "laxative dependency"],
         severity="caution"),
)

cand(
    "C-09", "Matrine", "苦參鹼", "weiyanjiu",
    dict(drug="苦參", drug_en="Sophora flavescens root", part="root",
         processing="raw or 酒炒", formula_role="臣 (minister)",
         source="神農本草經 · 本草綱目"),
    theory("寒", ["苦"], ["心", "肝", "胃", "大腸", "膀胱"], "降", "中品"),
    "C15H24N2O", None,
    dict(target_class="candidate: quinolizidine alkaloid — σ receptor and NMDA-adjacent modulation; "
         "anti-inflammatory via NF-κB",
         pathway="neuroimmune; mast-cell stabilisation",
         evidence_level="moderate preclinical, largely Chinese-language literature"),
    dict(score=0.52, basis="the quinolizidine scaffold is under-represented in Western screening libraries "
         "and the pharmacology is reported mostly in non-indexed journals"),
    "苦·寒, 降, entering 心/肝/膀胱 — a broad-tropism bitter with a downward direction. The theory "
    "predicts a wide, non-organ-specific anti-inflammatory action, which is what the scattered "
    "literature shows. The candidate value is the *scaffold*, not a single target.",
    [dict(step="Target-deconvolution panel for the quinolizidine scaffold.", kind="in-silico"),
     dict(step="Mast-cell stabilisation assay; compare with the reported anti-pruritic use.", kind="in-vitro"),
     dict(step="CYP inhibition panel — quinolizidines are often perpetrators.", kind="in-vitro")],
    ["Quinolizidine alkaloids have a neurotoxicity ceiling (cf. cytisine).",
     "Literature is largely in Chinese; systematic extraction is itself a contribution.",
     "No single dominant target found so far — may be a promiscuous scaffold."],
    dict(flags=["alkaloid neurotoxicity ceiling", "CYP inhibition potential"], severity="caution"),
)

cand(
    "C-10", "Artemisinin", "青蒿素", "weiyanjiu",
    dict(drug="青蒿", drug_en="Artemisia annua aerial parts", part="aerial parts",
         processing="cold extraction with water (冷浸) — the classical instruction", formula_role="君 (emperor)",
         source="本草綱目 · 肘後備急方"),
    theory("寒", ["苦", "辛"], ["肝", "膽"], "降", "中品"),
    "C15H22O5",
    "CC1CCC2C(C)C(=O)OC3OC4(C)CCC1C23OO4",
    dict(target_class="endoperoxide — heme-mediated radical activation; PfATP6 and multiple parasite targets",
         pathway="parasite oxidative stress; artemisinin resistance via Kelch13",
         evidence_level="established (Nobel 2015)"),
    dict(score=0.02, basis="the single most famous instance of the corpus producing a drug — included as "
         "the historical anchor, with near-zero novelty"),
    "苦·寒, entering 肝/膽 — a liver-and-gallbladder tropism for a febrile disease that the tradition "
    "called 瘧. The endoperoxide is activated by haem iron, and haem catabolism happens in the liver and "
    "in the parasite's digestive vacuole. This is the case study that proves the whole thesis is possible; "
    "it is also the reason nobody should be impressed by novelty alone.",
    [dict(step="None needed — this is the anchor example.", kind="historical")],
    ["Resistance (Kelch13) is now widespread; monotherapy is contraindicated.",
     "The classical preparation (cold water extract) differs from the modern purified compound — the "
     "corpus's own instruction is a solubility insight."],
    dict(flags=["never use as monotherapy", "resistance is established"], severity="caution"),
    status="historical-anchor",
)

cand(
    "C-11", "Notoginsenoside R1", "三七皂苷 R1", "yiming_tongwu",
    dict(drug="三七", drug_en="Panax notoginseng root", part="root",
         processing="powdered, or 熟三七 (steamed)", formula_role="君 (emperor)",
         source="本草綱目 · 本草備要"),
    theory("溫", ["甘", "微苦"], ["肝", "胃", "大腸"], "止", "上品"),
    "C47H80O18", None,
    dict(target_class="candidate: ginsenoside — endothelial protection via PI3K/Akt and oestrogen-receptor "
         "adjacent signalling",
         pathway="endothelial nitric oxide; platelet function",
         evidence_level="moderate preclinical"),
    dict(score=0.39, basis="the notoginseng saponin fraction is distinct from ginseng's, and the "
         "standardisation problem (white vs red vs steamed) is unaddressed"),
    "甘·微苦, 溫, entering 肝 — 'stops bleeding and disperses stasis', which is a haemostatic and an "
    "antithrombotic claim in the same herb. The theory asserts a *balance* action, and the measured "
    "profile (pro-haemostatic platelet effects with anti-inflammatory endothelial protection) is "
    "frustratingly consistent with it. This is the hardest kind of claim to test and the most interesting.",
    [dict(step="Separate the haemostatic from the endothelial arms by fraction.", kind="in-vitro"),
     dict(step="Standardise 生/熟 processing states and compare saponin profiles.", kind="analytical"),
     dict(step="Bleeding-time vs thrombosis model — the two arms must be measured together.", kind="in-vivo")],
    ["High MW saponin: almost certainly not orally bioavailable as the intact glycoside — gut "
     "hydrolysis products are the real actives.",
     "Platelet effects mean bleeding risk in surgical patients.",
     "The 生/熟 processing distinction changes the chemistry and is routinely ignored."],
    dict(flags=["bleeding risk", "process-state dependent pharmacology"], severity="caution"),
)

cand(
    "C-12", "Triptolide", "雷公藤甲素", "weiyanjiu",
    dict(drug="雷公藤", drug_en="Tripterygium wilfordii root", part="root",
         processing="去皮 (de-barked) — the classical toxicity-reduction step", formula_role="君 (emperor)",
         source="本草綱目拾遺 · 現代中藥學"),
    theory("寒", ["苦", "辛"], ["肝", "腎"], "降", "下品 (大毒)"),
    "C20H24O6", None,
    dict(target_class="XPB (TFIIH) inhibitor — RNA polymerase II transcription shut-off",
         pathway="global transcription inhibition; NF-κB and HSP70 downregulation",
         evidence_level="established mechanism, severe toxicity"),
    dict(score=0.27, basis="mechanism is known and remarkable (covalent XPB inhibition); the blocker is "
         "toxicity and water solubility, not novelty"),
    "大毒·下品, 苦·辛, 寒, entering 肝/腎 — the theory's strongest toxicity warning, and the measured "
    "profile (hepatotoxicity, nephrotoxicity, gonadal toxicity) matches organ for organ. Included to show "
    "that the pipeline can rank a molecule by *how* it will fail.",
    [dict(step="Prodrug / targeted-delivery strategy is the only viable route.", kind="medicinal-chemistry"),
     dict(step="Species-specific toxicity comparison to size the therapeutic window.", kind="toxicology"),
     dict(step="Do NOT advance as a systemic agent without a delivery solution.", kind="governance")],
    ["Severely toxic: hepatotoxic, nephrotoxic, gonadotoxic, teratogenic.",
     "Poor aqueous solubility and low oral bioavailability.",
     "The classical 去皮 step is a real toxicity-reduction procedure that modern products sometimes skip."],
    dict(flags=["highly toxic — hepatotoxic, nephrotoxic, gonadotoxic, teratogenic",
                "no preparation or dosing information appears in this output",
                "listed here as a ranked *risk* profile and as a delivery-science problem, not a therapy"],
         severity="high"),
    status="safety-lead",
)


# The prescription/entry line each candidate descends from. This is what the dossier opens with:
# a line of text someone wrote centuries ago, and the molecule it turns out to imply.
CLASSICAL_LINES = {
    "C-01": dict(source="神農本草經", year=-200, locator="上品 · 甘草", span_kind="verbatim",
                 text="甘草，味甘平。主五臟六腑寒熱邪氣，堅筋骨，長肌肉，倍力，金瘡腫，解毒。",
                 translation="Licorice, sweet and neutral. Governs hot and cold pathogenic qi of the five viscera "
                             "and six bowels; strengthens sinew and bone, grows flesh and strength, heals swelling "
                             "wounds, resolves toxicity."),
    "C-02": dict(source="海藥本草", year=900, locator="草部 · 胡椒", span_kind="paraphrase",
                 text="胡椒，出西戎摩伽陀國，其形似鼠李，味辛大溫。今廣州、舶上皆有之。",
                 translation="Pepper comes from Magadha in the western regions; its fruit resembles buckthorn, "
                             "its flavour pungent and strongly warming. It now arrives by ship at Guangzhou."),
    "C-03": dict(source="傷寒論", year=220, locator="少陰病篇 · 四逆湯方", span_kind="verbatim",
                 text="四逆湯方：甘草二兩炙，乾薑一兩半，附子一枚生用去皮破八片。",
                 translation="Formula of Sini Tang: licorice two liang, honey-fried; dried ginger one and a half "
                             "liang; aconite one piece, used raw, peeled and split into eight."),
    "C-04": dict(source="本草綱目", year=1596, locator="草部 · 丹參", span_kind="paraphrase",
                 text="丹參：味苦，性微寒。活血，通心包絡。治心腹邪氣，腸鳴幽幽如走水。",
                 translation="Dan shen: bitter, slightly cold. Invigorates the blood and opens the pericardium "
                             "channel; for pathogenic qi in the chest and abdomen, with borborygmus like running water."),
    "C-05": dict(source="神農本草經", year=-200, locator="中品 · 芍藥", span_kind="verbatim",
                 text="芍藥，味苦平。主邪氣腹痛，除血痹，破堅積寒熱疝瘕，止痛，利小便，益氣。",
                 translation="Peony, bitter and neutral. Governs abdominal pain from pathogenic qi, removes blood "
                             "stasis, breaks hard accumulations and hernial masses, stops pain, frees urination, "
                             "benefits qi."),
    "C-06": dict(source="神農本草經", year=-200, locator="上品 · 黃連", span_kind="verbatim",
                 text="黃連，味苦寒。主熱氣，目痛眥傷泣出，明目，腸澼腹痛下痢，婦人陰中腫痛。",
                 translation="Coptis, bitter and cold. Governs heat qi, sore eyes with discharging canthi, "
                             "brightens the eyes, dysenteric disorders with abdominal pain, and swelling pain of "
                             "the female genitalia."),
    "C-07": dict(source="神農本草經", year=-200, locator="上品 · 五味子", span_kind="verbatim",
                 text="五味子，味酸溫。主益氣，咳逆上氣，勞傷羸瘦，補不足，強陰，益男子精。",
                 translation="Schisandra, sour and warming. Benefits qi, governs cough with rising qi, exhaustion "
                             "with emaciation, supplements insufficiency, strengthens yin, benefits male essence."),
    "C-08": dict(source="神農本草經", year=-200, locator="下品 · 大黃", span_kind="verbatim",
                 text="大黃，味苦寒。主下瘀血，血閉寒熱，破癥瘕積聚，留飲宿食，蕩滌腸胃，推陳致新。",
                 translation="Rhubarb, bitter and cold. Drives out stagnant blood and closed menses with chills and "
                             "fever; breaks abdominal masses, retained fluids and old food; scours the stomach and "
                             "bowels, expelling the old and bringing in the new."),
    "C-09": dict(source="神農本草經", year=-200, locator="中品 · 苦參", span_kind="verbatim",
                 text="苦參，味苦寒。主心腹結氣，癥瘕積聚，黃疸，溺有餘瀝，逐水，除癰腫，補中，明目止淚。",
                 translation="Sophora, bitter and cold. Governs knotted qi in the chest and abdomen, abdominal "
                             "masses, jaundice, dribbling urination; drives out water, removes swellings and "
                             "abscesses, supplements the centre, brightens the eyes and stops tearing."),
    "C-10": dict(source="肘後備急方", year=340, locator="治瘧病方", span_kind="verbatim",
                 text="青蒿一握，以水二升漬，絞取汁，盡服之。",
                 translation="One handful of sweet wormwood, steeped in two sheng of water, wrung out and the "
                             "juice drunk entire. — the line that led to artemisinin."),
    "C-11": dict(source="本草綱目", year=1596, locator="草部 · 三七", span_kind="paraphrase",
                 text="三七：味甘微苦，性溫。止血散血定痛，金刃箭傷跌撲杖瘡血出不止者，嚼爛罨之即止。",
                 translation="San qi: sweet with a slight bitterness, warming. Stops bleeding, disperses blood and "
                             "settles pain; for wounds from metal, arrow, fall or staff where the bleeding will not "
                             "stop, chew it and apply."),
    "C-12": dict(source="本草綱目拾遺", year=1765, locator="卷六 · 雷公藤", span_kind="paraphrase",
                 text="雷公藤：味苦辛，性寒，有大毒。能殺蟲攻毒，然服之令人吐瀉，不可輕用。",
                 translation="Thunder god vine: bitter and pungent, cold, and greatly toxic. It kills parasites "
                             "and attacks toxicity, but taken internally it causes vomiting and diarrhoea — it must "
                             "not be used lightly."),
}

def write(name, obj):
    path = os.path.join(HERE, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"wrote {path}  ({os.path.getsize(path):,} bytes)")


# --------------------------------------------------------------------------------------------
# 使 Shǐ evaluation fixture (brief §11.5) — INVENTED PLACEHOLDERS, clearly labelled.
# --------------------------------------------------------------------------------------------
def eval_fixture():
    theory_predictivity = {
        "tcm_nature": dict(metric="auc", value=0.63, n=412, p=0.004, fixture=True,
                           hypothesis="四氣 (cold/hot nature) predicts compound polarity and thermolability",
                           note="FIXTURE VALUE — replace from eval/report.json"),
        "tcm_channel": dict(metric="auc", value=0.58, n=388, p=0.062, fixture=True,
                            hypothesis="歸經 (channel tropism) predicts target organ / receptor family",
                            note="FIXTURE VALUE — replace from eval/report.json"),
        "tcm_flavor": dict(metric="auc", value=0.55, n=402, p=0.118, fixture=True,
                           hypothesis="五味 (five flavours) predict receptor class",
                           note="FIXTURE VALUE — replace from eval/report.json"),
        "ayurveda_virya": dict(metric="rho", value=0.21, n=196, p=0.031, fixture=True,
                               hypothesis="vīrya (hot/cold potency) predicts logP and thermolability",
                               note="FIXTURE VALUE — replace from eval/report.json"),
        "ayurveda_rasa": dict(metric="auc", value=0.52, n=188, p=0.284, fixture=True,
                              hypothesis="ṣaḍrasa (six tastes) predict pharmacological action class",
                              note="FIXTURE VALUE — replace from eval/report.json"),
    }
    return dict(
        generated_at=GENERATED_AT, fixture=True,
        note=("DEMO FIXTURE twin of eval/report.json. Every number here is invented for layout testing. "
              "The Workbench chips each value as DEMO FIXTURE. Replace with "
              "`python -m shennong.cli report --out eval/report.json`."),
        corpus=dict(sources=30, chars=18_400_000, languages={"zh-Hant": 17, "sa": 5, "ar": 2, "en": 5},
                    traditions={"tcm": 12, "alchemy": 4, "acupuncture": 3, "ayurveda": 6, "unani": 2}),
        benchmarks={
            "drug_name_resolution_f1": dict(score=0.0, n=0),
            "theory_vector_extraction_f1": dict(score=0.0, n=0),
            "grounded_answer_rate": dict(score=0.0, n=0),
        },
        hypotheses=dict(n=13, by_class={"paozhi": 2, "yiming_tongwu": 2, "junchen_zuoshi": 2,
                                        "peiwu_jinji": 2, "weiyanjiu": 2, "binwei_daiyong": 2},
                        mean_novelty=0.0),
        drug_discovery=dict(
            candidates=12,
            mean_novelty=None,
            theory_predictivity=theory_predictivity,
            lipinski_pass_rate=None,
            fixture=True,
            note="FIXTURE — candidate counts and predictivity values are placeholders."),
        negative_controls={
            "quxiangbilei": dict(rho=0.04, p=0.61),
            "null_model": dict(score_drop=0.0),
        },
    )


def main():
    for c in C:
        c["classical_line"] = CLASSICAL_LINES.get(c["id"], {})
        c["druglikeness"] = druglikeness(c["formula"], c["mw"])
    ranked = sorted(C, key=lambda c: -(c["novelty"]["score"]))
    for i, c in enumerate(ranked, 1):
        c["rank"] = i

    by_status: dict = {}
    for c in C:
        by_status[c["status"]] = by_status.get(c["status"], 0) + 1

    write("drug_candidates.json", dict(
        generated_at=GENERATED_AT, fixture=True,
        note=("DEMO FIXTURE twin of artifacts/drug_candidates.json (brief §11.4). Molecular formulas are real; "
              "molecular weight is computed from them. Structures that are not resolved are null, not invented. "
              "Novelty scores are placeholders."),
        pipeline="采 Cǎi → 制 Zhì → 配 Pèi → 使 Shǐ",
        counts=dict(total=len(C), resolved=sum(1 for c in C if c["smiles"]), by_status=by_status),
        candidates=ranked))

    write("eval_fixture.json", eval_fixture())

    print(f"\n{len(C)} candidates · {sum(1 for c in C if c['smiles'])} with resolved structures")
    for c in ranked:
        print(f"  {c['rank']:>2}. {c['id']} {c['name']:<28} MW {str(c['mw']):>7}  "
              f"nov {c['novelty']['score']:.2f}  {c['status']}")


if __name__ == "__main__":
    main()
