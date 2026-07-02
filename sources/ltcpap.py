# -*- coding: utf-8 -*-
"""長照人員繼續教育積分課程 — 衛福部長照專業發展平台（ltcpap.mohw.gov.tw）。

公開課程查詢 API: /molcCourse/course/filter_eg100（bootstrap-table server pagination）
一次全量抓取（約 1700 筆 / 1MB / 15 秒），本地再過濾日期。
課程詳情頁: /molcCourse/course/edit/{id}
"""
import datetime

import requests

from . import make_course, region_of, topics_of, clean

SOURCE = {"key": "ltcpap", "name": "長照專業發展平台(衛福部)", "track": "ltc"}

API = "https://ltcpap.mohw.gov.tw/molcCourse/course/filter_eg100"
DETAIL = "https://ltcpap.mohw.gov.tw/molcCourse/course/edit/{id}"
HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def _date(iso):
    # holdSdt 形如 2026-07-12T05:00:00Z（UTC）；取台北時區日期
    if not iso:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (dt + datetime.timedelta(hours=8)).strftime("%Y-%m-%d")
    except ValueError:
        return iso[:10]


def fetch(session=None, days_back=7):
    s = session or requests.Session()
    r = s.get(API, params={"limit": 5000, "offset": 0}, headers=HEADERS, timeout=120, verify=False)
    r.raise_for_status()
    rows = r.json().get("rows", [])
    cutoff = (datetime.date.today() - datetime.timedelta(days=days_back)).isoformat()
    out = []
    for row in rows:
        start = _date(row.get("holdSdt"))
        end = _date(row.get("holdEdt"))
        if (end or start) < cutoff:  # 已結束太久的不收
            continue
        city = clean(row.get("holdCntname"))
        if city in ("-", ""):
            city = "網路課程"
        cls_prop = [p for p in clean(row.get("classProp")).split(",") if p]
        case_type = [p for p in clean(row.get("caseType")).split(",") if p and p != "其他"]
        title = clean(row.get("actName"))
        organizer = clean(row.get("actUnit")) or clean(row.get("classUnit"))
        out.append(make_course(
            id=f"ltcpap-{row.get('id')}",
            title=title,
            start=start, end=end,
            city=city,
            region=region_of(city, title),
            organizer=organizer,
            url=DETAIL.format(id=row.get("id")),
            source=SOURCE["name"], source_key=SOURCE["key"], track="ltc",
            audience=clean(row.get("longClassTop")),
            categories=sorted(set([t for t in topics_of(title) if t != "其他"] + cls_prop + case_type)) or ["其他"],
            professions=[],
            points="",
            extra={
                "認可單位": clean(row.get("recUnitDesc")),
                "訓練課程": clean(row.get("trainClassDesc")),
                "語言": clean(row.get("statusDesc")),
            },
        ))
    return out


if __name__ == "__main__":
    import json
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    print(json.dumps(cs[:2], ensure_ascii=False, indent=1))
