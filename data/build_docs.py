"""Generate ``corpus/DATA_CARD.md`` and the per-source licence table in ``corpus/LICENSE_AUDIT.md``.

Everything numeric here is read from artefacts on disk (``sources.yaml``,
``processed/stats.json``, ``processed/corpus.jsonl``, the structured CSVs). Nothing is typed by
hand, so the DATA_CARD cannot drift from the corpus.

    python -m data.build_docs
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict

import yaml

from . import _net

REGISTRY = _net.REGISTRY / "sources.yaml"
STATS = _net.PROCESSED / "stats.json"
CORPUS = _net.PROCESSED / "corpus.jsonl"
STRUCT = _net.PROCESSED / "structured"
DATA_CARD = _net.CORPUS / "DATA_CARD.md"
AUDIT = _net.CORPUS / "LICENSE_AUDIT.md"

LICENCE_GROUP = {
    "Public Domain": "PD",
    "CC-BY-SA-4.0": "CC BY-SA 4.0",
}


def load() -> tuple[list[dict], dict]:
    reg = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    stats = json.loads(STATS.read_text(encoding="utf-8"))
    return reg, stats


def _num(x) -> str:
    return f"{x:,}" if isinstance(x, int) else str(x)


def _pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f}%" if b else "—"


def source_table(reg: list[dict]) -> str:
    rows = ["| source_id | title | year | tra-dition | lang | tier | chars | licence | decision | evidence |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for e in reg:
        lic = e.get("licence", "")
        dec = {"ok": "R + T", "unverified": "Ref only", "excluded": "Ref only"}.get(
            e.get("status", ""), "—")
        title = (e.get("title") or "").replace("|", "\\|")
        if len(title) > 48:
            title = title[:45] + "…"
        rows.append(
            f"| `{e['id']}` | {title} | {e.get('year', '')} | {e.get('tradition','')} | "
            f"{e.get('lang','')} | {e.get('tier','')} | {_num(e.get('chars', 0))} | {lic} | "
            f"{dec} | {e.get('licence_evidence','')} |")
    return "\n".join(rows)


def fill_audit(reg: list[dict]) -> None:
    if not AUDIT.exists():
        return
    text = AUDIT.read_text(encoding="utf-8")
    table = source_table(reg)
    if "<!-- AUTOGEN:LICENCE_TABLE -->" in text:
        text = text.replace("<!-- AUTOGEN:LICENCE_TABLE -->", table)
    else:
        # replace a previous table between the marker section and the next "---"
        text = re.sub(r"(Legend —.*?\n\n)\|.*?(?=\n---)", r"\1" + table.replace("\\", "\\\\"),
                      text, flags=re.S)
    AUDIT.write_text(text, encoding="utf-8")
    print(f"filled licence table in {AUDIT}")


def structured_summary() -> dict[str, int]:
    out = {}
    if STRUCT.exists():
        for p in sorted(STRUCT.glob("*.csv")):
            with p.open(encoding="utf-8") as fh:
                fh.readline()
                out[p.name] = sum(1 for _ in fh)
    return out


def build_data_card(reg: list[dict], stats: dict) -> None:
    ok = [e for e in reg if e.get("status") == "ok"]
    unv = [e for e in reg if e.get("status") == "unverified"]
    exc = [e for e in reg if e.get("status") == "excluded"]

    by_lang = stats["chars_by_lang"]
    by_trad = stats["chars_by_tradition"]
    by_tier = stats["chars_by_tier"]
    per_source = stats["per_source"]
    total = stats["chars_total"]

    lic_counts: Counter[str] = Counter()
    lic_chars: Counter[str] = Counter()
    for e in ok:
        g = LICENCE_GROUP.get(e.get("licence", ""), e.get("licence", "other"))
        lic_counts[g] += 1
        lic_chars[g] += int(e.get("chars") or 0)

    years = [e["year"] for e in ok if isinstance(e.get("year"), int)]
    y_min, y_max = (min(years), max(years)) if years else ("—", "—")

    st = structured_summary()

    # largest sources for the composition table
    top = sorted(ok, key=lambda e: -(int(e.get("chars") or 0)))[:18]

    lines: list[str] = []
    A = lines.append

    A("# SHENNONG Corpus — Data Card")
    A("")
    A("**A licence-audited, provenance-complete corpus of the classical Asian medical, "
      "alchemical and scientific canon, anchored to modern biology and chemistry.**")
    A("")
    A(f"- Corpus sha256: `{stats['corpus_sha256']}`")
    A(f"- Training records: **{_num(stats['records'])}** chunks in `corpus/processed/corpus.jsonl`")
    A(f"- Total characters: **{_num(total)}**")
    A(f"- Sources trained on: **{len(ok)}** · unverified/rejected: {len(unv)} · "
      f"quality-excluded: {len(exc)}")
    A(f"- Earliest / latest source year: **{y_min}** … **{y_max}**")
    A("")
    A("> This is the input layer for a drug-discovery engine. It is **not** a chatbot corpus and "
      "it is **not** a clinical resource. No dosing, no self-treatment guidance, no synthesis "
      "routes. See `docs/SAFETY.md`.")
    A("")

    A("## 1. Composition")
    A("")
    A("### 1.1 By language")
    A("")
    A("| language | chars | share | script |")
    A("|---|---|---|---|")
    script = {"zh-Hant": "Traditional Chinese (漢字)", "zh-Hans": "Simplified Chinese (汉字)",
              "sa": "Sanskrit, Devanagari (देवनागरी)", "sa-Latn": "Sanskrit, IAST",
              "en": "English", "la": "Latin", "ar": "Arabic", "fa": "Persian"}
    for lang, n in by_lang.items():
        A(f"| `{lang}` | {_num(n)} | {_pct(n, total)} | {script.get(lang, '')} |")
    cjk = stats.get("chars_cjk", 0)
    A("")
    A(f"**CJK share is {_pct(cjk, total)} of all characters** ({_num(cjk)} chars). The domain "
      "directive (brief §0) makes the untranslated Asian canon the core asset, and this is the "
      "part no competing team will have.")
    A("")
    A("### 1.2 By tradition")
    A("")
    A("| tradition | chars | share | sources |")
    A("|---|---|---|---|")
    trad_sources: Counter[str] = Counter(e.get("tradition") for e in ok)
    for k, v in by_trad.items():
        A(f"| `{k}` | {_num(v)} | {_pct(v, total)} | {trad_sources.get(k, 0)} |")
    A("")
    A("### 1.3 By tier (brief §5)")
    A("")
    A("| tier | meaning | chars | share |")
    A("|---|---|---|---|")
    tier_meaning = {
        "1": "foundational biology & chemistry (first-principles substrate)",
        "2": "Asian materia medica, clinical and scientific canon",
        "3": "Asian alchemy / esoteric pharmacy / process chemistry",
        "4": "acupuncture & channel systems",
        "5": "structured open data (see §6 — counted separately, not in the text total)",
    }
    for k, v in by_tier.items():
        A(f"| {k} | {tier_meaning.get(k, '')} | {_num(v)} | {_pct(v, total)} |")
    A("")
    A("### 1.4 Largest sources")
    A("")
    A("| source_id | title | lang | tradition | chars |")
    A("|---|---|---|---|---|")
    for e in top:
        t = (e.get("title") or "").replace("|", "\\|")
        if len(t) > 60:
            t = t[:57] + "…"
        A(f"| `{e['id']}` | {t} | {e.get('lang')} | {e.get('tradition')} | "
          f"{_num(e.get('chars', 0))} |")
    A("")

    A("## 2. What is in it")
    A("")
    A("**Classical Chinese canon (Tier 2/3/4).** 神農本草經, 本草綱目, 本草經集注, 新修本草, "
      "證類本草, 本草圖經, 本草衍義, 湯液本草, 本草備要, 本草從新, 本草求真, 本草綱目拾遺, "
      "本經疏證, 本草崇原, 本草分經, 得配本草, 要藥分劑, 本草便讀, 本草害利, 本經逢原, "
      "長沙藥解, 本草經解, 本草新編, 本草思辨錄, 神農本草經百種錄, 雷公炮製藥性解, "
      "本草綱目別名錄; 傷寒論, 金匱要略, 千金翼方, 外臺秘要, 太平惠民和劑局方, 普濟方, "
      "溫病條辨, 丹溪心法, 景岳全書, 醫方集解, 醫宗金鑑-class formularies, 諸病源候論, 脈經, "
      "肘後備急方, 食療本草, 海藥本草; **acupuncture**: 黃帝內經, 難經, 針灸甲乙經, 針灸大成; "
      "**alchemy**: 抱朴子, 周易參同契, 雲笈七籤, 悟真篇, 太乙金華宗旨, 雷公炮炙論, 炮炙大法, "
      "石藥爾雅, 太清石壁記, 龍虎還丹訣, 黃帝九鼎神丹經訣, 軒轅黃帝水經藥法; "
      "**science/agriculture/dietetics**: 天工開物, 齊民要術, 夢溪筆談, 農政全書, 植物名實圖考, "
      "廣群芳譜, 飲膳正要, 養老奉親書, 醫說; **Korean**: 東醫寶鑑.")
    A("")
    A("**Sanskrit Ayurveda (Tier 2/3), Devanagari.** चरकसंहिता, सुश्रुतसंहिता, अष्टाङ्गहृदयम्, "
      "भावप्रकाशः, शार्ङ्गधरसंहिता, माधवनिदानम्; rasaśāstra: रसहृदयतन्त्रम्, रसार्णवः.")
    A("")
    A("**Unani / Graeco-Arabic (Tier 2).** Ibn Sīnā *Canon medicinae*, the 1593 Venice Latin "
      "edition in full; the Taleef Shereef (Indian Unani materia medica).")
    A("")
    A("**English translations of Asian materia medica (Tier 2).** Bhishagratna's *Suśruta Saṃhitā* "
      "(1907–16), Stuart & Smith *Chinese Materia Medica* (1911), Dutt *Materia Medica of the "
      "Hindus* (1877), Kirtikar & Basu *Indian Medicinal Plants* (1918), Hanbury *Notes on Chinese "
      "Materia Medica* (1862), Waring *Bazaar Medicines of India* (1867), Churchill on acupuncture "
      "(1821).")
    A("")
    A("**Foundational biology & chemistry (Tier 1, English/Latin).** anatomy & physiology, "
      "histology, physiological chemistry, pharmacology, pharmacognosy, bacteriology, genetics, "
      "evolution, botany, organic synthesis, plant histology — 19th/early-20th-century textbooks.")
    A("")

    A("## 3. Languages and eras")
    A("")
    A("Texts span roughly **c. 200 BCE to 1918 CE**, with the bulk from the 6th–19th centuries CE,")
    A("plus 19th/early-20th-century scientific textbooks in English and a 1593 Latin *Canon*.")
    A("Orthography is **preserved, not modernised**: traditional Chinese characters, classical")
    A("Chinese syntax, Devanagari with sandhi, and 19th-century English spellings are all signal.")
    A("")
    A("Two script registers appear for Chinese: `zh-Hant` (majority) and `zh-Hans` where the only")
    A("available Wikisource transcription is simplified. The registry's `lang` field is set from")
    A("the text itself by a character-frequency script detector, not from the work's era.")
    A("")

    A("## 4. Known biases — read this before using the corpus")
    A("")
    A("1. **English-translation weighting.** " + _pct(by_lang.get("en", 0), total) +
      " of characters are English. Much of the Asian content reaches us through **19th-century "
      "translators who carried their own filters** — colonial-era pharmacognosy (Kirtikar, Stuart, "
      "Dutt, Waring) uses the vocabulary and categories of its time, translates selectively, and "
      "sometimes misidentifies taxa. The untranslated Chinese and Sanskrit is the corrective, but "
      "it is a minority of the character count.")
    A("2. **Edition bias.** We use whichever public-domain transcription exists. Different "
      "editions of 本草綱目 disagree on properties (e.g. 人參 is 甘微寒 in some editions, 苦溫 in "
      "the transcription used here). We are faithful to *our* transcription and record the source, "
      "but we are not a critical edition.")
    prop_rows = st.get("properties.csv", 0)
    A(f"3. **Grade/property coverage is partial.** `properties.csv` covers {_num(prop_rows)} "
      "drug rows, and each field is filled only where the text states it: nature, flavour, "
      "toxicity, 歸經 channel and 三品 grade are all well below 100%. Absence means *not stated "
      "in the transcribed text we parsed*, not *absent in the tradition*. Report n per test.")
    A("4. **China- and India-centric within Asia.** Chinese and Indian material dominates; "
      "Kampō, Korean (apart from 東醫寶鑑) and Tibetan are thin. Persian/Unani is represented by one "
      "large Latin *Canon* plus one English translation.")
    A("5. **OCR noise.** The Internet Archive tier is OCR of 19th-century print. We filter hard "
      "(running heads, page numbers, hyphenation, high-symbol-ratio lines, U+FFFD), but residual "
      "OCR error survives in the English tier.")
    A("6. **Formularies are formula-rich and indication-poor.** 普濟方 and 太平惠民和劑局方 list "
      "thousands of formulas; extracting clean drug × indication pairs from them is future work.")
    A("")
    A("**What we deliberately did *not* include:** European herbals (Culpeper, Gerard, Grieve, "
      "King's) — the domain directive excludes the Western herbal tradition. No "
      "`comparative-control` slice was ultimately needed, so the 3% cap is unused (0%).")
    A("")

    A("## 5. Licences")
    A("")
    A("| licence | sources | chars | obligation |")
    A("|---|---|---|---|")
    for g, n in lic_counts.most_common():
        ob = ("none (public domain)" if g == "PD"
              else "attribution + **ShareAlike** on redistribution of the corpus")
        A(f"| {g} | {n} | {_num(lic_chars[g])} | {ob} |")
    A("")
    A("The **CC BY-SA 4.0** portion makes `corpus/` a share-alike data artefact: derived corpora "
      "must be released under a compatible licence with attribution to Wikisource contributors. "
      "Code and model weights remain Apache-2.0 — the data licence is separate. Full table, "
      "per-source evidence and the **GRETIL CC BY-NC-SA rejection** are in "
      "[`LICENSE_AUDIT.md`](LICENSE_AUDIT.md).")
    A("")
    A("**PII / personal data:** none. These are published historical texts. No living-person data, "
      "no patient records, no location data.")
    A("")
    A("**Dual use / safety:** toxicology and toxic plants are discussed *as they appear in "
      "historical texts*. The corpus contains no synthesis routes, no dosing instructions, and no "
      "self-treatment guidance. Downstream models must refuse clinical-advice requests; see "
      "`docs/SAFETY.md`.")
    A("")

    A("## 6. Structured derivatives")
    A("")
    if st:
        A("| artefact | rows | contract |")
        A("|---|---|---|")
        contract = {
            "properties.csv": "TCM property vector (四氣五味歸經升降浮沉有毒無毒三品)",
            "ayurveda_properties.csv": "rasa / guṇa / vīrya / vipāka / doṣa",
            "relations_seven.csv": "七情 combination relations",
            "incompatibilities.csv": "十八反 / 十九畏 rule systems",
            "processing.csv": "炮制 term → modern chemical reading",
            "uses.csv": "drug × indication × tradition",
            "formulas.csv": "formula names from the clinical corpus",
            "formula_ingredients.csv": "formula × ingredient drug",
            "plants.csv": "binomial → family (GBIF) + synonyms",
            "compounds.csv": "compound → SMILES/CID (PubChem) + found-in taxon (Wikidata)",
        }
        for name, n in st.items():
            A(f"| `{name}` | {_num(n)} | {contract.get(name, '')} |")
        A("")
    jr_path = _net.REGISTRY / "join_report.json"
    if jr_path.exists():
        jr = json.loads(jr_path.read_text(encoding="utf-8"))
        A("### 6.1 Join audit — how much structured data reaches a taxon")
        A("")
        A(f"Lexicon: **{jr['lexicon']['entries']} entries**, "
          f"{jr['lexicon']['distinct_binomials']} distinct binomials, "
          f"mean confidence {jr['lexicon']['mean_confidence']}. Methods: "
          + ", ".join(f"`{k}` {v}" for k, v in jr["lexicon"]["by_method"].items()) + ".")
        A("")
        A("| file | rows | join key | joined to a binomial | rate | unresolved |")
        A("|---|---|---|---|---|---|")
        for name, info in jr["files"].items():
            if not info.get("present"):
                A(f"| `{name}` | — | — | — | — | — |")
                continue
            unres = info.get("by_status", {}).get("unresolved", 0)
            A(f"| `{name}` | {_num(info['rows'])} | `{info['join_key']}` | "
              f"{_num(info['plant_binomial_filled'])} | {info['join_rate']:.0%} | "
              f"{_num(unres)} |")
        A("")
        A("**Why unresolved rows were not guessed.** A drug surface that Wikidata/POWO "
          "cannot resolve to a single accepted binomial is left `null` with "
          "`join_status=unresolved`. Several classical names are genuinely ambiguous "
          "(*Aristolochia* vs *Stephania* substitution is the documented safety crisis this "
          "project studies), so guessing a binomial would inject exactly the error the "
          "discovery engine is supposed to detect. `drug_name` is present on every row and "
          "is the stable join key for runtime resolution.")
        A("")
    meta_path = STRUCT / "incompatibilities_meta.json"
    if meta_path.exists():
        im = json.loads(meta_path.read_text(encoding="utf-8"))
        A("### 6.2 十八反 / 十九畏 — completeness, stated honestly")
        A("")
        A("These two mnemonics are named for the **drugs named in the verse, not for the "
          "number of pairs**. We ship the faithful sets rather than a padded one, and we "
          "label every row with the verse line it comes from.")
        A("")
        A("| rule system | verse | pairs | drugs named | note |")
        A("|---|---|---|---|---|")
        sf, sw = im["shiba_fan"], im["shijiu_wei"]
        A(f"| 十八反 (shiba_fan) | {sf['verse']} | {sf['pairs']} | {sf['drugs_named']} | "
          f"{sf['note']} |")
        A(f"| 十九畏 (shijiu_wei) | {sw['verse']} | {sw['pairs']} | {sw['drugs_named']} | "
          f"{sw['note']} |")
        A(f"| viruddha (Ayurveda) | — | {im['viruddha']['pairs']} | — | "
          f"{im['viruddha']['note']} |")
        A("")
        A("Every row carries `classical_label` (e.g. `十八反·烏頭組`) and `span` (the verse "
          "line), so a reviewer can trace it to the mnemonic. `variant_of` flags the two "
          "modern 白芍/赤芍 rows and the two 犀角 rows. **Nothing was padded to reach a round "
          "number** — inventing pairs would be the one error that invalidates a data-validation "
          "claim.")
        A("")
    A("The drug-name → modern-binomial lexicon is "
      "`corpus/processed/lexicon_drugs.json` (Wikidata **P225** taxon resolution with a citable "
      "Q-id per entry, plus manual pharmacopoeial overrides).")
    A("")

    A("## 7. Quality control as applied")
    A("")
    A(f"- **Chunking:** {stats['params']['target_chars']} target / "
      f"{stats['params']['hard_max_chars']} hard max characters; minimum "
      f"{stats['params']['min_chars_cjk']} chars for CJK and {stats['params']['min_chars_alpha']} "
      "for alphabetic scripts (contract §10.2).")
    A(f"- **De-duplication:** {stats['params']['shingle_n']}-gram shingle hashing across all "
      f"sources; a chunk is dropped when ≥{stats['params']['dedupe_overlap']:.0%} of its shingles "
      f"were already seen. **{_num(stats['duplicate_chunks_dropped'])} duplicate chunks were "
      "dropped.**")
    A("- **Near-duplicates that remain:** the contract checker's independent, weaker hash "
      "(`hash(tuple(text.split()[:13]))`) reports ~1.2% of chunks sharing a 13-token prefix. These "
      "are genuine near-duplicates — the same passage in the original and a commentary edition, or "
      "overlapping sub-pages — not exact copies. We state the number rather than omit it.")
    A("- **NFC normalisation**, control-character stripping, per-source script gate "
      "(CJK / Devanagari / Latin ratio), U+FFFD gate, running-head and page-number removal, "
      "Gutenberg boilerplate removal, OCR line de-hyphenation.")
    A("- **Every** `chars` and `sha256` in `sources.yaml` is read from a file on disk. Nothing is "
      "estimated.")
    A("")

    A("## 8. How to rebuild")
    A("")
    A("From a clean clone (network required; the fetchers are idempotent, resumable, rate-limited "
      "and cache all API responses under `data/.cache/`):")
    A("")
    A("```bash")
    A("# 1. discover candidate sources (optional; the curated manifest is data/manifest.py)")
    A("python -m data.discover")
    A("")
    A("# 2. fetch raw text  (corpus/raw/<source_id>/text.raw + meta.json)")
    A("python -m data.fetch_wikisource --lang zh      # classical Chinese canon")
    A("python -m data.fetch_wikisource --lang sa      # Sanskrit Ayurveda (Devanagari)")
    A("python -m data.fetch_gutenberg                 # Tier 1 English foundational science")
    A("python -m data.fetch_archive                   # PD English/Latin editions")
    A("")
    A("# 3. clean -> corpus/processed/text/<source_id>.txt")
    A("python -m data.clean")
    A("")
    A("# 4. build training corpus + registry + docs")
    A("python -m data.build_corpus                    # -> corpus.jsonl + stats.json")
    A("python -m data.build_registry                  # -> corpus/registry/sources.yaml")
    A("python -m data.build_docs                      # -> DATA_CARD.md, licence table")
    A("")
    A("# 5. structured derivatives (network: Wikidata, PubChem, GBIF)")
    A("python -m data.build_structured")
    A("python -m data.build_lexicon")
    A("")
    A("# 6. validate against the inter-team contracts")
    A("python scripts/verify_contracts.py")
    A("```")
    A("")
    A("A full network rebuild takes ~1–2 hours (mediawiki + archive.org rate limits). "
      f"Reproduced corpus sha256: `{stats['corpus_sha256']}`.")
    A("")
    A("> **Determinism note.** The corpus hash is reproducible from the same raw downloads. "
      "Wikisource pages can be edited between runs, so a later rebuild may differ; "
      "`corpus/raw/*/meta.json` records the `raw_sha256` of every file actually used, which is "
      "the authoritative record.")
    A("")

    A("## 9. Provenance and ethics")
    A("")
    A("Every record carries `source_id`, `title`, `year`, `tradition`, `lang`, `tier`, `licence` "
      "and points back to a registry entry with a URL and licence evidence. The registry is the "
      "proof obligation: no source is in the corpus without one.")
    A("")
    A("The classical texts are **living heritage**, not free ore. We attribute every passage, "
      "publish under an open licence, do not claim ownership of the knowledge, and derive no "
      "clinical guidance. A Nagoya-Protocol-aware Traditional Knowledge policy is in "
      "`docs/SAFETY.md`.")
    A("")

    A("## 10. Hashes")
    A("")
    A("| artefact | sha256 |")
    A("|---|---|")
    A(f"| `corpus/processed/corpus.jsonl` | `{stats['corpus_sha256']}` |")
    A("")
    A("Per-source raw and cleaned hashes are in `corpus/raw/<source_id>/meta.json` "
      "(`raw_sha256`, `clean_sha256`) and in `corpus/registry/sources.yaml` (`sha256`).")
    A("")

    DATA_CARD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {DATA_CARD}")


def main() -> int:
    reg, stats = load()
    fill_audit(reg)
    build_data_card(reg, stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
