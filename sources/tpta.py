# -*- coding: utf-8 -*-
"""物理治療師 — 臺灣物理治療學會（www.tpta.org.tw）。

列表: GET articles.php?type=courses&page=N（div#posts div.entry；積分直接在列表）
"""
import re

import requests
from bs4 import BeautifulSoup

from . import make_course, region_of, topics_of, clean, west_to_iso
from .aspnet import UA

SOURCE = {"key": "tpta", "name": "臺灣物理治療學會", "track": "med"}
BASE = "https://www.tpta.org.tw/"
MAX_PAGES = 6


def _parse_dates(txt):
    """解析「2026年10月10日」「2026年7月9~12日」「6月29日~7月2日」等格式，回傳所有日期。"""
    m_year = re.search(r"(20\d{2})\s*年", txt)
    if not m_year:
        return []
    year = int(m_year.group(1))
    dates = []
    # M月D日（含 M月D~D日 範圍）
    for m in re.finditer(r"(\d{1,2})\s*月\s*(\d{1,2})\s*(?:[~～\-至]\s*(\d{1,2})\s*)?日", txt):
        mo, d1 = int(m.group(1)), int(m.group(2))
        if not (1 <= mo <= 12 and 1 <= d1 <= 31):
            continue
        dates.append(f"{year:04d}-{mo:02d}-{d1:02d}")
        if m.group(3):
            d2 = int(m.group(3))
            if 1 <= d2 <= 31:
                dates.append(f"{year:04d}-{mo:02d}-{d2:02d}")
    return sorted(set(dates))


def fetch():
    s = requests.Session()
    out = []
    for p in range(1, MAX_PAGES + 1):
        r = s.get(BASE + "articles.php", params={"type": "courses", "page": p}, headers=UA, timeout=60, verify=False)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        entries = soup.select("#posts .entry") or soup.select("div.entry")
        if not entries:
            break
        for e in entries:
            a = e.select_one(".entry_title a") or e.find("a")
            if not a:
                continue
            title = clean(a.get_text())
            href = a.get("href") or ""
            url = href if href.startswith("http") else BASE + href.lstrip("/")
            code = clean(" ".join(x.get_text() for x in e.select(".entry_date .day, .entry_date .month")))
            location, date_txt, points = "", "", ""
            for li in e.select(".entry_meta li"):
                txt = clean(li.get_text())
                if li.find("i", class_=re.compile("map-marker")):
                    location = txt
                elif li.find("i", class_=re.compile("clock")):
                    date_txt = txt
                elif li.find("i", class_=re.compile("trophy")):
                    points = txt.replace("積分點數", "").strip(" :：")
            dates = _parse_dates(date_txt)
            m_pts = re.search(r"([\d.]+)\s*(?:積分|學分|點)", points)
            out.append(make_course(
                id=f"tpta-{re.search(r'pid=([0-9]+)', href).group(1) if re.search(r'pid=([0-9]+)', href) else title}",
                title=title if (code.replace(" ", "") in title.replace(" ", "")) else ((f"({code}) " if code else "") + title),
                start=min(dates) if dates else "",
                end=max(dates) if dates else "",
                city=location,
                region=region_of("", title, location),
                organizer="臺灣物理治療學會",
                url=url,
                source=SOURCE["name"], source_key=SOURCE["key"], track="med",
                audience="物理治療師",
                categories=topics_of(title),
                professions=["物理治療師"],
                points=(m_pts.group(1) + " 積分") if m_pts else points,
                extra={"時間": date_txt.strip("/ ")},
            ))
        # 只有一頁時避免重複抓
        if len(entries) < 10:
            break
    # 去重（不同頁可能重複）
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
    print(_j.dumps(cs[:2], ensure_ascii=False, indent=1))
