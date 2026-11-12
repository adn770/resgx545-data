# SPDX-License-Identifier: MIT
"""Round 5 planning, offline (2026-11-12; post hoc reading of kept data, not frozen, not a result).
Q276: what the kept images of R3 p-c3 and R4 p4-o4 say about the two readings E838 left
(R-CLR: the path clears bits 5:3 of o4's word; R-OR: the tag-5 words are o0 | o3) and their kin.
Reads only resgx545-data (published sessions).  Standard library.
  python -I o4_offline.py > o4_offline.out"""
import collections
import gzip
import pathlib
import re
import struct
import sys

sys.dont_write_bytecode = True
DATA = pathlib.Path.home() / "src/resgx545-data/render"
R3 = DATA / "closing-r3-pixel"
R4 = DATA / "closing-r4-pixel"
BG = 0xff203040
W = H = 64


def rows_of(text):
    r = {}
    for ln in text.splitlines():
        m = re.search(r"row (\d+): (.*)$", ln)
        if m:
            r[int(m[1])] = [int(v, 16) for v in m[2].split()]
    return [r[i] for i in sorted(r)]


def grid(d, name):
    p = d / f"{name}.txt.gz"
    if not p.exists():
        return None
    g = rows_of(gzip.open(p).read().decode(errors="replace"))
    return g if len(g) == H and all(len(r) == W for r in g) else None


def f32(b):
    return struct.unpack("<f", struct.pack("<I", b & 0xffffffff))[0]


def hi_of(s):
    """Top 16 bits of the float of the normalised coordinate of pixel s (E570: (s + 0.5 - W/2) / (W/2))."""
    return struct.unpack("<I", struct.pack("<f", (s + 0.5 - W / 2) / (W / 2)))[0] >> 16


HI = {hi_of(s): s for s in range(W)}
assert len(HI) == W
LOWZERO = all(struct.unpack("<I", struct.pack("<f", (s + 0.5 - 32) / 32))[0] & 0xffff == 0 for s in range(W))


def markers(path, col=1, base=10):
    out = {}
    for ln in path.read_text().splitlines():
        a = ln.split("\t")
        out[a[0]] = int(a[col], base)
    return out


def tagstats(g, shift, mk):
    """Counter of tags; per tag the words whose marker field is the job's own, and exact-coordinate high halves."""
    tags, own, exact = collections.Counter(), collections.Counter(), collections.Counter()
    for y, r in enumerate(g):
        for x, v in enumerate(r):
            if v == BG:
                continue
            t = v & 15
            tags[t] += 1
            if mk is not None and (v & 0xffff) >> shift == mk:
                own[t] += 1
            if (v >> 16) in HI:
                exact[t] += 1
    return tags, own, exact


def section(title):
    print("\n" + "=" * 100 + "\n" + title + "\n" + "=" * 100)


print("premise: the float of every pixel's normalised coordinate has a zero low half:", LOWZERO)

# ------------------------------------------------------------------ A. R3 p-c3: marker bits 5:4 at the tag-5 words
section("A. R3 p-c3 (E808): low 16 bits = marker * 16 + tag, so the marker's two low bits sit at bits 5:4 of the word.\n"
        "   R-CLR (the o4 path clears bits 5:3) predicts tag-5 words with marker & ~3; anything else keeps the marker.")
d3 = R3 / "out/20261110-160415/p-c3"
m3 = markers(R3 / "bins/p-c3-markers.tsv") if (R3 / "bins/p-c3-markers.tsv").exists() else None
if m3 is None:
    cand = sorted((R3 / "bins").glob("*markers*"))
    m3 = markers(cand[0])
    print("markers file:", cand[0].name)
tot = collections.Counter()
for name in sorted(m3):
    if not re.match(r"c-.*-[xy]$", name) or name.startswith(("c-rd", "c-rdf")):
        continue
    g = grid(d3, name)
    if g is None:
        print(name, "no 64x64 grid")
        continue
    mk = m3[name]
    n5 = own = clr = other = 0
    for r in g:
        for v in r:
            if v != BG and v & 15 == 5:
                n5 += 1
                m = (v & 0xffff) >> 4
                if m == mk:
                    own += 1
                elif m == mk & ~3:
                    clr += 1
                else:
                    other += 1
    informative = mk & 3 != 0
    tot["jobs"] += 1
    if informative:
        tot["informative jobs"] += 1
        tot["tag-5 words, informative"] += n5
        tot["  own marker (bits 5:4 kept)"] += own
        tot["  marker & ~3 (bits 5:4 cleared: R-CLR)"] += clr
        tot["  other marker"] += other
    print(f"{name:14s} marker {mk:#x} (bits 5:4 = {mk & 3}) tag-5 words {n5:3d}: own marker {own:3d}, cleared {clr:3d}, other {other}")
for k, v in tot.items():
    print(f"  {k}: {v}")

# ------------------------------------------------------------------ B. R4 p4-o4: c-e709-x (0xcf5) and the marker jobs
section("B. R4 p4-o4 (E838): c-e709-x's o4 immediate is 0xcf5 (bits 5:4 set, E709's own program); marker jobs m << 6 | v << 4 | tag")
d4 = R4 / "out/20261111-205726/p4-o4"
m4 = markers(R4 / "bins/p4o4-markers.tsv")
for name in ("c-e709-x", "c-e709-y"):
    g = grid(d4, name)
    c = collections.Counter(v & 0xffff for r in g for v in r if v != BG and v & 7 == 5 and v & 15 in (5, 13))
    print(name, "low 16 bits of the tag-5 words:", {hex(k): n for k, n in sorted(c.items())})
alltags = collections.Counter()
for f in sorted(d4.glob("c-*.txt.gz")):
    name = f.name[:-7]
    g = grid(d4, name)
    base = name[:-4] if name.endswith("-rep") else name
    mk = m4.get(base[:-1] + "x")
    if mk is not None and base.endswith("-y"):
        mk += 1
    tags, own, exact = tagstats(g, 6, mk)
    alltags.update(tags)
    low6 = collections.Counter(v & 0x3f for r in g for v in r if v != BG and v & 15 in (5, 13, 6, 7, 15))
    print(f"{name:16s} tags {dict(sorted(tags.items()))}  exact-coordinate high half {dict(sorted(exact.items()))}  low6 of 5/6/7/13/15 {({hex(k): n for k, n in sorted(low6.items())})}")
print("tags over the stage:", dict(sorted(alltags.items())))

# ------------------------------------------------------------------ C. o1 dependence (R3): readings that involve o1
section("C. R3 p-c3: jobs whose o1 word is 12 at some or all instances (k rows: !p1 writes 12, p1 writes 2; k5/k7: 12 everywhere).\n"
        "   XOR(o1,o2,o3) = 2^3^4 = 5 predicts tag 13 (12^3^4) for the tag-5 words where o1 is 12 (k5, k7: all; k3: the\n"
        "   lane-0 sources).  'tag 6 = o1 | o3' predicts no tag 6 where o1 is 12 (12 | 4 = 12).")
for name in sorted(m3):
    if not re.match(r"c-(k\d|u|u-r2|e709|o4.*|g25b\d)-[xy]$", name):
        continue
    g = grid(d3, name)
    if g is None:
        continue
    tags, own, exact = tagstats(g, 4, m3[name])
    print(f"{name:14s} tags {dict(sorted(tags.items()))}  own marker {dict(sorted(own.items()))}")

# ------------------------------------------------------------------ D. positions: where the tag-5..7 words sit and come from
section("D. R4 + R3: pairs (same destination, same tag in the x and y job): source parity, displacement, the word at the source")


def pairs(gx, gy, tagset):
    out = []
    for y in range(H):
        for x in range(W):
            vx, vy = gx[y][x], gy[y][x]
            if BG in (vx, vy) or vx & 15 != vy & 15 or vx & 15 not in tagset:
                continue
            if (vx >> 16) in HI and (vy >> 16) in HI:
                out.append((vx & 15, (x, y), (HI[vx >> 16], HI[vy >> 16])))
    return out


par = collections.Counter()
disp = collections.Counter()
atsrc = collections.Counter()
dpar = collections.Counter()
unexact = collections.Counter()
for d, mm in ((d4, m4), (d3, m3)):
    for name in sorted(mm):
        if not name.endswith("-x") or name.startswith(("c-rd", "c-rdf")):
            continue
        gx, gy = grid(d, name), grid(d, name[:-1] + "y")
        if gx is None or gy is None:
            continue
        for g in (gx, gy):
            for r in g:
                for v in r:
                    if v != BG and v & 15 in (5, 6, 7) and (v >> 16) not in HI:
                        unexact[v & 15] += 1
        for t, (x, y), (sx, sy) in pairs(gx, gy, (5, 6, 7, 2, 3)):
            par[(t, sx & 1, sy & 1)] += 1
            if t in (5, 6, 7):
                dpar[(t, x & 1, y & 1)] += 1
                disp[(t, "same tile" if (x // 32, y // 16) == (sx // 32, sy // 16) else "other tile")] += 1
                vs = gx[sy][sx]
                atsrc[(t, "bg" if vs == BG else f"tag {vs & 15}" + (" own" if HI.get(vs >> 16) == sx else " displaced"))] += 1
print("source parity (tag, x&1, y&1):", dict(sorted(par.items())))
print("destination parity of tags 5..7:", dict(sorted(dpar.items())))
print("tags 5..7, destination tile vs source tile:", dict(sorted(disp.items())))
print("word at the source pixel of a tag-5..7 pair (x job):", dict(sorted(atsrc.items())))
print("tag 5..7 words whose high half is not an exact pixel coordinate:", dict(unexact))

# ------------------------------------------------------------------ E. o0-only programs (R3 rd-pa: o0 = pa | tag 15)
section("E. R3 rd-pa / rdf-pa (the program writes o0 only, tag 15): are there displaced words at all?")
for name in ("c-rd-pa-x", "c-rd-pa-y", "c-rdf-pa-x", "c-rdf-pa-y"):
    g = grid(d3, name)
    if g is None:
        print(name, "no grid")
        continue
    ax = 0 if name.endswith("x") else 1
    own = disp = 0
    tags = collections.Counter()
    for y, r in enumerate(g):
        for x, v in enumerate(r):
            if v == BG:
                continue
            tags[v & 15] += 1
            if HI.get(v >> 16) == (x, y)[ax]:
                own += 1
            else:
                disp += 1
    print(f"{name:14s} tags {dict(tags)} own-coordinate words {own}, displaced {disp}")

# ------------------------------------------------------------------ F. the rare tags (7, 12, 13, 14, 15): where, and from where
section("F. rare tags in R4 p4-o4 and R3 p-c3 (x jobs decode the source column, y jobs the source row): tag, destination, source coordinate")
for d, mm, sh, lab in ((d4, m4, 6, "R4"), (d3, m3, 4, "R3")):
    cnt = collections.Counter()
    for f in sorted(d.glob("c-*.txt.gz")):
        name = f.name[:-7]
        if name.startswith(("c-rd", "c-rdf")):
            continue
        g = grid(d, name)
        if g is None:
            continue
        ax = 1 if name.replace("-rep", "").endswith("y") else 0
        for y, r in enumerate(g):
            for x, v in enumerate(r):
                if v != BG and v & 15 in (7, 13, 14, 15):
                    cnt[v & 15] += 1
                    if lab == "R4" or v & 15 in (13, 14):
                        s = HI.get(v >> 16)
                        print(f"   {lab} {name:16s} tag {v & 15:2d} low16 {v & 0xffff:#06x} at ({x},{y}) source {'xy'[ax]} = {s} ({'even' if s is not None and s % 2 == 0 else 'odd'})")
    print(f"   {lab} totals:", dict(sorted(cnt.items())))
