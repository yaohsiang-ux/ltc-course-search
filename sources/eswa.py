# -*- coding: utf-8 -*-
"""社工師（老人長照領域）— 台灣老人暨長期照護社會工作專業協會「老社專協」（eswa.org.tw）。

課程線上報名: portal_d16.php（單一表格：名稱｜開始~結束｜報名起訖）
"""
import datetime
import re

import requests
from bs4 import BeautifulSoup

from . import make_course, region_of, topics_of, clean
from .aspnet import UA

SOURCE = {"key": "eswa", "name": "老社專協(老人長照社工)", "track": "med", "allow_empty": True}
LIST = "https://www.eswa.org.tw/portal_d16.php?owner_num=d16_340960&button_num=d16"


def fetch():
    r = requests.get(LIST, headers=UA, timeout=60, verify=False)
    r.raise_for_status()
    r.encoding = "utf-8"  # 伺服器未送 charset，requests 會誤判 ISO-8859-1
    soup = BeautifulSoup(r.text, "html.parser")
    table = None
    for tb in soup.find_all("table"):
        if "報名截止日期" in tb.get_text():
            table = tb
    if table is None:
        raise RuntimeError("找不到課程報名表格")
    cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    out = []
    for idx, tr in enumerate(table.find_all("tr")):
        cells = [re.sub(r"\s+", " ", td.get_text()).strip() for td in tr.find_all("td")]
        if len(cells) < 3 or "名稱" in cells[0][:4]:
            continue
        title = re.sub(r"(截止報名|開放報名|目前已額滿。?|額滿即提前截止|\d+)\s*$", "", cells[0]).strip()
        if not title:
            continue
        dates = re.findall(r"20\d{2}-\d{2}-\d{2}", cells[1])
        signup = re.findall(r"20\d{2}-\d{2}-\d{2}", cells[2])
        start = dates[0] if dates else ""
        end = dates[-1] if dates else start
        if (end or start) and (end or start) < cutoff:
            continue  # 已結束
        out.append(make_course(
            id=f"eswa-{start}-{title[:40]}",
            title=title,
            start=start, end=end,
            city="",
            region=region_of("", title),
            organizer="台灣老人暨長期照護社會工作專業協會",
            url=LIST,
            source=SOURCE["name"], source_key=SOURCE["key"], track="med",
            audience="社工師",
            categories=topics_of(title),
            professions=["社工師"],
            points="",
            extra={"報名期間": f"{signup[0]} ~ {signup[-1]}" if signup else ""},
        ))
    return out


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    cs = fetch()
    print(len(cs), "筆")
    for c in cs:
        print(" ", c["start"], "~", c["end"], c["title"][:50])
