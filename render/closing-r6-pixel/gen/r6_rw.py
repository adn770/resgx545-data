# SPDX-License-Identifier: MIT
"""Stages g6-rwa (8 jobs) and g6-rw (106 jobs) of R6-pixel (Q230, the 1/w word; plan closing6/pixel/exp-pixel-r6.md section 4,
decisions R6-2 a, pixel decision 7 a).  Command: R4's and R5's CMD byte for byte (r5_rw.CMD); template vtx_zws.s (o0 = S x, o1 = S y).
g6-rwa: rw-k0..k5 and d-01, d-02, R5's programs byte for byte (copied from the published R5 bins, checked against a rebuild); the
gate before g6-rw: every control word exact.  g6-rw, in order: L (72: windows at strides 1, 2^8, 2^16), B (8: frac 0.42 to 0.62),
two L jobs again (replicates), E (24: four R4 rows at six exponents; last, so a clipped far exponent costs nothing before it).
Frozen per job (R5's rows): object, 3 vertices in input order, window 32 + 32 S x / w, depth 0x3f000000, every word RZ or RZ + 1;
L and B: frac per vertex and H-FRAC (RZ where frac < 0.5); E: H-MANT = R4's delta; replicates: the words of their L job.
See score/rwdesign6.py."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import r5common as K  # noqa: E402
import r5_rw as R5W  # noqa: E402
import rwdesign6 as D  # noqa: E402
from r5common import Row, build_bin  # noqa: E402

KNOBS = "stophang s2"
CMD = R5W.CMD


def fr4(x):
    return "%.4f" % float(x)


def build_stage(which):
    rows, preds, needs = [], [], []
    needs.append(build_bin("pix_green", (K.TEMPLATES / "pix_green.s").read_text()))
    if which == "g6-rwa":
        plist = [(p, "control") for p in D.controls()]
    else:
        plist = ([(p, "heldout") for p in D.l_rows()] + [(p, "heldout") for p in D.b_rows()]
                 + [(p, "replicate") for p in D.replicates()] + [(p, "heldout") for p in D.e_rows()])
    for p, st in plist:
        assert D.exact(p), p["name"]
        assert D.viewport_ok(p["w"], p["S"]), f"{p['name']}: a vertex outside the viewport"
        prog = p.get("of", p["name"])
        if p["kind"].startswith("control"):
            (K.BINS / f"{prog}.bin").write_bytes((D.R5_BINS / f"{prog}.bin").read_bytes())
            needs.append(f"$S/{prog}.bin")
            if p["template"] in ("vtx_zws", "r5"):            # R5's own vtx_zws programs: the copy must equal a rebuild
                q = dict(p, template="vtx_zws")
                build_bin(f"chk-{prog}", R5W.text_of(q))
                chk = (K.BINS / f"chk-{prog}.bin")
                assert chk.read_bytes() == (K.BINS / f"{prog}.bin").read_bytes(), f"{prog}: R5's bytes are not a rebuild"
                chk.unlink()
                del K._built[f"chk-{prog}"]
        elif "of" in p:
            needs.append(f"$S/{prog}.bin")
        else:
            needs.append(build_bin(prog, R5W.text_of(p)))
        role = f"{p['kind']}: S {float(p['S']):g}, w = {', '.join('%.6g' % float(x) for x in p['w'])}"
        if "window" in p:
            role += f" (window {p['window'][0]}: stride {p['window'][1]}, base {p['window'][2]:#x})"
        if "r4" in p:
            role += f" (R4's {p['r4']} at exponent {p['exp']})"
        if "of" in p:
            role += f" (replicate of {p['of']})"
        rows.append(Row(p["name"], st, K.SAFE, KNOBS, "-", CMD.format(prog=prog), role))
        P = lambda q, v, m: preds.append((p["name"], q, v, m, st))
        P("object", "present", "no clip: z = 0 inside +-w, every vertex inside the viewport (E782 t3-nocut; R5 design)")
        P("nvert", "3", "3 vertices in input order (E782)")
        P("w_words", ",".join(D.hx(b) for b in p["words"]), "the exact w words (C x + D exact in float32)")
        P("scale", D.hx(D.bits(p["S"])), "o0 = S x, o1 = S y (vtx_zws.s; 1 for R4's programs)")
        P("xy_ordered", R5W.fmt_xy(p), "window = 32 + 32 S x / w per vertex, tolerance 1/32 pixel")
        P("depth_words", ",".join(["0x3f000000"] * 3), "z = 0: depth 0.5 (E782)")
        P("rz_words", ",".join(D.hx(D.rz_word(b)) for b in p["words"]), "RZ of 1/w: every word RZ or RZ + 1 (E842, E859: 168 of 168)")
        if "known" in p:
            P("rhw_known", ",".join(D.hx(b) if b is not None else "?" for b in p["known"]),
              "the known words (R4 controls: E754, E795, E796, E798; rw-k4 RZ, rw-k5 RZ + 1: E795; d-01, d-02: R5's six words, E859)")
        if p["kind"] in ("l", "b", "replicate"):
            fs = [D.frac(D.mant(b)) for b in p["words"]]
            P("frac", ",".join(fr4(f) for f in fs), "frac = fractional part of 2^47 / M (E872)")
            P("hfrac", ",".join("RZ" if f < D.F(1, 2) else "?" for f in fs), "H-FRAC (E872): frac < 0.5 never stores RZ + 1")
        if "window" in p:
            P("window", f"{p['window'][0]}:{p['window'][1]}:{p['window'][2]:#x}", "the window (tag, stride, base) of this job")
        if p["kind"] == "e":
            P("hmant", ",".join(str(d) for d in p["hmant"]), f"H-MANT (E851, E859): R4's delta of the same mantissa, exponent {p['exp']}")
            P("exp", str(p["exp"]), "the exponent of every w of the job")
        if p["kind"] == "replicate":
            P("same_as", p["of"], "the replicate's words equal its L job's words")
    if which == "g6-rw":
        A = lambda q, v, m, st="heldout": preds.append(("@g6-rw", q, v, m, st))
        A("premise", "0 of 512703 declared models fit the 99 FIT mantissas; H-FRAC read on FIT, frozen, held 13 of 13 on HELD OUT",
          "E872 (resgx545 main d9b2969): the rows ask how e varies between neighbouring mantissas")
        A("hfrac_rule", "held iff no L or B word with frac < 0.5 stores RZ + 1 and >= 20 such words are read; one refutes", "plan 4, E872")
        A("separable_rule", "a window is separable iff every RZ + 1 word has a larger frac than every RZ word; scored only with >= 30 of "
          "36 words read, >= 4 RZ + 1 and >= 4 RZ words above frac 0.5 (else cannot tell)", "plan 4 L")
        A("hsmooth_rule", "H-SMOOTH(s) held iff both windows of stride s are separable, refuted iff both have an inversion, mixed "
          "otherwise; no stride is predicted to hold", "plan 4 L")
        A("hmant_rule", "per exponent: held iff 12 of 12 E words equal R4's delta; a job without its frozen shape is 'no object at "
          "this exponent', recorded, not a refutation", "plan 4 E")
        A("shape_stop", "three L or B jobs without 3 vertices at the frozen window void L and B (the design is wrong)", "plan 4", "table")
        A("windows", " ".join(f"{t}:{s}:{b:#x}" for t, s, b in D.windows()), "the six windows (sha256 of 'r6-rw-win-<n>')", "table")
        A("e_source", " ".join(D.e_source()), "R4's rows with the most RZ + 1 words, ties by name (E842)", "table")
    head = {"g6-rwa": """Q230 (geometry), g6-rw part a: 8 controls, R5's programs byte for byte: rw-k0..k5 (the known words exact) and d-01, d-02
(R5's six words exact, two RZ + 1).  Gate before part b: every control word exact.""",
            "g6-rw": """Q230 (geometry), g6-rw part b (106 jobs): L, windows of 36 neighbouring mantissas at strides 1, 2^8 and 2^16, two bases each
(H-SMOOTH: is e smooth in the mantissa; H-FRAC on every word); B, 8 jobs with every mantissa's frac in [0.42, 0.62) (H-FRAC near
its cut); replicates l-1a-00 and l-16a-00; E, R4's four rows with the most RZ + 1 words at exponents -12, -6, -3, 5, 8, 12
(H-MANT per exponent; a clipped exponent is 'no object', not a refutation)."""}[which]
    return rows, preds, list(dict.fromkeys(needs)), head
