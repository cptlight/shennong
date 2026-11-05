"""Turn a raw download into clean training text.

One function per source family, because the artefacts are genuinely different:

* ``gutenberg`` -- plain prose with a licence header/footer block to strip.
* ``archive``   -- OCR'd book scans: page numbers, running heads, hyphenated line breaks,
  "Digitized by Google" stamps and other librarial noise.
* ``wikisource``-- MediaWiki plaintext extracts: structural ``<篇名>`` markers, hard-wrapped
  CJK lines that must be re-joined (CJK has no inter-word spaces), occasional U+FFFD.

Historical orthography is *kept*: traditional characters, 19th-century English spellings and
Vedic transliteration are signal, not noise. We only remove noise that is clearly mechanical.

    python -m data.clean            # clean every fetched source
    python -m data.clean --report   # print a per-source quality report
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

from . import _net

PROCESSED_TEXT = _net.PROCESSED / "text"

# --------------------------------------------------------------------------
# character-class detectors
# --------------------------------------------------------------------------
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_DEV = re.compile(r"[\u0900-\u097f]")
_ALPHA = re.compile(r"[A-Za-z\u00c0-\u024f]")
_CTRL = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]")
_FFFD = "\ufffd"
_MULTISPACE = re.compile(r"[ \t\u00a0\u3000]{2,}")
_MANY_NL = re.compile(r"\n{3,}")


def ratio(pat: re.Pattern, text: str) -> float:
    if not text:
        return 0.0
    return len(pat.findall(text)) / max(1, len(text))


def cjk_ratio(t: str) -> float:
    return ratio(_CJK, t)


def devanagari_ratio(t: str) -> float:
    return ratio(_DEV, t)


def alpha_ratio(t: str) -> float:
    return ratio(_ALPHA, t)


def replacement_ratio(t: str) -> float:
    if not t:
        return 0.0
    return t.count(_FFFD) / len(t)


# --------------------------------------------------------------------------
# Gutenberg
# --------------------------------------------------------------------------
_PG_START = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
                       re.I | re.S)
_PG_END = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I | re.S)


def strip_gutenberg(text: str) -> str:
    m = _PG_START.search(text)
    if m:
        text = text[m.end():]
    m = _PG_END.search(text)
    if m:
        text = text[:m.start()]
    return text


# --------------------------------------------------------------------------
# Internet Archive OCR
# --------------------------------------------------------------------------
# lines that are pure pagination / librarial noise
_IA_NOISE = re.compile(
    r"^\s*(?:"
    r"digiti[sz]ed by (?:google|microsoft|the internet archive)"
    r"|generated (?:on|by) .{0,60}"
    r"|original from .{0,60}"
    r"|harvard university|university of .{0,40}librar.{0,10}"
    r"|downloaded from .{0,80}"
    r"|[ivxlcdm]{1,7}\s*"          # roman page numbers
    r"|\d{1,4}\s*"                 # arabic page numbers
    r"|page \d+.*"
    r"|chapter [ivxlcdm]+.*"       # running heads
    r")\s*$",
    re.I,
)
_HYPHEN_BREAK = re.compile(r"(\w)[-\u2010\u2011]\n(\w)")


def _dedupe_running_heads(lines: list[str], min_repeat: int = 12, max_len: int = 70) -> list[str]:
    """Drop short lines that recur suspiciously often (book title / chapter running heads)."""
    from collections import Counter

    norm = [re.sub(r"\s+", " ", ln).strip().lower() for ln in lines]
    counts = Counter(ln for ln in norm if 3 <= len(ln) <= max_len)
    head = {ln for ln, c in counts.items() if c >= min_repeat}
    if not head:
        return lines
    out = []
    for ln, key in zip(lines, norm):
        # never delete a line that looks like real prose (lots of lowercase words)
        if key in head and len(key.split()) <= 8:
            continue
        out.append(ln)
    return out


def clean_archive(text: str, lang: str = "en") -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n")
    # de-hyphenate words broken across a line (English/Latin only)
    if lang in ("en", "la", "sa-Latn"):
        text = _HYPHEN_BREAK.sub(r"\1\2", text)
    lines = text.split("\n")
    kept = []
    for ln in lines:
        s = ln.strip()
        if not s:
            kept.append("")
            continue
        if _IA_NOISE.match(s):
            continue
        # OCR garbage: too few alphanumerics relative to symbols
        alnum = sum(c.isalnum() for c in s)
        if len(s) > 12 and alnum / len(s) < 0.45:
            continue
        if replacement_ratio(s) > 0.02:
            continue
        kept.append(s)
    kept = _dedupe_running_heads(kept)
    return "\n".join(kept)


# --------------------------------------------------------------------------
# Wikisource
# --------------------------------------------------------------------------
_WS_TAG_LINE = re.compile(r"^\s*<(目录|篇名|内容|正文|标题|书名|作者|朝代|年份)>\s*$")
_WS_TAG_INLINE = re.compile(r"<(篇名|目录|内容)>")
_WS_CONTENT_PREFIX = re.compile(r"^内容[：:]\s*")


def clean_wikisource(text: str, lang: str = "zh-Hant") -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n")
    text = _WS_TAG_INLINE.sub("", text)
    out_lines: list[str] = []
    for ln in text.split("\n"):
        s = ln.strip()
        if _WS_TAG_LINE.match(s):
            continue
        s = _WS_CONTENT_PREFIX.sub("", s)
        out_lines.append(s)
    if lang.startswith("zh"):
        return _reflow_cjk(out_lines)
    # Devanagari: verses are meaningful lines; just collapse runs of blanks
    return _MANY_NL.sub("\n\n", "\n".join(out_lines)).strip()


_CJK_PUNCT_END = "。！？；：」』）】…"
_FIELD_MARK = re.compile(r"^【[^】]{1,8}】")
# A line that is a drug/entry name: short, and carries no sentence punctuation at all.
_CJK_NAME_MAX = 18


def _is_cjk_heading(s: str) -> bool:
    """True for a classical entry-name line ("甘草") or a field marker ("【氣味】…")."""
    if _FIELD_MARK.match(s):
        return True
    if len(s) > _CJK_NAME_MAX:
        return False
    if re.search(r"[。！？；：，、]", s):
        return False
    return True


def _reflow_cjk(lines: list[str]) -> str:
    """Re-join hard-wrapped CJK prose while preserving entry structure.

    CJK text has no inter-word spaces, so a newline in the middle of a sentence is an
    artefact of the source transcription, not a boundary. But 本草 "entries" *are* delimited
    by a standalone drug-name line followed by 【釋名】【氣味】【主治】 field markers, and that
    structure is exactly what the property parser needs. So: re-join prose lines, keep
    heading and field lines as their own paragraphs.
    """
    paras: list[str] = []
    buf: list[str] = []

    def flush():
        if buf:
            paras.append("".join(buf))
            buf.clear()

    for ln in lines:
        if not ln:
            flush()
            continue
        if _is_cjk_heading(ln):
            flush()
            paras.append(ln)
            continue
        buf.append(ln)
    flush()
    return "\n\n".join(p for p in paras if p.strip()).strip()


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------
def clean_text(raw: str, kind: str, lang: str) -> str:
    if kind == "gutenberg":
        raw = strip_gutenberg(raw)
        txt = clean_archive(raw, lang="en")  # same OCR-noise rules are harmless for PG
        txt = unicodedata.normalize("NFC", txt)
    elif kind == "archive":
        txt = clean_archive(raw, lang=lang)
        txt = unicodedata.normalize("NFC", txt)
    elif kind == "wikisource":
        txt = clean_wikisource(raw, lang=lang)
        txt = unicodedata.normalize("NFC", txt)
    else:
        raise ValueError(f"unknown source kind {kind!r}")
    txt = _CTRL.sub("", txt)
    txt = _MULTISPACE.sub(" ", txt)
    # normalise the whitespace-only edges of every line but keep structure
    lines = [ln.rstrip() for ln in txt.split("\n")]
    txt = "\n".join(lines)
    txt = _MANY_NL.sub("\n\n", txt)
    return txt.strip()


# highly discriminative simplified-only characters and their traditional counterparts
_SIMP = set("气药归经肾胆肠见医学体发为这个来时说会后点头长门问间关开无与从众优传伤养净减动劳势单卫变叶号听员响图坏坚处复备宁宝实审对导尔岁岗币师当录彻忆应废弃弥张弹强务农刘剧劝区华协单卖卫却厂厅历压厌县参双发变叙叠只台叶号叹叼吗吧听呜吴员呛呜响哑唤啧喷嗳嘘嘱噜团园围图圆圣场坏坟垄垒垦垫埘墙壮声壳壶处备复够头夹夺奁妆娄婴媪娱孪宁宝实宠审宪宫宽宾寝对寻导寿将尔尘尝尧尸尽层屉届属岁岂岗岚岛岭峡币帅师帐帘帜带帮广庆库应庙废开异弃张弹归当录彻径忆忧怀态怜总恋恳恶恼悦惊惧惨惩愿懒战户扑执扩扫扬扰抚抛抢护报担拟拢挂挟挠挡挣挤挥捞损换据掳掷揽搀搁搂搅携摊撑攒敌敛数斋斗斩断无旧时旷昙显晒晓晕暂术机杀杂权条来杨极构枢枣枪枫柜柠标栋栏树样档桥桦档检梦梼棂椁椭楼榄榈榉槛横樯橹橼欢欧歼殁殇残殒殓殚殡毁毂毕毙毡气氢氧氨汉汤沟没沣沥沦沧沪泞注泪泶泼泽洁洒洗浃浇浊测济浑浓浔涂涌涡涣涤润涧涨涩淀渊渍渎渐渑温湾湿溃溅溆滗滚滞満滤滥滨滩满漤潆潇潋潍潜潴澜濑濒灏灭灯灵灾灿炉炖炜点炼烂烛烟烦烧烩烫热焕焖焘煅煳熘燃灺爱爷牍牦牵犊状犹狈狞独狭狮狱猎猕猪猫猬献猴猸猾獬玑玛玮环现玱玺珐珑琏琐琼瑶璎瓒瓯电画畅疗疟疡疬疬疮疯疱疴症痈痉痒痖痨痪痫瘅瘗瘘瘪瘫瘾癞癣皑皱皲盏盐监盖盘眍眦眵眼睁睐睑瞒瞩矫矿码砖砗砚砜砺砻础硅硕确硷碍碛碜碱碹碾磐磙磔祢祷祸禀禄禅离秃秆种积称秽稳穑穗穷窃窍窑窜窝窥窦竖竞笋笔笕笺笼笾筑筚筛筜筝筹签简箓箦箧箨箩箪箫篑篓篮篱簖籁籴类籼粜粝粞粮粲粪粝紧絷纠纡红纣纤纥约级纨纩纪纫纬纭纮纯纰纱纲纳纴纵纶纷纸纹纺纻纼纽纾线绀绁绂练组绅细织终绉绊绋绌绍绎经绐绑绒结绔绕绖绗绘给绚绛络绝绞统绠绡绢绣绤绥绦继绨绩绪绫绬续绮绯绰绱绲绳维绵绶绷绸绹绺绻综绽绾绿缀缁缂缃缄缅缆缇缈缉缊缋缌缍缎缏缐缑缒缓缔缕编缗缘缙缚缛缜缝缞缟缠缡缢缣缤缥缦缧缨缩缪缫缬缭缮缯缰缱缲缳缴缵罂网罗罚罢罴羁羟羡翘耢耧耸耻聂聋职聍联聩聪肃肠肤肷肾肿胀胁胆胜胧胨胪胫胶脉脍脏脐脑脓脔脚脱脶脸腊腌腘腭腻腼腽腾膑臜舆舣舰舱舻艰艳艹艺节芈芗芜芦苁苇苈苋苌苍苎苏苘苹茎茏茑茔茕茧荆荐荙荚荛荜荞荟荠荡荣荤荥荦荧荨荩荪荫荬荭荮药莅莱莲莳莴莶获莸莹莺莼萚萝萤营萦萧萨葱蒇蒉蒋蒌蓝蓟蓠蓣蓥蓦蔷蔹蔺蔼蕲蕴薮藁藓虏虑虚虫虬虮虽虾虿蚀蚁蚂蚕蚝蚬蛊蛎蛏蛮蛰蛱蛲蛳蛴蜕蜗蜡蝇蝈蝉蝎蝼蝽螀螨蟏衅衔补衬衮袄袅袆袜袭袯装裆裈裢裣裤裥褛褴襁襕见观觃规觅视觇览觉觊觋觌觍觎觏觐觑角觞触觯詟誉誊讠计订讣认讥讦讧讨让讪讫训议讯记讱讲讳讴讵讶讷许讹论讻讼讽设访诀证诂诃评诅识诇诈诉诊诋诌词诎诏诐译诒诓诔试诖诗诘诙诚诛诜话诞诟诠诡询诣诤该详诧诨诩诪诫诬语诮误诰诱诲诳说诵诶请诸诹诺读诼诽课诿谀谁谂调谄谅谆谇谈谊谋谌谍谎谏谐谑谒谓谔谕谖谗谘谙谚谛谜谝谞谟谠谡谢谣谤谥谦谧谨谩谪谫谬谭谮谯谰谱谲谳谴谵谶谷豮贝贞负贠贡财责贤败账货质贩贪贫贬购贮贯贰贱贲贳贴贵贶贷贸费贺贻贼贽贾贿赀赁赂赃资赅赆赇赈赉赊赋赌赍赎赏赐赑赒赓赔赕赖赗赘赙赚赛赜赝赞赟赠赡赢赣赪赵赶趋趱趸跃跄跖跞践跶跷跸跹跻踊踌踪踬踯蹑蹒蹰蹿躁躏躜躯车轧轨轩轪轫转轭轮软轰轱轲轳轴轵轶轸轹轺轻轼载轾轿辀辁辂较辄辅辆辇辈辉辊辋辌辍辎辏辐辑辒输辔辕辖辗辘辙辚辞辩辫边辽达迁过迈运还这进远违连迟迩迳迹适选逊递逦逻遗遥邓邝邬邮邹邺邻郁郄郏郐郑郓郦郧郸酂酝酦酱酽酾酿释里鉴銮錾钅钆钇针钉钊钋钌钍钎钏钐钑钒钓钔钕钖钗钘钙钚钛钜钝钞钟钠钡钢钣钤钥钦钧钨钩钪钫钬钭钮钯钰钱钲钳钴钵钶钷钸钹钺钻钼钽钾钿铀铁铂铃铄铅铆铈铉铊铋铌铍铎铏铐铑铒铕铖铗铙铚铛铜铝铞铟铠铡铢铣铤铥铧铨铩铪铫铬铭铮铯铰铱铲铳铴铵银铷铸铹铺铻铼铽链铿销锁锂锃锄锅锆锇锈锉锊锋锌锍锎锏锐锑锒锓锔锕锖锗锘错锚锛锜锝锞锟锠锡锢锣锤锥锦锧锨锩锪锫锬锭键锯锰锱锲锳锴锵锶锷锸锹锺锻锼锽锾锿镀镁镂镃镄镅镆镇镈镉镊镋镌镍镎镏镐镑镒镓镔镕镖镗镘镙镚镛镜镝镞镟镠镡镢镣镤镥镦镧镨镩镪镫镬镭镮镯镰镱镲镳镴镶长门闩闪闫闭问闯闰闱闲闳间闵闶闷闸闹闺闻闼闽闾闿阀阁阂阃阄阅阆阇阈阉阊阋阌阍阎阏阐阑阒阓阔阕阖阗阘阙阚阛队阳阴阵阶际陆陇陈陉陕陧陨险随隐隶隽难雏雠雳雾霁霉霭靓静靥鞑鞒鞯鞴韦韧韨韩韪韫韬韵页顶顷顸项顺须顼顽顾顿颀颁颂颃预颅领颇颈颉颊颋颌颍颏颐频颒颓颔颕颖颗题颙颚颛颜额颞颟颠颡颢颣颤颥颦颧风飏飐飑飒飓飔飕飖飗飘飙飚飞飨餍饤饥饦饧饨饩饪饫饬饭饮饯饰饱饲饳饴饵饶饷饸饹饺饻饼饽饾饿馀馁馂馃馄馅馆馇馈馉馊馋馌馍馎馏馐馑馒馓馔馕马驭驮驯驰驱驲驳驴驵驶驷驸驹驺驻驼驽驾驿骀骁骂骃骄骅骆骇骈骉骊骋验骍骎骏骐骑骒骓骔骕骖骗骘骙骚骛骜骝骞骟骠骡骢骣骤骥骦骧髅髋髌鬓魇魉鱼鱽鱾鱿鲀鲁鲂鲃鲄鲅鲆鲇鲈鲉鲊鲋鲌鲍鲎鲏鲐鲑鲒鲓鲔鲕鲖鲗鲘鲙鲚鲛鲜鲝鲞鲟鲠鲡鲢鲣鲤鲥鲦鲧鲨鲩鲪鲫鲬鲭鲮鲯鲰鲱鲲鲳鲴鲵鲶鲷鲸鲹鲺鲻鲼鲽鲾鲿鳀鳁鳂鳃鳄鳅鳆鳇鳈鳉鳊鳋鳌鳍鳎鳏鳐鳑鳒鳓鳔鳕鳖鳗鳘鳙鳛鳜鳝鳞鳟鳠鳡鳢鳣鸟鸠鸡鸢鸣鸥鸦鸨鸩鸪鸫鸬鸭鸮鸯鸰鸱鸲鸳鸴鸵鸶鸷鸸鸹鸺鸻鸼鸽鸾鸿鹀鹁鹂鹃鹄鹅鹆鹇鹈鹉鹊鹋鹌鹍鹎鹏鹐鹑鹒鹓鹔鹕鹖鹗鹘鹚鹛鹜鹝鹞鹟鹠鹡鹢鹣鹤鹥鹦鹧鹨鹩鹪鹫鹬鹭鹯鹰鹱鹲鹳鹴鹾麦麸黄黉黡黩黪黾鼋鼍鼗鼹齄齐齑齿龀龁龂龃龄龅龆龇龈龉龊龋龌龙龚龛龟")
_TRAD = set("氣藥歸經腎膽腸見醫學體發為這個來時說會後點頭長門問間關開無與從眾優傳傷養淨減動勞勢單衛變葉號聽員響圖壞堅處復備寧寶實審對導爾歲崗幣師當錄徹憶應廢棄彌張彈強務農劉劇勸區華協單賣衛卻廠廳歷壓厭縣參雙發變敘疊隻台葉號嘆叼嗎吧聽嗚吳員嗆嗚響啞喚嘖噴噯噓囑嚕團園圍圖圓聖場壞墳壟壘墾墊埘牆壯聲殼壺處備復夠頭夾奪奩妝婁嬰媼娛孿寧寶實寵審憲宮寬賓寢對尋導壽將爾塵嘗堯屍盡層屜屆屬歲豈崗嵐島嶺峽幣帥師帳簾幟帶幫廣慶庫應廟廢開異棄張彈歸當錄徹徑憶憂懷態憐總戀懇惡惱悅驚懼慘懲願懶戰戶撲執擴掃揚擾撫拋搶護報擔擬攏掛挾撓擋掙擠揮撈損換據擄擲攬攙擱摟攪攜攤撐攢敵斂數齋鬥斬斷無舊時曠曇顯曬曉暈暫術機殺雜權條來楊極構樞棗槍楓櫃檸標棟欄樹樣檔橋樺檔檢夢檮欞槨橢樓欖櫚櫸檻橫檣櫓櫞歡歐殲歿殤殘殞殮殫殯毀轂畢斃氈氣氫氧氨漢湯溝沒灃瀝淪滄滬濘註淚澩潑澤潔灑洗浹澆濁測濟渾濃潯塗湧渦渙滌潤澗漲澀澱淵漬瀆漸澠溫灣濕潰濺漵滗滾滯満濾濫濱灘滿漤瀠瀟瀲濰潛瀦瀾瀨瀕灝滅燈靈災燦爐燉煒點煉爛燭煙煩燒燴燙熱煥燜燾煅煳熘燃灺愛爺牘犛牽犢狀猶狽獰獨狹獅獄獵獼豬貓蝟獻猴猸猾獬璣瑪瑋環現璵璽琺瓏璉瑣瓊瑤瓔瓚甌電畫暢療瘧瘍癧癧瘡瘋皰痾症癰痙癢瘂癆瘓癇癉瘞瘻癟癱癮癩癬皚皺皸盞鹽監蓋盤眍眥眵眼睜睞瞼瞞矚矯礦碼磚硨硯碸礪礱礎矽碩確鹼礙磧磣鹼碹碾磐磙磔禰禱禍稟祿禪離禿稈種積稱穢穩穡穗窮竊竅窯竄窩窺竇豎競筍筆筧箋籠籩築篳篩簹箏籌簽簡籙簀篋籜籮簞簫簣簍籃籬簖籟籴類秈糶糲粞糧粲糞糲緊縶糾紆紅紂纖紇約級紈纊紀紉緯紜紘純紕紗綱納紝縱綸紛紙紋紡紵紖紐紓線紺紲紱練組紳細織終縐絆紼絀紹繹經紿綁絨結絝繞絰絎繪給絢絳絡絕絞統綆綃絹繡綌綏絛繼綈績緒綾緓續綺緋綽綽緄繩維綿綬繃綢綯綹綣綜綻綰綠綴緇緙緗緘緬纜緹緲緝縕繢緦綞緞緶緱縋緩締縷編緡緣縉縛縟縝縫縗縞纏縭縊縑繽縹縵縲纓縮繆縹纈繚繕繒韁繾繰繯繳纘罌網羅罰罷羆羈羥羨翹耮耬聳恥聶聾職聹聯聵聰肅腸膚膁腎腫脹脅膽勝朧腖臚脛膠脈膾臟臍腦膿臠腳脫腡臉臘醃膕腭膩靦膃騰臏臢輿艤艦艙艫艱艷艹藝節羋薌蕪蘆蓯葦藶莧萇蒼苧蘇檾蘋莖蘢蔦塋煢繭荊薦薘莢蕘蓽蕎薈薺蕩榮葷滎犖熒蕁藎蓀蔭蕒葒葤藥蒞萊蓮蒔萵薟獲蕕瑩鶯蓴蘀蘿螢營縈蕭薩蔥蕆蕢蔣蔞藍薊蘺蕷鎣驀薔蘞藺藹蘄蘊藪槁蘚虜慮虛蟲虯蟣雖蝦蠆蝕蟻螞蠶蠔蜆蠱蠣蟶蠻蟄蛺蟯螄蠐蛻蝸蠟蠅蟈蟬蠍螻蝽螿蟎蠨釁銜補襯袞襖裊褘襪襲襏裝襠褌褢襝褲襇褸襤繈襴見觀覎規覓視覘覽覺覬覡覿覥覦覯覲覷角觴觸觶讋譽謄訁計訂訃認譏訐訌討讓訕訖訓議訊記訒講諱謳詎訝訥許訛論訩訟諷設訪訣證詁訶評詛識詗詐訴診詆謅詞詘詔詖譯詒誆誄試詿詩詰詼誠誅詵話誕詬詮詭詢詣諍該詳詫諢詡譸誡誣語誚誤誥誘誨誑說誦誒請諸諏諾讀諑誹課諉諛誰諗調諂諒諄誶談誼謀諶諜謊諫諧謔謁謂諤諭諼讒諮諳諺諦謎諞諝謨讜謖謝謠謗謚謙謐謹謾謫譾謬譚譖譙讕譜譎讞譴譫讖穀豶貝貞負贠貢財責賢敗賬貨質販貪貧貶購貯貫貳賤賁貰貼貴貺貸貿費賀貽賊贄賈賄貲賃賂贓資賅贐賕賑賚賒賦賭齎贖賞賜贔賙賡賠賕賴賗贅賻賺賽賾贗贊贇贈贍贏贛赬趙趕趨趲趸躍蹌蹠躒踐躂蹺蹕躚躋踴躊蹤躓躑躡蹣蹰躥躁躪躦軀車軋軌軒轪軔轉軛輪軟轟軲軻轤軸軹軼軫轢軺輕軾載輊轎輈輁輅較輒輔輛輦輩輝輥輞輬輟輜輳輻輯轀輸轡轅轄輾轆轍轔辭辯辮邊遼達遷過邁運還這進遠違連遲邇逕跡適選遜遞邐邏遺遙鄧鄺鄔郵鄒鄴鄰鬱郤郟鄶鄭鄆酈鄖鄲酇醞醱醬釅釃釀釋里鑒鏨钅钆釔針釘釗釙釕釷釺釧釤釴釩釣鍆釹鍚釵鈃鈣鈈鈦鉅鈍鈔鍾鈉鋇鋼鈑鈐鑰欽鈞鎢鉤鈧鈁鈥鈄鈕鈀鈺錢鉦鉗鈷缽鈳鉕鈽鈸鉞鑽鉬鉭鉀鈿鈾鐵鉑鈴鑠鉛鉚鈰鉉鉈鉍鈮鈹鐸鉶銬銠鉺銪鋮鋏鐃銍鐺銅鋁銱銦鎧鍘銖銑鋌銩銚銓銩鉿銚鉻銘錚銫鉸銥鏟銃鐋銨銀銣鑄鐒鋪鋙錸鋱鏈鏗銷鎖鋰鋯鋤鍋鋯鋨銹銼鋝鋒鋅鋶鐦鐧銳銻鋃鋟鋦锕錆鍺鍩錯錨錛錡鍀錁錕錩錫錮鑼錘錐錦鑕鍁鍘錕鎦錞錠鍵鋸錳錙鍥鍈鍇鏘鍶鍔鍤鍬鍾鍛鎪鍠鍰鎄鍍鎂鏤鎡鐨鎇鏌鎮鎛鎘鑷钂鐫鎳鎿鎦鎬鎊鎰鎵鑌鎔鏢鏜鏝鏍鏰鏞鏡鏑鏃鏇鏜鏢鏃鏞鏍鏝鏜鏢鏜鏝鏜鏞鏢鏜鐐鏷鑥鐓鑭鐠鑹鏹鐙鑊鐳鐶鐲鐮鐿鑔鑣鑞鑲長門閂閃閆閉問闖閏闈閒閎間閔閌悶閘鬧閨聞闥閩閭闓閥閣閡閫鬮閱閬闍閾閹閶鬩閿閽閻閼闡闌闃闠闊闋闔闐闒闕闞闤隊陽陰陣階際陸隴陳陘陝隉隕險隨隱隸雋難雛讎靂霧霽黴靄靚靜靨韃鞽韉韝韋韌韍韓韙韞韜韻頁頂頃頇項順須頊頑顧頓頎頒頌頏預顱領頗頸頡頰頲頜潁頦頤頻頮頹頷頴穎顆題顒顎顓顏額顳顢顛顙顥頦顫顬顰顴風颺颭颮颯颶颸颼颻飀飄飆飈飛饗饜飣飢飥餳飩餼飪飫飭飯飲餞飾飽飼飿飴餌饒餉餄餎餃餏餅餑餖餓餘餒餕餜餛餡館餷饋餶餿饞饁饃餺餾饈饉饅饊饌饢馬馭馱馴馳驅馹駁驢駔駛駟駙駒騶駐駝駑駕驛駘驍罵駰驕驊駱駭駢驫驪騁驗騂駸駿騏騎騍騅騌驌驂騙騭騤騷騖驁騮騫騸驃騾驢騲騶驟驥驦驤髏髖髕鬢魘魎魚魛魢魷魨魯魴魺魻鮁魴魷魷魷鮐鮑鮑鮐鮚鮒鮓鮐鮑鮞鮦鮦鮞鮪鮪鮪鮪鮪鮪鮪鮪鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭鮭")

def detect_script(txt: str) -> tuple[str, float]:
    s = sum(1 for ch in txt if ch in _SIMP)
    t = sum(1 for ch in txt if ch in _TRAD)
    if s + t == 0:
        return "zh-Hant", 0.0
    ratio_s = s / (s + t)
    return ("zh-Hans" if ratio_s > 0.55 else "zh-Hant"), round(ratio_s, 3)


def quality(txt: str, lang: str) -> dict:
    n = len(txt)
    stats = {
        "chars": n,
        "cjk_ratio": round(cjk_ratio(txt), 4),
        "devanagari_ratio": round(devanagari_ratio(txt), 4),
        "alpha_ratio": round(alpha_ratio(txt), 4),
        "replacement_ratio": round(replacement_ratio(txt), 6),
        "lines": txt.count("\n") + 1 if txt else 0,
    }
    if lang.startswith("zh"):
        detected, simp_ratio = detect_script(txt)
        stats["detected_script"] = detected
        stats["simplified_ratio"] = simp_ratio
        # 0.42 rather than 0.55: a synonym register ("甘草（國老 靈通 …）") is legitimately
        # mostly punctuation and digits by character count, while still being CJK text.
        stats["script_ok"] = stats["cjk_ratio"] > 0.42
    elif lang == "sa":
        stats["script_ok"] = stats["devanagari_ratio"] > 0.45
    else:
        stats["script_ok"] = stats["alpha_ratio"] > 0.55
    stats["clean"] = bool(stats["script_ok"] and stats["replacement_ratio"] < 0.002
                          and n >= 2000)
    return stats


def clean_source(source_id: str, force: bool = False) -> dict | None:
    raw_dir = _net.RAW / source_id
    meta_path = raw_dir / "meta.json"
    raw_path = raw_dir / "text.raw"
    if not meta_path.exists() or not raw_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    kind = meta.get("fetcher", "wikisource")
    lang = meta.get("lang", "en")
    out = PROCESSED_TEXT / f"{source_id}.txt"
    PROCESSED_TEXT.mkdir(parents=True, exist_ok=True)
    if out.exists() and not force:
        txt = out.read_text(encoding="utf-8")
    else:
        raw = raw_path.read_text(encoding="utf-8", errors="replace")
        txt = clean_text(raw, kind, lang)
        out.write_text(txt + "\n", encoding="utf-8", newline="\n")
    stats = quality(txt, lang)
    meta["clean_stats"] = stats
    meta["clean_file"] = f"corpus/processed/text/{source_id}.txt"
    meta["clean_sha256"] = _net.sha256_file(out)
    meta_path.write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"source_id": source_id, "lang": lang, **stats}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true", help="print per-source quality table")
    ap.add_argument("--force", action="store_true", help="re-clean even if output exists")
    ap.add_argument("--only", action="append", default=None)
    args = ap.parse_args(argv)

    ids = sorted(p.name for p in _net.RAW.iterdir()
                 if p.is_dir() and (p / "meta.json").exists())
    if args.only:
        ids = [i for i in ids if i in set(args.only)]
    rows = []
    for sid in ids:
        try:
            r = clean_source(sid, force=args.force)
            if r:
                rows.append(r)
                if not r["clean"]:
                    print(f"[WARN] {sid}: script_ok={r['script_ok']} "
                          f"repl={r['replacement_ratio']} chars={r['chars']:,}",
                          file=sys.stderr)
        except Exception as e:
            print(f"[FAIL] {sid}: {e!r}", file=sys.stderr)

    if args.report or True:
        print(f"\n{'source_id':<44}{'lang':<8}{'chars':>10}  script  repl   ok")
        for r in rows:
            print(f"{r['source_id']:<44}{r['lang']:<8}{r['chars']:>10,}  "
                  f"{str(r['script_ok']):<6}{r['replacement_ratio']:<7}{r['clean']}")
    ok = sum(1 for r in rows if r["clean"])
    print(f"\ncleaned {len(rows)} sources, {ok} pass quality gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
