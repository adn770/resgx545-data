"""S1 geometry: E8b (translucent order) and E3 (clip, w and off-target objects)."""
from __future__ import annotations

import math
import struct

from s1common import BINS, REPO, Row, f32, probe

TE = REPO / "probes"
E3_TEMPLATES = TE / "mte/templates"


def build_red() -> None:
    src = (TE / "usse/templates/pix_op.s").read_text()
    p = probe.Probe(name="s1-red", question="", source="pix_op.s", params={}, inputs=["OP"],
                    cases=[["mov.skipinv.end o0, #0xFFFF0000"]], hypotheses={})
    probe._assemble(probe.render(p, p.cases[0], src), BINS / "pix-red.bin")


def e8b():
    """Blend order (E8 b): two objects, the second a copy with its own colour and depth."""
    rows, preds = [], []
    cmd = ('probe --tri pixel --vertices 6 --obj2 3 --obj2-pixel "$S/pix-red.bin" '
           '--blk 1={i1} --obj2-blk 1={i2} --obj2-blk 10={z2} --dump-render "$W/dump" --pixels '
           '"$S/p1139-green.bin"')
    OPQ, TRL = "0x00400200", "0x02400200"          # less + depth write; pass type 1 (bits 27:25)
    NEAR, FAR = "0x3e800000", "0x3f400000"        # obj2 z offset 0.25 / 0.75 (obj1 at 0.5)
    cases = [("t-opq-near", OPQ, OPQ, NEAR, "control", "both opaque, second nearer: red expected"),
             ("t-opq-far", OPQ, OPQ, FAR, "control", "both opaque, second farther: green expected"),
             ("t-2-near", OPQ, TRL, NEAR, "heldout", "translucent second, nearer"),
             ("t-2-far", OPQ, TRL, FAR, "heldout", "translucent second, farther"),
             ("t-1-near", TRL, OPQ, NEAR, "heldout", "translucent first, second nearer"),
             ("t-1-far", TRL, OPQ, FAR, "heldout", "translucent first, second farther")]
    win = {  # winner of the overlap: HL list order, HD depth order (also the opaque rule), HP pass order
        "t-opq-near": ("red", "red", "red"), "t-opq-far": ("green", "green", "green"),
        "t-2-near": ("red", "red", "red"), "t-2-far": ("red", "green", "green"),
        "t-1-near": ("red", "red", "red"), "t-1-far": ("red", "green", "green")}
    for nm, i1, i2, z2, st, role in cases:
        rows.append(Row(nm, st, "safe", "-", "stophang", "-", cmd.format(i1=i1, i2=i2, z2=z2), role, nm))
        for m, v in zip(("HL-list-order", "HD-depth-order", "HP-pass-order"), win[nm]):
            preds.append((nm, "overlap_winner", v, m, st))
    head = """E8b (geometry): translucent order, 6 jobs (the proposal's 14 = 8 + 6 jobs; 'on both' dropped).
Object 1 green at depth 0.5 (the default z offset), object 2 red (--obj2-pixel) as the copy from
vertex 3 (--obj2 3), its state block word 10 (viewport z offset) 0.25 = nearer or 0.75 = farther
(the proposal's --copy-depth would only ever make the copy farther).  ISP word 0 (block word 1,
read from the library's tri_block): less + depth write 0x00400200; translucent = pass type 1
(bits 27:25) 0x02400200.  Both-opaque controls first: they must show the nearer object's colour.
Hypotheses: HL second object wins whatever the depth, HD nearer wins, HP translucent after opaque."""
    return rows, preds, ["$S/p1139-green.bin", "$S/pix-red.bin"], head


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


def _p3(name, source, slot, inputs, case, **kw):
    d = dict(name=name, question="s1 e3", source=source, host="tri", slot=slot, size=[64, 64], pixels=True,
             inputs=inputs, cases=[case], dump_render=True, **kw)
    p = probe._probe(d, "s1-e3.toml")
    probe.build(p, BINS, E3_TEMPLATES)
    return p


def _hx(v):
    return f"0x{v:08X}"


def _rz32(x: float) -> int:
    b = struct.unpack('<I', struct.pack('<f', x))[0]
    return b if struct.unpack('<f', struct.pack('<I', b))[0] <= x else b - 1


def e3():
    rows, preds = [], []
    needs = ["$S/p1139-green.bin"]

    def add(p, st, role, cond=None, extra="", knobs="stophang"):
        rows.append(Row(p.name, st, "safe", "-", knobs, "-", _cmd_of(p, E3_TEMPLATES, extra), role, cond or p.name))
        needs.append(f"$S/{p.name}__0.bin")

    def P(nm, q, v, m, st):
        preds.append((nm, q, v, m, st))

    # (a) w scan, dumped
    for nm, w, st, cond in (("e3w-w1", 0x3f800000, "control", None), ("e3w-w2", 0x40000000, "heldout", "e3w-w2"),
                            ("e3w-w2-r2", 0x40000000, "replicate", "e3w-w2"), ("e3w-w05", 0x3f000000, "heldout", None),
                            ("e3w-w1e3", 0x3a83126f, "heldout", None), ("e3w-w1e5", 0x3727c5ac, "heldout", None)):
        p = _p3(nm, "vtx_w.s", "vtxuse", ["W"], [_hx(w)])
        wf = struct.unpack('<f', struct.pack('<I', w))[0]
        add(p, st, f"w scan dumped: every vertex w = {wf:g}", cond)
        P(nm, "rhw_word", hex(_rz32(1 / wf)), "RZ32(1/w) [fit: mte/rhw, 9 vertices]", st)
        P(nm, "rhw_word", hex(struct.unpack('<I', struct.pack('<f', 1 / wf))[0]), "RN32(1/w)", st)
        if w == 0x3f800000:
            P(nm, "object_equals_default", "yes", "E651", "control")
        if wf in (2.0, 0.5):
            s = 1 / wf
            vv = [(32 + (a - 32) * s, 32 + (b - 32) * s) for a, b in ((8, 8), (56, 20), (20, 56))]
            P(nm, "xy_pixels", ";".join(f"{x:g},{y:g}" for x, y in vv), "HW-exact", st)
    # (b) z clip
    for nm, a, b, st, cond, role in (
            ("e3z-flat099", 0, f32(0.99), "control", None, "control: flat z 0.99 inside the volume"),
            ("e3z-flat101", 0, 0x3F8147AE, "heldout", None, "flat z 1.01: removed (E287 image)"),
            ("e3z-flatm101", 0, 0xBF8147AE, "heldout", None, "flat z -1.01: removed"),
            ("e3z-cut-p", 0x40000000, 0x3F800000, "heldout", "e3z-cut-p", "z = 2x + 1: cut where z = +w"),
            ("e3z-cut-p-r2", 0x40000000, 0x3F800000, "replicate", "e3z-cut-p", "replicate"),
            ("e3z-cut-m", 0x40000000, 0xBF800000, "heldout", "e3z-cut-m", "z = 2x - 1: cut where z = -w"),
            ("e3z-cut-m-r2", 0x40000000, 0xBF800000, "replicate", "e3z-cut-m", "replicate")):
        p = _p3(nm, "vtx_zab.s", "vtxuse", ["A", "B"], [_hx(a), _hx(b)], temps=8, vtx_coords=2,
                slots={"pixel": "pix_green.s"})
        probe.build_helpers([p], BINS, E3_TEMPLATES)
        add(p, st, role, cond)
        needs.append("$S/pix_green.bin")
        if "flat1" in nm or "flatm" in nm:
            P(nm, "object", "none", "HR-none", st)
            P(nm, "object", "written-unlisted", "HR-obj", st)
        elif "cut" in nm:
            P(nm, "nvert", ">=4", "HC-poly", st)
            P(nm, "nvert", "3", "HC-orig", st)
        else:
            P(nm, "object_equals_default", "yes", "E651", "control")
    # (c) wclip
    wc = {"e3c-w1": ([0x3f800000, 0, 0x3f800000], "control", "control: no clipping (w 1)"),
          "e3c-w01": ([0x3f800000, 0xbf99999a, 0x3f800000], "heldout", "second vertex w 0.1"),
          "e3c-w0": ([0x3f800000, 0xbfaaaaab, 0x3f800000], "heldout", "second vertex w 0"),
          "e3c-wm005": ([0x3f800000, 0xbfb33333, 0x3f800000], "heldout", "second vertex w -0.05"),
          "e3c-wm05": ([0x3f800000, 0xc0000000, 0x3f800000], "heldout", "second vertex w -0.5")}
    for nm, (c, st, role) in wc.items():
        p = _p3(nm, "vtx_wclip.s", "vtxuse", ["S", "A", "B"], [_hx(x) for x in c])
        add(p, st, role)
        if st == "control":
            P(nm, "object_equals_default", "yes", "E651", "control")
        else:
            P(nm, "nvert", ">=4", "HC-poly", st)
            P(nm, "nvert", "3", "HC-orig", st)
    # (d) off target: viewport x offset (state block word 6, E061), absolute pixels
    for nm, off, st, cond in (("e3o-x8", 8, "heldout", None), ("e3o-x64", 64, "heldout", None),
                              ("e3o-x128", 128, "heldout", "e3o-x128"), ("e3o-x128-r2", 128, "replicate", "e3o-x128"),
                              ("e3o-x512", 512, "heldout", None), ("e3o-x1000", 1000, "control", None)):
        rows.append(Row(nm, st, "safe", "-", "stophang", "-",
                        f'probe --tri pixel --width 64 --height 64 --blk 6={_hx(f32(float(off)))} '
                        f'--dump-render "$W/dump" --pixels "$S/p1139-green.bin"',
                        f"viewport x offset {off} (control: 1000, E182/E650: no object)", cond or nm))
        P(nm, "object", "none" if off >= 128 else "present", "HO-region", st)
        P(nm, "object", "none" if off >= 1000 else ("?" if off == 512 else "present"), "HO-guard", st)
    # (e) fine grid, 1/1024 pixel (unit 10); control 1/256 pixel
    def fine(nm, unit, vs, st, role):
        v = ",".join(str(c) for c in vs)
        rows.append(Row(nm, st, "safe", "-", "stophang", "-",
                        f'probe --tri pixel --width 64 --height 64 --tri-v {v} --tri-unit {unit} '
                        f'--dump-render "$W/dump" --pixels "$S/p1139-green.bin"', role, nm))
        sc = 1 << unit
        for lab, fn in (("HF-trunc", math.floor), ("HF-round", lambda x: math.floor(x + 0.5))):
            P(nm, "packed_24bit", ";".join(f"{fn((c / sc + 4096) * 256):d}" for c in vs), lab, st)
    base = [(8, 8), (56, 20), (20, 56)]
    fine("e3f-ctl", 8, [c * 256 for p in base for c in p], "control", "control: a 1/256 triangle (E651)")
    for nm, r in (("e3f-r1", 1), ("e3f-r3", 3), ("e3f-r2", 2)):
        vs = [c * 1024 + r + 4 * k for p in base for k, c in enumerate(p)]
        fine(nm, 10, vs, "heldout", f"steps of 1/1024, step index = {r} mod 4")
    # (f) WCLAMP boundary (blk 14 compares w, as E194: clamp 1e-3 removes w <= 1e-5)
    for nm, w, cl, st, role in (("e3k-ctl", 0x3727c5ac, 0x3a83126f, "control", "control: E194, w 1e-5 under clamp 1e-3"),
                                ("e3k-eq", 0x3a83126f, 0x3a83126f, "heldout", "clamp = w"),
                                ("e3k-above", 0x3a83126f, 0x3a831270, "heldout", "clamp one ulp above w"),
                                ("e3k-below", 0x3a83126f, 0x3a83126e, "heldout", "clamp one ulp below w")):
        p = _p3(nm, "vtx_w.s", "vtxuse", ["W"], [_hx(w)], blk={14: cl})
        add(p, st, role)
        P(nm, "object", {"e3k-ctl": "none", "e3k-eq": "?", "e3k-above": "none", "e3k-below": "present"}[nm],
          "w < clamp removes (E194)", st)
    # (g) guard band scale
    for nm, c in (("e3g-8x", [0x41000000, 0, 0x3f800000]), ("e3g-64x", [0x42800000, 0, 0x3f800000]),
                  ("e3g-1024x", [0x44800000, 0, 0x3f800000])):
        p = _p3(nm, "vtx_wclip.s", "vtxuse", ["S", "A", "B"], [_hx(x) for x in c])
        add(p, "heldout", "guard band scale (E063 images exist; dumped now)")
    needs = list(dict.fromkeys(needs))
    head = """E3 (geometry): Q230, what the TA writes for clipped, perspective and off-target triangles.
Offline first (done here): the three mte/rhw dumps (w = x + 2 per vertex) give the stored 1/w =
round-toward-zero float32 of the exact reciprocal (0x3f4ccccc, 0x3eba2e8b, 0x3f1d89d8 against the
nearest 0x...cd, 0x...8c, 0x...d9) in 9 of 9 vertices; those 9 are the FIT.  The packed x, y of
those jobs are unchanged (8, 56, 20): that vertex program does not divide x, y, so the division is
untested.  Every group's control comes first in its group and must reproduce a landed object (E651)
or image (E194, E287, E650) before the group's cells count.  Offsets are the state block's
viewport x offset (word 6, absolute pixels, E061/E182), not distances.  Programs are the landed mte
templates; the commands come from probe.tool_args, and --tri-v/--tri-unit are appended by hand
(probe.py does not model them).  35 jobs; the *-r2 jobs are replicates of one condition."""
    return rows, preds, needs, head
