# -*- coding: utf-8 -*-
"""積分課程搜尋 — 資料來源共用工具。

每個來源模組需提供:
    SOURCE = {"key": "...", "name": "顯示名稱", "track": "ltc"|"med"}
    def fetch() -> list[dict]   # 回傳正規化課程 list

正規化課程欄位:
    id, title, start, end (YYYY-MM-DD), city, region, organizer,
    url, source, source_key, track, audience, categories(list),
    professions(list), points, extra(dict)
"""
import re
import socket
import unicodedata

# ── 本機 HiNet IPv6 黑洞防護（見 CLAUDE.md 排程穩定性）──
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)


def force_ipv4():
    socket.getaddrinfo = _ipv4_getaddrinfo


# ── 地區對應 ──
REGION_MAP = {
    "北部": ["臺北市", "台北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣", "宜蘭縣"],
    "中部": ["苗栗縣", "臺中市", "台中市", "彰化縣", "南投縣", "雲林縣"],
    "南部": ["嘉義市", "嘉義縣", "臺南市", "台南市", "高雄市", "屏東縣", "澎湖縣"],
    "東部": ["花蓮縣", "臺東縣", "台東縣"],
}
ONLINE_HINTS = ["直播", "視訊", "線上", "網路", "遠距", "webinar", "online", "google meet", "teams", "webex", "youtube", "數位"]
CITY_SHORT = {
    "北部": ["台北", "臺北", "新北", "基隆", "桃園", "新竹", "宜蘭"],
    "中部": ["苗栗", "台中", "臺中", "彰化", "南投", "雲林"],
    "南部": ["嘉義", "台南", "臺南", "高雄", "屏東", "澎湖"],
    "東部": ["花蓮", "台東", "臺東"],
}


def region_of(city, title="", extra_text=""):
    """由縣市/文字判斷地區。回傳 北部/中部/南部/東部/線上/其他。"""
    blob = f"{city} {title} {extra_text}".lower()
    for h in ONLINE_HINTS:
        if h in blob:
            return "線上"
    for region, cities in REGION_MAP.items():
        for c in cities:
            if c in (city or ""):
                return region
    loc_blob = f"{city} {extra_text}"
    for region, keys in CITY_SHORT.items():
        for k in keys:
            if k in loc_blob:
                return region
    # 常見場館地標（最後才比對，避免蓋過縣市名）
    landmarks = {
        "北部": ["台大", "臺大", "北醫", "國北護", "北護", "三軍總醫院", "三總", "馬偕", "振興醫院", "萬芳醫院", "亞東醫院", "長庚大學", "林口長庚", "輔仁大學", "輔大", "陽明交通大學", "國立陽明", "淡江", "政大", "師大", "台師大", "公務人力發展學院", "集思台大", "張榮發基金會"],
        "中部": ["中國醫藥大學", "中山醫學大學", "中興大學", "彰基", "彰化基督教", "澄清醫院", "童綜合"],
        "南部": ["成大", "成功大學", "高醫", "高雄醫學大學", "義大", "奇美", "長庚紀念醫院高雄", "輔英", "嘉南藥理"],
        "東部": ["慈濟大學", "花蓮慈濟", "東華大學"],
    }
    for region, keys in landmarks.items():
        for k in keys:
            if k in loc_blob:
                return region
    return "其他"


# ── 日期解析 ──
def roc_to_iso(s):
    """115/7/2 或 115.07.02 → 2026-07-02。"""
    m = re.search(r"(\d{2,3})[./年](\d{1,2})[./月](\d{1,2})", s or "")
    if not m:
        return ""
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 1000:
        y += 1911
    return f"{y:04d}-{mo:02d}-{d:02d}"


def west_to_iso(s):
    """2026.07.26 / 2026年10月10日 / 2026-07-26 → ISO。"""
    m = re.search(r"(20\d{2})[./年-](\d{1,2})[./月-](\d{1,2})", s or "")
    if not m:
        return ""
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def any_date_to_iso(s):
    return west_to_iso(s) or roc_to_iso(s)


# ── 主題關鍵字標籤（比照範例網站的「類別」chips）──
TOPIC_KEYWORDS = [
    ("失智症", ["失智", "認知症", "認知功能", "認知障礙"]),
    ("復能/復健", ["復能", "復健", "肌力", "行動能力", "運動治療", "體適能"]),
    ("吞嚥/營養", ["吞嚥", "營養", "膳食", "飲食", "咀嚼", "管灌", "灌食"]),
    ("心理/情緒", ["心理", "情緒", "壓力", "諮商", "憂鬱", "自殺", "精神", "身心健康"]),
    ("安寧/緩和", ["安寧", "緩和", "臨終", "善終", "預立醫療", "病主法"]),
    ("感染管制", ["感染", "感控", "防疫", "傳染"]),
    ("安全照護", ["跌倒", "壓傷", "壓瘡", "約束", "safety", "急救", "cpr", "bls", "噎", "哈姆立克"]),
    ("身心障礙", ["身心障礙", "身障", "障礙者"]),
    ("用藥安全", ["用藥", "藥物", "藥事", "多重用藥"]),
    ("法規/倫理", ["法規", "倫理", "法律", "性別", "個資", "勞基", "消防", "緊急應變"]),
    ("慢性病照護", ["糖尿病", "高血壓", "慢性病", "腎臟", "心血管", "中風", "帕金森", "巴金森"]),
    ("家庭照顧者", ["家庭照顧者", "喘息", "照顧者支持"]),
    ("輔具/無障礙", ["輔具", "無障礙", "居家環境"]),
    ("口腔照護", ["口腔", "牙", "潔牙"]),
]


def topics_of(*texts):
    blob = " ".join(t for t in texts if t).lower()
    tags = [name for name, kws in TOPIC_KEYWORDS if any(k in blob for k in kws)]
    return tags or ["其他"]


def clean(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFC", str(s))
    return re.sub(r"\s+", " ", s).strip()


def make_course(**kw):
    c = {
        "id": "", "title": "", "start": "", "end": "", "city": "",
        "region": "其他", "organizer": "", "url": "", "source": "",
        "source_key": "", "track": "med", "audience": "",
        "categories": [], "professions": [], "points": "", "extra": {},
    }
    c.update(kw)
    for k in ("title", "city", "organizer", "audience", "points"):
        c[k] = clean(c[k])
    return c
