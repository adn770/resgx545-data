#!/usr/bin/env python3
"""The R3GC offline models (gen/r3_geo.py) against the data they were read from (E730's twelve kept depth dumps, E625's and E779's
count claims) and against independent arithmetic.  FIT checks, not evidence.  Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import gzip  # noqa: E402
import math  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import struct  # noqa: E402

R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R3 / "gen")]
import r3_geo as M  # noqa: E402

FX = R3 / "tests/fixtures/e730"
ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


# ---- C1: rule arithmetic (independent: floats with exact binary fractions)
for w in range(2, 200, 2):
    f = 1.25 * w                                           # exact in binary: w even gives .0 or .5
    a = sum(1 for x in range(0, 400) if x + 0.5 < f)
    b = sum(1 for x in range(0, 400) if x + 1 < f)
    if M.extent("A", w, 2)[0] != a or M.extent("RSTRICT", w, 2)[0] != b:
        check(f"rule extents at W = {w}", False, f"{M.extent('A', w, 2)[0]} vs {a}, {M.extent('RSTRICT', w, 2)[0]} vs {b}")
        break
else:
    check("rule A (x + 0.5 < 1.25 W) and RSTRICT (x + 1 < 1.25 W) equal a direct count at every even W up to 198", True)
check("at E730's sizes (W = 18, 34, 50, 66, 98) A gives x < 22, 42, 62, 82, 122 (E730's extents)",
      [M.extent("A", w, 2)[0] for w in (18, 34, 50, 66, 98)] == [22, 42, 62, 82, 122])
check("... and heights 18, 26, 34, 50 give y < 22, 32, 42, 62", [M.extent("A", 2, h)[1] for h in (18, 26, 34, 50)] == [22, 32, 42, 62])
check("at E730's .5 sizes ROUND and CEIL differ from A, FLOOR and RSTRICT equal A (the controls separate A from ROUND/CEIL only)",
      all(M.extent("ROUND", w, 2)[0] == M.extent("A", w, 2)[0] + 1 and M.extent("CEIL", w, 2)[0] == M.extent("A", w, 2)[0] + 1
          and M.extent("FLOOR", w, 2)[0] == M.extent("A", w, 2)[0] and M.extent("RSTRICT", w, 2)[0] == M.extent("A", w, 2)[0]
          for w in (18, 34, 50, 66, 98)))
check("at the integer fraction (W = 20, 36, 44, 76) A = FLOOR = ROUND = CEIL and RSTRICT is one less",
      all(len({M.extent(r, w, 2)[0] for r in ("A", "FLOOR", "ROUND", "CEIL")}) == 1 and M.extent("RSTRICT", w, 2)[0] == M.extent("A", w, 2)[0] - 1
          for w in (20, 36, 44, 76)))
check("the fractions .25 / .75 cannot be built: odd sizes are refused by the tool (render.c: width % 2), so A and FLOOR agree on every even size",
      all(M.extent("A", w, 2)[0] == M.extent("FLOOR", w, 2)[0] for w in range(2, 400, 2)))

# ---- C1: E730's twelve dumps reproduce the rule-A set and the counts (the reader and the layout)
cases = {}
for ln in (FX / "cases.tsv").read_text().splitlines()[1:]:
    f = ln.split("\t")
    cases[f[0]] = f[5]
E730_COUNTS = {(34, 18): 924, (18, 18): 484, (50, 26): 1984, (66, 34): 3444, (98, 50): 7564, (34, 50): 2604}
nset = ncnt = npitch = npages = 0
for name, opts in cases.items():
    w, h = (int(re.search(rf"--{k} (\d+)", opts)[1]) for k in ("width", "height"))
    raw = gzip.open(FX / f"{name}.depth.1.bin.gz").read()
    words = struct.unpack("<%dI" % (len(raw) // 4), raw)
    st, dead = M.stored_set(words, w, h)
    nset += (st == M.band_set("A", w, h) and dead == 0)
    ncnt += len(st) == E730_COUNTS[(w, h)]
    npitch += (M.depth_ctl(w) == int(re.search(r"--depth-ctl (0x[0-9a-f]+)", opts)[1], 16))
    npages += (M.depth_pages(w, h) == int(re.search(r"--depth-pages (\d+)", opts)[1]))
check("E730's 12 kept dumps: the stored set equals rule A's, no 0xdeadbeef in the tile area", nset == 12, f"{nset} of 12")
check("... and the stored counts are E730's 924, 484, 1984, 3444, 7564, 2604", ncnt == 12, f"{ncnt} of 12")
check("the depth pitch (--depth-ctl) per width equals E730's own on all 12 jobs", npitch == 12, f"{npitch} of 12")
check("the --depth-pages formula equals E730's on all 12 jobs", npages == 12, f"{npages} of 12")
# the alternatives are refuted by the same dumps at the .5 sizes
n_round = sum(1 for name, o in cases.items()
              if M.stored_set(struct.unpack("<%dI" % (len(gzip.open(FX / f"{name}.depth.1.bin.gz").read()) // 4), gzip.open(FX / f"{name}.depth.1.bin.gz").read()),
                              int(re.search(r"--width (\d+)", o)[1]), int(re.search(r"--height (\d+)", o)[1]))[0]
              == M.band_set("ROUND", int(re.search(r"--width (\d+)", o)[1]), int(re.search(r"--height (\d+)", o)[1])))
check("E730's dumps refute ROUND on all 12 jobs", n_round == 0, str(n_round))
check("mort: 512 distinct dword indexes in a 32 x 16 tile", len({M.mort(x, y) for x in range(32) for y in range(16)}) == 512
      and max(M.mort(x, y) for x in range(32) for y in range(16)) == 511)

# ---- C1: the raster model of a single triangle
d, a = M.tri_raster([0, 0, 64 * 256, 0, 0, 64 * 256], "A", 64, 64)
check("raster model: the right triangle (0,0) (64,0) (0,64) holds 2016 pixel centres strictly inside + 64 on the diagonal",
      len(d) + len(a) >= 2016 and len(d) == sum(1 for x in range(64) for y in range(64) if x + y + 1 < 64), f"{len(d)} {len(a)}")
d1, _ = M.tri_raster([24 * 256, 8 * 256, 40 * 256, 8 * 256, 24 * 256, 20 * 256], "A", 34, 18)
check("z-tri-in lies wholly inside the band (a clip changes nothing): the band rule gives the same set as no clip",
      all(x < 42 and y < 22 for x, y in d1) and d1, str(len(d1)))
dc, ac = M.tri_raster([24 * 256, 8 * 256, 80 * 256, 8 * 256, 24 * 256, 56 * 256], "A", 36, 20)
dr, ar = M.tri_raster([24 * 256, 8 * 256, 80 * 256, 8 * 256, 24 * 256, 56 * 256], "RSTRICT", 36, 20)
check("z-tri-cross: the band edge cuts the triangle (A stores a column and a row more than RSTRICT)",
      max(x for x, _ in dc) == 44 and max(y for _, y in dc) == 24 and max(x for x, _ in dr) == 43, f"{max(x for x, _ in dc)} {max(x for x, _ in dr)}")

# ---- C2: the count family and the pairs
check("the grid of surviving pairs is the 20 of closing3/rank/q211_fit.out", len(M.PAIRS) == 20 and (-8, 27) in M.PAIRS and (0, 30) in M.PAIRS)
check("every pair fits E625's 10 and E779's 9 cells", all(M.count(287, k, s, P) == n for k, s in M.PAIRS for P, n in {**M.E625_COUNTS, **M.E779_COUNTS}.items()))
check("the grid is complete: the search range holds no other pair (k -60..60, s 1..0x5f)", len(M.fit_pairs()) == 20)
check("the 19 fit cells are the cells where the pairs split, 0x24 .. 0xa2",
      M.split_cells() == [0x24, 0x25, 0x27, 0x28, 0x29, 0x2c, 0x2d, 0x31, 0x32, 0x39, 0x3a, 0x43, 0x44, 0x53, 0x54, 0x6d, 0x6e, 0xa1, 0xa2])
check("the 19 cells leave 13 classes of pairs (some pairs agree on every cell at U = 287)",
      len(M.classes(M.PAIRS, [(287, P) for P in M.split_cells()])) == 13)
ho = M.pick_heldout()
sel = [(287, P) for P in M.split_cells()] + [(M.SCENES[s][0], P) for s, cells in ho.items() for P in cells]
check("the held-out cells (6 a scene) separate all 20 pairs", len(M.classes(M.PAIRS, sel)) == 20 and all(len(v) == 6 for v in ho.values()), str(ho))
check("no held-out cell predicts more than 9 partial renders for any pair (E625 ran up to 10)",
      all(max(M.count(M.SCENES[s][0], k, sx, P) for k, sx in M.PAIRS) <= 9 for s, cells in ho.items() for P in cells))
check("each scene has one cell where all 20 pairs agree (a plain test of the family at the new U)",
      all(sum(1 for P in cells if len({M.count(M.SCENES[s][0], k, sx, P) for k, sx in M.PAIRS}) == 1) == 1 for s, cells in ho.items()))
check("thr0 + 0x20 <= C = 0x371 holds at every cell (4096x4096, so the raise rule is in the same regime)", all(P - 0x22 + 0x20 <= 0x371 for P in range(0x23, 0x141)))
check("count() against a direct loop (aborts at thr0, then every thr0 + s pages)",
      all(M.count(U, k, s, P) == (lambda t: 1 + (U + k - t) // (t + s) if U + k >= t else 1)(P - 0x22)
          for U in (275, 287, 438) for k, s in M.PAIRS for P in range(0x23, 0x140)))
sys.exit(0 if ok else 1)
