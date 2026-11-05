# GLOSSARY

Terms a technical judge will meet in this repository. Two vocabularies collide here — ethnopharmacology and
the classical theoretical systems — and neither is obvious to a reader from the other side.

Each entry gives: the term, a working translation, what it means *operationally in this project*, and why it
matters for the science. Where a term is contested in the literature, that is said.

---

## Part 1 · The classical Chinese theoretical system

### 四氣五味 · sì qì wǔ wèi — four natures, five flavours
The core property vector of Chinese materia medica. **四氣** (also 四性): 寒 cold, 熱 hot, 溫 warm, 涼 cool,
平 neutral — a drug's thermal action. **五味**: 辛 pungent, 甘 sweet, 酸 sour, 苦 bitter, 鹹 salty, with 淡
bland and 澀 astringent sometimes added, each associated with a direction of action (辛 disperses, 甘
harmonises/nourishes, 酸 gathers, 苦 drains, 鹹 softens).
**In SHENNONG:** encoded as an ordinal nature axis plus a multi-hot flavour vector, then tested against
measured polarity, thermolability and volatility (`docs/EVALUATION.md` T1, T3). This is the single most
leveraged encoding decision in the project.

### 歸經 · guī jīng — channel tropism
Which **meridian/channel system** (經絡) and therefore which organ a drug is said to act on. "Enters the Liver
and Heart channels" is a claim about anatomical compartment and target tissue.
**In SHENNONG:** encoded as multi-hot over twelve channels and tested against **target organ and receptor
family** (T2). This is the most direct theory→modern-biology mapping available, and therefore the most
interesting test. Note the honest caveat: channel assignments differ between editions, and we inherited the
disagreement instead of picking a winner.

### 升降浮沉 · shēng jiàng fú chén — direction of action
Upward (升), downward (降), floating/outward (浮), sinking/inward (沉). A drug's tendency to move action toward
the surface or the interior, upward or downward.
**In SHENNONG:** recorded as data but **not tested** — there is no obvious modern correlate we can defend, so
we say so rather than inventing one (`docs/METHODOLOGY.md` §3).

### 君臣佐使 · jūn chén zuǒ shǐ — sovereign, minister, assistant, courier
The four **roles** of ingredients in a formula. 君 (emperor) addresses the principal pattern; 臣 (minister)
supports it; 佐 (assistant) modifies or moderates; 使 (courier) directs the action and often guides the
formula to a channel or enhances delivery.
**In SHENNONG:** encoded as typed edges on the formula node, not as an attribute — which allows the corpus-wide
query "are 使-role herbs enriched for pharmacokinetic modulators?" That is hypothesis H-07, and it is testable
against ChEMBL CYP3A4/P-gp data. This role hierarchy is also what makes the conservation analysis possible:
a CITES-listed 君 ingredient is structurally load-bearing in a way a 佐 is not.

### 七情 · qī qíng — the seven relations of combination
The classical taxonomy of how two drugs interact: 單行 (used alone), 相須 (mutual necessity), 相使 (mutual
enhancement), 相畏 (mutual restraint), 相殺 (mutual suppression), 相惡 (mutual antagonism), 相反 (mutual
incompatibility).
**In SHENNONG:** this is the most important term in the project's interaction class. It is a **pre-modern
drug-interaction taxonomy**, and 相惡/相反 encode negative interactions — i.e. it is a hypothesis set about
pharmacokinetic and pharmacodynamic interactions, asserted for centuries and almost never tested as such.

### 十八反 · shí bā fǎn — the eighteen antagonisms
A canonical list of eighteen herb pairs considered mutually incompatible: 本草明言十八反，半蔞貝蘞及攻烏，
藻戟遂芫俱戰草，諸參辛芍叛藜蘆 (the mnemonic from 儒門事親, 1228). Classic example: 甘草 + 甘遂.
**In SHENNONG:** encoded as `incompatible_18fan` graph edges with the asserting source attached. Hypothesis
H-05 proposes these are largely **pharmacokinetic** rather than pharmacological antagonisms, and gives the
18 pairs as an enrichment test against a shuffled null.

### 十九畏 · shí jiǔ wèi — the nineteen mutual fears
A second list of incompatible pairs, partly overlapping. The famous entry is 水銀莫與砒霜見 — "mercury must not
meet arsenic".
**In SHENNONG:** encoded as `incompatible_19wei`. Treated strictly as **toxicology data**: a hypothesis about
speciation and thiol chemistry (H-06), never a preparation question. All output here is hazard ranking.

### 炮制 · páo zhì — processing
The set of pre-preparation procedures that transform a crude drug: 炮 (roast), 煅 (calcine), 煨 (roast in
wrapped medium), 淬 (quench), 蒸 (steam), 炒 (stir-fry), 炙 (co-fire with honey/wine/vinegar), 浸 (soak),
九蒸九曬 (nine steam-and-sun cycles), 麴 (ferment).
**In SHENNONG:** the highest-value translation problem in the corpus. Each term is mapped to a modern
operation with parameters where the text supplies them (`corpus/processed/structured/processing.csv`).
The insight the project is built around: 雷公炮炙論 specifies *endpoints* ("roast until it splits") that
correspond to hydrolysis, oxidation, volatilisation and complexation stages — i.e. it is process chemistry
written in operational language.

### 異名同物 / 同名異物 · yì míng tóng wù / tóng míng yì wù — one thing many names / one name many things
The two directions of nomenclature drift. 異名同物: several historical names for one taxon. 同名異物: one name
covering different taxa in different eras or regions.
**In SHENNONG:** a first-class **discovery class**, and the most immediately useful public-health output.
Worked example: 木通 has denoted both *Akebia* (harmless) and *Aristolochia manshuriensis* (aristolochic acid,
IARC Group 1). The collision is ranked by **toxicity divergence** between the colliding taxa.

### 取象比類 · qǔ xiàng bǐ lèi — reasoning by analogy/resemblance
Deriving a drug's action from morphological, colour or habitat resemblance to a body part or process — the
"doctrine of signatures" of Chinese medicine. Walnut looks like a brain, therefore it tonifies the brain.
**In SHENNONG:** a **negative control**, not a method. It is the reasoning pattern a naive text-mining system
will "discover" if you do not test for it. Reported as ρ and p on every run; a strong positive would
invalidate our extraction (`docs/EVALUATION.md` §3.1).

### 三品 · sān pǐn — the three grades
The 神農本草經 classification: 上品 (upper — non-toxic, for long-term use), 中品 (middle — conditional), 下品
(lower — toxic, for acute use only).
**In SHENNONG:** encoded as an ordinal hazard prior. 下品 is a toxicity class from 200 CE, and it turns out to
be a usable prior (`docs/METHODOLOGY.md` §3).

### 五行 · wǔ xíng — the five phases
Wood, fire, earth, metal, water — a correlative system linking organs, seasons, colours, flavours and emotions.
**In SHENNONG:** recorded in the ontology (`concept` nodes) because it structures the source texts, but **not
used as a predictor**. It is too coarse to operationalise without inventing a mapping, and inventing mappings
is exactly what this project refuses to do.

### 經絡 · jīng luò — channels and network vessels
The meridian system through which qi and blood move, and along which acupuncture points are located.
**In SHENNONG:** the referent of 歸經, and the reason channel tropism is testable: it is a claim about *where*
a drug acts. The acupuncture tier of the corpus (黃帝內經, 難經, 針灸甲乙經, 針灸大成) supplies the terminology.

---

## Part 2 · The Ayurvedic theoretical system

### ṣaḍrasa — the six tastes
madhura (sweet), amla (sour), lavaṇa (salty), kaṭuka (pungent), tikta (bitter), kaṣāya (astringent).
Each taste is held to have a specific action on the doṣas.
**In SHENNONG:** encoded as a multi-hot vector, tested against pharmacological action class (T5).

### guṇa — quality
Twenty qualities in ten opposed pairs (heavy/light, cold/hot, oily/dry, etc.). The operational quality is
usually taken from **vīrya** (below), because guṇa is a broader descriptor.
**In SHENNONG:** recorded; the opposing pairs are encoded ordinally where a modern correlate exists.

### vīrya — potency
The heating or cooling potency of a drug: **uṣṇa** (hot) or **śīta** (cold). This is the Ayurvedic analogue of
四氣, and the cleanest cross-tradition test in the project.
**In SHENNONG:** tested against logP and thermolability (T4). If the TCM 四氣 test and the Ayurvedic vīrya test
agree in direction, that is independent-tradition convergence — which is far stronger evidence than either
alone.

### vipāka — post-digestive effect
The taste a drug is said to have *after* digestion (madhura, amla, or kaṭuka).
**In SHENNONG:** encoded as a field; not yet tested, because "post-digestive" has no agreed modern operationalisation.

### prabhāva — specific action
The idiosyncratic effect of a drug not explained by its other properties. In practice, the term the tradition
uses when its own system does not predict the observed effect.
**In SHENNONG:** encoded, and treated as an honest admission: a system that needs a residual category is a
system whose predictions are incomplete. We do not test it; we count how often it is invoked.

### tridoṣa — the three humours
vāta (wind/movement), pitta (bile/transformation), kapha (phlegm/structure). Health is their balance.
**In SHENNONG:** encoded as a three-way `doṣa_effect` field on drugs; a candidate predictor for
inflammatory-versus-metabolic action class.

### viruddha — incompatible combination
Ayurvedic counterpart of 十八反/十九畏: food and drug combinations held to be incompatible because they
aggravate the doṣas without expelling them.
**In SHENNONG:** third incompatibility rule system in the graph (`incompatible_viruddha`), enabling a
cross-tradition comparison of interaction rules — do the two traditions agree about the same plant pairs?

### rasaśāstra — mercurial/metallic pharmacy
The Indian alchemical pharmaceutical tradition: metals and minerals purified, incinerated and combined into
medicines, including **bhasma**.

### bhasma — incinerated metal/mineral preparation
A metal or mineral repeatedly incinerated with herbal media until it becomes a fine ash-like powder whose
toxicity is held to have been removed and whose potency is made subtle.
**In SHENNONG:** treated as a **toxicology and speciation** subject, never as a preparation. The analytic
interest is real (particle size, speciation, bioavailability) and the safety constraint is absolute: hazard
analysis only, and the Ask surface refuses preparation questions in this class.

---

## Part 3 · Ethnopharmacology and natural-product chemistry

### ethnopharmacology
The study of medicinal substances used by particular cultures, combining field observation, historical
philology, botany and pharmacology. Its central methodological problem is the one this project attacks:
**the evidence is textual and interpretive, while the claims are mechanistic.**

### materia medica
The body of substances used as medicines in a tradition — for Chinese medicine, the 本草 ("rooted in herbs")
corpus. Not a list of plants: a list of *used forms*, with parts, preparations and grades.

### pharmacognosy
The study of medicinal drugs from natural sources: identity, purity, constituents, and their biological
activity. Closest traditional discipline to what SHENNONG automates.

### chemotype
A chemically distinct population within one species — e.g. linalool-rich versus camphor-rich lavender.
**Why it matters here:** a classical drug name does not specify a chemotype, so a claim about "lavender"
may be a claim about a plant whose chemistry varies by an order of magnitude. Chemotype is where
historical claims and modern chemistry most often fail to meet.

### LC-MS / LC-MS/MS
Liquid chromatography–mass spectrometry. The workhorse analytical method in the falsification plans: it is how
you quantify the diester/monester diterpene alkaloids in processed vs raw 附子, and it is cheap enough that
"test this" is a realistic ask.

### PAINS — pan-assay interference compounds
Compounds that appear active in many assays for reasons unrelated to specific target binding (redox cycling,
metal chelation, aggregation, fluorescence). Curcumin and many flavonoids and anthraquinones are the canonical
examples.
**In SHENNONG:** encoded as a liability flag on compound nodes, and the reason hypotheses H-05 and H-10 are
explicitly framed as possible assay artefacts rather than leads.

### Lipinski's rule of five
Drug-likeness heuristics: MW < 500 Da, logP < 5, H-bond donors ≤ 5, acceptors ≤ 10. A screening filter, not a
verdict.
**In SHENNONG:** evaluated rule by rule; molecular weight is computed from the formula (checkable arithmetic),
while logP/HBD/HBA are **null until a structure is resolved** — reported as "1 of 4 evaluated", never as
"compliant".

### SMILES / InChIKey
Line-notation representations of molecular structure, and the hash form used to match a compound across
databases.
**In SHENNONG:** a structure is resolved by name against PubChem and stored as SMILES; if it cannot be
resolved, the field is `null` and the interface says so. We do not invent structures.

### target, mechanism, pathway
**Target**: the molecular entity a drug acts on (a receptor, enzyme, transporter, channel).
**Mechanism**: the causal chain from binding to effect.
**Pathway**: the signalling cascade the target sits in.
**In SHENNONG:** these three are separate fields on every candidate, because "it works via NF-κB" (pathway),
"it alkylates p65 Cys38" (mechanism) and "it inhibits NF-κB p65" (target) are different claims with different
falsification tests.

### falsification plan
The specific experiment that could kill a hypothesis, with a named readout, a discriminating arm, a positive
control, and a stated retraction condition.
**In SHENNONG:** not optional. Every emitted hypothesis carries one, and a hypothesis whose plan cannot
produce a negative result is not emitted (`docs/METHODOLOGY.md` §6).

### permutation null
The statistical control used throughout: shuffle the predictor (the theory vector, or the plant↔use edges),
recompute the statistic 10,000 times, and place the observed value in that distribution.
**Why it is the backbone of this project:** with small, imbalanced, historically contaminated data, almost any
plausible feature looks predictive. The permutation null is what distinguishes a result from a coincidence.

### Nagoya Protocol
The 2010 supplementary agreement to the Convention on Biological Diversity governing access to genetic
resources and the fair and equitable sharing of benefits from their utilisation.
**In SHENNONG:** the model for our Traditional Knowledge position (`docs/SAFETY_AND_ETHICS.md` §4) — attribution,
prior agreement, benefit-sharing, and an opt-out mechanism.

### CITES
The Convention on International Trade in Endangered Species. Appendices I and II list species whose trade is
prohibited or regulated.
**In SHENNONG:** CITES status is joined to the taxon table and attached to every formula ingredient, which is
how the conservation substitution list is generated.

---

## Part 4 · Engineering terms used with project-specific meanings

### 采 Cǎi / 制 Zhì / 配 Pèi / 使 Shǐ
The four classical operations of Chinese pharmacy — collect, prepare, combine, deploy — used as the pipeline
vocabulary in code, CLI, docs and UI (`docs/METHODOLOGY.md` §2). Using the tradition's own vocabulary for the
engineering stages is a deliberate choice: the texts are the specification, and the names keep that visible.

### theory vector
The encoded property set (四氣五味, 歸經, direction, grade; and rasa/guṇa/vīrya/vipāka/tridoṣa for the Ayurvedic
material) treated as a machine-learning feature matrix. The object under test in the central experiment.

### discovery class
One of six kinds of finding SHENNONG produces — 配伍禁忌, 炮制, 异名同物, 君臣佐使, 未研究本草, 濒危代用品 —
each with its own module, failure modes and falsification test.

### drug candidate
The terminal artefact: classical lead → chemotype → molecule (formula, computed MW, structure if resolved) →
novelty vs modern chemistry → mechanism → development path → residual risk. Distinct from a hypothesis, which
is the reasoning layer beneath it.

### DEMO FIXTURE
Data shipped in `app/data/` so the Workbench can be built and demonstrated before the pipeline artefacts
exist. Every panel running on it displays a `DEMO FIXTURE` badge, and the server prints a per-panel
`LIVE`/`FIXTURE` banner at startup. `python app/serve.py --strict` refuses to start at all if any panel would
show fixture data, which is the mode we use for the final recording.
