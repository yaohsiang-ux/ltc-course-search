# -*- coding: utf-8 -*-
"""呼吸治療師 — 台灣呼吸治療學會（www.tsrt.org.tw）。

列表: GET Activity.aspx?mid=78&page=N（純 HTML table）
詳情: Activity_1.aspx?id={id}&mid=78（積分在內文自由文字，快取）
"""
import re

import requests
from bs4 import BeautifulSoup

from . import make_course, region_of, topics_of, clean, west_to_iso
from .aspnet import UA, DetailCache

SOURCE = {"key": "tsrt", "name": "台灣呼吸治療學會", "track": "med"}
BASE = "https://www.tsrt.org.tw/"
LIST = BASE + "Activity.aspx?mid=78"


def _detail_info(s, url):
    r = s.get(url, headers=UA, timeout=30, verify=False)
    flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))
    m_loc = re.search(r"活動地點\s*[:：]?\s*([^ ]{2,40})", flat)
    m_pts = re.search(r"([\d.]+)\s*學分", flat)
    return {
        "location": clean(m_loc.group(1)) if m_loc else "",
        "points": f"{m_pts.group(1)} 學分" if m_pts else "",
    }


def fetch():
    s = requests.Session()
    cache = DetailCache("tsrt")
    out = []
    for page in range(1, 5):
        r = s.get(f"{LIST}&page={page}", headers=UA, timeout=60, verify=False)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        rows = []
        for tr in soup.select("table tr"):
            a = tr.find("a", href=re.compile(r"Activity_1\.aspx\?id="))
            if a:
                rows.append((tr, a))
        if not rows:
            break
        for tr, a in rows:
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue
            title = clean(a.get_text())
            from . import any_date_to_iso
            date_iso = west_to_iso(clean(tds[0].get_text())) or any_date_to_iso(title)
            m_id = re.search(r"id=(\d+)", a["href"])
            cid = m_id.group(1) if m_id else title[:30]
            url = f"{BASE}Activity_1.aspx?id={cid}&mid=78"
            fee = clean(tds[2].get_text()) if len(tds) > 2 else ""
            signup = clean(tds[3].get_text()) if len(tds) > 3 else ""
            cached = cache.get(cid)
            if cached is None:
                try:
                    cached = _detail_info(s, url)
                except Exception:
                    cached = {"location": "", "points": ""}
                if cached.get("location") or cached.get("points"):  # 只快取有解析到內容的
                    cache.put(cid, cached)
            out.append(make_course(
                id=f"tsrt-{cid}",
                title=title,
                start=date_iso, end=date_iso,
                city=cached.get("location", ""),
                region=region_of("", title, cached.get("location", "")),
                organizer="台灣呼吸治療學會",
                url=url,
                source=SOURCE["name"], source_key=SOURCE["key"], track="med",
                audience="呼吸治療師",
                categories=topics_of(title),
                professions=["呼吸治療師"],
                points=cached.get("points", ""),
                extra={"費用": fee, "報名期間": signup},
            ))
        if len(rows) < 10:
            break
    cache.save()
    # 去重
    seen, deduped = set(), []
    for c in out:
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        deduped.append(c)
    return deduped


if __name__ == "__main__":
    import json as _j
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    print(_j.dumps(cs[:3], ensure_ascii=False, indent=1))
