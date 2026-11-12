#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""r7plan.py: the frozen content of R7-dpm, generated from the approved plan closing7/b/exp-dpm-r7.md (DECISIONS-R7.md R7-2 (a),
R7-4 (a), R7-6 (a); the plan's own decisions all (a)).  Writes tables/STAGE.txt, predictions/STAGE.tsv, TABLES.md and stages.txt.

    .../pixel-faults/.venv/bin/python gen/r7plan.py

Two sets, two freezes (README.md):
  set A  s-a0 (6), s-m (50), s-b (29), s-v (2, exploration)  on the test module 41E2F5C7 (fork 3f0b3e74), as loaded now
  set B  s-k (10)                                              on the module 37EC97AB (fork 664fd0d0) after the lead's one-shot
                                                               boot: the own task oomring2 (oomring + ldr of 0x0724 and 0x072c)
Every predicted number comes from a frozen offline rule (gen/r7model.py loads them with their FREEZE hashes checked): H-STEPMODEL
(E874's step replay, S_k and U), H-SPAN (E900's A_k: left 2 iff S_k < thr0 < A_k) with E874's B_k as the rival, H-REPLAY64 (E899:
E875's replay in the walk order read from the dumps) with row order as the rival, H-WALK64 (E899) on the dump of a new scene, R-5's
guard (3d.md 6.4, with A_3 = B_3), F9's replay (exploratory).  s-v: E900 froze no step rule for larger objects (G5: H-CUM 9 of 12
at N 4, not frozen), so by the plan's decision 5 (a) s-v is two calibrations as exploration (their predictions are R6-dpm's kept
readings of the same jobs, a repeat).  The build-side choices (scenes, cells, spares) are made here by rules written next to them.

Every CONTROL declares the readings it needs (`reads:` in its knobs) and the generator refuses one its row's job cannot produce
(scorekit.refuse_unreadable with producible() below, the frozen prediction of the job: r6-dpm's a0-cal-2048f "grow" on a job that
never takes a partial render cannot be frozen again).
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "gen"), str(KP / "score")]
import scorekit as SK  # noqa: E402

# r7model is imported lazily (it loads the frozen rules from resgx545-data): the runner mock, the world and the scorer import this file
# per job and need only the constants below.
_M = None


def M():
    global _M
    if _M is None:
        import r7model
        _M = r7model
    return _M


# ------------------------------------------------------------------------------------------------ the measurement (r5's, unchanged)
RT = "0x012c,0x0624-0x0628,0x0658,0x0660,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,0x0a74"
PROG = "p1139-green.bin"
D_OFF = 0x22                                   # P = thr0 + 0x22 (the knob proof: the job's own 0x0624 = P - 0x22)
CLAMP = 0x400                                  # thr0 at P 0x422 (E753): a calibration completes only below it
DUMP_MAX = 2048 * 2048                         # --dump-render only on targets up to 2048x2048 (plan section 4)
SRCV = {"A": "41E2F5C756F96D20F7109A4", "B": "37EC97AB0CB37213C42FCCC"}
SET_OF = {"s-a0": "A", "s-m": "A", "s-b": "A", "s-v": "A", "s-k": "B"}


def probe(w, h, coords=None):
    vc = f" --vtx-coords {coords}" if coords else ""
    dump = ' --dump-render "$W/dump"' if w * h <= DUMP_MAX else ""
    return f'probe --tri pixel --width {w} --height {h} --vertices 1500{vc}{dump} "$S/{PROG}"'


def qtri(w=4096, h=4096, move=None, dump=False):
    """g-qf's command (E832); a moved scene as E773's s275 and R6-dpm's r-b (-n 1 --move 1:DX,DY --keep-going); a dump as G1's u-2048
    (closing-r1-pixgeo: --dump-render, kept as NAME.tri.param.bin / NAME.tri.tadata.bin)."""
    mv = f" --move 1:{move[0]},{move[1]} --keep-going" if move else ""
    dp = ' --dump-render "$W/dump"' if dump else ""
    return f'tri --width {w} --height {h} -n 1{mv} --keep-overflow --wait-ms 20000{dp} --words "$W/words" --regs 0x0700-0x074c'


def hx(v):
    return f"0x{v:x}"


# ------------------------------------------------------------------------------------------------ targets and the frozen model
TARGETS = {"c2048": (2048, 2048), "c2048f": (2048, 2048), "c33": (3072, 3072), "c32": (3072, 2048), "c23": (2048, 3072),
           "c25": (2560, 2560), "c11": (1024, 1024), "c2x4": (2048, 4096)}
SPARES = [(2560, 1536), (1024, 1536)]          # plan: a size the tool refuses is replaced from this list (tests/mock_all.py: none was)
NEW = ["c33", "c32", "c23", "c25", "c11"]
# (w, h) -> (S {k: S_k}, A {k: A_k}, B {k: B_k}, U): g3_span.model (gen/r7model.py model()), written out so that importing this file
# computes nothing; tests/test_gen.py recomputes every one from the frozen rules (recompute() below) and requires equality.
MODEL_FROZEN = {
    (2048, 2048): ({2: 0x51, 3: 0x9d, 4: 0xe8, 5: 0x132, 6: 0x181, 7: 0x1ca}, {2: 0x97, 3: 0xe3, 4: 0x12e, 5: 0x178, 6: 0x1c3, 7: 0x20d},
                   {2: 0x97, 3: 0xe3, 4: 0x12e, 5: 0x176, 6: 0x1c1, 7: 0x20c}, 0x213),
    (3072, 3072): ({2: 0xa9, 3: 0x14d, 4: 0x1ef, 5: 0x293, 6: 0x335, 7: 0x3d9}, {2: 0x145, 3: 0x1e9, 4: 0x28a, 5: 0x32f, 6: 0x3cf, 7: 0x472},
                   {2: 0x145, 3: 0x1e9, 4: 0x28a, 5: 0x32a, 6: 0x3cd, 7: 0x470}, 0x479),
    (3072, 2048): ({2: 0x77, 3: 0xe2, 4: 0x150, 5: 0x1bf, 6: 0x22c, 7: 0x299}, {2: 0xdf, 3: 0x14d, 4: 0x1b8, 5: 0x229, 6: 0x293, 7: 0x300},
                   {2: 0xdf, 3: 0x14d, 4: 0x1b8, 5: 0x225, 6: 0x292, 7: 0x300}, 0x305),
    (2048, 3072): ({2: 0x77, 3: 0xe6, 4: 0x156, 5: 0x1c3, 6: 0x233, 7: 0x2a3}, {2: 0xde, 3: 0x14f, 4: 0x1bd, 5: 0x22d, 6: 0x29a, 7: 0x30a},
                   {2: 0xde, 3: 0x14f, 4: 0x1bd, 5: 0x22a, 6: 0x299, 7: 0x309}, 0x30f),
    (2560, 2560): ({2: 0x7a, 3: 0xeb, 4: 0x15c, 5: 0x1d4, 6: 0x244, 7: 0x2b6}, {2: 0xe6, 3: 0x158, 4: 0x1c9, 5: 0x23d, 6: 0x2b1, 7: 0x322},
                   {2: 0xe6, 3: 0x158, 4: 0x1c9, 5: 0x23c, 6: 0x2ae, 7: 0x321}, 0x328),
    (1024, 1024): ({2: 0x1c, 3: 0x30, 4: 0x45, 5: 0x5a, 6: 0x6f, 7: 0x86}, {2: 0x2e, 3: 0x41, 4: 0x57, 5: 0x6d, 6: 0x83, 7: 0x98},
                   {2: 0x2e, 3: 0x41, 4: 0x57, 5: 0x6b, 6: 0x82, 7: 0x97}, 0x99),
    (2048, 4096): ({2: 0x9a, 3: 0x129, 4: 0x1be, 5: 0x255, 6: 0x2e8, 7: 0x37b}, {2: 0x125, 3: 0x1b7, 4: 0x248, 5: 0x2db, 6: 0x370, 7: 0x404},
                   {2: 0x125, 3: 0x1b7, 4: 0x248, 5: 0x2da, 6: 0x36e, 7: 0x402}, 0x40d),
}
MODEL = MODEL_FROZEN
# the 2048x4096 steps of the KEPT calibrations (R3-geo c5b-cal, R5-dpm a2b-cal-2x4: tests/test_read.py reads them): the creep cell's
# scene check compares with these, not with the model, which misses S3 there (0x129 against 0x12c: R6's void, plan section 4)
KEPT_2X4 = {2: 0x9a, 3: 0x12c, 4: 0x1be}

# s-m: per new target, the parting band (the first band from 5 where A_k > B_k: E874's B_k says 1 where H-SPAN says 2) and its cells
# B_k - 1 .. A_k; plus B3 - 1 and B3 (R-5's raise flips at B3 = A3) except at 3072x3072, which runs bands 5 and 6 (plan section 4)
PART = {"c33": (5, 6), "c32": (5,), "c23": (5,), "c25": (6,), "c11": (5,)}
B3_CELLS = {"c32", "c23", "c25", "c11"}
# s-a0's six controls (R6-dpm's kept rows of the same jobs read held: tests/test_controls.py)
QF = {0xA2: 2}                                  # E832: g-qf at P 0xa2, two partial renders
# s-v: R6-dpm's kept calibrations at 2048x2048 --vtx-coords 4 and 8 (out/a2/r-v, read by run/r7read.py: tests/test_gen.py), repeated
VCAL = {4: ({2: 0x4f, 3: 0x52, 4: 0x98, 5: 0x9f, 6: 0xe7, 7: 0x12e, 8: 0x133, 9: 0x17d, 10: 0x182, 11: 0x1c7, 12: 0x1cd, 13: 0x214}, 538),
        8: ({2: 0x4f, 3: 0x98, 4: 0x9e, 5: 0xe5, 6: 0xe7, 7: 0x12d, 8: 0x133, 9: 0x17a, 10: 0x17e, 11: 0x1c4, 12: 0x1c9, 13: 0x1cb,
             14: 0x210, 15: 0x215, 16: 0x25d, 17: 0x260, 18: 0x2b0}, 691)}
# s-k: the 2048x4096 band 4 creep cell (dword 36 = 2 above 1 page left; R6's k-creep, thr0 0x24a); band 5's A - 1 and A at 2048x2048
CREEP = 0x24A
K_B5 = (0x177, 0x178)


# ------------------------------------------------------------------------------------------------ s-b: scenes and cells (H-REPLAY64)
# the U of every one-triangle scene already run at 4096x4096 (E773, E832, R5-dpm d-b, R6-dpm r-b): a new scene there keeps 10 pages
# from each; at the other targets only the default triangle ran (move (0, 0), excluded below), so no U is excluded
KEPT_U = {(4096, 4096): (287, 275, 262, 243, 220, 198, 179, 119), (1024, 768): (), (4096, 2048): (), (2048, 2048): ()}
B_PLAN = [("s44a", 4096, 4096, 6), ("s44b", 4096, 4096, 6), ("s42", 4096, 2048, 4), ("s22", 2048, 2048, 4), ("s17", 1024, 768, 4)]
B_STEP = {(4096, 4096): 256, (4096, 2048): 256, (2048, 2048): 128, (1024, 768): 64}
B_UMIN = {(4096, 4096): 40, (4096, 2048): 30, (2048, 2048): 20, (1024, 768): 12}


def b_candidates(w, h):
    """Build rule (plan section 4: moves where H-REPLAY64 and row order differ most): moves (dx, dy), both >= 0 (every kept move is),
    on a grid of B_STEP pixels with dx < w, dy < h and (dx, dy) != (0, 0), U >= B_UMIN; ranked by (cells where the counts of walk64 and
    row order differ, cells where their run peaks differ), most first, ties to the smaller (dx, dy)."""
    out = []
    for dx in range(0, w, B_STEP[(w, h)]):
        for dy in range(0, h, B_STEP[(w, h)]):
            if (dx, dy) == (0, 0):
                continue
            U = M().scene_u(w, h, dx, dy)
            if U < B_UMIN[(w, h)]:
                continue
            rc = pk = 0
            for t in range(2, U):
                a, b = M().replay(w, h, dx, dy, t), M().replay(w, h, dx, dy, t, "row")
                if a is None or b is None:
                    continue
                rc += a[0] != b[0]
                pk += a[1] != b[1]
            out.append((-rc, -pk, dx, dy, U))
    return sorted(out)


def b_scenes():
    """B_PLAN's scenes: the best candidate of each target whose U is at least 10 from every kept scene's U at that target and from
    every scene taken before at it."""
    taken, cache = [], {}
    for name, w, h, _ in B_PLAN:
        if (w, h) not in cache:
            cache[(w, h)] = b_candidates(w, h)
        us = list(KEPT_U[(w, h)]) + [u for n_, w_, h_, dx_, dy_, u in taken if (w_, h_) == (w, h)]
        pick = next(c for c in cache[(w, h)] if all(abs(c[4] - u) >= 10 for u in us))
        taken.append((name, w, h, pick[2], pick[3], pick[4]))
    return taken


def b_cells(w, h, dx, dy, U, want):
    """`want` cells: every thr0 (2 <= thr0 < U, both replays defined) where the counts of walk64 and row order differ, ascending; then
    from the cells where only their run peaks differ, spread evenly (indices round(i (n - 1) / (m - 1)) of the ascending list)."""
    cnt, pk = [], []
    for t in range(2, U):
        a, b = M().replay(w, h, dx, dy, t), M().replay(w, h, dx, dy, t, "row")
        if a is None or b is None:
            continue
        if a[0] != b[0]:
            cnt.append(t)
        elif a[1] != b[1]:
            pk.append(t)
    cells = cnt[:want]
    m = want - len(cells)
    if m > 0 and pk:
        idx = sorted({round(i * (len(pk) - 1) / (m - 1)) for i in range(m)}) if m > 1 else [len(pk) // 2]
        cells += [pk[i] for i in idx]
    return sorted(cells)


# b_scenes() and b_cells() written out (recomputed and compared by tests/test_gen.py: about four minutes)
B_SCENES_FROZEN = [("s44a", 4096, 4096, 0, 2304, 157), ("s44b", 4096, 4096, 2048, 1792, 131), ("s42", 4096, 2048, 768, 256, 145),
                   ("s22", 2048, 2048, 0, 384, 78), ("s17", 1024, 768, 64, 64, 22)]
B_CELLS_FROZEN = {"s44a": [2, 7, 32, 48, 101, 154], "s44b": [3, 23, 27, 50, 62, 129], "s42": [5, 13, 28, 69], "s22": [2, 6, 24, 73],
                  "s17": [2, 9, 14, 21]}
B_SCENES = B_SCENES_FROZEN
B_CELLS = B_CELLS_FROZEN


def recompute():
    """Every frozen constant above, recomputed from the frozen rules (tests/test_gen.py)."""
    model = {wh: M().model(*wh) for wh in MODEL_FROZEN}
    scenes = b_scenes()
    cells = {n: b_cells(w, h, dx, dy, U, next(c for nm, _, _, c in B_PLAN if nm == n)) for n, w, h, dx, dy, U in scenes}
    return dict(model=model, scenes=scenes, cells=cells)


def scene_of(name):
    return next(s for s in B_SCENES if s[0] == name)


# ------------------------------------------------------------------------------------------------ the stages
STAGES = {"A": ["s-a0", "s-m", "s-b", "s-v"], "B": ["s-k"]}
HDR = {
    "s-a0": "s-a0 premise (6): 2048x2048 calibrations at P 0x162 (S2..S5, 2 pages left) and 0x422 (complete: S2..S7, need 0x213), "
            "c4-b5 R and 2 left, c4-b6 N and 1 left, t-s3m6 1 left, g-qf at P 0xa2 2 partial renders and H-REPLAY64's run peaks.  "
            "Every row is a control and declares what it reads: a control off or WITHOUT A READING, a knob proof off or a capture not "
            "whole STOPS the session before s-m (rc 10, state/CTLFAIL; rc 13 for the capture).",
    "s-m": "s-m margin (50, held out): 3072x3072 (calibration, bands 5 and 6 thr0 B-1..A), 3072x2048, 2048x3072, 2560x2560, "
           "1024x1024 (never run: calibration, B3-1, B3, the parting band's B-1..A) and the six 2048x2048 replicates A-1, A of bands "
           "5 to 7.  H-SPAN: 2 pages left below A_k, 1 from it; E874's B_k the rival (19 cells where it says 1).  A calibration off "
           "the model re-picks its cells as its own S_k + (cell - model S_k), scored for H-SPAN only.",
    "s-b": "s-b count (29, held out): one-triangle scenes never run, picked where H-REPLAY64 and row order differ most: two at "
           "4096x4096 (calibration + 6 cells), one at 4096x2048, 2048x2048 (its calibration dumped: H-WALK64) and 1024x768 "
           "(calibration + 4).  A calibration whose need is not HU1's voids its scene's cells.",
    "s-v": "s-v objects (2, exploration): 2048x2048 --vtx-coords 4 and 8, calibrations with dumps (E900 froze no step rule for larger "
           "objects: R6-dpm's kept readings repeated, no verdict).",
    "s-k": "s-k passes (10, SET B, after the one-shot boot of module 37EC97AB): oomring2 armed before each job (oomring + ldr of 0x0724 "
           "and 0x072c, words 6 and 7 of each rung).  k-b6 first: its premise (the arm accepted, rungs with non-zero counts inside "
           "the host samples' bracket) else STOP; k-b5 and k-b6 controls; c4-b3, S3, S4+1, t-s3m6, band 5 A-1 and A (0x177, "
           "0x178), the 2048x4096 creep cell twice.  An EDM stall is reset once; a second ends s-k.",
}


def row(name, sset, P, knobs, cmd, rt=RT, risk="safe"):
    return dict(name=name, set=sset, risk=risk, P=P, knobs=knobs, rt=rt, cmd=cmd)


def model_knob(wh):
    S, A, B, U = MODEL[wh]
    return "model:" + ",".join(hx(S[k]) for k in sorted(S) if S[k] < CLAMP)


def m_cell(g, k, thr):
    """M:G:k:d:0xP: the model's cell thr0 (P = thr0 + 0x22) when calibration G's steps lie in the model's brackets, else G's own S_k + d
    (d = thr0 - model S_k: the plan's re-pick rule A_k = S_k + (model A_k - model S_k))."""
    S = MODEL[TARGETS[g]][0]
    return f"M:{g}:{k}:{thr - S[k]}:{hx(thr + D_OFF)}"


def reads(*keys):
    return "reads:" + ",".join(keys)


P42 = probe(2048, 2048)


def tables(check=False):
    """The rows of every stage.  check=True (the generator, tests/test_gen.py): refuse a control its job cannot read."""
    T = {}
    S, A, B, U = MODEL[(2048, 2048)]
    T["s-a0"] = [
        row("a0-cal-2048", "control", "0x162", f"stophang prem cal:c2048 {model_knob((2048, 2048))} ctlleft:2 "
            + reads("S2", "S3", "S4", "S5", "knob", "mono", "gps_left"), P42),
        row("a0-cal-2048f", "control", "0x422", f"stophang prem cal:c2048f {model_knob((2048, 2048))} ctlneed:0x213 ctlcnt:0 "
            + reads("S2", "S3", "S4", "S5", "S6", "S7", "knob", "mono", "need", "nparts"), P42),
        row("a0-c4-b5", "control", "0x104", "stophang prem ctl:R ctlleft:2 " + reads("cls", "gps_left", "knob"), P42),
        row("a0-c4-b6", "control", "0x105", "stophang prem ctl:N ctlleft:1 " + reads("cls", "gps_left", "knob"), P42),
        row("a0-t-s3m6", "control", "0xb9", "stophang prem ctlleft:1 " + reads("gps_left", "knob"), P42),
        row("a0-qf-0xa2", "control", "0xa2", "stophang expectdiff prem ctlcnt:2 ctlpeaks:0x80,0xa0,0x2 "
            + reads("nparts", "runpeaks", "knob", "gmax"), qtri()),
    ]
    m = []
    for g in NEW:
        wh = TARGETS[g]
        S, A, B, U = MODEL[wh]
        pr = probe(*wh)
        m.append(row(f"m-cal-{g}", "heldout", "0x422", f"stophang cal:{g} {model_knob(wh)} " + reads("knob", "mono"), pr))
        if g in B3_CELLS:
            for t in (B[3] - 1, B[3]):
                m.append(row(f"m-{g}-{hx(t)}", "heldout", m_cell(g, 3, t), "stophang", pr))
        for k in PART[g]:
            for t in range(B[k] - 1, A[k] + 1):
                m.append(row(f"m-{g}-{hx(t)}", "heldout", m_cell(g, k, t), "stophang", pr))
    S, A, B, U = MODEL[(2048, 2048)]
    for k in (5, 6, 7):
        for t in (A[k] - 1, A[k]):
            m.append(row(f"m-r{k}-{hx(t)}", "repeat", hx(t + D_OFF), "stophang", P42))
    T["s-m"] = m
    b = []
    for name, w, h, dx, dy, U in B_SCENES:
        dump = (w, h) == (2048, 2048)
        b.append(row(f"b-cal-{name}", "heldout", "0x422", f"stophang expectdiff ucal:{name}:{U} " + reads("need", "nparts", "knob", "gmax")
                     + (" tdump" if dump else ""), qtri(w, h, (dx, dy), dump)))
        for t in B_CELLS[name]:
            b.append(row(f"b-{name}-{hx(t)}", "heldout", hx(t + D_OFF), f"stophang expectdiff uneed:{name}", qtri(w, h, (dx, dy))))
    T["s-b"] = b
    T["s-v"] = [row(f"v-cal-c{N}", "explore", "0x422", f"stophang cal:v{N} vprem", probe(2048, 2048, N)) for N in (4, 8)]
    p24 = probe(2048, 4096)
    T["s-k"] = [row("k-b6", "control", "0x105", "stophang fw fwprem " + reads("ring_counts", "dec_sa8_380"), P42),
                row("k-b5", "control", "0x104", "stophang fw " + reads("dec_sa8_380", "cls"), P42),
                row("k-b3", "repeat", "0x10a", "stophang fw", P42),
                row("k-s3", "heldout", hx(S[3] + D_OFF), "stophang fw", P42),
                row("k-s4p1", "heldout", hx(S[4] + 1 + D_OFF), "stophang fw", P42),
                row("k-s3m6", "heldout", "0xb9", "stophang fw", P42),
                row(f"k-b5-{hx(K_B5[0])}", "heldout", hx(K_B5[0] + D_OFF), "stophang fw", P42),
                row(f"k-b5-{hx(K_B5[1])}", "heldout", hx(K_B5[1] + D_OFF), "stophang fw", P42),
                row("k-creep", "heldout", hx(CREEP + D_OFF), "stophang fw", p24),
                row("k-creep2", "repeat", hx(CREEP + D_OFF), "stophang fw", p24)]
    if check:
        SK.refuse_unreadable(control_decls(T), producible)
    return T


def control_decls(T):
    """{name: (reads, row)} of every row that is a control or declares readings (scorekit's form)."""
    return {r["name"]: (tuple(knob_reads(r)), r) for st in T for r in T[st] if r["set"] == "control" or knob_reads(r)}


def knob_reads(r):
    k = next((x[6:] for x in r["knobs"].split() if x.startswith("reads:")), None)
    return k.split(",") if k else []


def target_of(cmd):
    m = re.search(r"--width (\d+) --height (\d+)", cmd)
    return (int(m.group(1)), int(m.group(2))) if m else None


def coords_of(cmd):
    m = re.search(r"--vtx-coords (\d+)", cmd)
    return int(m.group(1)) if m else None


def move_of(cmd):
    m = re.search(r"--move 1:(-?\d+),(-?\d+)", cmd)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def thr0_of(r):
    """The thr0 a row runs at by the frozen model (an M cell: the model's value; the runner re-picks it only if its calibration is off)."""
    P = r["P"]
    if P.startswith("M:"):
        return int(P.split(":")[4], 16) - D_OFF
    return int(P, 16) - D_OFF


def stage_of(name):
    return next(st for st, rows in tables().items() for r in rows if r["name"] == name)


# ------------------------------------------------------------------------------------------------ what a job can read (frozen outcome)
def outcome(r):
    """The frozen expectation of a job's outcome, enough to say which readings it produces: dict(kind, thr0, complete, nparts, U, steps)."""
    t = thr0_of(r)
    wh = target_of(r["cmd"])
    if r["cmd"].startswith("tri"):
        dx, dy = move_of(r["cmd"])
        U = scene_u_frozen(wh, (dx, dy))
        if t >= U:
            return dict(kind="tri", thr0=t, complete=True, nparts=0, U=U)
        n = M().replay(*wh, dx, dy, t)[0]
        return dict(kind="tri", thr0=t, complete=False, nparts=n, U=U)
    N = coords_of(r["cmd"])
    if N:
        S, U = VCAL[N]
        return dict(kind="probe", thr0=t, complete=t >= U, nparts=0 if t >= U else 1, U=U, steps=[k for k, v in S.items() if v < t])
    S, A, B, U = MODEL[wh]
    if t >= U:
        return dict(kind="probe", thr0=t, complete=True, nparts=0, U=U, steps=sorted(S))
    cls = M().guard_class(t, S, A)
    f9 = M().f9_count(*wh, t, cls == "R")
    return dict(kind="probe", thr0=t, complete=False, nparts=f9[0] if f9 else 1, U=U, steps=[k for k, v in S.items() if v < t])


def scene_u_frozen(wh, mv):
    if wh == (4096, 4096) and mv == (0, 0):
        return 287
    s = next((s for s in (B_SCENES or []) if (s[1], s[2]) == wh and (s[3], s[4]) == mv), None)
    return s[5] if s else M().scene_u(*wh, *mv)


def producible(r):
    """The reading keys a row's job produces by its frozen outcome (run/r7read.py line, and r7read.py ring for the own task)."""
    o = outcome(r)
    keys = {"knob", "gmax", "nparts", "mono"} if o["kind"] == "probe" else {"knob", "gmax", "nparts", "runpeaks"}
    if o["kind"] == "probe":
        keys |= {f"S{k}" for k in o.get("steps", [])}
    if o["complete"]:
        keys.add("need")
    else:
        keys |= {"gps_abort", "gps_left", "grow"} if o["kind"] == "probe" else set()
        if o["kind"] == "probe" and o["nparts"] >= 2:
            keys.add("cls")                    # the raise is read at a second abort (R1's valid)
    if " fw" in " " + r["knobs"] and not o["complete"]:
        keys |= {"dec_sa8_380", "ring_counts", "abort_gp", "dec_gp", "pass_tl"}
    return keys


# ------------------------------------------------------------------------------------------------ predictions
def predictions():
    """{stage: [(case, quantity, value, model, set)]}: the frozen predictions."""
    T = tables()
    out = {}
    for st, rows in T.items():
        P = []
        for r in rows:
            n, s, wh, kn = r["name"], r["set"], target_of(r["cmd"]), r["knobs"].split()
            t = thr0_of(r)
            rd = knob_reads(r)
            sset = lambda q: "control" if q in rd else (s if s != "control" else "explore")
            if r["cmd"].startswith("tri"):
                if n.startswith("a0-qf-"):
                    rp = M().replay(4096, 4096, 0, 0, t)
                    P += [(n, "nparts", str(QF[int(r["P"], 16)]), "CTL", "control"), (n, "knob", hx(t), "CTL", "control"),
                          (n, "runpeaks", " ".join(hx(x) for x in rp[1]), "H-REPLAY64", "control"), (n, "gmax", "1", "SCENE", "control")]
                    rr = M().replay(4096, 4096, 0, 0, t, "row")
                    P.append((n, "runpeaks", " ".join(hx(x) for x in rr[1]), "ROW", "explore"))
                    continue
                if n.startswith("b-cal-"):
                    sc = n[len("b-cal-"):]
                    _, w, h, dx, dy, U = scene_of(sc)
                    P += [(n, "need", str(U), "HU1", "control"), (n, "nparts", "0", "HU1", "control"), (n, "knob", hx(t), "CTL", "control"),
                          (n, "gmax", "1", "SCENE", "control")]
                    if "tdump" in kn:
                        P.append((n, "walk64", "exact", "H-WALK64", "heldout"))
                        P.append((n, "walkrow", "exact", "ROW", "heldout"))
                    continue
                sc = n.split("-")[1]
                _, w, h, dx, dy, U = scene_of(sc)
                P.append((n, "knob", hx(t), "CTL", s))
                for o, mdl in (("walk64", "H-REPLAY64"), ("row", "ROW")):
                    rp = M().replay(w, h, dx, dy, t, o)
                    P.append((n, "nparts", str(rp[0]), mdl, s))
                    P.append((n, "runpeaks", " ".join(hx(x) for x in rp[1]), mdl, s))
                P.append((n, "nparts", str(M().dcount(t, U, 1.75)), "d=7/4", s))
                P.append((n, "nparts", str(M().dcount(t, U, 1.0)), "d=1", s))
                P.append((n, "gmax", "1", "SCENE", s))
                continue
            N = coords_of(r["cmd"])
            if N:                                        # s-v: R6-dpm's kept calibrations repeated (exploration)
                S, U = VCAL[N]
                P += [(n, f"S{k}", hx(v), "R6-REPEAT", "explore") for k, v in sorted(S.items())]
                P += [(n, "need", str(U), "R6-REPEAT", "explore"), (n, "nparts", "0", "R6-REPEAT", "explore"),
                      (n, "gmax", ">=2", "SCENE", "explore")]
                continue
            S, A, B, U = MODEL[wh]
            cal = next((k[4:] for k in kn if k.startswith("cal:")), None)
            if cal:
                mdl = "H-STEPMODEL" if st == "s-m" else "H-IV"
                for k in sorted(S):
                    if S[k] < min(t, U):
                        P.append((n, f"S{k}", hx(S[k]), mdl, sset(f"S{k}")))
                if t >= U:
                    P.append((n, "need", hx(U), mdl, sset("need")))
                    P.append((n, "nparts", "0", mdl, sset("nparts")))
                else:
                    P.append((n, "gps_left", str(M().span_left(t, S, A)), "H-SPAN", sset("gps_left")))
                P.append((n, "knob", hx(t), "CTL", sset("knob")))
                P.append((n, "mono", "1", "CTL", sset("mono")))
                P.append((n, "gmax", ">=2", "SCENE", sset("gmax")))
                continue
            P.append((n, "knob", hx(t), "CTL", sset("knob")))
            on = t in S.values()
            if st != "s-k":
                P.append((n, "grow", "1" if on else "0", "H-GREQ", s if s != "control" else "explore"))
            left = M().span_left(t, S, A)
            ctl_l = next((k[8:] for k in kn if k.startswith("ctlleft:")), None)
            if ctl_l:
                P.append((n, "gps_left", ctl_l, "CTL", "control"))
            elif left is not None:
                P.append((n, "gps_left", str(left), "H-SPAN", s))
                P.append((n, "gps_left", str(M().span_left(t, S, B)), "E874-B", s))
            cls = M().guard_class(t, S, A)
            ctl_c = next((k[4:] for k in kn if k.startswith("ctl:")), None)
            f9 = M().f9_count(*wh, t, cls == "R")
            if ctl_c:
                P.append((n, "cls", ctl_c, "CTL", "control"))
            elif st == "s-m":
                if f9 and f9[0] >= 2:                      # the raise is decided at a second abort
                    P.append((n, "cls", cls, "R-5", s))
                P.append((n, "nparts", str(f9[0]) if f9 else "None", "F9", "explore"))
            if st == "s-k":
                kref = KEPT_2X4 if wh == (2048, 4096) else S
                ab = M().gps_abort(t, kref)
                dl = 1 if on else (left if left in (1, 2) else None)
                if n == "k-b5":
                    P += [(n, "dec_sa8_380", "0x180", "CTL", "control"), (n, "cls", "R", "CTL", "control")]
                elif n == "k-b6":
                    P += [(n, "dec_sa8_380", "0x0", "CTL", "control"), (n, "cls", "N", "CTL", "control"),
                          (n, "ring_counts", "1", "PREMISE", "control")]
                else:
                    P.append((n, "dec_sa8_380", "0x180" if cls == "R" else "0x0", "R-5", s))
                    P.append((n, "cls", cls, "R-5", s))
                    if n.startswith("k-creep"):
                        P.append((n, "dec_sa8_380", "0x180", "ISUB-REV", s))
                    if n.startswith("k-b5-"):
                        cb = M().guard_class(t, S, B)
                        P.append((n, "dec_sa8_380", "0x180" if cb == "R" else "0x0", "R-5|E874-B", s))
                P.append((n, "abort_gp", str(ab), "H-PASS", s if s != "control" else "heldout"))
                if dl is not None:
                    P.append((n, "dec_gp", str(dl), "H-PASS", s if s != "control" else "heldout"))
                P.append((n, "pass_tl", "1", "H-PASS", s if s != "control" else "heldout"))
                f9 = M().f9_count(*wh, t, cls == "R")
                P.append((n, "nparts", str(f9[0]) if f9 else "None", "F9", "explore"))
        out[st] = P
    return out


def table_text(st, rows):
    lines = [f"#stage {st}", f"#set {SET_OF[st]}", f"#module {SRCV[SET_OF[st]]}", f"#need $S/{PROG}"]
    if st == "s-k":
        lines.append("#need $S/oomring2.blob")
    for chunk in [HDR[st][i:i + 128] for i in range(0, len(HDR[st]), 128)]:
        lines.append("# " + chunk)
    for r in rows:
        lines.append("|".join((r["name"], r["set"], r["risk"], r["P"], r["knobs"], r["rt"], r["cmd"])))
    return "\n".join(lines) + "\n"


def tables_md(T, Pr):
    out = ["# R7-dpm: the frozen tables and predictions (generated by gen/r7plan.py; do not edit)", "",
           f"Register list (all rows, r5's): `{RT}`.", "",
           "P forms: `0xN` fixed; `M:G:k:d:0xP` the frozen model's cell 0xP (thr0 = P - 0x22), re-picked as calibration G's own S_k + d "
           "when G's steps lie outside the model's brackets.  The thr0 column is the frozen model's value.  `reads:` names the readings a "
           "control needs: a control without one of them STOPS at the premise (s-a0, s-k's k-b6).", "",
           "s-b scenes (build rule in gen/r7plan.py b_scenes): " + ", ".join(f"{n} = {w}x{h} --move 1:{dx},{dy} (HU1 U {U})"
                                                                         for n, w, h, dx, dy, U in B_SCENES) + ".", ""]
    tot = {"A": 0, "B": 0}
    for set_ in ("A", "B"):
        for st in STAGES[set_]:
            out += [f"## {st} (set {set_}, module {SRCV[set_][:8]}: {len(T[st])} jobs)", "", HDR[st], "",
                    "| job | set | P | thr0 (model) | knobs | target / scene | predictions |", "|---|---|---|---|---|---|---|"]
            tot[set_] += len(T[st])
            for r in T[st]:
                pr = "; ".join(f"{q} = {v} [{m}]" for c, q, v, m, s in Pr[st] if c == r["name"])
                if r["cmd"].startswith("probe"):
                    sc = "tri 1500" + (f" vtx-coords {coords_of(r['cmd'])}" if coords_of(r["cmd"]) else "")
                else:
                    sc = "tri -n 1 " + ("move %d,%d" % move_of(r["cmd"]) if "--move" in r["cmd"] else "default")
                wh = target_of(r["cmd"])
                kn = r["knobs"].replace("|", "/")
                if len(kn) > 70:
                    kn = kn[:67] + "..."
                out.append(f"| {r['name']} | {r['set']} | {r['P']} | {hx(thr0_of(r))} | {kn} | {wh[0]}x{wh[1]} {sc} | {pr} |")
            out.append("")
    out.insert(4, f"**{tot['A'] + tot['B']} jobs**: set A {tot['A']} (" + ", ".join(f"{st} {len(T[st])}" for st in STAGES["A"])
               + f"), set B {tot['B']} (s-k).")
    out.insert(5, "")
    return "\n".join(out) + "\n"


def write(sets=("A", "B")):
    T, Pr = tables(check=True), predictions()
    (KP / "tables").mkdir(exist_ok=True)
    (KP / "predictions").mkdir(exist_ok=True)
    for set_ in sets:
        for st in STAGES[set_]:
            (KP / "tables" / f"{st}.txt").write_text(table_text(st, T[st]))
            (KP / "predictions" / f"{st}.tsv").write_text("case\tquantity\tvalue\tmodel\tset\n" +
                                                          "".join("\t".join(p) + "\n" for p in Pr[st]))
    (KP / "stages.txt").write_text("\n".join(STAGES["A"]) + "\n")
    (KP / "stagesB.txt").write_text("\n".join(STAGES["B"]) + "\n")
    (KP / "TABLES.md").write_text(tables_md(T, Pr))
    return T


def main():
    T = write()
    print(sum(len(v) for v in T.values()), "jobs;", {st: len(v) for st, v in T.items()}, "B scenes:", B_SCENES)


if __name__ == "__main__":
    if sys.argv[1:] == ["--print-frozen"]:
        rc = recompute()
        print("B_SCENES_FROZEN =", rc["scenes"])
        print("B_CELLS_FROZEN =", rc["cells"])
        for wh, v in rc["model"].items():
            print(wh, v)
    else:
        main()
