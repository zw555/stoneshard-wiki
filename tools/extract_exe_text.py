# -*- coding: utf-8 -*-
"""Extract multilingual text blocks (ru;en;zh;de;...) from StoneShard.exe (YYC build).

The game is compiled with YoYo Compiler: GML string literals live in the
native executable. UI text is stored as ';'-joined language chains such as:

    <key>;Russian;English;SimplifiedChinese;German;Spanish;French;...

This script splits the exe by NUL bytes, keeps segments that contain CJK
characters (guaranteeing the translation chain is present), and saves them
as JSONL for later structuring.
"""
import json, os, re, sys

EXE = r"E:\SteamLibrary\steamapps\common\Stoneshard\StoneShard.exe"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(OUT_DIR, exist_ok=True)

CJK = re.compile(r"[\u4e00-\u9fff]")

def printable_ratio(b: bytes) -> float:
    if not b:
        return 0.0
    ok = sum(1 for x in b if 9 <= x <= 126 or x >= 128)
    return ok / len(b)

def main():
    data = open(EXE, "rb").read()
    print(f"exe size: {len(data):,}", flush=True)
    segments = data.split(b"\x00")
    print(f"NUL-delimited segments: {len(segments):,}", flush=True)

    kept = []
    for seg in segments:
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
        kept.append(s)
    print(f"segments containing Chinese: {len(kept):,}", flush=True)

    with open(os.path.join(OUT_DIR, "exe_text_segments.jsonl"), "w", encoding="utf-8") as out:
        for s in kept:
            out.write(json.dumps({"raw": s}, ensure_ascii=False) + "\n")

    # preview
    print("--- samples ---", flush=True)
    for s in kept[:5] + kept[len(kept)//2:len(kept)//2+5]:
        print(repr(s[:160]), flush=True)

    # rough stats on ';'-chain depth
    from collections import Counter
    depths = Counter(s.count(";") for s in kept)
    common = depths.most_common(12)
    print("most common ';'-counts:", common, flush=True)

if __name__ == "__main__":
    main()
