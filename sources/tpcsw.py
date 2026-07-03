# -*- coding: utf-8 -*-
"""社工師 — 台北市社會工作師公會（tpcsw.org.tw）。

列表: GET /lesson（offset 分頁 /lesson/index/{0,10,20}）
詳情: /lesson/detail/{id}（開課時間/地點/報名日期結構化；積分在內文 regex，快取）
"""
import datetime
import re

import requests
from bs4 import BeautifulSoup

from . import make_course, region_of, topics_of, clean, west_to_iso
from .aspnet import UA, DetailCache

SOURCE = {"key": "tpcsw", "name": "台北市社工師公會", "track": "med", "allow_empty": True}
BASE = "https://www.tpcsw.org.tw"


def _detail(s, url):
    r = s.get(url, headers=UA, timeout=30, verify=False)
    r.raise_for_status()
    r.encoding = "utf-8"  # 伺服器不一定送 charset
    soup = BeautifulSoup(r.text, "html.parser")
    info = {}
    for div in soup.select(".lesson-info-area .lesson-info, .lesson-info-area li, .lesson-info-area p"):
        txt = clean(div.get_text())
        for key in ("開課單位", "開課地點", "開課時間", "報名日期", "報名金額"):
            m = re.search(key + r"\s*[:：]\s*(.+?)(?=(?:開課單位|開課地點|開課時間|報名日期|報名金額)\s*[:：]|$)", txt)
            if m and key not in info:
                info[key] = clean(m.group(1))
    flat = re.sub(r"\s+", "", soup.get_text())
    m_pts = re.search(r"(?:積分|學分)[^0-9]{0,10}([\d.]+)(?:點|分)?", flat)
    alert = soup.select_one(".alert-red")
    return {
        "start": west_to_iso(info.get("開課時間", "")),
        "location": info.get("開課地點", ""),
        "organizer": info.get("開課單位", ""),
        "signup": info.get("報名日期", ""),
        "fee": info.get("報名金額", ""),
        "points": f"{m_pts.group(1)} 積分" if m_pts else "",
        "status": clean(alert.get_text()) if alert else "",
    }


def fetch():
    s = requests.Session()
    cache = DetailCache("tpcsw")
    cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    out = []
    for offset in (0, 10, 20):
        url = f"{BASE}/lesson" if offset == 0 else f"{BASE}/lesson/index/{offset}"
        r = s.get(url, headers=UA, timeout=60, verify=False)
        r.raise_for_status()
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".text-list-area .text-list a.date-title-area") or soup.select("a[href*='/lesson/detail/']")
        if not items:
            break
        for a in items:
            href = a.get("href") or ""
            m_id = re.search(r"/lesson/detail/(\d+)", href)
            if not m_id:
                continue
            lid = m_id.group(1)
            title_el = a.select_one(".title span") or a.select_one(".title")
            title = clean(title_el.get_text() if title_el else a.get_text())
            durl = href if href.startswith("http") else BASE + href
            info = cache.get(lid)
            if info is None:
                try:
                    info = _detail(s, durl)
                except Exception:
                    info = {}
                if info.get("start"):
                    cache.put(lid, info)
            start = info.get("start", "")
            if start and start < cutoff:
                continue  # 已開課結束（單日課為主）
            out.append(make_course(
                id=f"tpcsw-{lid}",
                title=title,
                start=start, end=start,
                city=info.get("location", ""),
                region=region_of("", title, info.get("location", "") + " 台北"),
                organizer=info.get("organizer", "") or "台北市社工師公會",
                url=durl,
                source=SOURCE["name"], source_key=SOURCE["key"], track="med",
                audience="社工師",
                categories=topics_of(title),
                professions=["社工師"],
                points=info.get("points", ""),
                extra={"報名日期": info.get("signup", ""), "費用": info.get("fee", ""), "狀態": info.get("status", "")},
            ))
        if len(items) < 10:
            break
    cache.save()
    return out


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    for c in cs[:6]:
        print(" ", c["start"] or "????", c["title"][:40], "|", c["points"] or "-")
