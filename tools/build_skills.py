"""Build site/skills.html from community wiki dataset (data/community_wiki_zh.json,
data/community_skill_books.json).

Skill nodes: 238 items with is_skill_tree_node, grouped by skill_tree_key,
positioned by visual_x / visual_y (in-game tree layout), requirements from
skill_tree_position (unlock_tier / level_to_open / attributes).
"""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE = os.path.join(ROOT, "site")
TOOLS = os.path.dirname(os.path.abspath(__file__))

ATTR_ZH = {"STR": "力量", "AGL": "敏捷", "PRC": "感知", "VIT": "活力",
           "WIL": "意志", "Vitality": "活力", "Perception": "感知"}


def icon_of(image):
    if not image:
        return ""
    return image.replace("_0.png", ".png")


def main():
    wiki = json.load(open(os.path.join(DATA, "community_wiki_zh.json"), encoding="utf-8"))
    books = json.load(open(os.path.join(DATA, "community_skill_books.json"), encoding="utf-8"))["books"]

    nodes = [i for i in wiki["items"] if i.get("is_skill_tree_node")]

    # books by tree key
    books_by_tree = collections.defaultdict(list)
    for b in books:
        k = b.get("skill_tree_canonical_key") or b.get("skill_tree_key")
        if k:
            books_by_tree[k].append({
                "id": b.get("id"), "zh": (b.get("names") or {}).get("zh", ""),
                "en": (b.get("names") or {}).get("en", ""),
                "desc": (b.get("descs") or {}).get("zh", ""),
                "unlock": [u for u in (b.get("unlock_skill_names") or [])],
            })

    branches = collections.defaultdict(lambda: {"nodes": [], "group": "", "name": ""})
    for n in nodes:
        key = n.get("skill_tree_key") or "misc"
        pos = n.get("skill_tree_position") or {}
        br = branches[key]
        br["group"] = n.get("L2") or ""
        br["name"] = n.get("L3") or n.get("L1") or key
        attrs = []
        if pos.get("attributes_names_to_open"):
            attrs = [ATTR_ZH.get(a, a) for a in pos["attributes_names_to_open"]]
        br["nodes"].append({
            "id": n.get("id"), "zh": n.get("name", ""), "en": n.get("name_en", ""),
            "desc": n.get("desc", ""), "ic": icon_of(n.get("image")),
            "tier": pos.get("unlock_tier") or 0,
            "lv": pos.get("level_to_open") or 0,
            "attr": attrs, "attrv": pos.get("attributes_value_to_open") or 0,
            "x": pos.get("visual_x") or 0, "y": pos.get("visual_y") or 0,
            "branch": pos.get("branch") or "",
        })
        # per-node placeholder formulas (reverse-engineered GML from the game)
        f = {fr["key"]: fr["display_expression"].strip()
             for fr in (n.get("formula_refs") or []) if fr.get("display_expression")}
        if f:
            br["nodes"][-1]["f"] = f

    for k, br in branches.items():
        br["nodes"].sort(key=lambda n: (n["tier"], n["y"], n["x"]))
        br["books"] = books_by_tree.get(k, [])

    # order branches: by group order then branch order from the game data
    order = {}
    for n in nodes:
        k = n.get("skill_tree_key")
        if k and k not in order:
            p = n.get("skill_tree_position") or {}
            order[k] = (n.get("skill_tree_group_order") or 99, n.get("skill_tree_order") or 99)
    payload = [{"key": k, "name": br["name"], "group": br["group"],
                "books": br["books"], "nodes": br["nodes"]}
               for k, br in sorted(branches.items(), key=lambda kv: order.get(kv[0], (99, 99)))]

    # branch icons: use first node icon of each branch
    for b in payload:
        b["icon"] = b["nodes"][0]["ic"] if b["nodes"] else ""

    tpl = open(os.path.join(TOOLS, "skills_template.html"), encoding="utf-8").read()
    formulas = json.load(open(os.path.join(DATA, "formulas.json"), encoding="utf-8"))
    html = tpl.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
    html = html.replace("__FORMULAS__", json.dumps(formulas["by_key"], ensure_ascii=False, sort_keys=True))
    out = os.path.join(SITE, "skills.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    total = sum(len(b["nodes"]) for b in payload)
    print("branches:", len(payload), "| nodes:", total, "| books:", len(books))
    print("groups:", collections.Counter(b["group"] for b in payload))
    print("wrote", out)


if __name__ == "__main__":
    main()
