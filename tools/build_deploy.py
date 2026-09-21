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


def referenced():
    need = set()
    for f in PAGES:
        h = open(os.path.join(SITE, f), encoding="utf-8").read()
        need |= set(re.findall(r'icons/([A-Za-z0-9_@.\-]+\.png)', h))
    return need


def main():
    need = referenced()
    stems = {n[:-4] for n in need}
    if "--prune-all" in sys.argv and os.path.exists(DEPLOY):
        shutil.rmtree(DEPLOY)
    os.makedirs(os.path.join(DEPLOY, "icons"), exist_ok=True)

    for f in PAGES + EXTRA_FILES:
        shutil.copy2(os.path.join(SITE, f), os.path.join(DEPLOY, f))

    # 图标：复制被引用的（同尺寸则跳过），清理不再被引用的
    copied, stale = 0, 0
    icon_dir = os.path.join(DEPLOY, "icons")
    for n in need:
        src = os.path.join(SITE, "icons", n)
        dst = os.path.join(icon_dir, n)
        if not os.path.exists(src):
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
    print("pages:", len(PAGES) + 1, "| icons copied:", copied, "| icons pruned:", stale, "| gallery rows:", len(kept), "/", len(rows))
    print("deploy size: %.1f MB" % (total / 1048576))


if __name__ == "__main__":
    main()
