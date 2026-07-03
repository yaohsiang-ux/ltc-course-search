# -*- coding: utf-8 -*-
"""家庭照顧者 — 家照據點活動公告平台（家總；全國 22 縣市家照/共融據點共用發布）。

資料源: Google Apps Script 公開 JSON API（一次全量，302 轉 googleusercontent 需 allow_redirects）
前端: https://workdai.github.io/care-platform/
台北市的 8 個共融據點（立心/健順/士林靈糧堂/婦女新知/紅心字會…）活動都發布於此。
"""
import datetime

import requests

from . import make_course, region_of, topics_of, clean

SOURCE = {"key": "careplatform", "name": "家照據點活動平台(家總)", "track": "ltc"}
API = "https://script.google.com/macros/s/AKfycbyPuDTU4NJN7FJDiEIhV1NbAs5rYsPmNmddCN6hMOuoLCAoVM3qdB1N8BjDHth49MBu/exec"
FRONT = "https://workdai.github.io/care-platform/"


def fetch():
    r = requests.get(API, timeout=90, allow_redirects=True)
    r.raise_for_status()
    rows = r.json()
    if not isinstance(rows, list):
        raise RuntimeError("API 回傳非 list")
    cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    out = []
    for row in rows:
        title = clean(row.get("title"))
        if not title:
            continue
        start = clean(row.get("sortDate"))[:10]
        if start and start < cutoff:
            continue
        city = clean(row.get("city"))
        location = clean(row.get("location"))
        center = clean(row.get("centerName"))
        signup_url = clean(row.get("signupUrl"))
        fee = clean(row.get("fee"))
        out.append(make_course(
            id=f"careplat-{row.get('id') or (start + title[:30])}",
            title=title,
            start=start, end=start,
            city=f"{city} {location}".strip(),
            region=region_of(city, title, location),
            organizer=center or "家照據點",
            url=signup_url if signup_url.startswith("http") else FRONT,
            source=SOURCE["name"], source_key=SOURCE["key"], track="ltc",
            audience="家庭照顧者",
            categories=sorted(set(topics_of(title) + ["家庭照顧者"])),
            professions=[],
            points="",
            extra={"時間": clean(row.get("time")), "費用": fee, "報名說明": clean(row.get("signupNote"))[:60]},
        ))
    return out


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    tp = [c for c in cs if "臺北" in c["city"] or "台北" in c["city"]]
    print(len(cs), "筆 / 台北", len(tp), "筆")
    for c in tp[:5]:
        print(" ", c["start"], c["title"][:36], "|", c["organizer"][:14], "|", c["extra"].get("費用", ""))
