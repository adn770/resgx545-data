#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""od1_wide.py (round 9, S9-ldpm offline step OD-1, Q211: the page need U of wide scenes of many
vertices; offline, read-only, standard library only, no number fitted).

The 1500-vertex scene (`probe --tri pixel --vertices 1500`, E630's scene family) has a need above
one stream a region: its 100 objects of 67 dwords each take streams in every region they list
(f5lib, E874). OD-1 freezes, before any row of stage w runs, the needs the frozen rules give at
wide targets (one side at least twice the other) never run:

  H-REPLAY  E874's block-level replay of the TA (g3_span.model's U, lag 3, from the published frozen
            library through ol7lib, hash-checked): the need held at nine kept calibrations (E915,
            E935, E936) of square and 3:2 targets, never on a target wider than 2:1
  HU1       dpm.rs scene_page_need (E939): one 128-byte stream a region the 500 triangles list,
            32 a page per macrotile, plus the global page. The plan named it; it is printed on the
            nine kept calibrations first, where it is far below every need (so it is refuted
            offline for this scene and stays a tally, never a verdict)

Part 1 prints both rules against the nine kept calibration needs (r8-ldpm m6, sp; R7-dpm E915).
Part 2 prints U at the candidate wide targets with both rules, and S_k, A_k; a target is usable when
U < 0x3f0 (the clamp 0x400 less the plan's margin). Part 3 picks stage w's four targets (the
plan's examples where usable, then the next candidates in list order) and one cell each: the
lowest thr0 in [U / 4, U / 2] where F9's count with the raise R-5's guard gives equals F9's count
without a raise (so band 4's unraised cells, E938, cannot decide it) and parts from E854's
d = 7/4 and d = 1, the cell not a step. Writes od1_wide.json (sorted keys); its sha256 goes into
FREEZE-od1.sha256 after the run, the script's before it.

  python3 -I -B od1_wide.py > od1_wide.out
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ol7lib as L  # noqa: E402

U_MAX = 0x3F0
KEPT = {(2048, 2048): 0x213, (3072, 2048): 0x305, (2048, 3072): 0x30F, (1536, 1536): 0x13A,
        (1024, 1024): 0x99, (4096, 2048): 0x3F7, (2560, 2560): 0x328, (2560, 3072): 0x3C3,
        (3072, 2560): 0x3BE}
PLAN = [(4096, 1024), (4096, 1536), (3584, 1024), (2048, 512)]
MORE = [(4096, 768), (4096, 512), (3072, 1024), (1024, 2048), (1024, 4096), (2048, 1024),
        (3584, 1536), (1536, 3072)]


def hx(v):
    return f"0x{v:x}"


def tris(w, h):
    return [L.F5.tri(w, h, j) for j in range(L.F5.OBJS * L.F5.PER)]


def hu1(w, h):
    return L.u_of(w, h, tris(w, h))


def f9_both(w, h, t):
    S, A, B, U = L.model(w, h)
    a = L.F9.run(L.ents(w, h), t, L.guard_class(t, S, A) == "R", w, h)
    b = L.F9.run(L.ents(w, h), t, False, w, h)
    return a, b


def cell(w, h):
    S, A, B, U = L.model(w, h)
    for t in range(U // 4, U // 2 + 1):
        if t in S.values():
            continue
        a, b = f9_both(w, h, t)
        if a is None or b is None or a[0] != b[0]:
            continue
        d74, d1 = L.dcount(t, U, 1.75), L.dcount(t, U, 1.0)
        if a[0] != d74 and a[0] != d1:
            return t, a, d74, d1
    return None


def main():
    res = {"kept": {}, "targets": {}, "w": []}
    print("== part 1: the nine kept calibrations of the 1500-vertex scene (need read at P 0x422)")
    for (w, h), need in KEPT.items():
        S, A, B, U = L.model(w, h)
        u1 = hu1(w, h)
        res["kept"][f"{w}x{h}"] = {"read": hx(need), "H-REPLAY": hx(U), "HU1": hx(u1)}
        print(f"{w}x{h}: read {need:#x}  H-REPLAY {U:#x} {'ok' if U == need else 'OFF'}  "
              f"HU1 {u1:#x} {'ok' if u1 == need else 'OFF'}")
    print("== part 2: candidate wide targets")
    usable = []
    for w, h in PLAN + MORE:
        S, A, B, U = L.model(w, h)
        u1 = hu1(w, h)
        ok = U < U_MAX
        res["targets"][f"{w}x{h}"] = {"U": hx(U), "HU1": hx(u1), "S": {str(k): hx(v) for k, v in sorted(S.items())},
                                      "A": {str(k): hx(v) for k, v in sorted(A.items())}, "usable": ok}
        print(f"{w}x{h}: H-REPLAY U {U:#x} HU1 {u1:#x} {'usable' if ok else 'not usable (U >= 0x3f0)'} | S "
              + " ".join(f"{k}:{v:#x}" for k, v in sorted(S.items())))
        if ok:
            usable.append((w, h))
    pick = [t for t in PLAN if t in usable] + [t for t in MORE if t in usable]
    pick = pick[:4]
    print("== part 3: stage w's targets and cells")
    for w, h in pick:
        S, A, B, U = L.model(w, h)
        c = cell(w, h)
        if c is None:
            raise SystemExit(f"{w}x{h}: no cell parts F9 from d = 7/4 and d = 1")
        t, f9, d74, d1 = c
        res["w"].append({"w": w, "h": h, "U": hx(U), "HU1": hx(hu1(w, h)), "thr0": hx(t),
                         "F9": [f9[0], [hx(x) for x in f9[1]]], "d=7/4": d74, "d=1": d1,
                         "steps_below": {str(k): hx(v) for k, v in sorted(S.items()) if v < t},
                         "gps_abort": L.gps_abort(t, S)})
        print(f"w {w}x{h}: U {U:#x} (HU1 {hu1(w, h):#x}); cell thr0 {t:#x}: F9 {f9[0]} "
              f"{[hex(x) for x in f9[1]]} (raise or not), d=7/4 {d74}, d=1 {d1}, gps_abort {L.gps_abort(t, S)}")
    with open(os.path.join(HERE, "od1_wide.json"), "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    main()
