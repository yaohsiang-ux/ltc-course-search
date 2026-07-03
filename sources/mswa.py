# -*- coding: utf-8 -*-
"""社工師 — 中華民國醫務社會工作協會（mswa.org.tw）。

本會活動: /tw/activity/index.php（詳情 show.php?act_id=，日期在 .sub-info .date，快取）
代刊活動: /tw/activity/activity.php（活動日期直接在列表）
"""
import datetime
import re

import requests
from bs4 import BeautifulSoup

from . import make_course, region_of, topics_of, clean, west_to_iso
from .aspnet import UA, DetailCache

SOURCE = {"key": "mswa", "name": "醫務社工協會", "track": "med", "allow_empty": True}
BASE = "https://www.mswa.org.tw"


def _detail(s, url):
    r = s.get(url, headers=UA, timeout=30, verify=False)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    date_el = soup.select_one(".title-box .sub-info .date") or soup.select_one(".sub-info .date")
    dates = re.findall(r"20\d{2}\.\d{1,2}\.\d{1,2}", date_el.get_text()) if date_el else []
    fee_el = soup.select_one(".tit-price")
    flat = re.sub(r"\s+", "", soup.get_text())
    m_pts = re.search(r"(?:積分|學分)[^0-9]{0,10}([\d.]+)(?:點|分)?", flat)
    return {
        "start": west_to_iso(dates[0]) if dates else "",
        "end": west_to_iso(dates[-1]) if dates else "",
        "fee": clean(fee_el.get_text()) if fee_el else "",
        "points": f"{m_pts.group(1)} 積分" if m_pts else "",
    }


def _own_activities(s, cache, cutoff):
    out = []
    r = s.get(f"{BASE}/tw/activity/index.php", headers=UA, timeout=60, verify=False)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.select("a[href*='show.php?act_id=']"):
        href = a.get("href") or ""
        m_id = re.search(r"act_id=(\d+)", href)
        if not m_id:
            continue
        aid = m_id.group(1)
        tr = a.find_parent("tr")
        title_el = (tr.select_one("td .p_title") if tr else None) or a
        title = clean(title_el.get_text())
        if not title or len(title) < 4:
            continue
        durl = f"{BASE}/tw/activity/show.php?act_id={aid}&page=1"
        info = cache.get(f"act-{aid}")
        if info is None:
            try:
                info = _detail(s, durl)
            except Exception:
                info = {}
            if info.get("start"):
                cache.put(f"act-{aid}", info)
        start, end = info.get("start", ""), info.get("end", "")
        if (end or start) and (end or start) < cutoff:
            continue
        out.append(make_course(
            id=f"mswa-{aid}",
            title=title,
            start=start, end=end,
            city="",
            region=region_of("", title),
            organizer="醫務社會工作協會",
            url=durl,
            source=SOURCE["name"], source_key=SOURCE["key"], track="med",
            audience="社工師",
            categories=topics_of(title),
            professions=["社工師"],
            points=info.get("points", ""),
            extra={"費用": info.get("fee", "")},
        ))
    return out


def _relay_activities(s, cutoff):
    """相關學協會代刊活動（日期直接在列表）。"""
    out = []
    r = s.get(f"{BASE}/tw/activity/activity.php", headers=UA, timeout=60, verify=False)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tr in soup.select("table tr"):
        topic_td = tr.find("td", attrs={"data-th": "主題"})
        a = (topic_td.find("a", href=re.compile(r"activity_show\.php\?num=\d+")) if topic_td
             else None) or tr.find("a", href=re.compile(r"activity_show\.php\?num=\d+"))
        if not a:
            continue
        if topic_td and a not in topic_td.find_all("a"):
            a = topic_td.find("a") or a
        m_id = re.search(r"num=(\d+)", a["href"])
        date_td = tr.find("td", attrs={"data-th": "活動日期"})
        date_iso = west_to_iso(clean(date_td.get_text())) if date_td else ""
        title = clean(a.get_text())
        if not title or re.fullmatch(r"[\d/.\- ~]+", title):
            continue  # 標題不能是純日期（抓錯欄）
        if date_iso and date_iso < cutoff:
            continue
        out.append(make_course(
            id=f"mswa-r{m_id.group(1) if m_id else title[:30]}",
            title=title,
            start=date_iso, end=date_iso,
            city="",
            region=region_of("", title),
            organizer="醫務社工協會(代刊)",
            url=f"{BASE}/tw/activity/activity_show.php?num={m_id.group(1)}" if m_id else f"{BASE}/tw/activity/activity.php",
            source=SOURCE["name"], source_key=SOURCE["key"], track="med",
            audience="社工師",
            categories=topics_of(title),
            professions=["社工師"],
            points="",
            extra={},
        ))
    return out


def fetch():
    s = requests.Session()
    cache = DetailCache("mswa")
    cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    out = _own_activities(s, cache, cutoff)
    cache.save()
    try:
        out += _relay_activities(s, cutoff)
    except Exception:
        pass
    # 同一活動的不同身分報名區（【低收】【一般】…）合併為一筆
    seen, deduped = set(), []
    for c in out:
        key = (re.sub(r"^【[^】]*】", "", c["title"]), c["start"])
        if c["id"] in seen or key in seen:
            continue
        seen.add(c["id"])
        seen.add(key)
        c["title"] = re.sub(r"^【[^】]*身分報名區】", "", c["title"]).strip()
        deduped.append(c)
    return deduped


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    for c in cs[:8]:
        print(" ", c["start"] or "????", c["title"][:44], "|", c["points"] or "-")
