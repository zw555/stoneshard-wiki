"""Link localization text with sprite icons -> data/items.json + site/items.html.

Join strategy:
  sprite name (s_inv_rusty_key) -> normalized query ("rusty key")
  -> case-insensitive lookup in localization keys (with a no-space fallback map).
Heuristics for unmatched: strip segment prefixes (goods_/recipe_/trophy_...),
strip state suffixes (_rot/_piece/_half/_cooked), split camelCase, retry.
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE = os.path.join(ROOT, "site")

PREFIXES = ["s_inv_", "s_skills_", "s_spell_"]
SEG_PREFIXES = ["goods", "recipe", "appearance", "treasure", "lore", "quest", "book", "potion", "scroll"]
STATE_SUFFIXES = ["_cooked_rot", "_cooked", "_rot", "_piece", "_half", "_burnt"]


def split_camel(s):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)


def candidates(rest):
    """Yield possible normalized English-name queries for a sprite rest-name."""
    base = rest
    # strip segment prefix (first segment if it is a known container prefix)
    first, _, tail = base.partition("_")
    if first.lower() in SEG_PREFIXES and tail:
        base = tail
    # split camelCase inside segments: goods_Coal -> Coal
    base = split_camel(base)
    out = []
    for b in [base] + [base.rsplit("_", 1)[0] for _ in [0]]:  # with / without last segment
        for s in [b, re.sub(r"_(rot|cooked|piece|half|burnt)$", "", b, flags=re.I)]:
            q = s.lower().replace("_", " ").strip()
            if q and q not in out:
                out.append(q)
    return out


# 人工映射表：精灵名（去 s_skills_/s_inv_ 前缀）-> 实际 key（用于游戏内部 typo 等）
MANUAL_MAP = {
    "riposite": "Riposte",
    "supression": "Suppression",
    "glutonny": "Gluttony",
    "inceneration": "Incineration",
    "mightly_swing": "Mighty Swing",
    "unstopable_force": "Unstoppable Force",
    "massressurection": "Mass Resurrection",
    "ressurection": "Resurrection",
    "sacrifacialblood": "Sacrificial Blood",
    "sigilofdarkness": "Sigil of Darkness",
    "ball_lighting": "Ball Lightning",
    "explodingflesh": "Exploding Flesh",
    "choppinglunge": "Chopping Lunge",
    "piercethroughmissle": "Pierce Through Missile",
    "vampiricrune": "Vampiric Rune",
    "passive_binding_rune": "Binding Rune",
    "passive_engulfing_rune": "Engulfing Rune",
    "passive_fortyfying_rune": "Fortifying Rune",
    "passive_impact_rune": "Impact Rune",
    "passive_power_rune": "Power Rune",
    "passive_supporting_rune": "Supporting Rune",
    "passive_weakening_rune": "Weakening Rune",
    "terrifying_shriek": "Terrifying Shriek",
    "blessed_be_the_dead": "Blessed Be the Dead",
    "DeadVengeance": "Dead Man's Vengeance",
    "skinng": "Skinning",
    "feint_maneuver": "Feint Maneuver",
    "counteroffensive": "Counteroffensive",
    "swipe02": "Swipe",
    "bloodhunter_dash": "Dash",
    "flying": "Flying",
    "screamofdoomharpy": "Scream of Doom",
    "keepdistance": "Keeping_Distance",
    "warehousekey": "key_warehouse",
    "choppinglunge": "Crippling_Lunge",
    "treasure_BenorsTheFearlessCrown": "benor_crown",
    "passive_binding_rune": "rune_of_binding",
    "passive_weakening_rune": "rune_of_weakening",
    "passive_supporting_rune": "rune_of_support",
    "passive_engulfing_rune": "rune_of_engulfment",
    "passive_impact_rune": "rune_of_impact",
    "passive_fortyfying_rune": "rune_of_fortifying",
    "passive_power_rune": "rune_of_power",
    "vampiricrune": "rune_of_vampirism",
    "recipe_fruitsalad": "salad_fruits",
}


def levenshtein(a, b, cap=3):
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def main():
    recs = [json.loads(l) for l in open(os.path.join(DATA, "localization.jsonl"), encoding="utf-8")]
    sprites = json.load(open(os.path.join(DATA, "sprites.json"), encoding="utf-8"))

    kmap, kmap_nospace = {}, {}
    for r in recs:
        k = (r.get("key") or "").strip()
        if not k:
            continue
        kmap.setdefault(k.lower(), []).append(r)
        kmap_nospace.setdefault(re.sub(r"[^a-z0-9]", "", k.lower()), []).append(r)

    def lookup(queries):
        for q in queries:
            if q in kmap:
                return kmap[q]
        for q in queries:
            ns = re.sub(r"[^a-z0-9]", "", q)
            if ns and ns in kmap_nospace:
                return kmap_nospace[ns]
        return None

    def make_item(n, typ, rest, hits):
        icon = "icons/%s.png" % n
        if not hits:
            return {"sprite": n, "type": typ, "icon": icon,
                    "name_en": rest.replace("_", " "), "name_zh": "",
                    "desc_en": "", "desc_zh": "", "extra": []}
        key = (hits[0].get("key") or "").strip()
        # name record: en equals key (or shortest); descriptions: the rest, longest first
        name_rec = None
        for r in hits:
            if (r.get("en") or "").strip().lower() == key.lower():
                name_rec = r
                break
        if name_rec is None:
            name_rec = min(hits, key=lambda r: len(r.get("en") or ""))
        descs = [r for r in hits if r is not name_rec]
        descs.sort(key=lambda r: -len(r.get("en") or ""))
        desc = descs[0] if descs else None
        extra = []
        for r in descs[1:]:
            t_en = (r.get("en") or "").strip()
            if t_en and t_en != (desc.get("en") if desc else ""):
                extra.append({"en": t_en, "zh": r.get("zh") or ""})
        return {"sprite": n, "type": typ, "icon": icon,
                "name_en": name_rec.get("en") or rest, "name_zh": name_rec.get("zh") or "",
                "desc_en": (desc.get("en") if desc else "") or "",
                "desc_zh": (desc.get("zh") if desc else "") or "",
                "extra": extra}

    items, pending = [], []
    for s in sprites:
        n = s["name"] or ""
        p = next((x for x in PREFIXES if n.startswith(x)), None)
        if not p:
            continue
        typ = {"s_inv_": "item", "s_skills_": "skill", "s_spell_": "spell"}[p]
        rest = n[len(p):]
        hits = lookup(candidates(rest))
        if hits:
            items.append(make_item(n, typ, rest, hits))
        else:
            pending.append((n, typ, rest))

    # ---------- second pass: fuzzy / containment / manual ----------
    manual_hits, fuzzy_hits, contain_hits = 0, 0, 0
    def second_pass(rest):
        nonlocal manual_hits, fuzzy_hits, contain_hits
        # 1) manual map
        target = MANUAL_MAP.get(rest) or MANUAL_MAP.get(rest.replace("_", "").lower())
        if target:
            hits = kmap.get(target.lower()) or kmap_nospace.get(re.sub(r"[^a-z0-9]", "", target.lower()))
            if hits:
                manual_hits += 1
                return hits
        q = re.sub(r"[^a-z0-9]", "", rest.lower())
        if q.endswith("equipped"):
            q = q[: -len("equipped")]
        if not q:
            return None
        # 2) food/state variants: prefix a state word
        for pre in ("rotten", "spoiled", "cooked", "raw", "half", "piece"):
            h = kmap_nospace.get(pre + q)
            if h:
                return h
        # 2b) segment reorder: recipe_fruitsalad <-> salad_fruits
        base_rest = rest
        first, _, tail = base_rest.partition("_")
        if first.lower() in SEG_PREFIXES and tail:
            base_rest = tail
        segs = [x for x in base_rest.lower().replace("-", "_").split("_") if x.isalpha()]
        if len(segs) >= 2:
            h = kmap_nospace.get(re.sub(r"[^a-z0-9]", "", "".join(reversed(segs))))
            if h:
                return h
        elif len(q) >= 8:
            # single concatenated word: try rotating two-part splits (fruitsalad -> saladfruit)
            qb = re.sub(r"[^a-z0-9]", "", base_rest.lower())
            for i in range(3, len(qb) - 2):
                h = kmap_nospace.get(qb[i:] + qb[:i])
                if h:
                    return h
        # 3) containment: sprite name and key share a long common part
        if len(q) >= 8:
            best_c, best_len = None, 0
            for knos, recs2 in kmap_nospace.items():
                if len(knos) < 8:
                    continue
                if knos.endswith(q) or q.endswith(knos):
                    overlap = min(len(knos), len(q))
                    if overlap >= 8 and overlap > best_len and abs(len(knos) - len(q)) >= 4:
                        best_c, best_len = recs2, overlap
            if best_c:
                contain_hits += 1
                return best_c
        # 4) fuzzy: edit distance <= 2
        best, best_d = None, 3
        for knos, recs2 in kmap_nospace.items():
            if abs(len(knos) - len(q)) > 2:
                continue
            d = levenshtein(q, knos, cap=2)
            if d < best_d:
                best, best_d = recs2, d
        if best:
            fuzzy_hits += 1
        return best

    still_missing = []
    for n, typ, rest in pending:
        hits = second_pass(rest)
        if hits:
            items.append(make_item(n, typ, rest, hits))
        else:
            still_missing.append(n)
            items.append(make_item(n, typ, rest, None))

    # order: named & translated first
    items.sort(key=lambda it: (not it["name_zh"], it["type"], it["name_en"].lower()))

    # attach numeric stats from community dataset (stoneshardwiki.com, v0.9.4.24)
    stats_path = os.path.join(DATA, "community_equipment_stats.json")
    n_stats = 0
    if os.path.exists(stats_path):
        eq = json.load(open(stats_path, encoding="utf-8"))
        for it in items:
            rec = eq.get(it["sprite"]) or eq.get(it["sprite"] + "_0")
            if rec:
                it["stats"] = {k: rec.get(k) for k in
                               ("rarity", "type_text", "damage", "stats", "durability", "price")}
                it["stats"] = {k: v for k, v in it["stats"].items() if v not in (None, "", [])}
                if it["stats"]:
                    n_stats += 1
    print("items with numeric stats:", n_stats)

    # attach classification from community dataset (四级层级，注入 l1 code + 细分中文)
    # 匹配方式与 formulas.per_item_norm 一致：规范化英文名
    cls_path = os.path.join(DATA, "community_wiki_zh.json")
    n_cls = 0
    if os.path.exists(cls_path):
        wiki = json.load(open(cls_path, encoding="utf-8"))["items"]
        def _norm(s):
            return re.sub(r"[^a-z0-9]", "", (s or "").lower())
        cls_map = {}
        for w in wiki:
            c = w.get("classification")
            if not c:
                continue
            key = _norm(w.get("name_en") or w.get("id"))
            if key and key not in cls_map:
                tr = w.get("tier_raw")
                try:
                    tr = int(tr)
                except (TypeError, ValueError):
                    tr = None
                if tr is not None and not (1 <= tr <= 5):
                    tr = None
                cls_map[key] = (c, tr)
        # 通用「药剂」(potion) 在游戏内没有独立图标，potion01-04 的水/空瓶精灵即其外观，
        # 手动挂到 wiki 的 potion 分类上，让「药水」细分导航非空
        SPRITE_CLS_OVERRIDE = {}
        for _pn in ("01", "02", "03", "04"):
            SPRITE_CLS_OVERRIDE["potion%s_water" % _pn] = "potion"
            SPRITE_CLS_OVERRIDE["potion%s_empty" % _pn] = "potion"
        for it in items:
            if it["type"] != "item":
                continue
            # 精灵名 rest（s_inv_flask_water -> flaskwater）优先：本地化名常与 wiki id 不同
            rest = it["sprite"]
            for p in PREFIXES:
                if rest.startswith(p):
                    rest = rest[len(p):]
                    break
            override_id = SPRITE_CLS_OVERRIDE.get(rest)
            hit = (cls_map.get(_norm(override_id)) if override_id else None) \
                or cls_map.get(_norm(rest)) or cls_map.get(_norm(it["name_en"]))
            if not hit:
                continue
            c, tr = hit
            l1 = c.get("l1", {})
            l2 = c.get("l2", {})
            l3 = c.get("l3", {})
            code = l1.get("code") or ""
            l2zh = l2.get("labels", {}).get("zh") or ""
            # 饮品二级全是「喝」，用三级细分（酒水/药水/水/奶类）做导航维度
            if code == "food" and l2zh == "喝":
                sub = l3.get("labels", {}).get("zh") or ""
            else:
                sub = l2zh
            it["cl"] = [code, sub]
            it["tr"] = tr
            n_cls += 1
    print("items with classification:", n_cls)

    with open(os.path.join(DATA, "items.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)

    by_type = {}
    linked_zh = 0
    for it in items:
        by_type[it["type"]] = by_type.get(it["type"], 0) + 1
        if it["name_zh"]:
            linked_zh += 1
    matched = len(items) - len(still_missing)
    print("sprite entries:", len(items), "| matched:", matched, "| unmatched:", len(still_missing))
    print("second pass: manual=%d fuzzy=%d containment=%d" % (manual_hits, fuzzy_hits, contain_hits))
    print("by type:", by_type, "| with zh name:", linked_zh)
    print("sample unmatched:", still_missing[:15])

    # ---------- build items.html ----------
    payload = [{"s": it["sprite"], "t": it["type"], "i": it["icon"],
                "en": it["name_en"], "zh": it["name_zh"],
                "de": it["desc_en"], "dz": it["desc_zh"],
                "x": it["extra"], "st": it.get("stats") or None,
                "cl": it.get("cl") or None, "tr": it.get("tr") or None} for it in items]

    # 占位符公式：build_formulas.py 从社区数据集的反编译 GML 提取。
    # per_item_norm 按规范化英文名索引（items.json 没有 wiki id），条目自带公式
    # 优先于全局 by_key（同名占位符在不同技能里的缩放公式不同）。
    fpath = os.path.join(DATA, "formulas.json")
    f_by_key, f_norm = {}, {}
    if os.path.exists(fpath):
        _f = json.load(open(fpath, encoding="utf-8"))
        f_by_key, f_norm = _f.get("by_key", {}), _f.get("per_item_norm", {})
    matched_f = 0
    for p, it in zip(payload, items):
        m = f_norm.get(re.sub(r"[^a-z0-9]", "", (it["name_en"] or "").lower()))
        if m:
            p["f"] = m
            matched_f += 1
    print("placeholder formulas: per-item matched=%d / by_key=%d keys" % (matched_f, len(f_by_key)))

    # 属性极性表（由 build_stat_polarity.py 从游戏原文 ~lg~ / ~r~ 标记挖掘而来）
    # 只注入本页实际用到的标签，避免无关/噪声条目被误匹配
    used = set()
    for it in items:
        st = it.get("stats")
        if not isinstance(st, dict):
            continue
        for s in (st.get("stats") or []):
            if s.get("label"):
                used.add(s["label"].strip())
        for s in (st.get("damage") or []):
            if s.get("label"):
                used.add(s["label"].strip())

    pol = {}
    missing = []
    pol_path = os.path.join(DATA, "stat_polarity.json")
    if os.path.exists(pol_path):
        full = json.load(open(pol_path, encoding="utf-8")).get("labels", {})
        for lab in sorted(used):
            v = full.get(lab)
            if not v:
                missing.append(lab)
                continue
            pol[lab] = {"+": v.get("+") or "", "-": v.get("-") or "", "0": v.get("0") or ""}
    print("stat polarity: used=%d injected=%d missing=%s" % (len(used), len(pol), missing or "none"))

    html = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "items_template.html"),
                encoding="utf-8").read()
    html = html.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
    html = html.replace("__POLARITY__", json.dumps(pol, ensure_ascii=False))
    html = html.replace("__FORMULAS__", json.dumps(f_by_key, ensure_ascii=False, sort_keys=True))
    out = os.path.join(SITE, "items.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", out)


if __name__ == "__main__":
    main()
