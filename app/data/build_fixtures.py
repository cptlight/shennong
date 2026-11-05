#!/usr/bin/env python3
"""
ATHANOR Workbench — DEMO FIXTURE generator.

WHY THIS FILE EXISTS
--------------------
The Workbench must run *before* the real pipeline artefacts land, and the repo must stay
honest: nothing here is a measured result. Everything this script writes is stamped
``"fixture": true`` and the UI renders a permanent ``DEMO FIXTURE`` badge on any panel
fed by it.

Every fixture number below is invented *for layout and interaction testing only*.
When the real artefacts appear, ``app/serve.py`` prefers them automatically:

    eval/report.json                  -> Methodology eval table + negative control
    training/runs/*/metrics.json      -> loss curve
    corpus/registry/sources.yaml      -> Corpus provenance panel
    app/data/hypotheses.json          -> Hypothesis explorer (written by `athanor`)
    app/data/kg.json                  -> Knowledge graph
    app/data/passages.json            -> Ask panel retrieval index

Run:  python app/data/build_fixtures.py
Safe to delete once the real artefacts exist.  Output is deterministic (fixed seed).
"""

from __future__ import annotations

import json
import math
import os
import random
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
GENERATED_AT = "2026-11-05T09:00:00Z"

# --------------------------------------------------------------------------------------------
# Weighted geometric mean — the same ranking rule stated in docs/METHODOLOGY.md.
# composite = novelty^0.30 * plausibility^0.30 * testability^0.25 * evidence^0.15
# --------------------------------------------------------------------------------------------
W = {"novelty": 0.30, "plausibility": 0.30, "testability": 0.25, "evidence": 0.15}


def composite(s: dict) -> float:
    acc = 0.0
    for k, w in W.items():
        acc += w * math.log(max(s[k], 0.01))
    return round(math.exp(acc), 3)


# --------------------------------------------------------------------------------------------
# Sources (fixture). Deliberately no URLs / sha256 / Gutenberg IDs: a fabricated identifier
# is the one piece of fixture data most likely to leak into a document and embarrass us.
# The real ledger is corpus/registry/sources.yaml.
# --------------------------------------------------------------------------------------------
SOURCES = [
    dict(source_id="fixture:dioscorides", title="De Materia Medica", author="Pedanius Dioscorides",
         year=70, era="1st c. CE", tier=2, licence="Public Domain", chars=612_400, status="ok"),
    dict(source_id="fixture:galen", title="De Simplicium Medicamentorum Facultatibus", author="Galen of Pergamon",
         year=180, era="2nd c. CE", tier=2, licence="Public Domain", chars=488_100, status="ok"),
    dict(source_id="fixture:parkinson-1629", title="Paradisi in Sole Paradisus Terrestris", author="John Parkinson",
         year=1629, era="17th c.", tier=2, licence="Public Domain", chars=934_700, status="ok"),
    dict(source_id="fixture:gerard-1633", title="The Herball or Generall Historie of Plantes", author="John Gerard",
         year=1633, era="17th c.", tier=2, licence="Public Domain", chars=2_104_300, status="ok"),
    dict(source_id="fixture:culpeper-1653", title="The Complete Herbal", author="Nicholas Culpeper",
         year=1653, era="17th c.", tier=3, licence="Public Domain", chars=1_187_600, status="ok"),
    dict(source_id="fixture:paracelsus", title="On the Nature of Things (spagyric writings)", author="Paracelsus",
         year=1537, era="16th c.", tier=3, licence="Public Domain", chars=341_200, status="ok"),
    dict(source_id="fixture:ripley", title="The Compound of Alchymy (Ripley Scroll tradition)", author="George Ripley",
         year=1471, era="15th c.", tier=3, licence="Public Domain", chars=98_400, status="ok"),
    dict(source_id="fixture:rosarium", title="Rosarium Philosophorum", author="anon. (Pseudo-Arnaldus)",
         year=1550, era="16th c.", tier=3, licence="Public Domain", chars=54_900, status="ok"),
    dict(source_id="fixture:bencao-gangmu", title="Bencao Gangmu (Compendium of Materia Medica, trans.)",
         author="Li Shizhen", year=1596, era="16th c.", tier=2, licence="Public Domain", chars=1_642_000, status="ok"),
    dict(source_id="fixture:charaka", title="Charaka Samhita (English trans.)", author="Agnivesha / Charaka",
         year=100, era="1st–2nd c. CE", tier=2, licence="Public Domain", chars=1_310_500, status="ok"),
    dict(source_id="fixture:kings-1898", title="King's American Dispensatory", author="Harvey W. Felter & John U. Lloyd",
         year=1898, era="19th c.", tier=2, licence="Public Domain", chars=3_402_800, status="ok"),
    dict(source_id="fixture:grieve-1931", title="A Modern Herbal", author="Maud Grieve",
         year=1931, era="20th c.", tier=2, licence="Public Domain", chars=1_736_900, status="ok"),
    dict(source_id="fixture:ema-monographs", title="EMA herbal monographs (selected)", author="European Medicines Agency",
         year=2016, era="21st c.", tier=2, licence="CC-BY-SA-4.0", chars=402_300, status="ok"),
    dict(source_id="fixture:duke", title="Dr Duke's Phytochemical and Ethnobotanical Databases",
         author="James A. Duke (USDA ARS)", year=2003, era="21st c.", tier=5, licence="Public Domain",
         chars=8_910_000, status="ok"),
    dict(source_id="fixture:chembl", title="ChEMBL — compound bioactivity records (subset)",
         author="EMBL-EBI", year=2025, era="21st c.", tier=5, licence="CC-BY-SA-4.0", chars=2_207_000, status="ok"),
    dict(source_id="fixture:wfo", title="World Flora Online / WCVP taxonomy backbone",
         author="WFO Consortium", year=2024, era="21st c.", tier=5, licence="CC-BY-4.0", chars=744_500, status="ok"),
    dict(source_id="fixture:huangdi-neijing", title="Huangdi Neijing — Suwen (trans.)", author="anon. (Yellow Emperor corpus)",
         year=-200, era="2nd c. BCE", tier=4, licence="Public Domain", chars=613_000, status="ok"),
    dict(source_id="fixture:zhenjiu", title="Zhenjiu Jiayi Jing (Systematic Classic of Acupuncture, trans.)",
         author="Huangfu Mi", year=282, era="3rd c. CE", tier=4, licence="Public Domain", chars=289_400, status="ok"),
    dict(source_id="fixture:unverified-grimoire", title="Untraced grimoire scan (licence unclear)",
         author="unknown", year=1700, era="18th c.", tier=3, licence="UNVERIFIED", chars=0, status="excluded"),
]

# --------------------------------------------------------------------------------------------
# Passages — the Ask panel's retrieval index. span_kind is always "paraphrase" here: these are
# modern-English restatements of well-attested traditional claims, NOT verbatim quotations.
# Verbatim spans arrive with the real corpus (nigredo -> albedo output).
# --------------------------------------------------------------------------------------------
P = dict(span_kind="paraphrase", fixture=True)


def ps(pid, sid, text, **kw):
    src = next(s for s in SOURCES if s["source_id"] == sid)
    d = dict(id=pid, source_id=sid, title=src["title"], author=src["author"], year=src["year"],
             era=src["era"], tier=src["tier"], licence=src["licence"], text=text)
    d.update(kw)
    d.update(P)
    return d


PASSAGES = [
    ps("fx-cp-001", "fixture:culpeper-1653",
       "Lavender is of a sharp and keen scent, and is reported to comfort the brain and the nerves, "
       "and to be good against the falling sickness, the palsy, and the trembling of the joints. "
       "The flowers steeped in wine are given for the head and the spirits."),
    ps("fx-cp-002", "fixture:culpeper-1653",
       "Lungwort is so called because the leaves are spotted like the lungs of a man, and therefore "
       "it was held by the signature of the thing to be a sovereign remedy for all diseases of the "
       "lungs, for coughs, and for the shortness of breath."),
    ps("fx-cp-003", "fixture:culpeper-1653",
       "Wormwood is bitter and warming; it strengthens the stomach, kills worms, and is good for "
       "a weak digestion. The juice of the herb is used outwardly, and the decoction inwardly."),
    ps("fx-cp-004", "fixture:culpeper-1653",
       "Liquorice root is hot and moist in quality; it is good for the roughness of the throat, the "
       "hoarseness of the voice, and the sharpness of humours, and it is often boiled in waters for "
       "the breast."),
    ps("fx-gd-001", "fixture:gerard-1633",
       "The distilled water of Lavender drawn in a bath of warm water, that the fire touch it not, "
       "is of all the waters the most comfortable to the head and to the sinews; and being smelled "
       "unto it refresheth the spirits."),
    ps("fx-gd-002", "fixture:gerard-1633",
       "Rosemary is a remedy against the stuffings of the head, and the water thereof distilled is "
       "used to wash the temples; the herb is accounted to strengthen the memory."),
    ps("fx-pa-001", "fixture:paracelsus",
       "The spagyric artist separates the three principles from the plant: the sulphur, which is the "
       "oil and the scent; the mercury, which is the spirit and the water; and the salt, which remaineth "
       "in the ashes. Each is prepared apart, and then joined again, that the virtue may be more open."),
    ps("fx-ri-001", "fixture:ripley",
       "Calcine the body until it be white and friable, then dissolve it in a moist menstruum, and "
       "digest it in gentle heat for a season, closing the vessel that nothing evaporate."),
    ps("fx-ri-002", "fixture:ripley",
       "Putrefaction is the first gate: the matter must be dissolved into blackness and be suffered "
       "to rest in the dung of a horse, or in a bath of temperate heat, until the colour change."),
    ps("fx-ro-001", "fixture:rosarium",
       "In the bath of Mary the vessel is warmed with the heat of water only, so that the gentle heat "
       "may draw the spirit without burning it; this is the distillation that admitteth no violence."),
    ps("fx-ga-001", "fixture:galen",
       "The faculties of simples are taken from their qualities; the hot and dry herb attenuates, the "
       "cold and moist herb thickens, and the physician must temper the one with the other, "
       "considering the heat of the body and the season of the year."),
    ps("fx-di-001", "fixture:dioscorides",
       "Peony: the root dried and drunk helpeth the falling sickness, and the seed taken in wine "
       "appeaseth the pains of the belly. The root of the female peony is of the greater virtue."),
    ps("fx-bg-001", "fixture:bencao-gangmu",
       "Dang gui: the root nourishes the blood and moves it, quiets the spirit, and is used when the "
       "menses are irregular or when the blood is deficient and the face is pale. It is warmed with wine."),
    ps("fx-bg-002", "fixture:bencao-gangmu",
       "Dan shen: the root invigorates the blood, cools the heart, and quiets the spirit; it is given "
       "when the blood is stasis and the chest is oppressed. It is decocted in water or in wine."),
    ps("fx-ch-001", "fixture:charaka",
       "The physician should consider the country, the season, the digestive fire of the patient, the "
       "strength of the body and the nature of the illness, for the same drug acts differently in "
       "different constitutions."),
    ps("fx-ka-001", "fixture:kings-1898",
       "Liquorice is demulcent and expectorant, and is largely employed to mask the taste of nauseous "
       "medicines; in large doses, long continued, it has been known to produce puffiness of the face "
       "and swelling of the ankles, and to disorder the action of the heart."),
    ps("fx-ka-002", "fixture:kings-1898",
       "Peony is antispasmodic and tonic; it has been recommended in chorea, in spasms of the muscles, "
       "and in the convulsive affections of childhood."),
    ps("fx-gr-001", "fixture:grieve-1931",
       "Lavender. The volatile oil is obtained by distilling the fresh flowering tops with water. It is "
       "used in nervous affections, in giddiness and sick headache, and as a stimulant in faintness."),
    ps("fx-gr-002", "fixture:grieve-1931",
       "Horehound. The herb is esteemed for its bitter tonic action and for coughs; it gently promotes "
       "expectoration. Its bitterness is very great, and it is given as a syrup or an infusion."),
    ps("fx-pk-001", "fixture:parkinson-1629",
       "The leaves of Sage are hot and dry, and are held to quicken the memory and to restore the senses, "
       "and the decoction thereof gargled helpeth the mouth and the throat."),
    ps("fx-hn-001", "fixture:huangdi-neijing",
       "The channels of the body carry the qi and the blood; where the qi is blocked there is pain, and "
       "where the blood is stasis the pain is fixed and pricking. Needling is applied where the channel "
       "is obstructed."),
    ps("fx-zj-001", "fixture:zhenjiu",
       "The point Zusanli is on the leg below the knee; needling it regulates the stomach and the spleen "
       "and is used when the digestion is weak and the limbs are cold."),
    ps("fx-em-001", "fixture:ema-monographs",
       "Lavender flower: traditional herbal medicinal product for the relief of mild symptoms of mental "
       "stress and exhaustion, and for the relief of mild sleep disorders, on the basis of longstanding use."),
    ps("fx-em-002", "fixture:ema-monographs",
       "Liquorice root: contraindicated in patients with hypertension, hypokalaemia, or a history of "
       "fluid retention; use is limited to a maximum of four to six weeks because of the mineralocorticoid effect."),
    ps("fx-em-003", "fixture:ema-monographs",
       "Peony root: traditional use for the relief of mild spasms and cramping in the lower abdomen; "
       "combinations with liquorice root are traditional in Japanese kampo medicine for muscle cramp."),
    ps("fx-du-001", "fixture:duke",
       "Lavandula angustifolia: linalool, linalyl acetate, borneol, camphor, terpinen-4-ol. Reported "
       "activity records for the volatile oil include sedative, anxiolytic and antimicrobial."),
    ps("fx-du-002", "fixture:duke",
       "Marrubium vulgare: marrubiin, premarrubiin, marrubenol. Reported activity records include "
       "bitter stimulant, expectorant and antispasmodic."),
    ps("fx-chm-001", "fixture:chembl",
       "Bioactivity records: linalool and linalyl acetate screened against GABA receptor complexes; "
       "flumazenil-reversible modulation of the benzodiazepine site reported in the patch-clamp "
       "literature summary table."),
    ps("fx-wfo-001", "fixture:wfo",
       "Lavandula angustifolia Mill. — accepted name in the WCVP backbone; family Lamiaceae. Former "
       "usage 'Lavandula vera' is listed as a synonym."),
    ps("fx-wfo-002", "fixture:wfo",
       "Marrubium vulgare L. — accepted; family Lamiaceae; syn. Marrubium apulum. Peucedanum ostruthium "
       "is listed under Apiaceae."),
    ps("fx-hm-001", "fixture:huangdi-neijing",
       "The five viscera are each associated with a colour, a season, an emotion and a taste; the "
       "physician who reads the complexion and the pulse may know the state of the viscera without "
       "asking the patient."),
]

# --------------------------------------------------------------------------------------------
# Hypotheses.  Scores are fixture-only.  The ranking is computed, not asserted.
# --------------------------------------------------------------------------------------------
H = []


def hyp(hid, title, archetype, chain, scores, prov, falsification, uncertainty,
        safety=None, dossier=None, **extra):
    scores = dict(scores)
    scores["composite"] = composite(scores)
    h = dict(id=hid, title=title, archetype=archetype, chain=chain, scores=scores,
             provenance=prov, falsification_plan=falsification, uncertainty=uncertainty,
             safety=safety or {"flags": [], "severity": "none"},
             dossier=dossier or {})
    h.update(extra)
    H.append(h)


def pv(sid, span, locator=""):
    s = next(x for x in SOURCES if x["source_id"] == sid)
    return dict(source_id=sid, title=s["title"], author=s["author"], year=s["year"], era=s["era"],
                tier=s["tier"], licence=s["licence"], span=span, span_kind="paraphrase",
                locator=locator)


hyp(
    "H-06",
    "Liquorice decoction, taken for weeks, reproduces the mineralocorticoid excess the herbals describe",
    "repurposing",
    dict(plant="Glycyrrhiza glabra", preparation="Decoction of the root, taken daily for 4–6 weeks",
         chemotype="18β-glycyrrhetinic acid (glycyrrhizin aglycone)",
         target="11β-hydroxysteroid dehydrogenase type 2 (11β-HSD2) inhibition",
         indication="Iatrogenic apparent mineralocorticoid excess: hypertension, hypokalaemia, oedema"),
    dict(novelty=0.47, plausibility=0.83, testability=0.91, evidence=0.88),
    [pv("fixture:kings-1898", "In large doses, long continued, it has been known to produce puffiness "
        "of the face and swelling of the ankles, and to disorder the action of the heart.", "Liquorice"),
     pv("fixture:ema-monographs", "Contraindicated in patients with hypertension, hypokalaemia, or a "
        "history of fluid retention; use limited to four to six weeks.", "Liquorice root"),
     pv("fixture:culpeper-1653", "The root is boiled in waters for the breast and the roughness of the throat.", "")],
    "Take urinary free cortisol/cortisone ratio in a 24 h collection, with and without a 4-week "
    "liquorice-decoction exposure in a controlled feeding study n=24. 11β-HSD2 inhibition raises the "
    "cortisol:cortisone ratio and lowers serum potassium; if neither moves at intake-matched exposure, "
    "the mechanism is wrong and the effect is something else. Readouts are non-invasive and cost "
    "roughly the price of a metabolic-ward day-case.",
    "The historical record does not tell us how much glycyrrhizin the decoctions contained — root "
    "quality varies by an order of magnitude. We also cannot separate glycyrrhizin from the "
    "flavonoid fraction, which may contribute independently.",
    safety=dict(flags=["highest-severity safety signal in the ranked set",
                       "contraindicated in hypertension / hypokalaemia / pregnancy",
                       "interacts with diuretics and digoxin via potassium"],
                severity="high"),
    dossier=dict(
        rationale=("This is the ranked list doing its job in the direction nobody advertises. King's "
                   "American Dispensatory (1898) already describes the oedema; the EMA monograph turns "
                   "that observation into a contraindication. The corpus contains both ends of the "
                   "chain. Nothing in the output is new pharmacology — the new thing is that a system "
                   "reconstructed a hazard from a 17th-century comfort remedy and surfaced it beside "
                   "the therapeutic hypotheses, where a person could actually read it."),
        mechanistic_chain=[
            "Glycyrrhizin is hydrolysed in the gut to 18β-glycyrrhetinic acid.",
            "18β-glycyrrhetinic acid competitively inhibits 11β-HSD2 in the distal nephron.",
            "Cortisol is no longer inactivated to cortisone, so it occupies the mineralocorticoid receptor.",
            "Sodium retention, potassium loss, hypertension, suppression of renin and aldosterone.",
            "The same enzyme inhibition explains the hypokalaemic muscle weakness reported in the older dispensatories.",
        ],
        prior_art_refs=["Conn, Rovner & Cohen (1968) — liquorice-induced pseudoaldosteronism",
                        "Stewart et al. (1987) — 11β-HSD2 and the cortisol/cortisone shuttle",
                        "EMA herbal monograph, Glycyrrhiza glabra root"],
        cost_estimate="Low — no new compounds, no animal work; a clinical-metabolism collaborator and one IRB amendment.",
        next_steps=["Add a dose-duration field to the Preparation entity so the graph can reason about exposure.",
                    "Check whether the corpus records the same warning for other glycyrrhizin-containing formulas.",
                    "Ship as a safety annotation on every hypothesis that proposes a liquorice preparation."],
    ),
)

hyp(
    "H-03",
    "Wormwood's sesquiterpene lactones alkylate NF-κB p65 — a colitis rationale hiding in a bitter digestive",
    "repurposing",
    dict(plant="Artemisia absinthium", preparation="Ethanolic tincture of the flowering tops (1:5, 45% EtOH)",
         chemotype="absinthin, artabsin, artemolin (guaianolide sesquiterpene lactones; α-methylene-γ-butyrolactone)",
         target="NF-κB p65 (RelA) — irreversible Michael addition at Cys38",
         indication="Ulcerative colitis, mucosal inflammatory signalling"),
    dict(novelty=0.62, plausibility=0.64, testability=0.79, evidence=0.48),
    [pv("fixture:culpeper-1653", "Wormwood is bitter and warming; it strengthens the stomach, kills worms, "
        "and is good for a weak digestion.", ""),
     pv("fixture:gerard-1633", "The herb is used in bitter drinks and conserves for the stomach and the "
        "obstructions of the liver and the spleen.", ""),
     pv("fixture:grieve-1931", "Wormwood is one of the most bitter plants; the infusion is a stomachic and a "
        "tonic, and the powdered herb has been used as a vermifuge.", "")],
    "The claim is mechanism-specific. Treat DSS-colitis mice with an absinthin-enriched fraction and a "
    "lactone-depleted fraction at matched bitterness; if p65 Cys38 adducts are absent by click-probe and "
    "the lactone-depleted fraction is equally protective, the NF-κB mechanism is dead. Positive control: "
    "parthenolide. If IL-10-/- spontaneous colitis is unaffected, the effect is DSS-model-specific and "
    "does not generalise.",
    "Bitterness itself drives gut hormone release (GLP-1, CCK), which could produce an anti-inflammatory "
    "readout with no direct NF-κB involvement. The guaianolide content of commercial wormwood varies "
    "enormously and is rarely specified.",
    safety=dict(flags=["thujone content limits oral use and is itself a regulatory concern",
                       "absinthe-associated neurotoxicity is historically contested; do not conflate",
                       "no dosing conclusion is implied — this is a preclinical rationale"],
                severity="caution"),
    dossier=dict(
        rationale=("Bitter European digestives are a pharmacological family, not a list of folk claims. "
                   "The α-methylene-γ-butyrolactone pharmacophore is the best-characterised covalent "
                   "NF-κB warhead in natural products — parthenolide is the reference compound. Wormwood "
                   "carries the same warhead on guaianolide scaffolds. The tradition recorded the use "
                   "(weak digestion, 'obstructions'); the modern literature supplies the chemistry; "
                   "nobody appears to have put the two together for colitis specifically."),
        mechanistic_chain=[
            "Absinthin/artabsin bear an exocyclic methylene on the lactone ring.",
            "The β-carbon is electrophilic and is attacked by the Cys38 thiol of p65 — covalent, irreversible.",
            "Loss of p65 DNA binding reduces transcription of IL-6, TNF-α and ICAM-1.",
            "In intestinal epithelium this maps onto the documented mucosal inflammatory cascade.",
            "Bitterness additionally recruits TAS2R signalling in enteroendocrine cells — a second, independent axis.",
        ],
        prior_art_refs=["García-Piñeres et al. — sesquiterpene lactones as NF-κB inhibitors",
                        "Mathema et al. (2012) — parthenolide and NF-κB in inflammation",
                        "Bork et al. (1997) — guaianolides of Artemisia absinthium"],
        cost_estimate="Medium — one fractionation campaign plus a 4-week DSS study.",
        next_steps=["Resolve 'absinthium' vs 'absinthium album' historical naming to one taxon with confidence scores.",
                    "Ask whether the corpus's 'obstructions' language co-occurs with intestinal terms more than chance.",
                    "Specify the chemotype requirement explicitly in the falsification plan before any wet work."],
    ),
)

hyp(
    "H-02",
    "Danshen's tanshinones activate Nrf2 — a vascular oxidative-stress rationale for a heart herb",
    "chemotype_bridge",
    dict(plant="Salvia miltiorrhiza", preparation="Wine decoction of the root (traditional 'jiu jian')",
         chemotype="tanshinone IIA, cryptotanshinone, salvianolic acid B",
         target="KEAP1/Nrf2 (cytoprotective response element induction)",
         indication="Endothelial oxidative stress in early hypertension"),
    dict(novelty=0.55, plausibility=0.61, testability=0.72, evidence=0.58),
    [pv("fixture:bencao-gangmu", "Dan shen invigorates the blood, cools the heart and quiets the spirit; it is "
        "given when the blood is stasis and the chest is oppressed.", ""),
     pv("fixture:grieve-1931", "The red-rooted sage of the Chinese is used for the blood, and the decoction is "
        "taken warm with wine where the circulation is sluggish.", "")],
    "Human aortic endothelial cells under H2O2: if tanshinone IIA does not raise NQO1/HO-1 transcripts "
    "and nuclear Nrf2, and if ML385 (Nrf2 inhibitor) does not ablate the protective effect, the pathway "
    "claim fails. In vivo: Nrf2-/- mice should lose the vascular protection completely.",
    "'Blood stasis' is a process category, not a molecular one — the mapping to oxidative stress is our "
    "inference, and a plausible alternative reading is that the TCM category is closer to rheology.",
    safety=dict(flags=["Danshen is a recognised warfarin interaction — bleeding risk",
                       "no dosing or co-administration guidance is implied"], severity="caution"),
    dossier=dict(rationale=("Tanshinones are lipophilic quinones with a well-documented electrophilic "
                            "response element signature; salvianolic acid B is a parallel antioxidant "
                            "axis in the same root. The tradition's 'blood stasis' category and the modern "
                            "oxidative-stress literature describe the same organ-level problem at two "
                            "different resolutions."),
                mechanistic_chain=["Tanshinone IIA modifies KEAP1 cysteines.",
                                   "Nrf2 escapes ubiquitination and translocates.",
                                   "NQO1, HO-1, GCLM induced.",
                                   "Endothelial ROS burden falls; adhesion molecule expression drops."],
                prior_art_refs=["Xu & Liu — tanshinones and Nrf2 signalling",
                                "EMA/WHO monographs on Salvia miltiorrhiza"],
                cost_estimate="Medium — cell work is cheap; the in vivo arm needs a breeding colony.",
                next_steps=["Separate the quinone and the phenolic-acid arms in the fractionation plan.",
                            "Check the corpus for 'blood stasis' co-occurrence with pulse-quality terms."]),
)

hyp(
    "H-01",
    "The water-bath distillation the alchemists insisted on yields a linalool chemotype that modulates the benzodiazepine site",
    "process_translation",
    dict(plant="Lavandula angustifolia",
         preparation="Hydrodistillation in balneum Mariae, 3 h (the alchemical 'bath of Mary')",
         chemotype="linalool 28–44%, linalyl acetate 25–38%, terpinen-4-ol",
         target="GABA_A receptor complex, benzodiazepine site (positive allosteric modulation)",
         indication="Generalised anxiety — inhaled and oral routes are not interchangeable"),
    dict(novelty=0.41, plausibility=0.68, testability=0.86, evidence=0.62),
    [pv("fixture:rosarium", "In the bath of Mary the vessel is warmed with the heat of water only, so that the "
        "gentle heat may draw the spirit without burning it; this is the distillation that admitteth no violence.", ""),
     pv("fixture:gerard-1633", "The distilled water of Lavender drawn in a bath of warm water, that the fire touch "
        "it not, is of all the waters the most comfortable to the head and to the sinews.", ""),
     pv("fixture:culpeper-1653", "It comforteth the brain and the nerves, and is good against the trembling of "
        "the joints and the palsy.", ""),
     pv("fixture:ema-monographs", "Traditional herbal medicinal product for the relief of mild symptoms of mental "
        "stress and exhaustion, and mild sleep disorders.", "Lavender flower")],
    "Elevated plus maze in C57BL/6J, inhaled linalool at a fixed chamber concentration. If flumazenil "
    "(3 mg/kg i.p.) fails to reverse the anxiolytic effect, the benzodiazepine-site mechanism is "
    "falsified and a 5-HT1A or olfactory route remains. Second kill: β2/β3-subunit knockouts should "
    "abolish the effect if the GABA_A site is truly involved. Preclinical design only — not a dosing "
    "recommendation for any human.",
    "Route is the confounder that decides the whole hypothesis: inhaled linalool reaches plasma at a "
    "fraction of the oral dose, and the human trial literature mixes both. 'Anxiolytic' also spans "
    "acute sedation and chronic trait anxiety, which are different claims.",
    safety=dict(flags=["essential oils are not benign by default — oral linalool has a documented paediatric "
                       "toxicity literature", "no dosing guidance is offered or implied"], severity="caution"),
    dossier=dict(
        rationale=("The alchemists were emphatic about the water bath, and they were right for a reason "
                   "they did not articulate: hydrodistillation at ~100 °C in a sealed gentle-heat regime "
                   "preserves the acetate esters that a naked flame destroys. Gerard's 'that the fire "
                   "touch it not' is an extraction parameter wearing a liturgical costume. The chemistry "
                   "of the resulting oil points at a specific receptor site, and that site has a "
                   "selective antagonist, which makes the whole hypothesis cheap to kill."),
        mechanistic_chain=[
            "Balneum Mariae holds the still below the thermal degradation threshold of linalyl acetate.",
            "The condensate is a monoterpene-rich oil rather than a sesquiterpene-heavy one.",
            "Linalool reaches the GABA_A complex and potentiates GABA-evoked currents at the benzodiazepine site.",
            "Flumazenil reverses the potentiation — the discriminating experiment.",
            "Chronic exposure additionally down-regulates 5-HT1A in some models — a second axis.",
        ],
        prior_art_refs=["Russo (2011) — linalool and the GABA_A / 5-HT1A framework",
                        "Hritcu et al. — inhaled linalool and anxiety behaviour",
                        "EMA monograph, Lavandula angustifolia flower"],
        cost_estimate="Low — one still, one GC-MS run, one behavioural cohort.",
        next_steps=["Encode the distillation temperature as a Process entity attribute, not free text.",
                    "Check whether the corpus's water-bath insistence correlates with ester-rich plants.",
                    "Run the flumazenil arm before committing to any larger study."],
    ),
)

hyp(
    "H-10",
    "Horehound's bitterness may be a bronchodilator, not just an expectorant",
    "chemotype_bridge",
    dict(plant="Marrubium vulgare", preparation="Infusion of the dried herb",
         chemotype="marrubiin, premarrubiin (labdane diterpenoid bitter)",
         target="TAS2R bitter receptors on airway smooth muscle (bronchodilation)",
         indication="Cough and bronchospasm in obstructive airway disease"),
    dict(novelty=0.66, plausibility=0.52, testability=0.71, evidence=0.35),
    [pv("fixture:grieve-1931", "Horehound is esteemed for its bitter tonic action and for coughs; it gently "
        "promotes expectoration. Its bitterness is very great.", ""),
     pv("fixture:kings-1898", "Horehound is tonic, expectorant and gently laxative; it is much used in cough "
        "mixtures and in the form of a syrup.", "")],
    "Isolated human airway smooth-muscle strips, pre-contracted with carbachol: if marrubiin does not "
    "relax them and if the effect is not lost in TAS2R-specific knockdown, the bitter-bronchodilator "
    "hypothesis fails. Chloroquine (known TAS2R agonist) is the positive control.",
    "The expectorant tradition and the bronchodilator hypothesis can both be true; a cough outcome "
    "cannot distinguish them. Marrubiin's bitterness is on a different receptor class from the "
    "canonical horehound mucilage effect, so the fraction matters.",
    safety=dict(flags=["animal toxicity signal for marrubiin at high parenteral doses — route matters"],
                severity="none"),
    dossier=dict(rationale=("Bitter taste receptors are expressed in airway smooth muscle, where agonists "
                            "cause relaxation that is independent of β2-adrenoceptors. Horehound is one of "
                            "the bitterest herbs in the European materia medica and its indication is "
                            "literally the airway. The tradition had the right organ and the wrong "
                            "mechanism; the receptor was only characterised in the 2010s."),
                mechanistic_chain=["Marrubiin binds TAS2R isoforms on airway smooth muscle.",
                                   "Gβγ and PLCβ signalling raises local Ca²⁺ in a compartmentalised way.",
                                   "BK_Ca channel opening hyperpolarises the cell.",
                                   "Smooth muscle relaxes — bronchodilation without β2 involvement."],
                prior_art_refs=["Deshpande et al. (2010) — TAS2R agonists relax human airway smooth muscle",
                                "Ligresti et al. — marrubiin and TRP channel modulation"],
                cost_estimate="Low — isolated-tissue pharmacology is the cheapest honest test in the set.",
                next_steps=["Check whether the corpus pairs horehound with 'wheeze' rather than 'cough'.",
                            "Add TAS2R to the Target ontology with a receptor-family parent."]),
)

hyp(
    "H-08",
    "Peony–liquorice may act on muscle chloride handling — and we are the least sure of this one",
    "repurposing",
    dict(plant="Paeonia lactiflora / Glycyrrhiza uralensis",
         preparation="Combined decoction (kampo shakuyaku-kanzo-tō proportions)",
         chemotype="paeoniflorin + glycyrrhizin, co-extracted",
         target="NKCC1 / KCC2 chloride homeostasis in skeletal muscle (candidate)",
         indication="Muscle cramp and spasm"),
    dict(novelty=0.58, plausibility=0.49, testability=0.68, evidence=0.55),
    [pv("fixture:ema-monographs", "Peony root: traditional use for mild spasms and cramping in the lower abdomen; "
        "combinations with liquorice root are traditional in Japanese kampo medicine for muscle cramp.", ""),
     pv("fixture:kings-1898", "Peony is antispasmodic and tonic; it has been recommended in spasms of the muscles "
        "and in the convulsive affections of childhood.", ""),
     pv("fixture:dioscorides", "The root dried helpeth the falling sickness, and the seed taken in wine "
        "appeaseth the pains of the belly.", "")],
    "Intracellular chloride imaging in isolated muscle fibres with and without the formula: if the "
    "NKCC1/KCC2 ratio does not shift, or if bumetanide (NKCC1 inhibitor) occludes the whole effect "
    "rather than adding to it, the chloride hypothesis is unsupported. The honest alternative is that "
    "the effect is glycyrrhizin-driven mineralocorticoid action, which H-06 already covers.",
    "This is the weakest hypothesis in the ranked set and it is presented as such. The formula is a "
    "combination, so attribution to a single compound is not available. The mechanism is a candidate, "
    "not a finding — the composite score reflects that.",
    safety=dict(flags=["contains liquorice — inherits every H-06 contraindication",
                       "combination products make dose attribution impossible"],
                severity="caution"),
    dossier=dict(rationale=("Two independent traditions converge on spasm and cramp with the same pair of "
                            "roots, which is the kind of convergence the pipeline is built to notice. "
                            "The mechanism, however, is genuinely unknown; we surface the hypothesis with "
                            "a deliberately low plausibility score rather than dressing it up."),
                mechanistic_chain=["Unexplained at the molecular level.",
                                   "Candidate: altered NKCC1/KCC2 balance changes intracellular Cl⁻.",
                                   "Candidate: glycyrrhizin-mediated mineralocorticoid effect on the muscle membrane.",
                                   "Distinguishing experiment: chloride imaging plus bumetanide occlusion."],
                prior_art_refs=["Kampo clinical literature on shakuyaku-kanzo-tō and muscle cramp",
                                "EMA monograph, Paeonia lactiflora root"],
                cost_estimate="Medium — needs electrophysiology or chloride-sensitive dye work.",
                next_steps=["Mark this as 'mechanism open' in the UI rather than shipping a fake chain.",
                            "Search the corpus for the two plants named together — that is the real signal."]),
)

hyp(
    "H-09",
    "Feverfew's parthenolide is the reference NF-κB warhead — and that is exactly why its novelty score is low",
    "repurposing",
    dict(plant="Tanacetum parthenium", preparation="Freeze-dried leaf capsules (traditional prophylactic)",
         chemotype="parthenolide (germacranolide sesquiterpene lactone)",
         target="NF-κB p65 Cys38 alkylation; also IKKβ",
         indication="Migraine prophylaxis"),
    dict(novelty=0.18, plausibility=0.78, testability=0.74, evidence=0.83),
    [pv("fixture:gerard-1633", "Featherfew is used for the megrim and for the giddiness of the head, and the "
        "herb is worn about the person by some for that purpose.", ""),
     pv("fixture:grieve-1931", "Feverfew has been used for many years for the relief of migraine, and the "
        "leaves are eaten fresh in some country districts for that complaint.", "")],
    "Already substantially tested — the falsifying experiment is the literature itself. A novelty score "
    "of 0.18 is the system reporting that this idea is in the modern literature, which is the correct "
    "answer, not a failure.",
    "The clinical trial literature is mixed and the parthenolide content of commercial preparations is "
    "wildly variable. We cite this as a calibration point for the novelty axis.",
    safety=dict(flags=["Asteraceae allergy", "traditional contraindication in pregnancy"], severity="caution"),
    dossier=dict(rationale=("A deliberately included low-novelty control at the *scientific* level (as "
                            "distinct from the negative control at the statistical level). If our "
                            "novelty score could not recognise parthenolide/NF-κB as well-trodden, it "
                            "would not be measuring novelty at all."),
                mechanistic_chain=["Parthenolide alkylates p65 Cys38 and inhibits IKKβ.",
                                   "NF-κB-dependent cytokine transcription falls.",
                                   "Downstream effect on trigeminal CGRP release is the migraine link (inferred)."],
                prior_art_refs=["Mathema et al. (2012)", "Palevitch & Earon — feverfew migraine trials",
                                "EMA monograph, Tanacetum parthenium"],
                cost_estimate="None — the experiment has been run by others. This is a calibration record.",
                next_steps=["Keep as a regression test: if the novelty score drifts above 0.4 on a known "
                            "pairing, the novelty estimator is broken."]),
)

hyp(
    "H-07",
    "Berberine, AMPK and the gut — a known axis, scored as known",
    "chemotype_bridge",
    dict(plant="Berberis vulgaris", preparation="Decoction of the root bark",
         chemotype="berberine (protoberberine isoquinoline alkaloid)",
         target="AMPK activation (indirect, via gut microbiota and mitochondrial respiration)",
         indication="Metabolic syndrome: dyslipidaemia, insulin resistance"),
    dict(novelty=0.22, plausibility=0.74, testability=0.61, evidence=0.70),
    [pv("fixture:dioscorides", "The root of the barberry is sharp and cleansing; it is given for the jaundice and "
        "for the fluxes of the belly.", ""),
     pv("fixture:kings-1898", "Barberry is tonic and laxative; the bark is used in jaundice and in dyspepsia with "
        "a bitter taste.", "")],
    "Well studied; the discriminating experiment is germ-free vs conventionalised mice, which separates "
    "the microbiota-mediated effect from direct AMPK activation. Largely already done.",
    "The tradition's indication (jaundice, fluxes) is not the modern one (metabolic syndrome). The chain "
    "is real but the traditional-source link is weak, which is why evidence is graded 0.70 rather than "
    "higher.",
    safety=dict(flags=["berberine interacts with CYP3A4 substrates; pregnancy contraindication"],
                severity="caution"),
    dossier=dict(rationale=("Another calibration record: high plausibility, high evidence, low novelty. "
                            "The corpus link is thin because the tradition used barberry for the liver "
                            "and the bowel, not for glucose — the modern indication is an extension, "
                            "not a rediscovery."),
                mechanistic_chain=["Berberine alters bile-acid metabolism and gut microbiota composition.",
                                   "Secondary bile acids modulate FXR signalling.",
                                   "AMPK is activated indirectly; hepatic gluconeogenesis falls."],
                prior_art_refs=["Kong et al. (2004) — berberine and AMPK",
                                "Zhang et al. — gut microbiota and berberine"],
                cost_estimate="Already done in the literature.",
                next_steps=["Grade the traditional-evidence axis separately from the modern-mechanism axis."]),
)

hyp(
    "H-05",
    "Curcumin for osteoarthritis — ranked last on novelty because it is ranked by novelty",
    "repurposing",
    dict(plant="Curcuma longa", preparation="Decoction / powder", chemotype="curcumin, demethoxycurcumin",
         target="NF-κB; also numerous pan-assay interference liabilities",
         indication="Osteoarthritis pain and inflammation"),
    dict(novelty=0.03, plausibility=0.72, testability=0.44, evidence=0.81),
    [pv("fixture:charaka", "The physician should consider the country, the season, the digestive fire and the "
        "strength of the body, for the same drug acts differently in different constitutions.", ""),
     pv("fixture:grieve-1931", "Turmeric is used as a colouring and as a stimulant to the liver.", "")],
    "Nothing left to falsify that has not been attempted. Included as the floor of the novelty axis: "
    "2,000 years of use and a very large modern literature.",
    "Curcumin is the canonical cautionary tale of natural-product pharmacology — poor bioavailability "
    "and PAINS interference. Its low rank is a feature of the scorer.",
    safety=dict(flags=["curcumin is a known pan-assay interference compound; bioactivity readings need care"],
                severity="none"),
    dossier=dict(rationale=("The floor of the novelty axis and the reason the axis exists. A system that "
                            "ranked curcumin highly would be re-deriving other people's search results."),
                mechanistic_chain=["Curcumin is an electrophile that modifies many targets.",
                                   "NF-κB inhibition is reported but not mechanism-specific.",
                                   "Bioavailability without an adjuvant is very low."],
                prior_art_refs=["Nelson et al. (2017) — the curcumin clinical literature",
                                "Baell & Holloway (2010) — PAINS"],
                cost_estimate="None — do not run this experiment.",
                next_steps=["Keep as the novelty floor regression test."]),
)

hyp(
    "H-04",
    "Lungwort is spotted like a lung, therefore it treats the lungs — the negative control",
    "signature_test",
    dict(plant="Pulmonaria officinalis", preparation="Infusion of the leaves",
         chemotype="mucilage polysaccharides, allantoin, rosmarinic acid (no lung-specific warhead identified)",
         target="Pulmonary epithelium (by morphological analogy only)",
         indication="Cough, catarrh, 'diseases of the lungs'"),
    dict(novelty=0.12, plausibility=0.15, testability=0.55, evidence=0.20),
    [pv("fixture:culpeper-1653", "Lungwort is so called because the leaves are spotted like the lungs of a man, "
        "and therefore it was held by the signature of the thing to be a sovereign remedy for all diseases "
        "of the lungs.", ""),
     pv("fixture:gerard-1633", "It is called lungwort of the spots and marks of the leaf, resembling the lungs of "
        "a beast; and is thought good for the cough and the ptisick.", "")],
    "This is the doctrine of signatures stated as a testable claim. Prediction: across the corpus, "
    "morphological similarity to an organ predicts the recorded indication better than chance. The "
    "measured answer is close to zero (see the negative control in the eval table). A null here is the "
    "result we expect; a strong non-zero correlation would mean our extraction is picking up "
    "organ-word co-occurrence, not pharmacology.",
    "Demulcent mucilage genuinely soothes a sore throat — a real, non-signature effect that could "
    "mimic a positive correlation on cough outcomes. That confound is why the test is on "
    "organ-level indication, not symptom relief.",
    safety=dict(flags=[], severity="none"),
    dossier=dict(rationale=("Included so the negative control has a face. The doctrine of signatures is one "
                            "of the most productive and most wrong ideas in the history of pharmacology, "
                            "and it is exactly what a naive text-mining system will 'discover' if you do "
                            "not test for it."),
                mechanistic_chain=["Morphological resemblance asserted.", "Indication assigned by analogy.",
                                   "No molecular link proposed.", "This is the null."],
                prior_art_refs=["Foucault, The Order of Things — the signature episteme",
                                "Pearce (2008) — doctrine of signatures in practice"],
                cost_estimate="None — and it is the reason we trust the rest of the list.",
                next_steps=["Report the rho and p in the eval table on every run, not just once."]),
)

# --------------------------------------------------------------------------------------------
# Knowledge graph — derived from the chains plus explicit provenance links.
# --------------------------------------------------------------------------------------------
edges_i: list = []

KG_EXTRA = [
    # (source, target, rel)
    ("taxon:Lavandula angustifolia", "process:Balneum Mariae", "prepared_by"),
    ("process:Balneum Mariae", "compound:Linalool", "yields"),
    ("process:Balneum Mariae", "compound:Linalyl acetate", "yields"),
    ("taxon:Rosmarinus officinalis", "compound:Linalool", "yields"),
    ("taxon:Mentha x piperita", "compound:Linalool", "yields"),
    ("compound:Linalool", "target:GABA-A", "modulates"),
    ("target:GABA-A", "indication:Anxiety", "implicated_in"),
    ("taxon:Glycyrrhiza glabra", "compound:Glycyrrhizin", "yields"),
    ("compound:Glycyrrhizin", "compound:Glycyrrhetinic acid", "metabolised_to"),
    ("compound:Glycyrrhetinic acid", "target:11b-HSD2", "inhibits"),
    ("target:11b-HSD2", "target:Mineralocorticoid receptor", "regulates"),
    ("target:Mineralocorticoid receptor", "indication:Hypertension", "implicated_in"),
    ("taxon:Artemisia absinthium", "compound:Absinthin", "yields"),
    ("taxon:Artemisia absinthium", "compound:Artabsin", "yields"),
    ("compound:Absinthin", "target:NF-kB p65", "modulates"),
    ("compound:Artabsin", "target:NF-kB p65", "modulates"),
    ("compound:Parthenolide", "target:NF-kB p65", "inhibits"),
    ("taxon:Tanacetum parthenium", "compound:Parthenolide", "yields"),
    ("target:NF-kB p65", "indication:Colitis", "implicated_in"),
    ("target:NF-kB p65", "indication:Migraine", "implicated_in"),
    ("target:NF-kB p65", "indication:Osteoarthritis", "implicated_in"),
    ("taxon:Salvia miltiorrhiza", "compound:Tanshinone IIA", "yields"),
    ("taxon:Salvia miltiorrhiza", "compound:Salvianolic acid B", "yields"),
    ("compound:Tanshinone IIA", "target:Nrf2/KEAP1", "activates"),
    ("target:Nrf2/KEAP1", "indication:Endothelial dysfunction", "implicated_in"),
    ("taxon:Marrubium vulgare", "compound:Marrubiin", "yields"),
    ("compound:Marrubiin", "target:TAS2R", "agonises"),
    ("target:TAS2R", "indication:Bronchospasm", "implicated_in"),
    ("taxon:Paeonia lactiflora", "compound:Paeoniflorin", "yields"),
    ("compound:Paeoniflorin", "compound:Glycyrrhizin", "co-administered_with"),
    ("compound:Paeoniflorin", "target:NKCC1/KCC2", "candidate"),
    ("target:NKCC1/KCC2", "indication:Muscle cramp", "implicated_in"),
    ("taxon:Berberis vulgaris", "compound:Berberine", "yields"),
    ("compound:Berberine", "target:AMPK", "activates"),
    ("target:AMPK", "indication:Metabolic syndrome", "implicated_in"),
    ("taxon:Curcuma longa", "compound:Curcumin", "yields"),
    ("compound:Curcumin", "target:NF-kB p65", "modulates"),
    ("taxon:Pulmonaria officinalis", "target:Pulmonary epithelium", "signature_link"),
    ("target:Pulmonary epithelium", "indication:Cough", "implicated_in"),
    ("taxon:Pulmonaria officinalis", "compound:Rosmarinic acid", "yields"),
    ("source:fixture:culpeper-1653", "taxon:Lavandula angustifolia", "attests"),
    ("source:fixture:culpeper-1653", "taxon:Pulmonaria officinalis", "attests"),
    ("source:fixture:culpeper-1653", "taxon:Artemisia absinthium", "attests"),
    ("source:fixture:gerard-1633", "taxon:Lavandula angustifolia", "attests"),
    ("source:fixture:gerard-1633", "taxon:Pulmonaria officinalis", "attests"),
    ("source:fixture:rosarium", "process:Balneum Mariae", "describes"),
    ("source:fixture:ripley", "process:Dung digestion", "describes"),
    ("source:fixture:paracelsus", "process:Spagyric separation", "describes"),
    ("source:fixture:kings-1898", "taxon:Glycyrrhiza glabra", "attests"),
    ("source:fixture:ema-monographs", "taxon:Glycyrrhiza glabra", "attests"),
    ("source:fixture:bencao-gangmu", "taxon:Salvia miltiorrhiza", "attests"),
    ("source:fixture:grieve-1931", "taxon:Marrubium vulgare", "attests"),
    ("source:fixture:huangdi-neijing", "tradition:Channel theory", "grounds"),
]

TYPE_PREFIX = {"taxon", "process", "compound", "target", "indication", "source", "tradition"}
NODE_TYPE = {
    "taxon": "taxon", "process": "preparation", "compound": "compound", "target": "target",
    "indication": "indication", "source": "source", "tradition": "preparation",
}


def build_kg():
    nodes = {}

    def add(nid, label=None, ntype=None, weight=0.0):
        if nid in nodes:
            nodes[nid]["weight"] = max(nodes[nid]["weight"], weight)
            return
        prefix = nid.split(":", 1)[0]
        label = label or nid.split(":", 1)[1]
        nodes[nid] = dict(id=nid, label=label, type=ntype or NODE_TYPE.get(prefix, "compound"),
                          weight=weight)

    for s in SOURCES:
        if s["status"] != "ok":
            continue
        add(f"source:{s['source_id']}", s["author"].split(",")[0], "source", 0.3)

    for h in H:
        c = h["chain"]
        add(f"taxon:{c['plant']}", c["plant"], "taxon", 0.9)
        prep_label = c["preparation"].split("(")[0].strip()
        add(f"process:{prep_label}", prep_label, "preparation", 0.7)
        add(f"target:{c['target'].split(' (')[0]}", c["target"].split(" (")[0], "target", 0.8)
        add(f"indication:{c['indication'].split(' —')[0]}", c["indication"].split(" —")[0], "indication", 0.7)
        edges_i.append((f"taxon:{c['plant']}", f"process:{prep_label}", "prepared_by"))
        edges_i.append((f"process:{prep_label}", f"target:{c['target'].split(' (')[0]}", "points_to"))
        edges_i.append((f"target:{c['target'].split(' (')[0]}", f"indication:{c['indication'].split(' —')[0]}", "implicated_in"))
        for p in h["provenance"]:
            sid = f"source:{p['source_id']}"
            if sid in nodes:
                edges_i.append((sid, f"taxon:{c['plant']}", "attests"))

    for a, b, rel in KG_EXTRA:
        add(a)
        add(b)
        edges_i.append((a, b, rel))

    edges, seen = [], set()
    for a, b, rel in edges_i:
        if a not in nodes or b not in nodes:
            continue
        k = (a, b, rel)
        if k in seen:
            continue
        seen.add(k)
        edges.append(dict(source=a, target=b, rel=rel, weight=1.0))
    return nodes, edges


# --- deterministic Fruchterman–Reingold, so the UI never computes layout at runtime -------
def layout(nodes, edges, w=1200.0, hgt=820.0, iters=520, seed=7):
    rnd = random.Random(seed)
    ids = list(nodes)
    n = len(ids)
    pos = {}
    for i, nid in enumerate(ids):
        t = 2 * math.pi * i / n
        pos[nid] = [w / 2 + (w / 3) * math.cos(t) * (0.7 + 0.6 * rnd.random()),
                    hgt / 2 + (hgt / 3) * math.sin(t) * (0.7 + 0.6 * rnd.random())]
    adj = []
    for e in edges:
        a, b = (e["source"], e["target"]) if isinstance(e, dict) else (e[0], e[1])
        if a in pos and b in pos:
            adj.append((a, b))
    k = math.sqrt(w * hgt / max(n, 1))
    t0 = k * 1.8
    for it in range(iters):
        disp = {i: [0.0, 0.0] for i in ids}
        for i in range(n):
            for j in range(i + 1, n):
                a, b = ids[i], ids[j]
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                d2 = dx * dx + dy * dy
                if d2 < 1e-6:
                    dx, dy, d2 = rnd.random() - 0.5, rnd.random() - 0.5, 1e-6
                d = math.sqrt(d2)
                f = k * k / d
                ux, uy = dx / d, dy / d
                disp[a][0] += ux * f
                disp[a][1] += uy * f
                disp[b][0] -= ux * f
                disp[b][1] -= uy * f
        for a, b in adj:
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            d = max(math.sqrt(dx * dx + dy * dy), 1e-6)
            f = d * d / k
            ux, uy = dx / d, dy / d
            disp[a][0] -= ux * f
            disp[a][1] -= uy * f
            disp[b][0] += ux * f
            disp[b][1] += uy * f
        temp = t0 * (1 - it / iters) ** 1.6
        for nid in ids:
            dx, dy = disp[nid]
            d = max(math.sqrt(dx * dx + dy * dy), 1e-6)
            step = min(d, temp)
            pos[nid][0] += dx / d * step
            pos[nid][1] += dy / d * step
            # gentle centring pressure keeps the disc readable
            pos[nid][0] += (w / 2 - pos[nid][0]) * 0.004
            pos[nid][1] += (hgt / 2 - pos[nid][1]) * 0.004
    out = {}
    for nid in ids:
        out[nid] = [round(min(max(pos[nid][0], 40), w - 40), 1),
                    round(min(max(pos[nid][1], 40), hgt - 40), 1)]
    return out


def write(name, obj):
    path = os.path.join(HERE, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")
    print(f"wrote {path}  ({os.path.getsize(path):,} bytes)")


def main():
    ranked = sorted(H, key=lambda h: (-h["scores"]["composite"], -h["scores"]["novelty"]))
    for i, h in enumerate(ranked, 1):
        h["rank"] = i

    write("hypotheses.json", dict(
        generated_at=GENERATED_AT, fixture=True,
        note="DEMO FIXTURE — invented scores, paraphrased provenance spans, for UI development only. "
             "Replaced by athanor's real output.",
        corpus=dict(sources=sum(1 for s in SOURCES if s["status"] == "ok"),
                    chars=sum(s["chars"] for s in SOURCES), tokens=0),
        hypotheses=ranked))

    write("passages.json", dict(
        generated_at=GENERATED_AT, fixture=True,
        note="DEMO FIXTURE — modern-English paraphrases of attested traditional claims, not verbatim spans.",
        passages=PASSAGES))

    nodes, edges = build_kg()
    write("kg.json", dict(
        generated_at=GENERATED_AT, fixture=True, nodes=list(nodes.values()), edges=edges,
        layout=layout(nodes, edges)))

    write("corpus.json", dict(
        generated_at=GENERATED_AT, fixture=True, sources=SOURCES,
        built=dict(
            fetched=len(SOURCES), kept=sum(1 for s in SOURCES if s["status"] == "ok"),
            excluded=sum(1 for s in SOURCES if s["status"] != "ok"),
            deduped=0, chars=sum(s["chars"] for s in SOURCES)),
        stages=[
            dict(stage="aquire", label="Licence-audited fetch", detail="one entry per source in corpus/registry/sources.yaml"),
            dict(stage="clean", label="OCR clean · NFC · ≥200 chars", detail="drops headers, page furniture, ligature noise"),
            dict(stage="dedupe", label="13-gram hash across sources", detail="removes Gutenberg boilerplate and parallel editions"),
            dict(stage="split", label="deterministic 98/2 held-out", detail="hash-based, reproducible from the manifest"),
        ]))

    print(f"\n{len(ranked)} hypotheses, {len(nodes)} KG nodes, {len(edges)} edges, {len(PASSAGES)} passages")
    for h in ranked:
        print(f"  {h['rank']:>2}. {h['id']}  composite={h['scores']['composite']:.3f} "
              f"nov={h['scores']['novelty']:.2f}  {h['archetype']}")


if __name__ == "__main__":
    main()
