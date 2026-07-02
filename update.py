#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""積分課程搜尋 — 每日自動更新總控（LaunchAgent com.yaoxiang.course-search 呼叫）。

流程：fetch_all（失敗來源沿用舊資料）→ build_page → 推送 GitHub Pages → 寫內部 log。
內部 log 含完成標記「課程更新完成 @ YYYY-MM-DD」（守門員/健檢可查）。
GitHub 推送失敗只記 log 不影響本機更新（政府網站鎖境外 IP，雲端無法自抓，由本機推送）。
"""
import datetime
import io
import shutil
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
LOG = BASE / "logs" / "update.log"
GIT = "/usr/bin/git"


def push_to_github():
    """把最新頁面與資料推上 GitHub（Pages 從 docs/ 發布）。回傳狀態字串。"""
    if not (BASE / ".git").exists():
        return "略過推送（非 git repo）"
    (BASE / "docs").mkdir(exist_ok=True)
    shutil.copy(BASE / "積分課程搜尋.html", BASE / "docs" / "index.html")

    def run(*args, timeout=180):
        return subprocess.run([GIT, "-C", str(BASE), *args],
                              capture_output=True, text=True, timeout=timeout)

    try:
        run("pull", "--rebase", "--autostash", "origin", "main")
        run("add", "data", "docs", "積分課程搜尋.html")
        diff = run("diff", "--cached", "--quiet")
        if diff.returncode == 0:
            return "GitHub 無變更"
        c = run("commit", "-m", f"自動更新課程資料 {datetime.date.today().isoformat()}")
        if c.returncode != 0:
            return f"⚠️ GitHub commit 失敗: {c.stderr.strip()[:200]}"
        p = run("push", "origin", "main")
        if p.returncode != 0:
            return f"⚠️ GitHub push 失敗: {p.stderr.strip()[:200]}"
        return "✅ 已推送 GitHub Pages"
    except Exception as e:
        return f"⚠️ GitHub 推送異常: {type(e).__name__}: {e}"


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
        lines.append(push_to_github())
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
