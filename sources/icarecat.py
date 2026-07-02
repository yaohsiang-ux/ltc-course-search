# -*- coding: utf-8 -*-
"""長照喵（icarecat.com）— 民間長照課程活動平台（補充來源）。

列表: GET /searchevent/{城市}/長照學分（每城市單頁約 30 筆，無分頁）
詳情: GET /event/{id} 內含 schema.org Event JSON-LD（日期/地點/主辦/費用，快取）
"""
import datetime
import json
import re

import requests

from . import make_course, region_of, topics_of, clean
from .aspnet import UA, DetailCache

SOURCE = {"key": "icarecat", "name": "長照喵(民間平台)", "track": "ltc"}
BASE = "https://www.icarecat.com"
CITIES = ["臺北", "新北", "基隆", "桃園", "新竹", "苗栗", "臺中", "彰化", "南投", "雲林",
          "嘉義", "臺南", "高雄", "屏東", "宜蘭", "花蓮", "臺東", "澎湖", "金門", "連江", "線上"]
CATEGORY = "長照學分"


def _event_detail(s, eid):
    r = s.get(f"{BASE}/event/{eid}", headers=UA, timeout=30, verify=False)
    r.raise_for_status()
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', r.text, re.S):
        try:
            d = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if d.get("@type") == "Event":
            loc = d.get("location") or {}
            org = d.get("organizer") or {}
            offer = d.get("offers") or {}
            online = "Online" in (d.get("eventAttendanceMode") or "")
            return {
                "title": clean(d.get("name")),
                "start": (d.get("startDate") or "")[:10],
                "end": (d.get("endDate") or d.get("startDate") or "")[:10],
                "location": clean(loc.get("name") if isinstance(loc, dict) else ""),
                "organizer": clean(org.get("name") if isinstance(org, dict) else ""),
                "price": str(offer.get("price", "")) if isinstance(offer, dict) else "",
                "online": online,
            }
    return None


def fetch():
    s = requests.Session()
    cache = DetailCache("icarecat")
    # 蒐集各城市的 event id（線上分區另標記）
    ids = {}
    for city in CITIES:
        try:
            r = s.get(f"{BASE}/searchevent/{city}/{CATEGORY}", headers=UA, timeout=30, verify=False)
            if r.status_code != 200:
                continue
            for eid in set(re.findall(r"/event/(\d+)", r.text)):
                ids.setdefault(eid, city)
        except Exception:
            continue
    today = datetime.date.today()
    cutoff = (today - datetime.timedelta(days=7)).isoformat()
    out = []
    for eid, city in ids.items():
        info = cache.get(eid)
        if info is None:
            try:
                info = _event_detail(s, eid)
            except Exception:
                info = None
            if info and info.get("start"):
                cache.put(eid, info)
        if not info or not info.get("title"):
            continue
        if (info.get("end") or info.get("start") or "") < cutoff:
            continue  # 已結束
        title = info["title"]
        location = info.get("location", "")
        is_online = info.get("online") or city == "線上"
        out.append(make_course(
            id=f"icarecat-{eid}",
            title=title,
            start=info.get("start", ""), end=info.get("end", ""),
            city=location or (f"{city}（線上）" if is_online else city),
            region="線上" if is_online else region_of(city, title, location),
            organizer=info.get("organizer", "") or "長照喵刊登單位",
            url=f"{BASE}/event/{eid}",
            source=SOURCE["name"], source_key=SOURCE["key"], track="ltc",
            audience="",
            categories=topics_of(title),
            professions=[],
            points="",
            extra={"費用": (info.get("price") or "") and f"NT${info['price']}"},
        ))
    cache.save()
    return out


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    for c in cs[:5]:
        print(" ", c["start"], c["title"][:40], "|", c["region"], "|", c["organizer"][:20])
