"""Extract placeholder formulas from the community wiki dataset.

data/community_wiki_zh.json items carry `formula_refs`: for each /*KEY*/ placeholder
in a skill description, the reverse-engineered GML expression that the game evaluates
at runtime to fill the value (from utmt_dump of o_skill_* objects).

Output: data/formulas.json = { "by_key": { KEY: [expr, ...] }, "meta": {...} }

The expressions reference owner.* runtime stats (attributes, Magic_Power, school
powers, ...). The page templates evaluate them against a base character built from
the community planner's own stat engine (see tools/_smoke_dialog.mjs and AGENT.md).
Expressions with scr_* calls (enemy stats) or unknown terms stay unresolvable.
"""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def main():
    wiki = json.load(open(os.path.join(DATA, "community_wiki_zh.json"), encoding="utf-8"))
    by_key = collections.defaultdict(set)
    per_item = {}
    for it in wiki["items"]:
        frs = it.get("formula_refs") or []
        for fr in frs:
            e = fr.get("display_expression")
            if not e:
                continue
            e = e.strip()
            by_key[fr["key"]].add(e)
        if frs:
            m = {fr["key"]: fr["display_expression"].strip()
                 for fr in frs if fr.get("display_expression")}
            if m:
                per_item[it.get("id") or it.get("name_en")] = m

    out = {
        "by_key": {k: sorted(v) for k, v in sorted(by_key.items())},
        "per_item": {k: v for k, v in sorted(per_item.items())},
        "meta": {"keys": len(by_key), "exprs": sum(len(v) for v in by_key.values())},
    }
    # normalized lookup for build_linkage (items.json has no wiki ids, only names)
    import re as _re

    def _norm(s):
        return _re.sub(r"[^a-z0-9]", "", (s or "").lower())

    per_item_norm = {}
    for it in wiki["items"]:
        frs = it.get("formula_refs") or []
        if not frs:
            continue
        m = {fr["key"]: fr["display_expression"].strip()
             for fr in frs if fr.get("display_expression")}
        if not m:
            continue
        for cand in (it.get("id"), it.get("name_en")):
            n = _norm(cand)
            if n and n not in per_item_norm:
                per_item_norm[n] = m
    out["per_item_norm"] = per_item_norm
    p = os.path.join(DATA, "formulas.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, sort_keys=True)
    print("keys:", len(by_key), "| exprs:", out["meta"]["exprs"], "| per_item:", len(per_item))
    print("wrote", p)
    report(by_key)


# ---------------------------------------------------------------------------
# Resolution report: emulate the page-side evaluator at attributes=10 to split
# keys into "computable" vs "ambiguous" vs "needs runtime state".
# ---------------------------------------------------------------------------

def thresholds(x):
    return (x >= 15) + (x >= 20) + (x >= 25) + (x >= 30)


def base_ctx():
    """Base character at attributes 10, no equipment / skills (community planner
    stat engine, decoded from ssw_base.js)."""
    s = a = pr = v = w = 10
    ts, ta, tp, tv, tw = thresholds(s), thresholds(a), thresholds(pr), thresholds(v), thresholds(w)
    return {
        "STR": s, "AGL": a, "PRC": pr, "WIL": w, "Vitality": v,
        "Magic_Power": 100 + 7.5 * tw,
        "Pyromantic_Power": 0, "Geomantic_Power": 0, "Electromantic_Power": 0,
        "Venomantic_Power": 0, "Cryomantic_Power": 0, "Arcanistic_Power": 0,
        "Astromantic_Power": 0, "Psimantic_Power": 0,
        "HP": 100 + 15 * tv, "max_hp": 100 + 15 * tv, "max_mp": 60 + 4 * v,
        "PRR": 0, "Block_PowerMax": 0, "Legs_DEF": 0, "Body_DEF": 0,
        "Spell_Hit_Chance": 1.5 * pr, "Miscast_Chance": 35 - 1.5 * a,
        "Miracle_Chance": 5 + 5 * tp, "Miracle_Power": 25,
        "Mainhand_Efficiency": 100, "Offhand_Efficiency": 100,
        "EVS": 1 + 5 * ta, "Knockback_Chance": 0,
        "CRT": 1 + 5 * tp, "CRTD": 25 + 10 * ts, "CTA": -14 + 1.5 * a,
        "FMB": 35 - 1.5 * a, "Hit_Chance": 65 + 1.5 * pr,
        "Weapon_Damage": 85 + 1.5 * s, "Armor_Piercing": -15 + 1.5 * pr,
        "Bodypart_Damage": 7.5 * ts, "Armor_Damage": 15 * ts,
        "Fortitude": 7.5 * tw, "Stun_Resistance": 7.5 * tv,
        "Knockback_Resistance": 7.5 * ta, "Pain_Resistance": 7.5 * tw,
        "Cooldown_Reduction": 115 - 1.5 * w, "Abilities_Energy_Cost": 115 - 1.5 * w,
        "Health_Restoration": 10, "Healing_Received": 100, "MP_Restoration": 2 * v,
        "Crit_Avoid": 0, "Lifesteal": 0, "Manasteal": 0,
        "Stagger_Chance": 0, "Daze_Chance": 0, "Stun_Chance": 0,
        "Immob_Chance": 0, "Bleeding_Chance": 0,
        "Skills_Energy_Cost": 0, "Spells_Energy_Cost": 0,
        "Damage_Received": 100, "Backfire_Damage": 0,
    }


import re

TERM_RE = re.compile(r"owner\.([A-Za-z_0-9]+)")
ALLOWED_RE = re.compile(r"^[\d\s+\-*/(),.]*$")


def eval_expr(expr, ctx):
    """Mirror of the JS evaluator: substitute owner.* and math_round, then eval a
    pure-arithmetic expression. Returns float or None if unresolvable."""
    if "scr_" in expr:
        return None

    def sub(m):
        v = ctx.get(m.group(1))
        if v is None:
            raise KeyError(m.group(1))
        return "(%s)" % v

    try:
        e = TERM_RE.sub(sub, expr)
        e = e.replace("math_round(", "round(").replace("max(", "max(")
        if not ALLOWED_RE.match(e.replace("round", "").replace("abs", "")):
            # round(...) calls: allow identifier 'round' too
            if not re.match(r"^[\d\s+\-*/(),.round]*$", e):
                return None
        r = eval(e, {"__builtins__": {}}, {"round": round, "max": max, "min": min, "abs": abs})
        return float(r)
    except Exception:
        return None


def report(by_key):
    ctx = base_ctx()
    loc = open(os.path.join(DATA, "localization.jsonl"), encoding="utf-8").read()
    all_keys = set(re.findall(r"/\*([A-Za-z_0-9]+)\*/", loc))
    ok, ambiguous, noformula = [], [], []
    for k in sorted(all_keys):
        exprs = by_key.get(k)
        if not exprs:
            noformula.append(k)
            continue
        vals = [eval_expr(e, ctx) for e in exprs]
        good = {round(v, 2) for v in vals if v is not None}
        if len(good) == 1:
            ok.append((k, good.pop()))
        else:
            ambiguous.append(k)
    print("\n=== 可计算（%d 个键，属性=10 时的值）===" % len(ok))
    for k, v in ok:
        print("  %-24s %s" % (k, int(v) if float(v).is_integer() else v))
    print("\n=== 公式互相矛盾/含未知项（%d 个键）===" % len(ambiguous))
    for k in ambiguous:
        print("  " + k)
    print("\n=== 完全没有公式（%d 个键，运行时/界面文本）===" % len(noformula))
    for k in noformula:
        print("  " + k)


if __name__ == "__main__":
    main()
