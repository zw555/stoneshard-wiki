# -*- coding: utf-8 -*-
"""Parse GameMaker data.win STRG chunk: dump all strings to JSON."""
import struct, json, os

DATA_WIN = r"E:\SteamLibrary\steamapps\common\Stoneshard\data.win"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(OUT_DIR, exist_ok=True)

def read_chunk_offsets(f):
    f.seek(0)
    assert f.read(4) == b"FORM"
    f.seek(8)  # skip FORM header (name + total size)
    chunks = {}
    while True:
        hdr = f.read(8)
        if len(hdr) < 8:
            break
        name = hdr[:4].decode("ascii", "replace")
        size = struct.unpack("<I", hdr[4:8])[0]
        chunks[name] = (f.tell(), size)
        f.seek(size, 1)
    return chunks

def read_string_at(f, base, p):
    f.seek(base + p)
    ln = struct.unpack("<I", f.read(4))[0]
    if ln > 1_000_000:
        return None
    return f.read(ln).decode("utf-8", "replace")

def main():
    f = open(DATA_WIN, "rb")
    chunks = read_chunk_offsets(f)
    off, size = chunks["STRG"]
    f.seek(off)
    count = struct.unpack("<I", f.read(4))[0]
    print(f"STRG chunk @ {off}, size {size:,}, count={count}", flush=True)
    ptrs = struct.unpack(f"<{count}I", f.read(4 * count))
    print(f"first pointers: {ptrs[:5]}", flush=True)
    # this build stores STRG pointers as absolute file offsets (verified:
    # ptrs[0] == off + 4 + count*4, right after the pointer list)
    base = 0
    strings = []
    bad = 0
    for i, p in enumerate(ptrs):
        s = read_string_at(f, base, p)
        if s is None:
            bad += 1
            s = ""
        strings.append(s)
        if i in (0, 1000, 10000, len(ptrs) - 1):
            print(f"  progress {i}: {s[:50]!r}", flush=True)
    print(f"bad strings: {bad}", flush=True)
    with open(os.path.join(OUT_DIR, "strings.json"), "w", encoding="utf-8") as out:
        json.dump(strings, out, ensure_ascii=False)
    cjk = [s for s in strings if any("\u4e00" <= ch <= "\u9fff" for ch in s)]
    print(f"total strings: {len(strings)}, CJK strings: {len(cjk)}", flush=True)
    print("--- sample Chinese strings (15) ---", flush=True)
    for s in cjk[:15]:
        print(repr(s[:80]), flush=True)

if __name__ == "__main__":
    main()
