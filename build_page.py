#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由 data/courses.json 產生自包含搜尋網頁 積分課程搜尋.html。"""
import datetime
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "積分課程搜尋.html"

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>長照×醫事人員積分課程搜尋</title>
<style>
:root{--org:#D65A31;--amber:#E6AF2E;--brown:#4B3621;--bg:#f5f3f0;--card:#fff;--line:#e8e2da;--txt:#3a3126;--muted:#8a7d6d}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"PingFang TC","Microsoft JhengHei",system-ui,sans-serif;background:var(--bg);color:var(--txt)}
.hero{background:linear-gradient(135deg,var(--brown) 0%,#8a4a2a 55%,var(--org) 100%);color:#fff;padding:34px 16px 30px;text-align:center}
.hero h1{font-size:1.7rem;letter-spacing:.05em}
.hero p.sub{margin-top:8px;opacity:.92;font-size:.95rem}
.badges{margin-top:16px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.badge{background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.35);border-radius:20px;padding:5px 14px;font-size:.85rem}
.wrap{max-width:1060px;margin:0 auto;padding:0 14px 60px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-top:14px;box-shadow:0 1px 4px rgba(75,54,33,.06)}
.searchrow{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.searchrow input{flex:1;min-width:220px;padding:11px 16px;border:1.5px solid var(--line);border-radius:26px;font-size:1rem;outline:none}
.searchrow input:focus{border-color:var(--org)}
.searchrow select{padding:10px 12px;border:1.5px solid var(--line);border-radius:10px;font-size:.9rem;background:#fff;color:var(--txt)}
.frow{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:10px}
.frow:first-child{margin-top:0}
.flabel{font-weight:700;font-size:.88rem;color:var(--brown);min-width:52px}
.chip{border:1.5px solid var(--line);background:#fff;color:var(--txt);border-radius:18px;padding:4px 13px;font-size:.85rem;cursor:pointer;transition:.15s;white-space:nowrap}
.chip:hover{border-color:var(--org);color:var(--org)}
.chip.on{background:var(--org);border-color:var(--org);color:#fff;font-weight:700}
.chip.amber.on{background:var(--amber);border-color:var(--amber);color:var(--brown)}
.chip.green.on{background:#3e7d4f;border-color:#3e7d4f;color:#fff}
.count{margin:16px 4px 4px;font-size:.92rem;color:var(--muted)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-top:10px;display:flex;gap:14px;transition:.15s}
.card:hover{box-shadow:0 3px 12px rgba(214,90,49,.14);border-color:#e9c4b3}
.datebox{min-width:74px;text-align:center;align-self:flex-start;background:linear-gradient(160deg,#faf6ef,#f3e8d8);border:1px solid var(--line);border-radius:10px;padding:8px 6px}
.datebox .md{font-size:1.15rem;font-weight:800;color:var(--org)}
.datebox .wd{font-size:.78rem;color:var(--muted);margin-top:2px}
.datebox .yr{font-size:.72rem;color:var(--muted)}
.datebox.tbd .md{font-size:.9rem;color:var(--muted)}
.cmain{flex:1;min-width:0}
.ctitle{font-size:1.02rem;font-weight:700;line-height:1.45}
.ctitle a{color:var(--brown);text-decoration:none}
.ctitle a:hover{color:var(--org);text-decoration:underline}
.cmeta{margin-top:6px;font-size:.85rem;color:var(--muted);display:flex;gap:12px;flex-wrap:wrap}
.tags{margin-top:8px;display:flex;gap:6px;flex-wrap:wrap}
.tag{font-size:.75rem;border-radius:12px;padding:2px 10px;background:#f4ede3;color:#7a6a52;border:1px solid #eadfce}
.tag.track-ltc{background:var(--amber);color:var(--brown);border-color:var(--amber);font-weight:700}
.tag.track-med{background:#2a7fb8;color:#fff;border-color:#2a7fb8;font-weight:700}
.tag.pts{background:#fdf1e9;color:var(--org);border-color:#f2cdb9;font-weight:700}
.tag.src{background:#fff;border:1px dashed #cbb89a;color:#8a7d6d}
.more{display:block;margin:20px auto;padding:10px 34px;border:none;border-radius:24px;background:var(--org);color:#fff;font-size:.95rem;cursor:pointer}
.more:hover{background:#b8481f}
details.remind{background:linear-gradient(160deg,#fdf6ec,#faeedd);border:1.5px solid var(--amber);border-radius:14px;margin-top:14px;overflow:hidden}
details.remind summary{cursor:pointer;padding:13px 16px;font-weight:700;color:var(--brown);list-style:none;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
details.remind summary::-webkit-details-marker{display:none}
details.remind summary .hint{font-weight:400;font-size:.82rem;color:#9a7b3f}
details.remind[open] summary{border-bottom:1px dashed #e3cfa5}
.rbody{padding:12px 16px 16px;font-size:.88rem;line-height:1.7}
.rbody h4{margin:10px 0 4px;color:var(--org);font-size:.92rem}
.rbody h4:first-child{margin-top:0}
.rbody table{border-collapse:collapse;width:100%;background:#fff;border-radius:8px}
.rbody td,.rbody th{border:1px solid #eadfce;padding:5px 10px;text-align:left;font-weight:400}
.rbody th{background:#f7efe2;font-weight:700;color:var(--brown)}
.rbody .go{display:inline-block;border:1px solid var(--org);color:var(--org);border-radius:12px;padding:0 10px;font-size:.78rem;cursor:pointer;background:#fff;white-space:nowrap}
.rbody .go:hover{background:var(--org);color:#fff}
.rbody .src{font-size:.78rem;color:var(--muted);margin-top:8px}
.empty{text-align:center;padding:50px 0;color:var(--muted)}
footer{margin-top:34px;font-size:.8rem;color:var(--muted);line-height:1.8}
footer table{border-collapse:collapse;margin-top:6px}
footer td,footer th{border:1px solid var(--line);padding:3px 10px;font-weight:400;text-align:left}
footer .ok{color:#3e7d4f}.footer .bad{color:#b8481f}
@media(max-width:640px){.hero h1{font-size:1.3rem}.datebox{min-width:60px}.flabel{width:100%}}
</style>
</head>
<body>
<div class="hero">
  <h1>🎓 長照 × 醫事人員積分課程搜尋</h1>
  <p class="sub">長照人員繼續教育 ＋ 醫事九職類學會課程彙整（__NSOURCES__ 個資料來源）</p>
  <div class="badges">
    <span class="badge">📅 __TODAY__ 起</span>
    <span class="badge">🔄 資料更新：__GENERATED__</span>
    <span class="badge">📚 共 __TOTAL__ 筆</span>
  </div>
</div>
<div class="wrap">
  <details class="remind">
    <summary>📋 教育訓練年度時數提醒
      <span class="hint">每人每年 20 小時（復能8・居家安全2・感管4・原民1・多元1）｜長照認證 6 年 120 點｜點開看明細與一鍵找課</span>
    </summary>
    <div class="rbody">
      <h4>① 每年在職訓練 — 每位服務人員至少 20 小時</h4>
      <table>
        <tr><th>必含課程</th><th>時數</th><th>找課</th></tr>
        <tr><td>復能課程</td><td>≥ 8 小時</td><td><button class="go" data-cat="復能/復健">🔍 復能/復健</button></td></tr>
        <tr><td>居家安全課程</td><td>≥ 2 小時</td><td><button class="go" data-cat="安全照護">🔍 安全照護</button></td></tr>
        <tr><td>感染管制（衛生局查核另計）</td><td>≥ 4 小時/年</td><td><button class="go" data-cat="感染管制">🔍 感染管制</button></td></tr>
        <tr><td>原住民族文化敏感度及能力</td><td>每年 1 點（6年≥6點）</td><td><button class="go" data-q="原住民">🔍 原住民</button></td></tr>
        <tr><td>多元族群文化敏感度及能力</td><td>每年 1 點（6年≥6點）</td><td><button class="go" data-q="多元族群">🔍 多元族群</button></td></tr>
      </table>
      <div>⚠️ 課程須符合<b>長照人員繼續教育積分認證</b>；<b>網路（預錄）課程時數 ×½ 計、每年至多採計 5 小時</b> → 實體/直播課至少要 15 小時。</div>
      <h4>② 長照人員認證更新 — 每 6 年 120 點（平均每年 20 點）</h4>
      <table>
        <tr><th>組成要求</th><th>點數</th></tr>
        <tr><td>專業品質＋專業倫理＋專業法規</td><td>合計 ≥24 點（超過 36 點以 36 點計 → 專業課程實質需 ≥84 點）</td></tr>
        <tr><td>消防安全＋緊急應變＋感染管制＋性別敏感度</td><td>4 項合計 ≥10 點／6 年</td></tr>
        <tr><td>原住民族文化、多元族群文化敏感度及能力</td><td>各 ≥6 點（113.6.3 起每一認證年度各 1 點）</td></tr>
        <tr><td>網路課程採認上限</td><td>超過 80 點以 80 點計（115.3.17 修正）</td></tr>
      </table>
      <div>💡 <b>醫事人員積分可抵免</b>（115/7/1 起系統直接串接）：感染管制、性別敏感度、專業倫理課程直接抵免；「專業課程」依關鍵詞抵免最高 96 點（護理 115/1/1 起；牙醫、職能、呼吸 115/7/1 起，其他職類陸續比照）。</div>
      <h4>③ 其他固定要求</h4>
      <table>
        <tr><td>新進人員</td><td>到職 <b>1 個月內</b>職前訓練 ≥<b>16 小時</b>（勞安、感管、性平、實務操作）</td></tr>
        <tr><td>業務負責人</td><td>每年行政或品質管理教育訓練 ≥<b>4 小時</b></td></tr>
        <tr><td>督導機制</td><td>每位專業人員<b>每季 1 次</b>個督/團督；每年 1 次跨專業（≥3 專業）個案討論團督</td></tr>
      </table>
      <div class="src">依據：115 年臺北市社會局居家服務併居家復能機構評鑑指標 26、28｜114 年臺北市衛生局長照 2.0 專業服務品質查核表 1.4、3.4、3.5｜衛福部《長期照顧服務人員訓練認證繼續教育及登錄辦法》§15（115.3.17 修正）。實際認定以主管機關公告為準。</div>
    </div>
  </details>
  <div class="panel searchrow">
    <input id="q" type="search" placeholder="搜尋課程名稱、主辦單位或地點...">
    <select id="sort">
      <option value="asc">📅 日期由近到遠</option>
      <option value="desc">📅 日期由遠到近</option>
    </select>
  </div>
  <div class="panel" id="filters">
    <div class="frow" data-key="track">
      <span class="flabel">體系：</span>
      <button class="chip green on" data-v="">全部</button>
      <button class="chip green" data-v="ltc">🏠 長照積分</button>
      <button class="chip green" data-v="med">⚕️ 醫事積分</button>
    </div>
    <div class="frow" data-key="prof">
      <span class="flabel">醫事職類：</span>
      <button class="chip on" data-v="">全部</button>
      __PROF_CHIPS__
    </div>
    <div class="frow" data-key="aud">
      <span class="flabel">長照對象：</span>
      <button class="chip amber on" data-v="">全部</button>
      __AUD_CHIPS__
    </div>
    <div class="frow" data-key="cat">
      <span class="flabel">類別：</span>
      <button class="chip on" data-v="">全部</button>
      __CAT_CHIPS__
    </div>
    <div class="frow" data-key="region">
      <span class="flabel">地區：</span>
      <button class="chip green on" data-v="">全台</button>
      <button class="chip green" data-v="北部">🏙 北部</button>
      <button class="chip green" data-v="中部">⛰ 中部</button>
      <button class="chip green" data-v="南部">🌊 南部</button>
      <button class="chip green" data-v="東部">🌄 東部</button>
      <button class="chip green" data-v="線上">💻 線上</button>
      <button class="chip green" data-v="其他">❓ 其他</button>
    </div>
    <div class="frow" data-key="source">
      <span class="flabel">來源：</span>
      <button class="chip amber on" data-v="">全部</button>
      __SRC_CHIPS__
    </div>
  </div>
  <div class="count" id="count"></div>
  <div id="list"></div>
  <button class="more" id="more" style="display:none">顯示更多 ▾</button>
  <footer>
    <b>資料來源狀態</b>（每日自動更新；點課程名稱可連至原網頁報名/詳情）
    <table><tr><th>來源</th><th>體系</th><th>筆數</th><th>最近成功抓取</th></tr>__STATUS_ROWS__</table>
    <p style="margin-top:8px">⚠️ 課程資訊與積分認定以各主辦單位／認證單位公告為準。長照課程資料來自衛福部長照專業發展平台；醫事課程來自各職類學會公開網頁，僅列公開可查之課程，各縣市公會場次請洽所屬公會。</p>
  </footer>
</div>
<script>
const DATA=__DATA__;
const TODAY="__TODAY__";
const WD=['日','一','二','三','四','五','六'];
const AUD_SHORT={'照顧服務人員':'照服員','居家服務督導員':'居督','社會工作人員':'社工','醫事人員':'醫事','照顧管理人員':'照管','社區整合型服務中心個案管理人員（A個管）':'A個管','教保員':'教保員'};
const state={track:'',prof:'',aud:'',cat:'',region:'',source:'',q:'',sort:'asc'};
let shown=0;const CHUNK=100;let cur=[];
const esc=s=>(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function sortKey(c){
  const s=c.start||c.end||'9999-12-31';
  // 已開始但尚未結束的長期課程：以今天為排序基準（現在就能參加）
  if(c.start&&c.start<TODAY&&(c.end||c.start)>=TODAY)return TODAY;
  return s;
}
function apply(){
  const q=state.q.toLowerCase();
  cur=DATA.filter(c=>{
    if(state.track&&c.track!==state.track)return false;
    if(state.prof&&!(c.professions||[]).includes(state.prof))return false;
    if(state.aud&&!(c.audience||'').includes(state.aud))return false;
    if(state.cat&&!(c.categories||[]).includes(state.cat))return false;
    if(state.region&&c.region!==state.region)return false;
    if(state.source&&c.source_key!==state.source)return false;
    if(q){const blob=(c.title+' '+c.organizer+' '+c.city+' '+c.source).toLowerCase();if(!blob.includes(q))return false;}
    return true;
  });
  cur.sort((a,b)=>{const ka=sortKey(a),kb=sortKey(b);return state.sort==='asc'?(ka<kb?-1:ka>kb?1:0):(ka>kb?-1:ka<kb?1:0);});
  shown=0;document.getElementById('list').innerHTML='';renderMore();
  document.getElementById('count').textContent=`顯示 ${cur.length} 筆課程（資料庫共 ${DATA.length} 筆）`;
}
function dateBox(c){
  if(!c.start&&!c.end)return '<div class="datebox tbd"><div class="md">日期</div><div class="wd">見內文</div></div>';
  const d=c.start||c.end;const dt=new Date(d+'T00:00:00');
  // 已開始未結束的長期課程
  if(c.start&&c.start<TODAY&&(c.end||c.start)>=TODAY){
    const e=c.end||c.start;
    return `<div class="datebox"><div class="md" style="font-size:.95rem">進行中</div><div class="wd">至 ${e.slice(0,4)!==TODAY.slice(0,4)?e.slice(2,4)+"'":''}${e.slice(5,7)}/${e.slice(8,10)}</div></div>`;
  }
  const md=(d.slice(5,7))+'/'+d.slice(8,10);
  let range='';
  if(c.end&&c.end!==c.start&&c.start){
    const ey=c.end.slice(0,4)!==d.slice(0,4)?c.end.slice(2,4)+"'":'';
    range=`<div class="yr">~${ey}${c.end.slice(5,7)}/${c.end.slice(8,10)}</div>`;
  }
  const yr=d.slice(0,4)!==TODAY.slice(0,4)?`<div class="yr">${d.slice(0,4)}</div>`:'';
  return `<div class="datebox">${yr}<div class="md">${md}</div><div class="wd">週${WD[dt.getDay()]}</div>${range}</div>`;
}
function card(c){
  const tags=[];
  tags.push(`<span class="tag track-${c.track}">${c.track==='ltc'?'長照':'醫事'}</span>`);
  if(c.points)tags.push(`<span class="tag pts">⭐ ${esc(c.points)}</span>`);
  (c.categories||[]).slice(0,4).forEach(t=>{if(t!=='其他')tags.push(`<span class="tag">${esc(t)}</span>`)});
  tags.push(`<span class="tag src">${esc(c.source)}</span>`);
  const meta=[];
  if(c.organizer)meta.push('🏢 '+esc(c.organizer));
  if(c.city)meta.push('📍 '+esc(c.city));else if(c.region&&c.region!=='其他')meta.push('📍 '+esc(c.region));
  if(c.track==='ltc'&&c.audience){
    const shorts=c.audience.split(',').map(a=>AUD_SHORT[a.trim()]||'').filter(Boolean);
    if(shorts.length&&shorts.length<7)meta.push('👥 '+shorts.join('/'));
  }
  const ex=c.extra||{};const exparts=[];
  ['報名期間','報名時間','報名截止','報名狀態','費用','宣傳期間'].forEach(k=>{if(ex[k])exparts.push(k+'：'+esc(ex[k]))});
  const exline=exparts.length?`<div class="cmeta">${exparts.slice(0,3).join('　')}</div>`:'';
  return `<div class="card">${dateBox(c)}<div class="cmain">
    <div class="ctitle">${c.url?`<a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.title)}</a>`:esc(c.title)}</div>
    <div class="cmeta">${meta.join('')||''}</div>${exline}
    <div class="tags">${tags.join('')}</div></div></div>`;
}
function renderMore(){
  const slice=cur.slice(shown,shown+CHUNK);
  document.getElementById('list').insertAdjacentHTML('beforeend',slice.map(card).join(''));
  shown+=slice.length;
  document.getElementById('more').style.display=shown<cur.length?'block':'none';
  if(!cur.length)document.getElementById('list').innerHTML='<div class="empty">😢 沒有符合條件的課程，試著放寬篩選或換個關鍵字</div>';
}
document.getElementById('more').onclick=renderMore;
document.getElementById('q').addEventListener('input',e=>{state.q=e.target.value.trim();apply();});
document.getElementById('sort').addEventListener('change',e=>{state.sort=e.target.value;apply();});
document.querySelectorAll('.frow').forEach(row=>{
  const key=row.dataset.key;
  row.querySelectorAll('.chip').forEach(chip=>{
    chip.addEventListener('click',()=>{
      row.querySelectorAll('.chip').forEach(x=>x.classList.remove('on'));
      chip.classList.add('on');
      state[key]=chip.dataset.v;
      if(key==='prof'&&chip.dataset.v){setTrack('med');state.aud='';resetRow('aud');}
      if(key==='aud'&&chip.dataset.v){setTrack('ltc');state.prof='';resetRow('prof');}
      if(key==='track'){state.prof='';state.aud='';resetRow('prof');resetRow('aud');}
      apply();
    });
  });
});
function resetRow(key){const row=document.querySelector(`.frow[data-key="${key}"]`);row.querySelectorAll('.chip').forEach((x,i)=>x.classList.toggle('on',i===0));}
function setTrack(v){state.track=v;const row=document.querySelector('.frow[data-key="track"]');row.querySelectorAll('.chip').forEach(x=>x.classList.toggle('on',x.dataset.v===v));}
// 時數提醒面板的一鍵找課
document.querySelectorAll('.rbody .go').forEach(btn=>{
  btn.addEventListener('click',()=>{
    // 全部重設
    state.track='';state.prof='';state.aud='';state.cat='';state.region='';state.source='';state.q='';
    resetRow('track');resetRow('prof');resetRow('aud');resetRow('cat');resetRow('region');resetRow('source');
    document.getElementById('q').value='';
    if(btn.dataset.cat){
      state.cat=btn.dataset.cat;
      const row=document.querySelector('.frow[data-key="cat"]');
      row.querySelectorAll('.chip').forEach(x=>x.classList.toggle('on',x.dataset.v===btn.dataset.cat));
    }
    if(btn.dataset.q){state.q=btn.dataset.q;document.getElementById('q').value=btn.dataset.q;}
    apply();
    document.getElementById('count').scrollIntoView({behavior:'smooth'});
  });
});
apply();
</script>
</body>
</html>
"""

PROFESSIONS = ["護理師", "職能治療師", "物理治療師", "營養師", "諮商心理師", "藥師", "呼吸治療師", "語言治療師", "社工師"]
AUDIENCES = ["照顧服務人員", "居家服務督導員", "社會工作人員", "醫事人員", "照顧管理人員", "A個管", "教保員"]
CATEGORIES = ["失智症", "復能/復健", "吞嚥/營養", "心理/情緒", "感染管制", "安全照護", "安寧/緩和",
              "慢性病照護", "用藥安全", "身心障礙", "家庭照顧者", "輔具/無障礙", "口腔照護",
              "專業課程", "專業品質", "專業倫理", "專業法規"]


def chips(values, cls=""):
    return "\n      ".join(
        f'<button class="chip {cls}" data-v="{v}">{label}</button>'
        for v, label in values
    )


def main():
    data = json.loads((BASE / "data" / "courses.json").read_text(encoding="utf-8"))
    try:
        status = json.loads((BASE / "data" / "status.json").read_text(encoding="utf-8"))
    except Exception:
        status = {}
    today = datetime.date.today().isoformat()
    courses = [c for c in data["courses"]
               if not (c.get("start") or c.get("end")) or (c.get("end") or c.get("start")) >= today]
    # URL 白名單（防 javascript:/data: scheme 注入自包含頁面）
    for c in courses:
        if not str(c.get("url", "")).startswith(("http://", "https://")):
            c["url"] = ""

    src_pairs = []
    seen = set()
    for c in courses:
        if c["source_key"] not in seen:
            seen.add(c["source_key"])
            src_pairs.append((c["source_key"], c["source"]))

    # 類別 chips：策展清單 + 資料中常見（≥20 筆）但不在清單的類別（排除課程型態類）
    import collections
    cat_counts = collections.Counter(cat for c in courses for cat in c.get("categories", []))
    skip_cats = {"其他", "實體課程", "線上課程", "線上搭配實體"}
    categories = [c for c in CATEGORIES if cat_counts.get(c)]
    for cat, n in cat_counts.most_common():
        if n >= 20 and cat not in categories and cat not in skip_cats:
            categories.append(cat)

    status_rows = "".join(
        f'<tr><td>{s["name"]}</td><td>{"長照" if s.get("track") == "ltc" else "醫事"}</td>'
        f'<td>{s["count"]}</td><td>{"✅ " + s.get("fetched_at", "") if s.get("ok") else "⚠️ 抓取失敗（顯示舊資料 " + s.get("fetched_at", "") + "）"}</td></tr>'
        for s in status.values()
    )

    payload = json.dumps(courses, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = (TEMPLATE
            .replace("__DATA__", payload)
            .replace("__TODAY__", today)
            .replace("__GENERATED__", data.get("generated", ""))
            .replace("__TOTAL__", str(len(courses)))
            .replace("__NSOURCES__", str(len(status) or len(src_pairs)))
            .replace("__PROF_CHIPS__", chips([(p, p) for p in PROFESSIONS]))
            .replace("__AUD_CHIPS__", chips([(a, a) for a in AUDIENCES], "amber"))
            .replace("__CAT_CHIPS__", chips([(c, c) for c in categories]))
            .replace("__SRC_CHIPS__", chips(src_pairs, "amber"))
            .replace("__STATUS_ROWS__", status_rows))
    OUT.write_text(html, encoding="utf-8")
    print(f"✅ 產生 {OUT}（{len(courses)} 筆，{len(src_pairs)} 來源）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
