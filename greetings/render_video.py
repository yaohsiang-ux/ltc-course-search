#!/usr/bin/env python3
"""將 docs/greetings/ 底下的動畫頁逐幀截圖並以 ffmpeg 合成 MP4。

頁面需在 ?capture=1 模式提供 window.__seek(秒)，並可選擇提供 window.__DURATION（秒，預設 30）。

用法：
  python3 greetings/render_video.py                       # 三支賀卡（family staff public）
  python3 greetings/render_video.py storybook --jobs 4    # 中秋立體故事書，四段平行合成
  python3 greetings/render_video.py storybook --preview --times 8 20 --outdir /tmp/x
"""
import argparse, functools, glob, http.server, subprocess, tempfile, threading, time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "greetings"
W, H = 1080, 1920


def page_path(key):
    for cand in (OUT / f"{key}.html", OUT / f"mid-autumn-{key}.html"):
        if cand.exists():
            return cand
    raise SystemExit(f"找不到頁面：{key}")


def chromium_exe():
    for pat in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome", "/opt/pw-browsers/chromium/**/chrome"):
        m = sorted(glob.glob(pat, recursive=True))
        if m:
            return m[-1]
    return None


def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


_SERVER = {}


def serve_dir(root):
    """以本機 HTTP 伺服器提供頁面（ES module 無法從 file:// 載入）。"""
    if root not in _SERVER:
        handler = functools.partial(QuietHandler, directory=str(root))
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        _SERVER[root] = srv.server_address[1]
    return _SERVER[root]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def open_page(p, html):
    html = Path(html)
    port = serve_dir(html.parent)
    b = p.chromium.launch(executable_path=chromium_exe(),
                          args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    pg.on("pageerror", lambda e: print("  [頁面錯誤]", e, flush=True))
    pg.goto(f"http://127.0.0.1:{port}/{html.name}?capture=1")
    pg.wait_for_function("typeof window.__seek === 'function'", timeout=60000)
    pg.wait_for_function("document.fonts.status === 'loaded'", timeout=20000)
    pg.evaluate("document.fonts.ready")
    time.sleep(0.5)
    return b, pg


def page_duration(html):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b, pg = open_page(p, html)
        d = pg.evaluate("window.__DURATION || 30")
        b.close()
    return float(d)


def render_range(task):
    """在獨立程序中截取 [start, end) 幀並編碼成一段 MP4。"""
    html, start, end, fps, seg = task
    from playwright.sync_api import sync_playwright
    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "png", "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(seg)]
    with sync_playwright() as p:
        b, pg = open_page(p, html)
        pg.evaluate("window.__seek(0)")
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        t0 = time.time()
        for i in range(start, end):
            pg.evaluate(f"window.__seek({i / fps})")
            ff.stdin.write(pg.screenshot(type="png"))
            if (i - start) % (fps * 10) == 0:
                print(f"  段 {start}-{end}：{i - start}/{end - start} 幀（{time.time() - t0:.0f}s）", flush=True)
        ff.stdin.close()
        ff.wait()
        b.close()
    return str(seg)


def render(key, fps, jobs):
    html = page_path(key)
    mp4 = html.with_suffix(".mp4")
    dur = page_duration(html)
    total = round(dur * fps)
    print(f"[{html.stem}] {dur:g}s × {fps}fps = {total} 幀，{jobs} 段平行", flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        step = -(-total // jobs)
        tasks = [(str(html), s, min(s + step, total), fps, Path(tmp) / f"seg{n:02d}.mp4")
                 for n, s in enumerate(range(0, total, step))]
        if jobs == 1:
            segs = [render_range(tasks[0])]
        else:
            with ProcessPoolExecutor(jobs, mp_context=get_context("spawn")) as ex:
                segs = list(ex.map(render_range, tasks))
        lst = Path(tmp) / "list.txt"
        lst.write_text("".join(f"file '{s}'\n" for s in segs))
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c", "copy", "-movflags", "+faststart", str(mp4)], check=True)
    print(f"[{html.stem}] 完成 → {mp4}（{mp4.stat().st_size / 1e6:.1f} MB）", flush=True)


def preview(key, times, outdir):
    from playwright.sync_api import sync_playwright
    html = page_path(key)
    with sync_playwright() as p:
        b, pg = open_page(p, html)
        for t in times:
            pg.evaluate(f"window.__seek({t})")
            pg.screenshot(path=str(Path(outdir) / f"{html.stem}-{t:05.1f}s.png"))
        b.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="*", default=["family", "staff", "public"])
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--jobs", type=int, default=1, help="平行合成的程序數")
    ap.add_argument("--preview", action="store_true", help="只輸出指定時間點的 PNG")
    ap.add_argument("--times", type=float, nargs="*", default=[1, 4, 7, 14, 24, 29])
    ap.add_argument("--outdir", default=".")
    a = ap.parse_args()
    for k in a.keys:
        if a.preview:
            preview(k, a.times, a.outdir)
        else:
            render(k, a.fps, a.jobs)


if __name__ == "__main__":
    main()
