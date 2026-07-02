#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""積分課程搜尋 — 每日自動更新總控（LaunchAgent com.yaoxiang.course-search 呼叫）。

流程：fetch_all（10 來源，失敗來源沿用舊資料）→ build_page → 寫內部 log。
內部 log 含完成標記「課程更新完成 @ YYYY-MM-DD」（守門員/健檢可查）。
"""
import datetime
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
LOG = BASE / "logs" / "update.log"


def main():
    buf = io.StringIO()
    ok = False
    with redirect_stdout(buf), redirect_stderr(buf):
        try:
            import fetch_all
            import build_page
            fetch_rc = fetch_all.main()
            build_rc = build_page.main()
            ok = (fetch_rc == 0 and build_rc == 0)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"❌ 更新失敗: {e}")
    now = datetime.datetime.now()
    lines = [f"===== {now.strftime('%Y-%m-%d %H:%M:%S')} ====="]
    lines.append(buf.getvalue().rstrip())
    if ok:
        lines.append(f"課程更新完成 @ {now.strftime('%Y-%m-%d')}")
    else:
        lines.append(f"⚠️ 課程更新異常 @ {now.strftime('%Y-%m-%d')}")
    text = "\n".join(lines) + "\n"
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(text)
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
