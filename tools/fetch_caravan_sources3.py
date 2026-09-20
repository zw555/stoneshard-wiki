"""Re-fetch caravan material acquisition using rendered HTML (expands {{Acquired from}} template)."""
import json, io, os, re, time, urllib.request, urllib.parse, html as H

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "community_caravan_material_sources.json")
data = json.load(io.open(OUT, encoding="utf-8"))

def get(params):
    url = "https://stoneshard.com/wiki/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "ssw-wiki-builder/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if attempt == 2: raise
            time.sleep(2)

STRIP = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
TAG = re.compile(r"<[^>]+>")
def textify(s):
    s = STRIP.sub("", s)
    s = re.sub(r"<li[^>]*>", "\n* ", s)
    s = TAG.sub("", s)
    return H.unescape(s)

SEC = re.compile(r"<h[23][^>]*>(.*?)</h[23]>", re.S)
def section_html(page_html, names):
    heads = []
    for m in SEC.finditer(page_html):
        name = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        heads.append((m.start(), m.end(), name))
    for i, (pos, end, name) in enumerate(heads):
        if name.lower() in names:
            nxt = heads[i + 1][0] if i + 1 < len(heads) else len(page_html)
            return page_html[end:nxt]
    return ""

TITLE_FIX = {"cloth": "Bolt of Cloth", "Spice Box": None, "Spearmint": "Spearmint"}
manual = {  # no official wiki page — filled from official Caravan page / community research
    "Pile of Letters": ["韦伦（Verren）出售：2000 金币（人脉网络专属）"],
    "Signed Permit": ["韦伦（Verren）出售：1500 金币（往日人情专属）"],
    "Directives": ["韦伦（Verren）出售：1500 金币（本地线报专属）"],
    "Letter of Trading Authority": ["韦伦（Verren）出售：2000 金币（好客户专属）"],
}

for en in sorted(data):
    title = TITLE_FIX.get(en, en)
    if title is None:
        continue
    try:
        d = get({"action": "parse", "redirects": 1, "prop": "text", "format": "json", "page": title})
    except Exception as ex:
        print("ERR", en, ex); continue
    if d.get("error"):
        print("NOPAGE", en); continue
    ph = d["parse"]["text"]["*"]
    sec = section_html(ph, {"acquired from", "acquisition", "obtaining", "how to obtain"})
    cut = min([x for x in (sec.find('class="navbox"'), sec.find("Page last edited"), sec.find('class="mw-heading')) if x >= 0] or [len(sec)])
    sec = sec[:cut]
    txt = textify(sec)
    routes = [re.sub(r"\s*\[\d+\]\s*", "", ln).strip() for ln in txt.splitlines()]
    routes = [re.sub(r"^[\*\s•\-]+", "", ln).strip() for ln in routes]
    routes = [ln for ln in routes if len(ln) > 1
              and not re.search(r"\b(edit|edit source)\b", ln)
              and not ln.startswith(("Acquired", "Acquisition", "This item", "Material for", "^"))]
    # price
    mp = re.search(r"Price[^<]*</[^>]+>\s*", ph)
    if routes:
        data[en] = {"zh": data[en]["zh"], "found": True, "page": d["parse"].get("title", title), "routes": routes}
        print("HTML OK", en, len(routes), "|", routes[0][:60])
    else:
        print("HTML EMPTY", en)
    time.sleep(0.35)

for en, routes in manual.items():
    if not data[en]["routes"]:
        data[en]["routes"] = routes
        data[en]["manual"] = True

json.dump(data, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
empty = [k for k, v in data.items() if not v["routes"]]
print("still empty:", empty)
