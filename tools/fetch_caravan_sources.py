"""Fetch acquisition routes for caravan upgrade materials from the official wiki (MediaWiki API).
Writes data/community_caravan_material_sources.json
"""
import json, io, os, re, time, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "community_caravan_material_sources.json")

caravan = json.load(io.open(os.path.join(ROOT, "data", "community_caravan_upgrades.json"), encoding="utf-8"))
mats = {}
for b in caravan["branches"]:
    for n in b["nodes"]:
        for m in (n.get("materials") or []):
            mats[m["names"]["en"]] = {"zh": m["names"]["zh"], "id": m["id"]}

def fetch(title):
    url = ("https://stoneshard.com/wiki/api.php?action=parse&redirects=1&prop=wikitext&format=json&page="
           + urllib.parse.quote(title))
    req = urllib.request.Request(url, headers={"User-Agent": "ssw-wiki-builder/1.0 (local research)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    if d.get("error"):
        return None
    p = d["parse"]
    return p.get("wikitext", {}).get("*", ""), p.get("title", title)

SEC = re.compile(r"^(==+)\s*(.+?)\s*\1\s*$", re.M)
def acquired_section(wt):
    """Return lines of the 'Acquired From'/'Acquisition' section."""
    heads = [(m.start(), m.end(), m.group(2)) for m in SEC.finditer(wt)]
    for i, (s, e, name) in enumerate(heads):
        if name.strip().lower() in ("acquired from", "acquisition", "obtaining", "how to obtain"):
            nxt = heads[i + 1][0] if i + 1 < len(heads) else len(wt)
            body = wt[e:nxt]
            lines = []
            for ln in body.splitlines():
                ln = ln.strip()
                if not ln or ln.startswith(("__", "{{-}}")):
                    continue
                if ln.startswith(("*", "#", ";", ":")) or ln.startswith("[["):
                    lines.append(ln.lstrip("*#;: ").strip())
            return lines
    return []

def clean(line):
    # strip refs/templates, keep link labels
    line = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", line, flags=re.S)
    line = re.sub(r"\{\{[^}]*\}\}", "", line)
    def rep(m):
        parts = m.group(1).split("|")
        return parts[-1].replace("_", " ")
    return re.sub(r"\[\[([^\]]+)\]\]", rep, line).strip()

out = {}
for en in sorted(mats):
    try:
        res = fetch(en)
    except Exception as ex:
        res = None
        print("ERR", en, ex)
    if not res:
        out[en] = {"zh": mats[en]["zh"], "found": False, "routes": []}
        print("MISS", en)
    else:
        wt, title = res
        lines = acquired_section(wt)
        routes = [clean(l) for l in lines if clean(l)]
        # price
        mp = re.search(r"^\s*\{\{Price[^}]*\|(\d+)\s*\}\}", wt, re.M) or re.search(r"Price.*?(\d+)", wt[:1200])
        out[en] = {"zh": mats[en]["zh"], "found": True, "page": title, "routes": routes}
        print("OK", en, "->", title, len(routes), "routes")
    time.sleep(0.4)

json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved", OUT, len(out))
