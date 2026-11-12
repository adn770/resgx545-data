#!/usr/bin/env python3
"""g7gen.py: write r7-geo's job tables (tables/STAGE.txt), frozen predictions (predictions/STAGE.tsv), the probe programs (bins/),
TABLES.md, stages.txt and gen/data/controls.tsv from gen/models.py and the published records it reads (gen/data/sources.lst).
Deterministic: a second run writes the same bytes (tests/test_gen.py checks it).
  PY gen/g7gen.py            (then run/freeze_g.sh freeze)
Table line: name|set|risk|knobs|tool|args   (tool t4 = ~/sgxfive-test-rgn4, t6 = ~/scratch/r7g/bin/sgxfive-test; $W the job's work
            directory, $S the staged programs ~/scratch/r7g/stage)
Prediction line: case<TAB>quantity<TAB>value<TAB>model<TAB>set
Controls (gen/data/controls.tsv): name<TAB>stage<TAB>reads (the reading keys the run-time premise check needs), refused by
scorekit.refuse_unreadable when the row's job cannot produce one of them.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import gzip  # noqa: E402
import hashlib  # noqa: E402
import os  # noqa: E402
import random  # noqa: E402
import shlex  # noqa: E402
import subprocess  # noqa: E402

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
import models as M  # noqa: E402
import scorekit  # noqa: E402

ASM = os.path.join(KP, "debug/asm/tools/usse-asm/usse-asm")      # git archive of resgx545 1c64f3a tools/usse-asm, built (README)
ARITH = "/Users/jtorra/src/resgx545-data/isp/arith-1138"           # E606
ENV1140 = "/Users/jtorra/src/resgx545-data/isp/coverage-envelope"   # E680, E681, E683
R6M = "/Users/jtorra/src/resgx545-data/render/closing-r6-misc/out/20261112-144153/q289"   # E884
P1141 = "/Users/jtorra/src/resgx545-data/texture/p1141"           # E725
P1132R = "/Users/jtorra/src/resgx545-data/texture/p1132/tx-types-risky"   # E567, E894
INJECT_N = 112          # the memory controls' injected dwords: PROBE_MAX_WORDS (256 USSE words) leaves room for 112


def gz(path):
    with gzip.open(path, "rb") as f:
        return f.read()


def sha_file_gz(path):
    return hashlib.sha256(gz(path)).hexdigest()


def probe_rows(text):
    """probe NAME: row N: hex... -> dwords in raster order (2048 for a fill)."""
    rows = {}
    for ln in text.splitlines():
        i = ln.find(": row ")
        if ln.startswith("probe ") and i > 0:
            n, _, rest = ln[i + 6:].partition(":")
            rows[int(n)] = [int(t, 16) for t in rest.split()]
    return [v for k in sorted(rows) for v in rows[k]]


def rle_cover(text, w, h):
    """E680's --pixels-rle rows -> covered image (bool), for the controls' kept images."""
    import numpy as np
    img = np.zeros((h, w), dtype=bool)
    for ln in text.splitlines():
        if ln.startswith("rle "):
            y, _, rest = ln[4:].partition(":")
            x = 0
            for t in rest.split():
                v, _, n = t.rpartition("x")
                n = int(n)
                img[int(y), x:x + n] = int(v, 16) == M.GREEN
                x += n
    return img


def kept_hash(text):
    for ln in text.splitlines():
        if ln.startswith("target: "):
            return int(ln.split()[3], 16)
    return None


def kept_tri(text):
    for ln in text.splitlines():
        if ln.startswith("tri ") and " triangle, " in ln:
            return int(ln.split(": ")[1].split()[0])
    return None


ROWS, PREDS, CONTROLS = {}, {}, []


def row(stage, name, sset, risk, knobs, tool, args):
    ROWS.setdefault(stage, []).append("%s|%s|%s|%s|%s|%s" % (name, sset, risk, knobs, tool, args))


def pred(stage, case, q, v, model, sset):
    PREDS.setdefault(stage, []).append((case, q, str(v), model, sset))


def control(stage, name, reads):
    CONTROLS.append((name, stage, tuple(reads)))


def assemble(text, name):
    out = os.path.join(KP, "bins", name + ".bin")
    r = subprocess.run([ASM, "-l", "-o", out, "-"], input=text, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(name + ": " + r.stderr)
    n = os.path.getsize(out)
    assert n % 8 == 0 and n // 8 <= 256, (name, n)
    return name + ".bin"


# ================================================================================================================ xf (Q206)
def xf():
    st = "xf"
    k = gz(os.path.join(R6M, "f-128x64-x10.txt.gz")).decode()
    kb = gz(os.path.join(R6M, "f-base-128x64.txt.gz")).decode()
    ctl = [("xf-ctl-128x64-x10", 0x10, kept_hash(k)), ("xf-base-128x64", 0, kept_hash(kb))]
    cand = [(0x10, 0x2000), (0x18, 0x3000), (0x10, 0x4000), (0x20, 0x2000), (0x28, 0x6000), (0x30, 0x4000), (0x38, 0x2000),
            (0x20, 0x6000), (0x30, 0x3000), (0x18, 0x5000), (0x08, 0x2000), (0x28, 0x3000)]
    # the first 8 that separate H-INDEP, H-XFIRST and H-YFIRST (an odd field value acts as the even one below it under OR)
    pairs = [p for p in cand if len({M.fill_predict(128, 64, p[0] | p[1], m)[0] for m in ("INDEP", "XFIRST", "YFIRST")}) == 3][:8]
    assert len(pairs) == 8
    for name, v, kh in ctl:
        row(st, name, "control", "safe", "expectdiff needhash", "t4", M.fill_args(128, 64, v))
        control(st, name, ("hash",))
        assert M.fill_predict(128, 64, v, "INDEP")[0] == kh, name
        pred(st, name, "hash", "0x%016x" % kh, "E884", "control")
        pred(st, name, "job", "ok", "all", "control")
    for x, y in pairs:
        v = x | y
        name = "xf-128x64-x%02x-y%04x" % (x, y)
        row(st, name, "heldout", "safe", "expectdiff needhash", "t4", M.fill_args(128, 64, v))
        hs = {}
        for m in ("INDEP", "XFIRST", "YFIRST"):
            h, wrong = M.fill_predict(128, 64, v, m)
            hs[m] = h
            pred(st, name, "hash", "0x%016x" % h, "H-" + m, "heldout")
            pred(st, name, "wrong", wrong, "H-" + m, "heldout")
        assert len(set(hs.values())) == 3, (name, hs)        # every pair separates the three readings
        pred(st, name, "job", "ok", "all", "heldout")
    return ["#stage xf", "#limit 1",
            "# Q206's both-fields U1 clause (E876, E884; R7-5): 8 fills at 128 x 64 with the end-of-tile DOUTU1 (pds:pixev dword 12)",
            "# x field (bits 11:3) and y field (bits 21:12) XORed together.  Frozen: H-INDEP (each axis placed by E884's OR rule",
            "# independently), H-XFIRST (only x acts when both move), H-YFIRST (only y); every pair separates the three by hash.",
            "# Controls that can fail: E884's 128 x 64 x ^ 0x10 fill (kept hash) and the 128 x 64 baseline (kept hash).",
            "# expectdiff: a fill with wrong pixels exits 1 with its diff line; needhash: a second row without a hash stops (rc 17).",
            "# No fault expected (1556 fills of this poke ran clean): any fault, hang or failure stops the stage (rc 4)."]


# ================================================================================================================ tx (Q283, Q178)
def tx():
    st = "tx"
    tmpl = open(os.path.join(KP, "templates/tx_map.s")).read()
    # the control: E725's ty3-32x16 program, byte for byte, and its kept image
    b = assemble(M.tex_text(tmpl, M.tex_spec(3, 32, 16)), "r7g-ty3-32x16")
    assert open(os.path.join(KP, "bins", b), "rb").read() == open(os.path.join(P1141, "stage-bins/p1141-types__2.bin"), "rb").read()
    kept = probe_rows(gz(os.path.join(P1141, "out-hw/p1141tex-dumps/tex-f-types/ty3-32x16.txt.gz")).decode())
    assert kept == M.tex_image("RASTERW", 32, 16)
    jobs = [("tx-ctl-ty3-32x16", "control", 3, 32, 16, b)]
    for ty in (1, 3, 4):
        for w, h in ((4, 16), (64, 8), (128, 8)):
            jobs.append(("tx-ty%d-%dx%d" % (ty, w, h), "heldout", ty, w, h, None))
    for w, h in ((64, 32), (128, 32)):
        jobs.append(("tx-ty4-%dx%d" % (w, h), "heldout", 4, w, h, None))
    for name, sset, ty, w, h, b in jobs:
        if b is None:
            b = assemble(M.tex_text(tmpl, M.tex_spec(ty, w, h)), "r7g-ty%d-%dx%d" % (ty, w, h))
        row(st, name, sset, "risky" if ty == 4 else "safe", "after", "t4", "probe --temps 32 --coords --pixels \"$S/%s\"" % b)
        for hyp in M.TYPE_HYPS[ty]:
            pred(st, name, "pixels_sha", M.sha_list(M.tex_image(hyp, w, h)), hyp, sset)
        pred(st, name, "size", "%dx%d" % (w, h), "all", sset)
        pred(st, name, "type", ty, "all", sset)
        if sset == "control":
            control(st, name, ("rows",))
            pred(st, name, "pixels_sha", M.sha_list(kept), "E725", sset)
    # Q178: type 5 at 16 x 16 (E567's size: the control, E894's image), 8, 32, 64; the two memory controls at 16 x 16
    k5 = probe_rows(gz(os.path.join(P1132R, "rt5-2d.txt.gz")).decode())
    assert k5 == M.type5_image("H-STEP", 16)
    t5 = [("tx-ty5-16x16", "control", 16, None), ("tx-ty5-8x8", "heldout", 8, None), ("tx-ty5-32x32", "heldout", 32, None),
          ("tx-ty5-64x64", "heldout", 64, None), ("tx-ty5-16x16-zero", "memory", 16, 0), ("tx-ty5-16x16-ones", "memory", 16, 0xFFFFFFFF)]
    for name, sset, w, fillv in t5:
        inj = None if fillv is None else {i: fillv for i in range(INJECT_N)}
        b = assemble(M.tex_text(tmpl, M.tex_spec(5, w, w, inj)), "r7g-" + name[3:])
        row(st, name, sset, "risky", "after", "t4", "probe --temps 32 --coords --pixels \"$S/%s\"" % b)
        for hyp in ("H-STEP", "H-FIX16"):
            pred(st, name, "pixels_sha", M.sha_list(M.type5_image(hyp, w)), hyp, sset)
        pred(st, name, "size", "%dx%d" % (w, w), "all", sset)
        pred(st, name, "type", 5, "all", sset)
        if sset == "memory":
            pred(st, name, "same_as", "tx-ty5-16x16", "H-STEP", sset)
            pred(st, name, "differs_from", "tx-ty5-16x16", "H-MEM", sset)
            pred(st, name, "inject", "%d dwords of 0x%08x from dword 0" % (INJECT_N, fillv), "all", sset)
        if sset == "control":
            control(st, name, ("rows",))
            pred(st, name, "pixels_sha", M.sha_list(k5), "E894", sset)
    return ["#stage tx", "#limit 1",
            "# Q283 (E725) and Q178 (E567, E894; R7-4): E725's map-texture fill (64 x 32, texel (x mod w, y mod h), dword i of the",
            "# texture 0xD0000000 | i) for types 1, 3, 4 at 4 x 16, 64 x 8, 128 x 8 and type 4 at 64 x 32, 128 x 32 (held out: RASTERW",
            "# for 1 and 3; S32 against SMAXW, S2WCAP, RASTERW, RASTER2W for 4), and type 5 at 8, 32, 64 (H-STEP against H-FIX16) with",
            "# two memory controls at 16 x 16 (the program zeroes / sets the texture's first 112 dwords before its sample; H-STEP: the",
            "# image does not change).  Controls that can fail: E725's ty3-32x16 program byte for byte (its kept image) and type 5 at",
            "# 16 x 16 (E894's image).  after: the health fill and triangle after every job (as E567's types-risky); no fault expected",
            "# (E725's 12 and E567's 15 risky jobs ran clean): any fault, hang or failure stops the stage (rc 4)."]


# ================================================================================================================ zd / zf (Q262, Q240)
def e606_case(pred_fn):
    for ln in open(os.path.join(ARITH, "cases.tsv")):
        f = ln.rstrip("\n").split("\t")
        if pred_fn(f):
            return f
    raise LookupError


def e606_control(st, name, f):
    cid, w, h = int(f[0]), int(f[3]), int(f[4])
    v, z = [int(t) for t in f[5:11]], f[11:14]
    args = ("tri --keep-overflow --wait-ms 20000 --width %d --height %d --tri-v %s --tri-z %s --depth --depth-ctl %s "
            "--depth-fill 0xdeadbeef --depth-dump \"$W/depth\" --depth-pages %d --poke blk:1=0x00400200 --pixels"
            % (w, h, ",".join(map(str, v)), ",".join(z), hex(M.G.depth_ctl(w)), M.G.depth_pages(w, h)))
    txt = gz(os.path.join(ARITH, "main/D/%d.txt.gz" % cid)).decode()
    kh = kept_hash(txt)
    assert M.image_hash(M.cover(v, w, h)) == kh, name
    row(st, name, "control", "safe", "expectdiff needhash", "t4", args)
    control(st, name, ("hash", "tri", "dump"))
    pred(st, name, "hash", "0x%016x" % kh, "E606", "control")
    pred(st, name, "tri", kept_tri(txt), "E606", "control")
    pred(st, name, "dump_sha", sha_file_gz(os.path.join(ARITH, "main/D/%d.depth.gz" % cid)), "E606", "control")
    pred(st, name, "e606_case", cid, "all", "control")
    d_preds(st, name, "control", w, h, v, [float(t) for t in z], True)


def d_preds(st, name, sset, w, h, v, z, pixels):
    cov = M.cover(v, w, h)
    hh = M.image_hash(cov)
    pred(st, name, "size", "%dx%d" % (w, h), "all", sset)
    pred(st, name, "hash", "0x%016x" % hh if hh is not None else "-", "H-E606", sset)
    pred(st, name, "tri", int(cov.sum()), "H-E606", sset)
    pred(st, name, "covered_sha", M.cov_sha(cov), "H-E606", sset)
    pred(st, name, "dead", 0, "H-ZLS", sset)
    pred(st, name, "outside", 0, "H-ZLS", sset)
    pred(st, name, "depth_tol", M.DEPTH_TOL, "H-DEPTH", sset)
    pred(st, name, "gradient", "%.6f" % M.gradient(v, [M.Fraction(t).limit_denominator(1024) for t in z]), "all", sset)
    pred(st, name, "pixels", "yes" if pixels else "no", "all", sset)


def d_row(st, name, sset, w, h, v, z, tool="t4", knobs="", pixels=True):
    big = w * h > 4 * 1024 * 1024
    kn = "expectdiff" + ("" if big else " needhash") + (" " + knobs if knobs else "")
    row(st, name, sset, "safe", kn, tool, M.depth_args(w, h, v, z, pixels))
    d_preds(st, name, sset, w, h, v, z, pixels)


def i_row(st, name, sset, w, h, v, z, knobs=""):
    row(st, name, sset, "safe", "-" if not knobs else knobs, "t4", M.iter_args(w, h, v, z))
    cov = M.cover(v, w, h)
    pred(st, name, "size", "%dx%d" % (w, h), "all", sset)
    pred(st, name, "tri", int(cov.sum()), "H-E606", sset)
    pred(st, name, "covered_sha", M.cov_sha(cov), "H-E606", sset)
    pred(st, name, "iter_tol", M.ITER_TOL, "H-ITER", sset)
    pred(st, name, "range", "%.6f" % M.value_range_per_root_area(v, z), "all", sset)


def zd():
    st = "zd"
    r = random.Random(7262)
    e606_control(st, "zd-ctl-e606-64x64", e606_case(lambda f: f[1] == "fit" and f[2] == "medium" and "I" in f[15]))
    e606_control(st, "zd-ctl-e606-256x128", e606_case(lambda f: f[1] == "heldout" and f[3] == "256" and f[2] == "centre"))
    for w, h in ((512, 256), (640, 480), (1024, 768), (2048, 1024)):
        for cls in ("small", "medium"):
            for i in range(12):
                v, z = M.tri_case(r, w, h, cls)
                d_row(st, "zd-%dx%d-%s-%02d" % (w, h, cls[0], i), "heldout", w, h, v, z, pixels=(w * h <= 512 * 256))
    for i, cls in enumerate(("small", "medium", "small", "medium")):
        v, z = M.tri_case(r, 4096, 4096, cls)
        d_row(st, "zd-4096x4096-%s-%02d" % (cls[0], i), "heldout", 4096, 4096, v, z, knobs="soft", pixels=False)
    return ["#stage zd", "#limit 1",
            "# Q262 depth (E606, E680; R7-2 a): E606's D jobs (tri --tri-v --tri-z --depth, E465's pitch rule, the buffer pre-filled",
            "# 0xdeadbeef and dumped) on 512 x 256, 640 x 480, 1024 x 768, 2048 x 1024 (12 small and 12 medium each, every depth plane's",
            "# gradient below 0.03), then 4 at 4096 x 4096 (the 64 MB buffer dumped whole and gzipped).  --pixels up to 512 x 256 (above,",
            "# the hash, the triangle count and the depth dump decide).  Frozen: H-E606 (coverage: hash, count, covered set), H-ZLS (the",
            "# whole tile area written, nothing outside it), H-DEPTH (3 units of 2^-23).  Controls that can fail: E606's 64 x 64 and",
            "# 256 x 128 cases (kept hash, count, dump sha256).  soft (4096 x 4096): a failure that is no fault or hang is recorded in",
            "# void.tsv and the stage goes on; two in a row stop (rc 24).  No fault expected (0 in E606/E680's 3700 jobs): any fault or",
            "# hang stops the stage (rc 4)."]


def zi():
    st = "zi"
    r = random.Random(7263)
    # E606's I0 probe of case 1016 (128 x 128), its kept rows
    f = e606_case(lambda f: f[0] == "1016")
    w, h, v, zt = int(f[3]), int(f[4]), [int(t) for t in f[5:11]], f[11:14]
    args = M.iter_args(w, h, v, [M.Fraction(t) for t in zt])
    assert args.split("--tri-z ")[1].split()[0] == ",".join(zt)
    kept = probe_rows(gz(os.path.join(ARITH, "main/I0/1016.txt.gz")).decode())
    assert len(kept) == w * h
    row(st, "zi-ctl-e606-1016", "control", "safe", "-", "t4", args)
    control(st, "zi-ctl-e606-1016", ("rows",))
    pred(st, "zi-ctl-e606-1016", "pixels_sha", M.sha_list(kept), "E606", "control")
    pred(st, "zi-ctl-e606-1016", "size", "%dx%d" % (w, h), "all", "control")
    # E680's 1024 x 768 case 1 (1400246), its kept command less --pixels-rle (not in the rgn4 tool): colour only
    jl = [ln for ln in open(os.path.join(ENV1140, "main/jobs.tsv")) if ln.startswith("1400246\t")][0].rstrip("\n").split("\t")
    a = jl[6].split()[1:]
    assert a[-1] == "--pixels-rle"
    kt = gz(os.path.join(ENV1140, "main/raw/1400246.txt.gz")).decode()
    v = [int(t) for t in a[a.index("--tri-v") + 1].split(",")]
    assert M.image_hash(M.cover(v, 1024, 768)) == kept_hash(kt) and (rle_cover(kt, 1024, 768) == M.cover(v, 1024, 768)).all()
    row(st, "zi-ctl-e680-1024x768", "control", "safe", "expectdiff needhash", "t4", " ".join(a[:-1]))
    control(st, "zi-ctl-e680-1024x768", ("hash", "tri"))
    pred(st, "zi-ctl-e680-1024x768", "hash", "0x%016x" % kept_hash(kt), "E680", "control")
    pred(st, "zi-ctl-e680-1024x768", "tri", kept_tri(kt), "E680", "control")
    pred(st, "zi-ctl-e680-1024x768", "size", "1024x768", "all", "control")
    for w, h in ((512, 256), (640, 480), (1024, 768), (2048, 1024)):
        for i in range(6):
            v, z = M.tri_case(r, w, h, "medium")
            i_row(st, "zi-%dx%d-%02d" % (w, h, i), "heldout", w, h, v, z, knobs="soft" if w * h >= 1024 * 768 else "")
    return ["#stage zi", "#limit 1",
            "# Q262 iteration (E606; R7-2 a): E606's I0 probe (probe --tri, pa0 = the iterated clip z of the vertices as the colour,",
            "# every pixel printed) on 512 x 256, 640 x 480, 1024 x 768, 2048 x 1024, 6 medium triangles each whose clip-z range per root",
            "# area is below 0.05.  Frozen: H-E606 (the covered set) and H-ITER (pa0 within 4 units of 2^-23 of the plane at the centre).",
            "# Controls that can fail: E606's I0 case 1016 at 128 x 128 (kept rows, byte for byte; E606's repeats were identical) and",
            "# E680's 1024 x 768 case 1 (kept hash; the colour-only coverage control of the large sizes).  soft (1024 x 768 and up): a",
            "# probe the tool cannot take at that size is recorded in void.tsv; two in a row stop (rc 24).  No fault expected."]


ZF_SIZES = [(64, 128, "t4", ""), (128, 64, "t4", ""), (256, 64, "t4", ""), (128, 96, "t4", ""), (128, 144, "t4", ""),
            (32, 16, "t4", "gate"), (16, 8, "t4", "gate"), (4096, 16, "t4", ""), (64, 33, "t6", "gate"), (96, 47, "t6", "gate")]


def zf():
    st = "zf"
    r = random.Random(7240)
    e606_control(st, "zf-ctl-e606-64x64", e606_case(lambda f: f[1] == "fit" and f[2] == "small" and "I" in f[15]))
    e606_control(st, "zf-ctl-e606-128x128", e606_case(lambda f: f[1] == "heldout" and f[3] == "128" and f[2] == "medium"))
    for w, h, tool, gate in ZF_SIZES:
        g = "s%dx%d" % (w, h)
        first = True
        for cls in ("small", "medium"):
            for i in range(12):
                v, z = M.tri_case(r, w, h, cls)
                kn = "grp:%s" % g + (" gate" if gate and first else "")
                d_row(st, "zf-%dx%d-%s-%02d" % (w, h, cls[0], i), "heldout", w, h, v, z, tool=tool, knobs=kn)
                first = False
    return ["#stage zf", "#limit 1",
            "# Q240 (E606, E680, E885; R7-2 a, R7-7 a): E606's D jobs (colour and depth, --pixels) on the fixture sizes 64 x 128,",
            "# 128 x 64, 256 x 64, 128 x 96, 128 x 144, below a tile 32 x 16 and 16 x 8, 4096 x 16 and the odd heights 64 x 33 and",
            "# 96 x 47 (t6: the rgn4 tool refuses odd heights; E885 ran t6's depth recipe at odd heights), 12 small + 12 medium each.",
            "# Frozen as zd: H-E606, H-ZLS, H-DEPTH.  gate (the first row of 32 x 16, 16 x 8 and the odd heights): a refusal (rc 1, no",
            "# fault, no diff line) skips the rest of its size group (cannot tell) and the stage goes on.  Controls that can fail: E606's",
            "# 64 x 64 and 128 x 128 cases (kept hash, count, dump sha256).  No fault expected: any fault or hang stops the stage (rc 4)."]


# ================================================================================================================ zs (Q260)
def s_preds(st, name, sset, v):
    """per rival: the covered image's sha256 (models.cov_sha) and triangle count; the tool's hash only for HU (the scorer reads the
    image from --pixels and compares it with every rival's)."""
    for rv in M.RIVALS:
        cov = M.cover4096(v, M.SW, M.SH, rv)
        pred(st, name, "covered_sha", M.cov_sha(cov), "H-" + rv, sset)
        pred(st, name, "tri", int(cov.sum()), "H-" + rv, sset)
        if rv == "HU":
            pred(st, name, "hash", "0x%016x" % M.image_hash(cov), "H-HU", sset)
    for c in range(16):
        cov = M.cover4096(v, M.SW, M.SH, "SETUP", c)
        pred(st, name, "covered_sha", M.cov_sha(cov), "SETUP%d" % c, sset)
    pred(st, name, "size", "%dx%d" % (M.SW, M.SH), "all", sset)


def zs():
    st = "zs"
    # the stage's own-shape controls: E681's first 512 x 256 sweep case and E683's first 512 x 256 negative case, their kept
    # commands less --pixels-rle (+ --pixels) and kept hashes
    cases = {ln.split("\t")[0]: ln.rstrip("\n").split("\t") for ln in open(os.path.join(ENV1140, "main/cases-1140.tsv"))}
    jobs = {ln.split("\t")[0]: ln.rstrip("\n").split("\t") for ln in open(os.path.join(ENV1140, "main/jobs.tsv"))}
    picks = []
    for grp in ("S2", "S3"):
        cid = [k for k, f in cases.items() if f[2] == grp and f[4] == "512" and f[5] == "256" and k in jobs][0]
        picks.append((cid, grp))
    for cid, grp in picks:
        a = jobs[cid][6].split()[1:]
        assert a[-1] == "--pixels-rle" and a[a.index("--tri-unit") + 1] == "12"
        v = [int(t) for t in a[a.index("--tri-v") + 1].split(",")]
        kt = gz(os.path.join(ENV1140, "main/raw/%s.txt.gz" % cid)).decode()
        img = rle_cover(kt, 512, 256)
        name = "zs-ctl-%s-%s" % ({"S2": "e681", "S3": "e683"}[grp], cid)
        row(st, name, "control", "safe", "expectdiff needhash", "t4", " ".join(a[:-1] + ["--pixels"]))
        control(st, name, ("hash",))
        assert M.image_hash(img) == kept_hash(kt)
        pred(st, name, "hash", "0x%016x" % kept_hash(kt), "E681" if grp == "S2" else "E683", "control")
        s_preds(st, name, "control", v)
    for pos in M.POSITIONS:
        for axis in "xy":
            for d in range(-8, 9):
                v = M.sweep_case(pos, axis, d)
                p = "far" if pos == "far" else ("m%g" % -pos if pos < 0 else "p%g" % pos)
                name = "zs-%s-%s-%+d" % (p, axis, d)
                if pos == -0.5 and axis == "x":
                    sset = "fit"
                elif pos == 0.5 and axis == "x":
                    sset = "control"
                elif pos in (0.5, 64.5):
                    sset = "mirror"
                else:
                    sset = "heldout"
                row(st, name, sset, "safe", "expectdiff needhash", "t4", M.sweep_args(M.SW, M.SH, v))
                if sset == "control":
                    control(st, name, ("hash",))
                pred(st, name, "sweep", "%s %s %+d" % (pos, axis, d), "all", sset)
                s_preds(st, name, sset, v)
    r = random.Random(7260)
    for i in range(24):
        v, axis = M.nontie_case(r)
        name = "zs-nontie-%02d-%s" % (i, axis)
        row(st, name, "heldout", "safe", "expectdiff needhash", "t4", M.sweep_args(M.SW, M.SH, v))
        s_preds(st, name, "heldout", v)
    return ["#stage zs", "#limit 1",
            "# Q260 (E683, E681; R7-3, decision 4 a): vertices in 1/4096 pixel (--tri-unit 12) on 512 x 256: sweeps of one vertex's",
            "# coordinate in 17 steps of 1/4096 across the 1/512 tie above -0.5, -3.5, -64.5 (x and y), +0.5, +64.5 (the mirror) and",
            "# W + 0.5 / H + 0.5 (the far side), the edge aimed through a pixel centre 1, 4 or 100 pixels away; 24 cases with one",
            "# non-tie negative coordinate.  Frozen: HU, HA, FAR and SETUP(c) for c = 0..15 (c fitted on the -0.5 x sweep, the fit set;",
            "# every other row held out).  Controls that can fail: E681's and E683's first 512 x 256 cases (kept hashes) and the +0.5 x",
            "# sweep (HU, E681).  No fault expected: any fault or hang stops the stage (rc 4)."]


STAGES = {"xf": xf, "tx": tx, "zd": zd, "zi": zi, "zf": zf, "zs": zs}


def producible(row_):
    """The reading keys a row's job can produce (scorekit.refuse_unreadable)."""
    a = row_.split("|", 5)[5]
    if a.startswith("fill"):
        return {"hash"}
    if a.startswith("probe"):
        return {"rows"}
    keys = {"hash", "tri"}
    if "--depth-dump" in a:
        keys.add("dump")
    if "--pixels" in a.split():
        keys.add("rows")
    return keys


def write():
    os.makedirs(os.path.join(KP, "bins"), exist_ok=True)
    for f in os.listdir(os.path.join(KP, "bins")):
        os.remove(os.path.join(KP, "bins", f))
    md = ["# r7-geo job tables (generated by gen/g7gen.py; do not edit)", ""]
    heads = {}
    for st, fn in STAGES.items():
        heads[st] = fn()
    byname = {r.split("|")[0]: r for rows in ROWS.values() for r in rows}
    scorekit.refuse_unreadable({n: (reads, byname[n]) for n, _, reads in CONTROLS}, producible)
    for st in STAGES:
        head, rows, preds = heads[st], ROWS[st], PREDS[st]
        with open(os.path.join(KP, "tables", st + ".txt"), "w") as f:
            f.write("\n".join(head + rows) + "\n")
        with open(os.path.join(KP, "predictions", st + ".tsv"), "w") as f:
            f.write("case\tquantity\tvalue\tmodel\tset\n")
            for p in preds:
                f.write("\t".join(p) + "\n")
        md += ["## %s (%d jobs)" % (st, len(rows)), ""] + [h[2:] for h in head if h.startswith("# ")] + [""]
        md += ["| job | set | knobs | tool | command |", "|---|---|---|---|---|"]
        for r in rows:
            n, s, _, k, t, a = r.split("|", 5)
            md.append("| %s | %s | %s | %s | `%s` |" % (n, s, k, t, a))
        md.append("")
    with open(os.path.join(KP, "TABLES.md"), "w") as f:
        f.write("\n".join(md))
    with open(os.path.join(KP, "stages.txt"), "w") as f:
        f.write("\n".join(STAGES) + "\n")
    with open(os.path.join(KP, "gen/data/controls.tsv"), "w") as f:
        f.write("name\tstage\treads\n" + "".join("%s\t%s\t%s\n" % (n, s, " ".join(r)) for n, s, r in CONTROLS))
    with open(os.path.join(KP, "bins/SHA256SUMS"), "w") as f:
        for b in sorted(os.listdir(os.path.join(KP, "bins"))):
            if b.endswith(".bin"):
                f.write("%s  %s\n" % (hashlib.sha256(open(os.path.join(KP, "bins", b), "rb").read()).hexdigest(), b))


def copy_iter_bins():
    """E606's iteration programs, rebuilt from its templates with resgx545 1c64f3a's probe.py and assembler (byte-identical to the
    dataset's manifest-1138.sha256: tests/test_gen.py)."""
    import pathlib
    sys.path.insert(0, os.path.join(KP, "debug/asm/tools/usse-asm"))
    import probe
    t = [p for p in probe.load(pathlib.Path(KP, "gen/data/iter1138.toml")) if p.name == "p1138-it-a0"]
    out = pathlib.Path(KP, "bins")
    probe.build(t[0], out, pathlib.Path(KP, "templates"))
    probe.build_helpers(t, out, pathlib.Path(KP, "templates"))


if __name__ == "__main__":
    write()
    copy_iter_bins()
    with open(os.path.join(KP, "bins/SHA256SUMS"), "w") as f:
        for b in sorted(os.listdir(os.path.join(KP, "bins"))):
            if b.endswith(".bin"):
                f.write("%s  %s\n" % (hashlib.sha256(open(os.path.join(KP, "bins", b), "rb").read()).hexdigest(), b))
    print("tables:", ", ".join("%s %d" % (s, len(ROWS[s])) for s in STAGES), "; total", sum(len(v) for v in ROWS.values()))
