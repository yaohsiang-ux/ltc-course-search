# -*- coding: utf-8 -*-
"""諮商心理師 — 中華民國諮商心理師公會全國聯合會（tcpu.org.tw）。

RSS 一次全量: continuing-education-courses.html?format=feed&type=rss（~90 筆）
課程日期/地點在 description 自由文字，regex 解析。
"""
import datetime
import html as html_mod
import re
import xml.etree.ElementTree as ET

import requests

from . import make_course, region_of, topics_of, clean, any_date_to_iso
from .aspnet import UA

SOURCE = {"key": "tcpu", "name": "諮商心理師公會全聯會", "track": "med"}
RSS = "https://www.tcpu.org.tw/psychologist-continuing-education/continuing-education-courses.html?format=feed&type=rss"


def _strip_tags(s):
    return re.sub(r"<[^>]+>", " ", html_mod.unescape(s or ""))


def _course_dates(text):
    """從內文抓課程日期（今日-60 天 ~ +2 年之間的所有日期）。"""
    today = datetime.date.today()
    lo = (today - datetime.timedelta(days=60)).isoformat()
    hi = (today + datetime.timedelta(days=730)).isoformat()
    found = []
    for m in re.finditer(r"(20\d{2}|1[01]\d)\s*[./年-]\s*(\d{1,2})\s*[./月-]\s*(\d{1,2})", text):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 1000:
            y += 1911
        if not (1 <= mo <= 12 and 1 <= d <= 31):
            continue
        iso = f"{y:04d}-{mo:02d}-{d:02d}"
        if lo <= iso <= hi:
            found.append(iso)
    return sorted(found)


def fetch():
    r = requests.get(RSS, headers=UA, timeout=60, verify=False)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    out = []
    today = datetime.date.today()
    for item in root.iter("item"):
        title = clean(item.findtext("title"))
        link = clean(item.findtext("link"))
        desc = _strip_tags(item.findtext("description") or "")
        if not title:
            continue
        dates = _course_dates(desc)
        if not dates:
            # 無日期的舊公告（發佈超過 60 天）視為過期，略過
            pub = item.findtext("pubDate") or ""
            try:
                pub_dt = datetime.datetime.strptime(pub[5:16], "%d %b %Y").date()
                if (today - pub_dt).days > 60:
                    continue
            except ValueError:
                pass
        m_loc = re.search(r"地\s*點\s*[:：｜|]\s*(\S[^\n]{1,50})", desc)
        location = clean(m_loc.group(1)) if m_loc else ""
        m_pts = re.search(r"(?:積分|學分)[^0-9]{0,10}([\d.]+)\s*(?:點|分)|([\d.]+)\s*(?:點|分)?\s*(?:積分|學分)", desc)
        pts = (m_pts.group(1) or m_pts.group(2)) + " 積分" if m_pts else ""
        out.append(make_course(
            id=f"tcpu-{link.rsplit('/', 1)[-1][:80] or title[:50]}",
            title=title,
            start=dates[0] if dates else "",
            end=dates[-1] if dates else "",
            city=location,
            region=region_of("", title, location + " " + desc[:300]),
            organizer="諮商心理師公會全聯會(公告)",
            url=link or RSS,
            source=SOURCE["name"], source_key=SOURCE["key"], track="med",
            audience="諮商心理師",
            categories=topics_of(title, desc[:500]),
            professions=["諮商心理師"],
            points=pts,
            extra={"地點": location},
        ))
    return out


if __name__ == "__main__":
    import json as _j
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    dated = [c for c in cs if c["start"]]
    print("有日期:", len(dated))
    print(_j.dumps(cs[:2], ensure_ascii=False, indent=1))
