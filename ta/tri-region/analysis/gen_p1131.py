#!/usr/bin/env python3
"""Writes the 11.31 laptop batch under p1131/: the probe table and templates, the case tables of
the scripts, declared.tsv and predictions-declared.tsv (declared before any run, hashed in the
plan). `python3 -B gen/gen_p1131.py` from p1131/. Reads nothing from the repositories."""
from __future__ import annotations

import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import models as M  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
GREEN = '"$S/p1131-green__0.bin"'
BLUE = '"$S/p1131-blue__0.bin"'
DUMP = '--dump-render "$W/dump"'
cases: list[dict] = []
preds: list[tuple] = []


def add(script, name, sset, w, h, args, **meta):
    assert all(c["name"] != name for c in cases), name
    cases.append(dict(script=script, name=name, set=sset, w=w, h=h, args=" ".join(args), **meta))


def pred(name, quantity, value, model):
    preds.append((name, quantity, value, model))


def fmt_regions(d):
    return ";".join("%d:%d:%s" % (x, y, v if isinstance(v, str) else "".join(map(str, v)))
                    for (x, y), v in sorted(d.items(), key=lambda kv: (kv[0][1], kv[0][0])))


# ---------------------------------------------------------------- Q070 A: object format
def gen_format():
    sc = "ta-object-format"
    def job(name, sset, n, cs, cf):
        a = ["probe", "--tri", "pixpds:12", "--temps", "32", "--pixels", "--width", "64", "--height", "64",
             "--vtx-coords", str(n), "--blk", "16=%d" % cs, "--blk", "17=%d" % cf, DUMP,
             '--slot "pixel=$S/pix_pa0.bin"', '--slot "vtxuse=$S/vtx_c%d.bin"' % n, '"$S/p1131-fmt-%d__0.bin"' % n]
        add(sc, name, sset, 64, 64, a, kind="fmt", n=n, cs=cs, cf=cf)
        st, it, mk = M.object_format(n, cs, cf)
        pred(name, "stored_dwords", st, "H70-F")
        pred(name, "iterated_dwords", it, "H70-F")
        pred(name, "masks", ",".join("%x" % x for x in mk), "H70-M")
    # fit: the landed settings (E308: coordinate size 1..5, format 0, 1 and 3, N = 4), rerun once each
    for cs, cf in ((1, 0), (3, 0), (5, 0), (5, 1), (18, 3)):
        job("fmt-fit-n4-cs%d-cf%d" % (cs, cf), "fit", 4, cs, cf)
    for n in (2, 3, 5, 6, 8, 9, 11):
        m = -(-n // 4)
        def word(sizes):
            return sum(s << (3 * i) for i, s in enumerate(sizes[:m]))
        cyc = [1, 3, 4, 5]
        opts = [("s1", word([1] * m), 0), ("s3", word([3] * m), 0), ("s5", word([5] * m), 0),
                ("mix", word(cyc), 0), ("f1", word([2] * m), (1 << m) - 1),
                ("alt", word([5, 3, 1]), 0b101 if m > 1 else 1)]
        for tag, cs, cf in opts:
            job("fmt-n%d-%s" % (n, tag), "heldout", n, cs, cf)


# ---------------------------------------------------------------- lines and points
def line_job(name, sset, w, h, ox, sx, oy, sy, nv, nidx, width=None, pixels=False):
    a = ["probe", "--tri", "pixel", "--temps", "32", "--width", str(w), "--height", str(h)]
    if nv != 3:
        a += ["--vertices", str(nv)]
    a += ["--blk 1=0x01d08200"] + M.vp_args(ox, sx, oy, sy)
    if width is not None:
        a += ["--blk 2=0x%08x" % (width << 8 | 0xf0)]
    a += ["--vdm", "2=0x%08x" % (0x84c00000 | nidx)]
    if pixels:
        a += ["--pixels"]
    a += [DUMP, GREEN]
    add("ta-line-point", name, sset, w, h, a, kind="line", geom=(w, h, ox, sx, oy, sy, nv), nidx=nidx,
        width=width if width is not None else 0x10)
    v = M.vertices(w, h, ox, sx, oy, sy, nv)
    nl = nidx // 2
    lr = M.line_regions(v, nl, w, h)
    pred(name, "regions", ";".join("%d:%d:%s" % (x, y, "+".join(map(str, hit)))
                                   for (x, y), hit in sorted(lr.items(), key=lambda kv: (kv[0][1], kv[0][0]))), "H70-L2")
    if nl == 1:
        pred(name, "forms", "all 0x90", "H70-L1")


def point_job(name, sset, w, h, ox, sx, oy, sy, nv, width=None, pixels=False, vtxuse=None):
    """Points (index list type 2, ISP word 0 with 0x18000); vtxuse: the file of a vertex program that
    writes the size to the one coordinate output (--vtx-coords 1), the case's main program."""
    a = ["probe", "--tri", "vtxuse" if vtxuse else "pixel", "--temps", "32", "--width", str(w), "--height", str(h)]
    if nv != 3:
        a += ["--vertices", str(nv)]
    a += ["--blk 1=0x01d18200"] + M.vp_args(ox, sx, oy, sy)
    if width is not None:
        a += ["--blk 2=0x%08x" % (width << 8 | 0xf0)]
    a += ["--vdm", "2=0x%08x" % (0x88c00000 | nv)]
    if vtxuse:
        a += ["--vtx-coords", "1", '--slot "pixel=$S/p1131-green__0.bin"']
    if pixels:
        a += ["--pixels"]
    a += [DUMP, vtxuse or GREEN]
    wd = width if width is not None else 0x10
    add("ta-line-point", name, sset, w, h, a, kind="point", geom=(w, h, ox, sx, oy, sy, nv), width=wd,
        vtxuse=bool(vtxuse))
    v = M.vertices(w, h, ox, sx, oy, sy, nv)
    pred(name, "regions", fmt_regions(M.point_regions(v, nv, w, h)), "H70-P0")
    if pixels and not vtxuse:
        pred(name, "pixels", M.point_pixels(v, nv, wd, w, h), "H117-W")


def gen_lines_points():
    # landed geometry at 64 x 64 (E181): fit, rerun
    for r in (1, 2):
        line_job("ln-ctl64-r%d" % r, "fit", 64, 64, 32, 32, 32, 32, 3, 2, pixels=True)
    line_job("ln-ctl64-two", "fit", 64, 64, 32, 32, 32, 32, 6, 4)
    # horizontal-ish segment (y scale 1/2) round the row boundary at y = 16, two widths
    for tag, oy in (("a", 16.125), ("b", 16.1875), ("c", 16.3125), ("d", 16.375), ("e", 16.5625)):
        for wd in (0x10, 0x40):
            line_job("ln-row-%s-w%02x" % (tag, wd), "heldout", 128, 128, 64, 32, oy, 0.5, 3, 2, width=wd)
    # near-vertical segment (x scale 1/2): the tile line at x = 16 and the region line at x = 32
    for tag, ox in (("a", 8.375), ("b", 24.375), ("c", 32.375), ("d", 31.8125)):
        for wd in (0x10, 0x40):
            line_job("ln-col-%s-w%02x" % (tag, wd), "heldout", 128, 128, ox, 0.5, 48, 32, 3, 2, width=wd)
    # several lines in one object: masks and forms
    line_job("ln-two128", "heldout", 128, 128, 64, 64, 64, 64, 6, 4)
    line_job("ln-three128", "heldout", 128, 128, 64, 64, 64, 64, 6, 6)
    line_job("ln-two128-shift", "heldout", 128, 128, 80, 64, 64, 64, 6, 4)
    line_job("ln-three64", "heldout", 64, 64, 32, 32, 32, 32, 6, 6)
    line_job("ln-two128-w40", "heldout", 128, 128, 64, 64, 64, 64, 6, 4, width=0x40)
    # points: landed geometry (E181), then the boundaries with the copies' 1/16 step
    point_job("pt-ctl64", "fit", 64, 64, 32, 32, 32, 32, 3, pixels=True)
    point_job("pt-ctl128", "heldout", 128, 128, 64, 64, 64, 64, 3, pixels=True)
    e = 1 / 16
    for tag, (vx, vy) in (("16m", (16 - e, 16 - e)), ("16", (16.0, 16.0)), ("c32m", (32 - e, 16 - e)),
                          ("c32", (32.0, 16.0)), ("d32m", (32 - e, 32 - e)), ("d32", (32.0, 32.0)),
                          ("e48m", (48 - e, 32 - e)), ("e48", (48.0, 32.0))):
        point_job("pt-b-%s" % tag, "heldout", 128, 128, vx + 48, 64, vy + 48, 64, 6)
    for wd in (0x20, 0x40, 0x80, 0xf0):
        point_job("pt-w%02x-64" % wd, "heldout", 64, 64, 32, 32, 32, 32, 3, width=wd)
    # footprints (Q117): centres and corners of pixels, ISP word 1 bits 15:8 (width / 16 pixels)
    for wd in (0x10, 0x20, 0x40):
        point_job("pt-f-c-w%02x" % wd, "fit", 64, 64, 22.5, 16, 22.5, 16, 3, width=wd, pixels=True)
    for wd in (0x00, 0x08, 0x80, 0xf0):
        point_job("pt-f-c-w%02x" % wd, "heldout", 64, 64, 22.5, 16, 22.5, 16, 3, width=wd, pixels=True)
    for wd in (0x10, 0x20, 0x40, 0x80, 0xf0):
        point_job("pt-f-k-w%02x" % wd, "heldout", 64, 64, 22.0, 16, 22.0, 16, 3, width=wd, pixels=True)
    # the vertex output row as a size (no OUTSEL change): 1.0 and 8.0 at the centre placement
    for i, val in ((0, 1.0), (1, 8.0)):
        point_job("pt-o-c-s%d" % int(val), "heldout", 64, 64, 22.5, 16, 22.5, 16, 3, width=0x10, pixels=True,
                  vtxuse='"$S/p1131-psize__%d.bin"' % i)


# ---------------------------------------------------------------- Q070 C: triangle boundaries
def tri_job(name, sset, w, h, ox, sx, oy, sy, nv, pixels=False, tag=""):
    a = ["probe", "--tri", "pixel", "--temps", "32", "--width", str(w), "--height", str(h)]
    if nv != 3:
        a += ["--vertices", str(nv)]
    a += M.vp_args(ox, sx, oy, sy)
    if pixels:
        a += ["--pixels"]
    a += [DUMP, GREEN]
    add("ta-tri-boundary", name, sset, w, h, a, kind="tri", geom=(w, h, ox, sx, oy, sy, nv))
    v = M.vertices(w, h, ox, sx, oy, sy, nv)
    pred(name, "regions", fmt_regions(M.tri_classes(v, w, h)), "H70-T1")


def gen_tri():
    e = 1 / 16
    for r in (1, 2):
        tri_job("tb-ctl-e180a-r%d" % r, "fit", 128, 128, 64, 64, 64, 64, 3, pixels=True)
    tri_job("tb-ctl-e180b", "fit", 128, 128, 78, 64, 64, 64, 3)
    # five copies (the copy c moves c/16 pixel right and down, so the viewport scale is W/2):
    # vertex 0 or 1 placed 2/16 before the boundary, the five copies at -2/16 ... +2/16
    for w in (64, 128, 256):
        s = w / 2
        for (bx, by) in ((16, 16), (32, 16), (32, 32), (16, 32)):
            for k in (0, 1):
                vx, vy = bx - 2 * e, by - 2 * e
                ox = vx - NDCX[k] * s
                oy = vy - NDCY[k] * s
                tri_job("tb-w%d-k%d-%d-%d" % (w, k, bx, by), "fit" if (w == 128 and k == 0 and (bx, by) == (16, 16)) else "heldout",
                        w, w, ox, s, oy, s, 15)


NDCX = [-0.75, 0.75, -0.375]
NDCY = [-0.75, -0.375, 0.75]



# ---------------------------------------------------------------- Q070 C, the cases that need `--tri-v`
def edge_job(name, sset, w, h, v16):
    """The first triangle with its vertices at v16 (1/16 pixel units, 3 of them): needs the tool
    change of tool-tests/test_cli_tri_probe_vertices.py (probe --tri ... --tri-v I=X,Y)."""
    a = ["probe", "--tri", "pixel", "--temps", "32", "--width", str(w), "--height", str(h)]
    for i, (x, y) in enumerate(v16):
        a += ["--tri-v", "%d=%d,%d" % (i, x, y)]
    a += [DUMP, GREEN]
    add("ta-tri-edges", name, sset, w, h, a, kind="tri", geom=None, v16=v16)
    v = [(x / 16, y / 16) for x, y in v16]
    pred(name, "regions", fmt_regions(M.tri_classes(v, w, h)), "H70-T1")


def gen_edges():
    e = 1
    # vertical edges on the region line x = 32 and the tile line x = 16 (and 1/16 either side),
    # horizontal edges on the row line y = 16 and 32 (and 1/16 either side), 128 x 128
    for tag, d in (("m", -e), ("0", 0), ("p", e)):
        for line in (16, 32):
            x = line * 16 + d
            edge_job("te-vert%d%s" % (line, tag), "heldout", 128, 128, [(x, 20 * 16), (x, 60 * 16), (80 * 16, 40 * 16)])
            edge_job("te-vertr%d%s" % (line, tag), "heldout", 128, 128, [(x, 20 * 16), (x, 60 * 16), (6 * 16, 40 * 16)])
        for line in (16, 32):
            y = line * 16 + d
            edge_job("te-horiz%d%s" % (line, tag), "heldout", 128, 128, [(20 * 16, y), (70 * 16, y), (40 * 16, 90 * 16)])
            edge_job("te-horizu%d%s" % (line, tag), "heldout", 128, 128, [(20 * 16, y), (70 * 16, y), (40 * 16, 6 * 16)])

# ---------------------------------------------------------------- Q047
BASE = 0x0a022405


def state_job(sc, name, sset, block, word, mode, run):
    """block 2: the second block's word 9 changed, the second object carrying the marks; block 1: the
    first block's word 1 changed with the first object carrying them. mode: 'xor' or 'set'."""
    a = ["probe", "--tri", "pixel", "--temps", "32", "--pixels", "--width", "64", "--height", "64", "--vertices", "12"]
    if block == 2:
        a += ["--obj2 6", "--obj2-blk 6=0x42400000", "--obj2-blk 2=0x000020f0"]
    else:
        a += ["--blk 6=0x42400000", "--blk 2=0x000020f0", "--obj2 6", "--obj2-blk 6=0x42000000",
              "--obj2-blk 2=0x000010f0"]
    a += ['--obj2-pixel "$S/p1131-green__0.bin"', DUMP]
    idx = 9 if block == 2 else 1
    if word is not None:
        a += ["--vdm", "%d%s=0x%08x" % (idx, "^" if mode == "xor" else "", word)]
    a += [BLUE]
    add(sc, name, sset, 64, 64, a, kind="state", block=block, word=word, mode=mode, run=run)


def field_xor(shift, base_v, v):
    return (base_v ^ v) << shift


STATE_SAFE = [("ctl", None, None, "PPP"), ("b8", "xor", 0x100, "PPP")] + \
    [("b119-%d" % v, "xor", field_xor(9, 2, v), "AAA" if v == 0 else "PPP") for v in (0, 3, 4, 5)] + \
    [("b1513-%d" % v, "xor", field_xor(13, 1, v), "PPP") for v in (2, 3, 4)]
STATE_RISKY = [("b119-%d" % v, "xor", field_xor(9, 2, v), "H" if v in (1, 6) else "?") for v in (1, 6, 7)] + \
    [("b1513-%d" % v, "xor", field_xor(13, 1, v), "H") for v in (0, 5, 6, 7)] + \
    [("b17", "xor", 0x20000, "APP"), ("b25", "xor", 0x02000000, "PPP"),
     ("formA", "set", 0x0800e105, "AAA"), ("formB", "set", 0x08002505 & ~0, "APP")]


def gen_state():
    for blk in (2, 1):
        for (tag, mode, word, exp) in STATE_SAFE:
            for run in (1, 2):
                nm = "st-b%d-%s-r%d" % (blk, tag, run)
                state_job("vdm-state-units", nm, "control" if tag == "ctl" else "heldout", blk, word, mode, run)
                if blk == 1 and tag.startswith("b119-1"):
                    pass
                pred(nm, "markers", exp, "H47-N+17")
    for blk in (2, 1):
        for (tag, mode, word, exp) in STATE_RISKY:
            for run in (1, 2):
                nm = "st-b%d-%s-r%d" % (blk, tag, run)
                e = exp
                if blk == 1 and tag in ("b119-1",):
                    e = "PPP"          # E427: bits 11:9 at 1 complete in the first block
                state_job("vdm-state-risky", nm, "heldout", blk, word, mode, run)
                pred(nm, "markers", e, "H47-N+17")
        # a control between the blocks of risky jobs keeps E413's alternation honest
        state_job("vdm-state-risky", "st-b%d-ctl-r3" % blk, "control", blk, None, "xor", 3)
        pred("st-b%d-ctl-r3" % blk, "markers", "PPP", "H47-N+17")
    # attribute rows (7:0) against bits 11:9 on the second block, one run each
    for rows in (1, 2, 3, 8):
        for v in range(8):
            word = (BASE & ~0xe00 & ~0xff) | (v << 9) | rows
            nm = "st-grid-r%d-v%d" % (rows, v)
            state_job("vdm-state-risky", nm, "heldout", 2, word, "set", 1)
            pred(nm, "completes", "yes" if v in (2, 3, 4, 5) else "no" if v in (1, 6) else "alt" if v == 7 else "obj2 absent", "H47-P0")


# ---------------------------------------------------------------- Q094 / Q092
def gen_vtask():
    sc = "vdm-vtask"
    for n in (2, 4, 8, 11):
        for f in (15, 13, 9, 7, 2, 3, 1):
            a = ["probe", "--tri", "pixpds:12", "--temps", "32", "--width", "64", "--height", "64", "--vertices", "126",
                 "--vtx-coords", str(n)]
            if f != 15:
                a += ["--vdm", "6^=0x%08x" % ((15 ^ f) << 28)]
            a += [DUMP, '--slot "pixel=$S/pix_pa0.bin"', '--slot "vtxuse=$S/vtx_c%d.bin"' % n,
                  '"$S/p1131-fmt-%d__0.bin"' % n]
            nm = "vt-n%d-f%d" % (n, f)
            add(sc, nm, "fit" if f == 15 else "heldout", 64, 64, a, kind="vtask", n=n, f=f)
            pred(nm, "ids_found", 126, "H94-none")
    # Q092: the first trailing word's top nibble against the task's attribute rows, five copies
    sc = "vdm-vtask-risky"
    for nib in (0xf, 0xd, 0x7):
        for rows in (1, 2, 4):
            a = ["probe", "--tri", "pixel", "--temps", "32", "--width", "64", "--height", "64", "--vertices", "15",
                 "--vdm", "4=0x%08x" % (nib << 28), "--vdm", "7^=0x%08x" % ((1 ^ rows) << 7), DUMP, GREEN]
            nm = "q92-nib%x-rows%d" % (nib, rows)
            add(sc, nm, "control" if (nib, rows) == (0xf, 1) else "heldout", 64, 64, a, kind="q92", nib=nib, rows=rows)
            pred(nm, "object_equals_control", "yes", "H92-none")


# ---------------------------------------------------------------- risky: OUTSEL flips, point size output
def gen_risky_ta():
    sc = "ta-risky"
    for k in (11, 12, 8, 9, 10, 13, 14, 15, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31):
        a = ["probe", "--tri", "pixel", "--temps", "32", "--width", "64", "--height", "64", "--blk", "13^=0x%08x" % (1 << k), DUMP, GREEN]
        nm = "of-outsel-b%d" % k
        add(sc, nm, "fit" if k in (11, 12) else "heldout", 64, 64, a, kind="outsel", bit=k)
        fmtw = {11: "0x000c0101", 12: "0x00000101"}.get(k, "0x00040101")
        pred(nm, "format_word", fmtw, "H70-O")
    for k in (8, 9, 10, 14, 15, 20, 21, 22, 23):
        for i, val in ((0, 1.0), (1, 8.0)):
            a = ["probe", "--tri", "vtxuse", "--temps", "32", "--pixels", "--width", "64", "--height", "64",
                 "--vtx-coords", "1", "--blk 1=0x01d18200", "--blk 13^=0x%08x" % (1 << k)] + \
                M.vp_args(22.5, 16, 22.5, 16) + ["--vdm", "2=0x88c00003", '--slot "pixel=$S/p1131-green__0.bin"', DUMP,
                                                  '"$S/p1131-psize__%d.bin"' % i]
            nm = "ps-outsel-b%d-s%d" % (k, int(val))
            add(sc, nm, "heldout", 64, 64, a, kind="psize", bit=k, size=val)
            pred(nm, "pixels_equal_for_sizes", "yes", "H117-O0")


def write_all():
    out = ROOT
    by_script: dict[str, list[dict]] = {}
    for c in cases:
        by_script.setdefault(c["script"], []).append(c)
    for sc, cs in by_script.items():
        table = "\n".join("%s|%s|%d|%d|%s" % (c["name"], c["set"], c["w"], c["h"], c["args"]) for c in cs)
        (out / "gen" / ("table-%s.txt" % sc)).write_text(table + "\n")
    with open(out / "declared.tsv", "w") as f:
        f.write("name\tscript\tset\tW\tH\n")
        for c in cases:
            f.write("%s\t%s\t%s\t%d\t%d\n" % (c["name"], c["script"], c["set"], c["w"], c["h"]))
    with open(out / "predictions-declared.tsv", "w") as f:
        f.write("name\tquantity\tpredicted\tmodel\n")
        for p in preds + EVENT_PREDS:
            f.write("%s\t%s\t%s\t%s\n" % tuple(map(str, p)))
    return by_script


# ---------------------------------------------------------------- Q111 predictions (static)
TA_BITS = {12: "Y", 13: "Y", 18: "Y", 0: "Y"}
EVENT_PREDS: list[tuple] = []


def gen_events():
    stat = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28]
    for kind in ("tri64", "fill"):
        for b in stat:
            if kind in ("fill", "copy"):
                v = "N" if b in (12, 13, 18, 23, 1, 2, 3, 25, 28) else "?"
            elif kind == "partial":
                v = "Y" if b in (12, 13, 18) else "?" if b in (0, 1, 2, 3, 25, 4, 22, 23, 24) else "N"
            elif kind == "zstore":
                v = "Y" if b in (12, 13, 18, 0) else "?" if b in (21, 23, 10, 11, 22, 24) else "N"
            else:
                v = "Y" if b in (12, 13, 18, 0) else "?" if b in (23, 24, 10, 11, 22, 21, 19, 20, 26) else "N"
            EVENT_PREDS.append(("irq-%s-st%d" % (kind, b), "extra_interrupt", v, "H111-fw"))
    for kind in ("tri64", "fill"):
        for b in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15):
            EVENT_PREDS.append(("irq-%s-st2b%d" % (kind, b), "extra_interrupt", "?" if b in (12,) else "N", "H111-fw"))
    for kind in ("tri64", "fill"):
        EVENT_PREDS.append(("irq-%s-none" % kind, "extra_interrupt", "N", "H111-ctl"))


if __name__ == "__main__":
    gen_format()
    gen_lines_points()
    gen_tri()
    gen_state()
    gen_vtask()
    gen_risky_ta()
    gen_events()
    by = write_all()
    for sc, cs in by.items():
        print("%-18s %3d jobs" % (sc, len(cs)))
    print("total", len(cases), "jobs;", len(preds) + len(EVENT_PREDS), "predictions")
