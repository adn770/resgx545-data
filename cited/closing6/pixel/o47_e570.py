# SPDX-License-Identifier: MIT
"""Round 6 planning, Q276, offline step O3 (post hoc reading of E570's kept images, 68 jobs; exploration, nothing held out).
E570's shader: o0..o7 each = the pixel's own x (x job) or y (y job) float with low 16 bits = marker * 16 + tag (tag = j + 1).
For every configuration (x job, y job) and every tag: paired words (same low nibble at one pixel of both images), split into
  own       : source pixel == destination
  regular   : same place in the 32x16 tile, another tile (tile step in raster index reported)
  irregular : everything else (source parity reported)
The question for round 6: does any target shape show REGULAR words of tag 4..8 (an own word of o3..o7, as o1 and o2 land), or
only irregular ones from (even, even) sources (the OR words of E858)?
Reads only usse/output-room-tiles of resgx545-data.  Standard library only."""
import collections, gzip, pathlib, re, struct, sys
D = pathlib.Path("/Users/jtorra/src/resgx545-data/usse/output-room-tiles/dumps")
def fl(v): return struct.unpack('<f', struct.pack('<I', v & 0xffff0000))[0]
def grid(p):
    rows = {}
    for line in gzip.open(p, "rt", errors="replace"):
        m = re.match(r"probe \S+: row (\d+): (.*)$", line)
        if m: rows[int(m[1])] = [int(v, 16) for v in m[2].split()]
    return [rows[i] for i in sorted(rows)]
tot = collections.defaultdict(collections.Counter)
single = collections.Counter()
for tab in ("o23-tiles", "o23-order", "o23-size"):
    names = sorted({p.name[:-9] for p in (D / tab).glob("*-x.txt.gz")})
    for n in names:
        gx, gy = grid(D / tab / f"{n}-x.txt.gz"), grid(D / tab / f"{n}-y.txt.gz")
        if not gx or len(gx) != len(gy): print(tab, n, "no grid"); continue
        H, W = len(gx), len(gx[0]); TW = -(-W // 32)
        bgx = collections.Counter(v for r in gx for v in r).most_common(1)[0][0]
        mk = lambda g: collections.Counter((v & 0xffff) >> 4 for r in g for v in r if v != bgx and (v & 15) == 1).most_common(1)[0][0]
        mx, my = mk(gx), mk(gy)        # the job's marker: the commonest marker of its tag-1 words (non-marker words exist at some sizes)
        for g, m in ((gx, mx), (gy, my)):                      # single images too: any word with the job's marker, by tag
            for r in g:
                for v in r:
                    if v != bgx and ((v & 0xffff) >> 4) == m: single[v & 15] += 1
        c = collections.defaultdict(collections.Counter); steps = collections.defaultdict(collections.Counter)
        par = collections.defaultdict(collections.Counter)
        for y in range(H):
            for x in range(W):
                vx, vy = gx[y][x], gy[y][x]
                if vx == bgx or (vx & 15) != (vy & 15): continue
                if ((vx & 0xffff) >> 4) != mx or ((vy & 0xffff) >> 4) != my: continue    # both words carry their job's marker
                t = vx & 15
                sx, sy = round(fl(vx) * W / 2 + W / 2 - .5), round(fl(vy) * H / 2 + H / 2 - .5)
                if not (0 <= sx < W and 0 <= sy < H): c[t]["offtarget"] += 1; continue
                if (sx, sy) == (x, y): c[t]["own"] += 1
                elif (sx % 32, sy % 16) == (x % 32, y % 16):
                    c[t]["regular"] += 1
                    steps[t][(sy // 16 * TW + sx // 32) - (y // 16 * TW + x // 32)] += 1
                else:
                    c[t]["irregular"] += 1; par[t][(sx & 1, sy & 1)] += 1
        line = f"{tab} {n} {W}x{H} m {mx:#x}/{my:#x}:"
        for t in sorted(c):
            line += f" | t{t} own {c[t]['own']} reg {c[t]['regular']}{dict(steps[t]) if steps[t] else ''} irr {c[t]['irregular']}{dict(par[t]) if par[t] else ''}"
            for kk in ("own", "regular", "irregular"): tot[t][kk] += c[t][kk]
            if t >= 4:
                for s, v in steps[t].items(): tot[t][f"step{s}"] += v
                for s, v in par[t].items(): tot[t][f"irrpar{s}"] += v
        print(line)
print()
for t in sorted(tot): print("tag", t, dict(tot[t]))
print("single-image words carrying their job's marker, by tag (68 jobs):", dict(sorted(single.items())))
