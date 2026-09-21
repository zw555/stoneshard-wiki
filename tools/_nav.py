"""全站统一外壳：顶部导航 + 页头 + 内容容器（单一真源）。

任何会重新生成某个页面的构建脚本，都应在写盘后调用 inject_nav(page, active)，
否则该页面的导航/页头会被模板里的旧样式覆盖掉（历史上 planner / caravan 都踩过这个坑）。

统一约定（只改本文件 = 全站生效）：
  1. body 不留内外边距；导航与页头满宽（通栏），宽度靠 inner 的 1200px + 24px 内边距收敛；
  2. 内容容器统一 max-width:1200px / margin:0 auto / padding:0 24px；
     这样「页头文字左边线」与「正文内容左边线」在任意视口宽度下都严格对齐；
  3. 页头统一结构 <header class="ssw-head"><div class="ssw-head-inner"><h1>…</h1><div class="ssw-sub">…；
     页面里原有的 <header>（紫渐变 / 白底 / .meta 三种写法）会被自动重写成上面的结构，
     标题与副标题从原内容里原样搬运，因此不需要改 8 个模板。

用法：
    from _nav import inject_nav
    inject_nav("caravan.html", "caravan.html")
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")

# 导航链接：(文件名, 显示名)
LINKS = [
    ("index.html", "全文搜索"),
    ("items.html", "物品图鉴"),
    ("skills.html", "技能树"),
    ("planner.html", "配装规划"),
    ("enemies.html", "敌人图鉴"),
    ("trade.html", "交易行情"),
    ("caravan.html", "马车营地"),
    ("icons.html", "图标库"),
]

NAV = """
<nav class="ssw-nav">
  <div class="ssw-nav-inner">
    <a class="ssw-brand" href="index.html">Stoneshard 中文资料库</a>
%s
  </div>
</nav>
<style>
  /* ================= 全站统一外壳 · 请勿在单页重复定义这里的规则 ================= */
  :root { --ssw-ink:#2c2a26; --ssw-sub:#6f695c; --ssw-line:#e2ddd2; --ssw-acc:#7a4b2a; }
  body { margin:0; padding:0; }
  /* 恒定显示滚动条：否则「内容短、无滚动条」的页面可用宽多出 15px，
     居中的 1200px 容器会横向偏移 ~7.5px，切换页面时正文左右跳动。
     （不用 scrollbar-gutter:stable —— 它只在排版上留槽、不绘制滚动条，
       深色导航条右侧会露出一条未绘制的白缝。） */
  html { overflow-y:scroll; }

  /* --- 顶部导航（通栏深色条） --- */
  .ssw-nav { background:#2c2a26; position:sticky; top:0; z-index:60; }
  .ssw-nav-inner { max-width:1200px; margin:0 auto; padding:0 24px; height:48px;
                   display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
  .ssw-nav a { color:#cfc9bc; text-decoration:none; font-size:14px; padding:6px 12px; border-radius:6px; }
  .ssw-nav a:hover { background:#3d3a34; color:#fff; }
  .ssw-nav a.ssw-on { background:var(--ssw-acc); color:#fff; }
  .ssw-nav .ssw-brand { font-weight:700; color:#fff; margin-right:14px; }

  /* --- 页头（通栏白条 + 底边线） --- */
  .ssw-head { max-width:none; margin:0 0 18px; padding:0; background:#fff; border-bottom:1px solid var(--ssw-line); }
  .ssw-head-inner { max-width:1200px; margin:0 auto; padding:20px 24px 16px; }
  .ssw-head h1 { font-size:22px; font-weight:700; color:var(--ssw-ink); margin:0 0 7px;
                 line-height:1.35; letter-spacing:.2px; }
  .ssw-head h1 span { color:#8a7b5c; font-weight:600; }
  .ssw-head .ssw-sub { color:var(--ssw-sub); font-size:13px; line-height:1.7; }
  .ssw-head .ssw-sub a { color:#8a5a33; }
  .ssw-head .ssw-stats { display:flex; flex-wrap:wrap; gap:10px; margin-top:11px; }
  .ssw-head .ssw-stat { background:#faf7f1; border:1px solid var(--ssw-line); border-radius:9px; padding:6px 13px; }
  .ssw-head .ssw-stat b { display:block; font-size:17px; color:var(--ssw-acc); }
  .ssw-head .ssw-stat span { color:#8a857a; font-size:12px; }

  /* --- 内容容器：让正文与页头左右对齐（body 直接子元素） --- */
  body > :not(.ssw-nav):not(.ssw-head):not(style):not(script):not(dialog):not(#tip) {
    max-width:1200px; margin-left:auto; margin-right:auto;
    padding-left:24px; padding-right:24px;
  }

  @media (max-width:720px) { .ssw-nav-inner { height:auto; padding:8px 16px; } }
</style>
"""

# 页头标准结构（所有页面共用）。title 里可用 <span> 标注副题。
HEAD_TMPL = """<header class="ssw-head">
  <div class="ssw-head-inner">
    <h1>{title}</h1>
{sub}  </div>
</header>"""


def ssw_head(title, sub="", extra=""):
    """生成统一的页面头部。"""
    body = ('    <div class="ssw-sub">%s</div>\n' % sub) if sub else ""
    if extra:
        body += extra.rstrip("\n") + "\n"
    return HEAD_TMPL.format(title=title, sub=body)


HEAD_RE = re.compile(r"<header[^>]*>(.*?)</header>", re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
SUB_RES = (
    re.compile(r'<div[^>]*class="[^"]*\bssw-sub\b[^"]*"[^>]*>(.*?)</div>', re.S),
    re.compile(r'<p[^>]*>(.*?)</p>', re.S),
    re.compile(r'<div[^>]*class="[^"]*\bmeta\b[^"]*"[^>]*>(.*?)</div>', re.S),
)


def normalize_head(h):
    """把页面自带的 <header> 重写成统一结构（可重复执行）。

    只搬走 h1 与副标题（.ssw-sub / <p> / .meta），页头里的其它内容（如 caravan 的
    .stats 统计块，其 id 被页面 JS 引用）原样保留在 .ssw-head-inner 内 —— 早先
    整块替换曾把 caravan 的 #st-mats 一并删掉，导致该页 JS 抛错、整页失效。
    """
    m = HEAD_RE.search(h)
    if not m:
        return h, False
    inner = m.group(1)

    # 已是统一结构时先剥掉 .ssw-head-inner 外壳（可能套了多层），否则重复注入会层层套娃
    while True:
        w = re.search(r'<div[^>]*class="[^"]*\bssw-head-inner\b[^"]*"[^>]*>(.*)</div>', inner, re.S)
        if not w:
            break
        inner = w.group(1)

    t = H1_RE.search(inner)
    if not t:
        return h, False

    sub, sub_span = "", None
    for rx in SUB_RES:
        s = rx.search(inner)
        if s:
            sub, sub_span = s.group(1).strip(), s.span()
            break

    cuts = sorted([t.span()] + ([sub_span] if sub_span else []))
    rest, prev = "", 0
    for a, b in cuts:
        rest += inner[prev:a]
        prev = b
    rest += inner[prev:]
    rest = rest.strip()

    return h[:m.start()] + ssw_head(t.group(1).strip(), sub, rest) + h[m.end():], True


def _build_nav(active):
    items = []
    for f, label in LINKS:
        on = ' class="ssw-on"' if f == active else ""
        items.append('    <a href="%s"%s data-p="%s">%s</a>' % (f, on, f, label))
    return NAV % "\n".join(items)


def inject_nav(page, active=None, site=None):
    """把共享导航 + 统一外壳写入 site/<page>（重复注入会先移除旧块，幂等）。"""
    site = site or SITE
    p = os.path.join(site, page)
    if not os.path.exists(p):
        print("skip missing", page)
        return False
    h = open(p, encoding="utf-8").read()

    if 'class="ssw-nav"' in h:  # 已注入过 -> 先移除旧块，避免重复堆积
        h = re.sub(r'\n?<nav class="ssw-nav">.*?</style>\n?', "\n", h, flags=re.S)
    h, had_head = normalize_head(h)

    nav = _build_nav(active)
    m = re.search(r"<body[^>]*>", h)
    if m:
        h = h[:m.end()] + "\n" + nav + h[m.end():]
    else:
        h = nav + h
    with open(p, "w", encoding="utf-8") as f:
        f.write(h)
    print("nav ->", page, "(head normalized)" if had_head else "(no header found)")
    return True


def inject_all(pages, site=None):
    for pg in pages:
        inject_nav(pg, pg, site=site)
