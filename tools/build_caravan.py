"""Build site/caravan.html: 马车升级材料清单 + 材料获取途径大全.
Sources:
- data/community_caravan_upgrades.json   (游戏 GML 逆向: 30 节点/材料/官方多语言)
- data/community_caravan_material_sources.json (官方 wiki Acquired From 抓取)
- 人工整理的中文获取途径 (zh_routes, 依据官方 wiki 物品页 + Rags to Riches 社区资料)
"""
import json, io, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE = os.path.join(ROOT, "SITE_X")  # placeholder, fixed below
SITE = os.path.join(ROOT, "site")
TOOLS = os.path.join(ROOT, "tools")

caravan = json.load(io.open(os.path.join(DATA, "community_caravan_upgrades.json"), encoding="utf-8"))
sources = json.load(io.open(os.path.join(DATA, "community_caravan_material_sources.json"), encoding="utf-8"))

def clean_color(s):
    return re.sub(r"~[a-zA-Z]+~|~/~", "", s or "").strip()

# ---------- 人工整理的中文获取途径（官方 wiki 物品页 + Rags to Riches 资料） ----------
ZH_ROUTES = {
    "Toolbox": ["各地木匠出售（奥斯布鲁克·尤格 / 曼郡·德克）", "布林·独眼龙魏格玛", "杂货商人 / 集市商人"],
    "Nails": ["各地铁匠出售（奥斯布鲁克·杰巴尔 / 曼郡·狄特里希）", "世界搜刮（板条箱、木桶等）"],
    "Huge Cauldron": ["各地铁匠出售（杰巴尔 / 狄特里希）", "杂货商人 / 集市商人 / 独眼龙魏格玛"],
    "Ladle": ["杂货商人", "地牢搜刮", "奥克桶酿酒厂里可以偷到一个"],
    "Charcoal Chunk": ["曼郡被烧毁的房屋、布林铸币广场银行附近拾取", "烂柳酒馆旁的炭场购买"],
    "Alchemical Apparatus": ["布林码头「奇异之物炼金商店」雷诺德·坎恩"],
    "Foraging Supplies": ["草药师（奥斯布鲁克·弗利德 / 布林草药师）", "曼郡牧师乔什", "集市商人"],
    "Shovel": ["猎人布兰偶尔出售", "杂货商人", "游商老托特偶尔出售"],
    "Sickle": ["奥斯布鲁克磨坊（阿兰）", "草药师弗利德"],
    "Sacks of Grain": ["奥斯布鲁克磨坊主阿兰"],
    "Bucket": ["各地杂货商 / 木匠", "村庄水井附近可拾取"],
    "Cages with Chickens": ["各地木匠出售（尤格 / 德克）"],
    "Spice Box": ["布林铸币广场「青线商行」精灵商人阿尔穆兹"],
    "Ginger Root": ["布林青线商行（阿尔穆兹）", "布林食物商贩（胖扬）", "野外采集"],
    "Spearmint": ["野外采集", "草药师 / 食物商贩"],
    "Leek": ["食物 / 蔬菜商贩", "野外采集"],
    "Garlic": ["食物 / 蔬菜商贩", "野外采集"],
    "Onion": ["食物 / 蔬菜商贩", "野外采集"],
    "Hieronite Altar": ["曼郡牧师乔什出售"],
    "Wax Candle": ["坟墓 / 衣柜 / 橱柜搜刮", "变节新徒地牢掉落（社区资料）"],
    "Altar Bell": ["书架搜刮", "变节新徒（新教徒）地牢掉落"],
    "Lesser Runic Stone": ["布林码头矮人商人（库存轮换，社区资料）", "地牢搜刮"],
    "Candle-end": ["亡灵地牢内拾取"],
    "Skull": ["地牢中的石棺 / 坟墓 / 尸体搜刮"],
    "Meditation Table": ["布林码头斯卡迪亚商人兹杰内布拉德", "布林青线商行（精灵版本）"],
    "Incense": ["布林青线商行", "布林当铺（维·诺姆斯家）", "地牢箱子搜刮"],
    "Incense Burner": ["布林青线商行精灵商人（阿尔穆兹）", "布林当铺补货后可遇"],
    "Censer": ["变节新徒地牢稀有掉落", "书架搜刮"],
    "Canvas Roll": ["奥斯布鲁克裁缝霍特"],
    "Rope": ["各地杂货商人", "坟墓 / 世界搜刮"],
    "Spool of Thread": ["各地裁缝（霍特）", "板条箱搜刮"],
    "Straw": ["奥斯布鲁克磨坊与干草堆免费采集", "衣柜搜刮"],
    "Straw Dummy": ["各地木匠出售（尤格 / 德克）"],
    "Hardy Tent Cloth": ["裁缝出售（完成小营帐后解锁：霍特 / 梅里克）"],
    "Apothecary Box": ["草药师（弗利德 / 布林草药师）"],
    "Mindwort": ["野外采集", "草药师", "板条箱搜刮"],
    "Thyme": ["野外采集（草原）", "草药师"],
    "Burnet": ["松树林采集", "布林草药师"],
    "Set of Sturdy Wheels": ["各地木匠出售（尤格 / 德克）"],
    "Bottle of Oil": ["草药师弗利德", "布林码头炼金商店", "烂柳酒馆附近"],
    "Carpenter Hammer": ["曼郡木匠德克（通常与车轮一同出售）"],
    "Sturdy Chest": ["各地木匠出售", "铁匠", "独眼龙魏格玛"],
    "Quality Reins": ["奥斯布鲁克马厩安塞尔姆", "独眼龙魏格玛"],
    "Horseshoe": ["马厩（安塞尔姆）与曼郡铁匠学徒林德", "坟墓搜刮"],
    "Set of Ironbound Wheels": ["曼郡木匠德克（完成牢固车轮后）", "烂柳酒馆掌柜"],
    "Spacious Chests": ["独眼龙魏格玛", "木匠 / 集市商人"],
    "Reinforced Harness": ["烂柳酒馆掌柜（完成马车装具后）"],
    "cloth": ["奥斯布鲁克裁缝霍特", "尼斯商人（布林码头）", "坟墓 / 箱子搜刮"],
    "Ironbound Chests": ["世界搜刮与各地商人偶有出售（高级地牢更常见）"],
    "Foldable Flagpole": ["维伦（Verren）提供"],
    "Cage with Pigeons": ["杂货商人 / 集市商人", "独眼龙魏格玛"],
    "Pile of Letters": ["维伦出售：2000 金币（人脉网络专用）"],
    "Signed Permit": ["维伦出售：1500 金币（往日人情专用）"],
    "Directives": ["维伦出售：1500 金币（本地线报专用）"],
    "Letter of Trading Authority": ["维伦出售：2000 金币（好客户专用）"],
}

RACE_ZH = {"human": "人类出身", "dwarf": "矮人出身", "elf": "精灵出身"}

def mat_payload(m):
    en = m["names"]["en"]
    src = sources.get(en, {})
    icon = ""
    ip = (m.get("icon_path") or "").split("/")[-1]
    ip = re.sub(r"_0\.png$", ".png", ip)
    if os.path.exists(os.path.join(SITE, "icons", ip)):
        icon = "icons/" + ip
    routes = ZH_ROUTES.get(en) or []
    price = src.get("price")
    if en == "Spice Box":
        price = None  # wiki 重定向错页，价格不可信
    return {"zh": m["names"]["zh"], "en": en, "n": m.get("quantity") or 1,
            "icon": icon, "price": price, "routes": routes,
            "type": (m.get("type_labels") or {}).get("zh", "")}

def node_payload(n):
    return {
        "id": n["id"], "zh": n["names"]["zh"], "eff": clean_color((n.get("effects") or {}).get("zh")),
        "desc": clean_color((n.get("descriptions") or {}).get("zh")),
        "sprite": ("icons/" + n["sprite"] + ".png") if n.get("sprite") and os.path.exists(
            os.path.join(SITE, "icons", n["sprite"] + ".png")) else "",
        "basic": bool(n.get("basic")),
        "prereq": n.get("prerequisites") or [],
        "needN": n.get("required_upgrades_count") or 0,
        "mats": [mat_payload(m) for m in (n.get("materials") or [])],
        "variants": [
            {"race": RACE_ZH.get(v.get("race"), v.get("race")), "zh": v["names"]["zh"],
             "eff": clean_color((v.get("effects") or {}).get("zh")),
             "mats": [mat_payload(m) for m in (v.get("materials") or [])]}
            for v in (n.get("variants") or {}).values()
        ],
        "notImpl": "尚未实装" in ((n.get("effects") or {}).get("zh") or ""),
    }

branches = []
id2zh = {}
for b in caravan["branches"]:
    for n in b["nodes"]:
        id2zh[n["id"]] = n["names"]["zh"]
for b in caravan["branches"]:
    branches.append({
        "id": b["id"], "zh": b["labels"]["zh"],
        "nodes": [node_payload(n) for n in b["nodes"]],
    })

# fix prereq ids -> zh
for b in branches:
    for n in b["nodes"]:
        n["prereq"] = [id2zh.get(p, p) for p in n["prereq"]]

# ---------- 材料总表（按类型分组） ----------
seen, mats_order = {}, []
for b in branches:
    for n in b["nodes"]:
        for m in n["mats"]:
            if m["en"] not in seen:
                seen[m["en"]] = dict(m, used=[])
                mats_order.append(seen[m["en"]])
            if n["zh"] not in seen[m["en"]]["used"]:
                seen[m["en"]]["used"].append(n["zh"])
for b in branches:  # variants materials too
    for n in b["nodes"]:
        for v in n["variants"]:
            for m in v["mats"]:
                if m["en"] not in seen:
                    seen[m["en"]] = dict(m, used=[])
                    mats_order.append(seen[m["en"]])
                if v["zh"] not in seen[m["en"]]["used"]:
                    seen[m["en"]]["used"].append(v["zh"])

by_type = {}
for m in mats_order:
    by_type.setdefault(m["type"] or "其他", []).append(m)
TYPE_ORDER = ["升级项目", "材料", "工具", "废品", "商货", "食物", "原料", "贵重物品", "其他"]
type_groups = [{"type": t, "items": by_type[t]} for t in TYPE_ORDER if t in by_type]

# ---------- 全升级累计需求 ----------
totals = {}
for m in mats_order:
    if m["type"] == "升级项目" or m["type"] == "其他":
        pass
for b in branches:
    for n in b["nodes"]:
        if n["basic"]:
            continue
        use = n["variants"] if n["variants"] else [{"mats": n["mats"]}]
        for v in use:
            for m in v["mats"]:
                t = totals.setdefault(m["en"], dict(m, total=0, where=[]))
                t["total"] += m["n"]
                if n["zh"] not in t["where"]:
                    t["where"].append(n["zh"])
total_list = sorted(totals.values(), key=lambda x: (x["type"] != "升级项目", -(x["price"] or 0) * x["total"]))
crown_total = sum(m["total"] * (m["price"] or 0) for m in total_list if m["type"] != "升级项目")
verren_total = 2000 + 1500 + 1500 + 2000

payload = {
    "branches": branches,
    "types": type_groups,
    "totals": total_list,
    "crownTotal": crown_total,
    "verrenTotal": verren_total,
}

tpl = io.open(os.path.join(TOOLS, "caravan_template.html"), encoding="utf-8").read()
html = tpl.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
out = os.path.join(SITE, "caravan.html")
io.open(out, "w", encoding="utf-8").write(html)
kb = os.path.getsize(out) / 1024
print("caravan.html %.0f KB | nodes %d | materials %d | estimated materials cost %d + Verren %d"
      % (kb, sum(len(b["nodes"]) for b in branches), len(mats_order), crown_total, verren_total))
