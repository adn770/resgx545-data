#!/usr/bin/env python3
"""Ninth follow-up of 11.31, declared after ta-points and before ta-points-vertex runs.
H117-V: each point reads its own vertex's size row: with a vertex program that writes o4 = K * c + B (c the
vertex's clip x or y, K = 16, B = 20: sizes 8, 32, 14 by x and 8, 14, 32 by y at the three vertices (clip x
-0.75, 0.75, -0.375; clip y -0.75, -0.375, 0.75)), the pixels covered are the union of the squares
[v - s/2, v + s/2) of each vertex with its own s (H117-S1 per vertex). Placements: pixel centres (22.5, scale
16: vertices (10.5, 10.5), (34.5, 16.5), (16.5, 34.5)) and corners (22.0). Four jobs."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import models as M
ROOT = pathlib.Path(__file__).resolve().parent.parent
(ROOT / "templates" / "vtx_psizev.s").write_text("""; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; The triangle's vertex shader with one coordinate output (slot vtxuse, --vtx-coords 1) holding 16 * C + 20
; (C the vertex's clip x or y, pa0 or pa1): a size that differs per vertex, if a point reads its own vertex's
; row (Q117). Temporaries r1-r3. The second phase at #11.
        phas #11, #0, pixel, vcull, parallel
        nop.nosched
        and.skipinv.testtanz.chan0 !r0, p0, #0x00000000, #0
        p0 ldad.skipinv.fetch4 pa0, [pa0,+#0], drc0
        wdf drc0
        mov.skipinv.repeat4 o0, pa0                     ; o0-o3 = x, y, z, w
        mov.skipinv r1, #0x41800000                     ; 16
        mov.skipinv r2, #0x41A00000                     ; 20
        fmad.skipinv r3, {C}, r1, r2                    ; 16 * C + 20
        mov.skipinv o4, r3                              ; o4 = the size
        emitvcbvtx.end.twopart #0, #0
        phas #0, #0, pixel, end, parallel
        emitmtevtx.end.twopart.freep #0, #0, #0
""")
toml = (ROOT / "p1131-progs.toml").read_text()
if "p1131-psizev" not in toml:
    toml += """
[[probe]]
name = "p1131-psizev"
question = "a vertex shader writing 16 * C + 20 to the one coordinate output, C = clip x (pa0) or clip y (pa1)"
source = "vtx_psizev.s"
host = "tri"
slot = "vtxuse"
slots = { pixel = "pix_green.s" }
size = [64, 64]
pixels = true
inputs = ["C"]
labels = ["by x", "by y"]
cases = [["pa0"], ["pa1"]]
"""
    (ROOT / "p1131-progs.toml").write_text(toml)
cases, preds = [], []
def covered(v, sizes, w, h):
    px = set()
    for (x, y), s in zip(v, sizes):
        s = int(s * 16) / 16.0
        for i in range(w):
            if x - s / 2 <= i + 0.5 < x + s / 2:
                for j in range(h):
                    if y - s / 2 <= j + 0.5 < y + s / 2:
                        px.add((i, j))
    return px
for name, prog, o, sizes in (("pv-x-c", 0, 22.5, (8, 32, 14)), ("pv-y-c", 1, 22.5, (8, 14, 32)), ("pv-x-k", 0, 22.0, (8, 32, 14)), ("pv-y-k", 1, 22.0, (8, 14, 32))):
    a = ["probe", "--tri", "vtxuse", "--temps", "32", "--pixels", "--width", "64", "--height", "64", "--vtx-coords", "1",
         "--blk 1=0x01d18200", "--blk 13^=0x00000100"] + M.vp_args(o, 16, o, 16) + \
        ["--vdm", "2=0x88c00003", '--slot "pixel=$S/p1131-green__0.bin"', '--dump-render "$W/dump"', '"$S/p1131-psizev__%d.bin"' % prog]
    cases.append("%s|heldout|64|64|%s" % (name, " ".join(a)))
    v = M.vertices(64, 64, o, 16, o, 16, 3)
    preds.append((name, "sizes", ",".join("%g" % s for s in sizes), "H117-V"))
    preds.append((name, "pixels", str(len(covered(v, sizes, 64, 64))), "H117-V"))
(ROOT / "declared-followup9.tsv").write_text("name\tscript\tset\tW\tH\n" + "".join("%s\tta-points-vertex\theldout\t64\t64\n" % c.split("|")[0] for c in cases))
(ROOT / "predictions-followup9.tsv").write_text("name\tquantity\tpredicted\tmodel\n" + "".join("\t".join(p) + "\n" for p in preds))
src = (ROOT / "vdm-vtask2.sh").read_text().split("TABLE=$(cat <<'TABLE'")[0].replace("SCRIPT_NAME=vdm-vtask2", "SCRIPT_NAME=ta-points-vertex")
src = src.replace('for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do', 'for f in "$S"/p1131-green__0.bin "$S"/p1131-psizev__0.bin "$S"/p1131-psizev__1.bin; do')
tail = "TABLE\n)\nrun_table \"$TABLE\"\nhealth </dev/null || true\necho \"## end\"\n"
(ROOT / "ta-points-vertex.sh").write_text(src + "TABLE=$(cat <<'TABLE'\n" + "\n".join(cases) + "\n" + tail)
(ROOT / "gen" / "table-ta-points-vertex.txt").write_text("\n".join(cases) + "\n")
print(len(cases), "cases")
