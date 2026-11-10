# SPDX-License-Identifier: MIT
"""Stage q-t (Q082, pixel side): occupancy with the working triangle loop (decision R3-P2: full-target triangles at seven sizes
plus the 64x32 bridge to the fill; R3-P5: jobs up to about 100 ms, pixels x N <= 2.3e7; R3-P8: the 4x4 loop rows last).
closing3/pixel/exp-pixel-r3.md section 1.3."""
from __future__ import annotations

import r3common as K
from r3common import C, LP, Row, build_bin, mark_hex

S2 = "stophang s2"
GREEN_COLOR = "0xff00ff00"


def tcmd(w, h, prog, full=True):
    return (f'probe --tri pixel --temps 32 --width {w} --height {h}' + (" --tri-full" if full else "") + f' "{prog}"')


def loop_prog(n):
    name, text, info = LP.pixel_loop_source("b8", n)
    return build_bin(name, text), name


def sz(w, h):
    return f"{w}x{h}"


def t():
    rows, preds, needs = [], [], []
    green = build_bin("pix_green", (K.TEMPLATES / "pix_green.s").read_text())
    needs.append(green)

    def add(name, st, cmd, role, w, h, full, n=None):
        rows.append(Row(name, st, K.SAFE, S2, C.RT_REGS, cmd, role))
        preds.append((name, "status2_pre", "0x400", "R1-events / E784 (a debugfs reset leaves CR_EVENT_STATUS2 at 0x400)", st))
        if n is not None and full:
            preds.append((name, "proof", f"{mark_hex(n)} {w * h}", "the MARK loop proof: o0 = MARK on every pixel of the target", st))

    # controls: the stock green shader over the whole target, and the loop at N = 1, at the seven sizes
    for w, h in C.T_SIZES:
        n = f"t-ctl-green-{sz(w, h)}"
        add(n, "control", tcmd(w, h, green), f"control: stock pix_green over the whole {w}x{h} target (full triangle)", w, h, True)
        preds.append((n, "green", f"{GREEN_COLOR} {w * h}", "the full triangle covers the target: o0 green on W x H of W x H", "control"))
        preds.append((n, "bit6", "clear", "R1-events / E784 (no loop: STATUS2 stays 0x400)", "control"))
    for w, h in C.T_SIZES:
        p, prog = loop_prog(1)
        needs.append(p)
        n = f"t-ctl-n1-{sz(w, h)}"
        add(n, "control", tcmd(w, h, p), f"control: the loop at N = 1 over the whole {w}x{h} target: MARK on W x H of W x H "
            f"(a size failing it is void)", w, h, True, 1)
        preds.append((n, "bit6", "clear", "far below any threshold (one iteration)", "control"))
    # the bridge to the fill: the 64x32 target at 53 and 56 (the fill's own size: 2048 pixels)
    for N, bit in ((53, "clear"), (56, "set")):
        p, prog = loop_prog(N)
        needs.append(p)
        n = f"t-bridge-64x32-n{N}"
        add(n, "control", tcmd(64, 32, p), f"bridge: 64x32 at N = {N} (the fill's size; E431: 53 clear, 56 set)", 64, 32, True, N)
        preds.append((n, "bit6", bit, "E431 / E769 (the fill's threshold at 2048 pixels)", "control"))
    # ladders, every size ascending in N, cut where pixels x N would pass 2.3e7
    order = [(64, 32), (32, 32), (32, 16), (16, 16), (8, 8), (128, 128), (256, 256)]
    for w, h in order:
        lad = C.t_ladder(w, h)
        for N in lad:
            p, prog = loop_prog(N)
            needs.append(p)
            n = f"t-{sz(w, h)}-n{N}"
            add(n, "heldout", tcmd(w, h, p), f"ladder {w}x{h} ({w * h} pixels), N = {N}: HELD OUT", w, h, True, N)
            for hyp in ("H-INST", "H-TILE", "H-JOB"):
                preds.append((n, "bit6", "formula", f"{hyp} (first ladder point with the bit set in "
                              f"{C.t_allowed(hyp, (w, h))}; see ladder-{sz(w, h)})", "heldout"))
            preds.append((n, "t6_us", f"{C.T6_LO:.0f}..{C.T6_HI:.0f}",
                          "H-WD (the latch 120..340 us after the burst starts at every size where the bit sets well above its threshold)",
                          "heldout"))
    for w, h in C.T_SIZES:
        for hyp in ("H-INST", "H-TILE", "H-JOB"):
            allowed = C.t_allowed(hyp, (w, h))
            preds.append((f"ladder-{sz(w, h)}", "first_set", ",".join(str(a) for a in allowed),
                          f"{hyp} (the design's table scaled by the measured 64x32 first set / 56; "
                          f"INST per instance incl. H-MA, TILE per 32x16 tile incl. H-WD, JOB for the whole job)", "heldout"))
    # the default (partial) triangle of E770, done right: exploratory, no prediction
    for N in (53, 56, 110):
        p, prog = loop_prog(N)
        needs.append(p)
        n = f"t-par-64x64-n{N}"
        add(n, "heldout", tcmd(64, 64, p, full=False), f"exploratory: E770 done right, the default (partial) triangle at 64x64, N = {N}", 64, 64, False)
        preds.append((n, "bit6", "none", "exploratory: no frozen prediction (the covered pixels are fewer than the target)", "heldout"))
    # R3-P8: the 4x4 loop rows (16 pixels, reaches a quad) last
    for N in C.T_EXTRA_4X4:
        p, prog = loop_prog(N)
        needs.append(p)
        n = f"t-4x4-n{N}"
        add(n, "heldout", tcmd(4, 4, p), f"R3-P8: 4x4 (16 pixels) at N = {N}: a batch smaller than 64 pixels (H-INST says set from 56)", 4, 4, True, N)
        preds.append((n, "bit6", "formula", "H-INST (set from 56 whatever the pixel count); H-TILE / H-JOB: clear (fewer pixels)", "heldout"))
    head = """Q082 pixel side, stage q-t: occupancy with the working triangle loop (decisions R3-P1, P2, P5, P8).  `probe --tri pixel --temps 32
--width W --height H --tri-full` with the relative b8 loop + MARK: the triangle covers the whole target (the tool prints
`triangle (0,0) (3W,0) (0,3H)`), so every pixel must hold MARK.  Sizes 8x8, 16x16, 32x16, 32x32, 64x32, 128x128, 256x256; ladder
N = 4, 14, 28, 53, 56, 110, 220, 440, 880, 1760, 3520 cut where pixels x N would pass 2.3e7 (E357's longest completed fill, 112 ms).
Controls: the stock pix_green full triangle at seven sizes, the loop at N = 1 at seven sizes (MARK on W x H of W x H, else void),
and the 64x32 bridge at 53 and 56 (clear, set: the fill's threshold).  The ladders are HELD OUT.  The first ladder point with the
bit set, by hypothesis (frozen table in score/r3const.py, scaled by the measured 64x32 first set / 56): H-INST per instance
(including H-MA), H-TILE per 32x16 tile (including H-WD), H-JOB for the whole job.  E770 done right (the partial default triangle
at 64x64, N = 53, 56, 110) is exploratory.  The 4x4 rows (R3-P8) are last.  Every row runs under regtimeline and STATUS2 reads."""
    return rows, preds, list(dict.fromkeys(needs)), head
