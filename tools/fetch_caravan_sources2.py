"""Second pass: resolve missed caravan material pages via opensearch, then fetch."""
import json, io, os, re, time, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "community_caravan_material_sources.json")
data = json.load(io.open(OUT, encoding="utf-8"))

API = "https://stoneshard.com/wiki/api.php"
def get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "ssw-wiki-builder/1.0 (local research)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:
            if attempt == 2: raise
            time.sleep(2)

SEC = re.compile(r"^(==+)\s*(.+?)\s*\1\s*$", re.M)
def acquired_section(wt):
    heads = [(m.start(), m.end(), m.group(2)) for m in SEC.finditer(wt)]
    for i, (s, e, name) in enumerate(heads):
        if name.strip().lower() in ("acquired from", "acquisition", "obtaining", "how to obtain"):
            nxt = heads[i + 1][0] if i + 1 < len(heads) else len(wt)
            body = wt[e:nxt]
            lines = []
            for ln in body.splitlines():
                ln = ln.strip()
                if not ln or ln.startswith(("__", "{{-}}")): continue
                if ln.startswith(("*", "#", ";", ":", "[[")):
                    lines.append(ln.lstrip("*#;: ").strip())
            return lines
    return []

def clean(line):
    line = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", line, flags=re.S)
    line = re.sub(r"\{\{[^}]*\}\}", "", line)
    def rep(m):
        return m.group(1).split("|")[-1].replace("_", " ")
    return re.sub(r"\[\[([^\]]+)\]\]", rep, line).strip()

RETRY = ["Spearmint", "Spice Box"]
VARIANTS = {
    "Alchemical Apparatus": ["Alchemy Apparatus", "Alchemical Apparatus"],
    "Cages with Chickens": ["Cage with Chickens", "Chicken Cage"],
    "Canvas Roll": ["Canvas Tent Roll", "Canvas Roll"],
    "Charcoal Chunk": ["Coal Chunk", "Charcoal Chunk"],
    "Sturdy Chest": ["Sturdy Chests"],
    "Set of Ironbound Wheels": ["Ironbound Wheels", "Set of Ironbound Wheels"],
    "Foldable Flagpole": ["Foldable Flagpole", "Flagpole"],
    "Hieronite Altar": ["Hieronite Altar", "Hieronite"],
    "Incense Burner": ["Incense Burner", "Burner"],
    "Directives": ["Directives"],
    "Signed Permit": ["Signed Permit"],
    "Pile of Letters": ["Pile of Letters"],
    "Letter of Trading Authority": ["Letter of Trading Authority", "Trading Authority"],
}

for en in sorted(data):
    if data[en]["found"] and en not in RETRY:
        continue
    candidates = RETRY if en in RETRY else VARIANTS.get(en, [en])
    got = False
    for title in candidates:
        try:
            sr = get({"action": "opensearch", "search": title, "limit": 3, "format": "json"})
        except Exception as ex:
            print("SEARCH ERR", en, ex); continue
        found_titles = sr[1] if len(sr) > 1 else []
        for cand in found_titles:
            if not any(cand.lower().startswith(v.lower().split()[0]) for v in candidates) and cand.lower() not in [v.lower() for v in candidates]:
                # allow fuzzy: keep anyway if contains key word
                if title.split()[0].lower() not in cand.lower():
                    continue
            try:
                d = get({"action": "parse", "redirects": 1, "prop": "wikitext", "format": "json", "page": cand})
            except Exception as ex:
                print("ERR", en, cand, ex); continue
            if d.get("error"): continue
            wt = d["parse"].get("wikitext", {}).get("*", "")
            routes = [clean(l) for l in acquired_section(wt) if clean(l)]
            data[en] = {"zh": data[en]["zh"], "found": True, "page": d["parse"].get("title", cand), "routes": routes}
            print("OK2", en, "->", cand, len(routes))
            got = True
            break
        if got: break
        time.sleep(0.3)
    if not got:
        print("STILL MISS", en)

json.dump(data, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
miss = [k for k, v in data.items() if not v["found"] or not v["routes"]]
print("done. still empty:", miss)
