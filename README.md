# 長照 × 醫事人員積分課程搜尋

臺北市私立燿翔居家長照機構 — 長照人員與醫事人員繼續教育積分課程彙整搜尋。

**🔗 線上網頁**：https://yaohsiang-ux.github.io/ltc-course-search/

## 資料來源（11 個）

| 體系 | 來源 |
|------|------|
| 長照 | 衛福部長照專業發展平台、長照喵（民間平台） |
| 醫事 | 台灣護理學會、臺灣職能治療學會、臺灣物理治療學會、營養師公會全聯會、諮商心理師公會全聯會、藥師公會全聯會、台灣呼吸治療學會、台灣聽力語言學會、台灣社工專業人員協會 |

## 自動更新

機構主機每日台北時間 07:10 自動抓取所有來源、重建頁面並推送本 repo，
GitHub Pages 隨即發布最新 `docs/index.html`。
單一來源失敗時沿用該來源上次資料並於頁尾標示。

> 註：衛福部等台灣網站封鎖境外 IP，GitHub Actions 無法直接抓取（workflow 僅保留手動測試用）。

## 架構

```
sources/        各來源抓取模組（正規化為統一課程格式）
fetch_all.py    彙整所有來源 → data/courses.json
build_page.py   產生自包含搜尋網頁（含年度時數提醒面板）
update.py       本機排程總控（macOS LaunchAgent 用）
docs/index.html GitHub Pages 發布頁
```

課程資訊與積分認定以各主辦單位／認證單位公告為準。

## 節慶影片（docs/greetings）

中秋節慶賀動畫，直式 1080×1920，包含：

- 30 秒賀卡：「個案與家屬」「同仁」「對外社群」三個版本
- 中秋立體故事書（`mid-autumn-storybook.html`，約 100 秒）：后羿射日、嫦娥奔月、吳剛伐桂，3D 翻頁紙雕動畫，網頁版可用章節按鈕跳播
- 中秋 3D 故事書（`mid-autumn-storybook-3d.html`，約 100 秒）：同樣三則故事，人物、器物、場景皆以 Three.js 建模打光（`vendor/three.module.min.js`，MIT 授權）


- 線上播放：https://yaohsiang-ux.github.io/ltc-course-search/greetings/
- `greetings/build_greetings.py`：由文案設定產出三個自包含 HTML 動畫（修改文案後重新執行即可）
- `greetings/render_video.py`：以 Playwright 逐幀截圖、ffmpeg 合成 MP4（需 `pip install playwright imageio-ffmpeg`）
  - 賀卡：`python3 greetings/render_video.py`
  - 故事書：`python3 greetings/render_video.py storybook --jobs 4`
  - 3D 故事書：`python3 greetings/render_video.py storybook-3d --jobs 4`（以 SwiftShader 軟體 WebGL 渲染）
