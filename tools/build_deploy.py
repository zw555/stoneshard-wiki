"""Build a slim deploy folder: site_deploy/
- core pages (index / items / skills / enemies / trade)
- only the icons referenced by those pages
- icons.html rebuilt from ROWS filtered to the referenced sprites
"""
import json, os, re, shutil

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
    if os.path.exists(DEPLOY):
        shutil.rmtree(DEPLOY)
    os.makedirs(os.path.join(DEPLOY, "icons"), exist_ok=True)

    for f in PAGES + EXTRA_FILES:
        shutil.copy2(os.path.join(SITE, f), os.path.join(DEPLOY, f))

    copied = 0
    for n in need:
        src = os.path.join(SITE, "icons", n)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(DEPLOY, "icons", n))
            copied += 1

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
    print("pages:", len(PAGES) + 1, "| icons copied:", copied, "| gallery rows:", len(kept), "/", len(rows))
    print("deploy size: %.1f MB" % (total / 1048576))


if __name__ == "__main__":
    main()
