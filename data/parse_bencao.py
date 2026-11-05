"""Parse the classical Chinese *bencao* corpus into structured property/indication data.

The cleaned Wikisource texts preserve the two structural signals we need:

* a **drug-name line** -- short, no sentence punctuation (``甘草``, ``人參``);
* **field markers** -- ``【釋名】`` ``【氣味】`` ``【主治】`` ``【修治】`` ``【發明】`` ``【附方】``.

This module turns those into ``Entry`` objects and provides extraction of the Asian
pharmacological property vector (四氣五味, 有毒無毒, 三品, 歸經) plus indications.

Nothing here infers. If a field is absent in the text, the field is ``None``/empty and the
row still records the source span, so downstream code can measure coverage honestly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# vocabulary
# ---------------------------------------------------------------------------
NATURES = ["大寒", "大熱", "微寒", "微溫", "寒", "熱", "溫", "涼", "平"]
FLAVORS = ["辛", "甘", "酸", "苦", "鹹", "咸", "淡", "澀", "麻"]
TOXICITY = ["大毒", "小毒", "有毒", "無毒"]
CHANNEL_CORE = ["心包", "心", "肝", "脾", "肺", "腎", "胃", "膽", "大腸", "小腸",
                "膀胱", "三焦"]
GRADES = ["上品", "中品", "下品"]

# a standalone name that is really a *plant part* of the parent entry (本草綱目 lists
# 肉/殼/核/葉/花 … as sub-headings). These must not become drugs of their own.
PART_NAMES = {
    "肉", "殼", "核", "葉", "花", "子", "皮", "汁", "骨", "角", "毛", "頭", "尾", "足",
    "鱗", "甲", "膽", "肝", "心", "肺", "腎", "腸", "胃", "胎", "血", "腦", "髓", "脂",
    "油", "膏", "霜", "粉", "末", "灰", "炭", "苗", "莖", "根", "枝", "木", "節", "鬚",
    "蒂", "仁", "瓤", "膜", "筋", "爪", "翅", "卵", "蛻", "蛹", "糞", "溺", "乳", "淚",
    "汗", "津", "唾", "精", "經", "液", "巢", "窩", "殼", "葉", "莖", "花", "實",
    "本", "末", "屑", "刺", "茸", "膠", "酥", "砂", "石", "水", "汁", "瓤",
}

_NATURE_RE = re.compile("|".join(sorted(NATURES, key=len, reverse=True)))
_FLAVOR_RE = re.compile("|".join(FLAVORS))
_TOX_RE = re.compile("|".join(sorted(TOXICITY, key=len, reverse=True)))
_GRADE_RE = re.compile(r"(《本經》|本經)?\s*(上品|中品|下品)")
# 歸經 patterns: 入足厥陰肝經 / 歸肝經 / 入肝、脾二經 / 歸心、肺
_CH_RE = re.compile(
    r"(?:歸|归|入)(?:足|手)?(?:太陰|少陰|厥陰|太陽|少陽|陽明|太阴|少阴|厥阴|太阳|少阳|阳明)?"
    r"((?:(?:心包|大腸|小腸|膀胱|三焦|心|肝|脾|肺|腎|胃|膽|大肠|小肠|肾|胆)[、，]?)+)"
    r"(?:經|经|二經|二经|三經|三经|四經|四经)")
_FIELD_RE = re.compile(r"^【([^】]{1,8})】")
# Some 本草綱目 sections print the field name bare on its own line ("氣味") instead of
# using the 【…】 bracket style; both must be recognised.
BARE_FIELDS = {
    "釋名", "集解", "氣味", "主治", "發明", "附方", "修治", "正誤", "校正",
    "性味", "歸經", "功效", "應用", "用法", "用量", "禁忌", "別名", "附錄",
}

# drug-name lines that are actually section headings, not drugs
_SKIP_NAMES = {
    "序", "序例", "凡例", "目錄", "附錄", "主治", "釋名", "氣味", "發明", "附方",
    "修治", "正誤", "集解", "校正", "上卷", "中卷", "下卷", "上經", "中經", "下經",
    "草部", "木部", "石部", "蟲部", "獸部", "禽部", "果部", "菜部", "穀部", "人部",
    "水部", "火部", "土部", "金石部", "服器部", "介部", "鱗部", "獸部", "味部",
    "本經", "別錄", "綱目", "拾遺", "來源", "性味", "歸經", "功效", "用法", "用量",
    "禁忌", "附方", "別名", "英文名", "藥理", "應用", "成分", "炮製", "貯藏",
}
_PUNCT = re.compile(r"[。！？；：，、,.!?;:\s〔〕\[\]（）()《》〈〉·]")


@dataclass
class Entry:
    name: str
    block: list[str] = field(default_factory=list)
    fields: dict[str, str] = field(default_factory=dict)
    grade: str | None = None

    @property
    def text(self) -> str:
        return "\n".join(self.block)


def _is_name(line: str) -> bool:
    if not line or len(line) > 14:
        return False
    if line in _SKIP_NAMES or line in PART_NAMES:
        return False
    if len(line) < 2:
        return False
    if _FIELD_RE.match(line):
        return False
    if line.startswith(("（", "(", "《", "〈")):
        return False
    if _PUNCT.search(line):
        return False
    # a bare number/quantity line is not a name
    if re.fullmatch(r"[一二三四五六七八九十百千\d]+[兩銖枚升片錢分斤條莖寸具粒]+", line):
        return False
    # a plant-part + field merged into one line ("根修治", "莖氣味") is a heading artifact
    for f in BARE_FIELDS:
        if line != f and line.endswith(f):
            return False
    return True


def iter_entries(text: str, min_block: int = 1) -> list[Entry]:
    """Split a bencao text into drug entries by name-line boundaries."""
    lines = text.split("\n")
    entries: list[Entry] = []
    cur: Entry | None = None
    pending_grade: str | None = None

    def flush():
        nonlocal cur
        if cur is not None:
            _extract_fields(cur)
            if len(cur.block) >= min_block:
                entries.append(cur)
            cur = None

    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        if _is_name(s):
            flush()
            cur = Entry(name=s)
            if pending_grade:
                cur.grade = pending_grade
                pending_grade = None
            continue
        # a parenthetical like （《本經》上品） attaches grade to the *current* entry
        g = _GRADE_RE.search(s)
        if g and cur is not None and len(s) <= 24 and s.startswith(("（", "(")):
            cur.grade = g.group(2)
            continue
        if cur is not None:
            cur.block.append(s)
    flush()
    return entries


def _extract_fields(e: Entry) -> None:
    """Attach 【field】 contents (may span several paragraphs)."""
    cur_field = None
    buf: list[str] = []

    def commit():
        nonlocal buf, cur_field
        if cur_field and buf:
            e.fields[cur_field] = "\n".join(buf).strip()
        buf = []

    for line in e.block:
        m = _FIELD_RE.match(line)
        if m:
            commit()
            cur_field = m.group(1)
            rest = line[m.end():].strip()
            buf = [rest] if rest else []
        elif line in BARE_FIELDS:
            commit()
            cur_field = line
            buf = []
        elif any(line.endswith(f) and len(line) <= len(f) + 4 for f in BARE_FIELDS):
            # "根修治" -> the part prefix is a sub-heading, the suffix is the field
            commit()
            cur_field = next(f for f in BARE_FIELDS
                             if line.endswith(f) and len(line) <= len(f) + 4)
            buf = []
        elif cur_field:
            buf.append(line)
    commit()


# ---------------------------------------------------------------------------
# property extraction
# ---------------------------------------------------------------------------
def parse_nature_flavor(text: str) -> dict:
    """Extract 四氣五味 / toxicity from a 氣味 (or 性味) field."""
    out = {"nature": None, "flavors": [], "toxicity": None}
    if not text:
        return out
    # only inspect the first clause run -- later clauses are commentary
    head = re.split(r"[。\n]", text)[0][:60]
    m = _NATURE_RE.search(head)
    if m:
        n = m.group(0)
        out["nature"] = {"大寒": "寒", "大熱": "熱", "微寒": "寒", "微溫": "溫"}.get(n, n)
    # flavours before the nature token are the canonical ones
    prefix = head[:m.start()] if m else head
    seen: list[str] = []
    for fm in _FLAVOR_RE.finditer(prefix):
        f = fm.group(0)
        f = "鹹" if f == "咸" else f
        if f not in seen:
            seen.append(f)
    out["flavors"] = seen
    t = _TOX_RE.search(head)
    if t:
        out["toxicity"] = t.group(0)
    return out


def parse_channels(text: str) -> list[str]:
    """Extract 歸經 channels from prose."""
    if not text:
        return []
    found: list[str] = []
    _NORM = {"大肠": "大腸", "小肠": "小腸", "肾": "腎", "胆": "膽"}
    for m in _CH_RE.finditer(text):
        for c in re.findall(r"心包|大腸|小腸|膀胱|三焦|心|肝|脾|肺|腎|胃|膽|大肠|小肠|肾|胆",
                            m.group(1)):
            c = _NORM.get(c, c)
            if c not in found:
                found.append(c)
    return found


_DIRECTION_RE = re.compile(r"([升降浮沉])(?:而|，|、)?([升降浮沉])")


def parse_direction(text: str) -> list[str]:
    """Only explicit two-character directional compounds (升浮 / 沉降 / 升而降 …)."""
    if not text:
        return []
    out: list[str] = []
    for m in _DIRECTION_RE.finditer(text):
        for d in m.groups():
            if d not in out:
                out.append(d)
    return out


def split_indications(text: str, limit: int = 40) -> list[str]:
    """Split a 主治 field into short indication phrases."""
    if not text:
        return []
    text = re.sub(r"（[^）]{0,80}）", "", text)      # drop commentary parentheses
    text = re.sub(r"\([^)]{0,80}\)", "", text)
    text = re.sub(r"《[^》]{0,30}》", "", text)
    parts = re.split(r"[。；;，,、\n]", text)
    out = []
    for p in parts:
        p = p.strip(" 　·・")
        if 2 <= len(p) <= 24 and not p.isdigit():
            out.append(p)
        if len(out) >= limit:
            break
    return out


def parse_grade_from_text(text: str) -> str | None:
    m = re.search(r"(上品|中品|下品)", text)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# 神農本草經 — inline entries "丹砂 味甘微寒。…" grouped by 部/品
# ---------------------------------------------------------------------------
_SHENNONG_SECTION = re.compile(
    r"(玉石部|草部|木部|人部|獸部|禽部|蟲魚部|果部|米穀部|菜部)\s*(上品|中品|下品)")
_SHENNONG_ENTRY = re.compile(r"([\u4e00-\u9fff]{1,8})\s+味([^。]{1,20})。")


def parse_shennong(text: str, vocab: set[str]) -> dict[str, dict]:
    """Extract (name -> {grade, nature, flavors, toxicity}) from 神農本草經.

    The transcription runs entries together inside one paragraph, so the drug name is
    recovered by longest-suffix match against a vocabulary of known drug names rather than
    by blind regex (which would swallow the previous sentence's tail).
    """
    sections = [(m.start(), m.group(2)) for m in _SHENNONG_SECTION.finditer(text)]
    out: dict[str, dict] = {}
    for m in _SHENNONG_ENTRY.finditer(text):
        raw_name = m.group(1)
        props = m.group(2)
        name = None
        for cut in range(len(raw_name), 0, -1):
            cand = raw_name[len(raw_name) - cut:]
            if cand in vocab and len(cand) >= 2:
                name = cand
                break
        if not name:
            continue
        grade = None
        for pos, g in sections:
            if pos < m.start():
                grade = g
            else:
                break
        nf = parse_nature_flavor("味" + props)
        out.setdefault(name, {"grade": grade, **nf})
    return out
