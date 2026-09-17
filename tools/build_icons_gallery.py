# -*- coding: utf-8 -*-
"""Build site/icons.html — a searchable gallery of all extracted sprite icons."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
ICON_DIR = os.path.join(SITE, "icons")

def main():
    sprites = json.load(open(os.path.join(ROOT, "data", "sprites.json"), encoding="utf-8"))
    rows = []
    for s in sprites:
        name = s["name"]
        if not name:
            continue
        p = os.path.join(ICON_DIR, name + ".png")
        if os.path.exists(p):
            rows.append([name, s["w"], s["h"], s["nframes"], os.path.getsize(p)])
    rows.sort(key=lambda r: r[0])
    payload = json.dumps(rows, separators=(",", ":"))
    print("icons in gallery:", len(rows))

    page = TEMPLATE.replace("__PAYLOAD__", payload).replace("__COUNT__", str(len(rows)))
    out = os.path.join(SITE, "icons.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print("saved ->", out)

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stoneshard 图标库 (Wiki 雏形)</title>
<style>
:root { --bg:#f6f4ef; --panel:#fffdf8; --ink:#2b2620; --muted:#8a8177; --accent:#7c5cbf; --line:#e5dfd4; }
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--ink); font-family:"Segoe UI","Microsoft YaHei",sans-serif; }
header { background:linear-gradient(135deg,#3d2f5c,#241b3a); color:#efe9ff; padding:22px 24px 18px; }
header h1 { font-size:22px; } header h1 span { color:#c9b8ff; }
header p { margin-top:6px; color:#b7a9e0; font-size:12.5px; }
header a { color:#c9b8ff; }
.wrap { max-width:1100px; margin:0 auto; padding:16px; }
.searchbar input {
  width:100%; padding:12px 16px; font-size:15px; border:1px solid var(--line);
  border-radius:10px; background:var(--panel); color:var(--ink); outline:none;
  box-shadow:0 4px 14px rgba(60,40,100,.10);
}
.searchbar input:focus { border-color:var(--accent); }
.stats { color:var(--muted); font-size:13px; margin:12px 2px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(150px,1fr)); gap:10px; }
.card {
  background:var(--panel); border:1px solid var(--line); border-radius:8px;
  padding:8px; text-align:center;
}
.card img { max-width:96px; max-height:96px; image-rendering:pixelated; margin:4px auto; display:block; }
.card .n { font-family:Consolas,monospace; font-size:10.5px; color:var(--accent); word-break:break-all; line-height:1.3; }
.card .m { font-size:10px; color:var(--muted); margin-top:3px; }
.empty { text-align:center; color:var(--muted); padding:50px 0; }
</style>
</head>
<body>
<header>
  <h1>Stoneshard <span>图标库</span></h1>
  <p>共 __COUNT__ 个精灵 · 直接从 data.win 提取 · <a href="index.html">返回文本数据库</a></p>
</header>
<div class="wrap">
  <div class="searchbar"><input id="q" placeholder="搜索精灵名，如 rusty_key / duelist / skill / inv_" autofocus></div>
  <div class="stats" id="stats"></div>
  <div class="grid" id="grid"></div>
  <div class="empty" id="hint">输入关键词筛选图标</div>
</div>
<script>
const ROWS = __PAYLOAD__;
const q = document.getElementById('q'), grid = document.getElementById('grid'),
      stats = document.getElementById('stats'), hint = document.getElementById('hint');
function render(){
  const t = q.value.trim().toLowerCase();
  if (!t) { grid.innerHTML=''; stats.textContent=''; hint.style.display=''; return; }
  hint.style.display='none';
  const hits = ROWS.filter(r => r[0].toLowerCase().includes(t)).slice(0, 300);
  stats.textContent = `命中 ${hits.length}${hits.length>=300?'+':''} 个` + (hits.length>=300?'（仅显示前 300）':'');
  grid.innerHTML = hits.map(r =>
    `<div class="card"><img loading="lazy" src="icons/${encodeURIComponent(r[0])}.png" alt="${r[0]}">
     <div class="n">${r[0]}</div><div class="m">${r[1]}×${r[2]} · ${r[3]} 帧</div></div>`).join('');
}
let tid; q.addEventListener('input', ()=>{ clearTimeout(tid); tid=setTimeout(render,120); });
q.focus();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
