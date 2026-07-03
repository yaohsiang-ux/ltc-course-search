# -*- coding: utf-8 -*-
"""護理師 — 中華民國護理師護士公會全國聯合會（nurse.org.tw）。

列表: GET /publicUI/D/D101.aspx（與營養師公會同套系統，GridView；積分直接在列表）
"""
import re

import requests

from . import make_course, region_of, topics_of, clean, any_date_to_iso
from .aspnet import UA, soup_of

SOURCE = {"key": "nurse_union", "name": "護理師護士公會全聯會", "track": "med"}
LIST_URL = "https://www.nurse.org.tw/publicUI/D/D101.aspx"


def fetch():
    s = requests.Session()
    r = s.get(LIST_URL, headers=UA, timeout=60, verify=False)
    r.raise_for_status()
    soup = soup_of(r)
    table = soup.find("table", id=re.compile("GridView")) or soup.find("table")
    if not table:
        raise RuntimeError("找不到課程表格")
    out = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        row_text = clean(tr.get_text(" "))
        date_iso = any_date_to_iso(row_text)
        if not date_iso:
            continue
        a = tr.find("a")
        title = clean(a.get_text()) if a else ""
        if not title or len(title) < 4:
            # 標題可能在非連結欄
            cand = sorted((clean(td.get_text()) for td in tds), key=len, reverse=True)
            title = cand[0] if cand and len(cand[0]) > 6 else ""
        if not title:
            continue
        # 地點欄：含縣市/醫院/大樓字樣的最長欄
        place = ""
        for td in tds:
            t = clean(td.get_text())
            if t != title and re.search(r"(市|縣|醫院|大學|大樓|中心|會館|路|街)", t) and len(t) > len(place):
                place = t
        pts = ""
        for td in tds:
            t = clean(td.get_text())
            # 積分欄格式如「3 專業: 3,」「7.2 專業: 7.2,」
            m = re.match(r"^([\d.]+)\s*(?:專業|品質|倫理|法規|$)", t)
            if m and t != title and len(t) < 30:
                pts = f"{m.group(1)} 點"
                break
        m_signup = re.search(r"(\d{2}-\d{2}\s*\d{2}:\d{2})\s*[~～]\s*(\d{2}-\d{2}[\s\d:]*)", row_text)
        out.append(make_course(
            id=f"nurseu-{date_iso}-{title[:36]}",
            title=title,
            start=date_iso, end=date_iso,
            city=place,
            region=region_of("", title, place),
            organizer="護理師護士公會全聯會",
            url=LIST_URL,
            source=SOURCE["name"], source_key=SOURCE["key"], track="med",
            audience="護理師",
            categories=topics_of(title),
            professions=["護理師"],
            points=pts,
            extra={"報名": m_signup.group(0) if m_signup else ""},
        ))
    return out


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    for c in cs[:6]:
        print(" ", c["start"], c["title"][:36], "|", c["points"] or "-", "|", c["city"][:25])
