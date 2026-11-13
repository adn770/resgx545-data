# SPDX-License-Identifier: MIT
"""mock/world.py: r8-lgeo's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; it returns None (the health
pair) or dict(rc, out, err, files={path: bytes}, kmsg=[lines], latch=(int, word)). As strict as
the rgn4 tool for what the session uses: an option it does not take, an odd target side, a
--scratch-pages outside 16 to 64 or a missing program file is refused as the tool refuses it.

  probe [--temps N] [--coords] [--pixels] [--scratch-pages N] FILE
        the program FILE is looked up by its sha256 in mock/progs.tsv (gen/lgen.py: what each
        program samples), and the 64 x 32 image drawn under the world's layout: model = the frozen
        hypotheses (type 3 H-MIN8, type 1 RASTERW, type 4 H-BLKROW, type 5 H-DW8, the linear rows
        RASTERW), rival = their first rival (H-2W, H-2W, H-BLKZ, H-DW4B1, RASTERP2)
  tri --tri-unit 12 --tri-v ... --pixels W x H
        the covered image under HA (model) or HU (rival), the tool's FNV-1a hash, `diff:` against
        HU (the tool's own reference), rc 1 when it differs (expectdiff)
  tri --tri-full --pixels ... [--kpoke-render 1:ta:N=V] --keep-going --dump-render DIR
        R7-BLK's region headers written in block order (model) or row order (rival) into
        DIR/tri.tadata.bin (base 0x4000, three dwords a header, word 0 = (2 c) << 16 | 2 r, a
        stream block in DIR/tri.param.bin for each), the image 0xff00ff00 except 0xdeadbeef on the
        tiles whose header did not survive
EXPECT: the driver's status and each stage's runner status in every world:
  model, rival     every stage ends 0 (the scorer decides: rival's frozen rows FAIL)
  norows           probes print no pixel rows: tx3's first control has no reading, premise rc 25
  soft2            the two first linear rows of tx4 fail (rc 1, no diff line): the second soft
                   failure in a row stops tx4 (rc 24); the driver goes on, tx5 to q139 run
  ctlnohash        --tri-unit rows print no hash: zs2's first control has no reading, rc 25
  nohash           256 x 512 rows print no hash: the second stops zs2 (rc 24), q139 runs
  fault            a 256 x 512 row faults (BIF fault, latched): zs2 stops rc 4, the driver too
  nodump           q139 writes no dump: the first row's kept files lack the scorer's .tri.*.bin,
                   rc 23
Tokens for the scorer's tests only (tests/test_score.py, not EXPECT: their statuses are model's):
  bandy            pixels within (0, 6.4e-4] pixel of a long edge flip on the y sweeps (E914's misses)
  bandout          the same within 0.02 pixel: outside E914's band"""
import hashlib
import json
import os
import shlex
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
import q139model as Q  # noqa: E402
import texmodel as T  # noqa: E402
import zsmodel as Z  # noqa: E402

ALL0 = {"tx3": 0, "tx4": 0, "tx5": 0, "zs2": 0, "q139": 0}
EXPECT = {"model": (0, ALL0), "rival": (0, ALL0),
          "norows": (25, {"tx3": 25}),
          "soft2": (0, dict(ALL0, tx4=24)),
          "ctlnohash": (25, {"tx3": 0, "tx4": 0, "tx5": 0, "zs2": 25}),
          "nohash": (0, dict(ALL0, zs2=24)),
          "fault": (4, {"tx3": 0, "tx4": 0, "tx5": 0, "zs2": 4}),
          "nodump": (23, {"tx3": 0, "tx4": 0, "tx5": 0, "zs2": 0, "q139": 23})}
GREEN, SENT = 0xFF00FF00, 0xDEADBEEF
FAULT = "sgxfive: BIF fault 0x90004 at 0x10000016 stalls job 9, recovering"
PROBE_VAL = {"--temps", "--scratch-pages"}
PROBE_FLAG = {"--coords", "--pixels"}
TRI_VAL = {"--width", "--height", "--max-width", "--max-height", "--wait-ms", "--tri-unit", "--tri-v",
           "--kpoke-render", "--dump-render"}
TRI_FLAG = {"--keep-overflow", "--pixels", "--tri-full", "--keep-going"}


def usage(cmd):
    return dict(rc=2, err="usage: sgxfive-test %s ... (an option the tool does not take)\n" % cmd)


def parse(argv, vals, flags, positional=False):
    """{option: [values]} and the positional arguments, or None on an option the tool refuses."""
    opts, pos, i = {}, [], 1
    while i < len(argv):
        a = argv[i]
        if a in vals and i + 1 < len(argv):
            opts.setdefault(a, []).append(argv[i + 1])
            i += 2
        elif a in flags:
            opts.setdefault(a, []).append(True)
            i += 1
        elif positional and not a.startswith("--"):
            pos.append(a)
            i += 1
        else:
            return None, None
    return opts, pos


def progs():
    out = {}
    for ln in open(os.path.join(KP, "mock/progs.tsv")).read().splitlines():
        if ln and not ln.startswith("#"):
            sha, meta = ln.split("\t", 1)
            out[sha] = json.loads(meta)
    return out


# ---- probe -------------------------------------------------------------------------------------
def probe(argv, world):
    opts, pos = parse(argv, PROBE_VAL, PROBE_FLAG, positional=True)
    if opts is None or len(pos) != 1:
        return usage("probe")
    pages = int(opts.get("--scratch-pages", ["16"])[0], 0)
    if not 16 <= pages <= 64:
        return usage("probe")
    path = pos[0]
    if not os.path.isfile(path):
        return dict(rc=1, err="sgxfive-test: %s: No such file or directory\n" % path)
    meta = progs().get(hashlib.sha256(open(path, "rb").read()).hexdigest())
    if meta is None:
        return dict(rc=1, out="probe: a program the mock does not know\n")
    name = os.path.basename(path).rsplit(".", 1)[0]
    rival = "rival" in world
    ty, w, h, xo, yo, lin = meta["ty"], meta["w"], meta["h"], meta["xo"], meta["yo"], meta["linear"]
    stored = {int(k): v for k, v in meta["stored"]}
    if lin and "soft2" in world and w in (32, 24):
        return dict(rc=1, out="programs asm\nprobe %s: failed: job timed out\n" % name)
    if ty == 5:
        img = T.type5_image("H-DW4B1" if rival else "H-DW8", w, h, stored, xo, yo)
    else:
        if lin:
            hyp = "RASTERP2" if rival else "RASTERW"
        elif ty == 4:
            hyp = "H-BLKZ" if rival else "H-BLKROW"
        elif ty == 3:
            hyp = "H-2W" if rival else ("H-MIN8" if w < 8 else "RASTERW")
        else:
            hyp = "H-2W" if rival else "RASTERW"
        img = [0xA0A1A2A3 if p is None else p for p in T.tex_image(hyp, w, h, xo, yo, lin, dwords=pages * 1024)]
    out = ["programs asm", "probe %s: scratch at 0x3e003000 (%d KiB)" % (name, 4 * pages),
           "probe %s: job time: 624 us" % name]
    if "--pixels" in opts and "norows" not in world:
        out += ["probe %s: row %d: %s" % (name, y, " ".join("%08x" % p for p in img[64 * y:64 * y + 64]))
                for y in range(32)]
    return dict(out="\n".join(out) + "\n")


# ---- tri: the Q260 sweeps ----------------------------------------------------------------------
def rows_text(sp, w, flips=None):
    g, b = "0x%08x" % GREEN, "0x%08x" % Z.BG
    out = []
    for y, (lo, hi) in enumerate(sp):
        px = [b] * lo + [g] * (hi - lo) + [b] * (w - hi)
        for x in (flips or {}).get(y, ()):
            px[x] = b if px[x] == g else g
        out.append("row %d: %s" % (y, " ".join(px)))
    return out


def band_flips(v, sp, w, lim):
    """{y: {x}}: the pixels next to an edge end of a row whose centre lies within (0, lim] pixel of
    an edge of LONG_PX or more, on a sweep of y (the off-grid coordinate is a y): worlds bandy (lim
    E914's band: the misses E914 read, on target y sweeps only) and bandout (lim 0.02: outside it)."""
    off = [i for i, n in enumerate(v) if n % 16]
    if len(off) != 1 or off[0] % 2 == 0 or Z.longest_edge(v, "HA") < Z.LONG_PX:
        return {}
    out = {}
    for y, (lo, hi) in enumerate(sp):
        for x in {lo - 1, lo, hi - 1, hi}:
            if 0 <= x < w:
                dist, ln = Z.nearest_edge(v, "HA", x, y)
                if 0 < dist <= lim and ln >= Z.LONG_PX:
                    out.setdefault(y, set()).add(x)
    return out


def tri_unit(opts, world):
    w, h = int(opts["--width"][0]), int(opts["--height"][0])
    v = [int(x) for x in opts["--tri-v"][0].split(",")]
    if "fault" in world and (w, h) == (256, 512):
        return dict(rc=3, out="tri: render context for targets up to %dx%d\njob: failed\n" % (w, h),
                    kmsg=[FAULT], latch=(4, 0x10000016))
    sp = Z.cover4096(v, w, h, "HU" if "rival" in world else "HA")
    ref = Z.cover4096(v, w, h, "HU")
    nd = len(Z.diff_pixels(sp, ref, w))
    flips = {}
    if "bandy" in world or "bandout" in world:
        flips = band_flips(v, sp, w, Z.BAND_PX if "bandy" in world else 0.02)
        nd += sum(len(x) for x in flips.values())
    out = ["tri: render context for targets up to %dx%d" % (w, h), "tri: vertices4096 %s" % " ".join(map(str, v)),
           "job: ok"]
    if not ("ctlnohash" in world or ("nohash" in world and (w, h) == (256, 512))):
        out.append("target: %dx%d hash 0x%016x" % (w, h, Z.fnv_image(sp, w)))
    out += ["diff: %d of %d pixels" % (nd, w * h), "outside: 0 dwords", "layout: fb 0x3e001000",
            "tri %dx%d #1: %d triangle, %d background, 0 other; wrong %d inside, 0 outside, 0 at edges; 0 if flipped; "
            "guard 0" % (w, h, Z.count(sp), w * h - Z.count(sp), nd), "tri %dx%d #1: 249694 us" % (w, h)]
    if "--pixels" in opts:
        out += rows_text(sp, w, flips)
    out.append("tri: 1 renders ok" if not nd else "tri: 0 of 1 renders ok")
    return dict(rc=1 if nd else 0, out="\n".join(out) + "\n")


# ---- tri: the Q139 dumps -----------------------------------------------------------------------
def headers(w, h, args, order):
    """{slot: (c, r)} of the surviving headers, every tile R7-BLK writes, in the world's order."""
    F = Q.F
    key = Q.KEYS[order]
    tx, ty = F.cdiv(w, 32), F.cdiv(h, 16)
    m1, m2, s = F.words(w, h, args)
    n, bx, by = F.bounds(m1, m2)
    fx, fy = bx[1], by[1]
    ws = []
    for r in range(max(ty, by[-1] + fy)):
        for c in range(max(tx, bx[-1] + fx)):
            mcol, lx = F.place(c, bx)
            mrow, ly = F.place(r, by)
            sl = (mcol * n + mrow) * s + ((ly >> 2) * (fx >> 2) + (lx >> 2)) * 16 + (r & 3) * 4 + (c & 3)
            ws.append((key(r, c, mcol, mrow, n), sl, (c, r)))
    ws.sort(key=lambda t: t[0])
    own = {}
    for _, sl, t in ws:
        own[sl] = t
    return own


def tri_full(opts, world):
    w, h = int(opts["--width"][0]), int(opts["--height"][0])
    pokes = opts.get("--kpoke-render", [])
    args = " ".join("--kpoke-render " + p for p in pokes)
    own = headers(w, h, args, "raster" if "rival" in world else "blkrow")
    tx, ty = -(-w // 32), -(-h // 16)
    drawn = {t for t in own.values() if t[0] < tx and t[1] < ty}
    base, top = 0x4000, max(own) + 1
    td = bytearray(base + 12 * top + 0x1000)
    par = bytearray(0x2000 + 0x80 * top + 0x1000)
    for sl, (c, r) in own.items():
        stream = 0x2000 + 0x80 * sl
        struct.pack_into("<3I", td, base + 12 * sl, (2 * c) << 16 | (2 * r), stream, 0)
        struct.pack_into("<3I", par, stream - 0x1000, 0x88000000 | sl, 0x00001000, 0xC0000000)
    g, b = "0x%08x" % GREEN, "0x%08x" % SENT
    rows, bad = [], 0
    for y in range(h):
        px = [g if (x // 32, y // 16) in drawn else b for x in range(w)]
        bad += px.count(b)
        rows.append("row %d: %s" % (y, " ".join(px)))
    out = ["tri: render context for targets up to %dx%d" % (w, h)]
    out += ["tri: kpoke before render 1: %s" % p.split(":", 1)[1] for p in pokes]
    out += ["job: ok", "target: %dx%d hash 0x%016x" % (w, h, len(drawn) * 0x9E3779B97F4A7C15 & (2 ** 64 - 1)),
            "diff: %d of %d pixels" % (bad, w * h), "outside: 0 dwords", "layout: fb 0x3e001000",
            "tri %dx%d #1: %d triangle, 0 background, %d other; wrong %d inside, 0 outside, 0 at edges; 0 if flipped; "
            "guard 0" % (w, h, w * h - bad, bad, bad)] + rows
    files = {}
    d = opts["--dump-render"][0]
    if "nodump" not in world:
        files = {os.path.join(d, "tri.param.bin"): bytes(par), os.path.join(d, "tri.tadata.bin"): bytes(td)}
        out.append("probe tri: render memory to %s/tri.{param,tadata}.bin (%d, %d bytes)" % (d, len(par), len(td)))
    out.append("tri: 0 of 1 renders ok" if bad else "tri: 1 renders ok")
    return dict(rc=1 if bad else 0, out="\n".join(out) + "\n", files=files)


def tri(argv, world):
    opts, _ = parse(argv, TRI_VAL, TRI_FLAG)
    if opts is None or "--width" not in opts or "--height" not in opts:
        return usage("tri")
    w, h = int(opts["--width"][0]), int(opts["--height"][0])
    if w % 2 or h % 2 or w > 4096 or h > 4096:
        return dict(rc=1, out="tri: render context for targets up to %dx%d\njob: rejected (Invalid argument)\n" % (w, h),
                    err="sgxfive-test: render: Invalid argument\n")
    if "--tri-unit" in opts:
        if "--tri-v" not in opts or opts["--tri-unit"] != ["12"] or "--tri-full" in opts:
            return usage("tri")
        return tri_unit(opts, world)
    if "--tri-full" in opts and "--dump-render" in opts:
        return tri_full(opts, world)
    return usage("tri")


def answer(tool, argv, world):
    if tool != "t4" or not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe":
        return probe(argv, world)
    if argv[0] == "tri":
        return tri(argv, world)
    return usage(argv[0])


if __name__ == "__main__":      # python3 mock/world.py WORLD ARGS...: one answer, for a look by hand
    print(answer("t4", shlex.split(" ".join(sys.argv[2:])), set(sys.argv[1].split(",")))["out"][:2000])
