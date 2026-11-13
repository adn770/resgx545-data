#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""lgen.py: write r8-lgeo's job tables (tables/STAGE.txt), frozen predictions (predictions/STAGE.tsv
and the per-row files under predictions/zs2/ and predictions/q139/), the probe programs (bins/,
bins/SHA256SUMS) and the fake laptop's program index (mock/progs.tsv) from the models (gen/
texmodel.py, gen/zsmodel.py, gen/q139model.py) and the published records' kept files, every one
read at the pinned resgx545-data commit (git show, never the working tree; session.toml [freeze]
pins lists them all: tests/test_gen.py checks it). Deterministic: a second run writes the same
bytes (tests/test_gen.py). Plan: closing8/leftovers/exp-leftovers-r8.md, session L2.

  python3 gen/lgen.py [OUT_DIR]     (default: this session; the test writes to a scratch copy)

Table line: name|set|risk|knobs|tool|args (tool t4 = ~/sgxfive-test-rgn4; $S the staged tree,
$W the job's work directory). Prediction line: case quantity value model set source.
The programs are assembled with usse-asm built from `git archive` of the pinned resgx545 commit
(tools/usse-asm, tools/usse-dis; debug/asm, tests/run_all.sh builds it)."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import gzip  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import shlex  # noqa: E402
import subprocess  # noqa: E402
import tomllib  # noqa: E402

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "kit"))
import q139model as Q  # noqa: E402
import scorekit  # noqa: E402
import texbuild as TB  # noqa: E402
import texcatalog as TC  # noqa: E402
import texmodel as T  # noqa: E402
import zsmodel as Z  # noqa: E402

DATA = "/Users/jtorra/src/resgx545-data"
ASM = os.path.join(KP, "debug/asm/tools/usse-asm/usse-asm")
R7G = "render/closing-r7-geo"
R7G_OUT = R7G + "/out/20261112-211113"
R7R = "render/closing-r7-rp"
R7R_OUT = R7R + "/out/20261112-205431"
MTF = ("ta/mtile-fields", "ta/mtile-fields-risky")
PINS = []           # every data path read (session.toml [freeze] pins must hold each as data:PATH)


def data_commit():
    with open(os.path.join(KP, "session.toml"), "rb") as f:
        return tomllib.load(f)["freeze"]["data"]


DC = data_commit()


def blob(path):
    """A resgx545-data file at the pinned commit."""
    if path not in PINS:
        PINS.append(path)
    return subprocess.run(["git", "-C", DATA, "show", "%s:%s" % (DC, path)], capture_output=True,
                          check=True).stdout


def gz_text(path):
    return gzip.decompress(blob(path)).decode(errors="replace")


ROWS, PREDS, CONTROLS, PROGS, FILES = {}, {}, [], {}, {}


def row(stage, name, sset, risk, knobs, tool, args):
    ROWS.setdefault(stage, []).append("%s|%s|%s|%s|%s|%s" % (name, sset, risk, knobs, tool, args))


def pred(stage, case, q, v, model, sset, source):
    PREDS.setdefault(stage, []).append((case, q, str(v), model, sset, source))


def control(stage, name, reads):
    CONTROLS.append((name, stage, tuple(reads)))


def pfile(rel, text):
    FILES[rel] = text


# ================================================================================ the programs
T0_REP, T0_BIL = TC.T0_REP, TC.T0_REP | 1 << 12 | 1 << 10      # point; bilinear (texcatalog.afilt)


def spec(ty, w, h, xo=0, yo=0, linear=False, stored=None, t0=T0_REP, fmt=12):
    u, v = TC.swin(w, h) if linear else TC.window(w, h, xo, yo)
    s = dict(base=0, t0=t0, t1=TC.t1tw(w, h, fmt, ty), t3=TC.T3_TW, u=u, v=v, ins="none")
    if stored:
        s["inject"] = {str(k): val for k, val in stored.items()}
    return s


def assemble(sp, name, out_dir):
    tmpl = open(os.path.join(KP, "templates/tx_map.s")).read()
    pre, setup, smp = TB.case_inputs(sp)
    text = tmpl.replace("{PRE}", pre).replace("{SETUP}", setup).replace("{SMP}", smp)
    out = os.path.join(out_dir, "bins", name + ".bin")
    r = subprocess.run([ASM, "-l", "-o", out, "-"], input=text, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(name + ": " + r.stderr)
    b = open(out, "rb").read()
    assert len(b) % 8 == 0 and len(b) // 8 <= 256, (name, len(b))
    return b


def prog(stage, name, out_dir, ty, w, h, *, xo=0, yo=0, linear=False, stored=None, t0=T0_REP, fmt=12,
         same_as=None, pages=None):
    """Assemble one probe program; same_as: a published program it must equal byte for byte."""
    sp = spec(ty, w, h, xo, yo, linear, stored, t0, fmt)
    b = assemble(sp, name, out_dir)
    if same_as:
        assert b == blob(same_as), (name, same_as)
    meta = dict(ty=ty, w=w, h=h, xo=xo, yo=yo, linear=linear, t0=t0, fmt=fmt,
                stored=sorted((int(k), v) for k, v in (stored or {}).items()))
    PROGS[hashlib.sha256(b).hexdigest()] = meta
    sp_opt = " --scratch-pages %d" % pages if pages else ""
    return "probe --temps 32 --coords --pixels%s \"$S/bins/%s.bin\"" % (sp_opt, name)


def kept_image(name):
    return T.probe_rows(gz_text("%s/tx/%s.txt.gz" % (R7G_OUT, name)))


# ================================================================================ tx3 (Q283)
TX_KNOBS = "after needrows"


def tx3(out_dir):
    st = "tx3"
    hyps = {3: ("H-MIN8", "H-2W", "RASTERW"), 1: ("RASTERW", "H-MIN8", "H-2W")}
    jobs = [("tx3-ctl-ty3-32x16", "control", 3, 32, 16, "tx-ctl-ty3-32x16", R7G + "/bins/r7g-ty3-32x16.bin", "E725"),
            ("tx3-ctl-ty3-4x16", "control", 3, 4, 16, "tx-ty3-4x16", R7G + "/bins/r7g-ty3-4x16.bin", "E910"),
            ("tx3-ctl-ty1-4x16", "control", 1, 4, 16, "tx-ty1-4x16", R7G + "/bins/r7g-ty1-4x16.bin", "E910")]
    for ty, sizes in ((3, ((2, 16), (4, 8), (4, 32), (2, 8), (1, 16))), (1, ((2, 16), (1, 16)))):
        for w, h in sizes:
            jobs.append(("tx3-ty%d-%dx%d" % (ty, w, h), "heldout", ty, w, h, None, None, None))
    for name, sset, ty, w, h, kname, same, src in jobs:
        args = prog(st, "r8l-ty%d-%dx%d" % (ty, w, h), out_dir, ty, w, h, same_as=same)
        knobs = TX_KNOBS + (" reads:rows" if sset == "control" else "")
        row(st, name, sset, "safe", knobs, "t4", args)
        pred(st, name, "size", "%dx%d" % (w, h), "all", sset, "table")
        pred(st, name, "type", ty, "all", sset, "table")
        for hy in hyps[ty]:
            pred(st, name, "pixels_sha", T.sha_list(T.tex_image(hy, w, h)), hy, sset, "gen/texmodel.py")
        if sset == "control":
            control(st, name, ("rows",))
            k = kept_image(kname)
            assert k and k == T.tex_image("RASTERW" if (ty, w) != (3, 4) else "H-MIN8", w, h), name
            pred(st, name, "pixels_sha", T.sha_list(k), "kept", sset, "%s %s/tx/%s.txt.gz" % (src, R7G_OUT, kname))
    return ["#stage tx3", "#limit 0",
            "# Q283 below 8 wide (E725, E910): E725's map-texture fill (64 x 32 pixels, texel (x mod w, y mod h), dword i of the",
            "# texture 0xD0000000 | i).  Type 3 at 2 x 16, 4 x 8, 4 x 32, 2 x 8, 1 x 16 and type 1 at 2 x 16, 1 x 16, held out.",
            "# Frozen: type 3 H-MIN8 (rows max(8, w) dwords apart; E910's 4 x 16, post hoc) against H-2W (2 w) and RASTERW (w);",
            "# type 1 RASTERW against H-MIN8 and H-2W.  Controls that can fail (kept images, reads:rows): E725's type 3 32 x 16",
            "# program byte for byte, E910's type 3 and type 1 4 x 16 programs byte for byte.  after: the health fill and triangle",
            "# after every job (E725's and E910's practice).  needrows: the second row with no pixel rows stops tx3 (rc 24).",
            "# No fault expected (E910's 18 jobs clean): any fault, hang or failure stops the stage (rc 4) and the session."]


# ================================================================================ tx4 (Q283)
def tx4(out_dir):
    st = "tx4"
    hyps = ("H-BLKROW", "H-BLKCOL", "H-BLKZ")
    jobs = [("tx4-ctl-ty4-64x32", "control", 64, 32, 0, 0, "tx-ty4-64x32", R7G + "/bins/r7g-ty4-64x32.bin"),
            ("tx4-ctl-ty4-4x16", "control", 4, 16, 0, 0, "tx-ty4-4x16", R7G + "/bins/r7g-ty4-4x16.bin")]
    wins = [(64, 64, 0, yo) for yo in (0, 32)] + [(128, 64, xo, yo) for yo in (0, 32) for xo in (0, 64)] + \
        [(128, 128, xo, yo) for yo in (0, 32, 64, 96) for xo in (0, 64)] + [(256, 32, xo, 0) for xo in (0, 64, 128, 192)]
    for w, h, xo, yo in wins:
        jobs.append(("tx4-ty4-%dx%d-x%dy%d" % (w, h, xo, yo), "heldout", w, h, xo, yo, None, None))
    for name, sset, w, h, xo, yo, kname, same in jobs:
        pn = "r8l-ty4-%dx%d" % (w, h) + ("-x%dy%d" % (xo, yo) if (xo, yo) != (0, 0) or w * h > 64 * 32 else "")
        pages = None if sset == "control" else 64
        args = prog(st, pn, out_dir, 4, w, h, xo=xo, yo=yo, same_as=same, pages=pages)
        row(st, name, sset, "safe", TX_KNOBS + (" reads:rows" if sset == "control" else ""), "t4", args)
        pred(st, name, "size", "%dx%d" % (w, h), "all", sset, "table")
        pred(st, name, "window", "%d,%d" % (xo, yo), "all", sset, "table")
        kib = 4 * (pages or 16)
        pred(st, name, "scratch", "%d KiB" % kib, "all", sset, "sgxfive-test.c SCRATCH_FILL over SCRATCH_PAGES")
        imgs = {hy: T.tex_image(hy, w, h, xo, yo, dwords=kib * 256) for hy in hyps}
        assert all(None not in im for im in imgs.values()), name        # every rival's texel inside the tag fill
        for hy in hyps:
            pred(st, name, "pixels_sha", T.sha_list(imgs[hy]), hy, sset, "gen/texmodel.py")
        if sset == "control":
            control(st, name, ("rows",))
            k = kept_image(kname)
            assert k == imgs["H-BLKROW"], name
            pred(st, name, "pixels_sha", T.sha_list(k), "kept", sset, "E910 %s/tx/%s.txt.gz" % (R7G_OUT, kname))
    # the soft rows: non-power-of-two widths through the linear axis, and their bridge
    lin = [("tx4-lin-ty3-32x16", "bridge", 32, 16), ("tx4-lin-ty3-24x8", "heldout", 24, 8),
           ("tx4-lin-ty3-40x8", "heldout", 40, 8)]
    for name, sset, w, h in lin:
        args = prog(st, "r8l-lin-ty3-%dx%d" % (w, h), out_dir, 3, w, h, linear=True)
        row(st, name, sset, "safe", TX_KNOBS + " soft", "t4", args)
        pred(st, name, "size", "%dx%d" % (w, h), "all", sset, "table")
        for hy in ("RASTERW", "RASTERP2"):
            pred(st, name, "pixels_sha", T.sha_list(T.tex_image(hy, w, h, linear=True)), hy, sset, "gen/texmodel.py")
        if sset == "bridge":
            k = kept_image("tx-ctl-ty3-32x16")
            assert k == T.tex_image("RASTERW", 32, 16, linear=True)
            pred(st, name, "pixels_sha", T.sha_list(k), "kept", sset, "E725 the map axis's image")
    return ["#stage tx4", "#limit 0",
            "# Q283 type 4 past the first two 32 x 32 blocks (E910 post hoc: 32 x 32 blocks of 1024 dwords): the 64 x 32 window",
            "# moved over larger textures by the map axis's offset (texbuild.py axis_code ORs it in): 64 x 64 (2 windows), 128 x 64",
            "# (4), 128 x 128 (8), 256 x 32 (4), held out.  The tool's tag fill covers its whole scratch (sgxfive-test.c SCRATCH_FILL",
            "# over SCRATCH_PAGES: 16384 dwords by default, so 128 x 128 is tagged throughout); the held-out rows take --scratch-pages",
            "# 64 (256 KiB, 65536 dwords): H-BLKZ reads 256 x 32 up to dword 22527, and no rival reads past the fill (safe class);",
            "# the x0y0 windows repeat E910's blocks with it.  A row whose output names another scratch size cannot tell.  Frozen: H-BLKROW (blocks row by row) against H-BLKCOL and H-BLKZ; 128 x 64 parts all three.  Controls",
            "# (kept images, reads:rows): E910's type 4 64 x 32 and 4 x 16 programs byte for byte.  Soft, last: type 3 at 24 x 8 and",
            "# 40 x 8 through the linear axis (RASTERW against RASTERP2), with type 3 32 x 16 through the same axis as their bridge",
            "# (it must equal E725's map image, or the two rows cannot tell); the second soft failure in a row stops tx4 (rc 24).",
            "# No fault expected: any fault, hang or other failure stops the stage (rc 4) and the session."]


# ================================================================================ tx5 (Q178)
def tx5(out_dir):
    st = "tx5"
    hyps = ("H-DW8", "H-DW4B1")
    jobs = [("tx5-ctl-8x8", "control", 8, 8, None, 0, R7G + "/bins/r7g-ty5-8x8.bin", "tx-ty5-8x8"),
            ("tx5-ctl-16x16", "control", 16, 16, None, 0, R7G + "/bins/r7g-ty5-16x16.bin", "tx-ty5-16x16"),
            ("tx5-ctl-16x16-zero", "control", 16, 16, {i: 0 for i in range(112)}, 0,
             R7G + "/bins/r7g-ty5-16x16-zero.bin", "tx-ty5-16x16-zero")]
    for v in (0x1, 0x2, 0xFFFFFFFE, 0xFFFFFFFD, 0x4, 0x8, 0x10000, 0x80000000):
        jobs.append(("tx5-8x8-v%08x" % v, "heldout", 8, 8, {i: v for i in range(64)}, 0, None, None))
    for j in (0, 1, 3, 7):
        jobs.append(("tx5-8x8-j%d" % j, "heldout", 8, 8, {i: (0xFFFFFFFF if i == j else 0) for i in range(64)}, 0, None, None))
    for j in (0, 5, 31):
        jobs.append(("tx5-16x16-j%d" % j, "heldout", 16, 16, {i: (0xFFFFFFFF if i == j else 0) for i in range(112)}, 0,
                     None, None))
    for v in (0x1, 0x2):
        jobs.append(("tx5-16x16-v%08x" % v, "heldout", 16, 16, {i: v for i in range(112)}, 0, None, None))
    for w, h, yo in ((32, 8, 0), (8, 32, 0), (16, 8, 0), (64, 64, 32)):
        jobs.append(("tx5-plain-%dx%d-y%d" % (w, h, yo), "heldout", w, h, None, yo, None, None))
    for name, sset, w, h, stored, yo, same, kname in jobs:
        pn = "r8l-ty5-" + name[4:]
        args = prog(st, pn, out_dir, 5, w, h, yo=yo, stored=stored, same_as=same)
        row(st, name, sset, "safe", TX_KNOBS + (" reads:rows" if sset == "control" else ""), "t4", args)
        pred(st, name, "size", "%dx%d" % (w, h), "all", sset, "table")
        pred(st, name, "stored", "%d dwords" % len(stored) if stored else "none", "all", sset, "table")
        for hy in hyps:
            pred(st, name, "pixels_sha", T.sha_list(T.type5_image(hy, w, h, stored, yo=yo)), hy, sset,
                 "gen/texmodel.py")
        if sset == "control":
            control(st, name, ("rows",))
            k = kept_image(kname)
            assert k == T.type5_image("H-DW8", w, h, stored), name
            pred(st, name, "pixels_sha", T.sha_list(k), "kept", sset, "E911 %s/tx/%s.txt.gz" % (R7G_OUT, kname))
    for name, w, t0, fmt in (("tx5-x-fmt9-16x16", 16, T0_REP, 9), ("tx5-x-fmt18-16x16", 16, T0_REP, 18),
                             ("tx5-x-bil-16x16", 16, T0_BIL, 12), ("tx5-x-bil-8x8", 8, T0_BIL, 12)):
        args = prog(st, "r8l-ty5-" + name[4:], out_dir, 5, w, w, t0=t0, fmt=fmt)
        row(st, name, "explore", "safe", TX_KNOBS + " soft", "t4", args)
        pred(st, name, "size", "%dx%d" % (w, w), "all", "explore", "table")
        pred(st, name, "words", "t0 0x%08x format %d" % (t0, fmt), "all", "explore", "table")
    return ["#stage tx5", "#limit 0",
            "# Q178 type 5 (E911; the leftovers' P2, a post hoc fit on E911's six rows): which dword and which bit.  Frozen:",
            "# H-DW8 (the pixel is 0x0000ffff iff bit 0 of texture dword floor(t / 8) is set, t the raster index) against",
            "# H-DW4B1 (bit 1 of dword floor(t / 4)).  Held out: 8 x 8 with all 64 dwords stored V (0x1, 0x2, 0xfffffffe,",
            "# 0xfffffffd, 0x4, 0x8, 0x10000, 0x80000000), one dword j stored 0xffffffff among 64 zeros (j 0, 1, 3, 7), at 16 x 16",
            "# j 0, 5, 31 and V 0x1, 0x2 over 112 dwords (the generator's inject, E911's count), and four plain fills (32 x 8,",
            "# 8 x 32, 16 x 8, 64 x 64 at window y 32: the raster index; there the two are one function of the tag fill).",
            "# Controls (kept images, reads:rows): E911's 8 x 8, 16 x 16 and 16 x 16 zeroed programs byte for byte.  Soft, last,",
            "# explore: the format word (9, 18) and the filter word (bilinear) changed; the second soft failure in a row stops",
            "# tx5 (rc 24).  No fault expected: any fault, hang or other failure stops the stage (rc 4) and the session."]


# ================================================================================ zs2 (Q260)
SW, SH = 512, 256
STEPS = (-2, -1, 0, 1, 2)


def zs_preds(st, name, sset, v, w, h, axis_t, c_xy, group, source):
    """Frozen per row: the covered image under HA (half away from zero for negatives; HU for n >= 0)
    and HU, their sha and count, the aimed pixel's state, the longest edge (H-SHORT / H-BAND)."""
    for var in ("HA", "HU"):
        sp = Z.cover4096(v, w, h, var)
        pfile("predictions/zs2/%s.%s.spans" % (name, var), Z.spans_text(sp))
        pred(st, name, "covered_sha", Z.cov_sha(sp, w), "H-" + var, sset, source)
        pred(st, name, "tri", Z.count(sp), "H-" + var, sset, source)
        pred(st, name, "aimed", int(Z.covered(sp, *c_xy)), "H-" + var, sset, source)
    pred(st, name, "size", "%dx%d" % (w, h), "all", sset, "table")
    pred(st, name, "sweep", group, "all", sset, "table")
    pred(st, name, "target_axis", axis_t, "all", sset, "table")
    pred(st, name, "aimed_px", "%d,%d" % c_xy, "all", sset, "gen/zsmodel.py aimed_pixel")
    pred(st, name, "longest_edge", "%.3f" % Z.longest_edge(v, "HA"), "H-HA", sset, "gen/zsmodel.py")


def zs2(out_dir):
    st = "zs2"
    tab = {}
    for ln in blob(R7G + "/tables/zs.txt").decode().splitlines():
        if ln and not ln.startswith("#"):
            p = ln.split("|", 5)
            tab[p[0]] = p[5]
    for r7, name, src in (("zs-ctl-e681-1400606", "zs2-ctl-e681", "E681"), ("zs-ctl-e683-1401234", "zs2-ctl-e683", "E683"),
                          ("zs-m0.5-x--1", "zs2-ctl-m0.5-x-dm1", "E914"), ("zs-m0.5-x-+0", "zs2-ctl-m0.5-x-d0", "E914"),
                          ("zs-m0.5-x-+1", "zs2-ctl-m0.5-x-dp1", "E914")):
        args = tab[r7]
        kt = gz_text("%s/zs/%s.txt.gz" % (R7G_OUT, r7))
        kh = next(ln.split()[3] for ln in kt.splitlines() if ln.startswith("target: "))
        if r7.startswith("zs-m0.5"):
            d = int(r7.split("-x-", 1)[1])
            assert args == Z.tri_args(SW, SH, Z.sweep(-0.5, "x", d, 0, 3)), r7
        row(st, name, "control", "safe", "expectdiff needhash reads:hash", "t4", args)
        control(st, name, ("hash",))
        pred(st, name, "hash", kh, "kept", "control", "%s %s/zs/%s.txt.gz" % (src, R7G_OUT, r7))
    # (b) negative ties at other grid points, aimed at the nearest on-screen centre (pixel 0), 512 x 256
    for p, tag in ((-1 / 256, "m1o256"), (-1.25, "m1.25"), (-17.75, "m17.75"), ("far", None)):
        for axis in "xy":
            pp, tg = (p, tag) if p != "far" else ((-200.5, "m200.5") if axis == "x" else (-100.5, "m100.5"))
            for d in STEPS:
                v = Z.sweep(pp, axis, d, 0, 3)
                name = "zs2-g-%s-%s-%s" % (tg, axis, dtag(d))
                row(st, name, "heldout", "safe", "expectdiff needhash", "t4", Z.tri_args(SW, SH, v))
                zs_preds(st, name, "heldout", v, SW, SH, axis, Z.aimed_pixel(axis, 0, 3), "g %s %s" % (tg, axis),
                         "gen/zsmodel.py")
    # (c) long edges at -64.5 and +64.5 on 512 x 256 (aims: the swept-axis distance from the tie to the aimed centre)
    for p in (-64.5, 64.5):
        for axis in "xy":
            n = SW if axis == "x" else SH
            for k, aim in enumerate(aims(p, axis)):
                c = int(p + aim - 0.5)
                assert 0 <= c < n
                off = 3 if k < 2 else 30
                for d in STEPS:
                    v = Z.sweep(p, axis, d, c, off)
                    name = "zs2-l-%s%g-%s-a%d-%s" % ("m" if p < 0 else "p", abs(p), axis, aim, dtag(d))
                    row(st, name, "heldout", "safe", "expectdiff needhash", "t4", Z.tri_args(SW, SH, v))
                    zs_preds(st, name, "heldout", v, SW, SH, axis, Z.aimed_pixel(axis, c, off),
                             "l %g %s %d" % (p, axis, aim), "gen/zsmodel.py")
    # (t) the 100 and long aims again on 256 x 512, the scene transposed (an x sweep of 512 x 256 is a y sweep here)
    for p in (-64.5, 64.5):
        for axis in "xy":
            for aim in aims(p, axis)[2:]:
                c, off = int(p + aim - 0.5), 30
                for d in STEPS:
                    v = Z.sweep(p, axis, d, c, off, transpose=True)
                    name = "zs2-t-%s%g-%s-a%d-%s" % ("m" if p < 0 else "p", abs(p), axis, aim, dtag(d))
                    row(st, name, "heldout", "safe", "expectdiff needhash", "t4", Z.tri_args(SH, SW, v))
                    zs_preds(st, name, "heldout", v, SH, SW, "y" if axis == "x" else "x",
                             Z.aimed_pixel(axis, c, off, transpose=True), "t %g %s %d" % (p, axis, aim), "gen/zsmodel.py")
    return ["#stage zs2", "#limit 0",
            "# Q260 (E914): vertices in 1/4096 pixel (--tri-unit 12), one vertex swept in five steps d = -2 .. +2 of 1/4096",
            "# across the 1/512 tie above a grid point, its edge aimed through a pixel centre C (E914's construction, gen/zsmodel.py).",
            "# (g) negative ties at other grid points, -1/256, -1.25, -17.75 and -200.5 (x) / -100.5 (y), aimed at the nearest",
            "# on-screen centre (pixel 0), 512 x 256; (l) long edges at -64.5 and +64.5, both axes, aimed 1 and 4 (at -64.5: 65",
            "# and 68, pixel 0 and 3, the nearest on screen), 100 and 300 (x) / 200 (y; +64.5 y: 190, the last on screen) pixels",
            "# away, 512 x 256; (t) the 100 and long aims again on 256 x 512 with the scene transposed.  Frozen: HA (half away from",
            "# zero; C flips between d = 0 and d = +1 at a negative tie, between -1 and 0 at a positive one, E914's step table)",
            "# against HU; H-SHORT (the image is HA's exactly where no edge reaches 250 pixels); H-BAND (elsewhere it differs from",
            "# HA's only within 6.4e-4 pixel of an edge of 250 pixels or more); H-YAXIS (misses on target y sweeps only, both",
            "# targets) against H-GEOM (misses follow the transposed scene to x on 256 x 512).  Controls (kept hashes, reads:hash):",
            "# E681's and E683's cases and three steps of E914's -0.5 x sweep (d -1, 0, +1).  needhash: the second row without a",
            "# hash stops zs2 (rc 24).  No fault expected (E914: 230 jobs clean): any fault stops the stage (rc 4) and the session."]


def dtag(d):
    """A step's name: d0, dp1, dm2 (a row name has no sign)."""
    return "d0" if d == 0 else ("dp%d" % d if d > 0 else "dm%d" % -d)


def aims(p, axis):
    """The four aims of a long-edge sweep (pixels from the tie to the aimed centre on the swept axis)."""
    if p < 0:
        return (65, 68, 100, 300 if axis == "x" else 200)
    return (1, 4, 100, 300 if axis == "x" else 190)


# ================================================================================ q139 (Q139)
def q139_cmd(w, h, poke):
    return ("tri --tri-full --pixels --width %d --height %d --max-width %d --max-height %d%s --wait-ms 20000 --keep-going "
            "--dump-render \"$W\"" % (w, h, w, h, " --kpoke-render %s" % poke if poke else ""))


def image_wrong(text, w, h):
    """The kept wrong-tile set of a --pixels output (E877's reading: a tile with any pixel not 0xff00ff00)."""
    sys.path.insert(0, os.path.join(KP, "score"))
    import lib_dump as L
    comp, bad = L.image_tiles(text, w, h)
    assert comp
    return bad


def q139(out_dir):
    st = "q139"
    ds = {}
    for d in MTF:
        for ln in blob(d + "/cases.tsv").decode().splitlines()[1:]:
            p = ln.split("\t")
            ds[p[0]] = (d, int(p[2]), int(p[3]), p[4] if len(p) > 4 else "")
    s4 = gz_text(R7R_OUT + "/q139/q139-h-256x256-stride-4.txt.gz")
    jobs = [("q139-ctl-256x256", "control", 256, 256, "", None),
            ("q139-ctl-640x480", "control", 640, 480, "", None),
            ("q139-ctl-256x256-stride-4", "control", 256, 256, "1:ta:146=0x4",
             ("kept", image_wrong(s4, 256, 256), "E907 %s/q139/q139-h-256x256-stride-4.txt.gz" % R7R_OUT))]
    for s in (1, 2):
        nm = "q100-256x256-stride-%d" % s
        d, w, h, a = ds[nm]
        jobs.append(("q139-fit-256x256-stride-%d" % s, "fit", w, h, a.split()[1],
                     ("kept", image_wrong(gz_text("%s/dumps/%s.txt.gz" % (d, nm)), w, h), "P1 %s/dumps/%s.txt.gz" % (d, nm))))
    for w, h, ss in ((256, 256, (3, 5, 6, 7, 12, 20)), (640, 480, (5, 6, 7, 8, 12))):
        for s in ss:
            jobs.append(("q139-h-%dx%d-stride-%d" % (w, h, s), "heldout", w, h, "1:ta:146=0x%x" % s, None))
    for nm in ("q100-256x256-m1-B2-10", "q100-256x256-m1-B2-11", "q100-640x480-m1-B1-23", "q100-1280x720-m2-B3p1"):
        d, w, h, a = ds[nm]
        jobs.append(("q139-res-" + nm[5:], "residue", w, h, a.split()[1],
                     ("kept", image_wrong(gz_text("%s/dumps/%s.txt.gz" % (d, nm)), w, h), "P1 %s/dumps/%s.txt.gz" % (d, nm))))
    for name, sset, w, h, poke, kept in jobs:
        knobs = "expectdiff needhash" + (" reads:hash,dump" if sset == "control" else "")
        row(st, name, sset, "safe", knobs, "t4", q139_cmd(w, h, poke))
        if sset == "control":
            control(st, name, ("hash", "dump"))
        a = "--kpoke-render " + poke if poke else ""
        pred(st, name, "size", "%dx%d" % (w, h), "all", sset, "table")
        for o in Q.KEYS:
            pr = Q.predict(w, h, a, o)
            pred(st, name, "wrong", Q.tiles_text(Q.wrong(pr)), o, sset, "gen/q139model.py")
            pfile("predictions/q139/%s.%s.slots" % (name, o), Q.slots_text(pr) + "\n")
        if kept:
            pred(st, name, "wrong", Q.tiles_text(kept[1]), "kept", sset, kept[2])
            if sset in ("control", "fit"):
                assert kept[1] == Q.wrong(Q.predict(w, h, a, "blkrow")), name
    return ["#stage q139", "#limit 0",
            "# Q139's write order (E907 R7-BLK's slots; the leftovers' P1, SEMI): the datasets' own command (ta/mtile-fields*,",
            "# r7-rp's q139 rows token for token) with --keep-going and --dump-render into the job's work directory, one",
            "# --kpoke-render of the stride word (ta:146) or a macrotile word, only inside the ranges that drew without a fault in",
            "# the kept data (256 x 256 strides 0 to 31, 640 x 480 strides 4 to 63; the residue jobs drew in their datasets): safe",
            "# class.  Controls (reads:hash,dump; the scorer reads the image and the header slots): the 256 x 256 and 640 x 480",
            "# baselines (exact image, one header a tile, slots as R7-BLK) and 256 x 256 stride 4 (its kept wrong set, 84 tiles).",
            "# Fit: 256 x 256 strides 1 and 2 (images kept, never dumped).  Held out: 256 x 256 strides 3, 5, 6, 7, 12, 20 and",
            "# 640 x 480 strides 5, 6, 7, 8, 12.  Frozen: block order (blkrow), the wrong-tile set and every header slot; rivals",
            "# raster (row order), blkdown (blocks by column), mtblk (macrotile, then block).  Residue (dumps only, scored",
            "# nothing): P1's four jobs no order gives.  needhash: the second row without a hash stops q139 (rc 24).",
            "# No fault expected: any fault or hang stops the stage (rc 4)."]


STAGES = {"tx3": tx3, "tx4": tx4, "tx5": tx5, "zs2": zs2, "q139": q139}


def producible(row_):
    a = row_.split("|", 5)[5]
    if a.startswith("probe"):
        return {"rows"}
    keys = {"hash"}
    if "--dump-render" in a:
        keys.add("dump")
    return keys


def write(out_dir=KP):
    os.makedirs(os.path.join(out_dir, "bins"), exist_ok=True)
    for f in os.listdir(os.path.join(out_dir, "bins")):
        os.remove(os.path.join(out_dir, "bins", f))
    heads = {st: fn(out_dir) for st, fn in STAGES.items()}
    byname = {r.split("|")[0]: r for rows in ROWS.values() for r in rows}
    scorekit.refuse_unreadable({n: (reads, byname[n]) for n, _, reads in CONTROLS}, producible)
    for d in ("tables", "predictions", "predictions/zs2", "predictions/q139", "mock"):
        os.makedirs(os.path.join(out_dir, d), exist_ok=True)
    for d in ("predictions/zs2", "predictions/q139"):
        for f in os.listdir(os.path.join(out_dir, d)):
            os.remove(os.path.join(out_dir, d, f))
    for st in STAGES:
        with open(os.path.join(out_dir, "tables", st + ".txt"), "w") as f:
            f.write("\n".join(heads[st] + ROWS[st]) + "\n")
        with open(os.path.join(out_dir, "predictions", st + ".tsv"), "w") as f:
            f.write("case\tquantity\tvalue\tmodel\tset\tsource\n")
            for p in PREDS[st]:
                f.write("\t".join(p) + "\n")
    for rel, text in sorted(FILES.items()):
        with open(os.path.join(out_dir, rel), "w") as f:
            f.write(text)
    with open(os.path.join(out_dir, "bins/SHA256SUMS"), "w") as f:
        for b in sorted(os.listdir(os.path.join(out_dir, "bins"))):
            if b.endswith(".bin"):
                f.write("%s  %s\n" % (hashlib.sha256(open(os.path.join(out_dir, "bins", b), "rb").read()).hexdigest(), b))
    with open(os.path.join(out_dir, "mock/progs.tsv"), "w") as f:
        f.write("# mock/progs.tsv (gen/lgen.py): each program's sha256 and what it samples, for the fake tool\n")
        for sha, meta in sorted(PROGS.items()):
            f.write("%s\t%s\n" % (sha, json.dumps(meta, sort_keys=True)))
    with open(os.path.join(out_dir, "gen/pins.txt"), "w") as f:
        f.write("".join("data:%s\n" % p for p in sorted(PINS)))
    return {st: len(ROWS[st]) for st in STAGES}


if __name__ == "__main__":
    n = write(sys.argv[1] if len(sys.argv) > 1 else KP)
    print("tables:", ", ".join("%s %d" % kv for kv in n.items()), "; total", sum(n.values()))
