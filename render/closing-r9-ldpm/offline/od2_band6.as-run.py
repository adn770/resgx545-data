#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""od2_band6.py (round 9, S9-ldpm offline step OD-2, Q210: where band 6 keeps the second global page
past A_6; offline, read-only, standard library only).

Reads r8-ldpm's kept rows (render-closing-r8-ldpm, here its scratch copy closing8/r8-ldpm/out,
read-only) with r8-ldpm's frozen reader (score/read.py, imported from that directory).

  (a) The "left 0x6" cells (seeds finding 6): every kept row of r8-ldpm with a partial render,
      `left` (the frozen reader: the last sample of the first partial render) against `next` (the
      first sample after it); the timelines of the cells where they differ, around the stretch.
  (b) Per target of m6 (and the 2048x2048 controls): A_6 (H-SPAN), the frozen replay's page count
      after tiling objects b_6 + d (d = 0 .. 4; f5lib through ol7lib, hash-checked), and the
      first thr0 whose first partial render leaves 1 global page (read with `next` where `left`
      is the artefact of (a)).
  (c) Candidates, each written here before the comparison (all from the frozen replay, no number
      fitted but d):
        H-NEXTd   the second page is kept while thr0 < after[b_6 + d] (d = 0 is H-SPAN)
        H-HALFd   ... while thr0 < A_6 + ceil(d (after[b_6 + 1] - A_6) / 2)   [a half-object]
      FIT: d chosen on the two mapped targets (3072x3072, 2560x2560: both must hold).
      Held out offline: the other eight targets' cells (2048x2048 controls, 1536x1536, 1024x1024,
      4096x2048, 3072x2048, 2048x3072, 2560x3072, 3072x2560); SEMI, since E936 printed them.
      A candidate is frozen for m6b only if it is exact on at least 7 of the 8 (the plan).

  python3 -I -B od2_band6.py > od2_band6.out
"""
import collections
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ol7lib as L  # noqa: E402

R8 = os.path.normpath(os.path.join(HERE, "../../../closing8/r8-ldpm"))
ATT = os.path.join(R8, "out/20261113-021431")
sys.path.insert(0, os.path.join(R8, "score"))
import read as R  # noqa: E402

MAPPED = [(3072, 3072), (2560, 2560)]
HELD = [(2048, 2048), (1536, 1536), (1024, 1024), (4096, 2048), (3072, 2048), (2048, 3072),
        (2560, 3072), (3072, 2560)]
TAG = {(w, h): f"c{w // 256:02d}{h // 256:02d}" for w, h in MAPPED + HELD}


def hx(v):
    return "-" if v is None else f"0x{v:x}"


def rows_of(stage):
    import csv
    d = os.path.join(ATT, stage)
    for r in csv.DictReader(open(os.path.join(d, "cases.tsv")), delimiter="\t"):
        p = os.path.join(d, r["name"] + ".txt.gz")
        if os.path.exists(p):
            yield r, gzip.open(p).read().decode(errors="replace")


def thr0_of(r):
    k = next(w for w in r["knobs"].split() if w.startswith("dbg:render_pb_pages="))
    return int(k.split("=")[1], 16) - 0x22


def target(args):
    a = args.split()
    return int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])


def left_next(text):
    regs, rows, start = R.parse(text)
    rd = R.reading(text)
    if rd.get("void") or not rd["nparts"]:
        return rd, None, None, None
    st = R.stretches(rows)
    a, e = st[0]
    nxt = R.hi(rows[e + 1][1][0x72C]) if e + 1 < len(rows) else None
    return rd, rd["gps_left"], nxt, (rows, a, e)


def part_a():
    print("== (a) left (last sample of the first partial render) against next (the first sample after)")
    diff, same = [], 0
    for st in ("a0", "sp", "m6", "f9"):
        for r, text in rows_of(st):
            rd, left, nxt, tl = left_next(text)
            if left is None:
                continue
            if left == nxt:
                same += 1
                continue
            t = thr0_of(r)
            w, h = target(r["args"])
            S = rd["S"]
            step = t in S.values()
            diff.append((st, r["name"], t, left, nxt, step))
            rows, a, e = tl
            print(f"{st} {r['name']} {w}x{h} thr0 {t:#x}: left {left} next {nxt}; read steps {sorted(S.items())[-2:]};"
                  f" thr0 a read step: {step}")
            for i in range(max(0, a - 2), min(len(rows), e + 3)):
                tm, v = rows[i]
                print(f"    t {tm:>8} 0x0658 {v[0x658] & 1} 0x0724 hi {R.hi(v[0x724]):#x} lo {R.lo(v[0x724]):#x}"
                      f"  0x072c hi {R.hi(v[0x72C])} lo {R.lo(v[0x72C])}")
    print(f"left = next at {same} rows; differ at {len(diff)}:")
    for d in diff:
        print("   ", d)
    return diff


def observed():
    """{target: {thr0: pages left}} of m6 and the 2048x2048 m6 controls, `next` where `left` is
    above the abort's count (the (a) artefact), else `left`."""
    out = collections.defaultdict(dict)
    for r, text in rows_of("m6"):
        if "--vtx-coords" in r["args"] or "-cal-" in r["name"] or "-b7-" in r["name"] or "-b4-" in r["name"]:
            continue
        rd, left, nxt, _ = left_next(text)
        if left is None:
            continue
        val = nxt if rd["gps_abort"] is not None and left > rd["gps_abort"] else left
        out[target(r["args"])][thr0_of(r)] = val
    return out


def cand_end(name, d, w, h):
    S, A, B, U = L.model(w, h)
    _, _, after = L.F5.replay(w, h, L.ents(w, h), 3)
    b6 = L.F5.bk(6)
    if name == "H-NEXT":
        return after[b6 + d]
    if name == "H-HALF":
        return A[6] + -(-d * (after[b6 + 1] - A[6]) // 2)
    raise ValueError(name)


def holds(name, d, w, h, cells):
    """every cell of the target: 2 iff thr0 < E (above S_6), else 1; a step cell skipped."""
    S, A, B, U = L.model(w, h)
    E = cand_end(name, d, w, h)
    bad = []
    for t, got in sorted(cells.items()):
        if t <= S[6] or t >= S.get(7, 1 << 30):
            continue
        want = 2 if t < E else 1
        if want != got:
            bad.append((hx(t), got, want))
    return not bad, E, bad


def main():
    diff = part_a()
    obs = observed()
    print("\n== (b) per target: A_6, after[b_6 + d], the read cells")
    res = {"artefact": [list(map(str, d)) for d in diff], "targets": {}, "candidates": {}}
    b6 = L.F5.bk(6)
    for wh in MAPPED + HELD:
        w, h = wh
        S, A, B, U = L.model(w, h)
        _, opens, after = L.F5.replay(w, h, L.ents(w, h), 3)
        cells = obs[wh]
        first1 = min((t for t, v in cells.items() if v == 1 and t > S[6]), default=None)
        res["targets"][f"{w}x{h}"] = {"A6": hx(A[6]), "after": [hx(after[b6 + d]) for d in range(5)],
                                      "opens": [opens[b6 + d] for d in range(5)], "first1": hx(first1),
                                      "cells": {hx(t): v for t, v in sorted(cells.items())}}
        print(f"{w}x{h}: S6 {S[6]:#x} A6 {A[6]:#x} after[b6+d] {[hx(after[b6 + d]) for d in range(5)]} "
              f"opens {[opens[b6 + d] for d in range(5)]} first 1-page cell {hx(first1)} "
              f"(+{first1 - A[6] if first1 else '-'}) cells {[(hx(t), v) for t, v in sorted(cells.items())]}")
    print("\n== (c) candidates: fit on the mapped targets, then the eight others")
    best = None
    for name in ("H-NEXT", "H-HALF"):
        for d in range(0, 5):
            fit = [holds(name, d, w, h, obs[(w, h)]) for w, h in MAPPED]
            held = [holds(name, d, w, h, obs[(w, h)]) for w, h in HELD]
            nf, nh = sum(x[0] for x in fit), sum(x[0] for x in held)
            res["candidates"][f"{name}{d}"] = {"fit": nf, "held": nh,
                                               "ends": [hx(x[1]) for x in fit + held]}
            print(f"{name}{d}: fit {nf} of 2, held out {nh} of 8; ends {[hx(x[1]) for x in fit + held]}; "
                  f"misses {[(f'{wh[0]}x{wh[1]}', x[2]) for wh, x in zip(MAPPED + HELD, fit + held) if not x[0]]}")
            if nf == 2 and (best is None or nh > best[2]):
                best = (name, d, nh)
    if best and best[2] >= 7:
        print(f"FROZEN for m6b: {best[0]}{best[1]} (fit 2 of 2, held out {best[2]} of 8)")
        res["frozen"] = f"{best[0]}{best[1]}"
    else:
        print("NO CANDIDATE frozen for m6b (none fits both mapped targets and holds 7 of 8):"
              f" best {best}; m6b runs replicates and readings with H-SPAN and E936's rivals only")
        res["frozen"] = None
    with open(os.path.join(HERE, "od2_band6.json"), "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    main()
