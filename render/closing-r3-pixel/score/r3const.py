# SPDX-License-Identifier: MIT
"""Frozen constants and rules shared by the R3-pixel generator (gen/r3gen.py) and scorers (score/score_r3.py): the ladders, the
sizes, the E431/E357 fits the hypotheses are read from (FIT), the allowed bands and the hypothesis predictions that depend only
on the table (H-MA, H-INST, H-TILE, H-JOB).  Hypotheses that depend on what a job measures (H-WD, H-BURST, H-WD-busy, HV-*) are
functions below that the scorer applies to the measured burst length or bracket; their constants are frozen here.
Labels: FIT = from data before this run (E431, E357, E769, E784, R1/R2 kept output), HELD OUT = a row a rule predicts before
it runs."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

RT_REGS = "0x0008,0x0118,0x012c"
BIT6, BIT7 = 0x40, 0x80
BASE_DEPTH = 0x3F200000                       # stored depth word of a vertex loop of N iterations: BASE_DEPTH + N
E784_INTACT_VERTEX_ITERS = 3 * 1760           # work E784 ran intact: 3 vertices x 1760 iterations of body 8

# ---- Q082 pixel side: the fill ladders (q-f1), 54 jobs each order; the first two points of a ladder are its FIT rows
F_LADDERS = {
    "b16": [6, 12, 21, 22, 23, 24, 25, 104],
    "b12": [8, 16, 28, 30, 31, 32, 33, 34, 35, 36, 38, 136],
    "b4": [40, 80, 130, 140, 150, 156, 160, 164, 168, 172, 180, 200, 240, 320, 640],
    "b2": [500, 1000, 2000, 4000, 8000, 16000],
    "b8n": [60, 120, 240, 480, 960, 1920, 3840],
    "ld8": [20, 70, 79, 84, 160, 320],
}
IMAE_PER_ITER = {"b16": 14, "b12": 10, "b8": 6, "b4": 2, "b2": 0, "b8n": 0, "ld8": 4}
INSTR_PER_ITER = {"b16": 16, "b12": 12, "b8": 8, "b4": 4, "b2": 2, "b8n": 8, "ld8": 8}

# E431 / E357 timelines (closing3/pixel/q082_fit.out): burst length B = B0 + B1 * N (body 8), residual sd 36 us; bit 6 shows
# 124..329 us (median 200) after the burst starts whatever N; a tile (a fill is four 32x16 tiles) takes (B - B0) / 4
B0, B1, B_SD = 60.2, 9.02, 36.0
TILES = 4
T_STAR, T_TOL = 121.8, 3.0                    # H-WD: a tile's time >= T* sets the bit (E764: 121.1..124.1 us fault to bit)
WD_BAND = 0.08                                # H-WD: N* = 4 T* / s_body, +- max(8%, 2 sigma of the slope)
BURST_STAR, BURST_TOL = 536.0, 20.0           # H-BURST: the job's burst B >= 536 us sets the bit
M_LO, M_HI = 318, 336                         # H-MA: multiply-adds of an instance, M* in (318, 336] (E431: 53 clear, 56 set)
T6_LO, T6_HI = 120.0, 340.0                   # time of the latch from the burst's start: 124..329 us (32 of 32 FIT jobs)
T6_END_FRAC = 0.15                            # H-END: the latch within 15% of the burst's end
CLUSTER_START, CLUSTER_TOL = 25.0, 30.0       # near the threshold H-WD: t6 = 25 + k (B - B0) / 4 + T*, k = 0..3, +- 30 us
LONG_FACTOR = 1.3                             # "set well above its threshold": N >= 1.3 N*
EITHER = "either"


def ma_count(kind: str, n: int) -> int:
    return IMAE_PER_ITER[kind] * n


def pred_ma(kind: str, n: int) -> str:
    """H-MA: the bit is set iff the multiply-adds of an instance reach M* in (318, 336]."""
    m = ma_count(kind, n)
    return "clear" if m <= M_LO else "set" if m >= M_HI else EITHER


def wd_slope(points):
    """s_body (us an iteration) from a ladder's two short points [(N, B), (N, B)]: each gives (B - B0) / N with sd B_SD / N;
    inverse-variance weighted.  Returns (s, sd)."""
    num = sum((b - B0) / n * (n * n) for n, b in points)
    den = sum(n * n for n, b in points)
    return num / den, B_SD / den ** 0.5


def wd_nstar(points):
    s, sd = wd_slope(points)
    if s <= 0:
        return None, None
    n = TILES * T_STAR / s
    band = max(WD_BAND, 2 * sd / s)
    return n, band


def pred_wd(kind: str, n: int, nstar, band, own_b=None) -> str:
    """H-WD: clear below N* (1 - band), set above N* (1 + band), either between.  ld8 uses the job's own burst (a tile's time
    (B - B0) / 4 >= T* +- T_TOL, with the sd of that estimate B_SD / 4 added): the wait on a load is in B."""
    if kind == "ld8" and own_b is not None:
        t = (own_b - B0) / TILES
        tol = T_TOL + B_SD / TILES
        return "clear" if t <= T_STAR - tol else "set" if t >= T_STAR + tol else EITHER
    if nstar is None:
        return EITHER
    return "clear" if n <= nstar * (1 - band) else "set" if n >= nstar * (1 + band) else EITHER


def pred_burst(own_b) -> str:
    return "clear" if own_b <= BURST_STAR - BURST_TOL else "set" if own_b >= BURST_STAR + BURST_TOL else EITHER


# ---- q-t: occupancy with the working triangle loop: sizes, ladders and first-set tables of the design (bridge = 64x32)
T_SIZES = [(8, 8), (16, 16), (32, 16), (32, 32), (64, 32), (128, 128), (256, 256)]
T_LADDER = [4, 14, 28, 53, 56, 110, 220, 440, 880, 1760, 3520]
T_PIXEL_ITER_MAX = 2.3e7                       # pixels x N <= this (E357's longest completed fill, 112 ms)
T_EXTRA_4X4 = [56, 220, 880]
T_BRIDGE = (64, 32)
# the first ladder point with the bit set, by hypothesis, when the bridge's own first set is 56 (the design's table); a cell is a
# set of allowed first points; ref != 56 scales every value by ref / 56 (first ladder point >= value * ref / 56)
T_FIRST = {
    "H-INST": {(8, 8): [56], (16, 16): [56], (32, 16): [56], (32, 32): [56], (64, 32): [56], (128, 128): [56], (256, 256): [56]},
    "H-TILE": {(8, 8): [440, 880], (16, 16): [110], (32, 16): [56], (32, 32): [56], (64, 32): [56], (128, 128): [56], (256, 256): [56]},
    "H-JOB": {(8, 8): [1760, 3520], (16, 16): [440, 880], (32, 16): [220], (32, 32): [110], (64, 32): [56],
              (128, 128): [14, 28], (256, 256): [4, 14]},
}


def t_ladder(w: int, h: int):
    return [n for n in T_LADDER if w * h * n <= T_PIXEL_ITER_MAX]


def t_allowed(hyp: str, size, ref: int = 56, ladder=None):
    """The allowed first-set ladder points of a hypothesis at a size, scaled from the measured bridge point ref (56: as is)."""
    lad = ladder or t_ladder(*size)
    out = []
    for v in T_FIRST[hyp][size]:
        scaled = v * ref / 56.0
        first = next((n for n in lad if n >= scaled - 1e-9), None)
        out.append(first)
    return sorted({x for x in out if x is not None}) or [None]


def t_pixels(size):
    return size[0] * size[1]


# ---- q-v: the TA side, bit 7 (E784: i880 clear, i1760 set with body 8 on 3 vertices)
V_CTL = [0, 1, 3]
V_B8_UP = list(range(935, 1706, 55))                      # 15 points
V_B16 = [round(280 * (950 / 280) ** (i / 16)) for i in range(17)]
V_B4 = [round(1760 * (9000 / 1760) ** (i / 14)) for i in range(15)]
V_12 = [round(110 * (1760 / 110) ** (i / 12)) for i in range(13)]
V_48 = [round(28 * (880 / 28) ** (i / 7)) for i in range(8)]
V_ITER_PER_BODY = {"b8v": 8, "b16v": 16, "b4v": 4}
V_IMAE_PER_BODY = {"b8v": 5, "b16v": 13, "b4v": 1}
V_STEP_TOL = 1                                           # frozen formulas are met within one ladder step


def v_formula(hyp: str, ladder: str, n8: float):
    """Predicted first-set N of a ladder from N8* (the b8v bracket's point), by hypothesis; None = not predicted."""
    if ladder == "b16v":
        return {"HV-INSTR": n8 / 2, "HV-MA": 0.385 * n8}.get(hyp)
    if ladder == "b4v":
        return {"HV-INSTR": 2 * n8, "HV-MA": 5 * n8}.get(hyp)
    if ladder == "v12":
        return {"HV-INSTR": n8, "HV-MA": n8, "HV-JOB": n8 / 4}.get(hyp)
    if ladder == "v48":
        return {"HV-INSTR": n8, "HV-MA": n8, "HV-JOB": n8 / 16}.get(hyp)
    return None
