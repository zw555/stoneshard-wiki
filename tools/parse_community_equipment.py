"""Parse stoneshardwiki.com equipment detail pages (data/ssw_pages/*.html)
-> data/community_equipment_stats.json keyed by sprite stem.
"""
import json, os, re, glob
from html import unescape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, "data", "ssw_pages")
OUT = os.path.join(ROOT, "data", "community_equipment_stats.json")

RE_NAME = re.compile(r'class="iname ([^"]*)">([^<]+)<')
RE_EN = re.compile(r'class="en-name">([^<]+)<')
RE_TYPE = re.compile(r'class="itype">([^<]+)<')
RE_ICON = re.compile(r'equipment-icon-image" src="/deploy_sprites/(s_inv_[a-z0-9_]+?_\d+)\.png"')
RE_DMG = re.compile(r'game-damage-row ([a-z]+)">([0-9.\-]+)<span class="dmg-label">([^<]+)<')
RE_STAT = re.compile(r'<span class="sk">([^<]+)</span><span class="sv[^"]*">([^<]+)</span>')
RE_DUR = re.compile(r'耐久(?:<!-- -->)?\s*:</span><strong>(\d+)</strong>')
RE_DESC = re.compile(r'<p class="item-desc"><span class="game-rich-text">(.*?)</span></p>', re.S)
RE_PRICE = re.compile(r'<div class="item-price">.*?<strong>(\d+)</strong>', re.S)


def parse_page(path):
    h = open(path, encoding="utf-8").read()
    mn = RE_NAME.search(h)
    if not mn:
        return None
    it = {}
    it["rarity"] = mn.group(1).strip()
    it["name_zh"] = unescape(mn.group(2)).strip()
    m = RE_EN.search(h)
    it["name_en"] = unescape(m.group(1)).strip() if m else ""
    m = RE_TYPE.search(h)
    it["type_text"] = unescape(m.group(1)).strip() if m else ""
    m = RE_ICON.search(h)
    it["sprite"] = m.group(1) if m else ""
    it["damage"] = [{"type": t, "value": float(v) if "." in v else int(v), "label": unescape(lab).strip()}
                    for t, v, lab in RE_DMG.findall(h)]
    it["stats"] = [{"label": unescape(a).strip(), "value": unescape(b).strip()} for a, b in RE_STAT.findall(h)]
    m = RE_DUR.search(h)
    it["durability"] = int(m.group(1)) if m else None
    m = RE_DESC.search(h)
    it["desc_zh"] = unescape(m.group(1)).strip() if m else ""
    m = RE_PRICE.search(h)
    it["price"] = int(m.group(1)) if m else None
    return it


def main():
    out, n = {}, 0
    for p in sorted(glob.glob(os.path.join(PAGES, "*.html"))):
        try:
            it = parse_page(p)
        except Exception as e:
            print("ERR", os.path.basename(p), e)
            continue
        n += 1
        if it and it["sprite"]:
            out.setdefault(it["sprite"], it)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    dmg = sum(1 for c in out.values() if c["damage"])
    price = sum(1 for c in out.values() if c["price"])
    print("pages:", n, "| unique sprites:", len(out), "| with damage:", dmg, "| with price:", price)


if __name__ == "__main__":
    main()
