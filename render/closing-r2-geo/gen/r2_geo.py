"""R2 geometry stages (laptop session R2, decisions R2-5, R2-12, R2-14, R2-15, R2-17), order: g-t3, g-t4, g-t5v, g-c3,
g-c2 (C2, the pb:11 poke, last).  g-c3f (the proposal's 2048x1536 fallback and a 4096x3072 row set) is a table, not in the
session order.

Frozen predictions come from r2models / r1models (offline FITS on data measured before this file: R1 included); the runs
hold them out.  Helpers are r1_geo's (unchanged copy): the probe builders, the T2 z-row and its predictor.
"""
from __future__ import annotations

import r1_geo as G
import r2models as M2
from rcommon import BINS, RT_DPM2, TEMPLATES, Row, f32, probe

HX = G.HX
GREEN = G.GREEN
STOP = "stophang"
TOOL_SRC_NOTE = "the tool is ~/sgxfive-test-r1 (R1's binary, sha256 pinned in TOOL.sha256); no rebuild"


# ------------------------------------------------------------------------------------------------ T3
def _tpl_row(rows, preds, needs, name, template, inputs, case, st, role, **kw):
    """A vtxuse row of a program assembled from templates/ (z-row style command: temps 8, vtx_coords 2, green pixel)."""
    p = G._p3(name, template, "vtxuse", inputs, [HX(v) for v in case], src_dir=TEMPLATES, **kw)
    probe.build_helpers([p], BINS, TEMPLATES)
    needs += [f"$S/{name}__0.bin", "$S/pix_green.bin"]
    rows.append(Row(name, st, "safe", "-", STOP, "-", G._cmd_of(p, TEMPLATES), role, name))


def _fmt_xy_words(xy, words, sel=None):
    return ";".join(f"{x:.4f},{y:.4f}=0x{w:08x}" for (x, y), w, s in zip(xy, words, sel or [True] * len(xy)) if s)


def t3_predict(preds, name, A, B, C, D, st):
    pr = M2.predict_zwclip(A, B, C, D)
    P = lambda q, v, m: preds.append((name, q, v, m, st))
    fmt = lambda xy: ";".join(f"{x:.6f},{y:.6f}" for x, y in xy)
    P("object", "present", "clip")
    P("nvert", str(pr["nv"]), "HSH (Sutherland-Hodgman in (x, y, z, w), planes z <= w and z >= -w)")
    P("xy_set", fmt(sorted(pr["xy"])), "HSH (window = 32 + 32 x/w, made vertices at the cut)")
    P("xy_ordered", fmt(pr["xy"]), "HZZ (strip zigzag of the SH polygon)")
    P("prims", ";".join(",".join(str(e) for e in t) for t in pr["prims"]), "HPR (index | 16 for a boundary edge)")
    for lab, key, desc in (("HI-w", "rhw_w", "made 1/w = RZ of 1/w_made"),
                           ("HI-rhw", "rhw_lerp", "made 1/w = the 1/w of the ends interpolated with the edge parameter")):
        v = _fmt_xy_words(pr["xy"], pr[key])
        P("rhw_by_xy", v, f"{lab} ({desc}), exact word")
        P("rhw_by_xy", v, f"{lab} ({desc}), within 1 ulp")
    made = [m for m in pr["made"]]
    P("depth_made_by_xy", _fmt_xy_words(pr["xy"], [d or 0 for d in pr["depth_made"]], made),
      "HDP-made (z = +w / -w gives depth 1.0 / 0.0 exactly at a made vertex, whatever w)")
    return pr


def g_t3():
    rows, preds, needs = [], [], []
    # control: S1/S1b's z-cut-p (w = 1), the T2 model's own fit
    G._zrow(rows, preds, needs, "z-cut-p", 2.0, 1.0, "control", "control (repeat of S1/S1b e3z-cut-p): z = 2x + 1, w = 1")
    G.t2_predict(preds, "z-cut-p", 2.0, 1.0, "x", "control", (("+w", "-w"),))
    # (name, A, B, C, D, set, role)
    spec = [("t3-w-pos", 2.0, 1.0, 0.5, 1.25, "heldout", "z = 2x + 1, w = 0.5x + 1.25: cut at x = 1/6, made w = 4/3"),
            ("t3-w-neg", 2.0, 1.0, -0.5, 1.25, "heldout", "z = 2x + 1, w = -0.5x + 1.25: cut at x = 0.1, made w = 1.2"),
            ("t3-nocut", 0.0, 0.0, 0.5, 1.25, "heldout", "z = 0, w = 0.5x + 1.25: no clip, the perspective divide alone")]
    for n, A, B, C, D, st, role in spec:
        _tpl_row(rows, preds, needs, n, "vtx_zw.s", ["A", "B", "C", "D"], [f32(A), f32(B), f32(C), f32(D)], st, role,
                 temps=8, vtx_coords=2, slots={"pixel": "pix_green.s"})
        if n == "t3-nocut":
            pr = M2.predict_zwclip(A, B, C, D)
            fmt = lambda xy: ";".join(f"{x:.6f},{y:.6f}" for x, y in xy)
            P = lambda q, v, m: preds.append((n, q, v, m, st))
            P("object", "present", "no clip: z = 0 is inside +-w")
            P("nvert", "3", "HSH (nothing crosses)")
            P("xy_ordered", fmt(pr["xy"]), "HPD (window = 32 + 32 x/w per vertex, input order kept)")
            P("rhw_by_xy", _fmt_xy_words(pr["xy"], pr["rhw_w"]), "HI-w (original vertices: RZ of 1/w), exact word")
            P("depth_words", ",".join(["0x3f000000"] * 3), "HDP (z = 0: depth 0.5 whatever w)")
        else:
            t3_predict(preds, n, A, B, C, D, st)
    rows = [r for r in rows if r.set == "control"] + [r for r in rows if r.set != "control"]
    head = """T3 (geometry, Q230): the 1/w of clip-made vertices (vtx_zw.s: z = A x + B, w = C x + D from the vertex's own x).
Offline model (r2models.predict_zwclip): Sutherland-Hodgman in (x, y, z, w) against z <= w and z >= -w (a plane runs
only if a vertex crosses it), the strip zigzag, window = 32 + 32 x/w, a made vertex's depth exactly 1.0 / 0.0.  The made
vertex's stored 1/w by two candidates: HI-w (the reciprocal of the made w, RZ) and HI-rhw (the 1/w of the two ends
interpolated with the same edge parameter): 0.75 against 0.8205 at w = 0.5x + 1.25.  Originals: RZ of 1/w.  Frozen per
row: the vertex SET, ORDER, prim words, the 1/w words by position (exact and within one ulp: S1b saw 0x3f800001 on one
made vertex of two), the made vertices' depth words.  The originals' depth word is T4's clause (not scored here).
Controls: z-cut-p (w = 1, the T2 model); a group counts only if it holds.  t3-nocut (no clip) is held out."""
    return rows, preds, needs + [GREEN], head


# ------------------------------------------------------------------------------------------------ T4
T4_PAIRS = [("t4-m2p1-3", -2.1, 3.0), ("t4-m2p6-3", -2.6, 3.0), ("t4-m5p3-7", -5.3, 7.0),
            ("t4-m0p0027-0p003", -0.0027, 0.003), ("t4-m0p83-1p1", -0.83, 1.1), ("t4-m6p1-7", -6.1, 7.0)]


def g_t4():
    rows, preds, needs = [], [], []

    def row(n, Z, W, st, role):
        p = G._p3(n, "vtx_wzclip.s", "vtxuse", ["S", "A", "B", "Z"], [HX(G.f32(W)), HX(0), HX(G.f32(W)), HX(G.f32(Z))],
                  src_dir=TEMPLATES)
        rows.append(Row(n, st, "safe", "-", STOP, "-", G._cmd_of(p, TEMPLATES), role, n))
        needs.append(f"$S/{n}__0.bin")
        return p

    ctl = [("t4-ctl-z0-w3", 0.0, 3.0, "E754's e3i-w3: depth 0.5 (0x3f000000)", 0x3F000000),
           ("t4-ctl-zm05-w1", -0.5, 1.0, "S1/S1b cut-p's vertex A: depth 0.25 (0x3e800000)", 0x3E800000)]
    for n, Z, W, role, w in ctl:
        row(n, Z, W, "control", "control: Z = %g, W = %g, %s" % (Z, W, role))
        preds.append((n, "object", "present", "in band, no clip", "control"))
        preds.append((n, "depth_words", ",".join([f"0x{w:08x}"] * 3), "measured (every candidate gives this word)", "control"))
    for n, Z, W in T4_PAIRS:
        row(n, Z, W, "heldout", f"clip z = {Z:g}, w = {W:g}: z/w = {Z / W:.4f} in (-1, -0.5]")
        d = M2.depth_words(Z, W)
        assert len(set(d.values())) >= 3, (n, d)
        preds.append((n, "object", "present", "in band (x, y scaled by w): no clip", "heldout"))
        preds.append((n, "object_equals_default_xy", "yes", "in band", "heldout"))
        for k, desc in M2.DEPTH_CANDS:
            preds.append((n, "depth_words", ",".join([f"0x{d[k]:08x}"] * 3), f"{k} ({desc})", "heldout"))
        rzw, rnw = M2.rhw_words(W)
        preds.append((n, "rhw_word", f"0x{rzw:08x}", "RZ (1/w = RZ of 1/W: E754 in band 7 of 7)", "heldout"))
        if rnw != rzw:
            preds.append((n, "rhw_word", f"0x{rnw:08x}", "RN (1/w = RN of 1/W)", "heldout"))
    rows = [r for r in rows if r.set == "control"] + [r for r in rows if r.set != "control"]
    head = """T4 (geometry, Q230): the stored depth at w != 1 (vtx_wzclip.s: vtx_wclip plus `mov o2, #Z`; w = W constant, x and y
scaled by W so the triangle stays the default one).  z/w in (-1, -0.5] makes 0.5 + 0.5 q exact (Sterbenz) so the word is
a function of q = the stored z/w alone.  Six candidates for q (frozen words per pair, 3 to 4 distinct words a pair):
D1 RN(Z * RZ(1/W)), D2 RZ(Z/W), D3 RN(Z/W), D5 RZ(Z * RZ(1/W)), D6 RN(RN(Z + W)/(2W)) as a depth directly, D7 RN(Z *
RN(1/W)).  Controls: Z = 0, W = 3 (E754 e3i-w3) and Z = -0.5, W = 1 (cut-p's A); a group counts only if both hold.
Decision: the one candidate right in 6 of 6; none = the words are recorded and the clause narrows to one ulp."""
    return rows, preds, needs, head


# ------------------------------------------------------------------------------------------------ T5v (Q082 T5)
T5_BASE = 0x3F200000            # depth 0.5 + 0.5 z with z = 0.25 + 4 N ulp: the stored depth word is 0x3f200000 + N
T5_ITERS = (28, 53, 55, 110, 220, 440, 880, 1760, 3520, 7040)
T5_CTLN = (1, 3)


def g_t5v():
    rows, preds, needs = [], [], []
    S2 = "stophang s2"

    def loop(n, N, st, role, sweep):
        _tpl_row(rows, preds, needs, n, "vtx_loop.s", ["N", "ZB"], [N, 0x3E800000], st, role, temps=16, vtx_coords=2,
                 slots={"pixel": "pix_green.s"})
        rows[-1].knobs = S2 + (" sweep:t5v" if sweep else "")
        w = T5_BASE + N
        preds.append((n, "depth_words", ",".join([f"0x{w:08x}"] * 3),
                      f"HLOOP (the loop ran {N} times on every vertex: depth word 0x3f200000 + N)", st))
        preds.append((n, "object", "present", "HLOOP (the object is the default triangle)", st))
        preds.append((n, "object_equals_default_xy", "yes", "HLOOP", st))
        preds.append((n, "status2_pre", "0x400", "a debugfs reset leaves CR_EVENT_STATUS2 at 0x400 (R1-events: every job)", st))

    # control 0: no loop, the same depth (T2's flat z = 0.25): STATUS2 as after any job
    p = G._p3("t5v-ctl0", "vtx_zab.s", "vtxuse", ["A", "B"], [HX(f32(0.0)), HX(f32(0.25))], src_dir=G.E3T, temps=8,
              vtx_coords=2, slots={"pixel": "pix_green.s"})
    probe.build_helpers([p], BINS, G.E3T)
    needs += ["$S/t5v-ctl0__0.bin", "$S/pix_green.bin"]
    rows.append(Row("t5v-ctl0", "control", "safe", "-", S2, "-", G._cmd_of(p, G.E3T),
                    "control: no loop (vtx_zab, z = 0.25 flat): depth word 0x3f200000, STATUS2 0x400 after", "t5v-ctl0"))
    preds += [("t5v-ctl0", "depth_words", ",".join([f"0x{T5_BASE:08x}"] * 3), "E651/S1b (z = 0.25 flat: depth 0.625)", "control"),
              ("t5v-ctl0", "object", "present", "E651", "control"),
              ("t5v-ctl0", "status2_pre", "0x400", "R1-events (a reset leaves 0x400)", "control"),
              ("t5v-ctl0", "status2_bit7", "clear", "R1-events T6 (the stock vertex program: 0x400 after)", "control")]
    # controls 1, 3: the loop proof (one pass: no branch taken; three passes: two backward branches)
    for N in T5_CTLN:
        n = f"t5v-n{N}"
        loop(n, N, "control", f"control: {N} iteration{'s' if N > 1 else ''} (depth word 0x3f200000 + {N}): the knob proof"
             + (" (no branch taken)" if N == 1 else " (the first backward branch)"), False)
        preds.append((n, "status2_bit7", "clear", "R1-events T6 / E769 (far below the 55-iteration point)", "control"))
    for N in T5_ITERS:
        n = f"t5v-i{N}"
        loop(n, N, "heldout", f"{N} iterations of the 8-instruction body ({8 * N} instructions a vertex)", True)
        preds.append((n, "status2_bit7", "clear" if N <= 53 else "set",
                      "H-ITER / H-INSTR (E769: the pixel latch clear at 53, set from 55 iterations of body 8)", "heldout"))
        preds.append((n, "status2_bit7", "monotone: clear below one length, set from it", "H-TIME (~121 us a vertex instance: "
                      "the point depends on the vertex rate, not frozen)", "heldout"))
        preds.append((n, "status2_bit7", "clear", "H-NEVER (bit 7 is the TA fault latch of E357/E764, not an occupancy latch)",
                      "heldout"))
    head = """T5 (Q082): a looping vertex program through probe --tri vtxuse (templates/vtx_loop.s: 8 instructions an iteration as
E769's body 8, a RELATIVE backward branch `p1 br -#7`, the loop count carried into the vertex's depth).  Why relative:
the tool places the vtxuse program at instruction 0x40 of its page and absolute indices count from the code base (E476), so
the `ba` loops of R1-events landed elsewhere (E770: the pixel loops wrote o0 in 16 of 64 pixels).  Offline (sgx-sim):
tests/test_t5loop.py runs it at five code indices (all give the same z), and the absolute-`ba` form stops at a non-zero one.
Knob proof: every vertex's stored depth word is 0x3f200000 + N (z = 0.25 + 4N ulp, exact), so a loop that did not run N
times on EVERY vertex shows (E770's failure mode), as does a branch that fell through (word + 1).  CR_EVENT_STATUS2 (0x0118)
is read from the debugfs regs after the reset (must be 0x400) and after the job.  The sweep (knob sweep:t5v) stops at the
first length whose post-job STATUS2 has bit 7 (0x80) set: the rest are recorded as skipped.  H-ITER / H-INSTR: set from 55;
H-TIME: monotone, point by the vertex rate; H-NEVER: no length sets it.  Order: t5v-ctl0, n1, n3 (the first backward
branch, before any long loop), then the ladder.  A hang or fault stops the stage (rc 4), the debugfs reset recovers."""
    rows = [r for r in rows if r.set == "control"] + [r for r in rows if r.set != "control"]
    return rows, preds, list(dict.fromkeys(needs)) + [GREEN], head


# ------------------------------------------------------------------------------------------------ C3
def c3_cmd(w, h):
    return f'probe --tri pixel --width {w} --height {h} --vertices 1500 --dump-render "$W/dump" "{GREEN}"'


def c3_rows(w, h, cells, tag):
    """[(name, P, role, predictions)]: raise iff P - 2 <= C (0x371) under H-abs; H-target: the pair equal."""
    return [(f"{tag}-{P:#x}", P) for P in cells]


C3_2048 = (0x354, 0x372, 0x374, 0x394)                    # P* = 0x374: P* - 0x20, P* - 2, P*, P* + 0x20
# R = P - 2 = 0xa0 .. 0x160, run from the highest down (fewest partial renders first): the scene's reach at 2048 is unknown, and
# E630 saw a wide scene hang in 0x40 pages (47 to 92 partial renders), so no cell goes below thr0 = 0x80
C3_LOW = (0x162, 0x122, 0xe2, 0xa2)


def _c3_job(rows, preds, name, w, h, P, st, role):
    rows.append(Row(name, st, "safe", hex(P), "stophang", RT_DPM2, c3_cmd(w, h), role, name))
    preds.append((name, "knob0624_first", hex(P - 0x22), "knob", st))
    preds.append((name, "dw36", "no prediction (R1: dword 36 = 0x072c count - 2 holds 6 of 9 unraised, 0 of 13 raised)",
                  "D36 side table", st))


def _c3_raise_preds(preds, name, P, st, kind):
    if kind == "ctl":
        preds.append((name, "raise", "yes" if P - 2 <= M2.C_MEASURED else "no", "R1 (f-1500 ladder, measured)", st))
        return
    preds.append((name, "raise", "yes" if P - 2 <= M2.C_MEASURED else "no",
                  "H-same (C = 0x371 at every target: raise iff P - 2 <= 0x371)", st))
    if kind == "pair":
        preds.append((name, "raise", "same as the other cell of the pair (P* - 2, P*)",
                      "H-target (C moved by more than one step: the pair is on one side)", st))
    else:
        preds.append((name, "raise", "monotone: one flip along the ladder or none", "H-target (C lower at this target)", st))


def g_c3():
    rows, preds = [], []
    for P in (0x372, 0x374):
        n = f"c3-4096-{P:#x}"
        _c3_job(rows, preds, n, 4096, 4096, P, "control", f"control: R1's f-1500-{P:#x} at 4096x4096 ("
                + ("raise" if P - 2 <= M2.C_MEASURED else "none") + ")")
        _c3_raise_preds(preds, n, P, "control", "ctl")
    n = "c3-2048-cal"
    _c3_job(rows, preds, n, 2048, 2048, 0x422, "heldout", "calibration: 2048x2048 at the default P = 0x422 (the page need: no overflow expected)")
    preds.append((n, "raise", "no", "no overflow at P = 0x422 (E704's 4096 scene needs about 1300 pages; 2048 about a quarter)", "heldout"))
    for P in C3_2048:
        n = f"c3-2048-{P:#x}"
        _c3_job(rows, preds, n, 2048, 2048, P, "heldout", f"2048x2048, P = {P:#x} (thr0 {P - 0x22:#x}, raised {P - 2:#x})")
        _c3_raise_preds(preds, n, P, "heldout", "pair" if P in (0x372, 0x374) else "bracket")
    for P in C3_LOW:
        n = f"c3-2048-{P:#x}"
        _c3_job(rows, preds, n, 2048, 2048, P, "heldout", f"2048x2048 low ladder, P = {P:#x} (raised threshold {P - 2:#x})")
        _c3_raise_preds(preds, n, P, "heldout", "ladder")
    rows = [r for r in rows if r.set == "control"] + [r for r in rows if r.set != "control"]
    head = """C3 (geometry, Q210): a second target.  R1 measured C = 0x371 at 4096x4096 (raise at P = 0x373, none at 0x374: the last
raise has thr0 + 0x20 = 0x371).  P* = 0x374; the four cells P* - 2, P*, P* - 0x20, P* + 0x20 at 2048x2048 with the 4096
pair re-run as controls.  H-same: the raise outcome of each 2048 cell is that of the 4096 cell at the same P (raise iff P - 2
<= 0x371).  H-target: the (P* - 2, P*) pair is on one side of the new limit and the +-0x20 cells bracket it.  The proposal's
cells reach the first abort only if the 1500-vertex scene needs more than thr0 = 0x352 pages at 2048x2048; the scene's need
scales with the target's area (about 1300 pages at 4096x4096: E704), so they may all be NODATA (one render, no abort): the
calibration job (P = 0x422) measures the need and the low ladder (raised threshold 0xa0 .. 0x160, run from the highest down) tests a lower limit if the
second run can reach it.  A void cell = no first abort or the second run not reaching thr0.  The tool refuses more than 1500
vertices, so the scene cannot be made larger.  Knob proof: 0x0624 = P - 0x22 in the job's own rows.  The first 2048x2048
job is a context size never run: if the tool or the kernel refuses it the stage stops (rc 4)."""
    return rows, preds, [GREEN], head


def g_c3f():
    """The proposal's fallback (2048x1536) and a larger non-square target (4096x3072) at the same P*-cells: a table only."""
    rows, preds = [], []
    for (w, h) in ((2048, 1536), (4096, 3072)):
        for P in (0x372, 0x374, 0x354, 0x394):
            n = f"c3f-{w}x{h}-{P:#x}"
            _c3_job(rows, preds, n, w, h, P, "heldout", f"{w}x{h}, P = {P:#x}")
            _c3_raise_preds(preds, n, P, "heldout", "pair" if P in (0x372, 0x374) else "bracket")
    head = """C3 fallback cells (not in the session): the proposal's 2048x1536 (its stated fallback when the 2048x2048 second run does not
reach thr0) and 4096x3072 (three quarters of the area, so closer to a scene that reaches).  Same predictions as g-c3.
Run with `run/r2.sh --cell g-c3f JOB` or `--only g-c3f`."""
    return rows, preds, [GREEN], head


# ------------------------------------------------------------------------------------------------ C2
C2_V = (0x300, 0x33e, 0x351, 0x352, 0x35e, 0x3a0, 0x3de)
C2_KNOBS = "stophang expectdiff kpoke wd:75"


def g_c2():
    rows, preds = [], []
    tri = ('tri --width 4096 --height 4096 -n 1 --keep-overflow --wait-ms 20000 --words "$W/words" --regs 0x0700-0x074c '
           '--kpoke-render 1:pb:11=0x{:x}')
    for V, want, role in ((0x80, "yes", "control (E625): 4096x4096 default triangle, poke 0x80: raise, dword 35 0x9e"),
                          (0x100, "no", "control (E625): poke 0x100: none, dword 35 0xfe")):
        n = f"k-tri-{V:#x}"
        rows.append(Row(n, "control", "risky", "0x422", C2_KNOBS, RT_DPM2, tri.format(V), role, n))
        preds.append((n, "first_status", hex(V), "knob (the poked threshold is the first abort's status)", "control"))
        preds.append((n, "raise", want, "E625 (measured; 2 thr0 < U + k)", "control"))
    for V in C2_V:
        n = f"k-1500-{V:#x}"
        rows.append(Row(n, "heldout", "risky", "0x422", C2_KNOBS, RT_DPM2,
                        f'probe --tri pixel --width 4096 --height 4096 --vertices 1500 --kpoke pb:11=0x{V:x} '
                        f'--dump-render "$W/dump" "{GREEN}"', f"1500 vertices, poke pb:11 = {V:#x} (raised threshold {V + 0x20:#x})",
                        n))
        preds.append((n, "first_status", hex(V), "knob (the poked threshold is the first abort's status)", "heldout"))
        preds.append((n, "raise", "yes" if V + 0x20 <= M2.C_MEASURED else "no",
                      "H-abs (the limit C = 0x371 compares with the threshold the TA runs: raise iff V + 0x20 <= 0x371)",
                      "heldout"))
        preds.append((n, "raise", "no", "H-P (the limit is on the knob's P, 0x373: P = 0x422 never raises)", "heldout"))
        preds.append((n, "raise", "yes", "H-rel (the limit follows P: P = 0x422 raises every V up to 0x3de)", "heldout"))
    rows = [r for r in rows if r.set == "control"] + [r for r in rows if r.set != "control"]
    head = """C2 (geometry, Q210): decouple the threshold from P by the descriptor poke pb:11 = V (debugfs kpoke, user decision R2-12, E625's
`--kpoke-render 1:pb:11=V` ran 5 jobs without incident), P = 0x422 throughout, LAST in its session.  The kernel applies the poke once
to the next render it kicks and drops it; a debugfs reset (before every job) clears anything still armed.  R1 fixed the limit at
C = 0x371 for the threshold set through the knob: raise iff thr0 + 0x20 <= 0x371.  H-abs: the same comparison holds for a poked
threshold (V <= 0x351 raises: 0x351 and 0x352 bracket the limit exactly); H-P: the raise is tied to the knob's P (0x373), so no
poke raises at P = 0x422 (E625's 0x80 raise on the one-triangle scene is evidence against it); H-rel: the limit follows P (raise at
every V).  Knob proof per job: the first abort's status (0x0658 stretch start) is V; 0x0624's own reading is recorded.  A hung or
faulted job stops the stage; the runner's watchdog (wd:75) writes the kernel's own debugfs reset 75 s after the tool started and
the stage ends with a reset and a health triangle."""
    return rows, preds, [GREEN], head
