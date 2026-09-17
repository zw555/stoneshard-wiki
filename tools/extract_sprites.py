# -*- coding: utf-8 -*-
"""Extract all sprites (icons/frames) from Stoneshard data.win.

Pipeline:
  SPRT (sprite table, absolute pointers)  -> names (via STRG) + frame lists
  TPAG (155k texture page items, 22-byte entries, u16 fields)
  TXTR (149 texture pages, QOIZ container: magic + w/h + bzip2 + QOI variant)

Output:
  data/sprites.json  - metadata for every sprite (name, size, frames, pages)
  site/icons/<name>.png - first frame of every sprite (the "icon")
"""
import struct, bz2, zlib, os, json, time
from PIL import Image

DATA_WIN = r"E:\SteamLibrary\steamapps\common\Stoneshard\data.win"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
ICON_DIR = os.path.join(SITE, "icons")
PAGE_CACHE = os.path.join(ROOT, "data", "pagecache")
os.makedirs(ICON_DIR, exist_ok=True)
os.makedirs(PAGE_CACHE, exist_ok=True)


def load_chunks(data):
    chunks = {}
    off = 8
    while off + 8 <= len(data):
        name = data[off:off + 4].decode("ascii", "replace")
        size = struct.unpack_from("<I", data, off + 4)[0]
        chunks[name] = (off + 8, size)
        off += 8 + size
    return chunks


def read_strg_strings(data, chunks):
    """Return list of (offset, length) or just parse names on demand via pointer."""
    off, size = chunks["STRG"]
    cnt = struct.unpack_from("<I", data, off)[0]
    ptrs = struct.unpack_from(f"<{cnt}I", data, off + 4)
    return ptrs


def read_strg_name(data, ptr):
    """SPRT name pointers aim directly at the string bytes (NUL-terminated)."""
    if ptr == 0 or ptr >= len(data):
        return ""
    end = data.find(b"\x00", ptr, ptr + 256)
    if end < 0:
        end = ptr + 256
    return data[ptr:end].decode("utf-8", "replace")


def qoiz_decode(blob, expect_w, expect_h):
    """QOIZ container -> raw RGBA bytearray."""
    assert blob[12:16] == b"BZh9", blob[:16]
    qoi = bz2.decompress(blob[12:])
    assert qoi[:4] == b"fioq", qoi[:8]
    w = int.from_bytes(qoi[4:6], "little")
    h = int.from_bytes(qoi[6:8], "little")
    assert (w, h) == (expect_w, expect_h), (w, h, expect_w, expect_h)
    return qoi_decode(qoi, w, h)


def qoi_decode(qoi, w, h):
    """Decode GameMaker's custom QOI variant (per libgm implementation).

    Header: 'fioq' + width u16LE + height u16LE + length u32LE (12 bytes).
    Chunks: INDEX(0x00-0x3F), RUN_8(0x40-0x5F), RUN_16(0x60-0x7F),
            DIFF_8(0x80-0xBF), DIFF_16(0xC0-0xDF), DIFF_24(0xE0-0xEF),
            COLOR(0xF0-0xFF with per-channel mask).
    Initial pixel: rgba(0,0,0,255); index table starts as rgba(0,0,0,0);
    index hash: (r^g^b^a) & 0x3F.
    """
    npx = w * h
    out = bytearray(npx * 4)
    data = qoi
    pos = 12
    length = len(qoi)
    run = 0
    pr = pg = pb = 0
    pa = 255
    index = bytearray(256)  # 64 entries x 4 bytes, all zero (a=0)
    o = 0
    i = 0
    while i < npx:
        if run > 0:
            run -= 1
            out[o] = pr; out[o + 1] = pg; out[o + 2] = pb; out[o + 3] = pa
            o += 4; i += 1
            continue
        if pos >= length:
            # fill the rest with last pixel (should not happen for well-formed data)
            while i < npx:
                out[o] = pr; out[o + 1] = pg; out[o + 2] = pb; out[o + 3] = pa
                o += 4; i += 1
            break
        b1 = data[pos]; pos += 1
        if b1 & 0xC0 == 0x00:  # INDEX
            k = (b1 & 0x3F) * 4
            pr = index[k]; pg = index[k + 1]; pb = index[k + 2]; pa = index[k + 3]
        elif b1 & 0xE0 == 0x40:  # RUN_8 -> run+1 pixels
            run = b1 & 0x1F
        elif b1 & 0xE0 == 0x60:  # RUN_16 -> run+32+1 pixels
            run = ((b1 & 0x1F) << 8 | data[pos]) + 32
            pos += 1
        elif b1 & 0xC0 == 0x80:  # DIFF_8
            r = (b1 & 0x30) << 26 >> 30  # arithmetic-ish: [-2..1]
            g = (b1 & 0x0C) << 28 >> 30
            b = (b1 & 0x03) << 30 >> 30
            if r > 1: r -= 4
            if g > 1: g -= 4
            if b > 1: b -= 4
            pr = (pr + r) & 255; pg = (pg + g) & 255; pb = (pb + b) & 255
        elif b1 & 0xE0 == 0xC0:  # DIFF_16
            b2 = data[pos]; pos += 1
            merged = (b1 << 8) | b2
            r = (merged & 0x1F00) << 19 >> 27
            g = (merged & 0x00F0) << 24 >> 28
            b = (merged & 0x000F) << 28 >> 28
            if r > 15: r -= 32
            if g > 7: g -= 16
            if b > 7: b -= 16
            pr = (pr + r) & 255; pg = (pg + g) & 255; pb = (pb + b) & 255
        elif b1 & 0xF0 == 0xE0:  # DIFF_24
            b2 = data[pos]; b3 = data[pos + 1]; pos += 2
            merged = (b1 << 16) | (b2 << 8) | b3
            r = (merged & 0x0F8000) << 12 >> 27
            g = (merged & 0x007C00) << 17 >> 27
            b = (merged & 0x0003E0) << 22 >> 27
            a = (merged & 0x00001F) << 27 >> 27
            if r > 15: r -= 32
            if g > 15: g -= 32
            if b > 15: b -= 32
            if a > 15: a -= 32
            pr = (pr + r) & 255; pg = (pg + g) & 255; pb = (pb + b) & 255; pa = (pa + a) & 255
        elif b1 & 0xF0 == 0xF0:  # COLOR with mask
            if b1 & 8: pr = data[pos]; pos += 1
            if b1 & 4: pg = data[pos]; pos += 1
            if b1 & 2: pb = data[pos]; pos += 1
            if b1 & 1: pa = data[pos]; pos += 1
        # update index: hash (r^g^b^a) & 0x3F
        k = ((pr ^ pg ^ pb ^ pa) & 0x3F) * 4
        index[k] = pr; index[k + 1] = pg; index[k + 2] = pb; index[k + 3] = pa
        out[o] = pr; out[o + 1] = pg; out[o + 2] = pb; out[o + 3] = pa
        o += 4; i += 1
    return out


def png_encode(w, h, rgba):
    def chunk(tag, payload):
        c = struct.pack(">I", len(payload)) + tag + payload
        return c + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    stride = w * 4
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b""))


def main():
    t00 = time.time()
    print("loading data.win ...", flush=True)
    data = open(DATA_WIN, "rb").read()
    chunks = load_chunks(data)

    # ---- TXTR pages ----
    toff, _ = chunks["TXTR"]
    n_pages = struct.unpack_from("<I", data, toff)[0]
    page_ptrs = struct.unpack_from(f"<{n_pages}I", data, toff + 4)
    pages = []  # (w, h, rgba bytes)
    for i, ptr in enumerate(page_ptrs):
        e = struct.unpack_from("<7I", data, ptr)
        size, w, h, dataptr = e[2], e[3], e[4], e[6]
        cache = os.path.join(PAGE_CACHE, f"page_{i}_{w}x{h}.png")
        if os.path.exists(cache):
            im = Image.open(cache).convert("RGBA")
            rgba = im.tobytes()
        else:
            blob = data[dataptr:dataptr + size]
            rgba = qoiz_decode(blob, w, h)
            Image.frombytes("RGBA", (w, h), bytes(rgba)).save(cache, compress_level=1)
        pages.append((w, h, rgba))
        if i < 3 or i == n_pages - 1:
            print(f"  page {i+1}/{n_pages}: {w}x{h} loaded", flush=True)
    print(f"all {n_pages} texture pages decoded in {time.time()-t00:.1f}s", flush=True)

    # ---- TPAG entries ----
    poff, psize = chunks["TPAG"]
    n_tpi = struct.unpack_from("<I", data, poff)[0]
    tpi_ptrs = struct.unpack_from(f"<{n_tpi}I", data, poff + 4)
    tpi_set = set(tpi_ptrs)
    tpis = {}
    for ptr in tpi_ptrs:
        v = struct.unpack_from("<11H", data, ptr)
        tpis[ptr] = v  # srcX,srcY,srcW,srcH,tgtX,tgtY,tgtW,tgtH,boundW,boundH,tex
    print(f"TPAG entries: {n_tpi}", flush=True)

    # ---- SPRT entries ----
    soff, _ = chunks["SPRT"]
    n_spr = struct.unpack_from("<I", data, soff)[0]
    spr_ptrs = struct.unpack_from(f"<{n_spr}I", data, soff + 4)
    print(f"SPRT entries: {n_spr}", flush=True)

    sprites = []
    failed = 0
    total_frames = 0
    for si, sptr in enumerate(spr_ptrs):
        end = spr_ptrs[si + 1] if si + 1 < n_spr else soff + chunks["SPRT"][1]
        name = read_strg_name(data, struct.unpack_from("<I", data, sptr)[0])
        w, h = struct.unpack_from("<2I", data, sptr + 4)
        # scan for maximal run of TPAG-valid pointers
        best = (0, None)  # (len, start_pos)
        pos = 16
        while pos + 4 <= end - sptr:
            u = struct.unpack_from("<I", data, sptr + pos)[0]
            if u in tpi_set:
                run = 1
                while pos + 4 * run + 4 <= end - sptr:
                    u2 = struct.unpack_from("<I", data, sptr + pos + 4 * run)[0]
                    if u2 in tpi_set:
                        run += 1
                    else:
                        break
                if run > best[0]:
                    best = (run, pos)
                pos += run * 4
            else:
                pos += 4
        runlen, runpos = best
        if runlen == 0:
            failed += 1
            continue
        frames_raw = struct.unpack_from(f"<{runlen}I", data, sptr + runpos)
        frames = []
        for fp in frames_raw:
            v = tpis[fp]
            frames.append({
                "x": v[0], "y": v[1], "sw": v[2], "sh": v[3],
                "tx": v[4], "ty": v[5], "bw": v[8], "bh": v[9], "page": v[10],
            })
        total_frames += runlen
        sprites.append({"name": name, "w": w, "h": h, "nframes": runlen, "frames": frames})
    print(f"sprites parsed: {len(sprites)}, failed: {failed}, total frames: {total_frames} (TPAG total: {n_tpi})", flush=True)

    # ---- save metadata ----
    meta = [{"name": s["name"], "w": s["w"], "h": s["h"], "nframes": s["nframes"]} for s in sprites]
    with open(os.path.join(ROOT, "data", "sprites.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    with open(os.path.join(ROOT, "data", "sprites_frames.json"), "w", encoding="utf-8") as f:
        json.dump(sprites, f, ensure_ascii=False)

    # ---- export first-frame icons ----
    used = {}
    t0 = time.time()
    for idx, s in enumerate(sprites):
        f0 = s["frames"][0]
        pw, ph, rgba = pages[f0["page"]]
        bw, bh = f0["bw"], f0["bh"]
        sw, sh = f0["sw"], f0["sh"]
        if bw == 0: bw = sw
        if bh == 0: bh = sh
        canvas = bytearray(bw * bh * 4)  # transparent
        for yy in range(sh):
            sy = f0["y"] + yy
            ty = f0["ty"] + yy
            if ty < 0 or ty >= bh:
                continue
            src = (sy * pw + f0["x"]) * 4
            dst = (ty * bw + f0["tx"]) * 4
            cnt = min(sw, bw - f0["tx"]) * 4
            canvas[dst:dst + cnt] = rgba[src:src + cnt]
        name = s["name"] or f"sprite_{idx}"
        if name in used:
            used[name] += 1
            fname = f"{name}_{used[name]}"
        else:
            used[name] = 0
            fname = name
        safe = "".join(c if c not in '\\/:*?"<>|' else "_" for c in fname)
        outpath = os.path.join(ICON_DIR, safe + ".png")
        if not os.path.exists(outpath):
            im = Image.frombytes("RGBA", (bw, bh), bytes(canvas))
            im.save(outpath, compress_level=1)
        if (idx + 1) % 2000 == 0:
            print(f"  icons {idx+1}/{len(sprites)} ({time.time()-t0:.1f}s)", flush=True)
    print(f"exported {len(sprites)} icons in {time.time()-t0:.1f}s", flush=True)
    print(f"DONE total {time.time()-t00:.1f}s", flush=True)


if __name__ == "__main__":
    main()
