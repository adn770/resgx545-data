"""R1 geometry stages (exp-geometry-round2.md, decision R2-17 order): g-u1, g-c1 (+ g-c1f pause cells), g-t1, g-t2,
g-t7, g-u2, g-t5, g-t6.  NOT here: C2 (the pb:11 poke), C3, T3, T4 (their templates are built and mock-checked in
tests/test_templates.py but have no rows).

Every DPM job lists the base register range 0x0720-0x0724; the runner widens it to 0x0720-0x072c for the trial jobs
and, only after the gate passed, for the jobs carrying the knob s072c (run/lib_r1.sh).  Frozen predictions come from
r1models (HU1/HU2, SH + zigzag, RZ/RN): offline FITS on data measured before this file; the runs hold them out.
"""
from __future__ import annotations

import math

import numpy as np

import r1models as M
from rcommon import BINS, REPO, RT_DPM, RT_DPM_SHORT, TEMPLATES, Row, f32, probe

GREEN = "$S/p1139-green.bin"
E3T = REPO / "probes/mte/templates"
HX = lambda v: f"0x{v:08X}"
EXPECT = "stophang expectdiff"                     # every tri job: its own one-triangle reference may differ (rc 1)


def build_green() -> None:
    BINS.mkdir(exist_ok=True)
    src = (REPO / "probes/usse/templates/pix_op.s").read_text()
    p = probe.Probe(name="r1-green", question="", source="pix_op.s", params={}, inputs=["OP"],
                    cases=[["mov.skipinv.end o0, #0xFF00FF00"]], hypotheses={})
    probe._assemble(probe.render(p, p.cases[0], src), BINS / "p1139-green.bin")


def _cmd_of(p, src_dir, extra=""):
    args = probe.tool_args(p, src_dir=src_dir)
    out = []
    for i, a in enumerate(args):
        prev = args[i - 1] if i else ""
        if prev == "--dump-render":
            a = "$W/dump"
        elif prev == "--slot":
            n, f = a.split("=", 1)
            a = f"{n}=$S/{f}"
        out.append(f'"{a}"' if "$" in a else a)
    return "probe " + " ".join(out) + (" " + extra if extra else "") + f' "$S/{p.name}__0.bin"'


def _p3(name, source, slot, inputs, case, src_dir=E3T, **kw):
    d = dict(name=name, question="r1", source=source, host="tri", slot=slot, size=[64, 64], pixels=True,
             inputs=inputs, cases=[case], dump_render=True, **kw)
    p = probe._probe(d, "r1.toml")
    probe.build(p, BINS, src_dir)
    return p


def dpm_knobs(first=False, second=False):
    if first:
        return EXPECT + " trial072c:19"
    if second:
        return EXPECT + " trial072c:29"
    return EXPECT + " s072c"


# ------------------------------------------------------------------------------------------------ U1
def tri_cmd(w, h, moves, base_moved=None):
    """tri job of a K-triangle scene: kick 1 the base triangle (moved by base_moved if given), kicks 2..K moved."""
    k = 1 + len(moves)
    parts = [f"tri --width {w} --height {h} -n {k}"]
    parts += [f"--geometry {i}" for i in range(1, k)]
    if base_moved:
        parts.append(f"--move 1:{base_moved[0]},{base_moved[1]}")
    parts += [f"--move {i + 2}:{dx},{dy}" for i, (dx, dy) in enumerate(moves)]
    parts += ["--keep-going --keep-overflow --wait-ms 20000", '--dump-render "$W/dump" --dump-each',
              '--words "$W/words" --regs 0x0700-0x074c']
    return " ".join(parts)


def g_u1():
    rows, preds = [], []
    S = lambda w, h, mv: M.scene(w, h, mv)
    D = M.default_tri
    # (name, w, h, tris, set, role, cmd moves, base_moved)
    sc = [
        ("u-ctl-1", 1024, 768, [D(1024, 768)], "control", "control: 1024x768 default, U = 19 (E705/E735)", [], None),
        ("u-ctl-2a", 1024, 768, S(1024, 768, [(0, 288)]), "control", "control: two apart (0,288), U = 29 (E735)",
         [(0, 288)], None),
        ("u-m32", 1024, 768, [D(1024, 768, 32, 0)], "heldout", "moved (32,0)", [], (32, 0)),
        ("u-m0-96", 1024, 768, [D(1024, 768, 0, 96)], "heldout", "moved (0,96)", [], (0, 96)),
        ("u-m-128-96", 1024, 768, [D(1024, 768, -128, 96)], "heldout", "moved (-128,96) (E627 overflowed it at 0x30)",
         [], (-128, 96)),
        ("u-m384-288", 1024, 768, [D(1024, 768, 384, 288)], "heldout", "moved (384,288) (E627: completes at 0x30)",
         [], (384, 288)),
        ("u-2-m96", 1024, 768, S(1024, 768, [(-96, 0)]), "heldout", "two: base + (-96,0) (E627: U in 23..26)",
         [(-96, 0)], None),
        ("u-2-256-192", 1024, 768, S(1024, 768, [(256, 192)]), "heldout", "two: base + (256,192)", [(256, 192)], None),
        ("u-3-stk", 1024, 768, S(1024, 768, [(16, 0), (0, 16)]), "heldout", "three: base + (16,0) + (0,16)",
         [(16, 0), (0, 16)], None),
        ("u-4-corners", 1024, 768, [D(1024, 768, a, b) for a, b in ((0, 0), (512, 0), (0, 384), (512, 384))],
         "heldout", "four: (0,0) (512,0) (0,384) (512,384)", [(512, 0), (0, 384), (512, 384)], None),
        ("u-640", 640, 480, [D(640, 480)], "heldout", "640x480 default (a non-library size)", [], None),
        ("u-1280", 1280, 1024, [D(1280, 1024)], "heldout", "1280x1024 default (a non-library size)", [], None),
        ("u-2048", 2048, 2048, [D(2048, 2048)], "heldout", "2048x2048 default", [], None),
        ("u-2048-1536", 2048, 1536, [D(2048, 1536)], "heldout", "2048x1536 default (a non-library size)", [], None),
        ("u-512-m128", 512, 384, [D(512, 384, 128, 0)], "heldout", "512x384 moved (128,0)", [], (128, 0)),
        ("u-4096-m1024", 4096, 4096, [D(4096, 4096, 1024, 0)], "heldout", "4096x4096 moved (1024,0)", [], (1024, 0)),
        ("u-4096-2", 4096, 4096, S(4096, 4096, [(0, 1024)]), "heldout", "4096x4096 two: base + (0,1024)", [(0, 1024)],
         None),
    ]
    hu2_names = {r[0] for r in sc[:10]}               # HU2's values are frozen for the ten 1024x768 scenes
    for i, (n, w, h, tris, st, role, mv, bm) in enumerate(sc):
        u, per = M.hu1(w, h, tris)
        rows.append(Row(n, st, "safe", "0x422", dpm_knobs(first=i == 0, second=i == 1), RT_DPM_SHORT,
                        tri_cmd(w, h, mv, bm), role, n))
        preds.append((n, "knob0624_first", "0x400", "knob", st))
        # a control's U is the MEASURED value (one value, so the scorer can use it as the control); HU1 and HU2 on it are
        # the fit: label `repeat`, tallied apart from the held-out cells
        mst = "repeat" if st == "control" else st
        if st == "control":
            preds.append((n, "U", str(u), "E705/E735 (measured)", "control"))
        preds.append((n, "U", str(u), "HU1 (sgx-pipe TA model, 128 B a stream, + 1 global page)", mst))
        h2 = M.hu2(w, h, tris)
        if n in hu2_names:
            preds.append((n, "U", str(h2), "HU2 (macrotiles with streams + 8)", mst))
        preds.append((n, "kicks_open", str(len(tris) - 1), "option proof", st))
    # boundary pairs: E625's rule on HU1's U: overflow iff thr0 = P - 0x22 < U; P = U + 0x22 - 1 (overflow), U + 0x22
    for tag, w, h, mv, bm in (("b-2-m96", 1024, 768, [(-96, 0)], None), ("b-m32", 1024, 768, [], (32, 0))):
        tris = M.scene(w, h, mv) if mv else [M.default_tri(w, h, *bm)]
        u, _ = M.hu1(w, h, tris)
        for suf, P in (("lo", u + 0x22 - 1), ("hi", u + 0x22)):
            n = f"{tag}-{suf}"
            thr0 = P - 0x22
            rows.append(Row(n, "heldout", "safe", hex(P), dpm_knobs(), RT_DPM_SHORT, tri_cmd(w, h, mv, bm),
                            f"boundary of {tag.replace('b-', 'u-')}: HU1 U = {u}, P = U + 0x22{' - 1' if suf == 'lo' else ''}",
                            n))
            preds.append((n, "knob0624_first", hex(thr0), "knob", "heldout"))
            preds.append((n, "outcome", "overflow" if thr0 < u else "complete", f"E625 rule with HU1's U = {u}",
                          "heldout"))
            preds.append((n, "kicks_open", str(len(tris) - 1), "option proof", "heldout"))
    head = """U1 (geometry, Q211): the page need U of 17 scenes against HU1 = sgx-pipe's TA model as it stands (128 bytes a
stream, a page per macrotile that has streams, + 1 global page): residual 0 on all 16 measured U (a FIT).  HU2 (macrotiles
with streams + 8) is the alternative.  P = 0x422.  U is read as e2a's scorer does (peak of 0x0724 and the free-list walk,
a disagreement is cannot tell for the cell; a kick line other than 'geometry only, the scene left open' voids a K-scene
cell).  Two boundary pairs on HU1's U (E625's rule: overflow iff P - 0x22 < U): b-2-m96 at U = 24 is P = 0x39 / 0x3a (the
proposal's 0x45 / 0x46 would be U = 36's pair), b-m32 at U = 21 is P = 0x36 / 0x37.  The first two jobs are the 0x072c trial
(gate after each, see PREFLIGHT.md): u-ctl-1 (U 19), u-ctl-2a (U 29).  Non-library sizes (640x480, 1280x1024, 2048x1536)
run only because the tool's mock accepts them (tests/mock_all.py)."""
    return rows, preds, [], head


# ------------------------------------------------------------------------------------------------ C1
C1_CELLS = tuple(range(0x362, 0x380, 2))                 # 15 cells
C1_1350 = (0x366, 0x36e, 0x372, 0x376, 0x37a)


def c1_cmd(v):
    return (f'probe --tri pixel --width 4096 --height 4096 --vertices {v} '
            f'--dump-render "$W/dump" "{GREEN}"')


def g_c1():
    rows, preds = [], []

    def job(name, v, P, st, role):
        rows.append(Row(name, st, "safe", hex(P), "stophang s072c", RT_DPM, c1_cmd(v), role, name))
        preds.append((name, "knob0624_first", hex(P - 0x22), "knob", st))
        preds.append((name, "dw36", "max(0x072c count at the first abort - 2, 0)",
                      "D36 (Q273 offline: 99 of 99 unraised jobs)", st))

    job("c-1500-0x360", 1500, 0x360, "control", "control: E753 raised at P = 0x360 (thr0 0x33e -> 0x35e)")
    preds.append(("c-1500-0x360", "raise", "yes", "E753", "control"))
    job("c-1500-0x380", 1500, 0x380, "control", "control: E753 no raise at P = 0x380")
    preds.append(("c-1500-0x380", "raise", "no", "E753", "control"))
    for P in C1_CELLS:
        n = f"f-1500-{P:#x}"
        job(n, 1500, P, "heldout", f"1500 vertices at P = {P:#x}")
        preds.append((n, "raise", "monotone: raise up to one P, none from the next, exactly one flip",
                      "H-abs (E753: C in [0x35e, 0x37e); raise iff P - 2 <= C)", "heldout"))
    for P in C1_1350:
        n = f"f-1350-{P:#x}"
        job(n, 1350, P, "heldout", f"1350 vertices at P = {P:#x}")
        preds.append((n, "raise", f"same as f-1500-{P:#x}", "HP1 (one step for both scenes)", "heldout"))
    head = """C1 (geometry, Q210/Q273): the fine ladder of the raise limit at 4096x4096, 1500 vertices (and 1350 at five
cells), P = 0x360 .. 0x380.  H-abs: the raise happens iff thr0 + 0x20 = P - 2 <= C, C a constant in [0x35e, 0x37e)
(E753's controls: raise at 0x360, none at 0x380): along P the outcome flips exactly once, raise to none.  Two flips or
a no-raise to raise flip refute the monotone form.  HP1: 1350 vertices flip at the same P as 1500 (each of its five
cells equals the 1500 cell at that P).  Knob proof: the job's own 0x0624 rows (P - 0x22).  Void: a cell whose second run
does not reach thr0.  D36 (side table, never gating): dword 36 = max(0x072c's page count at the first abort - 2, 0)
in every job, raised jobs held out; scored only where 0x072c was sampled (the gate, PREFLIGHT.md).  After the ladder
the step-1 cell (g-c1f, one job, ONLY=name) fixes C exactly."""
    return rows, preds, [GREEN], head


def g_c1f():
    """The 16 candidate step-1 cells; the lead runs the one that lies between the flip's neighbours (ONLY=NAME)."""
    rows, preds = [], []
    for P in range(0x361, 0x380, 2):
        n = f"f-1500-{P:#x}"
        rows.append(Row(n, "heldout", "safe", hex(P), "stophang s072c", RT_DPM, c1_cmd(1500),
                        f"step-1 cell P = {P:#x} (run only the one between the ladder's flip neighbours)", n))
        preds.append((n, "knob0624_first", hex(P - 0x22), "knob", "heldout"))
        preds.append((n, "raise", "monotone: the outcome of the cell below or above, never a third value",
                      "H-abs (one flip)", "heldout"))
    head = """C1 pause cells: the step-1 cell between the ladder's last raise P_r and first silent P_s = P_r + 2 is P_r + 1;
this table holds all 16 candidates so that the freeze covers whichever is needed.  Run with
`run/r1.sh --cell g-c1f f-1500-0x373`.  A raise at P fixes C in [P - 2, P - 1), a silent cell C in [P - 3, P - 2)."""
    return rows, preds, [GREEN], head


# ------------------------------------------------------------------------------------------------ T1
def _blkjob(name, word, off, st, role):
    return Row(name, st, "safe", "-", "stophang", "-",
               f'probe --tri pixel --width 64 --height 64 --blk {word}={HX(f32(off))} --dump-render "$W/dump" '
               f'--pixels "{GREEN}"', role, name)


def g_t1():
    rows, preds = [], []
    P = lambda n, v, m, st: preds.append((n, "object", v, m, st))
    # (name, word, offset, HO-region, HO-band, set)
    cells = [("o-x64", 6, 64.0, "present", "present", "control"), ("o-x1000", 6, 1000.0, "none", "none", "control"),
             ("o-x87.5", 6, 87.5, "present", "present", "heldout"), ("o-x88", 6, 88.0, "none", "present", "heldout"),
             ("o-x88.5", 6, 88.5, "none", "?", "heldout"), ("o-x96", 6, 96.0, "none", "?", "heldout"),
             ("o-x104", 6, 104.0, "none", "?", "heldout"), ("o-xm24", 6, -24.0, "present", "present", "heldout"),
             ("o-xm24.5", 6, -24.5, "none", "present", "heldout"), ("o-y87.5", 8, 87.5, "present", "present", "heldout"),
             ("o-y88", 8, 88.0, "none", "present", "heldout")]
    for n, word, off, reg, band, st in cells:
        axis = "x" if word == 6 else "y"
        rows.append(_blkjob(n, word, off, st, f"viewport {axis} offset {off:g}: min {axis} = {off - 24:g}, "
                            f"max {off + 24:g} (control: E736 / E650)" if st == "control" else
                            f"viewport {axis} offset {off:g}: min {axis} = {off - 24:g}, max {off + 24:g}"))
        P(n, reg, "HO-region (E542's tile rule on target regions only, low side closed)"
          if st == "heldout" else "E736 / E650 (measured)", st)
        if st == "heldout":
            P(n, band, "HO-band (a band B > 0 beyond the edge)", st)
    head = """T1 (geometry, Q230): the off-target limit.  The viewport words 6 (x offset) and 8 (y offset) are ABSOLUTE
pixel offsets (default 32.0); the default triangle spans offset - 24 .. offset + 24.  HO-region (E542's tile rule on target
regions only, low side closed, high side open): an object iff the span reaches 0 .. 64, i.e. 87.5 present, 88.0 none,
-24.0 present, -24.5 none, y alike.  HO-band (B > 0): 88.0 present and the others up to 88 + B.  Controls: o-x64 (present,
E736) and o-x1000 (none, E650/E736); a control that fails makes the group cannot tell.  Object states: present, none,
written-unlisted (reported, never a hit).  ('?' = HO-band does not predict that cell.)"""
    return rows, preds, [GREEN], head


# ------------------------------------------------------------------------------------------------ T2
def _zrow(rows, preds, needs, name, A, B, st, role, template="vtx_zab.s", pa1=False, orders=(("+w", "-w"),),
          cond=None, copy_of=None):
    src_dir = TEMPLATES if pa1 else E3T
    if copy_of is None:
        p = _p3(name, "vtx_zab_pa1.s" if pa1 else template, "vtxuse", ["A", "B"], [HX(f32(A)), HX(f32(B))],
                src_dir=src_dir, temps=8, vtx_coords=2, slots={"pixel": "pix_green.s"})
        probe.build_helpers([p], BINS, src_dir)
        needs += [f"$S/{name}__0.bin", "$S/pix_green.bin"]
        rows.append(Row(name, st, "safe", "-", "stophang", "-", _cmd_of(p, src_dir), role, cond or name))
        binname = name
    else:                                                # the same program again: an identical job
        base = next(r for r in rows if r.name == copy_of)
        rows.append(Row(name, st, "safe", "-", "stophang", "-", base.args, role, cond or copy_of))
        binname = copy_of
    axis = "y" if pa1 else "x"
    return binname, axis


def t2_predict(preds, name, A, B, axis, st, orders):
    P = lambda q, v, m: preds.append((name, q, v, m, st))
    pr = [M.predict_zclip(A, B, axis, o) for o in orders]
    fmt = lambda xy: ";".join(f"{x:g},{y:g}" for x, y in xy)
    P("object", "present", "clip")
    P("nvert", str(pr[0]["nv"]), "HSH (Sutherland-Hodgman polygon of A->B, B->C, C->A)")
    P("xy_set", fmt(sorted(pr[0]["xy"])), "HSH (Sutherland-Hodgman polygon of A->B, B->C, C->A)")
    P("prims", ";".join(",".join(str(e) for e in t) for t in pr[0]["prims"]),
      "HPR (prim entry = stored index | 16 for a boundary edge, strip triangles)")
    for o, p in zip(orders, pr):
        suf = "" if len(orders) == 1 else f" ({o[0]} plane first)"
        P("xy_ordered", fmt(p["xy"]), "HZZ (strip zigzag of the SH polygon)" + suf)
        P("depth_words", ",".join(f"0x{f32(d):08x}" for d in p["depth"]),
          "HDP (stored depth = 0.5 + 0.5 z at every vertex, clip-made included)" + suf)


def g_t2():
    rows, preds, needs = [], [], []
    spec = [("z-flat099", 0.0, 0.99, "x", "control", "control: flat z 0.99 (E651's object, depth 0x3f7eb852)"),
            ("z-cut-p", 2.0, 1.0, "x", "control", "control (repeat of S1/S1b e3z-cut-p): z = 2x + 1"),
            ("z-cut-p05", 2.0, 0.5, "x", "heldout", "z = 2x + 0.5: cut at x = 0.25"),
            ("z-slab", 4.0, 0.0, "x", "heldout", "z = 4x: both planes cut (|x| <= 0.25), no original vertex"),
            ("z-cut-ym", 2.0, -1.0, "y", "heldout", "z = 2y - 1 (pa1 template, one changed line): cut at y = 0"),
            ("z-cut-m-slope", 4.0, -1.0, "x", "heldout", "z = 4x - 1: cut at x = 0 and x = 0.5 (B has z = 2 > w)")]
    for n, A, B, axis, st, role in spec:
        pa1 = axis == "y"
        _zrow(rows, preds, needs, n, A, B, st, role, pa1=pa1)
        if n == "z-flat099":
            preds.append((n, "object", "present", "E651 (S1 frozen)", st))
            preds.append((n, "object_equals_default_xy", "yes", "E651 (S1 frozen)", st))
            preds.append((n, "depth_words", ",".join([f"0x{f32(0.995):08x}"] * 3), "E651 (S1 frozen)", st))
            continue
        orders = (("+w", "-w"), ("-w", "+w")) if n in ("z-slab", "z-cut-m-slope") else (("+w", "-w"),)
        t2_predict(preds, n, A, B, axis, st, orders)
    _zrow(rows, preds, needs, "z-cut-p-r2", 2.0, 0.5, "replicate", "replicate of z-cut-p05 (the same program)",
          copy_of="z-cut-p05", cond="z-cut-p05")
    t2_predict(preds, "z-cut-p-r2", 2.0, 0.5, "x", "replicate", (("+w", "-w"),))
    rows = [r for r in rows if r.set == "control"] + [r for r in rows if r.set != "control"]
    needs = list(dict.fromkeys(needs))
    head = """T2 (geometry, Q230): clipped polygons, vertex SET, ORDER, prim words and depth words scored separately.  Model: a
plane runs only when a vertex crosses it (one pass rotates the polygon by one: S1/S1b cut-p's stored order is the zigzag of
ONE pass); Sutherland-Hodgman over the input edges A->B, B->C, C->A (end vertex when inside, intersection when crossing);
stored order p1 p2 p0 p3 p(n-1) p4 ...; prim entries index | 16 for a boundary edge over the strip triangles (0,1,2),
(2,1,3), (2,3,4); depth = 0.5 + 0.5 z (clip-made vertices exactly 0 or 1).  z-slab and z-cut-m-slope (both planes cut): both orders of the
two planes are frozen (either is a finding).  The proposal's z-cut-m-slope prediction (B kept) contradicts its own program: B has
z = 2 > w, so it is clipped at x = 0.5 too; the generator's SH gives the frozen 4-vertex polygon.  Controls z-flat099
and z-cut-p; a group counts only if both hold.  z-cut-ym uses vtx_zab_pa1.s (templates/, one line changed)."""
    return rows, preds, needs + [GREEN], head


# ------------------------------------------------------------------------------------------------ T7
def g_t7():
    rows, preds = [], []

    def fine(nm, unit, vs, st, role):
        v = ",".join(str(c) for c in vs)
        rows.append(Row(nm, st, "safe", "-", "stophang", "-",
                        f'probe --tri pixel --width 64 --height 64 --tri-v {v} --tri-unit {unit} '
                        f'--dump-render "$W/dump" --pixels "{GREEN}"', role, nm))
        sc = 1 << unit
        for lab, fn in (("HF-trunc", math.floor), ("HF-round", lambda x: math.floor(x + 0.5))):
            preds.append((nm, "packed_24bit", ";".join(f"{fn((c / sc + 4096) * 256):d}" for c in vs), lab, st))
            for c in vs:
                assert (c * 256 / sc) % 1 != 0.5, "no ties"

    base = [(8, 8), (56, 20), (20, 56)]
    fine("e3f-ctl", 8, [c * 256 for p in base for c in p], "control", "control: a 1/256 triangle (E651, as S1b)")
    for nm, res, offs in (("t7-a", (3, 1, 3, 3, 1, 1), (11, 37, 5, 61, 23, 7)),
                          ("t7-b", (1, 3, 3, 1, 3, 3), (29, 3, 47, 13, 19, 53)),
                          ("t7-c", (3, 3, 1, 3, 1, 3), (41, 17, 31, 9, 59, 25))):
        vs = [c * 1024 + 4 * o + r for (c, o, r) in zip([c for p in base for c in p], offs, res)]
        fine(nm, 10, vs, "heldout", f"1/1024 grid, numerator residues mod 4 {res} (no ties)")
    head = """T7 (geometry, Q230): the fine grid.  Three triangles at 1/1024 pixel (--tri-unit 10) whose step indices are 1 or 3
mod 4 (no ties): HF-round predicts the packed 1/256 value rounded to nearest, HF-trunc truncated; a residue-3 coordinate
separates them (S1 post hoc: HF-round, r2 and r3).  Control e3f-ctl (unit 8, E651's packing)."""
    return rows, preds, [GREEN], head


# ------------------------------------------------------------------------------------------------ U2
U2_U = 287
U2_K = range(2, 14)
U2_S = (0x1e, 0x1f)


def u2_count(thr0, k, s, u=U2_U):
    return 1 + (u + k - thr0) // (thr0 + s)


def g_u2():
    rows, preds = [], []
    cmd = ('tri --width 4096 --height 4096 -n 1 --keep-overflow --wait-ms 20000 --words "$W/words" '
           '--regs 0x0700-0x074c')

    def job(P, st, role):
        n = f"k-{P:#x}"
        rows.append(Row(n, st, "safe", hex(P), dpm_knobs(), RT_DPM_SHORT, cmd, role, n))
        preds.append((n, "knob0624_first", hex(P - 0x22), "knob", st))
        return n

    n = job(0xa0, "control", "control: E625's count 2 at P = 0xa0")
    preds.append((n, "nparts", "2", "E625 (measured)", "control"))
    n = job(0xb0, "control", "control: E625's count 1 at P = 0xb0")
    preds.append((n, "nparts", "1", "E625 (measured)", "control"))
    for P in range(0xa3, 0xaa):
        n = job(P, "heldout", f"k ladder cell P = {P:#x}: count 2 iff k >= {2 * (P - 0x22) - 256} (s = 0x1f), "
                f"{2 * (P - 0x22) - 257} (s = 0x1e)")
        for k in U2_K:
            for s in U2_S:
                preds.append((n, "nparts", str(u2_count(P - 0x22, k, s)), f"E625 count (k={k}, s={s:#x})", "heldout"))
    head = """U2 (geometry, Q211): the count constant k.  E625's count formula 1 + floor((U + k - thr0) / (thr0 + s)) with U = 287
(HU1 = E625's measure at 4096x4096) and the default triangle: partial renders = 2 iff k >= 2 thr0 - 256 (s = 0x1f) or
2 thr0 - 257 (s = 0x1e).  Ladder P = 0xa3 .. 0xa9 (thr0 129 .. 135: thresholds 2, 4, ... 14); controls P = 0xa0 (count 2)
and 0xb0 (count 1) from E625.  Every (k in 2..13, s in {0x1e, 0x1f}) pair is a frozen model: the scorer lists the pairs
the nine counts leave.  The first cell with count 1 fixes k to within 2, coupled to s by one.  Not in R1: the three
spacing cells at count 3 after a pause (they depend on the k found)."""
    return rows, preds, [], head


# ------------------------------------------------------------------------------------------------ T5
ORIG = [(8.0, 8.0), (56.0, 20.0), (20.0, 56.0)]


def _scaled_vs(ex, ey, unit=10):
    """tri-v integer coordinates of the default triangle scaled about the pixel corner (32, 32): bounding box ex x ey pixels."""
    sx, sy = ex / 48.0, ey / 48.0
    q = 1 << unit
    return [round(q * (32 + (x - 32) * sx)) if i % 2 == 0 else round(q * (32 + (x - 32) * sy))
            for p in ORIG for i, x in enumerate(p)]


def g_t5():
    rows, preds, needs = [], [], []
    for e in (0.3, 0.5, 0.6, 0.75, 0.9, 0.98):
        n = f"s-e{round(e * 100):03d}"
        vs = _scaled_vs(e, e)
        xs = [v / 1024 for v in vs[0::2]]
        ys = [v / 1024 for v in vs[1::2]]
        ext = max(max(xs) - min(xs), max(ys) - min(ys))
        rows.append(Row(n, "heldout", "safe", "-", "stophang", "-",
                        f'probe --tri pixel --width 64 --height 64 --tri-v {",".join(str(v) for v in vs)} '
                        f'--tri-unit 10 --dump-render "$W/dump" --pixels "{GREEN}"',
                        f"default triangle scaled to {e:g} px about the corner (32,32) (actual extent {ext:.4f})", n))
        area = 0.5 * abs((xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0]))
        preds.append((n, "extent", f"{ext:.6f}", "geometry", "heldout"))
        preds.append((n, "area", f"{area:.6f}", "geometry", "heldout"))
        preds.append((n, "object", "none" if e < 0.48 else ("present" if e > 0.96 else "monotone"),
                      "HS-ext (object iff extent >= T, T in (0.48, 0.96])", "heldout"))
        preds.append((n, "object", "none" if e < 0.48 else "monotone", "HS-area (object iff area >= A*)", "heldout"))
    vs = _scaled_vs(0.3, 0.98)
    xs = [v / 1024 for v in vs[0::2]]
    ys = [v / 1024 for v in vs[1::2]]
    area = 0.5 * abs((xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0]))
    n = "s-elong"
    rows.append(Row(n, "heldout", "safe", "-", "stophang", "-",
                    f'probe --tri pixel --width 64 --height 64 --tri-v {",".join(str(v) for v in vs)} '
                    f'--tri-unit 10 --dump-render "$W/dump" --pixels "{GREEN}"',
                    "elongated 0.3 x 0.98 px: HS-ext (extent 0.98) vs HS-area (small area)", n))
    preds.append((n, "extent", f"{max(max(xs) - min(xs), max(ys) - min(ys)):.6f}", "geometry", "heldout"))
    preds.append((n, "area", f"{area:.6f}", "geometry", "heldout"))
    preds.append((n, "object", "same as s-e098", "HS-ext (object iff extent >= T)", "heldout"))
    preds.append((n, "object", "present iff area >= A* (bracketed by the ladder)", "HS-area (object iff area >= A*)",
                  "heldout"))
    # controls: S1b's e3k-ctl (0.96-px square present) and e3k-i-c1e3 (0.48-px triangle none), re-run
    W5 = 0x3727c5ac
    p = _p3("t5-ctl-sq", "vtx_w.s", "vtxuse", ["W"], [HX(W5)], blk={14: 0x3a83126f})
    rows.append(Row("t5-ctl-sq", "control", "safe", "-", "stophang", "-", _cmd_of(p, E3T),
                    "control: S1b's e3k-ctl, w 1e-5 under clamp 1e-3, a 0.96-px square, present (E736)", "t5-ctl-sq"))
    needs.append("$S/t5-ctl-sq__0.bin")
    for q, v in (("object", "present"), ("rhw_word", "0x4479ffff"), ("xy_box", "31.5,32.5")):
        preds.append(("t5-ctl-sq", q, v, "HREP (S1b e3k-ctl measured)", "control"))
    p = _p3("t5-ctl-none", "vtx_wclip.s", "vtxuse", ["S", "A", "B"], [HX(W5), HX(0), HX(W5)], blk={14: 0x3a83126f})
    rows.append(Row("t5-ctl-none", "control", "safe", "-", "stophang", "-", _cmd_of(p, E3T),
                    "control: S1b's e3k-i-c1e3, the 0.48-px triangle, none", "t5-ctl-none"))
    needs.append("$S/t5-ctl-none__0.bin")
    preds.append(("t5-ctl-none", "object", "none", "S1b e3k-i-c1e3 (measured)", "control"))
    rows = [r for r in rows if r.set == "control"] + [r for r in rows if r.set != "control"]
    head = """T5 (geometry, Q230): the sub-pixel cull.  The default triangle scaled about the pixel corner (32,32) to a bounding box of
0.3 .. 0.98 px (no pixel centre inside: centres are 0.5 from the corner), at 1/1024 px (--tri-unit 10).  HS-ext: an object
iff the extent >= T with T in (0.48, 0.96] (so 0.3 none, 0.98 present, one flip between); HS-area: iff the area >= A*.
The elongated 0.3 x 0.98 triangle separates them (HS-ext: the outcome of the 0.98 cell; HS-area: present iff its area
0.147 exceeds the ladder's absent areas and none if below its present ones).  Controls: S1b's e3k-ctl (present) and
e3k-i-c1e3 (none), re-run; a failing control is cannot tell."""
    return rows, preds, needs + [GREEN], head


# ------------------------------------------------------------------------------------------------ T6
def g_t6():
    rows, preds, needs = [], [], []
    W5, W4 = 0x3727c5ac, bits32(1e-4)
    cells = [("c-6e5", W5, 6e-5), ("c-1p5e4", W5, 1.5e-4), ("c-2e4", W5, 2e-4),
             ("c-6e4", W4, 6e-4), ("c-7e4", W4, 7e-4), ("c-1p2e3", W4, 1.2e-3)]
    ctl = ("t6-ctl", W5, 3e-5, "control", "control: S1b's e3k-i-c3e5 (clamp 3e-5 over w 1e-5): 1/w 0x47023555")
    for tag, wb, c, st, role in [ctl] + [(f"t6-{t}", wb, c, "heldout", "") for t, wb, c in cells]:
        cb = bits32(c)
        p = _p3(tag, "vtx_wclip.s", "vtxuse", ["S", "A", "B"], [HX(wb), HX(0), HX(wb)], blk={14: cb})
        w = M.fval(wb)
        rz, rn = M.recip_words(cb)
        role = role or f"clamp {M.fval(cb):.3g} over w {w:.3g} (in band, x, y scaled by w): RZ {rz:#x}, RN {rn:#x}"
        rows.append(Row(tag, st, "safe", "-", "stophang", "-", _cmd_of(p, E3T), role, tag))
        needs.append(f"$S/{tag}__0.bin")
        s = float(np.float32(w) / np.float32(M.fval(cb)))
        pts = [(32 + (x - 32) * s, 32 + (y - 32) * s) for x, y in ORIG]
        preds.append((tag, "object", "present", "HREP (w below the clamp is replaced by it)", st))
        for lab, word in (("RZ", rz), ("RN", rn)):
            preds.append((tag, "rhw_word", f"{word:#x}", f"{lab} (1/w = {lab} of 1/clamp)", st))
        preds.append((tag, "xy_near", ";".join(f"{x:.6g},{y:.6g}" for x, y in pts),
                      "HREP-xy' (x, y divided by the clamp: shrinks by w/clamp)", st))
    head = """T6 (geometry, Q230): the clamp ladder.  vtx_wclip with x and y scaled by w (in band), block word 14 = the clamp,
chosen where RZ and RN of 1/clamp differ (6e-5 and 1.5e-4 over w 1e-5; 6e-4, 7e-4, 1.2e-3 over w 1e-4) and one cell where
they agree (2e-4 over 1e-5: a miss there is an error beyond 1 ulp).  Objects stay above T5's size (>= 2.4 px).  Frozen
per job: the RZ word, the RN word, the shrunk position x_in / clamp.  Control t6-ctl = S1b's e3k-i-c3e5 (0x47023555).
All five separating cells RZ or all RN closes the rounding clause; mixed closes it as 'within 1 ulp, not a rounding
rule' (the simulator accepts either neighbour)."""
    rows = [r for r in rows if r.set == "control"] + [r for r in rows if r.set != "control"]
    return rows, preds, needs, head


def bits32(x: float) -> int:
    return M.bits(float(np.float32(x)))
