"""Do the Asian theoretical systems predict chemistry and target biology? — the central experiment.

Brief §11.5 promotes these from "negative controls" to the headline scientific question:

* does 四氣 (nature) predict compound volatility / polarity?
* does 五味 (flavour) predict the compound-class family?
* does 歸經 (channel tropism) predict the organ of the recorded indication?
* does Āyurvedic vīrya (hot/cold) predict thermolability / volatility?
* does tridoṣa effect separate action classes?

Every test reports an effect size (AUC or Spearman ρ), n, and a **permutation-test
p-value** against a real null distribution.  A null result is a result: the code does not
tune thresholds or hunt for a favourable subset, and the report says "no signal" when the
number says so.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from shennong import ontology
from shennong.kg.schema import Graph, node_id
from shennong.theory.features import (
    CHANNEL_ORGAN,
    DOSHA_ACTION_CLASSES,
    FLAVOR_CLASS_FAMILIES,
    RASA_ACTION_CLASSES,
    TheoryFeatures,
)

N_PERMUTATIONS = 1000
SEED = 0


# --------------------------------------------------------------------------------------
# Statistics helpers (no scipy)
# --------------------------------------------------------------------------------------


def auc(scores: list[float], labels: list[bool]) -> float | None:
    """ROC AUC via the Mann–Whitney U statistic (ties handled by average ranks)."""
    n = len(scores)
    if n != len(labels):
        raise ValueError("scores and labels must have equal length")
    positives = [s for s, lab in zip(scores, labels) if lab]
    negatives = [s for s, lab in zip(scores, labels) if not lab]
    if not positives or not negatives:
        return None
    # average ranks of all scores
    order = sorted(range(n), key=lambda i: scores[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    pos_rank_sum = sum(ranks[i] for i, lab in enumerate(labels) if lab)
    u = pos_rank_sum - len(positives) * (len(positives) + 1) / 2.0
    return u / (len(positives) * len(negatives))


def spearman(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 3 or n != len(y):
        return None
    rx, ry = _rankdata(x), _rankdata(y)
    mx, my = np.mean(rx), np.mean(ry)
    num = float(np.sum((np.array(rx) - mx) * (np.array(ry) - my)))
    den = float(np.sqrt(np.sum((np.array(rx) - mx) ** 2) * np.sum((np.array(ry) - my) ** 2)))
    return num / den if den else None


def _rankdata(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def permutation_p(observed: float, permuted: list[float], *, two_sided: bool = True) -> float:
    """Empirical permutation p-value with the +1 correction."""
    if observed is None or not permuted:
        return 1.0
    arr = np.asarray(permuted, dtype=float)
    if two_sided:
        extreme = np.sum(np.abs(arr - 0.5) >= abs(observed - 0.5)) if abs(observed) <= 1 else np.sum(np.abs(arr) >= abs(observed))
    else:
        extreme = np.sum(arr >= observed)
    return float((1 + extreme) / (len(arr) + 1))


def _perm_p_generic(observed: float, permuted: list[float], *, centre: float | None = None) -> float:
    """Two-sided permutation p based on |stat − null centre|.

    ``centre`` is 0.5 for AUC-type statistics and 0.0 for correlation-type statistics;
    it is passed explicitly so a lucky permutation range can never misclassify the test.
    """
    arr = np.asarray(permuted, dtype=float)
    if observed is None or arr.size == 0:
        return 1.0
    if centre is None:
        centre = 0.5 if (arr.min() >= 0.0 and arr.max() <= 1.0) else 0.0
    extreme = np.sum(np.abs(arr - centre) >= abs(observed - centre))
    return float((1 + extreme) / (arr.size + 1))


# --------------------------------------------------------------------------------------
# Graph → feature extraction
# --------------------------------------------------------------------------------------


def chemotype_vector(graph: Graph, binomial: str) -> dict[str, float] | None:
    """Mean polarity/volatility/thermolability and class-family fractions for a taxon."""
    from shennong.kg.queries import classes_of_taxon

    classes = list(classes_of_taxon(graph, binomial))
    if not classes:
        return None
    polarity = volatility = thermolability = 0.0
    counted = 0
    family_counts: dict[str, int] = defaultdict(int)
    for cls in classes:
        profile = ontology.compound_class_profile(cls)
        if profile is None:
            continue
        polarity += profile.polarity
        volatility += profile.volatility
        thermolability += profile.thermolability
        counted += 1
        for family, members in _CLASS_FAMILIES.items():
            if cls in members:
                family_counts[family] += 1
                break
        else:
            family_counts["other"] += 1
    if counted == 0:
        return None
    fractions = {f: c / counted for f, c in family_counts.items()}
    return {
        "polarity": polarity / counted,
        "volatility": volatility / counted,
        "thermolability": thermolability / counted,
        **{f"family_{f}": v for f, v in fractions.items()},
    }


_CLASS_FAMILIES: dict[str, frozenset[str]] = {
    "volatile": frozenset({"monoterpenoid", "monoterpenoid_ester", "phenylpropanoid", "sesquiterpenoid", "phthalide", "ketone"}),
    "alkaloid": frozenset({"alkaloid", "diester_alkaloid", "monoester_alkaloid", "purine"}),
    "saponin_terpenoid": frozenset({"triterpenoid_saponin", "steroidal_saponin", "triterpenoid", "steroidal_lactone", "steroidal", "sesquiterpene_lactone", "diterpenoid"}),
    "polyphenol": frozenset({"flavonoid", "phenolic_acid", "tannin", "coumarin", "lignan", "anthraquinone", "chromone", "curcuminoid"}),
    "carbohydrate": frozenset({"polysaccharide", "mucilage", "glycoside", "iridoid_glycoside", "monoterpenoid_glycoside", "phenolic_glycoside", "cyanogenic_glycoside"}),
    "mineral": frozenset({"mineral_salt", "heavy_metal"}),
    "lipid": frozenset({"fatty_acid", "resin"}),
}


def observed_organs(graph: Graph, binomial: str) -> list[str]:
    """Organs of all indications recorded for a taxon (with repeats per use)."""
    out: list[str] = []
    for edge in graph.out_edges(node_id("taxon", binomial), "treats"):
        node = graph.nodes[edge.dst]
        organ = node.props.get("organ")
        if organ:
            out.append(organ)
    return out


def observed_action_classes(graph: Graph, binomial: str) -> set[str]:
    out: set[str] = set()
    for edge in graph.out_edges(node_id("taxon", binomial), "treats"):
        node = graph.nodes[edge.dst]
        action = node.props.get("action_class")
        if action:
            out.add(action)
    return out


# --------------------------------------------------------------------------------------
# The tests
# --------------------------------------------------------------------------------------


def _result(metric: str, value: float | None, n: int, p: float, detail: str = "") -> dict:
    return {
        "metric": metric,
        "value": None if value is None else round(float(value), 4),
        "n": int(n),
        "p": round(float(p), 4),
        "detail": detail or ("no signal" if value is not None and abs(value - 0.5) < 0.05 else ""),
    }


def test_tcm_nature(graph: Graph, features: TheoryFeatures) -> dict:
    """四氣 (warm/cold) vs compound volatility and polarity."""
    rng = np.random.default_rng(SEED)
    records = []
    for binomial, props in features.tcm.items():
        if props.warmth is None:
            continue
        chem = chemotype_vector(graph, binomial)
        if chem is None:
            continue
        records.append((binomial, props.warmth, chem["volatility"], chem["polarity"]))
    n = len(records)
    if n < 8:
        return _result("auc", None, n, 1.0, "insufficient paired data for a theory test")
    warmth = [r[1] for r in records]
    vol = [r[2] for r in records]
    polar = [r[3] for r in records]
    warm_bin = [w > 0 for w in warmth]
    vol_high = [v > float(np.median(vol)) for v in vol]
    observed_auc = auc([float(w) for w in warmth], vol_high)
    observed_spearman = spearman([float(w) for w in warmth], vol)
    observed_spearman_polarity = spearman([float(w) for w in warmth], polar)
    perm_auc, perm_rho = [], []
    order = np.arange(n)
    for _ in range(N_PERMUTATIONS):
        shuffled = rng.permutation(order)
        w = [warmth[i] for i in shuffled]
        perm_auc.append(auc([float(v) for v in w], vol_high) or 0.5)
        perm_rho.append(spearman([float(v) for v in w], vol) or 0.0)
    p_auc = _perm_p_generic(observed_auc, perm_auc, centre=0.5)
    p_rho = _perm_p_generic(observed_spearman, perm_rho, centre=0.0)
    return {
        "metric": "auc",
        "value": None if observed_auc is None else round(observed_auc, 4),
        "n": n,
        "p": round(p_auc, 4),
        "detail": (
            f"warm (溫/熱) vs volatile-rich compound classes: AUC={observed_auc:.3f}, p={p_auc:.4f}; "
            f"Spearman(warmth, volatility)={observed_spearman:+.3f} (p={p_rho:.4f}); "
            f"Spearman(warmth, polarity)={observed_spearman_polarity:+.3f}"
        ),
        "spearman_vs_volatility": {
            "rho": None if observed_spearman is None else round(observed_spearman, 4),
            "p": round(p_rho, 4),
        },
        "spearman_vs_polarity": None if observed_spearman_polarity is None else round(observed_spearman_polarity, 4),
    }


def test_tcm_flavor(graph: Graph, features: TheoryFeatures) -> dict:
    """五味: does a drug's flavour predict the class family it contains?"""
    rng = np.random.default_rng(SEED)
    records = []
    for binomial, props in features.tcm.items():
        chem = chemotype_vector(graph, binomial)
        if chem is None or not props.flavors:
            continue
        records.append((binomial, set(props.flavors), chem))
    n = len(records)
    if n < 8:
        return _result("auc", None, n, 1.0, "insufficient paired data for a theory test")
    # per-flavour AUC: score = family fraction expected for that flavour
    per_flavour: dict[str, dict] = {}
    for flavour, family_classes in FLAVOR_CLASS_FAMILIES.items():
        # map expected compound classes → family names present in the vector
        expected_families = set()
        for cls in family_classes:
            for family, members in _CLASS_FAMILIES.items():
                if cls in members:
                    expected_families.add(family)
        if not expected_families:
            continue
        scores = [sum(rec[2].get(f"family_{fam}", 0.0) for fam in expected_families) for rec in records]
        labels = [flavour in rec[1] for rec in records]
        value = auc(scores, labels)
        if value is None:
            continue
        permuted = []
        for _ in range(N_PERMUTATIONS):
            shuffled = rng.permutation(len(records))
            shuffled_labels = [labels[i] for i in shuffled]
            v = auc(scores, shuffled_labels)
            permuted.append(v if v is not None else 0.5)
        per_flavour[flavour] = {
            "auc": round(value, 4),
            "n": int(sum(labels)),
            "p": round(_perm_p_generic(value, permuted, centre=0.5), 4),
        }
    if not per_flavour:
        return _result("auc", None, n, 1.0, "no flavour maps to a compound-class family")
    mean_auc = float(np.mean([v["auc"] for v in per_flavour.values()]))
    mean_p = float(np.mean([v["p"] for v in per_flavour.values()]))
    return {
        "metric": "auc",
        "value": round(mean_auc, 4),
        "n": n,
        "p": round(mean_p, 4),
        "detail": "mean AUC over flavours vs expected compound-class family: " + ", ".join(
            f"{fl} {v['auc']:.3f} (n={v['n']}, p={v['p']:.3f})" for fl, v in per_flavour.items()
        ),
        "per_flavour": per_flavour,
    }


def test_tcm_channel(graph: Graph, features: TheoryFeatures) -> dict:
    """歸經: does the channel set predict the organ of the recorded indications?"""
    rng = np.random.default_rng(SEED)
    records = []  # (drug index, observed organ)
    channel_sets: list[set[str]] = []
    for binomial, props in features.tcm.items():
        if not props.channels:
            continue
        organs = observed_organs(graph, binomial)
        if not organs:
            continue
        predicted = {CHANNEL_ORGAN[c] for c in props.channels if c in CHANNEL_ORGAN}
        if not predicted:
            continue
        channel_sets.append(predicted)
        records.extend((len(channel_sets) - 1, organ) for organ in organs)
    n_pairs = len(records)
    n_drugs = len(channel_sets)
    if n_pairs < 10 or n_drugs < 6:
        return _result("auc", None, n_pairs, 1.0, "insufficient paired data for a theory test")

    def hit_rate(index_map: dict[int, set[str]]) -> float:
        hits = [1.0 if organ in index_map[drug_idx] else 0.0 for drug_idx, organ in records]
        return float(np.mean(hits))

    observed = hit_rate({i: s for i, s in enumerate(channel_sets)})
    permuted = []
    order = list(range(n_drugs))
    for _ in range(N_PERMUTATIONS):
        shuffled = rng.permutation(order)
        permuted.append(hit_rate({i: channel_sets[shuffled[i]] for i in range(n_drugs)}))
    perm_mean = float(np.mean(permuted))
    p = float((1 + sum(v >= observed for v in permuted)) / (len(permuted) + 1))
    return {
        "metric": "hit_rate",
        "value": None if observed is None else round(observed, 4),
        "n": n_pairs,
        "p": round(p, 4),
        "permutation_mean": round(perm_mean, 4),
        "detail": (
            f"channel-predicted organ vs recorded indication organ over {n_pairs} (drug, use) pairs "
            f"from {n_drugs} drugs: hit rate {observed:.3f}, permutation mean {perm_mean:.3f}, "
            f"one-sided p={p:.4f}. Set-valued predictors have no natural AUC; hit rate is the direct statistic."
        ),
    }


def test_ayurveda_virya(graph: Graph, features: TheoryFeatures) -> dict:
    """Vīrya (uṣṇa/śīta) vs compound thermolability and volatility."""
    rng = np.random.default_rng(SEED)
    records = []
    for binomial, props in features.ayurveda.items():
        hot = props.is_hot_virya
        if hot is None:
            continue
        chem = chemotype_vector(graph, binomial)
        if chem is None:
            continue
        records.append((binomial, 1 if hot else 0, chem["thermolability"], chem["volatility"]))
    n = len(records)
    if n < 8:
        return _result("rho", None, n, 1.0, "insufficient paired data for a theory test")
    virya = [float(r[1]) for r in records]
    thermo = [r[2] for r in records]
    vol = [r[3] for r in records]
    observed = spearman(virya, thermo)
    permuted = []
    for _ in range(N_PERMUTATIONS):
        shuffled = rng.permutation(virya)
        v = spearman(list(shuffled), thermo)
        permuted.append(v if v is not None else 0.0)
    p = _perm_p_generic(observed, permuted, centre=0.0)
    vol_rho = spearman(virya, vol)
    return {
        "metric": "rho",
        "value": None if observed is None else round(observed, 4),
        "n": n,
        "p": round(p, 4),
        "detail": (
            f"Spearman(hot vīrya, thermolability)={observed:+.3f} (p={p:.4f}); "
            f"Spearman(hot vīrya, volatility)={vol_rho:+.3f}" if observed is not None else "no signal"
        ),
        "spearman_vs_volatility": None if vol_rho is None else round(vol_rho, 4),
    }


def test_tridosha(graph: Graph, features: TheoryFeatures) -> dict:
    """Doṣa effect vs action-class overlap (observed vs predicted sets)."""
    rng = np.random.default_rng(SEED)
    records = []
    predicted_sets: list[set[str]] = []
    for binomial, props in features.ayurveda.items():
        observed = observed_action_classes(graph, binomial)
        if not observed or not props.dosha_effect:
            continue
        predicted: set[str] = set()
        for dosha, direction in props.dosha_effect.items():
            if direction < 0:  # pacifying this doṣa
                predicted |= set(DOSHA_ACTION_CLASSES.get(dosha, ()))
        if not predicted:
            continue
        predicted_sets.append(predicted)
        records.append((len(predicted_sets) - 1, observed))
    n = len(records)
    if n < 8:
        return _result("overlap", None, n, 1.0, "insufficient paired data for a theory test")

    def mean_jaccard(index_map: dict[int, set[str]]) -> float:
        vals = []
        for idx, observed in records:
            pred = index_map[idx]
            vals.append(len(pred & observed) / len(pred | observed))
        return float(np.mean(vals))

    observed_value = mean_jaccard({i: s for i, s in enumerate(predicted_sets)})
    permuted = []
    for _ in range(N_PERMUTATIONS):
        shuffled = rng.permutation(len(predicted_sets))
        permuted.append(mean_jaccard({i: predicted_sets[shuffled[i]] for i in range(len(predicted_sets))}))
    p = float((1 + sum(v >= observed_value for v in permuted)) / (len(permuted) + 1))
    return {
        "metric": "overlap",
        "value": round(observed_value, 4),
        "n": n,
        "p": round(p, 4),
        "detail": (
            f"mean Jaccard(predicted action classes from doṣa effect, observed action classes)="
            f"{observed_value:.3f}; permutation mean {float(np.mean(permuted)):.3f}; p={p:.4f}"
        ),
        "permutation_mean": round(float(np.mean(permuted)), 4),
    }


def theory_predictivity(graph: Graph, features: TheoryFeatures) -> dict:
    """Run all Asian-theory predictivity tests and return a report block."""
    return {
        "tcm_nature": test_tcm_nature(graph, features),
        "tcm_flavor": test_tcm_flavor(graph, features),
        "tcm_channel": test_tcm_channel(graph, features),
        "ayurveda_virya": test_ayurveda_virya(graph, features),
        "tridosha": test_tridosha(graph, features),
        "warning": (
            "These are tests of association between classical assignments and coarse "
            "compound-class chemistry. They cannot establish causal validity; a positive "
            "result means the classical variable is informative about chemotype, a null "
            "result is reported as a null, not massaged into a positive."
        ),
    }


# --------------------------------------------------------------------------------------
# Negative controls (brief §2 / §10.7)
# --------------------------------------------------------------------------------------


def control_quxiangbilei(graph: Graph, features: TheoryFeatures) -> dict:
    """取象比類: does the colour morpheme in a drug name predict the indication organ?"""
    rng = np.random.default_rng(SEED)
    drug_colours: dict[str, str] = {}
    for binomial in graph_taxa(graph):
        name = binomial
        node = graph.get("taxon", binomial)
        synonyms = str(node.props.get("synonyms", "")) if node else ""
        for text in [name, synonyms]:
            for colour, organ in ontology.COLOUR_ORGAN.items():
                if colour in text and binomial not in drug_colours:
                    drug_colours[binomial] = organ
    records = []
    for binomial, predicted_organ in drug_colours.items():
        organs = observed_organs(graph, binomial)
        if not organs:
            continue
        for organ in organs:
            records.append((predicted_organ, organ))
    n = len(records)
    if n < 10:
        return {"rho": 0.0, "p": 1.0, "auc": None, "n": n,
                "detail": "insufficient colour-named drugs with recorded indications"}
    hits = [1.0 if predicted == organ else 0.0 for predicted, organ in records]
    observed = float(np.mean(hits))
    permuted = []
    for _ in range(N_PERMUTATIONS):
        shuffled = [hits[i] for i in rng.permutation(len(hits))]
        permuted.append(float(np.mean(shuffled)))
    perm_mean = float(np.mean(permuted))
    p = float((1 + sum(abs(v - perm_mean) >= abs(observed - perm_mean) for v in permuted)) / (len(permuted) + 1))
    return {
        "rho": round(observed - perm_mean, 4),
        "p": round(p, 4),
        "hit_rate": round(observed, 4),
        "permutation_mean": round(perm_mean, 4),
        "n": n,
        "detail": (
            f"colour→organ hit rate {observed:.3f} vs permutation mean {perm_mean:.3f} over {n} "
            f"(drug, use) pairs; two-sided permutation p={p:.4f}. rho is the excess hit rate over the "
            "permutation null (not a correlation coefficient). This tests whether the classical "
            "colour–organ analogy predicts the recorded indication organ above chance."
        ),
    }


def control_ayurveda_rasa(graph: Graph, features: TheoryFeatures) -> dict:
    """Ṣaḍrasa: does the primary taste predict the action class of the recorded uses?"""
    rng = np.random.default_rng(SEED)
    records = []
    for binomial, props in features.ayurveda.items():
        rasa = props.primary_rasa
        if not rasa or rasa not in RASA_ACTION_CLASSES:
            continue
        observed = observed_action_classes(graph, binomial)
        if not observed:
            continue
        records.append((set(RASA_ACTION_CLASSES[rasa]), observed))
    n = len(records)
    if n < 8:
        return {"rho": 0.0, "p": 1.0, "n": n, "detail": "insufficient rasa data"}
    hit_rate = float(np.mean([len(pred & obs) / len(pred | obs) for pred, obs in records]))
    permuted = []
    for _ in range(N_PERMUTATIONS):
        shuffled = rng.permutation(n)
        permuted.append(float(np.mean([len(records[shuffled[i]][0] & records[i][1]) / len(records[shuffled[i]][0] | records[i][1]) for i in range(n)])))
    perm_mean = float(np.mean(permuted))
    p = float((1 + sum(abs(v - perm_mean) >= abs(hit_rate - perm_mean) for v in permuted)) / (len(permuted) + 1))
    excess = hit_rate - perm_mean
    return {
        "rho": round(excess, 4),
        "p": round(p, 4),
        "hit_rate": round(hit_rate, 4),
        "permutation_mean": round(perm_mean, 4),
        "n": n,
        "detail": (
            f"primary-rasa predicted action classes vs observed action classes: mean Jaccard "
            f"{hit_rate:.3f} (permutation mean {np.mean(permuted):.3f}, p={p:.4f}); rho is the "
            "excess hit rate over the permutation null."
        ),
    }


def graph_taxa(graph: Graph) -> list[str]:
    return [node.label for node in graph.by_type("taxon")]
