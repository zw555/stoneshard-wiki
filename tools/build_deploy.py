"""Build a slim deploy folder: site_deploy/
- core pages (index / items / skills / enemies / trade / planner / caravan)
- only the icons referenced by those pages
- icons.html rebuilt from ROWS filtered to the referenced sprites

增量同步：不再整目录 rmtree（会触发批量删除保护），改为逐文件比对复制 +
仅清理不再被引用的图标。加 --prune-all 可强制清空重建。
"""
import json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
DEPLOY = os.path.join(ROOT, "site_deploy")
PAGES = ["index.html", "items.html", "skills.html", "enemies.html", "trade.html", "planner.html", "caravan.html"]
EXTRA_FILES = ["planner_data.js"]


RE_ICON_STATIC = re.compile(r'icons/([A-Za-z0-9_@.\-]+\.png)')
RE_ICON_JSON = re.compile(r'"ic"\s*:\s*"([A-Za-z0-9_@.\-]+\.png)"')


def referenced():
    """页面引用到的图标名。

    必须同时扫「静态路径」和「JSON 里的 ic 字段」：skills / enemies / trade 的图标
    是 JS 运行时拼 `icons/${x.ic}` 的，页面上没有字面路径，只扫静态会漏掉一大半
    （历史上 skills 漏 101 个、enemies 漏 239 个，线上表现为图标空白）。
    """
    need = set()
    for f in PAGES + EXTRA_FILES:
        p = os.path.join(SITE, f)
        if not os.path.exists(p):
            continue
        h = open(p, encoding="utf-8", errors="ignore").read()
        need |= set(RE_ICON_STATIC.findall(h))
        need |= set(RE_ICON_JSON.findall(h))
    return need


def main():
    need = referenced()
    stems = {n[:-4] for n in need}
    if "--prune-all" in sys.argv and os.path.exists(DEPLOY):
        shutil.rmtree(DEPLOY)
    os.makedirs(os.path.join(DEPLOY, "icons"), exist_ok=True)

    # 大小写审计：Windows 上「引用名与真实文件名大小写不符」完全看不出来
    # （exists/复制都不报错），线上 Linux 却是 404。这里主动报出来。
    real = set(os.listdir(os.path.join(SITE, "icons")))
    low = {}
    for n in real:
        low.setdefault(n.lower(), n)
    case_bad = [n for n in sorted(need) if n not in real and n.lower() in low]
    absent = [n for n in sorted(need) if n.lower() not in low]

    for f in PAGES + EXTRA_FILES:
        shutil.copy2(os.path.join(SITE, f), os.path.join(DEPLOY, f))

    # 图标：复制被引用的（同尺寸则跳过），清理不再被引用的
    copied, stale, missing = 0, 0, 0
    icon_dir = os.path.join(DEPLOY, "icons")
    for n in need:
        src = os.path.join(SITE, "icons", n)
        dst = os.path.join(icon_dir, n)
        if not os.path.exists(src):
            missing += 1
            continue
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
            continue
        shutil.copy2(src, dst)
        copied += 1
    for n in os.listdir(icon_dir):
        if n not in need:
            os.remove(os.path.join(icon_dir, n))
            stale += 1

    # slim icons gallery
    h = open(os.path.join(SITE, "icons.html"), encoding="utf-8").read()
    m = re.search(r"const ROWS = (\[.*?\]);", h, re.S)
    rows = json.loads(m.group(1))
    kept = [r for r in rows if r[0] in stems]
    h2 = h[: m.start(1)] + json.dumps(kept, ensure_ascii=False) + h[m.end(1):]
    h2 = h2.replace("全部 ", "").replace("<title>", "<title>")
    with open(os.path.join(DEPLOY, "icons.html"), "w", encoding="utf-8") as f:
        f.write(h2)

    total = sum(os.path.getsize(os.path.join(DEPLOY, "icons", n)) for n in os.listdir(os.path.join(DEPLOY, "icons")))
    print("pages:", len(PAGES) + 1, "| icons copied:", copied, "| icons pruned:", stale,
          "| icons missing in site/icons:", missing, "| gallery rows:", len(kept), "/", len(rows))
    if case_bad:
        print("!! 图标名大小写不符（Linux 上会 404）:", len(case_bad), "如", case_bad[:3])
    if absent:
        print("!! 图标文件不存在:", len(absent), "如", absent[:3])
    print("deploy size: %.1f MB" % (total / 1048576))


if __name__ == "__main__":
    main()
