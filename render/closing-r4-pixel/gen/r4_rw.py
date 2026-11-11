# SPDX-License-Identifier: MIT
"""Stage g4-rw (Q230, the 1/w word): a table of w in R2's t3-nocut shape (vtx_zw.s, z = 0, w = C x + D, no clip), 24 jobs: 4
controls first, then 20 table jobs of three w each (60 w; 40 designed, 20 derived: see score/rwdesign.py).  Plan section 3.5.
Frozen per job: object present, 3 vertices in input order, window xy = 32 + 32 x / w, depth word 0x3f000000 (z = 0), every 1/w
word RZ or RZ + 1 of 1/w; controls: the words read in the kept data exact.  The 60 w are split 30 FIT / 30 HELD OUT by sha256 of
their bits (pseudo-case @split).  After the run the reciprocal families of score/rwfam.py are fitted on the FIT half and scored on
the HELD OUT half (score/score_rw.py).  Run alone:  RESGX545_MAIN=<tree> python gen/r4_rw.py"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import r4common as K  # noqa: E402
import rwdesign as D  # noqa: E402
from r4common import Row, build_bin  # noqa: E402

STOP = "stophang"
CMD = ('probe --temps 8 --pixels --tri vtxuse --width 64 --height 64 --vtx-coords 2 --dump-render "$W/dump" '
       '--slot "pixel=$S/pix_green.bin" "$S/{prog}.bin"')


def fmt_xy(w):
    return ";".join("%.6f,%.6f" % tuple(float(v) for v in D.window(i, w[i])) for i in range(3))


def build():
    rows, preds, needs = [], [], []
    green = build_bin("pix_green", (K.TEMPLATES / "pix_green.s").read_text())
    needs.append(green)
    tpl = (K.TEMPLATES / "vtx_zw.s").read_text()
    spl = D.split()

    def job(p, st, role):
        text = (tpl.replace("{A}", "0x00000000").replace("{B}", "0x00000000")
                .replace("{C}", D.hx(D.bits(p["C"]))).replace("{D}", D.hx(D.bits(p["D"]))))
        needs.append(build_bin(p["name"], text))
        rows.append(Row(p["name"], st, K.SAFE, STOP, "-", CMD.format(prog=p["name"]), role))
        P = lambda q, v, m: preds.append((p["name"], q, v, m, st))
        P("object", "present", "no clip: z = 0 is inside +-w (E782 t3-nocut)")
        P("nvert", "3", "nothing crosses a clip plane: 3 vertices in input order (E782 t3-nocut)")
        P("w_words", ",".join(D.hx(b) for b in p["words"]), "the exact w words of the three vertices (C x + D computed exactly)")
        P("xy_ordered", fmt_xy(p["w"]), "window = 32 + 32 x / w per vertex (E782), tolerance 1/32 pixel")
        P("depth_words", ",".join(["0x3f000000"] * 3), "z = 0: depth 0.5 whatever w (E782 t3-nocut)")
        P("rz_words", ",".join(D.hx(D.rz_word(b)) for b in p["words"]), "RZ of 1/w (frozen: every word is RZ or RZ + 1; 23 of 23 kept words)")
        return P

    for i in range(4):
        p = D.control_params(i)
        P = job(p, "control", f"control {p['name']}: w = {', '.join('%g' % float(x) for x in p['w'])} (C = {float(p['C'])}, D = {float(p['D'])})")
        P("rhw_known", ",".join(D.hx(b) if b is not None else "?" for b in p["known"]),
          "words read in the kept data (E754, E795, E796, E798: RZ at w = 1, 3, 7, 1.5; RZ + 1 at 9, 1.40625, 1.59375)")
    for i in range(20):
        p = D.job_params(i)
        job(p, "heldout", f"table job {i + 1}: scale {float(p['scale']):g}, w = {', '.join('%g' % float(x) for x in p['w'])}")
    for b in sorted(spl, key=lambda b: (spl[b], b)):
        preds.append(("@split", spl[b].replace(" ", "_"), D.hx(b), "sha256 of the word's 4 little-endian bytes, lower 30 FIT", "heldout"))
    head = """Q230 (geometry), g4-rw: a table of 60 w, three a job (w3 = 0.75 w1 + 0.25 w2 on the tool's triangle: two free, one derived),
in R2's t3-nocut shape (vtx_zw.s: z = 0, w = C x + D, no clip, window 32 + 32 x / w, vertices in input order).  C and D are chosen so
that every w is computed exactly in float32 (fused or not).  40 designed w: the 31 grid mantissas 1 + k/32 and 9 others with fine
low bits; a third of the jobs at scale 1, a third at 4, a third at 1/4.  Controls (4, first): w = 1; (3, 9, 4.5); (7, 10, 7.75);
(1.40625, 1.78125, 1.5): the known words exact.  Frozen: every word is RZ or RZ + 1 of 1/w; the 60 w split 30 FIT / 30 HELD OUT by the
sha256 of their bits.  After the run: the families of score/rwfam.py fitted on FIT, scored on HELD OUT; more than one family at 30 of
30 held out, or none: the words are recorded and no rule is adopted."""
    return rows, preds, list(dict.fromkeys(needs)), head


if __name__ == "__main__":
    r, p, n, h = build()
    K.write_table("g4-rw", r, n, h)
    K.write_preds("g4-rw", p)
    print(f"g4-rw: {len(r)} jobs, {len(p)} prediction rows, {len(n)} programs")
