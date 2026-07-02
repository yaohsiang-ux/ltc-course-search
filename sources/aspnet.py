# -*- coding: utf-8 -*-
"""ASP.NET WebForms postback 工具（護理學會 / 營養師公會 詳情頁解析用）。"""
import json
from pathlib import Path

from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"


def form_fields(soup):
    """收集頁面所有 input/select 欄位值（postback 需完整帶回，缺欄會 500）。"""
    data = {}
    for inp in soup.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        itype = (inp.get("type") or "text").lower()
        if itype in ("checkbox", "radio") and not inp.has_attr("checked"):
            continue
        if itype in ("submit", "button", "image"):
            continue
        data[name] = inp.get("value", "")
    for sel in soup.find_all("select"):
        name = sel.get("name")
        if not name:
            continue
        opt = sel.find("option", selected=True) or sel.find("option")
        data[name] = opt.get("value", "") if opt else ""
    return data


def postback_location(session, url, soup, event_target, event_argument=""):
    """對 url 做 __doPostBack，回傳 302 Location（絕對 URL）；失敗回 None。"""
    data = form_fields(soup)
    data["__EVENTTARGET"] = event_target
    data["__EVENTARGUMENT"] = event_argument
    r = session.post(url, data=data, headers=UA, timeout=30, verify=False, allow_redirects=False)
    loc = r.headers.get("Location")
    if r.status_code in (301, 302) and loc:
        from urllib.parse import urljoin
        return urljoin(url, loc)
    return None


class DetailCache:
    """課程詳情快取：key → {url, points, ...}，避免每日排程重複 postback。"""

    def __init__(self, name):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.path = CACHE_DIR / f"{name}.json"
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self.data = {}

    def get(self, key):
        return self.data.get(key)

    def put(self, key, value):
        self.data[key] = value

    def save(self):
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)


def soup_of(resp):
    return BeautifulSoup(resp.text, "html.parser")
