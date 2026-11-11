# SPDX-License-Identifier: MIT
"""Stage q4-t (Q082, pixel side, triangles; 54 jobs, plan section 3.3; decision: triangles a, the t6 row, without 2x2).

`probe --tri pixel --temps 32 --width W --height H --tri-full "loop"` with the relative b8 loop and MARK, as E806 (round 3's q-t).  E806
first set bit 6 at 56 iterations (32x16, 32x32, 128x128: clear at 53) and at 110 (8x8, 16x16, 64x32, 256x256) and at 220 (4x4); the
tile time of every size at its last clear and first set point brackets 120 to 160 us (slope a tile 0.72 us / N at 4x4, 1.65 at 8x8,
2.5 at 16x16 and 64x32; qt_slopes.out).  H-SEG: bit 6 latches when the pixel side makes no progress for about 125 us, progress being
the end of a piece of work that is at most a tile; H-N: the threshold is a pass count near 57 to 62 at every size; E806-DISC: the first
set point of a size is 56 or 110 (220 at 4x4) as E806 read it, discrete.  Rows (frozen, plan 3.3):
  controls (12, set control): the stock green triangle and the loop at N = 1 at 4x4, 8x8, 16x16, 32x16, 64x32 (MARK on W x H of W x H
    / green), and the fill (probe without --tri) at 53 and 56: clear, set (the bridge to E804 on the rgn4 module; want2 stops the
    session if it reads otherwise);
  8x8 at 60, 66, 72, 80, 88, 96, 104 (H-SEG: 60 and 66 clear, 104 set, first set 72 to 104; H-N: 66 and up set; E806-DISC: all clear);
  4x4 at 80, 110, 140, 170, 200 (H-SEG: 80, 110, 140 clear; H-N: set from 80; E806-DISC: all clear to 200);
  16x16, 32x16 and 64x32 at 46, 56, 56 again, 60, 66, 72 (H-SEG: 46 clear, 66 and 72 set at all three, 56 and 60 either; H-N the same;
    E806-DISC: 32x16 set from 56, the other two clear to 72);
  64x32 and 8x8 at 150, 180, 250, 330 (set; the first-piece reading: t6 = 250 + 0.43 N us after the burst starts to N = 290, 250 beyond,
    +- 15 us; the t6 rows are the only test of that reading: if they fail the bit rule can still hold);
  the default (partial) 64x64 triangle at 150, 200, 280, 400 (exploratory: no prediction).
H-SEG is refuted by 16x16 or 64x32 clear at 72, by 8x8 set at 60 or clear at 104, by 4x4 set at 110; E806-DISC by a size that sets at 66
where it predicts clear (8x8, 16x16, 64x32) or clear at 66 at 32x16.  sgx-pipe's status2_bit6 (a 64 x 32 fill without a load) stays
refused for a triangle and agrees with the fill controls (clear at 53 is the edge row of the bridge: it refuses 53 and 56 as in q4-f).
"""
from __future__ import annotations

import r4common as K
from r4common import C, LP, Row, build_bin

S2 = "stophang s2"
GREEN_COLOR = "0xff00ff00"
HYPS = ("H-SEG", "H-N", "E806-DISC")


def tcmd(w, h, prog, full=True):
    return f'probe --tri pixel --temps 32 --width {w} --height {h}' + (" --tri-full" if full else "") + f' "{prog}"'


def sz(w, h):
    return f"{w}x{h}"


def build():
    rows, preds, needs = [], [], []
    P = lambda *a: preds.append(a)
    green = build_bin("pix_green", (K.TEMPLATES / "pix_green.s").read_text())
    needs.append(green)

    def loop_prog(n):
        name, text, info = LP.pixel_loop_source("b8", n)
        p = build_bin(name, text)
        needs.append(p)
        return p

    def add(name, st, cmd, role, w, h, full, n=None, knobs=S2):
        rows.append(Row(name, st, K.SAFE, knobs, C.RT_REGS, cmd, role))
        P(name, "status2_pre", "0x400", "R1-events / E784 (a debugfs reset leaves CR_EVENT_STATUS2 at 0x400)", st)
        if n is not None and full:
            P(name, "proof", f"0x{LP.mark(n):08x} {w * h}", "the MARK loop proof: o0 = MARK on every pixel of the target", st)

    def bit6_hyps(name, w, h, n, st):
        for hyp in HYPS:
            P(name, "bit6", C.t_pred(hyp, (w, h), n), f"{hyp} (frozen table, score/r4const.py t_pred)", st)

    # ------------------------------------------------------------ controls (12)
    for w, h in C.T_CTL_SIZES:
        name = f"t4-ctl-green-{sz(w, h)}"
        add(name, "control", tcmd(w, h, green), f"control: the stock green triangle over the whole {w}x{h} target", w, h, True, knobs=S2 + " want2:0xc0:0x00")
        P(name, "green", f"{GREEN_COLOR} {w * h}", "the full triangle covers the target: o0 green on W x H of W x H", "control")
        P(name, "bit6", "clear", "R1-events / E784 (no loop: STATUS2 stays 0x400)", "control")
    for w, h in C.T_CTL_SIZES:
        name = f"t4-ctl-n1-{sz(w, h)}"
        add(name, "control", tcmd(w, h, loop_prog(1)), f"control: the loop at N = 1 over the whole {w}x{h} target: MARK on W x H of W x H (a size failing it is void)",
            w, h, True, 1, knobs=S2 + " want2:0xc0:0x00")
        P(name, "bit6", "clear", "far below any threshold (one iteration)", "control")
    for n, bit in ((53, "clear"), (56, "set")):
        p = loop_prog(n)
        name = f"t4-fill-n{n}"
        mk = LP.mark(n)
        rows.append(Row(name, "control", K.SAFE, f"{S2} proofstop:0x{mk:08x}:2048 want2:" + ("0x40:0x00" if bit == "clear" else "0x40:0x40"),
                        C.RT_REGS, f'probe "{p}"', f"bridge to E804: the fill (2048 pixels) at N = {n}: bit 6 {bit}"))
        P(name, "status2_pre", "0x400", "R1-events / E784 (a debugfs reset leaves CR_EVENT_STATUS2 at 0x400)", "control")
        P(name, "proof", f"0x{mk:08x} 2048", "the MARK loop proof: o0 = MARK on 2048 of 2048", "control")
        P(name, "bit6", bit, "E804 (53 clear, 56 set: 2 of 2 each) and E431; sgx-pipe status2_bit6 refuses both (tile time 119.5 / 126.5 us inside its edge)", "control")
    # ------------------------------------------------------------ 8x8 ladder, 4x4 ladder
    for n in C.T_8X8_N:
        name = f"t4-8x8-n{n}"
        add(name, "heldout", tcmd(8, 8, loop_prog(n)), f"8x8 at N = {n}: HELD OUT", 8, 8, True, n)
        bit6_hyps(name, 8, 8, n, "heldout")
    for n in C.T_4X4_N:
        name = f"t4-4x4-n{n}"
        add(name, "heldout", tcmd(4, 4, loop_prog(n)), f"4x4 (16 pixels) at N = {n}: HELD OUT", 4, 4, True, n)
        bit6_hyps(name, 4, 4, n, "heldout")
    # ------------------------------------------------------------ the three mid sizes at 46, 56, 56 again, 60, 66, 72
    for w, h in C.T_MID_SIZES:
        for tag, n in C.T_MID_N:
            name = f"t4-{sz(w, h)}-n{tag}"
            add(name, "heldout", tcmd(w, h, loop_prog(n)), f"{w}x{h} at N = {n}" + (" (second run)" if tag.endswith("b") else "") + ": HELD OUT", w, h, True, n)
            bit6_hyps(name, w, h, n, "heldout")
    # ------------------------------------------------------------ the time of the latch (first-piece reading)
    for w, h in C.T_T6_SIZES:
        for n in C.T_T6_N:
            name = f"t4-{sz(w, h)}-n{n}"
            add(name, "heldout", tcmd(w, h, loop_prog(n)), f"{w}x{h} at N = {n}: HELD OUT (set, and the time of the latch)", w, h, True, n)
            P(name, "bit6", "set", "H-SEG, H-N (a tile time of 250 us and more: set at every size)", "heldout")
            P(name, "t6_us", f"{C.t6_pred(n):.1f}+-{C.T6_TOL:.0f}", "first-piece reading (t6 = 250 + 0.43 N to N = 290, then 250 us after the burst starts; E806, FIT)", "heldout")
    # ------------------------------------------------------------ the default partial triangle: exploratory
    for n in C.T_PAR_N:
        name = f"t4-par-64x64-n{n}"
        add(name, "heldout", tcmd(64, 64, loop_prog(n), full=False), f"exploratory: the default (partial) triangle at 64x64, N = {n}", 64, 64, False)
        P(name, "bit6", "none", "exploratory: no frozen prediction (the covered pixels are fewer than the target)", "heldout")
    return rows, preds, list(dict.fromkeys(needs)), __doc__
