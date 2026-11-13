# SPDX-License-Identifier: MIT
"""mock/world.py: r10-geo's argv-driven fake laptop for kit/session.py mock. answer(tool, argv,
world) sees the tool's name, the argv, the world's tokens and, for t9, the two knobs it reads
(render_bg_layer, render_bg_src: the fake debugfs FAKE_DBGREAL the runner writes); never a case
name. It returns None (the health pair) or dict(rc, out, err, files, kmsg, latch).

As strict as the tools on the options the rows use: t4 (sgxfive-test at 4623753) takes `tri` with
--tri-v / --tri-unit (5 to 20, coordinates in [-2^30, 2^30)) and --pixels (pivot), or --tri-full
--pixels --kpoke-render 1:ta:N=V --dump-render DIR (q139c, DIR must exist); t9 (97447b04) takes
`tri --bg-layer --pixels --keep-going --dump-render DIR --kpoke-render 1:bg:3..22=V` and refuses
the option without the knob or the knob without the option (r9-k1's world). Any other option is a
usage refusal (rc 2). Every row is also replayed on its tool's library mock by the kit first.

Truths: pivot, H-PIVOT with D = 100 pixels (the far vertex's y moved by 100: the coverage of the
moved triangle, gen/far.py's integer rule); q139c, H-EVEN's surviving headers (gen/q139even.py)
with flag bit 7 on the last target tile's header in block order, a tile drawn iff its header
survives at or before it (H-LAST); bgw, H-INERT (every background pixel its own texel).

Worlds (EXPECT: the driver's status, {stage: the runner's status}):
  model     every stage 0
  nopix     tri prints no pixel rows: piv-ctl has no `pixels` reading, the premise stops the
            session at pivot (25)
  farfault  a vertex past 2^23 pixels faults the job: pivot's first such row is an unexpected
            fault, the session stops (4)
  rejected  every t4 tri prints `job: rejected` and a diff line (E934): a failure under expectdiff,
            the session stops at pivot (4)
  nolayer   a poked t9 row prints no bg-layer line: hook_check stops bgw (24), q139c runs (0)
  nohash    a poked q139c row prints no hash: the second stops q139c (24)
  fault     a poked q139c row faults: q139c and the session stop (4)
  nodump    q139c's first row keeps no dump: the runner stops q139c (23)
Tokens for the scorer's tests only (tests/test_score.py, not EXPECT): exact (pivot D = 0), d500
(D = 500), rival (q139c slots off H-EVEN's), noflag (no header with bit 7), scale (bgw under
H-SCALE0)."""
import os
import struct
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import bgl_model as M  # noqa: E402
import bgw as BGW  # noqa: E402
import far as FA  # noqa: E402
import q139even as E  # noqa: E402
import q139model as Q  # noqa: E402

ALL0 = {"pivot": 0, "bgw": 0, "q139c": 0}
EXPECT = {
    "model": (0, ALL0),
    "nopix": (25, {"pivot": 25}),
    "farfault": (4, {"pivot": 4}),
    "rejected": (4, {"pivot": 4}),
    "nolayer": (0, dict(ALL0, bgw=24)),
    "nohash": (0, dict(ALL0, q139c=24)),
    "fault": (4, dict(ALL0, q139c=4)),
    "nodump": (23, dict(ALL0, q139c=23)),
}
USAGE = "usage: sgxfive-test [--mock[=rev1|harness|none]] ... (mock world: %s)\n"
GREEN, SENT = 0xFF00FF00, 0xDEADBEEF
FAULT = "sgxfive: BIF fault 0x90020 at 0x3e10000c (PD 0xf4f2000) stalls job 7, recovering"
T4_OPTS = {"--keep-going": 0, "--pixels": 0, "--tri-full": 0, "--wait-ms": 1, "--width": 1,
           "--height": 1, "--max-width": 1, "--max-height": 1, "--tri-v": 1, "--tri-unit": 1,
           "--kpoke-render": 1, "--dump-render": 1}
T9_OPTS = {"--bg-layer": 0, "--pixels": 0, "--keep-going": 0, "--dump-render": 1,
           "--kpoke-render": 1}


def usage(why):
    return dict(rc=2, err=USAGE % why)


def parse(argv, table):
    """(opts {name: [values]}) or None for an option the tool would refuse here."""
    opts, i = {}, 1
    while i < len(argv):
        a = argv[i]
        if a not in table or i + table[a] >= len(argv):
            return None
        opts.setdefault(a, []).append(argv[i + 1] if table[a] else True)
        i += 1 + table[a]
    return opts


# ---- pivot: t4 tri --tri-v ---------------------------------------------------------------------
def pivot_tri(o, world):
    w, h = int(o["--width"][0]), int(o["--height"][0])
    unit = int(o.get("--tri-unit", ["8"])[0])
    if "--tri-v" not in o or not 5 <= unit <= 20 or "--tri-full" in o or "--kpoke-render" in o:
        return usage("tri: --tri-unit 5 to 20 with --tri-v, no --tri-full")
    v = [int(t) for t in o["--tri-v"][0].split(",")]
    if len(v) != 6 or any(not -(1 << 30) <= t < 1 << 30 for t in v):
        return usage("tri: a --tri-v coordinate out of range")
    g = [Fraction(t * 256, 1 << unit) for t in v]
    vs = [(g[0], g[1]), (g[2], g[3]), (g[4], g[5])]
    far = max(range(3), key=lambda i: abs(vs[i][0]) + abs(vs[i][1]))
    big = max(abs(vs[far][0]), abs(vs[far][1])) >= 256 * (1 << 23)
    out = ["tri: render context for targets up to %dx%d" % (w, h)]
    if big and max(abs(vs[far][0]), abs(vs[far][1])) > 256 * (1 << 23) and "farfault" in world:
        out.append("job: failed: job faulted, context lost (Input/output error)")
        return dict(rc=1, out="\n".join(out) + "\n", kmsg=[FAULT], latch=(0x90020, 0x3e10000c))
    if "rejected" in world:
        out += ["job: rejected (Invalid argument)", "diff: %d of %d pixels" % (w * h, w * h)]
        return dict(rc=1, out="\n".join(out) + "\n", err="sgxfive-test: render: Invalid argument\n")
    D = 0 if "exact" in world else 500 if "d500" in world else 100
    if big:
        vs[far] = (vs[far][0], vs[far][1] + 256 * D)
    iv = [(int(x), int(y)) for x, y in vs]
    cov = FA.coverage(iv)
    drawn = [cov[(i % 64, i // 64)][0] for i in range(4096)]
    out += ["job: ok", "target: %dx%d hash 0x%016x" % (w, h, hash(tuple(drawn)) & (2 ** 64 - 1)),
            "diff: %d of %d pixels" % (sum(drawn), w * h)]
    if "nopix" not in world:
        out += ["row %d: %s" % (y, " ".join("0x%08x" % (GREEN if drawn[y * 64 + x] else 0)
                                            for x in range(64))) for y in range(64)]
    out += ["tri %dx%d #1: %d triangle, %d background, 0 other" % (w, h, sum(drawn), 4096 - sum(drawn)),
            "tri: 0 of 1 renders ok"]
    return dict(rc=1, out="\n".join(out) + "\n")


# ---- q139c: t4 tri --tri-full ------------------------------------------------------------------
def headers(w, h, args, world):
    own = E.headers(w, h, args, "H-EVEN")
    if "rival" in world:
        own = {sl - (sl & 15) + (c & 3) * 4 + (r & 3): (c, r) for sl, (c, r) in own.items()}
    return own


def q139_tri(o, world):
    w, h = int(o["--width"][0]), int(o["--height"][0])
    if "--tri-v" in o or "--tri-unit" in o or "--dump-render" not in o:
        return usage("tri --tri-full: no --tri-v, a --dump-render")
    pokes = o.get("--kpoke-render", [])
    if any(not p.startswith("1:ta:") for p in pokes):
        return usage("tri --tri-full: --kpoke-render 1:ta:N=V only")
    if not os.path.isdir(o["--dump-render"][0]):
        return dict(rc=1, err="sgxfive-test: %s: No such file or directory\n" % o["--dump-render"][0])
    if pokes and "fault" in world:
        return dict(rc=3, out="tri: render context for targets up to %dx%d\njob: failed\n" % (w, h),
                    kmsg=[FAULT], latch=(0x90020, 0x3e10000c))
    args = " ".join("--kpoke-render " + p for p in pokes)
    own = headers(w, h, args, world)
    tx, ty = -(-w // 32), -(-h // 16)
    n = E.geometry(w, h, args)[0]
    key = Q.KEYS["blkrow"]
    tgt = {sl: t for sl, t in own.items() if t[0] < tx and t[1] < ty}
    last = max(tgt, key=lambda sl: key(tgt[sl][1], tgt[sl][0], 0, 0, n))
    drawn = {t for sl, t in tgt.items() if sl <= last}
    base, top = 0x4000, max(own) + 1
    td = bytearray(base + 12 * top + 0x1000)
    par = bytearray(0x2000 + 0x80 * top + 0x1000)
    for sl, (c, r) in own.items():
        stream = 0x2000 + 0x80 * sl
        flag = 0x80 if sl == last and "noflag" not in world else 0
        struct.pack_into("<3I", td, base + 12 * sl, flag << 24 | (2 * c) << 16 | (2 * r), stream, 0)
        struct.pack_into("<3I", par, stream - 0x1000, 0x88000000 | sl, 0x00001000, 0xC0000000)
    g, b = "0x%08x" % GREEN, "0x%08x" % SENT
    rows, bad = [], 0
    for y in range(h):
        px = [g if (x // 32, y // 16) in drawn else b for x in range(w)]
        bad += px.count(b)
        rows.append("row %d: %s" % (y, " ".join(px)))
    out = ["tri: render context for targets up to %dx%d" % (w, h)]
    out += ["tri: kpoke before render 1: %s" % p.split(":", 1)[1] for p in pokes]
    out += ["job: ok"]
    if not ("nohash" in world and pokes):
        out.append("target: %dx%d hash 0x%016x" % (w, h, len(drawn) * 0x9E3779B97F4A7C15 & (2 ** 64 - 1)))
    out += ["diff: %d of %d pixels" % (bad, w * h), "outside: 0 dwords", "layout: fb 0x3e001000",
            "tri %dx%d #1: %d triangle, 0 background, %d other" % (w, h, w * h - bad, bad)] + rows
    files = {}
    d = o["--dump-render"][0]
    if not ("nodump" in world and not pokes and w == 256):
        files = {os.path.join(d, "tri.param.bin"): bytes(par), os.path.join(d, "tri.tadata.bin"): bytes(td)}
        out.append("probe tri: render memory to %s/tri.{param,tadata}.bin (%d, %d bytes)" % (d, len(par), len(td)))
    out.append("tri: 0 of 1 renders ok" if bad else "tri: 1 renders ok")
    return dict(rc=1 if bad else 0, out="\n".join(out) + "\n", files=files)


# ---- bgw: t9 tri --bg-layer --------------------------------------------------------------------
def knobs():
    d = os.environ.get("FAKE_DBGREAL")
    vals = {"render_bg_layer": "N", "render_bg_src": "0"}
    for k in vals:
        p = os.path.join(d, k) if d else None
        if p and os.path.exists(p):
            vals[k] = open(p).read().strip() or vals[k]
    return vals["render_bg_layer"][:1] in ("Y", "y", "1"), int(vals["render_bg_src"], 0)


def bg_tri(argv, world):
    o = parse(argv, T9_OPTS)
    if o is None:
        return usage("an option tri does not take here")
    layer = "--bg-layer" in o
    on, src = knobs()
    if layer and (not on or src != M.SRC):
        return dict(rc=2, err="usage: sgxfive-test --bg-layer: debugfs render_bg_layer is N\n")
    if on and not layer:
        return dict(rc=2, err="usage: sgxfive-test --bg-layer: debugfs render_bg_layer is Y\n")
    pokes = {}
    for s in o.get("--kpoke-render", []):
        if not s.startswith("1:bg:"):
            return usage("a --kpoke-render that is not 1:bg:3..22")
        w, v = s[5:].split("=")
        if not 3 <= int(w) <= 22:
            return usage("a --kpoke-render that is not 1:bg:3..22")
        pokes[int(w)] = int(v, 0)
    mask = M.load_mask()
    pred = None
    if "scale" in world and pokes:
        (w, v), = pokes.items()
        f = struct.unpack("<f", struct.pack("<I", v))[0]
        pred = BGW.predict("H-SCALE0", w, f, mask)
    bg = {}
    for x, y in mask:
        t = pred.get((x, y), (0, 0)) if pred is not None else (x, y)
        bg[(x, y)] = M.texel(*t) if layer else M.BG
    diff = sum(1 for p in bg if bg[p] != (M.texel(*p) if layer else M.BG))
    inplace = sum(1 for p in bg if bg[p] == M.texel(*p))
    head = "bg-layer: source 0x%08x 64x64 RGBA8888, knob Y\n" % M.SRC if layer and not (
        "nolayer" in world and pokes) else ""
    out = head + "tri: render context for targets up to 64x64\njob: ok\n"
    out += "target: 64x64 hash 0x%016x\ndiff: %d of 4096 pixels\noutside: 0 dwords\n" % (
        hash(tuple(sorted(bg.items()))) & 0xffffffffffffffff, diff)
    if "--pixels" in o:
        out += "".join("row %d: %s\n" % (y, " ".join("0x%08x" % bg.get((x, y), M.TRI) for x in range(64)))
                       for y in range(64))
    out += "tri 64x64 #1: %d triangle, %d background, 0 other; wrong 0 inside, %d outside, 0 at edges; " \
        "0 if flipped; guard 0" % (4096 - len(bg), len(bg), diff)
    if layer:
        out += "; %d layer texels in place, %d elsewhere, 0 not a texel" % (inplace, len(bg) - inplace)
    out += "\n"
    files = {}
    for dd in o.get("--dump-render", []):
        ob = M.obj(pokes)
        words = [0x04000004, 0x00030001, 0x0c0000f0] + [ob[k] for k in range(3, 23)]
        files[os.path.join(dd, "tri.param.bin")] = bytes(M.OBJ_OFF) + struct.pack("<23I", *words)
        files[os.path.join(dd, "tri.tadata.bin")] = bytes(64)
        out += "probe tri: render memory to %s/tri.{param,tadata}.bin (%d, 64 bytes)\n" % (dd, M.OBJ_OFF + 92)
    out += "tri: 1 renders ok\n" if diff == 0 else "tri: 0 of 1 renders ok\n"
    return dict(rc=0 if diff == 0 else 1, out=out, files=files)


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None                      # the health pair (t4): an exact draw
    if argv[0] != "tri":
        return usage("only tri runs rows")
    if tool == "t9":
        return bg_tri(argv, world)
    if tool != "t4":
        return usage("an unknown tool")
    o = parse(argv, T4_OPTS)
    if o is None or "--width" not in o or "--height" not in o:
        return usage("an option tri does not take here")
    if "--tri-full" in o:
        return q139_tri(o, world)
    return pivot_tri(o, world)
