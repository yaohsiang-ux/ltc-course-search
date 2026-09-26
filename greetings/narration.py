#!/usr/bin/env python3
"""為中秋故事書產生旁白音軌，並合成進 MP4。

旁白稿取自故事書頁面的字幕時間軸（CAPS），每句語音對齊字幕出現時間；
若語音比字幕時段長，會把該段畫面時間拉長（時間伸縮），語速維持自然。

語音引擎：
  edge   微軟線上語音（zh-TW-HsiaoChenNeural 等台灣腔），需可連線 speech.platform.bing.com
  kokoro 離線 Kokoro 多語模型（sherpa-onnx），標準華語
預設 auto：能連線就用 edge，否則用 kokoro。

用法：
  python3 greetings/narration.py --models /path/to/models --qa   # 產生音軌、寫入兩頁的時間伸縮節點
  python3 greetings/render_video.py storybook storybook-3d --jobs 4
  python3 greetings/narration.py --mux                            # 把音軌合成進兩支故事書 MP4
  python3 greetings/narration.py --models ... --sample 3 5 9 --qa # 比較幾個 Kokoro 聲音
"""
import argparse, asyncio, html, json, re, subprocess, tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "greetings"
PAGE = OUT / "mid-autumn-storybook-3d.html"
TRACK = OUT / "mid-autumn-storybook-narration.m4a"
TRACK_WEB = OUT / "mid-autumn-storybook-narration.mp3"  # 網頁播放用（各瀏覽器皆支援）
VIDEOS = [OUT / "mid-autumn-storybook.mp4", OUT / "mid-autumn-storybook-3d.mp4"]
SR = 24000
DURATION = 100.0

# 旁白稿與字幕略有不同的句子（口語化、補上收尾祝福）
SPOKEN = {
    "翻開故事書——": "我們一起，翻開故事書。",
    "月圓人團圓<br>燿翔陪您　<b>安心過中秋</b>": "月圓人團圓，燿翔陪您，安心過中秋。燿翔居家長照機構，祝您中秋快樂！",
}
# 語音引擎容易唸錯的字，改用同音字
SOUNDS_LIKE = {"燿翔": "耀翔", "逄蒙": "龐蒙", "長照": "常照"}


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def load_caps():
    src = PAGE.read_text(encoding="utf-8")
    block = src[src.index("const CAPS = ["):]
    block = block[:block.index("];") + 1]
    caps = []
    for m in re.finditer(r"\[([\d.]+),\s*([\d.]+),\s*'([^']*)'\]", block):
        caps.append((float(m.group(1)), float(m.group(2)), m.group(3)))
    return caps


def spoken_text(raw):
    t = SPOKEN.get(raw, raw)
    t = re.sub(r"<br\s*/?>", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t).replace("　", "，").replace("——", "").replace("……", "。")
    for a, b in SOUNDS_LIKE.items():
        t = t.replace(a, b)
    return t.strip()


# ---------------- 語音引擎 ----------------
class Kokoro:
    name = "kokoro"

    def __init__(self, models, sid):
        import sherpa_onnx, opencc
        d = Path(models) / "kokoro-multi-lang-v1_1"
        cfg = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                    model=str(d / "model.onnx"), voices=str(d / "voices.bin"), tokens=str(d / "tokens.txt"),
                    data_dir=str(d / "espeak-ng-data"), dict_dir=str(d / "dict"),
                    lexicon=f"{d / 'lexicon-us-en.txt'},{d / 'lexicon-zh.txt'}"),
                num_threads=4),
            rule_fsts=f"{d / 'phone-zh.fst'},{d / 'date-zh.fst'},{d / 'number-zh.fst'}",
            max_num_sentences=1)
        self.tts = sherpa_onnx.OfflineTts(cfg)
        self.sid = sid
        self.t2s = opencc.OpenCC("t2s")

    def say(self, text, speed=1.0):
        a = self.tts.generate(self.t2s.convert(text), sid=self.sid, speed=speed)
        x = np.asarray(a.samples, dtype=np.float32)
        if a.sample_rate != SR:
            x = resample(x, a.sample_rate, SR)
        return trim(x)


class Edge:
    name = "edge"

    def __init__(self, voice):
        import edge_tts  # noqa
        self.voice = voice

    def say(self, text, speed=1.0):
        import edge_tts
        rate = f"{round((speed - 1) * 100):+d}%"
        with tempfile.TemporaryDirectory() as tmp:
            mp3 = Path(tmp) / "a.mp3"
            asyncio.run(edge_tts.Communicate(text, self.voice, rate=rate).save(str(mp3)))
            wav = Path(tmp) / "a.wav"
            subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(mp3), "-ar", str(SR), "-ac", "1", str(wav)], check=True)
            x, _ = sf.read(wav, dtype="float32")
        return trim(x)


def edge_available():
    try:
        import edge_tts
        asyncio.run(edge_tts.list_voices())
        return True
    except Exception:
        return False


def resample(x, sr_in, sr_out):
    n = int(round(len(x) * sr_out / sr_in))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def trim(x, thr=0.01):
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    a, b = max(0, idx[0] - int(.03 * SR)), min(len(x), idx[-1] + int(.12 * SR))
    return x[a:b]


# ---------------- 語音辨識檢查 ----------------
class ASR:
    def __init__(self, models):
        import sherpa_onnx, opencc
        d = Path(models) / "sherpa-onnx-paraformer-zh-small-2024-03-09"
        self.rec = sherpa_onnx.OfflineRecognizer.from_paraformer(
            paraformer=str(d / "model.int8.onnx"), tokens=str(d / "tokens.txt"), num_threads=4)
        self.t2s = opencc.OpenCC("t2s")

    def check(self, x, text):
        s = self.rec.create_stream()
        s.accept_waveform(SR, x)
        self.rec.decode_stream(s)
        hyp = s.result.text
        ref = re.sub(r"[^\w]", "", self.t2s.convert(text))
        return hyp, 1 - edit_distance(ref, re.sub(r"[^\w]", "", hyp)) / max(1, len(ref))


def edit_distance(a, b):
    dp = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, dp[0] = dp[0], i
        for j, cb in enumerate(b, 1):
            prev, dp[j] = dp[j], min(dp[j] + 1, dp[j - 1] + 1, prev + (ca != cb))
    return dp[-1]


# ---------------- 主流程 ----------------
PAGES = [OUT / "mid-autumn-storybook.html", OUT / "mid-autumn-storybook-3d.html"]
PLAN = OUT / "mid-autumn-storybook-narration.json"


def synth(engine, caps, speed, qa=None):
    clips, report = [], []
    for t0, t1, raw in caps:
        text = spoken_text(raw)
        x = engine.say(text, speed)
        row = {"t": t0, "text": text, "sec": round(len(x) / SR, 2)}
        if qa:
            row["asr"], acc = qa.check(x, text); row["acc"] = round(acc, 3)
        clips.append(x); report.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    return clips, report


def plan(caps, clips, lead=.3, tail=.6):
    """旁白比字幕時段長時，把該段畫面時間拉長（時間伸縮節點：[真實秒, 頁面秒]）。"""
    knots, starts, r = [[0.0, 0.0]], [], caps[0][0]
    knots.append([r, caps[0][0]])
    for i, (t0, _t1, _raw) in enumerate(caps):
        nxt = caps[i + 1][0] if i + 1 < len(caps) else DURATION
        real_len = max(nxt - t0, lead + len(clips[i]) / SR + tail)
        starts.append(r + lead)
        r += real_len
        knots.append([round(r, 3), nxt])
    return knots, starts, r


def build_track(clips, starts, total):
    track = np.zeros(int((total + .5) * SR), dtype=np.float32)
    for x, st in zip(clips, starts):
        a = int(st * SR); track[a:a + len(x)] += x[:len(track) - a]
    return track


def write_track(track):
    peak = float(np.max(np.abs(track))) or 1.0
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "n.wav"
        sf.write(wav, track / peak * 0.9, SR)
        subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(wav),
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000", "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart", str(TRACK)], check=True)
        subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(TRACK), "-c:a", "libmp3lame", "-b:a", "128k",
                        str(TRACK_WEB)], check=True)
    print("音軌 →", TRACK, "與", TRACK_WEB.name)


def patch_pages(knots):
    for page in PAGES:
        s = page.read_text(encoding="utf-8")
        new = re.sub(r"/\*WARP\*/.*?/\*WARP\*/", "/*WARP*/" + json.dumps(knots, separators=(",", ":")) + "/*WARP*/", s, count=1, flags=re.S)
        assert new != s or "/*WARP*/" + json.dumps(knots, separators=(",", ":")) in s, page
        page.write_text(new, encoding="utf-8")
        print("時間伸縮 →", page.name)


def mux(video, total):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / video.name
        subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(video), "-i", str(TRACK),
                        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy",
                        "-t", f"{total:.3f}", "-movflags", "+faststart", str(out)], check=True)
        out.replace(video)
    print("合成 →", video)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", help="放 sherpa-onnx 模型的資料夾")
    ap.add_argument("--engine", choices=["auto", "edge", "kokoro"], default="auto")
    ap.add_argument("--voice", default="zh-TW-HsiaoChenNeural", help="edge 語音名稱")
    ap.add_argument("--sid", type=int, default=3, help="Kokoro 說話者編號")
    ap.add_argument("--speed", type=float, default=.95, help="語速")
    ap.add_argument("--sample", type=int, nargs="*", help="只試幾個 Kokoro 說話者")
    ap.add_argument("--qa", action="store_true", help="以語音辨識檢查每句")
    ap.add_argument("--mux", action="store_true", help="只把現有音軌合成進兩支故事書 MP4（影片重新渲染後執行）")
    a = ap.parse_args()
    if a.mux:
        total = json.loads(PLAN.read_text())["duration"]
        for v in VIDEOS:
            mux(v, total)
        return
    caps = load_caps()
    qa = ASR(a.models) if a.qa else None
    if a.sample:
        probe = [c for c in caps if "十個太陽" in c[2] or "逄蒙" in c[2] or "長生" in c[2]]
        for sid in a.sample:
            eng = Kokoro(a.models, sid)
            accs, f0s = [], []
            for c in probe:
                x = eng.say(spoken_text(c[2]))
                if qa:
                    accs.append(qa.check(x, spoken_text(c[2]))[1])
                f0s.append(pitch(x))
            print(f"sid={sid} 音高≈{np.median(f0s):.0f}Hz 辨識正確率={np.mean(accs) if accs else float('nan'):.3f}", flush=True)
        return
    engine = a.engine
    if engine == "auto":
        engine = "edge" if edge_available() else "kokoro"
    eng = Edge(a.voice) if engine == "edge" else Kokoro(a.models, a.sid)
    print("語音引擎：", engine, a.voice if engine == "edge" else f"sid={a.sid}", flush=True)
    clips, report = synth(eng, caps, a.speed, qa)
    knots, starts, total = plan(caps, clips)
    write_track(build_track(clips, starts, total))
    patch_pages(knots)
    PLAN.write_text(json.dumps({"engine": engine, "voice": a.voice if engine == "edge" else f"kokoro sid={a.sid}",
                                "speed": a.speed, "duration": round(total, 3), "knots": knots, "lines": report},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"總長 {total:.1f} 秒；下一步：重新渲染兩支故事書，再執行 --mux", flush=True)


def pitch(x):
    """粗估基頻（自相關），用來分辨男女聲。"""
    seg = x[len(x) // 4: len(x) // 4 + SR // 2]
    seg = seg - seg.mean()
    ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
    lo, hi = SR // 400, SR // 70
    return SR / (lo + int(np.argmax(ac[lo:hi])))


if __name__ == "__main__":
    main()
