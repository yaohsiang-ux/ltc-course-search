# -*- coding: utf-8 -*-
"""社工師 — 台灣社會工作專業人員協會（www.tasw.org.tw）。

本會課程: /tw/CourseList（詳情 /tw/CourseData/{id}，課程日期在詳情內文，快取解析）
跨單位研習彙整: /tw/activity_list/{page}/（宣傳期間）
"""
import datetime
import re

import requests
from bs4 import BeautifulSoup

from . import make_course, region_of, topics_of, clean, west_to_iso
from .aspnet import UA, DetailCache

SOURCE = {"key": "tasw", "name": "台灣社工專業人員協會", "track": "med"}
BASE = "https://www.tasw.org.tw"


def _detail_first_date(s, url):
    """從詳情內文抓課程日期（今日-60 天~+2 年內最早的）。"""
    r = s.get(url, headers=UA, timeout=30, verify=False)
    flat = re.sub(r"<[^>]+>", " ", r.text)
    today = datetime.date.today()
    lo = (today - datetime.timedelta(days=60)).isoformat()
    hi = (today + datetime.timedelta(days=730)).isoformat()
    found = []
    for m in re.finditer(r"(20\d{2}|1[01]\d)\s*[./年-]\s*(\d{1,2})\s*[./月-]\s*(\d{1,2})", flat):
        y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
        y = int(y) + (1911 if int(y) < 1000 else 0)
        if not (1 <= mo <= 12 and 1 <= d <= 31):
            continue
        iso = f"{y:04d}-{mo:02d}-{d:02d}"
        if lo <= iso <= hi:
            found.append(iso)
    return sorted(found)


def _course_list(s, cache):
    out = []
    r = s.get(f"{BASE}/tw/CourseList", headers=UA, timeout=60, verify=False)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for li in soup.select("ul.class-list li"):
        if "list-title" in (li.get("class") or []):
            continue
        a = li.select_one("h3.class-name a") or li.find("a", href=re.compile(r"/CourseData/\d+"))
        if not a:
            continue
        title = clean(a.get_text())
        if any(k in title for k in ("購書", "徵才", "問卷", "招募", "會員大會")):
            continue  # 非課程公告
        href = a.get("href") or ""
        m_id = re.search(r"/CourseData/(\d+)", href)
        cid = m_id.group(1) if m_id else title[:30]
        url = href if href.startswith("http") else BASE + href
        vn = li.select_one("span.view-number")
        d1 = (vn.get("data-dat1") or "") if vn else ""
        d2 = (vn.get("data-dat2") or "") if vn else ""
        signup = f"{d1[:4]}/{d1[4:6]}/{d1[6:]} ~ {d2[:4]}/{d2[4:6]}/{d2[6:]}" if len(d1) == 8 and len(d2) == 8 else ""
        status_el = li.select_one("div.btn-start a")
        status = clean(status_el.get_text()) if status_el else ""
        cached = cache.get(f"course-{cid}")
        if cached is None:
            try:
                dates = _detail_first_date(s, url)
            except Exception:
                dates = []
            cached = {"start": dates[0] if dates else "", "end": dates[-1] if dates else ""}
            if dates:  # 只快取有解析到日期的
                cache.put(f"course-{cid}", cached)
        out.append(make_course(
            id=f"tasw-c{cid}",
            title=title,
            start=cached.get("start", ""), end=cached.get("end", ""),
            city="",
            region=region_of("", title),
            organizer="台灣社工專業人員協會",
            url=url,
            source=SOURCE["name"], source_key=SOURCE["key"], track="med",
            audience="社工師",
            categories=topics_of(title),
            professions=["社工師"],
            points="",
            extra={"報名期間": signup, "報名狀態": status},
        ))
    return out


def _activity_list(s):
    out = []
    for page in range(1, 4):
        r = s.get(f"{BASE}/tw/activity_list/{page}/", headers=UA, timeout=60, verify=False)
        if r.status_code != 200:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for li in soup.select("ul.class-list li"):
            a = li.select_one("h3.class-name a")
            if a:
                items.append((li, a))
        if not items:
            break
        for li, a in items:
            title = clean(a.get_text())
            href = a.get("href") or ""
            m_id = re.search(r"/activity_data/(\d+)", href)
            aid = m_id.group(1) if m_id else title[:30]
            url = href if href.startswith("http") else BASE + href
            kind_el = li.select_one("h2.class-title")
            kind = clean(kind_el.get_text()) if kind_el else ""
            time_el = li.select_one("span.class-date")
            period = clean(time_el.get_text()) if time_el else ""
            dates = [west_to_iso(x) for x in re.findall(r"20\d{2}/\d{1,2}/\d{1,2}", period)]
            dates = [d for d in dates if d]
            out.append(make_course(
                id=f"tasw-a{aid}",
                title=title,
                start="", end=max(dates) if dates else "",
                city="",
                region=region_of("", title),
                organizer=f"社工研習彙整{('(' + kind + ')') if kind else ''}",
                url=url,
                source=SOURCE["name"], source_key=SOURCE["key"], track="med",
                audience="社工師",
                categories=topics_of(title),
                professions=["社工師"],
                points="",
                extra={"宣傳期間": period},
            ))
    return out


def fetch():
    s = requests.Session()
    cache = DetailCache("tasw")
    out = _course_list(s, cache)
    cache.save()
    try:
        out += _activity_list(s)
    except Exception:
        pass
    # 去重
    seen, deduped = set(), []
    for c in out:
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        deduped.append(c)
    return deduped


if __name__ == "__main__":
    import json as _j
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    print(_j.dumps(cs[:3], ensure_ascii=False, indent=1))
