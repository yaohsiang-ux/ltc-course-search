# -*- coding: utf-8 -*-
"""物理治療師 — 中華民國物理治療師公會全國聯合會（pt.org.tw）。

乾淨 JSON API（免登入免 token）: /api/course/search?limit=100&page=N
積分欄位齊全（professional_point/quality_point/certification_point）。
"""
import datetime

import requests

from . import make_course, region_of, topics_of, clean

SOURCE = {"key": "ptroc", "name": "物理治療師公會全聯會", "track": "med", "allow_empty": True}
API = "https://www.pt.org.tw/api/course/search"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def fetch():
    cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    out = []
    page = 1
    while page <= 10:
        r = requests.get(API, params={"limit": 100, "page": page}, headers=UA, timeout=60, verify=False)
        r.raise_for_status()
        data = r.json()
        resp = data.get("response") or {}
        rows = None
        for v in resp.values():
            if isinstance(v, list):
                rows = v
                break
        if not rows:
            break
        total_page = int(resp.get("total_page", 1) or 1)
        for row in rows:
            title = clean(row.get("name"))
            if not title:
                continue
            start = clean(row.get("course_start_datetime"))[:10]
            end = clean(row.get("course_end_datetime"))[:10] or start
            if (end or start) and (end or start) < cutoff:
                continue
            is_online = (row.get("course_type") or "") == "online"
            city = clean(row.get("city"))
            addr = clean(row.get("full_address"))
            pts = []
            for key, label in (("professional_point", "專業"), ("quality_point", "品質"), ("certification_point", "認證")):
                v = row.get(key)
                try:
                    if v is not None and float(v) > 0:
                        pts.append(f"{label}{v}")
                except (TypeError, ValueError):
                    continue
            reg = f"{clean(row.get('registration_start_date'))[:10]} ~ {clean(row.get('registration_end_date'))[:10]}".strip(" ~")
            out.append(make_course(
                id=f"ptroc-{row.get('id') or row.get('code') or title[:30]}",
                title=title,
                start=start, end=end,
                city="線上" if is_online else (f"{city} {addr}".strip() or ""),
                region="線上" if is_online else region_of(city, title, addr),
                organizer=clean(row.get("organizer")) or "物理治療師公會全聯會",
                url="https://www.pt.org.tw/course",
                source=SOURCE["name"], source_key=SOURCE["key"], track="med",
                audience="物理治療師",
                categories=topics_of(title),
                professions=["物理治療師"],
                points=" / ".join(pts) + (" 點" if pts else ""),
                extra={"報名期間": reg, "費用": str(row.get("price", "")), "課程代碼": clean(row.get("code"))},
            ))
        if page >= total_page:
            break
        page += 1
    return out


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    for c in cs[:5]:
        print(" ", c["start"], c["title"][:36], "|", c["points"] or "-", "|", c["region"])
