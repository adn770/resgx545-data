# SPDX-License-Identifier: MIT
"""Stage q4-v (Q082, TA side): bit 7 held out against the TA-clock rule (28 jobs; plan section 3.1, decisions R4-9 a and the user's
bit-7 scope a: q4-v as written, the 1500-vertex rows included).

The rule (round 4's offline reading, E807's corrections, hw_spec EVENT_STATUS2: SEMI on E807's 74 jobs): with L the longest run of
regtimeline samples with CR_CLKGATESTATUS (0x0008) == 0x000ccff8 (the TA's clocks while it works on the vertices), bit 7 of STATUS2 is
set after the job iff L >= 129.5 us (clear below 122 us, set above 136 us, the edge between is not scored), and it shows 118 to 138 us
after that run began.  [infer] the latch means: the TA made no progress for about 125 to 130 us.  Rows: controls v-ctl0, v-n1, v-i880,
v-i1760 (the bridge to E807 on the rgn4 module: 0x400 / clear / clear with L 95 to 112 / set); three ladders of bodies and vertex
counts E807 never ran, b12v (10 multiply-adds, 13 instructions an iteration, 3 vertices), b2v (counter and branch only, 2
instructions, 3 vertices) and b8v on 24 vertices, each two FIT points (clear by the model, run first) and five HELD OUT points at
0.80, 0.92, 1.08, 1.20 and 1.60 x N* (N* from the frozen offline model of L, score/r4const.py); and the stock program with 1500
vertices at 2048x2048 (twice) and 4096x4096: H-STALL (no progress is what latches: clear, as the ten 1500-vertex jobs of R3-geo's
g-c4) against H-PHASE (the TA phase's length latches: set); a job whose L is below 125 us is void for that.  Every job runs under
regtimeline 0x0008, 0x0118, 0x012c and reads STATUS2 after the reset (0x400 else the stage stops) and after the job.  The loop
proof of a vertex loop is the stored depth word 0x3f200000 + N at every decoded vertex.  A bridge control that reads otherwise
stops the session (runner knob want2).
"""
from __future__ import annotations

import r4common as K
from r4common import C, LP, Row, build_bin

S2 = "stophang s2"
STOCK = "p1139-green"
LAT = f"{118}..{138}"


def vcmd(prog, temps=16, vertices=None):
    return (f'probe --temps {temps} --pixels --tri vtxuse --width 64 --height 64 --vtx-coords 2'
            + (f" --vertices {vertices}" if vertices else "") + f' --dump-render "$W/dump" --slot "pixel=$S/pix_green.bin" "{prog}"')


def build_stock():
    """The stock green pixel program of R3-geo's g-c4 (R1's build_green: pix_op.s with `mov.skipinv.end o0, #0xFF00FF00`)."""
    from r4common import probe
    p = probe.Probe(name="r1-green", question="", source="pix_op.s", params={}, inputs=["OP"],
                    cases=[["mov.skipinv.end o0, #0xFF00FF00"]], hypotheses={})
    src = (K.REPO / "probes/usse/templates/pix_op.s").read_text()
    return build_bin(STOCK, probe.render(p, p.cases[0], src))


def build():
    rows, preds, needs = [], [], []
    P = lambda *a: preds.append(a)
    green = build_bin("pix_green", (K.TEMPLATES / "pix_green.s").read_text())
    needs.append(green)
    zab = (K.REPO / "probes/mte/templates/vtx_zab.s").read_text().replace("{A}", "0x00000000").replace("{B}", "0x3E800000")
    ctl0 = build_bin("vctl0", zab)
    needs.append(ctl0)
    stock = build_stock()
    needs.append(stock)

    def loop(name, kind, n, st, role, knobs=S2, vertices=None):
        nm, text = LP.vertex_loop_source(kind, n)
        p = build_bin(nm, text)
        needs.append(p)
        rows.append(Row(name, st, K.SAFE, knobs, C.RT_REGS, vcmd(p, vertices=vertices), role))
        nv = vertices or 3
        P(name, "status2_pre", "0x400", "R1-events / E784 (a debugfs reset leaves CR_EVENT_STATUS2 at 0x400)", st)
        P(name, "depth_words", ",".join([f"0x{C.BASE_DEPTH + n:08x}"] * nv),
          f"HLOOP (the loop ran {n} times on every vertex: depth word 0x3f200000 + N)", st)
        P(name, "bit6", "clear", "E807 (a vertex loop sets bit 7 only: STATUS2 0x480 at i1760)", st)
        return name

    def bit7_rows(name, kind, nvert, n, st):
        Lm = C.v_model_L(kind, nvert, n)
        P(name, "bit7", "rule", "TA-125 (bit 7 set iff L >= 129.5 us, L the longest run of 0x0008 == 0x000ccff8; clear below 122, set above "
          "136 us, the edge between is not scored)", st)
        P(name, "t7_after_run_us", LAT, "TA-125 (bit 7 shows 118 to 138 us after the run began, in every set job)", st)
        P(name, "L_model_us", f"{Lm:.0f}", f"layout check only (the frozen offline model of L, N = {n}; not a hypothesis)", st)

    # ------------------------------------------------------------ controls: the bridge to E807 on the rgn4 module
    rows.append(Row("v-ctl0", "control", K.SAFE, S2 + " want2:0xc0:0x00", C.RT_REGS, vcmd(ctl0, temps=8), "control: no loop (vtx_zab, z = 0.25 flat)"))
    P("v-ctl0", "depth_words", ",".join([f"0x{C.BASE_DEPTH:08x}"] * 3), "E651 / E784 (z = 0.25 flat: depth word 0x3f200000)", "control")
    P("v-ctl0", "status2_pre", "0x400", "R1-events / E784", "control")
    P("v-ctl0", "bit7", "clear", "E784 / E807 (ctl0: STATUS2 0x400 after)", "control")
    P("v-ctl0", "L_us", "0", "E807 (no vertex loop: no run of 0x000ccff8)", "control")
    loop("v-n1", "b8v", 1, "control", "control: one iteration of the 8-instruction body (no branch taken), L about 5 us (E807)",
         knobs=S2 + " want2:0xc0:0x00")
    P("v-n1", "bit7", "clear", "E784 / E807 (n1: clear)", "control")
    P("v-n1", "L_us", "0..30", "E807 (v-n1 L 4.7 us)", "control")
    loop("v-i880", "b8v", 880, "control", "control (bridge to E807, E784): 880 iterations of body 8 on 3 vertices", knobs=S2 + " want2:0xc0:0x00")
    P("v-i880", "bit7", "clear", "E784 / E807 (i880 clear)", "control")
    P("v-i880", "L_us", "95..112", "E807 (v-i880 L 103.3 us; the model's 106)", "control")
    loop("v-i1760", "b8v", 1760, "control", "control (bridge to E807, E784): 1760 iterations of body 8 on 3 vertices", knobs=S2 + " want2:0x80:0x80")
    P("v-i1760", "bit7", "set", "E784 / E807 (i1760 set: STATUS2 0x480)", "control")
    P("v-i1760", "L_us", "160..260", "E807 (v-i1760 L 206.9 us; the model's 209)", "control")
    # ------------------------------------------------------------ the three ladders (HELD OUT; the FIT points are controls)
    lad = [("b12v", "b12v", 3, None, "vb12", "10 imae, 13 instructions an iteration, 3 vertices (a body between E807's b8v and b16v)"),
           ("b2v", "b2v", 3, None, "vb2", "counter and branch only, 2 instructions an iteration, 3 vertices (below E807's b4v, set already at 1760)"),
           ("v24", "b8v", 24, 24, "v24", "body 8 on 24 vertices (between E807's 12 and 48 vertices)")]
    for key, kind, nvert, vertices, grp, what in lad:
        fit, held = C.v_points(kind, nvert)
        for n in fit:
            name = f"v-{key}-n{n}"
            loop(name, kind, n, "control", f"{key} ladder ({what}), N = {n}: a FIT point (clear by the model, run first)", vertices=vertices)
            bit7_rows(name, kind, nvert, n, "control")
        for n in held:
            name = f"v-{key}-n{n}"
            loop(name, kind, n, "heldout", f"{key} ladder ({what}), N = {n}: HELD OUT ({n / C.v_nstar(kind, nvert):.2f} x N*)", vertices=vertices)
            bit7_rows(name, kind, nvert, n, "heldout")
        P(f"@ladder-{key}", "nstar_model", f"{C.v_nstar(kind, nvert):.0f}",
          f"layout check only (N* = (129.5 - a) / s of the frozen offline model; points at {C.V_RATIOS} x N*, FIT at {C.V_FIT_RATIOS})", "heldout")
    # ------------------------------------------------------------ the stock program, 1500 vertices (H-STALL against H-PHASE)
    for name, size in (("v-stock-2048-a", 2048), ("v-stock-2048-b", 2048), ("v-stock-4096", 4096)):
        rows.append(Row(name, "heldout", K.SAFE, S2, C.RT_REGS,
                        f'probe --tri pixel --width {size} --height {size} --vertices 1500 --dump-render "$W/dump" "{stock}"',
                        f"the stock program, 1500 vertices at {size}x{size}, default pages (g-c4's command and its p1139-green program)"))
        P(name, "status2_pre", "0x400", "R1-events / E784 (a debugfs reset leaves CR_EVENT_STATUS2 at 0x400)", "heldout")
        P(name, "bit7", "clear", "H-STALL (no progress latches: the stock vertex program makes progress through milliseconds of TA, as the ten "
          "1500-vertex jobs of R3-geo g-c4, STATUS2 0x400)", "heldout")
        P(name, "bit7", "set", "H-PHASE (the TA phase's length latches)", "heldout")
        P(name, "L_us", "record", "recorded; the row is void for H-STALL / H-PHASE if L is below 125 us", "heldout")
    head = __doc__
    return rows, preds, list(dict.fromkeys(needs)), head
