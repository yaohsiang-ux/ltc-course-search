# -*- coding: utf-8 -*-
"""藥師 — 中華民國藥師公會全國聯合會（taiwan-pharma.org.tw）。

主來源: POST post_education.php?act=C（⚠️ 年份參數用西元，勿用民國）
輔助來源: dpm.taiwan-pharma.org.tw/menu/64/（外部課程/研討會公告）
"""
import datetime
import re

import requests
from bs4 import BeautifulSoup

from . import make_course, region_of, topics_of, clean, west_to_iso
from .aspnet import UA

SOURCE = {"key": "pharma", "name": "藥師公會全聯會", "track": "med"}
MAIN = "https://www.taiwan-pharma.org.tw/education/post_education.php?act=C"
DPM = "https://dpm.taiwan-pharma.org.tw/menu/64/"


def _fetch_main(s):
    today = datetime.date.today()
    end = today + datetime.timedelta(days=365)
    out = []
    for page in range(1, 6):
        data = {
            "title": "", "page": str(page), "type_id": "A",
            "s_year": str(today.year), "s_month": f"{today.month:02d}", "s_day": "01",
            "e_year": str(end.year), "e_month": f"{end.month:02d}", "e_day": "28",
            "button": "送出",
        }
        r = s.post(MAIN, data=data, headers=UA, timeout=60, verify=False)
        r.raise_for_status()
        r.encoding = r.apparent_encoding  # 網站實際為 big5，requests 猜測會亂碼
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("tr.TrBar_41")
        if not rows:
            break
        for tr in rows:
            tds = tr.find_all("td")
            if len(tds) < 5:
                continue
            date_txt = clean(tds[0].get_text())
            dates = [west_to_iso(x) for x in re.findall(r"20\d{2}-\d{1,2}-\d{1,2}", date_txt)]
            a = tds[1].find("a")
            title = clean(tds[1].get_text())
            href = (a.get("href") or "") if a else ""
            m_id = re.search(r"id=(\d+)", href)
            url = f"https://www.taiwan-pharma.org.tw/education/class_detail.php?id={m_id.group(1)}" if m_id else MAIN
            place = clean(tds[2].get_text())
            organizer = clean(tds[3].get_text())
            m_pts = re.search(r"(\d+)\s*學分", title)
            out.append(make_course(
                id=f"pharma-{m_id.group(1) if m_id else title[:40]}",
                title=title,
                start=min(dates) if dates else "",
                end=max(dates) if dates else "",
                city=place,
                region=region_of("", title, place),
                organizer=organizer or "藥師公會全聯會",
                url=url,
                source=SOURCE["name"], source_key=SOURCE["key"], track="med",
                audience="藥師",
                categories=topics_of(title),
                professions=["藥師"],
                points=f"{m_pts.group(1)} 學分" if m_pts else "",
                extra={"收費": clean(tds[4].get_text())},
            ))
        if len(rows) < 10:
            break
    return out


def _fetch_dpm(s):
    """外部課程/研討會公告（自由文字標題，僅收含日期者）。"""
    out = []
    for page in range(0, 3):
        url = DPM if page == 0 else f"{DPM}?page={page}"
        try:
            r = s.get(url, headers=UA, timeout=60, verify=False)
            r.raise_for_status()
        except Exception:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        links = [a for a in soup.find_all("a", href=True) if re.search(r"/article/\d+", a["href"])]
        stale_cutoff = (datetime.date.today() - datetime.timedelta(days=60)).isoformat()
        for a in links:
            title = clean(a.get_text())
            if len(title) < 8:
                continue
            from . import any_date_to_iso
            iso = any_date_to_iso(title) or ""
            if iso and iso < stale_cutoff:
                continue  # 過期公告
            if not iso and page > 0:
                continue  # 無日期公告只收第 1 頁（最新轉知）
            m = re.search(r"/article/(\d+)", a["href"])
            href = a["href"]
            full = href if href.startswith("http") else "https://dpm.taiwan-pharma.org.tw" + href
            out.append(make_course(
                id=f"pharma-dpm-{m.group(1)}",
                title=title,
                start=iso, end=iso,
                city="",
                region=region_of("", title),
                organizer="藥師公會全聯會(轉知)",
                url=full,
                source=SOURCE["name"], source_key=SOURCE["key"], track="med",
                audience="藥師",
                categories=topics_of(title),
                professions=["藥師"],
                points="",
                extra={},
            ))
        if not links:
            break
    # 去重
    seen, deduped = set(), []
    for c in out:
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        deduped.append(c)
    return deduped


def fetch():
    s = requests.Session()
    out = _fetch_main(s)
    try:
        out += _fetch_dpm(s)
    except Exception:
        pass  # 輔助來源失敗不影響主來源
    return out


if __name__ == "__main__":
    import json as _j
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    print(_j.dumps(cs[:3], ensure_ascii=False, indent=1))
