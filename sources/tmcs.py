# -*- coding: utf-8 -*-
"""多職類醫事 — 台灣醫療繼續教育推廣學會（tmcs-edu.org.tw）。

⚠️ 只能走 http（https 是 Apache 預設頁 403）；回應帶 UTF-8 BOM。
列表: event_news_list.php（側欄有 11 個分類的加密 arg 連結，逐一抓）
詳情: event_news_detail.php?arg=（活動日期/地點/主辦/認證時數，快取）
"""
import datetime
import re

import requests
from bs4 import BeautifulSoup

from . import make_course, region_of, topics_of, clean, west_to_iso
from .aspnet import UA, DetailCache

SOURCE = {"key": "tmcs", "name": "醫療繼續教育推廣學會", "track": "med", "allow_empty": True}
BASE = "http://www.tmcs-edu.org.tw/activity/"
ENTRY = BASE + "event_news_list.php?class_id=2"
PROF_MAP = [
    ("護理", "護理師"), ("職能", "職能治療師"), ("物理", "物理治療師"),
    ("呼吸", "呼吸治療師"), ("營養", "營養師"), ("藥", "藥師"),
    ("心理", "諮商心理師"), ("語言", "語言治療師"), ("社工", "社工師"),
]


def _get(s, url):
    r = s.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    r.encoding = "utf-8-sig"
    return BeautifulSoup(r.text, "html.parser")


def _detail(s, url):
    soup = _get(s, url)
    flat = re.sub(r"\s+", " ", soup.get_text(" "))
    m_date = re.findall(r"20\d{2}/\d{1,2}/\d{1,2}", flat)
    m_loc = re.search(r"活動地點\s*[:：]?\s*(\S{3,40})", flat)
    m_org = re.search(r"主辦單位\s*[:：]?\s*(\S{3,40})", flat)
    m_pts = re.search(r"認證時數\s*[:：]?\s*([\d.]+)", flat)
    return {
        "start": west_to_iso(m_date[0]) if m_date else "",
        "end": west_to_iso(m_date[-1]) if m_date else "",
        "location": clean(m_loc.group(1)) if m_loc else "",
        "organizer": clean(m_org.group(1)) if m_org else "",
        "points": f"{m_pts.group(1)} 點" if m_pts else "",
    }


def fetch():
    s = requests.Session()
    cache = DetailCache("tmcs")
    cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    entry = _get(s, ENTRY)
    # 側欄分類連結（加密 arg）
    cats = {}
    for a in entry.find_all("a", href=re.compile(r"event_news_list\.php\?arg=")):
        name = clean(a.get_text())
        if name and len(name) < 25:
            cats[a["href"]] = name
    pages = list(cats.items()) or [("event_news_list.php?class_id=2", "")]
    out = []
    for href, cat_name in pages:
        try:
            soup = _get(s, BASE + href if not href.startswith("http") else href)
        except Exception:
            continue
        for a in soup.find_all("a", href=re.compile(r"event_news_detail\.php\?arg=")):
            title = clean(a.get_text())
            if not title or len(title) < 5:
                continue
            durl = BASE + a["href"] if not a["href"].startswith("http") else a["href"]
            key = title[:60]
            info = cache.get(key)
            if info is None:
                try:
                    info = _detail(s, durl)
                except Exception:
                    info = {}
                if info.get("start"):
                    cache.put(key, info)
            start, end = info.get("start", ""), info.get("end", "")
            if (end or start) and (end or start) < cutoff:
                continue
            profs = sorted({p for kw, p in PROF_MAP if kw in (cat_name + title)})
            out.append(make_course(
                id=f"tmcs-{key}",
                title=title,
                start=start, end=end,
                city=info.get("location", ""),
                region=region_of("", title, info.get("location", "")),
                organizer=info.get("organizer", "") or "醫療繼續教育推廣學會",
                url=durl,
                source=SOURCE["name"], source_key=SOURCE["key"], track="med",
                audience="醫事人員(多職類)",
                categories=topics_of(title) + ([cat_name] if cat_name and cat_name not in ("其他單位主辦",) else []),
                professions=profs,
                points=info.get("points", ""),
                extra={"分類": cat_name},
            ))
    cache.save()
    seen, deduped = set(), []
    for c in out:
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        deduped.append(c)
    return deduped


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    for c in cs[:8]:
        print(" ", c["start"] or "????", c["title"][:40], "|", c["points"] or "-", "|", c["extra"].get("分類", ""))
