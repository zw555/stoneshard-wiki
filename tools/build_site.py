"""Build the unified site:
1. slim enemies payload -> site/enemies.html (from tools/enemies_template.html)
2. inject shared top nav into index.html / items.html / icons.html
Run after build_preview.py / build_icons_gallery.py / build_linkage.py.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _nav import inject_nav  # noqa: E402  共享导航（planner/caravan 构建脚本也用它）

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE = os.path.join(ROOT, "site")
TOOLS = os.path.dirname(os.path.abspath(__file__))


def slim_enemies():
    d = json.load(open(os.path.join(DATA, "community_enemies.json"), encoding="utf-8"))
    out = []
    for e in d["enemies"]:
        # 技能：只保留中英描述（描述无 /*KEY*/ 占位符，无需公式引擎）
        sk = [{"id": s.get("id", ""), "zh": s.get("name", ""), "en": s.get("name_en", ""),
               "dz": (s.get("descs") or {}).get("zh", ""),
               "de": (s.get("descs") or {}).get("en", ""),
               "kind": s.get("kind", "")} for s in e.get("skills") or []]
        # 掉落：多候选全部展开（同一掉落脚本可能掉不同品质物品）
        dp = []
        for dd in e.get("drops") or []:
            for c in dd.get("candidates") or []:
                nm = c.get("names") or {}
                if not nm.get("zh") and not nm.get("en"):
                    continue
                dp.append({"zh": nm.get("zh", ""), "en": nm.get("en", ""),
                           "ic": (c.get("icon") or "").replace("_0.png", ".png"),
                           "ch": dd.get("chance")})
        out.append({
            "id": e.get("id", ""),
            "en": e.get("name", ""),
            "zh": (e.get("names") or {}).get("zh", ""),
            "fa": ((e.get("faction_names") or {}).get("zh")
                   or (e.get("faction_names") or {}).get("en") or e.get("faction", "")),
            "rk": e.get("rank") or 0,
            "ic": (e.get("sprite") or "").replace("_0.png", ".png"),
            "st": e.get("stats") or {},
            "sk": sk,
            "dp": dp,
            "bs": bool(e.get("is_boss")),
        })
    out.sort(key=lambda x: (x["fa"], x["rk"], x["en"].lower()))
    return out


def main():
    enemies = slim_enemies()
    tpl = open(os.path.join(TOOLS, "enemies_template.html"), encoding="utf-8").read()
    html = tpl.replace("__DATA__", json.dumps(enemies, ensure_ascii=False))
    with open(os.path.join(SITE, "enemies.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("enemies:", len(enemies), "-> site/enemies.html")

    for page in ("index.html", "items.html", "skills.html", "planner.html", "enemies.html", "trade.html", "caravan.html", "icons.html"):
        inject_nav(page, page)


if __name__ == "__main__":
    main()
