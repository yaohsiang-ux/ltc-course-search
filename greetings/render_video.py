#!/usr/bin/env python3
"""將 docs/greetings/mid-autumn-*.html 逐幀截圖並以 ffmpeg 合成 MP4。

用法：python3 greetings/render_video.py [family staff public] [--fps 30] [--preview]
--preview 只輸出幾個關鍵時間點的 PNG 到 scratch 目錄，供檢查版面。
"""
import argparse, glob, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "greetings"
W, H, DURATION = 1080, 1920, 30

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

def open_page(p, key):
    b = p.chromium.launch(executable_path=chromium_exe())
    pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    pg.goto((OUT / f"mid-autumn-{key}.html").as_uri() + "?capture=1")
    pg.wait_for_function("document.fonts.status === 'loaded'", timeout=20000)
    pg.evaluate("document.fonts.ready")
    time.sleep(0.5)
    return b, pg

def preview(p, key, outdir):
    b, pg = open_page(p, key)
    for t in (1, 4, 7, 14, 24, 29):
        pg.evaluate(f"window.__seek({t})")
        pg.screenshot(path=str(outdir / f"{key}-{t:02d}s.png"))
    b.close()

def render(p, key, fps):
    b, pg = open_page(p, key)
    n = pg.evaluate("window.__seek(0)")
    print(f"[{key}] 動畫數 {n}，{DURATION}s × {fps}fps = {DURATION*fps} 幀")
    mp4 = OUT / f"mid-autumn-{key}.mp4"
    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "png", "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = DURATION * fps
    t0 = time.time()
    for i in range(total):
        pg.evaluate(f"window.__seek({i/fps})")
        ff.stdin.write(pg.screenshot(type="png"))
        if i % (fps * 5) == 0:
            print(f"[{key}] {i}/{total} 幀 ({time.time()-t0:.0f}s)")
    ff.stdin.close()
    ff.wait()
    b.close()
    print(f"[{key}] 完成 → {mp4} ({mp4.stat().st_size/1e6:.1f} MB)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="*", default=["family", "staff", "public"])
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--outdir", default=".")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        for k in a.keys:
            if a.preview:
                preview(p, k, Path(a.outdir))
            else:
                render(p, k, a.fps)

if __name__ == "__main__":
    main()
