"""Build site/trade.html:
- per-item top-3 buyers (parsed from equipment detail pages, data/ssw_pages/*.html)
- merchant leaderboard (how often each merchant appears in top-3)
- trade mechanics reference (category demand rows + town reputation favorability)
Sources: stoneshardwiki.com detail pages + trade_category_matrix.json
"""
import json, os, re, glob, collections
from html import unescape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE = os.path.join(ROOT, "site")
TOOLS = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(DATA, "ssw_pages")

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


def main():
    pages = parse_pages()
    stats = json.load(open(RE_STATS, encoding="utf-8")) if os.path.exists(RE_STATS) else {}

    payload = []
    for sprite, it in pages.items():
        st = stats.get(sprite) or {}
        payload.append({
            "s": sprite, "zh": it["zh"], "en": it["en"],
            "ic": re.sub(r"_\d+$", "", sprite) + ".png",
            "base": st.get("price"),
            "ty": st.get("type_text") or "",
            "sel": it["sellers"],
        })
    payload.sort(key=lambda x: x["zh"] or x["en"])
    with_sellers = sum(1 for x in payload if x["sel"])

    matrix = json.load(open(os.path.join(DATA, "community_trade_category_matrix.json"), encoding="utf-8"))
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
    tpl = open(os.path.join(TOOLS, "trade_template.html"), encoding="utf-8").read()
    html = (tpl.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
               .replace("__MECH__", json.dumps(mech, ensure_ascii=False)))
    out = os.path.join(SITE, "trade.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("items:", len(payload), "| with seller ranking:", with_sellers)
    print("wrote", out)


if __name__ == "__main__":
    main()
