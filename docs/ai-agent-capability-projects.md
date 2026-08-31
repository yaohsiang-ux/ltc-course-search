# 從「會回答」到「能工作」：6 個補上 AI Agent 缺口的開源專案

AI Agent 是能讀取資料、呼叫工具並執行多步驟任務的 AI 系統。coding agent 則是專門處理程式工作的類型，例如讀檔、修改程式、執行測試與整理差異。

這 6 個專案受到關注，原因不在於又做了一個聊天介面。它們各自補上 Agent 從「會回答」走向「能工作」時缺少的一層：有的解決 Agent 看不見整個 codebase 的問題，有的讓 Agent 記得上次做過什麼，有的給 Agent 一雙操作瀏覽器的手，有的讓多個 Agent 平行開工而不互相踩線。

*資料時間：2026 年 8 月 31 日，星數取自各專案 GitHub 頁面，四捨五入至千位。*

| 專案 | 補上的能力 | GitHub Stars | 開源授權 | 最適合的情境 |
|------|-----------|-------------|---------|-------------|
| [Repomix](https://github.com/yamadashy/repomix) | 程式脈絡與結構打包 | 約 26,000 | MIT | Agent 每次都重讀同一批檔案 |
| [system-prompts-and-models-of-ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools) | 專家角色與工作規則參考 | 約 143,000 | GPL-3.0 | 經常重寫角色 Prompt 與檢查表 |
| [Mem0](https://github.com/mem0ai/mem0) | Agent 通用記憶層 | 約 64,000 | Apache-2.0 | 希望 Agent 記得使用者偏好與過往脈絡 |
| [OpenCut](https://github.com/opencut-app/opencut) | 端到端影片製作流程 | 約 88,000 | MIT | 想讓 coding agent 參與內容製作 |
| [browser-use](https://github.com/browser-use/browser-use) | 網頁與線上服務存取 | 約 112,000 | MIT | 研究時總在手動複製貼上資料 |
| [Vibe Kanban](https://github.com/BloopAI/vibe-kanban) | 多 Agent 平行工作區 | 約 28,000 | Apache-2.0 | 想同時比較多個 Agent 的成果 |

## 各專案在補什麼缺口

### Repomix — Agent 的「一次看懂整個 repo」

LLM 的脈絡視窗有限，Agent 面對大型專案時常常東讀一塊、西讀一塊。Repomix 把整個 repository 打包成單一份 AI 友善的檔案（XML、Markdown、JSON 皆可），並用 tree-sitter 做結構化壓縮，token 用量可減少約七成。提供 CLI、MCP Server、GitHub Actions 等多種使用方式。

### system-prompts-and-models-of-ai-tools — 看懂各家工具怎麼「教」模型工作

收錄 Cursor、Windsurf、Claude Code、Devin 等 30 多個 AI 工具的系統提示詞與內部工具定義。與其每次從零手寫角色設定與工作規則，不如先看業界最成熟的產品是怎麼寫的——這個倉庫等於一份公開的「Agent 工作規則範本庫」。注意授權為 GPL-3.0。

### Mem0 — 讓 Agent 記得上一次

Agent 每次對話都從零開始，是它「不像同事」的主因。Mem0 提供一層通用記憶：自動萃取、儲存並在適當時機取回使用者偏好、事實與過往互動，可自架也有託管服務，是目前記憶層方案中社群最大的一個。

### OpenCut — 讓 Agent 走進內容製作

開源的 CapCut 替代品，支援 Web、桌面與行動裝置。對 Agent 生態特別有意義的是它內建 MCP Server 與 headless 模式——coding agent 可以直接下指令剪輯、合成影片，把「寫程式的 Agent」延伸成「做內容的 Agent」。

### browser-use — 給 Agent 一雙操作網頁的手

讓 AI Agent 能實際瀏覽網站：點擊、填表、擷取資料。研究或資料蒐集時不必再手動複製貼上，交給 Agent 走完整個流程。Python 實作、MIT 授權，是目前瀏覽器操作類專案中星數最高者。

### Vibe Kanban — 多個 Agent 同時開工的調度台

用看板管理多個 coding agent（Claude Code、Codex、Cursor Agent、Gemini 等）：每個任務跑在獨立的 git worktree，Agent 之間不會互相干擾，完成後可視覺化審查、比較不同 Agent 的成果再合併。專案已轉為社群維護。

## 挑選時的三個判斷

1. **先確認缺的是哪一層。** 回答品質差可能是脈絡問題（Repomix）、記憶問題（Mem0）或根本是規則沒寫好（參考 system-prompts）。
2. **授權要看清楚。** GPL-3.0 與 AGPL 類授權對商用整合有衍生條款要求，MIT / Apache-2.0 則寬鬆許多。
3. **星數是熱度不是適配度。** 星數最高的專案未必補得上你的缺口；表格最後一欄「最適合的情境」比星數更值得對照自身工作流。
