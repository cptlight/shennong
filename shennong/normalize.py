"""Orthography normalisation for SHENNONG.

The corpus spans classical Chinese (traditional and simplified), Sanskrit in IAST and
Devanagari, Arabic/Persian, and English.  Entity extraction needs two different things:

* a **length-preserving** normalisation (``normalise_offsets``) so that every match can
  be reported with ``char_start``/``char_end`` into the *original* source text, which is
  what makes a claim citable (brief §10.5 / the Lead's dossier contract);
* a **query normalisation** (``normalise``) that is allowed to expand ligatures and
  transliterate Devanagari, used for lexicons and search keys.

The length-preserving pipeline handles, character by character:

1.  Traditional → simplified Chinese folding (炮製→炮制, 黃→黄, 麥→麦 …).
2.  IAST diacritics → ASCII (ā→a, ś→s, ṣ→s, ṭ→t, ṇ→n …).
3.  Arabic letter folding (أ/إ/آ→ا, ى→ي, ة→ه) and removal of ḥarakāt/tatweel.
4.  Early-modern English: long s (ſ→s), and the u/v, i/j ambiguities are *not* folded
    because they are not needed for the Asian domain and would corrupt English tokens.

No network, no dependencies.
"""

from __future__ import annotations

import re
import unicodedata

# --------------------------------------------------------------------------------------
# Traditional → simplified Chinese folding (single character, length preserving)
# --------------------------------------------------------------------------------------

_ZH_PAIRS = """
參参 黃黄 藥药 薑姜 棗枣 烏乌 貝贝 蔞蒌 蘞蔹 蘆芦 細细 銀银 牽牵 鬱郁 稜棱 靈灵
朮术 當当 歸归 連连 梔栀 麥麦 續续 斷断 澤泽 瀉泻 廣广 葉叶 膽胆 輕轻 鉛铅 礬矾
風风 濕湿 熱热 瘡疮 癰痈 腫肿 惡恶 癬癣 嘔呕 暈晕 癲癫 癇痫 驚惊 結结 壓压 瘧疟
癥症 積积 癭瘿 補补 氣气 臟脏 虛虚 勞劳 經经 調调 腎肾 腸肠 脹胀 滿满 蟲虫 損损
傷伤 續续 斷断 龍龙 龜龟 雞鸡 鴨鸭 馬马 驢驴 鶴鹤 鱉鳖 蠍蝎 蟬蝉 蠶蚕 糞粪 鹽盐
鐵铁 銅铜 錫锡 鋅锌 鈣钙 鎂镁 鉛铅 汞汞 砒砒 雄雄 雌雌 陰阴 陽阳 衛卫 營营 脈脉
絡络 針针 灸灸 穴穴 經经 絡络 臟脏 腑腑 證证 癥症 瘕瘕 積积 聚聚 痰痰 飲饮 瘀瘀
滯滞 閉闭 竅窍 竅窍 頭头 頸颈 項项 肩肩 背背 腰腰 膝膝 踝踝 腕腕 指指 足足 腹腹
胸胸 脇胁 脇胁 脅胁 脘脘 痞痞 噦哕 噯嗳 呃呃 咳咳嗽嗽 喘喘 哮哮 痰痰 涎涎 涕涕
唾唾 嘔呕 吐吐 泄泄 瀉泻 痢痢 秘秘 痔痔 瘡疮 疹疹 斑斑 痘痘 疥疥 癬癣 癩癞 癰痈
疽疽 疔疔 瘍疡 腫肿 潰溃 斂敛 膿脓 血血 衄衄 咯咯 嘔呕 便便 尿尿 淋淋 濁浊 遺遗
精精 滑滑 帶带 經经 產产 乳乳 汁汁 月月 信信 崩崩 漏漏 癥症 癖癖 疝疝 頹颓 疝疝
痺痹 痿痿 癱瘫 瘓痪 癲癫 狂狂 癇痫 驚惊 悸悸 怔怔 忡忡 煩烦 躁躁 鬱郁 憂忧 思思
慮虑 悲悲 恐恐 驚惊 忘忘 寐寐 眠眠 臥卧 眩眩 暈晕 鳴鸣 聾聋 耳耳 鼻鼻 咽咽 喉喉
牙牙 齒齿 齦龈 舌舌 口口 唇唇 目目 眥眦 淚泪 翳翳 盲盲 視视 紅红 赤赤 青青 白白
黑黑 黃黄 紫紫 丹丹 朱朱 砂砂 石石 膏膏 散散 丸丸 湯汤 飲饮 酒酒 醋醋 蜜蜜 鹽盐
麩麸 炒炒 炮炮 煅煅 煨煨 淬淬 蒸蒸 煮煮 炙炙 焙焙 曬晒 乾干 鮮鲜 陳陈 生生 熟熟
湯汤 洗洗 浸浸 漬渍 研研 磨磨 飛飞 昇升 伏伏 製制 法法 修修 合合 配配 伍伍 君君
臣臣 佐佐 使使 反反 畏畏 殺杀 解解 毒毒 病病 證证 症症 治治 主主 療疗 除除 止止
安安 補补 瀉泻 溫温 清清 涼凉 寒寒 熱热 平平 甘甘 苦苦 辛辛 酸酸 鹹咸 澀涩 淡淡
濃浓 苦苦 甜甜 香香 臭臭 腥腥 羶膻 焦焦 生生 死死 輕輕 重重 浮浮 沉沉 升升 降降
歸归 經经 入入 出出 表表 裡里 內内 外外 上上 下下 左左右右 前前 後后 陰阴 陽阳
氣气 血血 營营 衛卫 津津 液液 神神 魂魂 魄魄 志志 意意 思思 怒怒 喜喜 思思 憂忧
悲悲 恐恐 驚惊 五五 臟脏 六六 腑腑 心心 肝肝 脾脾 肺肺 腎肾 膽胆 胃胃 小小 腸肠
膀膀胱胱 三三 焦焦 心心 包包 絡络 腦脑 髓髓 骨骨 筋筋 脈脉 肉肉 皮皮 毛毛 髮发
發发 爪爪 齒齿 舌舌 耳耳 目目 口口 鼻鼻 咽咽 喉喉 胸胸 腹腹 腰腰 背背 脊脊 臍脐
經经 絡络 俞俞 募募 原原 絡络 郄郄 合合 穴穴 井井 滎荥 輸输 經经 合合
"""
ZH_FOLD: dict[str, str] = {}
for _pair in _ZH_PAIRS.split():
    if len(_pair) == 2 and _pair[0] != _pair[1]:
        ZH_FOLD[_pair[0]] = _pair[1]

# --------------------------------------------------------------------------------------
# IAST / Sanskrit folding (single character)
# --------------------------------------------------------------------------------------

_IAST_FOLD = {
    "ā": "a", "Ā": "A", "ī": "i", "Ī": "I", "ū": "u", "Ū": "U",
    "ṛ": "r", "Ṛ": "R", "ṝ": "r", "Ṝ": "R", "ḷ": "l", "Ḷ": "L",
    "ṃ": "m", "Ṃ": "M", "ṁ": "m", "Ṁ": "M", "ḥ": "h", "Ḥ": "H",
    "ś": "s", "Ś": "S", "ṣ": "s", "Ṣ": "S",
    "ṭ": "t", "Ṭ": "T", "ḍ": "d", "Ḍ": "D", "ṇ": "n", "Ṇ": "N",
    "ñ": "n", "Ñ": "N", "ṅ": "n", "Ṅ": "N",
    "ē": "e", "ō": "o",
}

# --------------------------------------------------------------------------------------
# Arabic folding (single character)
# --------------------------------------------------------------------------------------

_ARABIC_FOLD = {
    "\u0623": "\u0627",  # أ → ا
    "\u0625": "\u0627",  # إ → ا
    "\u0622": "\u0627",  # آ → ا
    "\u0671": "\u0627",  # ٱ → ا
    "\u0649": "\u064a",  # ى → ي
    "\u0629": "\u0647",  # ة → ه
    "\u0640": None,       # tatweel removed
}

#: ḥarakāt and Quranic marks to drop.
_ARABIC_DIACRITICS = frozenset(
    chr(c) for c in range(0x064B, 0x0660)
) | {"\u0670", "\u06D6", "\u06D7", "\u06D8", "\u06D9", "\u06DA", "\u06DB", "\u06DC", "\u06DF", "\u06E0"}

#: Early-modern English long s and a few typographic ligatures.
_EN_FOLD = {
    "\u017F": "s",  # ſ
    "\u00C6": "A", "\u00E6": "a",  # æ — fold to a single char to preserve offsets
    "\u0152": "O", "\u0153": "o",
}

# Devanagari → IAST (multi-character; used only for query keys, not span offsets)
_DEVANAGARI_CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n",
    "च": "c", "छ": "ch", "ज": "j", "झ": "jh", "ञ": "n",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v",
    "श": "s", "ष": "s", "स": "s", "ह": "h",
    "ळ": "l", "क़": "q", "ख़": "kh", "ग़": "g", "ज़": "z",
    "ड़": "r", "ढ़": "rh", "फ़": "f",
}
_DEVANAGARI_VOWELS = {
    "अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u",
    "ऋ": "r", "ॠ": "r", "ऌ": "l", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
}
_DEVANAGARI_MATRAS = {
    "ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "ृ": "r", "ॄ": "r",
    "ॢ": "l", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
}
_DEVANAGARI_MARKS = {
    "\u0902": "m",  # anusvāra
    "\u0903": "h",  # visarga
    "\u0901": "m",  # candrabindu
    "\u094D": "",   # virama
    "\u093C": "",   # nukta
}


def fold_zh(text: str) -> str:
    """Traditional → simplified folding, length preserving."""
    return "".join(ZH_FOLD.get(ch, ch) for ch in text)


def fold_iast(text: str) -> str:
    """Strip IAST diacritics, length preserving."""
    return "".join(_IAST_FOLD.get(ch, ch) for ch in text)


def fold_arabic(text: str) -> str:
    out: list[str] = []
    for ch in text:
        if ch in _ARABIC_DIACRITICS:
            continue
        repl = _ARABIC_FOLD.get(ch, ch)
        if repl is None:
            continue
        out.append(repl)
    return "".join(out)


def fold_english(text: str) -> str:
    return "".join(_EN_FOLD.get(ch, ch) for ch in text)


def devanagari_to_iast(text: str) -> str:
    """Transliterate Devanagari to a lower-case IAST-like ASCII string.

    Multi-character output, so this is NOT offset-preserving; it is used for lexicon
    keys and query normalisation only.
    """
    out: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in _DEVANAGARI_CONSONANTS:
            out.append(_DEVANAGARI_CONSONANTS[ch])
            # consume a following virama (no inherent vowel)
            if i + 1 < len(text) and text[i + 1] == "\u094D":
                i += 2
                continue
            # inherent 'a' unless a matra follows
            if i + 1 < len(text) and text[i + 1] in _DEVANAGARI_MATRAS:
                out.append(_DEVANAGARI_MATRAS[text[i + 1]])
                i += 2
                continue
            out.append("a")
            i += 1
            continue
        if ch in _DEVANAGARI_VOWELS:
            out.append(_DEVANAGARI_VOWELS[ch])
        elif ch in _DEVANAGARI_MATRAS:
            out.append(_DEVANAGARI_MATRAS[ch])
        elif ch in _DEVANAGARI_MARKS:
            out.append(_DEVANAGARI_MARKS[ch])
        else:
            out.append(ch)
        i += 1
    return fold_iast("".join(out))


def normalise_offsets(text: str) -> str:
    """Length-preserving normalisation used for span-faithful entity matching.

    Guarantees ``len(result) == len(text)`` so every character offset maps 1:1 back to
    the original document.
    """
    out: list[str] = []
    for ch in text:
        if ch in ZH_FOLD:
            out.append(ZH_FOLD[ch])
        elif ch in _IAST_FOLD:
            out.append(_IAST_FOLD[ch])
        elif ch in _ARABIC_FOLD:
            repl = _ARABIC_FOLD[ch]
            out.append(repl if repl is not None else "")
        elif ch in _ARABIC_DIACRITICS:
            continue
        elif ch in _EN_FOLD:
            out.append(_EN_FOLD[ch])
        else:
            out.append(ch)
    result = "".join(out)
    # Removals (tatweel, ḥarakāt) shrink the string; re-pad is not meaningful, so the
    # contract only holds for texts without removable marks. Assert to catch misuse.
    if len(result) != len(text):  # pragma: no cover - defensive
        raise ValueError("normalise_offsets is not length preserving for this input")
    return result


def normalise(text: str) -> str:
    """Full normalisation for match keys and queries (may change length)."""
    t = unicodedata.normalize("NFKC", text)
    t = fold_zh(t)
    t = fold_iast(t)
    t = devanagari_to_iast(t) if _contains_devanagari(t) else t
    t = fold_arabic(t)
    t = fold_english(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t.casefold()


def _contains_devanagari(text: str) -> bool:
    return any("\u0900" <= ch <= "\u097F" for ch in text)


def tokenize(text: str) -> list[str]:
    """Language-agnostic tokenisation: CJK characters, Arabic words, Latin words."""
    tokens: list[str] = []
    for match in re.finditer(
        r"[\u4e00-\u9fff\u3400-\u4dbf]|[\u0600-\u06ff]+|[\u0900-\u097f]+|[A-Za-z\u00c0-\u024f0-9]+",
        text,
    ):
        tokens.append(fold_iast(fold_zh(match.group(0))).casefold())
    return tokens


def char_ngrams(text: str, n: int = 2) -> list[str]:
    """Character n-grams over normalised text; used for fuzzy name matching."""
    t = normalise(text)
    t = re.sub(r"\s+", "", t)
    if len(t) < n:
        return [t] if t else []
    return [t[i : i + n] for i in range(len(t) - n + 1)]


def jaccard(a: str, b: str, n: int = 2) -> float:
    """Character n-gram Jaccard similarity of two names (0..1)."""
    sa, sb = set(char_ngrams(a, n)), set(char_ngrams(b, n))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)
