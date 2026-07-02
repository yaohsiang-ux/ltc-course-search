# -*- coding: utf-8 -*-
"""護理師 — 台灣護理學會研習活動（act.e-twna.org.tw，公開 PUB 路徑）。

列表: GET ActClass_List.aspx（GridView，td[data-th]）
詳情: postback → 302 → ActClass_Detail.aspx?{token}（積分數在此，快取避免重複 postback）
"""
import re

import requests

from . import make_course, region_of, topics_of, clean, roc_to_iso
from .aspnet import UA, DetailCache, postback_location, soup_of

SOURCE = {"key": "twna", "name": "台灣護理學會", "track": "med"}
LIST_URL = "https://www.act.e-twna.org.tw/ActSign/PUB/ActClass_List.aspx"


def _parse_points(html_text):
    flat = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", html_text))
    m = re.search(r"繼續教育積分[：:]([\d.]+)點", flat)
    return f"{m.group(1)} 點" if m else ""


def fetch():
    s = requests.Session()
    r = s.get(LIST_URL, headers=UA, timeout=60, verify=False)
    r.raise_for_status()
    soup = soup_of(r)
    table = soup.find("table", id="ctl00_ContentPlaceHolder1_GridView1")
    if not table:
        raise RuntimeError("找不到 GridView 表格")
    cache = DetailCache("twna")
    out = []
    for tr in table.find_all("tr"):
        td_name = tr.find("td", attrs={"data-th": "活動名稱"})
        if not td_name:
            continue
        a = td_name.find("a")
        title = clean(a.get_text() if a else td_name.get_text())
        if not title:
            continue
        dates_txt = clean(" ".join(sp.get_text() for sp in tr.find("td", attrs={"data-th": "辦理日期"}).find_all(["span", "font"])) if tr.find("td", attrs={"data-th": "辦理日期"}) else "")
        all_dates = [roc_to_iso(x) for x in re.findall(r"\d{2,3}/\d{1,2}/\d{1,2}", dates_txt)]
        all_dates = [d for d in all_dates if d]
        start = min(all_dates) if all_dates else ""
        end = max(all_dates) if all_dates else ""
        td_venue = tr.find("td", attrs={"data-th": "活動場地"})
        venue = clean(" ".join(sp.get_text() for sp in td_venue.find_all("span"))) if td_venue else ""
        td_fee = tr.find("td", attrs={"data-th": "費用"})
        fee = clean(td_fee.get_text()) if td_fee else ""
        td_status = tr.find("td", attrs={"data-th": "報名"})
        signup_status = clean(td_status.get_text()) if td_status else ""

        key = f"{title}|{start}"
        cached = cache.get(key)
        if cached is None:
            cached = {"url": LIST_URL, "points": ""}
            # 從 __doPostBack('...','') 取 event target 解析詳情頁
            href = (a.get("href") or "") if a else ""
            m = re.search(r"__doPostBack\('([^']+)'", href)
            if m:
                try:
                    detail_url = postback_location(s, LIST_URL, soup, m.group(1))
                    if detail_url:
                        dr = s.get(detail_url, headers=UA, timeout=30, verify=False)
                        cached = {"url": detail_url, "points": _parse_points(dr.text)}
                except Exception:
                    pass
            # 只快取成功解析的（失敗值不落盤，明天重試）
            if cached.get("url") != LIST_URL:
                cache.put(key, cached)
        out.append(make_course(
            id=f"twna-{key}",
            title=title, start=start, end=end,
            city=venue.split()[0] if venue else "",
            region="北部" if ("台灣護理學會" in venue and region_of("", title, venue) == "其他") else region_of("", title, venue),
            organizer="台灣護理學會",
            url=cached.get("url") or LIST_URL,
            source=SOURCE["name"], source_key=SOURCE["key"], track="med",
            audience="護理師",
            categories=topics_of(title),
            professions=["護理師"],
            points=cached.get("points", ""),
            extra={"費用": fee, "報名狀態": signup_status, "場地": venue},
        ))
    cache.save()
    return out


if __name__ == "__main__":
    import json as _j
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    print(_j.dumps(cs[:3], ensure_ascii=False, indent=1))
