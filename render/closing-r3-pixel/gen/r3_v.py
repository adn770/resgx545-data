# SPDX-License-Identifier: MIT
"""Stage q-v (Q082, TA side): narrowing bit 7 inside (880, 1760] and the three discriminating ladders (decision R3-P4: the whole
q-v, 88 jobs; the sweep stops only past E784's proven length).  closing3/pixel/exp-pixel-r3.md section 2.
R2-geo's g-t5v as built (vertex loop, relative branch, loop proof = the stored depth 0x3f200000 + N at every vertex), with the
body as a parameter (b8v 5 imae, b16v 13, b4v 1), `--vertices V` for the vertex-count ladders, and the regtimeline."""
from __future__ import annotations

import r3common as K
from r3common import C, LP, Row, build_bin

S2 = "stophang s2"
MASK = "0x80"


def vcmd(prog, temps=16, vertices=None, green="$S/pix_green.bin"):
    return (f'probe --temps {temps} --pixels --tri vtxuse --width 64 --height 64 --vtx-coords 2'
            + (f" --vertices {vertices}" if vertices else "") + f' --dump-render "$W/dump" --slot "pixel={green}" "{prog}"')


def v():
    rows, preds, needs = [], [], []
    green = build_bin("pix_green", (K.TEMPLATES / "pix_green.s").read_text())
    needs.append(green)
    zab = (K.REPO / "probes/mte/templates/vtx_zab.s").read_text().replace("{A}", "0x00000000").replace("{B}", "0x3E800000")
    ctl0 = build_bin("vctl0", zab)
    needs.append(ctl0)

    def loop(name, kind, n, st, role, knobs=S2, vertices=None):
        nm, text = LP.vertex_loop_source(kind, n)
        p = build_bin(nm, text)
        needs.append(p)
        rows.append(Row(name, st, K.SAFE, knobs, C.RT_REGS, vcmd(p, vertices=vertices), role))
        nv = vertices or 3
        w = C.BASE_DEPTH + n
        preds.append((name, "depth_words", ",".join([f"0x{w:08x}"] * nv),
                      f"HLOOP (the loop ran {n} times on every vertex: depth word 0x3f200000 + N)", st))
        preds.append((name, "status2_pre", "0x400", "R1-events / E784 (a debugfs reset leaves CR_EVENT_STATUS2 at 0x400)", st))
        return name

    # controls: no loop, one pass (no branch taken), three passes (E784: the first backward branch), E784's i880 / i1760
    rows.append(Row("v-ctl0", "control", K.SAFE, S2, C.RT_REGS, vcmd(ctl0, temps=8), "control: no loop (vtx_zab, z = 0.25 flat)"))
    preds += [("v-ctl0", "depth_words", ",".join([f"0x{C.BASE_DEPTH:08x}"] * 3), "E651 / E784 (z = 0.25 flat: depth word 0x3f200000)", "control"),
              ("v-ctl0", "status2_pre", "0x400", "R1-events / E784", "control"),
              ("v-ctl0", "bit7", "clear", "E784 (ctl0: STATUS2 0x400 after)", "control")]
    for n in (1, 3):
        nm = loop(f"v-n{n}", "b8v", n, "control", f"control: {n} iteration{'s' if n > 1 else ''} of the 8-instruction body "
                  f"({'no branch taken' if n == 1 else 'the first backward branch of this run'}; E784: it loops in a vertex task)")
        preds.append((nm, "bit7", "clear", "E784 (n1, n3: clear)", "control"))
    for n, bit in ((880, "clear"), (1760, "set")):
        nm = loop(f"v-i{n}", "b8v", n, "control", f"control (E784 FIT): {n} iterations of body 8 on 3 vertices ({8 * n} instructions a vertex)")
        preds.append((nm, "bit7", bit, "E784 (i880 clear, i1760 set: STATUS2 0x480)", "control"))
    # the narrowing ladder of body 8, up then down: HELD OUT, one bracket of 55
    for tag, ns in (("up", C.V_B8_UP), ("dn", list(reversed(C.V_B8_UP)))):
        for n in ns:
            nm = loop(f"v-{tag}-n{n}", "b8v", n, "heldout", f"b8v ladder {tag}, N = {n} ({8 * n} instructions a vertex): HELD OUT (narrowing)")
            preds.append((nm, "bit7", "formula", "HV-N8 (the bit sets from N8* in (880, 1760]: one bracket of 55, both orders within one step)", "heldout"))
    # the ladders that tell the hypotheses apart (formulas of N8*)
    lad = {"b16v": ("b16v", C.V_B16, None, "vb16", "13 imae, 16 instructions an iteration"),
           "b4v": ("b4v", C.V_B4, None, "vb4", "1 imae, 4 instructions an iteration"),
           "v12": ("b8v", C.V_12, 12, "v12", "body 8 on 12 vertices"),
           "v48": ("b8v", C.V_48, 48, "v48", "body 8 on 48 vertices")}
    for key, (kind, ns, nvert, grp, what) in lad.items():
        for n in ns:
            work = n * C.V_ITER_PER_BODY[kind] * (nvert or 3)               # instructions of the job's vertices together
            inside = work <= C.E784_INTACT_VERTEX_ITERS * 8                    # E784 ran 3 x 1760 x 8 intact
            if key == "b16v":
                kn = S2
            else:
                kn = S2 + f" {'watch' if inside else 'sweep'}:{grp}:{MASK}"
            nm = loop(f"v-{key}-n{n}", kind, n, "heldout", f"{key} ladder ({what}), N = {n}: HELD OUT"
                      + ("" if key == "b16v" else (" (inside E784's proven length: never skipped)" if inside else " (past E784's length: skipped once the group's bit set)")),
                      knobs=kn, vertices=nvert)
            preds.append((nm, "bit7", "formula", "HV-INSTR / HV-MA / HV-JOB / HV-TIME (formulas of N8*, tolerance one ladder step: "
                          f"see vladder-{key})", "heldout"))
    for key in lad:
        for hyp in ("HV-INSTR", "HV-MA", "HV-JOB", "HV-TIME"):
            if hyp == "HV-TIME":
                val = "B >= B(N8*) -10% (the burst's length at the narrowing ladder's bracket); t7 the same within 25% in every set job"
            else:
                f = C.v_formula(hyp, key, 1.0)
                if f is None:
                    if hyp == "HV-JOB" and key in ("b16v", "b4v"):
                        val = "by HV-INSTR or HV-MA"
                    else:
                        continue
                else:
                    val = f"N* = {f:g} x N8*"
            preds.append((f"vladder-{key}", "first_set", val, hyp, "heldout"))
    head = """Q082 TA side, stage q-v: bit 7 of CR_EVENT_STATUS2 with a looping VERTEX program (R2-geo's g-t5v; E784 measured i880 clear,
i1760 set with body 8 on 3 vertices, loop proof = the stored depth 0x3f200000 + N at every vertex).  `probe --temps 16 --pixels --tri
vtxuse --width 64 --height 64 --vtx-coords 2 [--vertices V] --dump-render ... --slot pixel=pix_green.bin LOOP`, regtimeline and STATUS2
reads.  Controls: ctl0 (no loop), n1, n3, i880, i1760.  The b8v ladder 935..1705 step 55, up then down (15 x 2), HELD OUT: one bracket
of 55 (N8*), both orders within one step.  Then b16v (13 imae, N 280..950), b4v (1 imae, 1760..9000), b8v on 12 and 48 vertices (110..1760,
28..880): frozen formulas of N8* (HV-INSTR: instructions a vertex; HV-MA: multiply-adds a vertex; HV-JOB: the job's vertices together;
HV-TIME: the burst's length).  Sweep stops (knob sweep:G:0x80) only where the work goes past E784's intact 3 x 1760 x 8 instructions:
those rows are skipped once a row of the group has set bit 7; rows inside it are `watch` rows (never skipped)."""
    return rows, preds, list(dict.fromkeys(needs)), head
