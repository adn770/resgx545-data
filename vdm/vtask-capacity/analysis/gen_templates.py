#!/usr/bin/env python3
"""Writes templates/vtx_c*.s (vertex programs with N coordinate outputs: o4, o5 = the vertex's clip x
and y, the rest distinct constants), templates/vtx_psize.s and p1131-progs.toml (what
stage-p1131.sh assembles). python3 -B gen/gen_templates.py from p1131/."""
import pathlib
import struct

ROOT = pathlib.Path(__file__).resolve().parent.parent
NS = (1, 2, 3, 4, 5, 6, 8, 9, 11)
HEAD = """; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; The triangle's vertex shader with {n} coordinate output dwords (slot vtxuse, --vtx-coords {n}):
; {what}. The second phase at #{k}. Written by gen/gen_templates.py in the form of
; probes/ta/templates/vtx_coord4.s.
        phas #{k}, #0, pixel, vcull, parallel
        nop.nosched
        and.skipinv.testtanz.chan0 !r0, p0, #0x00000000, #0
        p0 ldad.skipinv.fetch4 pa0, [pa0,+#0], drc0
        wdf drc0
        mov.skipinv.repeat4 o0, pa0                     ; o0-o3 = x, y, z, w
"""
TAIL = """        emitvcbvtx.end.twopart #0, #0
        phas #0, #0, pixel, end, parallel
        emitmtevtx.end.twopart.freep #0, #0, #0
"""


def f32(x):
    return "0x%08X" % struct.unpack("<I", struct.pack("<f", x))[0]


def vtx(n):
    body, k = "", 8
    if n == 1:
        body = "        mov.skipinv o4, pa0                             ; o4 = x\n"
        what = "o4 = the vertex's clip-space x"
    else:
        body = "        mov.skipinv.repeat2 o4, pa0                     ; o4, o5 = x, y\n"
        what = "o4, o5 = the vertex's clip-space x and y, o6 on constants %s" % ", ".join(f32(j / 8) for j in range(6, 4 + n))
        for j in range(6, 4 + n):
            body += "        mov.skipinv o%d, #%s\n" % (j, f32(j / 8))
        k = 8 + (n - 2)
    return HEAD.format(n=n, what=what, k=k) + body + TAIL


for n in NS:
    (ROOT / "templates" / ("vtx_c%d.s" % n)).write_text(vtx(n))
(ROOT / "templates" / "vtx_psize.s").write_text("""; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; The triangle's vertex shader with one coordinate output (slot vtxuse, --vtx-coords 1) holding the
; case's value V as a float: the size a point reads, if a vertex output is where a size comes from
; (Q117). The second phase at #8.
        phas #8, #0, pixel, vcull, parallel
        nop.nosched
        and.skipinv.testtanz.chan0 !r0, p0, #0x00000000, #0
        p0 ldad.skipinv.fetch4 pa0, [pa0,+#0], drc0
        wdf drc0
        mov.skipinv.repeat4 o0, pa0                     ; o0-o3 = x, y, z, w
        mov.skipinv o4, #{V}                            ; o4 = the size
        emitvcbvtx.end.twopart #0, #0
        phas #0, #0, pixel, end, parallel
        emitmtevtx.end.twopart.freep #0, #0, #0
""")
toml = ["# SPDX-License-Identifier: MIT", "# SPDX-FileCopyrightText: 2026 Josep Torra",
        "# p1131 progs: the program files of the 11.31 scripts (stage-p1131.sh builds and stages them; the",
        "# scripts give the render options themselves, one process per case). Written by",
        "# gen/gen_templates.py.", 'needs = ["render"]', ""]


def probe(name, q, source, slot, extra="", inputs="[]", cases="[[]]", labels='["one"]'):
    toml.extend(["[[probe]]", 'name = "%s"' % name, 'question = "%s"' % q, 'source = "%s"' % source,
                 'host = "tri"', 'slot = "%s"' % slot] + ([extra] if extra else []) +
                ["size = [64, 64]", "pixels = true", "inputs = %s" % inputs, "labels = %s" % labels,
                 "cases = %s" % cases, ""])


probe("p1131-green", "the plain green pixel shader", "pix_green.s", "pixel")
probe("p1131-blue", "a plain blue pixel shader (the first object's of the two-object streams)", "pix_op.s", "pixel",
      inputs='["OP"]', cases='[["mov.skipinv.end o0, #0xFF0000FF"]]')
for n in NS:
    probe("p1131-fmt-%d" % n, "the pixel PDS program of E437 with the pa0 shader and the vertex program of %d outputs" % n,
          "pds_iter_nofetch.s", "pixpds", extra='slots = { pixel = "pix_pa0.s", vtxuse = "vtx_c%d.s" }' % n,
          inputs='["A", "B", "U"]', cases="[[0x27000800, 0x0, 0x1000004]]", labels='["source 0"]')
probe("p1131-psize", "a vertex shader writing the case's size to the one coordinate output (as a float)", "vtx_psize.s",
      "vtxuse", extra='slots = { pixel = "pix_green.s" }', inputs='["V"]',
      cases="[[0x3F800000], [0x41000000]]", labels='["size 1.0", "size 8.0"]')
(ROOT / "p1131-progs.toml").write_text("\n".join(toml))
print("wrote", len(NS) + 1, "vertex templates, p1131-progs.toml")
