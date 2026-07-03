# -*- coding: utf-8 -*-
"""藥師 — 臺北市藥師公會（tpa.org.tw）。

列表: GET http://www.tpa.org.tw/activity.jsp?type=EDU（⚠️ 只有 http、伺服器慢 timeout 90s）
詳情: EDU01.jsp?year=&jobid=&type=EDU（認證點數含拆分，快取）
"""
import datetime
import re

import requests
from bs4 import BeautifulSoup

from . import make_course, topics_of, clean, roc_to_iso
from .aspnet import UA, DetailCache

SOURCE = {"key": "tpa", "name": "台北市藥師公會", "track": "med", "allow_empty": True}
BASE = "http://www.tpa.org.tw/"


def _detail(s, url):
    r = s.get(url, headers=UA, timeout=90)
    r.raise_for_status()
    r.encoding = "utf-8"
    flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))
    m_date = re.search(r"上課時間[^0-9]{0,6}(\d{2,3}年\d{1,2}月\d{1,2}日)", flat)
    m_loc = re.search(r"上課地點\s*[:：]?\s*([^ ]{4,50})", flat)
    m_pts = re.search(r"認證點數\s*[:：]?\s*([\d.]+)\s*點\s*(【[^】]*】)?", flat)
    return {
        "start": roc_to_iso(m_date.group(1)) if m_date else "",
        "location": clean(m_loc.group(1)) if m_loc else "",
        "points": (f"{m_pts.group(1)} 點" + (m_pts.group(2) or "")) if m_pts else "",
    }


def fetch():
    s = requests.Session()
    cache = DetailCache("tpa")
    cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    out = []
    for typ in ("EDU", "ACT"):
        try:
            r = s.get(f"{BASE}activity.jsp", params={"type": typ}, headers=UA, timeout=90)
            r.raise_for_status()
        except Exception:
            continue
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        # 課程列 = 含 td.Menu-t15-mbule18（課名）的 tr；日期直接在列表；報名連結在巢狀表格
        for td_title in soup.find_all("td", class_="Menu-t15-mbule18"):
            title = clean(td_title.get_text())
            if not title or len(title) < 5:
                continue
            tr = td_title.find_parent("tr")
            if tr is None:
                continue
            row_text = clean(tr.get_text(" "))
            dates = re.findall(r"20\d{2}-\d{2}-\d{2}", row_text)
            start = dates[0] if dates else ""
            end = dates[-1] if dates else start
            a = tr.find("a", href=re.compile(r"EDU01\.jsp\?"))
            if not dates and a is None:
                continue  # 選單/導覽列的同 class td，非課程列
            href = (a.get("href") or "") if a else ""
            m_id = re.search(r"jobid=(\d+)", href)
            jid = m_id.group(1) if m_id else f"{start}-{title[:20]}"
            durl = (BASE + href.lstrip("/")) if href and not href.startswith("http") else (href or f"{BASE}activity.jsp?type={typ}")
            info = cache.get(jid)
            if info is None:
                try:
                    info = _detail(s, durl) if href else {}
                except Exception:
                    info = {}
                if info.get("points") or info.get("location"):
                    cache.put(jid, info)
            if (end or start) and (end or start) < cutoff:
                continue
            out.append(make_course(
                id=f"tpa-{jid}",
                title=title,
                start=start, end=end,
                city=info.get("location", ""),
                region="北部",
                organizer="台北市藥師公會",
                url=durl,
                source=SOURCE["name"], source_key=SOURCE["key"], track="med",
                audience="藥師",
                categories=topics_of(title),
                professions=["藥師"],
                points=info.get("points", ""),
                extra={},
            ))
    cache.save()
    seen, deduped = set(), []
    for c in out:
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        deduped.append(c)
    return deduped


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    for c in cs[:6]:
        print(" ", c["start"] or "????", c["title"][:40], "|", c["points"] or "-")
