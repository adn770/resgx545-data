# SPDX-License-Identifier: MIT
"""Frozen constants shared by the R4-pixel generators and scorers (Q082 stages q4-v, q4-f, q4-t; the other stages carry their
own constants in their own modules).  Extended by the Q082 builder; stages p4-o4 and g4-rw import only RT_REGS from here."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

RT_REGS = "0x0008,0x0118,0x012c"
BIT6, BIT7 = 0x40, 0x80
BASE_DEPTH = 0x3F200000                       # stored depth word of a vertex loop of N iterations: BASE_DEPTH + N
EITHER = "either"

# ---- Q082 TA side (q4-v): the frozen offline model of L, the longest run of the TA's clocks, per vertex loop (FIT: E807's 74 jobs in
# closing-r3-pixel, least squares of L = a + s N over the jobs with L > 30 us, per ladder; round 4 planning scratch).  Used only to place
# the ladders' points (0.80 .. 1.60 x N*) and to print a layout check; the rule that is scored is the one on each job's own L.
V_L_FIT = {   # ladder: (slope us an iteration, intercept us)
    "b4v3": (0.0748, 6.15), "b8v3": (0.1166, 3.55), "b16v3": (0.1944, 5.30), "v12": (0.2041, 8.61), "v48": (0.2804, 8.07),
}
V_BODY_LEN = {"b2v": 2, "b4v": 4, "b8v": 8, "b12v": 13, "b16v": 16}   # instructions an iteration (the vertex bodies carry the depth accumulator, except b2v)
V_THRESHOLD = 129.5                            # us of L: bit 7 set iff L >= this (edge 122..136)
V_RATIOS = (0.80, 0.92, 1.08, 1.20, 1.60)      # held-out points of a ladder, times N*
V_FIT_RATIOS = (0.45, 0.70)                    # the two FIT points of a ladder (clear by the model)


def v_slope(kind: str, nvert: int):
    """(slope, intercept) of the model L = a + s N for a ladder kind and vertex count: the b8v/b16v/b4v slopes at 3 vertices are linear in the
    body length (0.0748, 0.1166, 0.1944 for 4, 8, 16: 0.0105 and 0.0097 an instruction; the line through b8v and b16v is used for b12v and
    b2v); the vertex count scales the b8v slope along log2 V between the 12 and 48 vertices fits (0.2041, 0.2804)."""
    import math
    if nvert == 3:
        s8, s16 = V_L_FIT["b8v3"][0], V_L_FIT["b16v3"][0]
        per = (s16 - s8) / 8.0
        s = s8 + per * (V_BODY_LEN[kind] - 8)
        return s, 5.0
    assert kind == "b8v"
    (s12, a12), (s48, a48) = V_L_FIT["v12"], V_L_FIT["v48"]
    f = (math.log2(nvert) - math.log2(12)) / (math.log2(48) - math.log2(12))
    return s12 + f * (s48 - s12), a12 + f * (a48 - a12)


def v_nstar(kind: str, nvert: int) -> float:
    s, a = v_slope(kind, nvert)
    return (V_THRESHOLD - a) / s


def v_points(kind: str, nvert: int):
    """([the 2 FIT points], [the 5 held-out points]) of a ladder as integers (rounded to 5)."""
    n = v_nstar(kind, nvert)
    r5 = lambda x: int(round(x / 5.0) * 5)
    return [r5(n * f) for f in V_FIT_RATIOS], [r5(n * f) for f in V_RATIOS]


def v_model_L(kind: str, nvert: int, n: int) -> float:
    s, a = v_slope(kind, nvert)
    return a + s * n

# ---- Q082 pixel side, fills (q4-f): the burst model of E431 / E804 (B = B0 + B1 N for the b8 body, sd 36 us) and the frozen rule on a
# tile's time (r4tl.bit6_rule: clear below 118 us, set above 132 us; the same edge as sgx-pipe's events::status2_bit6)
B0, B1, B_SD = 60.2, 9.02, 36.0
TILES = 4
T6_LO, T6_HI = 120.0, 340.0                   # bit 6 shows 120..340 us after the burst starts (E805: 48 of 48 set jobs)
F_BRIDGE = [("rel-b8-16", 16), ("rel-b8-53", 53), ("rel-b8-56", 56), ("rel-b8-136", 136)]
F_LD0 = [28, 53, 70, 110]
F_LDO = [(28, 4), (28, 16), (40, 8), (70, 1), (70, 4), (110, 2), (220, 1)]
# frozen predictions of the three readings of "a load" per row (plan 3.2): c = clear, S = set, either = not scored
F_HYP = {
    "H-YIELD": {"ld0": ["c", "either", "S", "S"], "ldo": ["c", "c", "c", "S", "S", "S", "S"]},     # a wait restarts the timer
    "H-LOADOFF": {"ld0": ["c", "c", "c", "c"], "ldo": ["c", "c", "c", "c", "c", "c", "c"]},        # a waiting program never latches
    "H-SUM": {"ld0": ["c", "either", "S", "S"], "ldo": ["S", "S", "S", "S", "S", "S", "S"]},       # the busy time of the tile is summed
}


def b8_burst(n: int) -> float:
    return B0 + B1 * n


def b8_tau(n: int) -> float:
    return (b8_burst(n) - B0) / TILES

# ---- Q082 pixel side, triangles (q4-t): E806's tile time per size (slope a tile us / N, closing4/pixel/qt_slopes.out: FIT) and the
# frozen predictions of H-SEG, H-N and E806-DISC per size and N (plan 3.3)
T_SLOPE = {(4, 4): 0.72, (8, 8): 1.65, (16, 16): 2.50, (32, 16): 2.55, (32, 32): 2.38, (64, 32): 2.50, (128, 128): 2.29, (256, 256): 2.27}
T_E806_FIRST = {(4, 4): 220, (8, 8): 110, (16, 16): 110, (32, 16): 56, (32, 32): 56, (64, 32): 110, (128, 128): 56, (256, 256): 110}
T_CTL_SIZES = [(4, 4), (8, 8), (16, 16), (32, 16), (64, 32)]
T_MID_SIZES = [(16, 16), (32, 16), (64, 32)]
T_MID_N = [("46", 46), ("56", 56), ("56b", 56), ("60", 60), ("66", 66), ("72", 72)]
T_8X8_N = [60, 66, 72, 80, 88, 96, 104]
T_4X4_N = [80, 110, 140, 170, 200]
T_T6_N = [150, 180, 250, 330]
T_T6_SIZES = [(64, 32), (8, 8)]
T_PAR_N = [150, 200, 280, 400]
T6_TOL = 15.0


def t6_pred(n: int) -> float:
    """The first-piece reading: bit 6 shows 250 + 0.43 N us after the burst starts up to N = 290, 250 us beyond (E806, FIT)."""
    return 250.0 + 0.43 * n if n <= 290 else 250.0


def t_pred(hyp: str, size, n: int) -> str:
    """'clear' / 'set' / 'either' of a hypothesis at a size and N (a fully covered triangle, relative b8 loop)."""
    if hyp == "H-SEG":
        if size == (8, 8):
            return "clear" if n <= 66 else "set" if n >= 104 else EITHER
        if size == (4, 4):
            return "clear" if n <= 140 else EITHER
        if size in T_MID_SIZES:
            return "clear" if n <= 46 else "set" if n >= 66 else EITHER
        return EITHER
    if hyp == "H-N":                               # a pass count near 57 to 62 at every size
        return "clear" if n <= 46 else EITHER if n <= 62 else "set"
    if hyp == "E806-DISC":                         # E806's reading read as discrete: the first set point of the size is 56 or 110 (220 at 4x4)
        return "set" if n >= T_E806_FIRST[size] else "clear"
    raise KeyError(hyp)
