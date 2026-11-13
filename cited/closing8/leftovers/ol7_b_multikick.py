#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ol7_b_multikick.py (round 8, leftovers OL7 (b), Q211; offline, read-only, a FIT on kept cells,
no held-out row): E875's page replay extended to scenes of several kicks with G4's reading
(E899: a later kick walks its triangle's regions again, in H-WALK64's order, and its blocks fill
the pages its macrotiles have open), written before the comparison below:

  H-KICKS  the kicks are walked in turn, each kick's triangle's regions in H-WALK64's order; a
           region that already holds a stream block takes none (HU1: a region counted once);
           a new block goes into its macrotile's open page while it has room (32 blocks), else
           takes a page; a page request above the threshold is a partial render, which keeps 1
           page, frees the rest (every region's block included) and raises the threshold by
           0x20 (f7_replay.replay's rules, unchanged).
  rival    H-UNION: f7_replay.replay of the union walked once in H-WALK64's order.

Scored against every kept job of the multi-kick stages the plan names (closing-s1 g-e2a and g-e2b,
closing-r1-pixgeo g-u1; `tri -n K --geometry ...`, K >= 2): the partial-render count, every TA
run's peak (the high half of 0x0724 per run, f7_replay.kept's reading) and, for a job without a
partial render, the need (the peak). All of these had been seen (E899's G4 printed their dumps),
so this is a FIT: the session's stage `k` holds it out only if it reproduces every kept cell here
(the plan: else `k` runs as explore). Prints FIT VERDICT.

  python3 -I -B ol7_b_multikick.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ol7lib as L  # noqa: E402

STAGES = (("closing-s1", "g-e2a"), ("closing-s1", "g-e2b"), ("closing-r1-pixgeo", "g-u1"))


def replay_kicks(w, h, kicks, thr0, raise_=0x20, cap=32, keep=1):
    """H-KICKS: kicks is the list of each kick's triangles; (partial renders, run peaks) or None."""
    used, cur, seen, peaks, n, thr = 1, {}, set(), [], 0, thr0
    for tris in kicks:
        for c, r, m in L.walk(w, h, tris):
            if (c, r) in seen:
                continue
            seen.add((c, r))
            if cur.get(m, 0) == 0:
                if used + 1 > thr:
                    peaks.append(used)
                    n += 1
                    used, cur, seen, thr = keep, {}, {(c, r)}, thr0 + raise_
                    if used + 1 > thr:
                        return None
                used += 1
                cur[m] = cap
            cur[m] -= 1
    peaks.append(used)
    return n, peaks


def kicks_of(args):
    """(w, h, kicks) of a `tri` command: render i + 1 is a kick of its own (--geometry renders
    leave the scene open; the last render ends it), its triangle moved by --move i+1:DX,DY."""
    w = int(re.search(r"--width (\d+)", args).group(1))
    h = int(re.search(r"--height (\d+)", args).group(1))
    n = int(re.search(r"(?:^|\s)-n (\d+)", args).group(1))
    mv = {int(a): (int(b), int(c)) for a, b, c in re.findall(r"--move (\d+):(-?\d+),(-?\d+)", args)}
    return w, h, [[L.tri_moved(w, h, *mv.get(i + 1, (0, 0)))] for i in range(n)]


def kept_reading(path):
    cols, rows = L.R6.load(path)
    if not rows or 0x724 not in rows[0][1] or 0x658 not in rows[0][1]:
        return None
    st = L.R6.stretches(rows)
    bounds = [(1, st[0][0] if st else len(rows))] + [
        (st[k][1] + 1, st[k + 1][0] if k + 1 < len(st) else len(rows)) for k in range(len(st))]
    peaks = [max(L.R6.hi(rows[i][1], 0x724) for i in range(a, e)) for a, e in bounds if e > a]
    return len(st), peaks


def main():
    import csv
    tal = {"H-KICKS": [0, 0, 0], "H-UNION": [0, 0, 0]}
    off = []
    for ds, stg in STAGES:
        d = os.path.join(str(L.DATA), "render", ds, "out", stg)
        for r in csv.DictReader(open(os.path.join(d, "cases.tsv")), delimiter="\t"):
            args = r.get("args") or ""
            if "--geometry" not in args or not args.startswith("tri"):
                continue
            got = kept_reading(os.path.join(d, r["name"] + ".txt.gz"))
            if got is None:
                print(f"   {ds[8:]}/{stg}/{r['name']}: no 0x0724 or 0x0658: not scored")
                continue
            w, h, kicks = kicks_of(args)
            thr0 = int(r["P"], 16) - L.D_OFF
            union = [t for k in kicks for t in k]
            U = L.u_of(w, h, union)
            pk = replay_kicks(w, h, kicks, thr0)
            pu = L.replay_union(w, h, union, thr0)
            line = []
            for nm, p in (("H-KICKS", pk), ("H-UNION", pu)):
                t = tal[nm]
                c_ok = p is not None and p[0] == got[0]
                a_ok = c_ok and p[1] == got[1]
                t[0] += c_ok
                t[1] += a_ok
                t[2] += 1
                line.append(f"{nm} {p[0] if p else None} {[hex(x) for x in p[1]] if p else None}"
                            f" {'ok' if a_ok else 'OFF'}")
                if nm == "H-KICKS" and not a_ok:
                    off.append(f"{ds[8:]}/{stg}/{r['name']}")
            print(f"{ds[8:]:10s} {stg:6s} {r['name']:14s} {w}x{h} K {len(kicks)} thr0 {thr0:#x} U {U}"
                  f" | kept {got[0]} {[hex(x) for x in got[1]]} | " + " | ".join(line))
    for nm, (c, a, n) in tal.items():
        print(f"{nm}: count {c} of {n}, count and every run peak {a} of {n}")
    print("FIT VERDICT H-KICKS:", "REPRODUCES every kept cell (stage k held out)" if not off and
          tal["H-KICKS"][2] else f"does NOT reproduce {len(off)} kept cells (stage k explore): "
          + ", ".join(off))


if __name__ == "__main__":
    main()
