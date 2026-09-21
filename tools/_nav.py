"""共享顶部导航：定义 + 注入。

任何会重新生成某个页面的构建脚本，都应在写盘后调用 inject_nav(page, active)，
否则该页面的导航会被模板覆盖掉（历史上 planner / caravan 都踩过这个坑）。

用法：
    from _nav import inject_nav
    inject_nav("caravan.html", "caravan.html")
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")

NAV = """
<nav class="ssw-nav">
  <div class="ssw-nav-inner">
    <a class="ssw-brand" href="index.html">Stoneshard 中文资料库</a>
    <a href="index.html" data-p="index.html">全文搜索</a>
    <a href="items.html" data-p="items.html">物品图鉴</a>
    <a href="skills.html" data-p="skills.html">技能树</a>
    <a href="planner.html" data-p="planner.html">配装规划</a>
    <a href="enemies.html" data-p="enemies.html">敌人图鉴</a>
    <a href="trade.html" data-p="trade.html">交易行情</a>
    <a href="caravan.html" data-p="caravan.html">马车营地</a>
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


def inject_nav(page, active=None, site=None):
    """把共享导航插入 site/<page> 的 <body> 之后（重复注入会先移除旧块）。"""
    site = site or SITE
    p = os.path.join(site, page)
    if not os.path.exists(p):
        print("skip missing", page)
        return False
    h = open(p, encoding="utf-8").read()
    nav = NAV
    if active:
        nav = nav.replace(f'data-p="{active}"', f'class="ssw-on" data-p="{active}"')
    if 'class="ssw-nav"' in h:  # 已注入过 -> 移除旧块，避免重复
        h = re.sub(r'<nav class="ssw-nav">.*?</style>', "", h, flags=re.S)
    if "<body>" in h:
        h = h.replace("<body>", "<body>" + nav, 1)
    else:
        h = nav + h
    with open(p, "w", encoding="utf-8") as f:
        f.write(h)
    print("nav ->", page)
    return True


def inject_all(pages, site=None):
    for pg in pages:
        inject_nav(pg, pg, site=site)
