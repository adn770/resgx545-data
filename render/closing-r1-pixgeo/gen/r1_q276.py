"""R1 stage p-c2: Q276 C2 (exp-pixel.md section 1, decision R2-11), generator of S1b's p-c (s1pix.c_program) with the
new configurations.  Each configuration is an x job and a y job (the source pixel of a landed word needs the pair,
as E709); the direct reads c-rd-g23 / c-rd-g25 are single jobs (the program writes only o0, which lands at the
pixel's own position: premise tested by the control c-rd-pa).

Hypotheses (frozen with their predictions, exp-pixel.md 1):
  HQ-a   p1 per instance with g25 = (x & 1) | (y & 1) << 1: k = 1 true only at (odd, even) sources, k = 2 only at
         (even, odd), each a quarter;  HQ-b the transpose;  HQ-none: g25 is a lane id 0..3, k = 5 never true
  HG     g23's low bits carry the source x: mask 1 << b true iff x bit b (b = 5, 3, 0), 0 disagreeing sources;
  HG-xy  g23 = y << 16 | x: bit 20 true iff y bit 4;  HG-x: bit 20 never true
  o4:    HN-o4 (the o4 write is not gated: tag 5 for every k), HG-o4 (gated like o1: k = 7, 3 only 5', k = 0 only 5),
         H-g25-7 (the o4 landings are instances with g25 == 7: 5 at k = 7, 5' at k = 0 and 3)
  direct o0 = g23: HG-xy (y << 16 | x);  o0 = g25: HQ-a ((x&1) | (y&1) << 1) / HQ-b (transposed)
"""
from __future__ import annotations

from rcommon import BINS, DATA, REPO, Row, probe

C_BASE = ('probe --tri pixel --temps 32 --pixels --dump-render "$W/dump" --width 64 --height 64 --vtx-coords 2 '
          '--blk 4=0x00030001 --slot pixpds="$S/pds_iter_xy.bin:12" --slot vtxuse="$S/vtx_coords.bin" '
          '"$S/{prog}.bin"')

# o1 tags: 2 (p1 true), 12 = 0xc (!p1), o4 tags: 5 (p1 true), 13 = 0xd (5', !p1)
K_TEST = {f"k{k}": f"xor.testtaz.chan0 !c0, p1, g25, #{k}" for k in (0, 1, 2, 3, 5, 7)}
G23_IMM = {"g23": "and.testtanz.chan0 !c0, p1, g23, #16"}                  # S1b's c-g23 program (bit 4), as is
G23_REG = {"g23r4": 4, "g23r5": 5, "g23r3": 3, "g23r0": 0, "g23r20": 20}      # mask in a register: any bit encodes
CONFIGS = ["e709", "u", "u-r2", "g23r4", "k7", "k0", "g23", "k1", "k2", "k5", "g23r5", "g23r3", "g23r0", "g23r20",
           "o4-k7", "o4-k3", "o4-k0", "o4-u"]
RD = ["rd-pa", "rd-g23", "rd-g25"]


def c_program(cfg: str, ax: str, m: int) -> str:
    """E709's shader with o1 guarded by complementary predicates (the second write wins = tag 2 under p1), or with o4
    guarded (o4-* configurations: o1 unpredicated, o4 written 5' under !p1 first, 5 under p1 second)."""
    pa = "pa0" if ax == "x" else "pa1"
    t = lambda j: f"#0x{m * 16 + j:x}"
    ops = ["phas #0, #0, pixel, end, parallel", f"or.skipinv o0, {pa}, {t(1)}"]
    key = cfg.split("-r2")[0] if cfg.startswith("u-") else cfg
    test = None
    if key in K_TEST:
        test = [K_TEST[key]]
    elif key in G23_IMM:
        test = [G23_IMM[key]]
    elif key in G23_REG:
        test = [f"mov.skipinv r1, #0x{1 << G23_REG[key]:x}", "and.testtanz.chan0 !c0, p1, g23, r1"]
    if cfg.startswith("o4-"):
        k = cfg[3:]
        o4test = [K_TEST[k]] if k in K_TEST else []
        ops += o4test
        ops += [f"or.skipinv o1, {pa}, {t(12)}", f"or.skipinv o1, {pa}, {t(2)}"]      # o1 as c-u: tag 2 wins
        ops += [f"or.skipinv o2, {pa}, {t(3)}", f"or.skipinv o3, {pa}, {t(4)}"]
        if o4test:
            ops += [f"!p1 or.skipinv o4, {pa}, {t(13)}", f"p1 or.skipinv o4, {pa}, {t(5)}"]
        else:
            ops += [f"or.skipinv o4, {pa}, {t(13)}", f"or.skipinv o4, {pa}, {t(5)}"]
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
    src = {"rd-g23": "g23", "rd-g25": "g25"}.get(cfg)
    if src:
        return f"phas #0, #0, pixel, end, parallel\nor.skipinv.end o0, {src}, #0\n"
    pa = "pa0" if ax == "x" else "pa1"                          # rd-pa: o0 = pa0 / pa1 | tag 15 (the premise control)
    return f"phas #0, #0, pixel, end, parallel\nor.skipinv.end o0, {pa}, #0x{m * 16 + 15:x}\n"


def p_c2():
    rows, preds, needs, markers = [], [], [], {}

    def build(name, text):
        probe._assemble(text, BINS / f"{name}.bin")
        needs.append(f"$S/{name}.bin")

    probe._assemble((REPO / "probes/usse/templates/pds_iter_xy.s").read_text(), BINS / "pds_iter_xy.bin", "pds")
    probe._assemble((REPO / "probes/usse/templates/vtx_coords.s").read_text(), BINS / "vtx_coords.bin")
    needs += ["$S/pds_iter_xy.bin", "$S/vtx_coords.bin"]
    PD = DATA / "vdm/verification-1141ta/programs"
    for ax in "xy":                                             # E709's own programs, byte for byte
        probe._assemble((PD / f"o4g-3-{ax}.s").read_text(), BINS / f"r1c-e709-{ax}.bin")
        needs.append(f"$S/r1c-e709-{ax}.bin")

    P = lambda n, q, v, mdl, st: preds.append((n, q, v, mdl, st))
    plan = {
        "e709": ("control", "control: E709's o4g-3 unchanged (17 to 29 tag-5 pairs)"),
        "u": ("control", "order control: both o1 writes unpredicated, the second (tag 2) wins"),
        "u-r2": ("control", "order control, second run"),
        "g23r4": ("control", "control of the register form: mask 0x10 in r1 (S1b's immediate form gave x bit 4)"),
        "k7": ("repeat", "REPEAT (S1b FIT): g25 == 7, never true"),
        "k0": ("repeat", "REPEAT (S1b FIT): g25 == 0"),
        "g23": ("repeat", "REPEAT (S1b FIT): and.testtanz g23 & 16 (immediate form)"),
        "k1": ("heldout", "g25 == 1: HQ-a (odd, even) vs HQ-b (even, odd)"),
        "k2": ("heldout", "g25 == 2: HQ-a (even, odd) vs HQ-b (odd, even)"),
        "k5": ("heldout", "g25 == 5: HQ-none (a lane id is 0..3)"),
        "g23r5": ("heldout", "g23 & 0x20: HG x bit 5"),
        "g23r3": ("heldout", "g23 & 0x08: HG x bit 3"),
        "g23r0": ("heldout", "g23 & 0x01: HG x bit 0"),
        "g23r20": ("heldout", "g23 & 0x100000: HG-xy y bit 4, HG-x never"),
        "o4-k7": ("heldout", "o4 complementary writes under g25 == 7: HN-o4 / HG-o4 / H-g25-7"),
        "o4-k3": ("heldout", "o4 complementary writes under g25 == 3"),
        "o4-k0": ("heldout", "o4 complementary writes under g25 == 0"),
        "o4-u": ("control", "o4 control: both o4 writes unpredicated, tag 5 (the second) wins, every model"),
    }
    m = 0x300
    for cfg in CONFIGS:
        st, role = plan[cfg]
        for ax in "xy":
            m += 1
            jn = f"c-{cfg}-{ax}"
            if cfg == "e709":
                prog = f"r1c-e709-{ax}"
            else:
                prog = f"r1c-{cfg}-{ax}"
                build(prog, c_program(cfg, ax, m))
                markers[jn] = m
            rows.append(Row(jn, st, "safe", "-", "stophang", "-", C_BASE.format(prog=prog), role, jn))
            if ax == "y":
                continue
            n = jn                                              # predictions live on the x job of the pair
            if cfg != "e709":
                P(n, "marker", f"{m:#x}", "frozen program marker (knob proof)", "control")
            if cfg == "e709":
                P(n, "tag5_pairs", "17-29", "E709", "control")
            elif cfg.startswith("u"):
                P(n, "ctl_min_frac", "0.98", "frozen criterion (S1b: 0.990)", "control")
            elif cfg == "g23r4":
                P(n, "rule", "x:4", "HG (S1b fit: x bit 4)", st)
            elif cfg == "k7":
                P(n, "frac_tag2_of_o1", "0.0", "HQ (S1b fit)", st)
                P(n, "rule", "never", "HQ (S1b fit)", st)
            elif cfg == "k0":
                P(n, "frac_tag2_of_o1", "0.25", "HQ (S1b fit)", st)
                P(n, "rule", "lane:0:A", "HQ (S1b fit)", st)
                P(n, "tag2_parity", "0,0", "HQ (S1b fit)", st)
            elif cfg == "g23":
                P(n, "rule", "x:4", "HG (S1b fit: x bit 4, 485 of 485)", st)
            elif cfg in ("k1", "k2"):
                k = int(cfg[1])
                P(n, "frac_tag2_of_o1", "0.25", "HQ-a (g25 = x&1 | (y&1)<<1)", st)
                P(n, "rule", f"lane:{k}:A", "HQ-a (g25 = x&1 | (y&1)<<1)", st)
                P(n, "tag2_parity", "1,0" if k == 1 else "0,1", "HQ-a (g25 = x&1 | (y&1)<<1)", st)
                P(n, "frac_tag2_of_o1", "0.25", "HQ-b (g25 = (x&1)<<1 | y&1, the transpose)", st)
                P(n, "rule", f"lane:{k}:B", "HQ-b (g25 = (x&1)<<1 | y&1, the transpose)", st)
                P(n, "tag2_parity", "0,1" if k == 1 else "1,0", "HQ-b (g25 = (x&1)<<1 | y&1, the transpose)", st)
            elif cfg == "k5":
                P(n, "frac_tag2_of_o1", "0.0", "HQ-none (a lane id is 0..3: g25 == 5 never)", st)
                P(n, "rule", "never", "HQ-none (a lane id is 0..3: g25 == 5 never)", st)
            elif cfg in ("g23r5", "g23r3", "g23r0"):
                b = G23_REG[cfg]
                P(n, "rule", f"x:{b}", f"HG (g23 low bits carry x: bit {b})", st)
            elif cfg == "g23r20":
                P(n, "rule", "y:4", "HG-xy (g23 = y<<16 | x: bit 20 is y bit 4)", st)
                P(n, "rule", "never", "HG-x (g23 = x: bit 20 never)", st)
            elif cfg.startswith("o4-"):
                k = cfg[3:]
                for mdl, cls in (("HN-o4 (the o4 write is not gated)", {"k7": "5", "k3": "5", "k0": "5", "u": "5"}),
                                 ("HG-o4 (o4 gated like o1 by g25 == k)", {"k7": "5'", "k3": "5'", "k0": "5", "u": "5"}),
                                 ("H-g25-7 (o4 landings are instances with g25 == 7)",
                                  {"k7": "5", "k3": "5'", "k0": "5'", "u": "5"})):
                    P(n, "o4_class", cls[k], mdl, "control" if k == "u" else st)
    # direct reads: o0 only
    for cfg in RD:
        if cfg == "rd-pa":
            for ax in "xy":
                m += 1
                jn = f"c-{cfg}-{ax}"
                build(f"r1c-{cfg}-{ax}", rd_program(cfg, ax, m))
                markers[jn] = m
                rows.append(Row(jn, "control", "safe", "-", "stophang", "-", C_BASE.format(prog=f"r1c-{cfg}-{ax}"),
                                "premise control of the direct reads: o0 = pa0 / pa1 lands at the pixel's own position",
                                jn))
            P("c-rd-pa-x", "marker", f"{markers['c-rd-pa-x']:#x}", "frozen program marker (knob proof)", "control")
            P("c-rd-pa-x", "rd_identity", "0.9", "o0 lands at the pixel's own position (>= 90% of written pixels)",
              "control")
        else:
            jn = f"c-{cfg}"
            build(f"r1c-{cfg}", rd_program(cfg, "x", m))
            rows.append(Row(jn, "heldout", "safe", "-", "stophang", "-", C_BASE.format(prog=f"r1c-{cfg}"),
                            f"DIRECT READ: o0 = {cfg[3:]} of the pixel's own instance (held out, R2-11)", jn))
            if cfg == "rd-g23":
                P(jn, "rd_value", "g23:y<<16|x", "HG-xy (g23 = y<<16 | x)", "heldout")
            else:
                P(jn, "rd_value", "g25:A", "HQ-a (g25 = (x&1) | (y&1)<<1)", "heldout")
                P(jn, "rd_value", "g25:B", "HQ-b (g25 = (x&1)<<1 | (y&1))", "heldout")
    # the replicate of c-k1-x (same program: an identical job)
    kx = next(r for r in rows if r.name == "c-k1-x")
    rows.append(Row("c-k1-x-rep", "replicate", "safe", "-", "stophang", "-", kx.args,
                    "replicate of c-k1-x (same program: identical job)", "c-k1-x"))
    P("c-k1-x-rep", "frac_tag2_of_o1", "same as c-k1-x", "repeat", "replicate")
    (BINS / "c2-markers.tsv").write_text("".join(f"{k}\t{v}\n" for k, v in markers.items()))
    needs = list(dict.fromkeys(needs))
    rows = [r for r in rows if r.set == "control"] + [r for r in rows if r.set != "control"]
    head = """C2 (pixel): Q276 held out (R2-11).  S1b's p-c generator (s1pix.c_program) with new configurations; every
configuration is an x job and a y job (source pixel identity), predictions on the x job.
HQ-a/HQ-b: k = 1, 2 (which parity the tag-2 sources have); HQ-none: k = 5.  HG: g23 masks 0x20, 0x08, 0x01 (x bits 5,
3, 0), 0x100000 (HG-xy y bit 4, HG-x never); masks go through a register (an immediate above 127 does not encode; the
register form is validated by c-g23r4, mask 0x10, against S1b's immediate form c-g23).  o4: complementary writes
under k = 7, 3, 0 and unpredicated.  Direct reads: o0 = g23 / g25 alone (c-rd-pa checks that o0 lands at the pixel's
own position).  Scoring per source: rule agreement (at most max(2, 2%) exceptions among >= 300 decoded o1 sources; the
proposal's '<= 2 of >= 400' would refute S1b's own fit, c-k0 having 6 exceptions of 490), not only fractions."""
    return rows, preds, needs, head
