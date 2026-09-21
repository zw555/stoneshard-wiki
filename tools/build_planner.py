"""Build the planner (build-out) page data.

Sources (all previously scraped / reverse-engineered, see AGENT.md):
- data/community_wiki_zh.json            items with planner-format stat_groups/damages (raw_key + zh labels)
- data/community_planner_item_modifiers.json  enchantments / curses with numeric effects
- data/community_planner_buffs.json      activatable skill buffs (28 resolved activations)
- data/community_planner_character_stats.json  the in-game character panel layout (82 stats / 4 groups)

Output: site/planner_data.js -> window.PD = {items, ench, curse, buffs, rows, keyZh, dmgZh, curseMult}
The page itself (tools/planner_template.html) implements the stat engine (port of the
community planner's kr() function, which replicates the game's own formulas).
"""
import json, os, re, collections, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _nav import inject_nav  # noqa: E402  生成页面后自注入导航，避免被 build_site 覆盖/漏注入

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE = os.path.join(ROOT, "site")

# section -> (slot, category)   category: 1h / 2h / ranged / shield / ammo / gear / jewelry
SECTION_MAP = {
    "SWORDS": ("weapon", "1h"), "AXES": ("weapon", "1h"), "MACES": ("weapon", "1h"),
    "DAGGERS": ("weapon", "1h"),
    "2H SWORDS": ("weapon", "2h"), "2H AXES": ("weapon", "2h"), "2H MACES": ("weapon", "2h"),
    "SPEARS": ("weapon", "2h"), "STAVES": ("weapon", "2h"),
    "BOWS": ("weapon", "ranged"), "XBOWS": ("weapon", "ranged"), "SLINGS": ("weapon", "ranged"),
    "SHIELDS": ("offhand", "shield"),
    "AMMO": ("ammo", "ammo"), "QUIVERS": ("ammo", "ammo"),
    "HELMETS": ("head", "gear"), "ARMORS": ("chest", "gear"), "CLOAKS": ("cloak", "gear"),
    "BELTS": ("belt", "gear"), "GLOVES": ("hands", "gear"), "BOOTS": ("boots", "gear"),
    "NECKLACES": ("neck", "jewelry"), "RINGS": ("ring", "jewelry"),
}
BLOCK_F = {"SWORDS": 1.1, "AXES": 0.75, "MACES": 0.75, "DAGGERS": 0.5,
           "2H SWORDS": 1.25, "STAFFS": 0.9, "SPEARS": 1.0, "2H AXES": 0.85, "2H MACES": 0.9}

NUM_RE = re.compile(r"^([+-]?\d+(?:\.\d+)?)")


def num(v):
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    m = NUM_RE.match(str(v).strip().replace(",", "."))
    return float(m.group(1)) if m else 0.0


def main():
    wiki = json.load(open(os.path.join(DATA, "community_wiki_zh.json"), encoding="utf-8"))
    mods = json.load(open(os.path.join(DATA, "community_planner_item_modifiers.json"), encoding="utf-8"))
    buffs = json.load(open(os.path.join(DATA, "community_planner_buffs.json"), encoding="utf-8"))
    panel = json.load(open(os.path.join(DATA, "community_planner_character_stats.json"), encoding="utf-8"))

    # ---- items -------------------------------------------------------------
    zh2key = {}
    for k, v in mods["modifierLabels"].items():
        if v.get("zh"):
            zh2key[v["zh"]] = k
    items, skipped, unmapped = [], collections.Counter(), collections.Counter()
    seen = set()
    for it in wiki["items"]:
        sec = (it.get("section") or "").strip()
        if sec not in SECTION_MAP or it["id"] in seen:
            continue
        seen.add(it["id"])
        slot, cat = SECTION_MAP[sec]
        dmg = collections.defaultdict(float)
        for d in it.get("damages") or []:
            k = d.get("raw_key") or zh2key.get(d.get("labels", {}).get("zh", ""))
            if k:
                dmg[k] += num(d.get("val"))
        st = collections.defaultdict(float)
        for grp in it.get("stat_groups") or []:
            if not isinstance(grp, list):
                continue
            for s in grp:
                k = s.get("raw_key")
                if not k:
                    unmapped[s.get("labels", {}).get("zh") or s.get("k")] += 1
                    continue
                st[k] += num(s.get("v"))
        icon = "icons/" + (it.get("image") or "")
        if not os.path.exists(os.path.join(SITE, icon)):
            icon = ""
        items.append({
            "id": it["id"], "zh": it.get("name") or it.get("name_en"), "en": it.get("name_en"),
            "slot": slot, "cat": cat, "sec": sec,
            "tier": it.get("tier") or "", "rar": it.get("rarity_zh") or "",
            "type": it.get("type_text") or "", "icon": icon,
            "dmg": dict(dmg), "st": dict(st),
        })
    items.sort(key=lambda x: (x["slot"], x.get("tier") or "", x["zh"] or ""))
    print("items:", len(items), "skipped sections:", dict(skipped), "unmapped stat labels:", dict(unmapped))

    # ---- enchantments & curses --------------------------------------------
    ench = [{"id": e["id"], "zh": (e.get("prefixNames") or {}).get("zh") or e["id"],
             "mt": e.get("metatypes") or [],
             "fx": [{"k": f["key"], "v": float(f["value"]), "m": f.get("mode", "flat")} for f in e.get("effects") or []]}
            for e in mods["enchantments"]]
    curse = [{"id": c["id"], "zh": (c.get("names") or {}).get("zh") or c["id"],
              "mt": c.get("metatypes") or [],
              "fx": [{"k": f["key"], "v": float(f["value"]), "m": f.get("mode", "flat")} for f in c.get("effects") or []]}
             for c in mods["curses"]]
    curse_mult = float(mods.get("curse_enchantment_multiplier") or 0.75)
    print("enchants:", len(ench), "curses:", len(curse), "curse_mult:", curse_mult)

    # ---- activatable skill buffs -------------------------------------------
    fx_by_id = {f["id"]: f for f in buffs["effects"]}
    bl, skipped_buffs = [], 0
    for a in buffs["activations"]:
        f = fx_by_id.get(a.get("effect_id"))
        if not f or not f.get("visible"):
            skipped_buffs += 1
            continue
        mlist = []
        ok = True
        for m in f.get("modifiers") or []:
            if "values_by_stage" in m and m["values_by_stage"]:
                vs = {int(k): float(v) for k, v in m["values_by_stage"].items() if isinstance(v, (int, float))}
                if not vs:
                    ok = False
                    break
                mlist.append({"k": m["key"], "u": m.get("unit", "percent"), "vs": vs})
            elif isinstance(m.get("value"), (int, float)):
                mlist.append({"k": m["key"], "u": m.get("unit", "percent"), "vs": {1: float(m["value"])}})
            else:
                ok = False
                break
        if not ok or not mlist:
            skipped_buffs += 1
            continue
        src = a.get("source") or {}
        bl.append({"id": a["id"], "zh": (src.get("names") or {}).get("zh") or src.get("id") or a["id"],
                   "src": src.get("kind") or "skill", "max": int((f.get("stage") or {}).get("max") or 1),
                   "def": int((f.get("stage") or {}).get("default") or 1), "m": mlist})
    bl.sort(key=lambda x: x["zh"])
    print("buffs:", len(bl), "skipped:", skipped_buffs)

    # ---- panel layout + key labels -----------------------------------------
    rows = [r for r in panel["rows"] if r["type"] in ("header", "stat", "space")]
    key_zh = {}
    for r in rows:
        if r["type"] == "stat":
            key_zh[r["key"]] = (r.get("label") or {}).get("zh") or r["key"]
    for k, v in mods["modifierLabels"].items():
        key_zh.setdefault(k, v.get("zh") or k)
    dmg_zh = {}
    for it in wiki["items"]:
        for d in it.get("damages") or []:
            if d.get("raw_key") and d.get("labels", {}).get("zh"):
                dmg_zh.setdefault(d["raw_key"], d["labels"]["zh"])
    key_zh.setdefault("BlockPowerBonus", "格挡强度加成")
    key_zh.setdefault("max_hp", "最大生命力")
    key_zh.setdefault("max_mp", "最大法力值")

    out = {
        "items": items, "ench": ench, "curse": curse, "buffs": bl,
        "rows": rows, "keyZh": key_zh, "dmgZh": dmg_zh,
        "curseMult": curse_mult, "blockF": BLOCK_F,
    }
    js = "window.PD=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"
    with open(os.path.join(SITE, "planner_data.js"), "w", encoding="utf-8") as f:
        f.write(js)
    print("wrote site/planner_data.js (%.1f KB)" % (len(js.encode("utf-8")) / 1024))

    tpl = open(os.path.join(ROOT, "tools", "planner_template.html"), encoding="utf-8").read()
    with open(os.path.join(SITE, "planner.html"), "w", encoding="utf-8") as f:
        f.write(tpl)
    inject_nav("planner.html", "planner.html")  # 自身带导航，不依赖 build_site 的执行顺序
    print("wrote site/planner.html")


if __name__ == "__main__":
    main()
