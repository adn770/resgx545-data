# SPDX-License-Identifier: MIT
"""Stage p-c3 (Q276, pixel): the frozen rerun of R1's p-c2 with a control that can fail for a reason (decisions R3-P6, R3-P7,
R3-P8: 75 jobs: 18 control, 28 CONFIRM, 28 HELD OUT, 1 replicate; the 128x128 direct reads last).  closing3/pixel/
exp-pixel-r3.md section 3.  Same job shape as R1's p-c2 (C_BASE of closing2/r1-pixgeo/gen/r1_q276.py), same decode.

Model M (frozen from E772's post hoc readings and E086): g25 = (x & 1) | (y & 1) << 1 (the lane in a 2x2 quad); g23 = x mod 32
(the high half 0); g24 = y mod 16; `xor.testtaz ... p1, g25, #k` is true for the instance whose lane is k; a predicate on the o4
write is ignored (both complementary writes run, the last wins).  Alternatives that differ are named per row."""
from __future__ import annotations

import r3common as K
from r3common import C, DATA, REPO, Row, build_bin

C_BASE = ('probe --tri pixel --temps 32 --pixels --dump-render "$W/dump" --width {w} --height {h} --vtx-coords 2 {full}'
          '--blk 4=0x00030001 --slot pixpds="$S/pds_iter_xy.bin:12" --slot vtxuse="$S/vtx_coords.bin" '
          '"$S/{prog}.bin"')
KNOBS = "stophang"
# o1 tags: 2 (p1 true), 12 = 0xc (!p1); o4 tags: 5 (p1 true), 13 = 0xd (5', !p1)
K_TEST = {f"k{k}": f"xor.testtaz.chan0 !c0, p1, g25, #{k}" for k in (0, 1, 2, 3, 5, 7)}
G25_TEST = {"g25b0": "and.testtanz.chan0 !c0, p1, g25, #1", "g25b1": "and.testtanz.chan0 !c0, p1, g25, #2"}
G23_EQ = {"g23eq20": 20, "g23eq40": 40}
G23_MASK = {"g23r4": 0x10, "g23r0": 1, "g23r1": 2, "g23r2": 4, "g23r3": 8, "g23r5": 0x20, "g23r6": 0x40, "g23r20": 0x100000,
            "g23m18": 0x18}
O4_PLAIN = ("o4-u", "o4-k0", "o4-k3", "o4-k7")
O4_SWAP = ("o4s-u", "o4s-k0", "o4s-k3", "o4s-k7")
RDS = {f"{p}-{g}": g for p in ("rd", "rdf", "rdf128") for g in ("g23", "g24", "g25")}


def c_program(cfg: str, ax: str, m: int) -> str:
    """E709's shader with o1 guarded by complementary predicates (the second write wins: tag 2 under p1), or with o4 guarded
    (o4-*: the !p1 write 5' first, the p1 write 5 last; o4s-*: the p1 write 5 first, the !p1 write 5' last)."""
    pa = "pa0" if ax == "x" else "pa1"
    t = lambda j: f"#0x{m * 16 + j:x}"
    ops = ["phas #0, #0, pixel, end, parallel", f"or.skipinv o0, {pa}, {t(1)}"]
    test = None
    key = cfg.split("-r2")[0] if cfg.startswith("u-") else cfg
    if key in K_TEST:
        test = [K_TEST[key]]
    elif key in G25_TEST:
        test = [G25_TEST[key]]
    elif key in G23_EQ:
        test = [f"xor.testtaz.chan0 !c0, p1, g23, #{G23_EQ[key]}"]
    elif key in G23_MASK:
        test = [f"mov.skipinv r1, #0x{G23_MASK[key]:x}", "and.testtanz.chan0 !c0, p1, g23, r1"]
    if cfg.startswith("o4"):
        k = cfg.split("-", 1)[1]
        o4test = [K_TEST[k]] if k in K_TEST else []
        ops += o4test + [f"or.skipinv o1, {pa}, {t(12)}", f"or.skipinv o1, {pa}, {t(2)}",
                         f"or.skipinv o2, {pa}, {t(3)}", f"or.skipinv o3, {pa}, {t(4)}"]
        swapped = cfg.startswith("o4s")
        first, last = (t(5), t(13)) if swapped else (t(13), t(5))
        if o4test:
            if swapped:
                ops += [f"p1 or.skipinv o4, {pa}, {first}", f"!p1 or.skipinv o4, {pa}, {last}"]
            else:
                ops += [f"!p1 or.skipinv o4, {pa}, {first}", f"p1 or.skipinv o4, {pa}, {last}"]
        else:
            ops += [f"or.skipinv o4, {pa}, {first}", f"or.skipinv o4, {pa}, {last}"]
    else:
        if test:
            ops += test + [f"!p1 or.skipinv o1, {pa}, {t(12)}", f"p1 or.skipinv o1, {pa}, {t(2)}"]
        else:                                                    # unpredicated: the second write wins
            ops += [f"or.skipinv o1, {pa}, {t(12)}", f"or.skipinv o1, {pa}, {t(2)}"]
        ops += [f"or.skipinv o2, {pa}, {t(3)}", f"or.skipinv o3, {pa}, {t(4)}"]
        ops += [f"p1 or.skipinv o4, {pa}, {t(5)}" if test else f"or.skipinv o4, {pa}, {t(5)}"]
    ops += [f"or.skipinv o5, {pa}, {t(6)}", f"or.skipinv o6, {pa}, {t(7)}", f"or.skipinv.end o7, {pa}, {t(8)}"]
    return "\n".join(ops) + "\n"


def rd_program(cfg: str, ax: str, m: int) -> str:
    """Direct reads: o0 only, so o0 is the pixel's own word."""
    if cfg in RDS:
        return f"phas #0, #0, pixel, end, parallel\nor.skipinv.end o0, {RDS[cfg]}, #0\n"
    pa = "pa0" if ax == "x" else "pa1"                          # rd-pa: o0 = pa0 / pa1 | tag 15 (the premise control)
    return f"phas #0, #0, pixel, end, parallel\nor.skipinv.end o0, {pa}, #0x{m * 16 + 15:x}\n"


# ---- the plan: (config, set, shape, role); shape = 'def' (default triangle 64x64), 'f64' (full 64x64), 'f128' (full 128x128)
CONTROL = [("e709", "def"), ("o4-u", "def"), ("u", "def"), ("u-r2", "def"), ("g23r4", "def"), ("o4s-u", "def"),
           ("rd-pa", "def"), ("rdf-pa", "f64")]
CONFIRM = [("k0", "def"), ("k1", "def"), ("k2", "def"), ("k3", "def"), ("k5", "def"), ("k7", "def"),
           ("g23r0", "def"), ("g23r3", "def"), ("g23r5", "def"), ("g23r20", "def"),
           ("o4-k0", "def"), ("o4-k3", "def"), ("o4-k7", "def")]
HELD = [("g23r1", "def"), ("g23r2", "def"), ("g23r6", "def"), ("g23m18", "def"), ("g23eq20", "def"), ("g23eq40", "def"),
        ("g25b0", "def"), ("g25b1", "def"), ("o4s-k0", "def"), ("o4s-k3", "def"), ("o4s-k7", "def")]
DIRECT_CONFIRM = ["rd-g23", "rd-g25"]
DIRECT_HELD_DEF = ["rd-g24"]
DIRECT_FULL64 = ["rdf-g23", "rdf-g24", "rdf-g25"]
DIRECT_FULL128 = ["rdf128-g23", "rdf128-g25"]


def shape_args(shape):
    return {"def": (64, 64, ""), "f64": (64, 64, "--tri-full "), "f128": (128, 128, "--tri-full ")}[shape]


def lane_pred(P, n, k, st):
    """HQ-a / HQ-b: the g25 lane predicate xor.testtaz g25, #k (A: (x&1)|(y&1)<<1; B: its transpose)."""
    if k in (5, 7):
        P(n, "frac_tag2_of_o1", "0.0", "M (a lane id is 0..3: g25 == %d never)" % k, st)
        P(n, "rule", "never", "M (a lane id is 0..3: g25 == %d never)" % k, st)
        return
    mm = "M (g25 = (x&1) | (y&1)<<1)"
    P(n, "frac_tag2_of_o1", "0.25", mm, st)
    P(n, "rule", f"lane:{k}:A", mm, st)
    par = {0: "0,0", 1: "1,0", 2: "0,1", 3: "1,1"}[k]
    P(n, "tag2_parity", par, mm, st)
    if k in (1, 2):                                                # the transpose differs only where the two lanes differ
        tb = "T (g25 = (x&1)<<1 | (y&1), the transpose)"
        P(n, "frac_tag2_of_o1", "0.25", tb, st)
        P(n, "rule", f"lane:{k}:B", tb, st)
        P(n, "tag2_parity", {1: "0,1", 2: "1,0"}[k], tb, st)


def g23_pred(P, cfg, n, st):
    """M: x bit b for b < 5, never above (g23 = x mod 32, the high half 0).  Alternatives: g23 = x (bit 5, 6 true at x >= 32, 64),
    g23 = y << 16 | x (bit 20 is y bit 4)."""
    mm = "M (g23 = x mod 32, high half 0)"
    b = {"g23r0": 0, "g23r1": 1, "g23r2": 2, "g23r3": 3, "g23r4": 4, "g23r5": 5, "g23r6": 6, "g23r20": 20}[cfg]
    P(n, "rule", f"x:{b}" if b < 5 else "never", mm, st)
    if b == 5:
        P(n, "rule", "x:5", "X (g23 = x, no wrap: bit 5 true for x in 32..63)", st)
    if b == 6:
        P(n, "rule", "x:6", "X (g23 = x: bit 6 true at x >= 64 only; also never in a 64-wide target: reported apart)", st)
    if b == 20:
        P(n, "rule", "y:4", "XY (g23 = y << 16 | x: bit 20 is y bit 4)", st)


def c3():
    rows, preds, needs, markers = [], [], [], {}
    P = lambda n, q, v, mdl, st: preds.append((n, q, v, mdl, st))
    pds = (REPO / "probes/usse/templates/pds_iter_xy.s").read_text()
    from r3common import probe, BINS
    BINS.mkdir(exist_ok=True)
    probe._assemble(pds, BINS / "pds_iter_xy.bin", "pds")
    probe._assemble((REPO / "probes/usse/templates/vtx_coords.s").read_text(), BINS / "vtx_coords.bin")
    needs += ["$S/pds_iter_xy.bin", "$S/vtx_coords.bin"]
    PD = DATA / "vdm/verification-1141ta/programs"
    for ax in "xy":                                             # E709's own programs, byte for byte
        build_bin(f"r3c-e709-{ax}", (PD / f"o4g-3-{ax}.s").read_text())
        needs.append(f"$S/r3c-e709-{ax}.bin")
    state = {"m": 0x300}

    def job(cfg, ax, st, shape, role, prog_text=None):
        w, h, full = shape_args(shape)
        state["m"] += 1
        m = state["m"]
        jn = f"c-{cfg}-{ax}" if ax else f"c-{cfg}"
        if cfg == "e709":
            prog = f"r3c-e709-{ax}"
        else:
            prog = f"r3c-{cfg}-{ax or 'x'}"
            text = rd_program(cfg, ax or "x", m) if (cfg in RDS or cfg.endswith("pa")) else c_program(cfg, ax, m)
            build_bin(prog, text)
            needs.append(f"$S/{prog}.bin")
            markers[jn] = m
        rows.append(Row(jn, st, K.SAFE, KNOBS, "-", C_BASE.format(w=w, h=h, full=full, prog=prog), role))
        return jn

    def pair(cfg, st, shape, role):
        jx = job(cfg, "x", st, shape, role)
        job(cfg, "y", st, shape, role + " (the y job of the pair: source pixel identity)")
        return jx

    mk = lambda jn: P(jn, "marker", f"{markers[jn]:#x}", "frozen program marker (knob proof)", "control")
    # ---------------------------------------------------------------- controls (18 jobs, the 128x128 premise control last)
    ctl_roles = {"e709": "G-o4 control: E709's o4g-3 unchanged", "o4-u": "G-o4 control: both o4 writes unpredicated (5 last)",
                 "u": "G-o1 order control: both o1 writes unpredicated, the second (tag 2) wins",
                 "u-r2": "G-o1 order control, second run", "g23r4": "register-form control: mask 0x10 in r1 (S1b: x bit 4)",
                 "o4s-u": "swapped-order control: the o4 writes unpredicated, 5' (the last) wins"}
    for cfg, shape in CONTROL:
        if cfg in ("rd-pa", "rdf-pa"):
            continue
        jx = pair(cfg, "control", shape, ctl_roles[cfg])
        if cfg != "e709":
            mk(jx)
        if cfg in ("e709", "o4-u"):
            P(jx, "g_o4_words", "10..100", "G-o4 structural (26 runs of R1 p-c2 and S1b p-c: tag-5 words 19..50 in the x and y job)", "control")
            P(jx, "g_o4_pairs", "5..60", "G-o4 structural (26 runs: pairs 8..42; one program 8..33)", "control")
            P(jx, "g_o4_parity", "even,even", "G-o4 structural (571 of 571 pair sources are (even x, even y))", "control")
            P(jx, "g_o4_tag5p_max", "2", "G-o4 structural (no tag-5' word in the x job of any of the 26 runs)", "control")
        if cfg == "o4-u":
            P(jx, "o4_class", "5", "M (the last o4 write wins: tag 5)", "control")
        if cfg == "o4s-u":
            P(jx, "o4_class", "5'", "M (the last o4 write wins: tag 5')", "control")
        if cfg in ("u", "u-r2"):
            P(jx, "ctl_min_frac", "0.98", "frozen criterion (R1 / S1b: tag-2 fraction 0.990 to 0.996 in 5 runs)", "control")
        if cfg == "g23r4":
            P(jx, "rule", "x:4", "M (g23 = x mod 32: bit 4; S1b's immediate form gave x bit 4)", "control")
    for cfg, shape in (("rd-pa", "def"), ("rdf-pa", "f64")):
        for ax in "xy":
            jn = job(cfg, ax, "control", shape, f"premise control of the direct reads ({'default' if shape == 'def' else 'full 64x64'} triangle): "
                     "o0 = pa0 / pa1 lands at the pixel's own position")
        P(f"c-{cfg}-x", "marker", f"{markers[f'c-{cfg}-x']:#x}", "frozen program marker (knob proof)", "control")
        P(f"c-{cfg}-x", "rd_identity", "0.9", "o0 lands at the pixel's own position (>= 90% of the written pixels)", "control")
    # ---------------------------------------------------------------- CONFIRM (28 jobs)
    roles = {}
    for cfg, shape in CONFIRM:
        jx = pair(cfg, "repeat", shape, f"CONFIRM (read post hoc in round 2, frozen now): {cfg}")   # tallied apart from HELD OUT
        mk(jx)
        st = "repeat"
        if cfg[0] == "k":
            lane_pred(P, jx, int(cfg[1]), st)
        elif cfg.startswith("g23"):
            g23_pred(P, cfg, jx, st)
        else:                                                    # o4-k*
            P(jx, "o4_class", "5", "M (a predicate on the o4 write is ignored: the last write, tag 5, wins)", st)
            if cfg in ("o4-k3", "o4-k7"):
                P(jx, "o4_class", "not5", "G (the o4 write gated like o1 by g25 == k: tag 5' for the instances where p1 is false)", st)
    for cfg in DIRECT_CONFIRM:
        jn = job(cfg, None, "repeat", "def", f"CONFIRM (direct read, set repeat): o0 = {RDS[cfg]} of the pixel's own instance")
        direct_pred(P, jn, cfg, "repeat", "def")
    # ---------------------------------------------------------------- HELD OUT (28 jobs; the direct reads after the o1/o4 rows)
    for cfg, shape in HELD:
        jx = pair(cfg, "heldout", shape, f"HELD OUT (never run): {cfg}")
        mk(jx)
        st = "heldout"
        if cfg.startswith("g23r"):
            g23_pred(P, cfg, jx, st)
        elif cfg == "g23m18":
            P(jx, "rule", "xany:24", "M (g23 = x mod 32: true iff bit 3 or 4 of x)", st)
        elif cfg.startswith("g23eq"):
            kk = G23_EQ[cfg]
            P(jx, "rule", f"xeq:{kk}", f"M (g23 = x mod 32: true iff x mod 32 == {kk}; x = 20 and 52 for 20, never for 40)", st)
            P(jx, "rule", f"xe:{kk}", f"X (g23 = x: true only at x == {kk})", st)
        elif cfg == "g25b0":
            P(jx, "rule", "x:0", "M (g25 = (x&1) | (y&1)<<1: g25 & 1 is odd x)", st)
            P(jx, "rule", "y:0", "T (the transpose: g25 & 1 is odd y)", st)
        elif cfg == "g25b1":
            P(jx, "rule", "y:0", "M (g25 & 2 is odd y)", st)
            P(jx, "rule", "x:0", "T (the transpose: g25 & 2 is odd x)", st)
        elif cfg.startswith("o4s-"):
            P(jx, "o4_class", "5'", "M (a predicate on the o4 write is ignored: the last write, tag 5', wins)", st)
            P(jx, "o4_class", "not5'", "G (the o4 write gated like o1: the p1-true instances keep tag 5)", st)
    for cfg in DIRECT_HELD_DEF:
        jn = job(cfg, None, "heldout", "def", f"HELD OUT (direct read): o0 = {RDS[cfg]} (g24, E086's fill reading)")
        direct_pred(P, jn, cfg, "heldout", "def")
    for cfg in DIRECT_FULL64:
        jn = job(cfg, None, "heldout", "f64", f"HELD OUT (direct read, full 64x64 triangle): o0 = {RDS[cfg]}")
        direct_pred(P, jn, cfg, "heldout", "f64")
    # ---------------------------------------------------------------- the 128x128 rows last: premise control, then two reads
    for ax in "xy":
        job("rdf128-pa", ax, "control", "f128", "premise control of the 128x128 direct reads: o0 = pa0 / pa1 lands at the pixel's own position")
    P("c-rdf128-pa-x", "marker", f"{markers['c-rdf128-pa-x']:#x}", "frozen program marker (knob proof)", "control")
    P("c-rdf128-pa-x", "rd_identity", "0.9", "o0 lands at the pixel's own position (>= 90% of the written pixels)", "control")
    for cfg in DIRECT_FULL128:
        jn = job(cfg, None, "heldout", "f128", f"HELD OUT (direct read, full 128x128 triangle): o0 = {RDS[cfg]}")
        direct_pred(P, jn, cfg, "heldout", "f128")
    # ---------------------------------------------------------------- the replicate (a second run of c-k1-x: an identical job)
    kx = next(r for r in rows if r.name == "c-k1-x")
    rows.append(Row("c-k1-x-rep", "replicate", K.SAFE, KNOBS, "-", kx.args, "replicate of c-k1-x (same program: identical job)"))
    P("c-k1-x-rep", "frac_tag2_of_o1", "same as c-k1-x", "repeat", "replicate")
    (BINS / "c3-markers.tsv").write_text("".join(f"{k}\t{v}\n" for k, v in markers.items()))
    # the order: controls (the 128 premise control last of them, and the rdf-pa control with them), CONFIRM, HELD OUT, direct reads, 128
    first = [r for r in rows if r.set == "control" and "rdf128" not in r.name]
    rest = [r for r in rows if r not in first and "rdf128" not in r.name]
    tail = [r for r in rows if "rdf128" in r.name]
    rows = first + rest + tail
    head = """Q276 (pixel), frozen rerun of R1's p-c2 (decisions R3-P6 to P8): same job shape and decode as R1's.  Model M (frozen from E772's post hoc
readings and E086): g25 = (x & 1) | (y & 1) << 1 (the lane in a 2x2 quad), g23 = x mod 32 (the high half 0), g24 = y mod 16; a
predicate on the o4 write is ignored (both complementary writes run, the last wins).  Each configuration is an x job and a y job
(a landed word's source pixel needs the pair); the direct reads (o0 alone) are single jobs, their premise (o0 = pa lands at the
pixel's own position) is tested by c-rd-pa (default triangle), c-rdf-pa (full 64x64) and c-rdf128-pa (full 128x128).  CONFIRM rows
(set `repeat`: round 2's post hoc readings, frozen now) are tallied apart from the HELD OUT rows (never run).  Controls are scoped to their group:
G-o4 (structural: tag-5 words 10..100 in each job, pairs 5..60, every pair source (even, even), tag-5' words <= 2: c-e709 and
c-o4-u) gates the o4 rows, G-o1 (tag-2 fraction >= 0.98: c-u, c-u-r2) the o1 rows, c-g23r4 the register-form rows, c-o4s-u the
swapped-order o4 rows, the three premise controls their direct reads; a failed control voids its group only.  The 128x128 rows
are last (new on hardware in this probe shape)."""
    return rows, preds, list(dict.fromkeys(needs)), head


def direct_pred(P, jn, cfg, st, shape):
    base = cfg.replace("rdf128", "rd").replace("rdf", "rd")
    if base == "rd-g23":
        P(jn, "rd_value", "g23:xmod32", "M (g23 = x mod 32)", st)
        P(jn, "rd_value", "g23:x", "X (g23 = x)", st)
        P(jn, "rd_value", "g23:y<<16|x", "XY (g23 = y << 16 | x)", st)
        if shape == "f128":
            P(jn, "rd_value", "g23:xmod64", "X64 (g23 = x mod 64)", st)
    elif base == "rd-g24":
        P(jn, "rd_value", "g24:ymod16", "M (g24 = y mod 16, E086's fill reading)", st)
        P(jn, "rd_value", "g24:y", "Y (g24 = y)", st)
    else:
        P(jn, "rd_value", "g25:A", "M (g25 = (x&1) | (y&1)<<1)", st)
        P(jn, "rd_value", "g25:B", "T (g25 = (x&1)<<1 | (y&1), the transpose)", st)
