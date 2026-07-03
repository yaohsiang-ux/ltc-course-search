#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取所有來源的積分課程 → data/courses.json + data/status.json。

單一來源失敗不影響其他來源；失敗來源沿用上次資料（stale-preserve）並標記。
"""
import datetime
import importlib
import json
import sys
import traceback
from pathlib import Path

import urllib3

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from sources import force_ipv4  # noqa: E402

# 來源模組清單（sources/ 下的模組名）
SOURCE_MODULES = [
    "ltcpap",      # 長照（衛福部）
    "icarecat",    # 長照（民間平台長照喵）
    "careplatform",  # 家庭照顧者（家總家照據點活動平台）
    "twna",        # 護理
    "ot",          # 職能
    "tpta",        # 物理
    "dietitians",  # 營養
    "tcpu",        # 諮商心理
    "pharma",      # 藥師
    "tsrt",        # 呼吸
    "slh",         # 語言/聽力
    "tasw",        # 社工
    "eswa",        # 社工（老人長照領域，老社專協）
    "tpcsw",       # 社工（台北市社工師公會）
    "mswa",        # 社工（醫務社工協會）
    "ptroc",       # 物理（公會全聯會 JSON API）
    "nurse_union",  # 護理（護理師護士公會全聯會）
    "tpa",         # 藥師（台北市藥師公會）
    "tmcs",        # 多職類（醫療繼續教育推廣學會）
]

DATA_DIR = BASE / "data"
COURSES_JSON = DATA_DIR / "courses.json"
STATUS_JSON = DATA_DIR / "status.json"


def load_previous():
    if COURSES_JSON.exists():
        try:
            return json.loads(COURSES_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"courses": [], "generated": ""}


def main():
    urllib3.disable_warnings()
    force_ipv4()
    prev = load_previous()
    prev_by_source = {}
    for c in prev.get("courses", []):
        prev_by_source.setdefault(c.get("source_key", "?"), []).append(c)

    old_status_all = {}
    if STATUS_JSON.exists():
        try:
            old_status_all = json.loads(STATUS_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass

    def _stale_courses(mod_name):
        """沿用上次資料；但超過 30 天沒成功抓過的來源直接放棄（避免殭屍課程）。"""
        old = old_status_all.get(mod_name, {})
        fetched = old.get("fetched_at", "")
        if fetched:
            try:
                age = (datetime.date.today() - datetime.date.fromisoformat(fetched[:10])).days
                if age > 30:
                    return [], f"舊資料已逾 {age} 天，不再沿用"
            except ValueError:
                pass
        return prev_by_source.get(mod_name, []), ""

    all_courses = []
    status = {}
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    for mod_name in SOURCE_MODULES:
        try:
            mod = importlib.import_module(f"sources.{mod_name}")
            courses = mod.fetch()
            if not courses and not mod.SOURCE.get("allow_empty"):
                raise RuntimeError("回傳 0 筆（視為失敗）")
            prev_count = old_status_all.get(mod_name, {}).get("count", 0)
            warn = ""
            if prev_count >= 10 and len(courses) < prev_count * 0.3:
                # 量驟減（selector 半壞/只抓到第一頁的徵兆）：合併舊資料保底
                merged_ids = {c["id"] for c in courses}
                extra = [c for c in prev_by_source.get(mod_name, []) if c["id"] not in merged_ids]
                courses = courses + extra
                warn = f"筆數驟減（{prev_count}→{len(merged_ids)}），已合併舊資料"
            all_courses.extend(courses)
            status[mod_name] = {
                "name": mod.SOURCE["name"], "track": mod.SOURCE["track"],
                "ok": True, "count": len(courses),
                "fetched_at": now_str,
                **({"warn": warn} if warn else {}),
            }
            print(f"✅ {mod.SOURCE['name']}: {len(courses)} 筆" + (f"（⚠️ {warn}）" if warn else ""))
        except Exception as e:
            stale, drop_reason = _stale_courses(mod_name)
            all_courses.extend(stale)
            old_status = old_status_all.get(mod_name, {})
            status[mod_name] = {
                "name": old_status.get("name", mod_name), "track": old_status.get("track", "?"),
                "ok": False, "count": len(stale),
                "error": f"{type(e).__name__}: {e}" + (f"；{drop_reason}" if drop_reason else ""),
                "fetched_at": old_status.get("fetched_at", ""),
            }
            print(f"⚠️ {mod_name} 失敗（沿用上次 {len(stale)} 筆）: {e}")
            traceback.print_exc()

    # 去重（同 id 保留第一筆）
    seen, deduped = set(), []
    for c in all_courses:
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        deduped.append(c)
    deduped.sort(key=lambda c: (c.get("start") or "9999", c.get("title", "")))

    DATA_DIR.mkdir(exist_ok=True)
    _atomic_write(COURSES_JSON, json.dumps({
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "courses": deduped,
    }, ensure_ascii=False))
    _atomic_write(STATUS_JSON, json.dumps(status, ensure_ascii=False, indent=1))
    ok_n = sum(1 for s in status.values() if s["ok"])
    print(f"共 {len(deduped)} 筆課程（{ok_n}/{len(status)} 來源成功）→ {COURSES_JSON}")
    # 七成以上來源成功才算整體成功（避免 1/10 成功也寫「更新完成」）
    return 0 if ok_n >= len(status) * 0.7 else 1


def _atomic_write(path, text):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


if __name__ == "__main__":
    sys.exit(main())
