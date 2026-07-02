# -*- coding: utf-8 -*-
"""營養師 — 中華民國營養師公會全國聯合會（dietitians.org.tw）。

列表: GET /publicUI/D/D101.aspx（GridView 固定 span id）
詳情: postback LinkButton2 → 302 → D10101.aspx?arg={ID}（快取）
"""
import re

import requests

from . import make_course, region_of, topics_of, clean, any_date_to_iso
from .aspnet import UA, DetailCache, postback_location, soup_of

SOURCE = {"key": "dietitians", "name": "營養師公會全聯會", "track": "med"}
LIST_URL = "https://www.dietitians.org.tw/publicUI/D/D101.aspx"


def _parse_points(html_text):
    flat = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", html_text))
    m = re.search(r"(?:積分|學分)[^0-9]{0,12}([\d.]+)(?:點|分)", flat)
    return f"{m.group(1)} 點" if m else ""


def fetch():
    s = requests.Session()
    r = s.get(LIST_URL, headers=UA, timeout=60, verify=False)
    r.raise_for_status()
    soup = soup_of(r)
    cache = DetailCache("dietitians")
    out = []
    n = 0
    while True:
        sp_date = soup.find("span", id=f"ContentPlaceHolder1_GridView1_lbl_actdate_{n}")
        if not sp_date:
            break
        date_iso = any_date_to_iso(clean(sp_date.get_text()))
        a = soup.find("a", id=f"ContentPlaceHolder1_GridView1_LinkButton2_{n}")
        title = clean(a.get_text()) if a else ""
        sp = soup.find("span", id=f"ContentPlaceHolder1_GridView1_lbl_actddesc_{n}")
        session_desc = clean(sp.get_text()) if sp else ""
        sp = soup.find("span", id=f"ContentPlaceHolder1_GridView1_lbl_actplace_{n}")
        place = clean(sp.get_text()) if sp else ""
        sp = soup.find("span", id=f"ContentPlaceHolder1_GridView1_lbl_status_{n}")
        status = clean(sp.get_text()) if sp else ""
        n += 1
        if not title or "完訓名單" in title:
            continue
        full_title = f"{title} {session_desc}".strip()
        key = f"{full_title}|{date_iso}"
        cached = cache.get(key)
        if cached is None:
            cached = {"url": LIST_URL, "points": ""}
            try:
                # 列 0 → ctl03（GridView 標頭佔 ctl01/02），此時 n 已 +1 故為 n+2
                target = f"ctl00$ContentPlaceHolder1$GridView1$ctl{n + 2:02d}$LinkButton2"
                detail_url = postback_location(s, LIST_URL, soup, target)
                if detail_url:
                    dr = s.get(detail_url, headers=UA, timeout=30, verify=False)
                    cached = {"url": detail_url, "points": _parse_points(dr.text)}
            except Exception:
                pass
            if cached.get("url") != LIST_URL:  # 只快取成功解析的
                cache.put(key, cached)
        out.append(make_course(
            id=f"diet-{key}",
            title=full_title,
            start=date_iso, end=date_iso,
            city=place,
            region=region_of("", full_title, place),
            organizer="營養師公會全聯會",
            url=cached.get("url") or LIST_URL,
            source=SOURCE["name"], source_key=SOURCE["key"], track="med",
            audience="營養師",
            categories=topics_of(full_title),
            professions=["營養師"],
            points=cached.get("points", ""),
            extra={"報名狀態": status, "地點": place},
        ))
    cache.save()
    return out


if __name__ == "__main__":
    import json as _j
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    print(_j.dumps(cs, ensure_ascii=False, indent=1)[:2000])
