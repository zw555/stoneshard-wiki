"""Build site/trade.html:
- per-item top-3 buyers (parsed from equipment detail pages, data/ssw_pages/*.html)
- merchant leaderboard (how often each merchant appears in top-3)
- trade mechanics reference (category demand rows + town reputation favorability)
- **商货收购**：全物品「谁收 / 收多少」，数据来自游戏文件逆向的商人收购系数
  （data/community_trade_category_matrix.json），补上社区 wiki 没有的商货（小麦/盐巴…）缺口。

收购价算法（对 1709 组社区实测价命中 94.7%，见 validate_prices()）：
    单价 = round(基准价 × 收购系数 × (1 + 材质修正) × Buying_Prices)
  · 收购系数 = 商货取该商品自身的单元（已含其 BP_Mod），其余取品类单元；
  · 材质修正仅对非商货生效（商货的修正已并入其自身单元，再乘会重复计算）；
  · 装备剩余偏差来自耐久 / 品质 / 赃物，商货无耐久故更准。

Sources: stoneshardwiki.com detail pages + trade_category_matrix.json
"""
import json, os, re, sys, glob, collections
from html import unescape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _nav import inject_nav  # noqa: E402  写盘后自注入共享外壳（项目约定）
from _icons import icon_index, real_name, mismatches  # noqa: E402  图标名大小写校正

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE = os.path.join(ROOT, "site")
TOOLS = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(DATA, "ssw_pages")
MATRIX_PATH = os.path.join(DATA, "community_trade_category_matrix.json")

RE_NAME = re.compile(r'class="iname [^"]*">([^<]+)<')
RE_EN = re.compile(r'class="en-name">([^<]+)<')
RE_ICON = re.compile(r'equipment-icon-image" src="/deploy_sprites/(s_inv_[a-z0-9_]+?_\d+)\.png"')
RE_SELLERS = re.compile(r'<ol class="detail-seller-ranking">(.*?)</ol>', re.S)
RE_LI = re.compile(r'<li><span>([^<]+)</span><strong>(\d+)</strong><em>([^<]+)</em></li>')
RE_STATS = os.path.join(DATA, "community_equipment_stats.json")


def parse_pages():
    items = {}
    for p in sorted(glob.glob(os.path.join(PAGES, "*.html"))):
        h = open(p, encoding="utf-8").read()
        mn = RE_NAME.search(h)
        mi = RE_ICON.search(h)
        if not (mn and mi):
            continue
        sellers = []
        ms = RE_SELLERS.search(h)
        if ms:
            for rank, price, who in RE_LI.findall(ms.group(1)):
                sellers.append({"rank": rank.strip(), "price": int(price), "who": unescape(who).strip()})
        me = RE_EN.search(h)
        items[mi.group(1)] = {
            "zh": unescape(mn.group(1)).strip(),
            "en": unescape(me.group(1)).strip() if me else "",
            "sellers": sellers,
        }
    return items


# ---------------------------------------------------------------- 商货收购
# 商货展示顺序（原料在前、酒类在后；比按中文码点排序自然）
COM_ORDER = ["wheat", "salt", "timber", "coal", "ale", "wine", "cider"]


def _icon_png(raw):
    """矩阵里的 icon 形如 s_inv_goods_Wheat_0.png -> site/icons 里是 s_inv_goods_Wheat.png"""
    return re.sub(r"_\d+\.png$", ".png", raw or "")


def build_goods():
    """把商人收购系数压成紧凑 payload，供前端按「单价分组」渲染。

    前端用的公式与 validate_prices() 校验的完全一致，避免两边各写一套。
    """
    mx = json.load(open(MATRIX_PATH, encoding="utf-8"))
    rows, mat_items, mrch = mx["rows"], mx["items"], mx["merchants"]
    idx = icon_index(SITE)          # 矩阵里的 icon 有 79 个是全小写，磁盘上是驼峰名

    cats = {r["id"]: (r.get("labels") or {}).get("zh") or r["id"] for r in rows}
    towns = {t["id"]: (t.get("labels") or {}).get("zh") or t["id"] for t in mx["towns"]}
    mats = {it["material"] for it in mat_items if it.get("material")}

    ms = []
    for m in mrch:
        vals = (m.get("price_modifiers") or {}).get("values") or {}
        # 系数 0 = 该商人实际上不收（全站仅 2 例：奥尔米-盐巴、怀俄特-小麦），按不收处理
        cells = {k: v["value"] for k, v in (m.get("cells") or {}).items()
                 if isinstance(v, dict) and (v.get("value") or 0) > 0}
        d = {}
        for mat in mats:
            v = vals.get(mat.capitalize() + "_BP_Mod")
            if v:
                d[mat] = v
        ms.append({
            "i": m["id"], "z": m["labels"].get("zh") or m["id"],
            "t": m.get("town_id") or "", "g": (m.get("gold_range") or {}).get("max"),
            "b": vals.get("Buying_Prices", 1.0),
            "c": cells, "d": d,
        })

    its = []
    for it in mat_items:
        if it.get("base_price") is None:
            continue
        its.append({
            "i": it["id"], "z": it["names"].get("zh") or it["id"], "e": it["names"].get("en") or "",
            "ic": real_name(_icon_png(it.get("icon")), idx), "b": it["base_price"],
            "c": (it.get("trade_categories") or [""])[0], "k": it.get("commodity_key") or "",
            "m": it.get("material") or "",
        })
    its.sort(key=lambda x: (COM_ORDER.index(x["k"]) if x["k"] in COM_ORDER else 99, x["z"]))
    return {"cats": cats, "towns": towns, "merchants": ms, "items": its}


def price_of(merchant, item, cells=None):
    """单价 = round(基准价 × 系数 × (1+材质修正) × Buying_Prices)；不收则 None。"""
    cells = merchant["c"] if cells is None else cells
    key = item["k"] or item["c"]
    coeff = cells.get(key)
    if coeff is None:
        return None
    mat = 0.0 if item["k"] else merchant["d"].get(item["m"], 0.0)
    return round(item["b"] * coeff * (1 + mat) * merchant["b"])


def validate_prices(goods):
    """用社区 wiki 的实测收购榜反查公式：命中率写入构建日志，防止公式悄悄跑偏。"""
    byicon = {it["ic"]: it for it in goods["items"]}
    towns = goods["towns"]
    bidx = {(towns.get(m["t"], ""), m["z"]): m for m in goods["merchants"]}
    ok = tot = 0
    unmatched = collections.Counter()
    for p in sorted(glob.glob(os.path.join(PAGES, "*.html"))):
        h = open(p, encoding="utf-8").read()
        mi, msel = RE_ICON.search(h), RE_SELLERS.search(h)
        if not (mi and msel):
            continue
        it = byicon.get(_icon_png(mi.group(1) + ".png"))
        if not it:
            continue
        for _rank, price, who in RE_LI.findall(msel.group(1)):
            who = unescape(who).strip()
            if " · " not in who:
                continue
            t, n = who.split(" · ", 1)
            m = bidx.get((t.strip(), n.strip()))
            if not m:
                unmatched[who] += 1
                continue
            got = price_of(m, it)
            if got is None:
                continue
            tot += 1
            ok += (got == int(price))
    return ok, tot, unmatched


def main():
    pages = parse_pages()
    stats = json.load(open(RE_STATS, encoding="utf-8")) if os.path.exists(RE_STATS) else {}

    payload = []
    icon_idx = icon_index(SITE)
    for sprite, it in pages.items():
        st = stats.get(sprite) or {}
        payload.append({
            "s": sprite, "zh": it["zh"], "en": it["en"],
            "ic": real_name(re.sub(r"_\d+$", "", sprite) + ".png", icon_idx),
            "base": st.get("price"),
            "ty": st.get("type_text") or "",
            "sel": it["sellers"],
        })
    payload.sort(key=lambda x: x["zh"] or x["en"])
    with_sellers = sum(1 for x in payload if x["sel"])

    matrix = json.load(open(MATRIX_PATH, encoding="utf-8"))
    mech = {
        "categories": [{"zh": (r["labels"] or {}).get("zh", r["id"]), "en": (r["labels"] or {}).get("en", ""),
                        "keys": r.get("source_keys") or [], "rt": r.get("runtime_keys") or {}}
                       for r in matrix["rows"]],
        "formula": matrix.get("formula") or {},
        "towns": [{"zh": (t["labels"] or {}).get("zh", t["id"]), "en": (t["labels"] or {}).get("en", ""),
                   "ic": (t.get("icon_sprite") or "") + ".png",
                   "tiers": [{"zh": (tt["labels"] or {}).get("zh", tt["id"]),
                              "en": (tt["labels"] or {}).get("en", ""),
                              "fav": tt.get("trade_favorability")} for tt in (t.get("reputation_tiers") or [])]}
                  for t in matrix["towns"]],
    }

    goods = build_goods()
    ok, tot, unmatched = validate_prices(goods)
    n_com = sum(1 for x in goods["items"] if x["k"])
    idx = icon_index(SITE)
    fixed = (mismatches([_icon_png(it.get("icon")) for it in matrix["items"]], idx)          # 商货 payload
             + mismatches([re.sub(r"_\d+$", "", s) + ".png" for s in pages], idx))          # 装备 payload
    tpl = open(os.path.join(TOOLS, "trade_template.html"), encoding="utf-8").read()
    html = (tpl.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
               .replace("__MECH__", json.dumps(mech, ensure_ascii=False))
               .replace("__TRADE__", json.dumps(goods, ensure_ascii=False)))
    out = os.path.join(SITE, "trade.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    inject_nav("trade.html", "trade.html")

    print("items:", len(payload), "| with seller ranking:", with_sellers)
    print("goods: %d 商人 / %d 物品（其中商货 %d）" % (len(goods["merchants"]), len(goods["items"]), n_com))
    print("图标名大小写校正: %d 个（Windows 掩盖、Linux 会 404）" % len(fixed))
    print("价格公式自校验: %d/%d 命中 (%.1f%%)" % (ok, tot, 100 * ok / max(tot, 1)))
    if unmatched:
        print("  未匹配商人名 %d 个，如 %s" % (len(unmatched), list(unmatched)[:3]))
    print("wrote", out)


if __name__ == "__main__":
    main()
