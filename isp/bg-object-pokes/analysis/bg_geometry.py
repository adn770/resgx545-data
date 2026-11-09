#!/usr/bin/env python3
"""Explore: does a background object whose vertex words are as poked (read from the kept parameter dump) cover the
pixels a plain geometry says? python3 -B analysis/bg_geometry.py DIR   (DIR = the bg-words dump directory).
Vertices as the object holds them: TL (dw9, dw10), TR (dw11, dw12), BL (dw14, dw15), each Y then X as 24-bit fixed point
with 8 fraction bits and the offset 4096; the fourth corner TR + BL - TL; a pixel is covered when its centre is inside the
parallelogram. Compared with the pixels of the job's image that are not the target's initial 0xdeadbeef."""
import gzip, pathlib, re, struct, sys
d = pathlib.Path(sys.argv[1])
OFF = 0x463000
def rd(p): return gzip.open(p).read() if p.exists() else None
def verts(w):
    def pt(y, x): return ((x - 0x100000) / 256.0, (y - 0x100000) / 256.0)
    tl = pt(w[9] & 0xffffff, (w[9] >> 24) | (w[10] & 0xffff) << 8)
    tr = pt((w[11] >> 16) | (w[12] & 0xff) << 16, w[12] >> 8)
    bl = pt(w[14] & 0xffffff, (w[14] >> 24) | (w[15] & 0xffff) << 8)
    return tl, tr, bl
def inside(tl, tr, bl, cx, cy):
    ux, uy = tr[0] - tl[0], tr[1] - tl[1]; vx, vy = bl[0] - tl[0], bl[1] - tl[1]
    det = ux * vy - uy * vx
    if det == 0: return False
    px, py = cx - tl[0], cy - tl[1]
    a = (px * vy - py * vx) / det; b = (ux * py - uy * px) / det
    return 0 < a < 1 and 0 < b < 1
def cover(txt):
    rows = {}
    for line in txt.decode().splitlines():
        m = re.search(r"row (\d+): (.*)$", line)
        if m: rows[int(m.group(1))] = m.group(2).split()
    return {(x, y) for y in rows for x, v in enumerate(rows[y]) if v.lower().lstrip("0x") != "deadbeef"}, len(rows)
res = []
for t in sorted(d.glob("b66-*.txt.gz")):
    name = t.name[:-7]
    pb = rd(d / (name + ".param.bin.gz")); tx = rd(t)
    if not pb or not tx: continue
    w = struct.unpack_from("<17I", pb, OFF)
    obs, nrows = cover(tx)
    if not nrows: continue
    tl, tr, bl = verts(w)
    pred = {(x, y) for x in range(64) for y in range(64) if inside(tl, tr, bl, x + .5, y + .5)}
    res.append((name, len(obs), len(pred), len(obs ^ pred)))
    print("%-16s observed %4d predicted %4d symmetric difference %4d  TL %s TR %s BL %s" % (name, len(obs), len(pred), len(obs ^ pred), tl, tr, bl))
print("jobs %d, geometry exact in %d" % (len(res), sum(1 for r in res if r[3] == 0)))
