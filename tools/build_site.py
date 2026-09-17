"""Build the unified site:
1. slim enemies payload -> site/enemies.html (from tools/enemies_template.html)
2. inject shared top nav into index.html / items.html / icons.html
Run after build_preview.py / build_icons_gallery.py / build_linkage.py.
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE = os.path.join(ROOT, "site")
TOOLS = os.path.dirname(os.path.abspath(__file__))

NAV = """
<nav class="ssw-nav">
  <div class="ssw-nav-inner">
    <a class="ssw-brand" href="index.html">Stoneshard 中文资料库</a>
    <a href="index.html" data-p="index.html">全文搜索</a>
    <a href="items.html" data-p="items.html">物品图鉴</a>
    <a href="skills.html" data-p="skills.html">技能树</a>
    <a href="enemies.html" data-p="enemies.html">敌人图鉴</a>
    <a href="trade.html" data-p="trade.html">交易行情</a>
    <a href="icons.html" data-p="icons.html">图标库</a>
  </div>
</nav>
<style>
  .ssw-nav { background:#2c2a26; position:sticky; top:0; z-index:50; }
  .ssw-nav-inner { max-width:1200px; margin:0 auto; display:flex; align-items:center; gap:6px; padding:0 16px; height:48px; flex-wrap:wrap; }
  .ssw-nav a { color:#cfc9bc; text-decoration:none; font-size:14px; padding:6px 12px; border-radius:6px; }
  .ssw-nav a:hover { background:#3d3a34; color:#fff; }
  .ssw-nav a.ssw-on { background:#7a4b2a; color:#fff; }
  .ssw-brand { font-weight:700; color:#fff !important; margin-right:14px; }
  @media (max-width: 720px) { .ssw-nav-inner { height:auto; padding:6px 12px; } }
</style>
"""


def slim_enemies():
    d = json.load(open(os.path.join(DATA, "community_enemies.json"), encoding="utf-8"))
    out = []
    for e in d["enemies"]:
        out.append({
            "id": e.get("id", ""),
            "en": e.get("name", ""),
            "zh": (e.get("names") or {}).get("zh", ""),
            "fa": ((e.get("faction_names") or {}).get("zh")
                   or (e.get("faction_names") or {}).get("en") or e.get("faction", "")),
            "rk": e.get("rank") or 0,
            "ic": (e.get("sprite") or "").replace("_0.png", ".png"),
            "st": e.get("stats") or {},
        })
    out.sort(key=lambda x: (x["fa"], x["rk"], x["en"].lower()))
    return out


def inject_nav(page, active):
    p = os.path.join(SITE, page)
    if not os.path.exists(p):
        print("skip missing", page)
        return
    h = open(p, encoding="utf-8").read()
    nav = NAV.replace(f'data-p="{active}"', f'class="ssw-on" data-p="{active}"')
    if 'class="ssw-nav"' in h:  # already injected -> replace old nav block
        h = re.sub(r'<nav class="ssw-nav">.*?</style>', "", h, flags=re.S)
    if "<body>" in h:
        h = h.replace("<body>", "<body>" + nav, 1)
    else:
        h = nav + h
    with open(p, "w", encoding="utf-8") as f:
        f.write(h)
    print("nav ->", page)


def main():
    enemies = slim_enemies()
    tpl = open(os.path.join(TOOLS, "enemies_template.html"), encoding="utf-8").read()
    html = tpl.replace("__DATA__", json.dumps(enemies, ensure_ascii=False))
    with open(os.path.join(SITE, "enemies.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("enemies:", len(enemies), "-> site/enemies.html")

    for page in ("index.html", "items.html", "skills.html", "enemies.html", "trade.html", "icons.html"):
        inject_nav(page, page)


if __name__ == "__main__":
    main()
