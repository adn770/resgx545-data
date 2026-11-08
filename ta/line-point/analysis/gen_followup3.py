#!/usr/bin/env python3
"""Third follow-up of 11.31, declared after ta-risky showed that OUTSEL bit 8 with a vertex output
makes points draw (3 pixels at size 1.0, 192 at size 8.0 of 3 points: 8 x 8 squares round the vertex)
and before ta-points runs. H117-S1: with OUTSEL bit 8 set, a point's size S is the first coordinate
output dword of its vertex (o4, as a float, in pixels); the point covers the pixels whose centre lies in
[v - S/2, v + S/2) in x and in y (low side closed, high side open), S taken in sixteenths (12.4); sizes
under 1/16 cover nothing; larger sizes follow the same rule up to the target. H70-P1: a point's tile
list: the tile [tx, tx + 16) x [ty, ty + 16) is listed iff [v - S/2, v + S/2] (closed at both ends) meets
it with the tile's high side open. H117-R: the size is read from o4 and not o5 (psize2). Fit: the one
case of ta-risky (S = 8, S = 1, centres); everything below is held out. Writes templates/vtx_psize2.s,
programs in p1131-progs.toml, declared-followup3.tsv, predictions-followup3.tsv, ta-points.sh."""
import pathlib, struct, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import models as M

ROOT = pathlib.Path(__file__).resolve().parent.parent
SIZES = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 11.0, 12.0, 16.0, 20.0, 24.0, 32.0, 48.0, 63.0, 64.0, 100.0, 255.0, 256.0, 0.0625, 0.03125, 0.0]
NEG = [-4.0]
fb = lambda f: "0x%08X" % struct.unpack("<I", struct.pack("<f", f))[0]
pairs = [(2.0, 6.0), (6.0, 2.0)]
# programs
(ROOT / "templates" / "vtx_psize2.s").write_text("""; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; The triangle's vertex shader with two coordinate outputs (slot vtxuse, --vtx-coords 2) holding the
; case's A and B as floats in o4 and o5: which of them a point reads as its size (Q117). The second
; phase at #8.
        phas #8, #0, pixel, vcull, parallel
        nop.nosched
        and.skipinv.testtanz.chan0 !r0, p0, #0x00000000, #0
        p0 ldad.skipinv.fetch4 pa0, [pa0,+#0], drc0
        wdf drc0
        mov.skipinv.repeat4 o0, pa0                     ; o0-o3 = x, y, z, w
        mov.skipinv o4, #{A}                            ; o4 = A
        mov.skipinv o5, #{B}                            ; o5 = B
        emitvcbvtx.end.twopart #0, #0
        phas #0, #0, pixel, end, parallel
        emitmtevtx.end.twopart.freep #0, #0, #0
""")
toml = (ROOT / "p1131-progs.toml").read_text()
if "p1131-psizes" not in toml:
    allsz = SIZES + NEG
    toml += """
[[probe]]
name = "p1131-psizes"
question = "a vertex shader writing the case's size to the one coordinate output (as a float), 28 sizes"
source = "vtx_psize.s"
host = "tri"
slot = "vtxuse"
slots = { pixel = "pix_green.s" }
size = [64, 64]
pixels = true
inputs = ["V"]
labels = [%s]
cases = [%s]

[[probe]]
name = "p1131-psize2"
question = "a vertex shader writing A to o4 and B to o5 (two coordinate outputs)"
source = "vtx_psize2.s"
host = "tri"
slot = "vtxuse"
slots = { pixel = "pix_green.s" }
size = [64, 64]
pixels = true
inputs = ["A", "B"]
labels = [%s]
cases = [%s]
""" % (", ".join('"%g"' % s for s in allsz), ", ".join("[%s]" % fb(s) for s in allsz),
       ", ".join('"%g/%g"' % p for p in pairs), ", ".join("[%s, %s]" % (fb(a), fb(b)) for a, b in pairs))
    (ROOT / "p1131-progs.toml").write_text(toml)

cases, preds = [], []
def covered(v, s, w, h):
    s = int(s * 16) / 16.0
    px = set()
    for (x, y) in v:
        for i in range(w):
            if x - s / 2 <= i + 0.5 < x + s / 2:
                for j in range(h):
                    if y - s / 2 <= j + 0.5 < y + s / 2:
                        px.add((i, j))
    return px
def tiles(v, s, w, h):
    s = int(s * 16) / 16.0
    out = []
    for ty in range(0, h, 16):
        for tx in range(0, w, 16):
            ps = [p for p, (x, y) in enumerate(v) if x + s / 2 >= tx and x - s / 2 < tx + 16 and y + s / 2 >= ty and y - s / 2 < ty + 16]
            if s >= 1 / 16 and ps:
                out.append("%d:%d:%s" % (tx, ty, "".join(map(str, ps))))
    return ";".join(out)
def job(name, ox, oy, sx, sy, prog, nco, extra=()):
    a = ["probe", "--tri", "vtxuse", "--temps", "32", "--pixels", "--width", "64", "--height", "64", "--vtx-coords", str(nco),
         "--blk 1=0x01d18200", "--blk 13^=0x00000100"] + list(extra) + M.vp_args(ox, sx, oy, sy) + \
        ["--vdm", "2=0x88c00003", '--slot "pixel=$S/p1131-green__0.bin"', '--dump-render "$W/dump"', '"$S/%s"' % prog]
    cases.append((name, "heldout" if True else "fit", 64, 64, " ".join(a)))
    return M.vertices(64, 64, ox, sx, oy, sy, 3)
allsz = SIZES + NEG
def idx(s): return allsz.index(s)
for s in SIZES:
    v = job("pp-c-s%g" % s, 22.5, 22.5, 16, 16, "p1131-psizes__%d.bin" % idx(s), 1)
    preds += [("pp-c-s%g" % s, "pixels", str(len(covered(v, s, 64, 64))), "H117-S1"), ("pp-c-s%g" % s, "tile_prims", tiles(v, s, 64, 64), "H70-P1")]
for s in (1.0, 2.0, 3.0, 4.0, 5.0, 8.0, 16.0):
    v = job("pp-k-s%g" % s, 22.0, 22.0, 16, 16, "p1131-psizes__%d.bin" % idx(s), 1)
    preds += [("pp-k-s%g" % s, "pixels", str(len(covered(v, s, 64, 64))), "H117-S1"), ("pp-k-s%g" % s, "tile_prims", tiles(v, s, 64, 64), "H70-P1")]
for s in (1.0, 2.0, 3.0, 4.5 if False else 4.0, 8.0, 11.0):
    v = job("pp-f-s%g" % s, 22.3125, 22.1875, 16, 16, "p1131-psizes__%d.bin" % idx(s), 1)
    preds += [("pp-f-s%g" % s, "pixels", str(len(covered(v, s, 64, 64))), "H117-S1"), ("pp-f-s%g" % s, "tile_prims", tiles(v, s, 64, 64), "H70-P1")]
# size 11 at the pixel-centre placement: the high end 16.0 is a tile line; size 9: 15.0; size 12: 16.5
# the ISP word 1 width with a size row: no effect predicted
v = job("pp-c-s4-w80", 22.5, 22.5, 16, 16, "p1131-psizes__%d.bin" % idx(4.0), 1, extra=["--blk 2=0x000080f0"])
preds += [("pp-c-s4-w80", "pixels", str(len(covered(v, 4.0, 64, 64))), "H117-S1")]
# which row
for k, (a_, b_) in enumerate(pairs):
    v = job("pp2-c-%g-%g" % (a_, b_), 22.5, 22.5, 16, 16, "p1131-psize2__%d.bin" % k, 2)
    preds += [("pp2-c-%g-%g" % (a_, b_), "pixels", str(len(covered(v, a_, 64, 64))), "H117-R")]
# negative size, last
v = job("pp-c-s-4", 22.5, 22.5, 16, 16, "p1131-psizes__%d.bin" % idx(-4.0), 1)
preds += [("pp-c-s-4", "pixels", "0", "H117-S1")]
body = "\n".join("%s|heldout|%d|%d|%s" % c[:1] + c[2:4] + (c[4],) if False else "%s|heldout|64|64|%s" % (c[0], c[4]) for c in cases)
(ROOT / "declared-followup3.tsv").write_text("name\tscript\tset\tW\tH\n" + "".join("%s\tta-points\theldout\t64\t64\n" % c[0] for c in cases))
(ROOT / "predictions-followup3.tsv").write_text("name\tquantity\tpredicted\tmodel\n" + "".join("\t".join(p) + "\n" for p in preds))
src = (ROOT / "vdm-vtask2.sh").read_text().split("TABLE=$(cat <<'TABLE'")[0].replace("SCRIPT_NAME=vdm-vtask2", "SCRIPT_NAME=ta-points")
src = src.replace('for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do', 'for f in "$S"/p1131-green__0.bin "$S"/p1131-psizes__0.bin "$S"/p1131-psize2__0.bin; do')
tail = "TABLE\n)\nrun_table \"$TABLE\"\nhealth </dev/null || true\necho \"## end\"\n"
(ROOT / "ta-points.sh").write_text(src + "TABLE=$(cat <<'TABLE'\n" + body + "\n" + tail)
(ROOT / "gen" / "table-ta-points.txt").write_text(body + "\n")
print(len(cases), "cases", len(preds), "predictions")
