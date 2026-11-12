#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""r6plan.py: the frozen content of R6-dpm, generated from the approved plan closing6/dpm/exp-dpm-r6.md (decisions R6-2 (a) and the
plan's own decisions all (a): six stages, oomring2 checked and, refused by both verifiers, r5's oomring unchanged for r-k).  Writes
tables/STAGE.txt, predictions/STAGE.tsv, TABLES.md and stages.txt.  Pure python, no I/O but those files.

    .../pixel-faults/.venv/bin/python gen/r6plan.py

Every predicted number comes from a frozen offline rule (gen/r6model.py loads them from resgx545-data cited/closing6/dpm/offline
with their FREEZE hashes checked): H-STEPMODEL and H-PHASE (f5lib/f5_stepmodel, E874), the timeline burst-end rule (f4_phase, E874),
F9's replay (exploratory, E874), H-REPLAY's walk orders and E854's spacing rivals (f7_replay, E875), H-IV (E873), R-5's guard (3d.md
6.4).  The build-side choices (cells, scenes, the r-v model at a measured L) are made here by rules written next to them and listed
in PREFLIGHT.md section 7.
"""
from __future__ import annotations

import pathlib
import re
import sys
from fractions import Fraction as Fr

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KP / "gen"))
import r6model as M  # noqa: E402

# ------------------------------------------------------------------------------------------------ the measurement (r5's, unchanged)
RT = "0x012c,0x0624-0x0628,0x0658,0x0660,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,0x0a74"
PROG = "p1139-green.bin"
D_OFF = 0x22                                   # P = thr0 + 0x22 (the knob proof: the job's own 0x0624 = P - 0x22)
DUMP_MAX = 2048 * 2048                         # --dump-render only on targets up to 2048x2048 (plan section 4; r5 freeze 2)


def probe(w, h, coords=None):
    vc = f" --vtx-coords {coords}" if coords else ""
    dump = ' --dump-render "$W/dump"' if w * h <= DUMP_MAX else ""
    return f'probe --tri pixel --width {w} --height {h} --vertices 1500{vc}{dump} "$S/{PROG}"'


def qtri(move=None):
    """g-qf's command (E832); a moved scene as E773's s275 and R5-dpm's d-b (-n 1 --move 1:DX,DY --keep-going)."""
    mv = f" --move 1:{move[0]},{move[1]} --keep-going" if move else ""
    return f'tri --width 4096 --height 4096 -n 1{mv} --keep-overflow --wait-ms 20000 --words "$W/words" --regs 0x0700-0x074c'


def hx(v):
    return f"0x{v:x}"


# ------------------------------------------------------------------------------------------------ targets and the frozen model
TARGETS = {"c2048": (2048, 2048), "c2048f": (2048, 2048), "c2x1": (2048, 1024), "c1x2": (1024, 2048), "c15": (1536, 1536),
           "c2x4": (2048, 4096)}
SPARES = [(1536, 1024), (1024, 1024)]           # plan: a size the tool or fork refuses is replaced from this list (none was)
NEW = ["c2x1", "c1x2", "c15"]
# The frozen model's numbers, written out so that importing this file computes nothing (the runner mock, the world and the scorer
# import it per job); tests/test_gen.py recomputes every one from the frozen rules (recompute() below) and requires equality.
# (w, h) -> (S {k: S_k}, B {k: B_k}, U): f5lib.replay + f5_stepmodel.bands, lag 3 (gen/r6model.py model())
MODEL_FROZEN = {
    (1024, 2048): ({2: 47, 3: 86, 4: 126, 5: 167, 6: 208, 7: 248}, {2: 81, 3: 123, 4: 161, 5: 201, 6: 242, 7: 283}, 288),
    (1536, 1536): ({2: 50, 3: 93, 4: 138, 5: 183, 6: 225, 7: 270}, {2: 91, 3: 135, 4: 177, 5: 221, 6: 265, 7: 308}, 314),
    (2048, 1024): ({2: 46, 3: 82, 4: 123, 5: 163, 6: 202, 7: 241}, {2: 80, 3: 121, 4: 159, 5: 198, 6: 237, 7: 275}, 277),
    (2048, 2048): ({2: 81, 3: 157, 4: 232, 5: 306, 6: 385, 7: 458}, {2: 151, 3: 227, 4: 302, 5: 374, 6: 449, 7: 524}, 531),
    (2048, 4096): ({2: 154, 3: 297, 4: 446, 5: 597, 6: 744, 7: 891}, {2: 293, 3: 439, 4: 584, 5: 730, 6: 878, 7: 1026}, 1037),
}
MODEL = MODEL_FROZEN
# F4's timeline burst ends at 2048x2048 (f4_phase.out, reference r2-geo/g-c3/c3-2048-0x354): the frozen rival of the model's B_k
E_TL_2048 = {2: 0x97, 3: 0xe3, 4: 0x12e, 5: 0x178, 6: 0x1c1, 7: 0x1cc}

# r-v: the object block size L of `--vtx-coords N` (3d.md 10.1: each vertex stores its 1/w and its N outputs raw, 1 + N dwords, where
# the position-only object stores 1): L0 = 67 + 15 N [infer]; the scorer reads L from the calibration's dump and evaluates the
# frozen rule there.  Frozen here: both models at L0 (CAP = f5lib's rule, PAGE = H-BURST-PAGE).
VTX = {4: 67 + 15 * 4, 8: 67 + 15 * 8}
# (N, mode) -> (S, B, U, burst objects): gen/r6model.py model_L(2048, 2048, VTX[N], mode)
VMODEL_FROZEN = {
    (4, 'cap'): ({2: 79, 3: 82, 4: 155, 5: 159, 6: 231, 7: 302, 8: 307, 9: 379, 10: 384, 11: 455, 12: 461, 13: 532}, {2: 152, 3: 152, 4: 229, 5: 229, 6: 302, 7: 377, 8: 377, 9: 453, 10: 453, 11: 529, 12: 529, 13: None}, 538, [15, 29, 43, 57, 72, 86]),
    (4, 'page'): ({2: 79, 3: 151, 4: 225, 5: 299, 6: 372, 7: 444, 8: 519, 9: 592, 10: 668, 11: 740, 12: 815, 13: 884}, {2: 151, 3: 225, 4: 298, 5: 372, 6: 444, 7: 518, 8: 592, 9: 668, 10: 739, 11: 815, 12: 884, 13: 957}, 957, [8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96]),
    (8, 'cap'): ({2: 79, 3: 80, 4: 83, 5: 153, 6: 157, 7: 230, 8: 233, 9: 238, 10: 308, 11: 309, 12: 382, 13: 386, 14: 390, 15: 462, 16: 463, 17: 468, 18: 540, 19: 543}, {2: 153, 3: 153, 4: 153, 5: 230, 6: 230, 7: 306, 8: 306, 9: 306, 10: 382, 11: 382, 12: 459, 13: 459, 14: 459, 15: 534, 16: 534, 17: 534, 18: 611, 19: 611}, 611, [14, 28, 42, 56, 70, 84, 98]),
    (8, 'page'): ({2: 79, 3: 151, 4: 225, 5: 299, 6: 370, 7: 445, 8: 520, 9: 592, 10: 664, 11: 737, 12: 811, 13: 885, 14: 960, 15: 1031, 16: 1104, 17: 1178, 18: 1251, 19: 1326}, {2: 151, 3: 225, 4: 299, 5: 370, 6: 445, 7: 520, 8: 592, 9: 664, 10: 737, 11: 811, 12: 885, 13: 960, 14: 1031, 15: 1104, 16: 1178, 17: 1251, 18: 1326, 19: 1396}, 1396, [5, 10, 16, 21, 27, 32, 38, 43, 49, 54, 60, 65, 71, 76, 82, 87, 93, 98]),
}
B_SCENES_FROZEN = [(256, 1280, 262), (1536, 0, 243), (1792, 256, 220), (2048, 1024, 179)]
VMODEL = VMODEL_FROZEN

# r-k: the 2048x4096 band 4 creep cell (dword 36 = 2 above 1 page left): thr0 between B4 and S5; F9's replay gives 2 partial renders
# at 0x248 to 0x24c and 1 from 0x24e (a decision entry needs a second abort): 0x24a, two above B4 = 0x248 and two below 0x24c.
CREEP = 0x24A


# ------------------------------------------------------------------------------------------------ r-b: scenes and cells (F7)
KEPT_U = (287, 275, 198, 119)                   # g-qf, s275, s198, s119: the scenes E875 read


def b_scenes(n=4, step=256):
    """Plan: four new one-triangle scenes at 4096x4096 where W* (col), its runner-up (row) and d = 1 differ most.  Build rule: moves
    (dx, dy) on a grid of `step` pixels, U >= 40; score = (cells where row and col counts differ, cells where any of row, col, d = 1,
    d = 7/4 differ); best first, ties to the smaller (dx, dy); a scene is taken only if its U is at least 10 from every kept scene's
    and every scene taken before."""
    cand = []
    for dx in range(0, 4096, step):
        for dy in range(0, 4096, step):
            _, U = M.scene(dx, dy)
            if U < 40:
                continue
            dis = rc = 0
            for t in range(2, U):
                a, b = M.h_replay(dx, dy, t, "row"), M.h_replay(dx, dy, t, "col")
                if a is None or b is None:
                    continue
                key = (a[0], b[0], M.dcount(t, U, 1.0), M.dcount(t, U, 1.75))
                dis += len(set(key)) > 1
                rc += a[0] != b[0]
            cand.append((-rc, -dis, dx, dy, U))
    out, us = [], list(KEPT_U)
    for _, _, dx, dy, U in sorted(cand):
        if all(abs(U - u) >= 10 for u in us):
            out.append((dx, dy, U))
            us.append(U)
        if len(out) == n:
            break
    return out


def b_cells(dx, dy, U, want=8):
    """Eight cells: every thr0 where row, col, d = 1 and d = 7/4 do not all agree (row != col first, then ascending); filled with the
    neighbours t + 1, t - 1 of those cells in the same order.  thr0 >= 2 and every model defined there."""
    def preds(t):
        a, b = M.h_replay(dx, dy, t, "row"), M.h_replay(dx, dy, t, "col")
        if a is None or b is None or t < 2 or t >= U:
            return None
        return (a[0], b[0], M.dcount(t, U, 1.0), M.dcount(t, U, 1.75))
    dis = [t for t in range(2, U) if (p := preds(t)) and len(set(p)) > 1]
    dis.sort(key=lambda t: (preds(t)[0] == preds(t)[1], t))
    cells = dis[:want]
    for t in dis:
        for u in (t + 1, t - 1):
            if len(cells) < want and u not in cells and preds(u):
                cells.append(u)
    return sorted(cells)


# b_scenes() and b_cells() written out (recomputed and compared by tests/test_gen.py: about a minute)
B_SCENES_FROZEN = [(256, 1280, 262), (1536, 0, 243), (1792, 256, 220), (2048, 1024, 179)]
B_CELLS_FROZEN = {'s262': [2, 6, 11, 18, 28, 43, 67, 116], 's243': [14, 15, 16, 24, 25, 38, 61, 106], 's220': [4, 5, 6, 11, 32, 33, 53, 95], 's179': [4, 11, 21, 22, 23, 39, 40, 74]}
B_SCENES = B_SCENES_FROZEN
B_NAME = {f"s{U}": (dx, dy) for dx, dy, U in B_SCENES}
B_U = {f"s{U}": U for dx, dy, U in B_SCENES}
B_CELLS = B_CELLS_FROZEN


def recompute():
    """Every frozen constant above, recomputed from the frozen rules (tests/test_gen.py)."""
    model = {wh: M.model(*wh)[:3] for wh in MODEL_FROZEN}
    vmodel = {(n, mode): M.model_L(2048, 2048, VTX[n], mode) for n in VTX for mode in ("cap", "page")}
    scenes = b_scenes()
    cells = {f"s{U}": b_cells(dx, dy, U) for dx, dy, U in scenes}
    return dict(model=model, vmodel=vmodel, scenes=scenes, cells=cells)
QF = {0x53: 4, 0x54: 3, 0xA2: 2, 0xA3: 1}       # E832's kept counts at U 287 (the controls)

# ------------------------------------------------------------------------------------------------ the stages
STAGES = ["r-a0", "r-m", "r-n", "r-v", "r-b", "r-k"]
HDR = {
    "r-a0": "r-a0 premise (7): the 2048x2048 calibrations at P 0x162 and 0x422 (complete: S2 to S7 in their brackets), c4-b5 R, "
            "c4-b6 N, t-s3m7 (thr0 0x96) 2 global pages left, t-s3m6 (0x97) 1, g-qf at P 0xa2 2 partial renders.  Every row is a "
            "premise: a control off, a calibration whose steps are not monotone or a job whose own 0x0624 is not P - 0x22 STOPS the "
            "session before r-m (rc 10, state/CTLFAIL).",
    "r-m": "r-m new bands (15, held out): 2048x2048, five consecutive thr0 around the model's burst end B5 0x176, B6 0x1c1, B7 0x20c "
           "(B - 2 .. B + 2): 2 global pages left below B, 1 from B (H-PHASE); the timeline rule's E5 0x178, E7 0x1cc the rival; "
           "all silent (R-5's guard).",
    "r-n": "r-n new targets (21, held out): 2048x1024, 1024x2048, 1536x1536: a calibration (P 0x422, complete: the model's steps and "
           "U) and in bands 3 and 4 the cells B - 1, B (the model's flip) and S - 1 (from the calibration's own step): left 2, 1, 1; "
           "band 3 raises at B3 - 1 only.  A calibration off the model's brackets re-picks its B cells by the timeline rule (then "
           "H-PHASE only).",
    "r-v": "r-v object size (6, discriminating): 2048x2048 with --vtx-coords 4 and 8: a calibration with its dump (L read from it, "
           "the steps against H-BURST-CAP and H-BURST-PAGE at that L), then the cells E - 1 and E of the first band from 3 on "
           "whose burst end the frozen timeline rule finds in the calibration (none found: the cells are skipped; the steps decide).  The first job is the premise: if it is not a 1500-vertex scene the stage's "
           "rest is skipped.",
    "r-b": "r-b count (40): four g-qf controls (P 0x53, 0x54, 0xa2, 0xa3: 4, 3, 2, 1 partial renders); four new one-triangle "
           "scenes at 4096x4096 (a calibration each: the page need must be HU1's, else the scene is void) and eight cells each, "
           "count and every run's peak by H-REPLAY in row order (E875, post hoc there) against column order (W*), d = 7/4 and d = 1.",
    "r-k": "r-k passes (8, LAST): the own task armed before each job (r5's oomring: oomring2's two ldr are refused by both verifiers, "
           "so the counts at the passes cannot be read and the sa8 bits are): c4-b5, c4-b6, c4-b3 (S4), the S3 cell, S4 + 1, "
           "t-s3m6, the 2048x4096 band 4 creep cell thr0 0x24a twice (dword 36 = 2 above 1 page left: sa8 & 0x380 = 0 pins the "
           "isub16 operand order).  An EDM stall is reset once; a second one ends r-k.",
}


def row(name, sset, P, knobs, cmd, rt=RT, risk="safe"):
    return dict(name=name, set=sset, risk=risk, P=P, knobs=knobs, rt=rt, cmd=cmd)


def s_ref(g, k, off):
    return f"S:{g}:{k}:{off:+d}" if off else f"S:{g}:{k}:0"


def model_knob(g):
    S, B, U = MODEL[TARGETS[g]]
    return "model:" + ",".join(hx(S[k]) for k in sorted(S))


def tables():
    p42 = probe(2048, 2048)
    T = {}
    T["r-a0"] = [
        row("a0-cal-2048", "control", "0x162", "stophang prem cal:c2048", p42),
        row("a0-cal-2048f", "control", "0x422", "stophang prem cal:c2048f", p42),
        row("a0-c4-b5", "control", "0x104", "stophang prem ctl:R", p42),
        row("a0-c4-b6", "control", "0x105", "stophang prem ctl:N", p42),
        row("a0-t-s3m7", "control", "0xb8", "stophang prem ctlleft:2", p42),
        row("a0-t-s3m6", "control", "0xb9", "stophang prem ctlleft:1", p42),
        row("a0-qf-0xa2", "control", "0xa2", "stophang expectdiff prem ctlcnt:2", qtri()),
    ]
    S, B, U = MODEL[(2048, 2048)]
    T["r-m"] = [row(f"m-b{k}-{hx(B[k] + o)}", "heldout", hx(B[k] + o + D_OFF), "stophang", p42)
                for k in (5, 6, 7) for o in (-2, -1, 0, 1, 2)]
    n = []
    for g in NEW:
        w, h = TARGETS[g]
        S, B, U = MODEL[(w, h)]
        pr = probe(w, h)
        n.append(row(f"n-cal-{g}", "control", "0x422", f"stophang cal:{g} {model_knob(g)}", pr))
        for k in (3, 4):
            n.append(row(f"n-{g}-b{k}m1", "heldout", f"M:{g}:{k}:-1:{hx(B[k] - 1 + D_OFF)}", "stophang", pr))
            n.append(row(f"n-{g}-b{k}", "heldout", f"M:{g}:{k}:0:{hx(B[k] + D_OFF)}", "stophang", pr))
            n.append(row(f"n-{g}-s{k + 1}m1", "heldout", s_ref(g, k + 1, -1), "stophang", pr))
    T["r-n"] = n
    v = []
    for N in (4, 8):
        pv = probe(2048, 2048, N)
        v.append(row(f"v-cal-c{N}", "heldout", "0x422", f"stophang cal:v{N} vprem", pv))
        v.append(row(f"v-c{N}-e3m1", "heldout", f"E:v{N}:3+:-1", "stophang", pv))
        v.append(row(f"v-c{N}-e3", "heldout", f"E:v{N}:3+:0", "stophang", pv))
    T["r-v"] = v
    b = [row(f"b-qf-{hx(P)}", "control", hx(P), "stophang expectdiff", qtri()) for P in QF]
    for sc, mv in B_NAME.items():
        U = B_U[sc]
        b.append(row(f"b-cal-{sc}", "control", "0x422", f"stophang expectdiff ucal:{sc}:{U}", qtri(mv)))
        for t in B_CELLS[sc]:
            b.append(row(f"b-{sc}-{hx(t)}", "heldout", hx(t + D_OFF), f"stophang expectdiff uneed:{sc}", qtri(mv)))
    T["r-b"] = b
    p24 = probe(2048, 4096)
    T["r-k"] = [row("k-b5", "control", "0x104", "stophang fw", p42), row("k-b6", "control", "0x105", "stophang fw", p42),
                row("k-b3", "repeat", "0x10a", "stophang fw", p42), row("k-s3", "heldout", s_ref("c2048", 3, 0), "stophang fw", p42),
                row("k-s4p1", "heldout", s_ref("c2048", 4, 1), "stophang fw", p42),
                row("k-s3m6", "heldout", "0xb9", "stophang fw", p42),
                row("k-creep", "heldout", hx(CREEP + D_OFF), "stophang fw", p24),
                row("k-creep2", "repeat", hx(CREEP + D_OFF), "stophang fw", p24)]
    return T


def target_of(cmd):
    m = re.search(r"--width (\d+) --height (\d+)", cmd)
    return (int(m.group(1)), int(m.group(2))) if m else None


def coords_of(cmd):
    m = re.search(r"--vtx-coords (\d+)", cmd)
    return int(m.group(1)) if m else None


def thr0_of(r):
    """The thr0 a row runs at by the frozen model (the runner reads S and E from the calibration; an M cell is the model's value).
    None for an E cell (placed on the laptop only)."""
    P = r["P"]
    if P.startswith("S:"):
        _, g, k, off = P.split(":")
        return MODEL[TARGETS[g]][0][int(k)] + int(off)
    if P.startswith("M:"):
        return int(P.split(":")[4], 16) - D_OFF
    if P.startswith("E:"):
        return None
    return int(P, 16) - D_OFF


def predictions():
    """{stage: [(case, quantity, value, model, set)]}: the frozen predictions."""
    T = tables()
    out = {}
    for st, rows in T.items():
        P = []
        for r in rows:
            n, s, wh, kn = r["name"], r["set"], target_of(r["cmd"]), r["knobs"].split()
            t = thr0_of(r)
            if r["cmd"].startswith("tri"):
                if n.startswith(("b-qf-", "a0-qf-")):
                    t = int(r["P"], 16) - D_OFF
                    sset = "control"
                    P.append((n, "nparts", str(QF[int(r["P"], 16)]), "CTL", sset))
                    P.append((n, "knob", hx(t), "CTL", sset))
                    for o in M.ORDERS:
                        rp = M.h_replay(0, 0, t, o)
                        P.append((n, "peaks", " ".join(hx(x) for x in rp[1]), f"H-REPLAY-{o.upper()}", "explore"))
                    P.append((n, "gmax", "1", "SCENE", sset))
                elif n.startswith("b-cal-"):
                    sc = n[len("b-cal-"):]
                    P += [(n, "need", str(B_U[sc]), "HU1", "control"), (n, "nparts", "0", "HU1", "control"),
                          (n, "gmax", "1", "SCENE", "control")]
                else:
                    sc = n.split("-")[1]
                    dx, dy = B_NAME[sc]
                    U = B_U[sc]
                    P.append((n, "knob", hx(t), "CTL", s))
                    for o in M.ORDERS:
                        rp = M.h_replay(dx, dy, t, o)
                        P.append((n, "nparts", str(rp[0]), f"H-REPLAY-{o.upper()}", s))
                        P.append((n, "peaks", " ".join(hx(x) for x in rp[1]), f"H-REPLAY-{o.upper()}", s))
                    P.append((n, "nparts", str(M.dcount(t, U, 1.75)), "d=7/4", s))
                    P.append((n, "nparts", str(M.dcount(t, U, 1.0)), "d=1", s))
                    P.append((n, "gmax", "1", "SCENE", s))
                continue
            N = coords_of(r["cmd"])
            if N:                                  # r-v
                if n.startswith("v-cal-"):
                    for mode in ("cap", "page"):
                        S, B, U, _ = VMODEL[(N, mode)]
                        for k in sorted(S):
                            if S[k] < 0x400:
                                P.append((n, f"S{k}", hx(S[k]), f"BURST-{mode.upper()}@L{VTX[N]}", s))
                        P.append((n, "need", hx(U) if U < 0x400 else ">0x400", f"BURST-{mode.upper()}@L{VTX[N]}", s))
                    P.append((n, "L", str(VTX[N]), "L0=67+15N", "explore"))
                    P.append((n, "gmax", ">=2", "SCENE", "control"))
                else:
                    want = "2" if n.endswith("m1") else "1"
                    P.append((n, "gps_left", want, "E-TL", s))
                    for mode in ("cap", "page"):
                        P.append((n, "gps_left", "rule", f"H-PHASE|BURST-{mode.upper()}", s))
                continue
            S, B, U = MODEL[wh]
            cal = next((k[4:] for k in kn if k.startswith("cal:")), None)
            if cal:
                if t >= U:                         # a complete run: every step and the need
                    for k in sorted(S):
                        P.append((n, f"S{k}", hx(S[k]), "H-STEPMODEL" if st == "r-n" else "H-IV", s))
                    P.append((n, "need", hx(U), "H-STEPMODEL" if st == "r-n" else "E785", s))
                    P.append((n, "nparts", "0", "H-STEPMODEL" if st == "r-n" else "E785", s))
                else:
                    for k in sorted(S):
                        if S[k] < t:
                            P.append((n, f"S{k}", hx(S[k]), "H-IV", s))
                P.append((n, "grow", "0", "H-GREQ", s))
                P.append((n, "knob", hx(t), "CTL", s))
                continue
            P.append((n, "knob", hx(t), "CTL", "control" if s == "control" else s))
            on = t in S.values()
            P.append((n, "grow", "1" if on else "0", "H-GREQ", s))
            left = M.phase_left(t, S, B)
            ctl_l = next((k[8:] for k in kn if k.startswith("ctlleft:")), None)
            if ctl_l:
                P.append((n, "gps_left", ctl_l, "CTL", "control"))
            elif left is not None:
                P.append((n, "gps_left", str(left), "H-PHASE", s))
                if st == "r-m":
                    P.append((n, "gps_left", str(M.F4.predict(t, S, E_TL_2048)), "E-TL", s))
            cls = M.guard_class(t, S, B)
            ctl_c = next((k[4:] for k in kn if k.startswith("ctl:")), None)
            f9 = M.f9_count(*wh, t, cls == "R") if st in ("r-m", "r-n") else None
            if ctl_c:
                P.append((n, "cls", ctl_c, "CTL", "control"))
            elif st in ("r-m", "r-n"):
                # the raise is decided at a second abort: predicted only where F9's replay gives 2 or more partial renders
                if f9 and f9[0] >= 2:
                    P.append((n, "cls", cls, "R-5", s))
                P.append((n, "nparts", str(f9[0]) if f9 else "None", "F9", "explore"))
            elif st != "r-k":
                P.append((n, "cls", cls, "R-5", s))
            if st == "r-k":
                if n.startswith("k-b5"):
                    P += [(n, "dec_sa8_380", "0x180", "H-BITS", "control"), (n, "cls", "R", "CTL-A3", "control")]
                elif n.startswith("k-b6"):
                    P += [(n, "dec_sa8_380", "0x0", "H-BITS", "control"), (n, "cls", "N", "CTL-A3", "control")]
                else:
                    P.append((n, "dec_sa8_380", "0x180" if cls == "R" else "0x0", "R-5", s))
                    P.append((n, "cls", cls, "R-5", s))
                    if n.startswith("k-creep"):
                        P.append((n, "dec_sa8_380", "0x180", "ISUB-REV", s))
                        f9 = M.f9_count(*wh, t, False)
                        P.append((n, "nparts", str(f9[0]), "F9", "explore"))
        out[st] = P
    return out


def table_text(st, rows):
    lines = [f"#stage {st}", f"#need $S/{PROG}"]
    for chunk in [HDR[st][i:i + 128] for i in range(0, len(HDR[st]), 128)]:
        lines.append("# " + chunk)
    for r in rows:
        lines.append("|".join((r["name"], r["set"], r["risk"], r["P"], r["knobs"], r["rt"], r["cmd"])))
    return "\n".join(lines) + "\n"


def tables_md(T, Pr):
    out = ["# R6-dpm: the frozen tables and predictions (generated by gen/r6plan.py; do not edit)", "",
           f"Register list (all rows, r5's): `{RT}`.", "",
           "P forms: `0xN` fixed; `S:G:k:off` thr0 = S_k read from calibration G's own timeline + off (r5's rule); `M:G:k:off:0xP` the "
           "frozen model's cell 0xP, re-picked as E_k + off (the timeline rule on calibration G) when G's steps are off the model's "
           "brackets; `E:G:k:off` thr0 = E_k of calibration G by the frozen timeline rule + off.  P = thr0 + 0x22.  The thr0 column is "
           "the frozen model's value.", "",
           f"r-b scenes (build rule in gen/r6plan.py b_scenes): " + ", ".join(f"{sc} = --move 1:{mv[0]},{mv[1]} (HU1 U {B_U[sc]})"
                                                                         for sc, mv in B_NAME.items()) + ".", ""]
    tot = 0
    for st in STAGES:
        out += [f"## {st} ({len(T[st])} jobs)", "", HDR[st], "", "| job | set | P | thr0 (model) | knobs | target / scene | predictions |",
                "|---|---|---|---|---|---|---|"]
        tot += len(T[st])
        for r in T[st]:
            pr = "; ".join(f"{q} = {v} [{m}]" for c, q, v, m, s in Pr[st] if c == r["name"])
            if r["cmd"].startswith("probe"):
                sc = "tri 1500" + (f" vtx-coords {coords_of(r['cmd'])}" if coords_of(r["cmd"]) else "")
            else:
                sc = "tri -n 1 " + (r["cmd"].split("--move ")[1].split()[0] if "--move" in r["cmd"] else "default")
            wh = target_of(r["cmd"])
            t = thr0_of(r)
            kn = r["knobs"].replace("|", "/")
            if len(kn) > 60:
                kn = kn[:57] + "..."
            out.append(f"| {r['name']} | {r['set']} | {r['P']} | {hx(t) if t is not None else 'E'} | {kn} | {wh[0]}x{wh[1]} {sc} | {pr} |")
        out.append("")
    out.insert(4, f"**{tot} jobs** in {len(STAGES)} stages: " + ", ".join(f"{st} {len(T[st])}" for st in STAGES) + ".")
    out.insert(5, "")
    return "\n".join(out) + "\n"


def main():
    T, Pr = tables(), predictions()
    (KP / "tables").mkdir(exist_ok=True)
    (KP / "predictions").mkdir(exist_ok=True)
    for st in STAGES:
        (KP / "tables" / f"{st}.txt").write_text(table_text(st, T[st]))
        (KP / "predictions" / f"{st}.tsv").write_text("case\tquantity\tvalue\tmodel\tset\n" +
                                                      "".join("\t".join(p) + "\n" for p in Pr[st]))
    (KP / "stages.txt").write_text("\n".join(STAGES) + "\n")
    (KP / "TABLES.md").write_text(tables_md(T, Pr))
    print(sum(len(v) for v in T.values()), "jobs;", {st: len(T[st]) for st in STAGES}, "B scenes:", B_SCENES)


if __name__ == "__main__":
    main()
