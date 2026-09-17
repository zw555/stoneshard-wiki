# -*- coding: utf-8 -*-
"""Structure the raw multilingual segments from StoneShard.exe into a clean
bilingual (EN/ZH + others) localization database.

Formats observed:
  A) 14 ';'-columns: [key];ru;en;zh;de;es;fr;it;pt;pl;tr;ja;ko;   (12,260)
  B) 19 ';'-columns: id;Tags;Role;Type;Faction;Settlement;ru;en;zh;de;es;fr;it;pt;pl;tr;ja;ko;
     (NPC dialogue with metadata, 4,103)

Some format-A entries have an empty key — the key often lives in the
preceding NUL-delimited segment, so we capture that as `prev_context`.
"""
import json, os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
EXE = r"E:\SteamLibrary\steamapps\common\Stoneshard\StoneShard.exe"

LANGS = ["ru", "en", "zh", "de", "es", "fr", "it", "pt", "pl", "tr", "ja", "ko"]
CJK = __import__("re").compile(r"[\u4e00-\u9fff]")


def printable_ratio(b):
    if not b:
        return 0.0
    return sum(1 for x in b if 9 <= x <= 126 or x >= 128) / len(b)


def main():
    data = open(EXE, "rb").read()
    segments = data.split(b"\x00")

    records = []
    prev_raw = b""
    for seg in segments:
        kept_prev = prev_raw
        prev_raw = seg
        if len(seg) < 8 or len(seg) > 200_000:
            continue
        if printable_ratio(seg) < 0.9:
            continue
        try:
            s = seg.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if not CJK.search(s):
            continue
        n = s.count(";")
        parts = s.split(";")
        if n == 13 and len(parts) == 14:
            key = parts[0].strip()
            vals = parts[1:13]
            rec = {"fmt": "ui", "key": key, "prev": ""}
        elif n == 18 and len(parts) == 19:
            rec = {
                "fmt": "dlg",
                "key": parts[0].strip(),
                "tags": parts[1].strip(),
                "role": parts[2].strip(),
                "type": parts[3].strip(),
                "faction": parts[4].strip(),
                "settlement": parts[5].strip(),
            }
            vals = parts[6:18]
        else:
            continue
        if rec.get("key") == "":
            try:
                rec["prev"] = kept_prev.decode("utf-8", "replace")[:200]
            except Exception:
                rec["prev"] = ""
        rec.update({lang: v.strip() for lang, v in zip(LANGS, vals)})
        records.append(rec)

    print(f"parsed records: {len(records)}")
    fmt = Counter(r["fmt"] for r in records)
    print("by format:", dict(fmt))
    ui = [r for r in records if r["fmt"] == "ui"]
    keyed = sum(1 for r in ui if r["key"])
    print(f"ui records with key: {keyed}/{len(ui)}")
    withkey = Counter()
    for r in ui:
        k = r["key"]
        if k:
            pref = k.split("_")[0][:12]
            withkey[pref] += 1
        elif r["prev"]:
            pref = r["prev"].split("_")[0][:12]
            withkey["prev:" + pref] += 1
    print("top key prefixes:", withkey.most_common(25))

    out = os.path.join(DATA, "localization.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("saved ->", out, f"({os.path.getsize(out):,} bytes)")

    # preview some zh translations
    print("--- sample ui entries with keys ---")
    shown = 0
    for r in ui:
        if r["key"] and r["en"] and r["zh"] and shown < 15:
            print(f"  {r['key'][:40]:42} | {r['en'][:45]:47} | {r['zh'][:30]}")
            shown += 1

if __name__ == "__main__":
    main()
