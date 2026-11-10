# SPDX-License-Identifier: MIT
"""Stages q-f0 and q-f1 (Q082, pixel side, fills): the loop controls and the what-does-the-latch-count ladders.
closing3/pixel/exp-pixel-r3.md sections 1.1 and 1.2; decisions R3-P1 (relative branch + MARK, no tool change) and R3-P3 (two
opposite orders: 108 jobs)."""
from __future__ import annotations

import r3common as K
from r3common import C, LP, Row, build_bin, mark_hex

S2 = "stophang s2"
FILL_ROWS = 2048


def fill_cmd(kind, n, form="rel"):
    name, text, info = LP.pixel_loop_source(kind, n, form)
    path = build_bin(name, text)
    return f'probe "{path}"', name


def common_preds(preds, row, n, kind, form, st):
    preds.append((row, "status2_pre", "0x400", "R1-events / E784 (a debugfs reset leaves CR_EVENT_STATUS2 at 0x400)", st))
    if form == "rel":
        preds.append((row, "proof", f"{mark_hex(n)} {FILL_ROWS}", "the MARK loop proof: o0 = MARK on 2048 of 2048", st))
    else:
        preds.append((row, "proof", f"0x00000000 {FILL_ROWS}", "E431 (the abs loop in a fill: o0 = 0 on 2048 of 2048)", st))


def f0():
    rows, preds, needs = [], [], []
    spec = [("rel", 53, "clear"), ("rel", 56, "set"), ("rel", 53, "clear"), ("rel", 56, "set"),
            ("abs", 53, "clear"), ("abs", 56, "set"), ("abs", 53, "clear"), ("abs", 56, "set"),
            ("rel", 16, "clear"), ("rel", 136, "set")]
    seen = {}
    for form, n, bit in spec:
        seen[(form, n)] = seen.get((form, n), 0) + 1
        suffix = "b" if seen[(form, n)] == 2 else ""
        name = f"f0-{form}-b8-{n}{suffix}"
        cmd, prog = fill_cmd("b8", n, form)
        needs.append(f"$S/{prog}.bin")
        knobs = S2 + (f" proofstop:{mark_hex(n)}:{FILL_ROWS}" if form == "rel" else "")
        role = {"rel": "the relative `br` loop + MARK (the bridge; the first control: a backward branch in a PIXEL task is "
                       "unproven on hardware)", "abs": "E431's absolute `ba` loop (a fill: o0 = 0)"}[form]
        rows.append(Row(name, "control", K.SAFE, knobs, C.RT_REGS, cmd, f"{role}: N = {n}"))
        common_preds(preds, name, n, "b8", form, "control")
        model = "E431 / E769 T0 (53 clear, 56 set)" if n in (53, 56) else "E431 timelines (60.2 + 9.02 N us)"
        preds.append((name, "bit6", bit, model, "control"))
        if n == 16:
            preds.append((name, "B_us", f"{C.B0 + C.B1 * 16:.0f}+-125", "E431 burst fit 60.2 + 9.02 N, 3 sigma", "control"))
        if n == 136:
            preds.append((name, "B_us", f"{C.B0 + C.B1 * 136:.0f}+-125", "E431 burst fit 60.2 + 9.02 N, 3 sigma", "control"))
            preds.append((name, "t6_us", f"{C.T6_LO:.0f}..{C.T6_HI:.0f}", "E431 / E357: bit 6 shows 124..329 us after the burst starts (32 of 32)", "control"))
    preds.append(("f0-agree", "abs_rel_same_bit", "yes", "E431 (the same program body: the branch form cannot move the bit)", "control"))
    head = """Q082 pixel side, stage q-f0: the loop controls on FILLS (10 jobs).  The first control is the relative backward `br` in a
pixel task (decision R3-P1): relative loop + MARK proof (prologue mov r30 = 0xC0DE0000 | N, last instruction xor.end o0, r1, r30),
so o0 = MARK on 2048 of 2048 only where the counter reached zero (E770's unwritten register cannot pass).  A fill's shader
sits at index 0 of the code base, so E431's absolute `ba` loop works in a fill (o0 = 0, E431/E769) and is kept here as the abs
control: never in a --tri slot (the generator and the guard refuse).  Rows: rel 53, 56, 53, 56 (proofstop: a failed proof stops
the stage with rc 17 and ends the pixel loop stages cleanly), abs 53, 56, 53, 56, rel 16 (clear, burst 204 +- 125 us), rel 136
(set, t6 120..340 us after the burst starts).  STATUS2 is read after the reset (must be 0x400) and after the job; every row
runs under regtimeline 0x0008 (clock-gate status, the burst), 0x0118 (STATUS2), 0x012c.  If abs and rel disagree on the bit
the session stops (driver exit 41): the fill ladders would have to run with both."""
    return rows, preds, list(dict.fromkeys(needs)), head


def ladder_names(order):
    """Job names of one order: ladders in the table order b16 b12 b4 b2 b8n ld8, N ascending (order a) or the exact reverse
    of the whole list (order b)."""
    seq = [(kind, n) for kind, ns in C.F_LADDERS.items() for n in ns]
    return seq if order == "a" else list(reversed(seq))


def f1(order):
    rows, preds, needs = [], [], []
    pfx = "fa" if order == "a" else "fb"
    for kind, n in ladder_names(order):
        name = f"{pfx}-{kind}-n{n}"
        cmd, prog = fill_cmd(kind, n)
        needs.append(f"$S/{prog}.bin")
        fit = n in C.F_LADDERS[kind][:2]
        st = "control" if fit else "heldout"
        role = (f"ladder {kind} (body {C.INSTR_PER_ITER[kind]} instructions, {C.IMAE_PER_ITER[kind]} multiply-adds), N = {n}"
                + (": one of the ladder's two short FIT points (the slope of its burst)" if fit else ": HELD OUT"))
        rows.append(Row(name, st, K.SAFE, S2, C.RT_REGS, cmd, role))
        common_preds(preds, name, n, kind, "rel", st)
        preds.append((name, "bit6", C.pred_ma(kind, n),
                      f"H-MA (multiply-adds of an instance >= M*, M* in ({C.M_LO}, {C.M_HI}]; {C.ma_count(kind, n)} here)", st))
        preds.append((name, "bit6", "formula", "H-WD (a tile's time (B - 60.2) / 4 >= T* = 121.8 us: N* = 4 T* / s_body +- max(8%, 2 sigma) "
                      "from the ladder's two short points; ld8: the job's own B)", st))
        preds.append((name, "bit6", "formula", "H-WD-busy (as H-WD, time waiting on a load not counted: ld8 first set later than H-WD's)", st))
        preds.append((name, "bit6", "formula", f"H-BURST (the job's burst B >= {C.BURST_STAR:.0f} +- {C.BURST_TOL:.0f} us)", st))
        iw = n * C.INSTR_PER_ITER[kind]
        preds.append((name, "bit6", "clear" if n <= 53 else "set" if n >= 55 else C.EITHER,
                      "H-ITER (54 to 55 iterations whatever the body; E769 refuted it: printed without weight)", "repeat"))
        preds.append((name, "bit6", "clear" if iw <= 424 else "set" if iw >= 440 else C.EITHER,
                      "H-INSTR (about 440 instructions an instance; E769 refuted it: printed without weight)", "repeat"))
        preds.append((name, "t6_us", f"{C.T6_LO:.0f}..{C.T6_HI:.0f}",
                      "H-EARLY (H-WD, H-MA: the latch 120..340 us after the burst starts, not growing with N; jobs set at N >= 1.3 N*)", st))
        preds.append((name, "t6_us", f"within {int(C.T6_END_FRAC * 100)}% of B", "H-END (the latch at the end of the burst)", st))
    head = f"""Q082 pixel side, stage q-f1{order}: what the latch counts (fills, 54 jobs; order {order}: {'ascending in the table order b16 b12 b4 b2 b8n ld8' if order == 'a' else 'the exact reverse of order a'}).  Relative `br` loops with MARK
(decision R3-P1), STATUS2 read after the reset (0x400) and after the job, regtimeline 0x0008 / 0x0118 / 0x012c.  Ladders: b16 (14 imae,
N 6..104), b12 (10 imae, 8..136), b4 (2 imae, 40..640), b2 (no imae, 500..16000), b8n (6 `or`, 60..3840), ld8 (ldad, wdf, 4 imae,
20..320).  The first two points of a ladder are its FIT rows (the burst slope s_body); every other point is HELD OUT.  Hypotheses
(frozen in score/r3const.py): H-MA (multiply-adds of an instance >= M*, M* in (318, 336]), H-WD (a tile's time (B - 60.2) / 4 >=
121.8 us), H-WD-busy, H-BURST (B >= 536 +- 20 us); H-ITER and H-INSTR are E769's refuted rows, printed without weight.  A hypothesis is
refuted by one ladder whose two orders agree and contradict it; the orders disagreeing at one N marks that N `edge`."""
    return rows, preds, list(dict.fromkeys(needs)), head
