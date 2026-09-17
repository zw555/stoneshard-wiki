# -*- coding: utf-8 -*-
"""Build a searchable bilingual (EN/ZH) lookup page from localization.jsonl.

Produces site/index.html — a single-file prototype of the future wiki,
with all extracted text embedded for offline client-side search.
"""
import json, os, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "localization.jsonl")
SITE = os.path.join(ROOT, "site")
os.makedirs(SITE, exist_ok=True)

def main():
    rows = []
    with open(DATA, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            en = r.get("en", "")
            zh = r.get("zh", "")
            if not en and not zh:
                continue
            fmt = r["fmt"]
            key = r.get("key", "")
            meta = ""
            if fmt == "dlg":
                bits = [b for b in (r.get("role"), r.get("type"), r.get("faction"), r.get("settlement")) if b]
                meta = " · ".join(bits)
            rows.append([fmt, key, meta, en, zh])
    print("rows embedded:", len(rows))
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    print("payload size: %.1f MB" % (len(payload.encode("utf-8")) / 1e6))

    page = TEMPLATE.replace("__PAYLOAD__", payload).replace("__COUNT__", str(len(rows)))
    out = os.path.join(SITE, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print("saved ->", out, f"({os.path.getsize(out):,} bytes)")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stoneshard 紫色晶石 · 双语数据库 (Wiki 雏形)</title>
<style>
:root {
  --bg:#f6f4ef; --panel:#fffdf8; --ink:#2b2620; --muted:#8a8177;
  --accent:#7c5cbf; --accent-2:#5c46a0; --line:#e5dfd4; --gold:#b98a2e;
}
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--ink); font-family:"Segoe UI","Microsoft YaHei",sans-serif; min-height:100vh; }
header { background:linear-gradient(135deg,#3d2f5c,#241b3a); color:#efe9ff; padding:28px 24px 22px; }
header h1 { font-size:26px; letter-spacing:1px; }
header h1 span { color:#c9b8ff; }
header p { margin-top:8px; color:#b7a9e0; font-size:13px; }
.wrap { max-width:1000px; margin:0 auto; padding:20px 16px 60px; }
.searchbar { display:flex; gap:10px; margin-top:-24px; }
.searchbar input {
  flex:1; padding:14px 18px; font-size:16px; border:1px solid var(--line);
  border-radius:10px; background:var(--panel); color:var(--ink); outline:none;
  box-shadow:0 4px 14px rgba(60,40,100,.10);
}
.searchbar input:focus { border-color:var(--accent); }
select { padding:12px 12px; border-radius:10px; border:1px solid var(--line); background:var(--panel); color:var(--ink); font-size:14px; }
.stats { color:var(--muted); font-size:13px; margin:14px 2px 10px; }
.card {
  background:var(--panel); border:1px solid var(--line); border-left:4px solid var(--accent);
  border-radius:8px; padding:12px 14px; margin-bottom:10px;
}
.card.dlg { border-left-color:var(--gold); }
.card .key { font-family:Consolas,monospace; font-size:11.5px; color:var(--accent-2); margin-bottom:6px; word-break:break-all; }
.card .meta { font-size:11px; color:var(--muted); margin-bottom:6px; }
.card .en { font-size:14.5px; line-height:1.45; }
.card .zh { font-size:14.5px; line-height:1.45; color:#1d4ed8; margin-top:6px; white-space:pre-wrap; }
.tag { display:inline-block; font-size:10.5px; padding:1px 7px; border-radius:99px; background:#efe9fb; color:var(--accent-2); margin-right:6px; }
.tag.dlg { background:#f7ecd6; color:#8a6415; }
mark { background:#ffe9a8; padding:0 2px; border-radius:3px; }
.empty { text-align:center; color:var(--muted); padding:60px 0; font-size:15px; }
kbd { background:var(--line); border-radius:4px; padding:0 6px; font-size:12px; }
</style>
</head>
<body>
<header>
  <h1>Stoneshard <span>紫色晶石</span> · 双语数据库</h1>
  <p>数据来源：从游戏本体 (StoneShard.exe / data.win) 直接提取 · 共 __COUNT__ 条文本 · Wiki 雏形 v0.1</p>
</header>
<div class="wrap">
  <div class="searchbar">
    <input id="q" type="text" placeholder="搜索英文 / 中文 / 键名… (支持中英混搜，按 Enter 清除高亮)" autofocus>
    <select id="cat">
      <option value="all">全部类型</option>
      <option value="ui">UI / 物品 / 技能文本</option>
      <option value="dlg">NPC 对话</option>
    </select>
  </div>
  <div class="stats" id="stats"></div>
  <div id="results"></div>
  <div class="empty" id="hint">输入关键词开始搜索，例如 <kbd>bleeding</kbd>、<kbd>出血</kbd>、<kbd>treatise</kbd>、<kbd>车队</kbd></div>
</div>
<script>
const ROWS = __PAYLOAD__;
const q = document.getElementById('q'), cat = document.getElementById('cat');
const results = document.getElementById('results'), stats = document.getElementById('stats'), hint = document.getElementById('hint');
let lastTerms = [];
function esc(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function hl(s, terms){
  let out = esc(s);
  for (const t of terms) {
    if (!t) continue;
    const re = new RegExp('('+ t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&') +')','gi');
    out = out.replace(re,'<mark>$1</mark>');
  }
  return out;
}
function norm(s){ return s.toLowerCase(); }
function search(){
  const term = norm(q.value.trim());
  const c = cat.value;
  if (!term) { results.innerHTML=''; stats.textContent=''; hint.style.display=''; return; }
  hint.style.display='none';
  const terms = term.split(/\s+/);
  const out = [];
  for (const r of ROWS) {
    if (c !== 'all' && r[0] !== c) continue;
    const hay = norm(r[1]) + '\x01' + norm(r[3]) + '\x01' + norm(r[4]);
    let ok = true;
    for (const t of terms) if (!hay.includes(t)) { ok=false; break; }
    if (ok) out.push(r);
    if (out.length >= 400) break;
  }
  lastTerms = terms;
  stats.textContent = `命中 ${out.length}${out.length>=400?'+':''} 条` + (out.length>=400?'（仅显示前 400 条）':'');
  const frag = [];
  for (const r of out) {
    frag.push(`<div class="card ${r[0]==='dlg'?'dlg':''}">
      <div class="key">${r[0]==='dlg'?'<span class="tag dlg">对话</span>':'<span class="tag">文本</span>'}${esc(r[1]||'(无键名)')}</div>
      ${r[2]?`<div class="meta">${esc(r[2])}</div>`:''}
      <div class="en">${hl(r[3], lastTerms)}</div>
      <div class="zh">${hl(r[4], lastTerms)}</div>
    </div>`);
  }
  results.innerHTML = frag.join('');
}
let tid;
q.addEventListener('input', ()=>{ clearTimeout(tid); tid=setTimeout(search, 120); });
cat.addEventListener('change', search);
q.focus();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
