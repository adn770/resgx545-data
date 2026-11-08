#!/usr/bin/env python3
"""11.26 post-hoc reading of the msaa-ident dumps (NOT the declared recompute: that one decodes
x + 0.5 / y + 0.5 and finds nothing, because the iterated position is x + 0.375, y + 0.125 even in
mode 0). Offsets are taken from the 64x64 mode 0 control (A-m0-te20-64x64) only, then applied to
every job. Per stored 32x16 tile: the source bounding box and the step in x and y."""
import gzip, os, re, struct, sys, collections
root = sys.argv[1]
OX, OY = 0.375, 0.125
def rows(p):
    img = {}
    for line in gzip.open(p, "rb").read().decode("latin-1").splitlines():
        m = re.search(r"row (\d+): (.*)$", line)
        if m:
            for x, v in enumerate(m.group(2).split()):
                try: img[(x, int(m.group(1)))] = int(v, 16)
                except ValueError: pass
    return img
def f(v): return struct.unpack("<f", struct.pack("<I", v))[0]
def src(v, off):
    x = f(v) - off
    return int(round(x)) if abs(x - round(x)) < 1e-4 and -1 < x < 4096 else None
cases = [l.rstrip("\n").split("\t") for l in open(os.path.join(root, "cases.tsv"))]
hdr = cases[0]; cases = [dict(zip(hdr, c)) for c in cases[1:]]
def tilesum(name, w, h, mode):
    X = rows(os.path.join(root, name + "-x.txt.gz")); Y = rows(os.path.join(root, name + "-y.txt.gz"))
    dec = 0; tiles = {}
    for (x, y), vx in X.items():
        vy = Y.get((x, y))
        if vy is None: continue
        sx, sy = src(vx, OX), src(vy, OY)
        if sx is None or sy is None: continue
        dec += 1
        tiles.setdefault((x // 32, y // 16), []).append((x % 32, y % 16, sx, sy))
    return len(X), dec, tiles
def read_tile(t):
    # per-axis step: number of stored columns sharing one source x in row 0 of the tile, etc.
    lx = {}; ly = {}
    for (a, b, sx, sy) in t:
        lx.setdefault(a, set()).add(sx); ly.setdefault(b, set()).add(sy)
    return lx, ly
H30 = collections.Counter()
for c in cases:
    name = c["name"]; w, h, mode = int(c["W"]), int(c["H"]), int(c["mode"]) if "mode" in c else None
    if not os.path.exists(os.path.join(root, name + "-x.txt.gz")): continue
    n, dec, tiles = tilesum(name, w, h, mode)
    # H30a, as the declared reading in its first form: stored tile (tx,ty) holds the pixels of its own
    # origin (32 tx, 16 ty), step 1 (mode 0), 2 stored per source in x (modes 1,2), y step 1 or 2
    sxs, sys_ = (1, 1) if mode == 0 else (2, 1) if mode == 1 else (2, 2)
    ok = 0; shifts = collections.Counter(); bad = 0
    for (tx, ty), t in sorted(tiles.items()):
        good = all(sx == 32 * tx + a // sxs and sy == 16 * ty + b // sys_ for (a, b, sx, sy) in t)
        full = len(t) == 32 * 16
        if good and full: ok += 1
        else:
            bad += 1
            a, b, sx, sy = t[0]
            shifts[((sx - a // sxs) // 32 - tx, (sy - b // sys_) // 16 - ty)] += 1
    ntiles = ((w + 31) // 32) * ((h + 15) // 16)
    print("%-24s %s set=%s: stored %d decodable %d tiles H30a-origin %d of %d (bad %d, tile shifts of the bad %s)" % (
        name, "%dx%d m%d te %s" % (w, h, mode, c["te"]) , c["set"], n, dec, ok, ntiles, bad, dict(shifts) or "-"))
    H30[(c["set"], c["te"], ok == ntiles)] += 1

if len(sys.argv) > 2:      # detail: a case, per tile source columns of local row 0 and rows of column 0
    for name in sys.argv[2:]:
        c = [c for c in cases if c["name"] == name][0]
        n, dec, tiles = tilesum(name, int(c["W"]), int(c["H"]), int(c["mode"]))
        for (tx, ty), t in sorted(tiles.items())[:int(os.environ.get("NT", "4"))]:
            r0 = [sx for (a, b, sx, sy) in sorted(t, key=lambda z: (z[1], z[0])) if b == 0]
            c0 = [sy for (a, b, sx, sy) in sorted(t, key=lambda z: (z[0], z[1])) if a == 0]
            print(name, "tile", (tx, ty), "n", len(t), "row0 src x:", r0, "col0 src y:", c0)

def te_rule():
    """Post-hoc rule read from the 64x64 fit: stored tile (tx,ty) holds the source pixels of origin
    (32 tx + 16 b31, 16 ty + 8 b30 [mode 2 only]), stepped 1 / 2 stored pixels per source pixel in x
    (modes 1, 2) and 1 / 1 / 2 in y (modes 0, 1, 2); fully written (512 pixels)."""
    print("== per config, tiles that equal the post-hoc rule (decodable tiles only)")
    tot = collections.Counter()
    for c in cases:
        name = c["name"]
        if not os.path.exists(os.path.join(root, name + "-x.txt.gz")): continue
        w, h, mode, te = int(c["W"]), int(c["H"]), int(c["mode"]), int(c["te"], 16)
        b31, b30 = te >> 31 & 1, te >> 30 & 1
        n, dec, tiles = tilesum(name, w, h, mode)
        sxs, sys_ = (1, 1) if mode == 0 else (2, 1) if mode == 1 else (2, 2)
        ok = 0; full = 0; part = 0
        for (tx, ty), t in tiles.items():
            ox, oy = 32 * tx + 16 * b31 * (mode > 0), 16 * ty + 8 * b30 * (mode == 2)
            good = all(sx == ox + a // sxs and sy == oy + b // sys_ for (a, b, sx, sy) in t)
            if good: ok += 1
            if len(t) == 512: full += 1
        ntiles = ((w + 31) // 32) * ((h + 15) // 16)
        print("%-24s %-9s %dx%d m%d te %s: tiles %d, with decodable pixels %d, equal to the rule %d, fully decodable %d, pixels decodable %d of %d" % (
            name, c["set"], w, h, mode, c["te"], ntiles, len(tiles), ok, full, dec, n))
        tot[(c["set"], ok == len(tiles) and len(tiles) == ntiles)] += 1
    print("configs whose every tile equals the rule, by set:", dict(tot))
if os.environ.get("RULE"): te_rule()
