# -*- coding: utf-8 -*-
"""語言治療師/聽力師 — 台灣聽力語言學會（www.slh.org.tw）。

列表: GET index.php?do=news&tpid=4&pid=41（div.Study > dl，單頁列全部進行中）
"""
import re

import requests
from bs4 import BeautifulSoup

from . import make_course, region_of, topics_of, clean, west_to_iso
from .aspnet import UA

SOURCE = {"key": "slh", "name": "台灣聽力語言學會", "track": "med"}
LIST = "https://www.slh.org.tw/index.php?do=news&tpid=4&pid=41"


def fetch():
    r = requests.get(LIST, headers=UA, timeout=60, verify=False)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for dl in soup.select("div.Study dl"):
        a = dl.select_one("h3 a") or dl.find("a", href=re.compile(r"id=\d+"))
        if not a:
            continue
        title = clean(a.get_text())
        href = a.get("href") or ""
        m_id = re.search(r"[?&]id=(\d+)", href)
        url = ("https://www.slh.org.tw/" + href.lstrip("/")) if href and not href.startswith("http") else (href or LIST)
        fields = {}
        for li in dl.find_all("li"):
            txt = clean(li.get_text())
            m = re.match(r"(演講者|活動地點|活動日期|報名時間|目前報名人數)\s*[:：]\s*(.*)", txt)
            if m:
                fields[m.group(1)] = m.group(2)
        date_iso = west_to_iso(fields.get("活動日期", ""))
        # 標題常含多日場次（6/27~28、7/4~5），用標題內 M/D 推算結束日
        end_iso = date_iso
        if date_iso:
            year = int(date_iso[:4])
            cands = [date_iso]
            for mm, dd in re.findall(r"(\d{1,2})/(\d{1,2})", title):
                mm, dd = int(mm), int(dd)
                if 1 <= mm <= 12 and 1 <= dd <= 31:
                    y = year + 1 if f"{mm:02d}-{dd:02d}" < date_iso[5:] and mm < int(date_iso[5:7]) - 6 else year
                    cands.append(f"{y:04d}-{mm:02d}-{dd:02d}")
            end_iso = max(cands)
        location = fields.get("活動地點", "")
        out.append(make_course(
            id=f"slh-{m_id.group(1) if m_id else title[:40]}",
            title=title,
            start=date_iso, end=end_iso,
            city=location,
            region=region_of("", title, location),
            organizer="台灣聽力語言學會",
            url=url,
            source=SOURCE["name"], source_key=SOURCE["key"], track="med",
            audience="語言治療師/聽力師",
            categories=topics_of(title),
            professions=["語言治療師"],
            points="",
            extra={"演講者": fields.get("演講者", ""), "報名時間": fields.get("報名時間", ""), "報名人數": fields.get("目前報名人數", "")},
        ))
    return out


if __name__ == "__main__":
    import json as _j
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    print(_j.dumps(cs[:3], ensure_ascii=False, indent=1))
