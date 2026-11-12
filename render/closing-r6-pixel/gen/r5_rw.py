# SPDX-License-Identifier: MIT
"""Stage g5-rw (Q230, the 1/w word; 48 jobs; plan closing5/pixel/exp-pixel-r5.md section 4, decisions R5-3 a, pixel D4 a, D5 a), run
as two job tables so that the plan's stops act before the table: g5-rwa (12 jobs: the 6 controls, then the 6 quarter jobs q-15..q-20)
and g5-rw (36 jobs: m-01..m-14, the replicates rw-07 and rw-10, the dense table d-01..d-20).  The driver scores g5-rwa and its gate
stops the session unless every control word is exact and fewer than three q jobs FAILED shape (the design is wrong again).
Command: R4's CMD byte for byte (R2's t3-nocut shape); R4's own programs for rw-k0..k3, rw-07, rw-10 (vtx_zw.s), the new template
vtx_zws.s (o0 = S x, o1 = S y) for the rest.  Frozen per job: object present, 3 vertices in input order, window 32 + 32 S x / w,
depth 0x3f000000, every word RZ or RZ + 1; controls: the known words exact; q: H-MANT on 4 words; m: H-MANT = R4's delta on 42 words;
replicates: R4's six words; d: RZ or RZ + 1 and the FIT / HELD OUT split (sha256) for a later fit.  See score/rwdesign5.py."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import r5common as K  # noqa: E402
import rwdesign5 as D  # noqa: E402
from r5common import Row, build_bin  # noqa: E402

KNOBS = "stophang s2"
CMD = ('probe --temps 8 --pixels --tri vtxuse --width 64 --height 64 --vtx-coords 2 --dump-render "$W/dump" '
       '--slot "pixel=$S/pix_green.bin" "$S/{prog}.bin"')
R4BINS = D.R4_SCORE.parent.parent.parent / "bins"


def fmt_xy(p):
    return ";".join("%.6f,%.6f" % tuple(float(v) for v in D.window(i, p["w"][i], p["S"])) for i in range(3))


def text_of(p):
    if p["template"] == "vtx_zw":
        t = (K.TEMPLATES / "vtx_zw.s").read_text()
    else:
        t = (K.TEMPLATES / "vtx_zws.s").read_text().replace("{S}", D.hx(D.bits(p["S"])))
    return (t.replace("{A}", "0x00000000").replace("{B}", "0x00000000")
            .replace("{C}", D.hx(D.bits(p["C"]))).replace("{D}", D.hx(D.bits(p["D"]))))


def build_stage(which):
    rows, preds, needs = [], [], []
    needs.append(build_bin("pix_green", (K.TEMPLATES / "pix_green.s").read_text()))
    kd = D.known_deltas()
    r4 = D.r4_words()
    spl = D.split()
    if which == "g5-rwa":
        plist = [(p, "control") for p in D.controls()] + [(p, "heldout") for p in D.q_rows()]
    else:
        plist = ([(p, "heldout") for p in D.m_rows()] + [(p, "replicate") for p in D.replicates()]
                 + [(p, "table") for p in D.d_rows()])
    for p, st in plist:
        assert D.exact(p), p["name"]
        assert D.viewport_ok(p["w"], p["S"]), f"{p['name']}: a vertex outside the viewport"
        prog = p["name"]
        if p["template"] == "vtx_zw":                      # R4's own program: the published bytes, checked against a rebuild
            (K.BINS / f"{prog}.bin").write_bytes((R4BINS / f"{prog}.bin").read_bytes())
            needs.append(f"$S/{prog}.bin")
        else:
            needs.append(build_bin(prog, text_of(p)))
        role = (f"{p['kind']}: S {float(p['S']):g}, w = {', '.join('%g' % float(x) for x in p['w'])}"
                + (f" (R4's {p['r4']} at another exponent)" if "r4" in p else ""))
        rows.append(Row(p["name"], st, K.SAFE, KNOBS, "-", CMD.format(prog=prog), role))
        P = lambda q, v, m: preds.append((p["name"], q, v, m, st))
        P("object", "present", "no clip: z = 0 inside +-w, every vertex inside the viewport (E782 t3-nocut; R5 design)")
        P("nvert", "3", "3 vertices in input order (E782)")
        P("w_words", ",".join(D.hx(b) for b in p["words"]), "the exact w words (C x + D exact in float32)")
        P("scale", D.hx(D.bits(p["S"])), "o0 = S x, o1 = S y (vtx_zws.s; 1 for R4's programs)")
        P("xy_ordered", fmt_xy(p), "window = 32 + 32 S x / w per vertex, tolerance 1/32 pixel")
        P("depth_words", ",".join(["0x3f000000"] * 3), "z = 0: depth 0.5 (E782)")
        P("rz_words", ",".join(D.hx(D.rz_word(b)) for b in p["words"]), "RZ of 1/w: every word RZ or RZ + 1 (E842: 42 of 42)")
        if "known" in p:
            P("rhw_known", ",".join(D.hx(b) if b is not None else "?" for b in p["known"]),
              "the known words (R4 controls: E754, E795, E796, E798; rw-k4 w 0.3 RZ, rw-k5 w 0.7 RZ + 1: E795)")
        if p["kind"] in ("q", "m"):
            if p["kind"] == "m":
                ds = []
                for v in range(3):
                    w4, rz4, g4 = r4[(p["r4"], v)]
                    assert (w4 & 0x7fffff) == (p["words"][v] & 0x7fffff) and g4 is not None
                    ds.append(str(g4 - rz4))
            else:
                ds = [("?" if D.hmant(b, kd) is None else str(D.hmant(b, kd))) for b in p["words"]]
            P("hmant", ",".join(ds), "H-MANT (E851, resgx545 main): word - RZ is a function of the 23-bit mantissa of w alone ("
              + ("R4's delta of the same mantissa)" if p["kind"] == "m" else "the frozen mantissa table; ? not read)"))
        if p["kind"] == "replicate":
            P("r4_words", ",".join(D.hx(r4[(p["name"], v)][2]) for v in range(3)), "replicate: R4's six words (E842)")
        if p["kind"] == "d":
            P("half", ",".join(spl[b].replace(" ", "_") for b in p["words"]), "sha256 split, lower 30 FIT (a later fit)")
    if which == "g5-rw":
        for b in sorted(spl, key=lambda b: (spl[b], b)):
            preds.append(("@split", spl[b].replace(" ", "_"), D.hx(b), "sha256 of 'r5' + the word's 4 little-endian bytes, lower 30 FIT", "table"))
        preds.append(("@g5-rw", "hmant_rule", "held iff controls pass and 42 of 42 m words equal R4's delta; one miss refutes unless "
                      "a replicate differs from R4 (then not deterministic: cannot tell)", "plan 4", "heldout"))
        preds.append(("@g5-rw", "shape_stop", "a table job without 3 vertices at the frozen window is FAILED shape; three void the table",
                      "plan 4", "table"))
    head = {"g5-rwa": """Q230 (geometry), g5-rw part a: 6 controls (R4's rw-k0..k3 programs, the known words exact; rw-k4 w 0.3 S 1/4 RZ, rw-k5 w 0.7 S
1/2 RZ + 1 in the new template) then R4's six quarter jobs q-15..q-20 with x and y scaled by 1/4 (vtx_zws.s: inside the viewport).
Gate before part b: every control word exact and fewer than three q jobs FAILED shape.""",
            "g5-rw": """Q230 (geometry), g5-rw part b: H-MANT (word - RZ follows the mantissa of w): m-01..m-07 = R4's rw-01..07 at scale 1/2, m-08..m-14 =
R4's rw-08..14 at scale 16 (42 words, R4's delta frozen, 11 of them RZ + 1); replicates rw-07, rw-10 (R4's programs: R4's six words);
the dense table d-01..d-20 (60 new mantissas: 1 + k/64 for odd k, 8 hashed, 20 derived; scales 1/4 to 4), FIT / HELD OUT split
frozen by sha256 for a later fit."""}[which]
    return rows, preds, list(dict.fromkeys(needs)), head


def build():
    return build_stage("g5-rwa")


if __name__ == "__main__":
    for st in ("g5-rwa", "g5-rw"):
        r, p, n, h = build_stage(st)
        K.write_table(st, r, n, h)
        K.write_preds(st, p)
        print(f"{st}: {len(r)} jobs, {len(p)} prediction rows, {len(n)} programs")
