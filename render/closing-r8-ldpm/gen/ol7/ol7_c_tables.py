#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ol7_c_tables.py (round 8, leftovers OL7 (c), Q210 and Q211; offline, read-only): the frozen
tables session r8-ldpm (L1) freezes from, computed from the published frozen rules only (ol7lib:
g3_span, f5lib, f9_loss, f7_replay, hu1, each hash-checked) and this directory's
ol7_b_multikick.replay_kicks (H-KICKS, frozen by FREEZE-ol7b.sha256 before its fit was read; the
fit did not reproduce 4 of 31 kept cells, so stage k scores its counts as explore). No number is
fitted here and no held-out reading is opened: L1 has not run. Writes ol7_tables.json (sorted
keys, its sha256 in FREEZE-ol7c.sha256 by the caller).

  models   per target WxH: E874's step replay S_k (lag 3), H-SPAN's A_k, E874's B_k, U (g3_span)
  f9       per cell of stage f9: F9's (count, run peaks), R-5's raise from H-SPAN's guard; the
           rivals E854's d = 7/4 and d = 1 (f7_replay.dcount) and E625's boundary (a partial
           render iff thr0 < U, no count)
  u        stage u's shapes (`tri --tri-unit 12 --tri-v ...`, one triangle): HU1's U and the rival
           H-BBOX (a stream for every region of the triangle's bounding box); the plan's five
           shapes, then the three of a fixed candidate list where the rivals part most
  k        stage k's scenes (`tri -n K --geometry 1 .. K-1 --move i:DX,DY`): the moves of the
           family move i = ((i - 1) DX, (i - 1) DY) that part H-KICKS and H-UNION in the most
           cells where both give at most 10 partial renders (E625's most at 4096x4096; a coarse
           scan, every 8th thr0), U = HU1 of the union below 0x3f0; four cells, count-parting
           ones spread evenly, then run-peak-parting ones spread evenly

  python3 -I -B ol7_c_tables.py > ol7_c_tables.out   (writes ol7_tables.json)

A first run (2026-11-13 00:51Z) was stopped after about two minutes, with no output written or
read, because the walk was recomputed at every replay; ol7lib.walk is memoised here since.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ol7lib as L  # noqa: E402
from ol7_b_multikick import replay_kicks  # noqa: E402

_WALK = L.walk
_WALKS: dict = {}


def _walk(w, h, tris):
    """ol7lib.walk memoised (the same regions in the same order; speed only)."""
    key = (w, h, tuple(tuple(tuple(p) for p in t) for t in tris))
    if key not in _WALKS:
        _WALKS[key] = _WALK(w, h, tris)
    return _WALKS[key]


L.walk = _walk

UNIT = 12
U_MAX = 0x3F0
TARGETS = [(2048, 2048), (2048, 3072), (2048, 4096), (3072, 3072), (2560, 2560), (1536, 1536),
           (1024, 1024), (4096, 2048), (3072, 2048), (2560, 3072), (3072, 2560)]
F9_CELLS = {(1536, 1536): (0x24, 0x30, 0x48, 0x60, 0x90), (1024, 1024): (0x24, 0x30, 0x48, 0x60, 0x90),
            (3072, 2048): (0x60, 0x90, 0xC0, 0x120, 0x1A0)}
K_SCENES = [(2048, 2048, 2), (2048, 2048, 3), (2048, 2048, 4), (4096, 4096, 2), (4096, 4096, 4)]
K_STEP = {2048: 256, 4096: 512}
K_SPAN = {2048: 768, 4096: 1536}


def hx(v):
    return f"0x{v:x}"


def default_winding(t):
    (ax, ay), (bx, by), (cx, cy) = t
    return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)


def bbox_u(w, h, t):
    """H-BBOX: a stream for every region (32 x 16) that meets the bounding box, HU1's pages."""
    tx, ty, n, mx, my = L.H.tiling(w, h)
    x0, x1 = min(p[0] for p in t), max(p[0] for p in t)
    y0, y1 = min(p[1] for p in t), max(p[1] for p in t)
    per = {}
    for r in range(max(0, int(y0 // 16)), min(ty, int(math.ceil(y1 / 16)))):
        for c in range(max(0, int(x0 // 32)), min(tx, int(math.ceil(x1 / 32)))):
            m = (c // mx) * n + r // my
            per[m] = per.get(m, 0) + 1
    return sum(math.ceil(k * 128 / 4096) for k in per.values()) + 1


def shape(name, w, h, pts):
    """pts in pixels -> the tool's --tri-v integers (1/4096 pixel) and both rivals' U."""
    t = [(float(x), float(y)) for x, y in pts]
    ref = default_winding(L.H.default_tri(w, h))
    if default_winding(t) * ref <= 0:
        t = [t[0], t[2], t[1]]
    v = [int(round(c * (1 << UNIT))) for p in t for c in p]
    tv = [(v[0] / 4096, v[1] / 4096), (v[2] / 4096, v[3] / 4096), (v[4] / 4096, v[5] / 4096)]
    return dict(name=name, w=w, h=h, triv=",".join(str(x) for x in v), unit=UNIT,
                U_hu1=L.u_of(w, h, [tv]), U_bbox=bbox_u(w, h, tv))


def u_shapes():
    fixed = [shape("u-full-1024", 1024, 768, [(0, 0), (2048, 0), (0, 1536)]),
             shape("u-full-2048", 2048, 2048, [(0, 0), (4096, 0), (0, 4096)]),
             shape("u-sliver", 2048, 2048, [(8, 8), (2040, 2036), (2036, 2040)]),
             shape("u-small20", 2048, 2048, [(1000, 1000), (1020, 1004), (1004, 1020)]),
             shape("u-band40", 4096, 2048, [(16, 1000), (4080, 1020), (2048, 1040)])]
    cand = [shape("u-anti-2048", 2048, 2048, [(2040, 8), (8, 2036), (12, 2040)]),
            shape("u-sliver-4096x2048", 4096, 2048, [(8, 8), (4088, 2036), (4084, 2040)]),
            shape("u-sliver-2048x4096", 2048, 4096, [(8, 8), (2040, 4084), (2036, 4088)]),
            shape("u-sliver-1024", 1024, 768, [(4, 4), (1020, 760), (1016, 764)]),
            shape("u-vert-4096x2048", 4096, 2048, [(2040, 4), (2056, 4), (2048, 2044)]),
            shape("u-fan-2048", 2048, 2048, [(8, 8), (2040, 64), (64, 2040)])]
    ok = [s for s in cand if max(s["U_hu1"], s["U_bbox"]) < U_MAX]
    ok.sort(key=lambda s: (-abs(s["U_bbox"] - s["U_hu1"]), s["name"]))
    for s in fixed:
        if max(s["U_hu1"], s["U_bbox"]) >= U_MAX:
            raise SystemExit(f"{s['name']}: U {s['U_hu1']} / {s['U_bbox']} not below 0x3f0")
    return fixed + ok[:3], ok[3:]


def kicks(w, h, K, dx, dy):
    return [[L.tri_moved(w, h, i * dx, i * dy)] for i in range(K)]


MAX_PARTS = 10


def parting(w, h, ks, U, step=1):
    cnt, pk = [], []
    union = [t for k in ks for t in k]
    for t in range(2, U, step):
        a, b = replay_kicks(w, h, ks, t), L.replay_union(w, h, union, t)
        if a is None or b is None or max(a[0], b[0]) > MAX_PARTS:
            continue
        if a[0] != b[0]:
            cnt.append(t)
        elif a[1] != b[1]:
            pk.append(t)
    return cnt, pk


def spread(xs, m):
    """m of the ascending list xs, at indices round(i (n - 1) / (m - 1)) (all of them if n <= m)."""
    if m <= 0 or not xs:
        return []
    if len(xs) <= m:
        return list(xs)
    if m == 1:
        return [xs[len(xs) // 2]]
    return [xs[i] for i in sorted({round(i * (len(xs) - 1) / (m - 1)) for i in range(m)})]


def k_scenes():
    out = []
    for w, h, K in K_SCENES:
        best = None
        s, span = K_STEP[w], K_SPAN[w]
        for dx in range(-span, span + 1, s):
            for dy in range(-span, span + 1, s):
                if (dx, dy) == (0, 0):
                    continue
                ks = kicks(w, h, K, dx, dy)
                U = L.u_of(w, h, [t for k in ks for t in k])
                if U >= U_MAX or U < 20:
                    continue
                cnt, pk = parting(w, h, ks, U, 8)
                key = (-len(cnt), -len(pk), abs(dx) + abs(dy), dx, dy)
                if best is None or key < best[0]:
                    best = (key, dx, dy, U)
        _, dx, dy, U = best
        ks = kicks(w, h, K, dx, dy)
        cnt, pk = parting(w, h, ks, U)
        cells = spread(cnt, 4)
        cells += spread(pk, 4 - len(cells))
        cells = sorted(cells)
        union = [t for k in ks for t in k]
        pred = {}
        for t in cells:
            a, b = replay_kicks(w, h, ks, t), L.replay_union(w, h, union, t)
            pred[hx(t)] = {"H-KICKS": [a[0], [hx(x) for x in a[1]]], "H-UNION": [b[0], [hx(x) for x in b[1]]]}
        out.append(dict(name=f"k{w // 1024}{h // 1024}-n{K}", w=w, h=h, K=K, move=[dx, dy], U=U,
                        cells=[hx(t) for t in cells], pred=pred, parting=[len(cnt), len(pk)]))
    return out


def main():
    res = {"models": {}, "f9": {}, "u": [], "u_spare": [], "k": []}
    for w, h in TARGETS:
        S, A, B, U = L.model(w, h)
        res["models"][f"{w}x{h}"] = {"S": {str(k): hx(v) for k, v in sorted(S.items())},
                                     "A": {str(k): hx(v) for k, v in sorted(A.items())},
                                     "B": {str(k): hx(v) for k, v in sorted(B.items())}, "U": hx(U)}
        print(f"{w}x{h}: U {U:#x} S " + " ".join(f"{k}:{v:#x}" for k, v in sorted(S.items()))
              + " | A " + " ".join(f"{k}:{v:#x}" for k, v in sorted(A.items())))
    for (w, h), cells in F9_CELLS.items():
        S, A, B, U = L.model(w, h)
        for t in cells:
            f = L.f9_count(w, h, t)
            res["f9"][f"{w}x{h}:{hx(t)}"] = {
                "F9": [f[0], [hx(x) for x in f[1]]] if f else None,
                "raised": L.guard_class(t, S, A) == "R",
                "d=7/4": L.dcount(t, U, 1.75), "d=1": L.dcount(t, U, 1.0), "E625": int(t < U)}
            print(f"f9 {w}x{h} thr0 {t:#x}: F9 {res['f9'][f'{w}x{h}:{hx(t)}']['F9']} d7/4 "
                  f"{L.dcount(t, U, 1.75)} d1 {L.dcount(t, U, 1.0)}")
    res["u"], res["u_spare"] = u_shapes()
    for s in res["u"] + res["u_spare"]:
        print(f"u {s['name']:20s} {s['w']}x{s['h']} HU1 {s['U_hu1']} H-BBOX {s['U_bbox']} --tri-v {s['triv']}")
    res["k"] = k_scenes()
    for s in res["k"]:
        print(f"k {s['name']} move {s['move']} U {s['U']} parting {s['parting']} cells {s['cells']} {s['pred']}")
    with open(os.path.join(HERE, "ol7_tables.json"), "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    main()
