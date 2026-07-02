# -*- coding: utf-8 -*-
"""職能治療師 — 臺灣職能治療學會（www.ot.org.tw；注意舊網域 ot-roc.org.tw 已被佔用勿使用）。

列表: GET /?action=physical-course|online-course|physical-online-course&p=N（td[data-title]）
"""
import re

import requests
from bs4 import BeautifulSoup

from . import make_course, region_of, topics_of, clean, west_to_iso
from .aspnet import UA

SOURCE = {"key": "ot", "name": "臺灣職能治療學會", "track": "med"}
BASE = "https://www.ot.org.tw/"
ACTIONS = [
    ("physical-course", "實體課程"),
    ("online-course", "線上課程"),
    ("physical-online-course", "線上搭配實體"),
]
MAX_PAGES = 8


def _td(tr, key):
    td = tr.find("td", attrs={"data-title": key})
    return td


def fetch():
    s = requests.Session()
    out = []
    for action, kind in ACTIONS:
        for p in range(1, MAX_PAGES + 1):
            r = s.get(BASE, params={"action": action, "p": p}, headers=UA, timeout=60, verify=False)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            rows = [tr for tr in soup.select("table.tablestyle tr") if _td(tr, "課程名稱：")]
            if not rows:
                break
            for tr in rows:
                td_name = _td(tr, "課程名稱：")
                a = td_name.find("a")
                title = clean(td_name.get_text())
                date_txt = clean(_td(tr, "課程日期：").get_text()) if _td(tr, "課程日期：") else ""
                dates = [west_to_iso(x) for x in re.findall(r"20\d{2}[./]\d{1,2}[./]\d{1,2}", date_txt)]
                dates = [d for d in dates if d]
                organizer = clean(_td(tr, "舉辦單位：").get_text()) if _td(tr, "舉辦單位：") else ""
                loc_td = _td(tr, "課程地點：") or _td(tr, "使用平台：")
                location = clean(loc_td.get_text()) if loc_td else ""
                deadline_td = _td(tr, "截止日期：")
                deadline = clean(deadline_td.get_text()) if deadline_td else ""
                href = a.get("href") if a else ""
                url = href if (href or "").startswith("http") else (BASE.rstrip("/") + "/" + (href or "").lstrip("/")) if href else BASE + f"?action={action}"
                is_online = action == "online-course"
                out.append(make_course(
                    id=f"ot-{action}-{re.search(r'id=([0-9]+)', href or '').group(1) if re.search(r'id=([0-9]+)', href or '') else title}",
                    title=title,
                    start=min(dates) if dates else "",
                    end=max(dates) if dates else "",
                    city=location,
                    region="線上" if is_online else region_of("", title, location),
                    organizer=organizer or "臺灣職能治療學會",
                    url=url,
                    source=SOURCE["name"], source_key=SOURCE["key"], track="med",
                    audience="職能治療師",
                    categories=sorted(set(topics_of(title) + [kind])),
                    professions=["職能治療師"],
                    points="",
                    extra={"課程型態": kind, "報名截止": deadline},
                ))
            if len(rows) < 10:
                break
    return out


if __name__ == "__main__":
    import json as _j
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    print(_j.dumps(cs[:2], ensure_ascii=False, indent=1))
