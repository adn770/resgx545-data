# SPDX-License-Identifier: MIT
"""mock/world.py: r13-isp's argv-driven fake laptop for kit/session.py mock. answer(tool, argv,
world) sees the tool's name, the argv and the world's tokens, never a case name; it returns None
(the health pair) or dict(rc, out, err, files, kmsg, latch).

As strict as t10 (sgxfive-test at a581c06) on the options the rows use: `probe --tri pixpds:12
--temps 32 --pixels --width W --height H --tri-v ... --vtx-coords 2 --cmd 16=V --slot vtxuse=F
--slot pixel=F FILE` (every FILE must exist; --vtx-coords 2 needs the vtxuse slot) and `tri
--keep-going --wait-ms N --width W --height H --max-width W --max-height H [--tri-unit 0..20]
--tri-v X0,..,Y2 --pixels` (--tri-unit needs --tri-v; six int32 coordinates). Any other option is
a usage refusal (rc 2). Every row is also replayed on t10's library mock by the kit first.

Truths: q201, H-SAMPLE0 (E1018's coverage at byte 0's point, every value read there: src0 the
pixel + (lo, hi)/16, cset the clip coordinate of that point, as float32); q261 and far, E1012's
clip with G = 18, a = 20, g = 16 (gen/clip.py's engine, the vertices as the tool submits them).

Worlds (EXPECT: the driver's status, {stage: the runner's status}):
  model        every stage 0
  nopix        no tool prints pixel rows: hook_check stops q201 at its first row (24); q261's
               first control has no `pixels` reading, the premise stops the session (25)
  rowsmissing  a probe with byte 0 other than 0x88 and 0x26 prints 63 rows: hook_check stops
               q201 (24), the driver goes on (q261, far 0)
  cmdrefused   the kernel refuses byte 0 other than 0x88 (`failed: Invalid argument`, rc 3): an
               unexplained failure at q201's 0x26 control, the session stops (4)
  rejected     every tri prints `job: rejected` and a diff line (E934): a failure under
               expectdiff, q261 and the session stop (4)
  farfault     a vertex past 2^25 pixels faults the job: far's first held-out row is an
               unexpected fault, far and the session stop there (4)
  farnojob     a vertex past 2^25 pixels ends rc 0 with `job: lost` (class ok): hook_check stops
               far (24) at its first held-out row
Tokens for the scorer's tests only (tests/test_score.py, not EXPECT): centre, swap, split (q201's
rivals), exact (q261 and far without the clip), g20 (G = 20), abs (an absolute guard h = 82)."""
import os
import struct
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
sys.dont_write_bytecode = True
import clip as C  # noqa: E402
import q201 as Q  # noqa: E402

STAGES = {"q201": 0, "q261": 0, "far": 0}
EXPECT = {
    "model": (0, STAGES),
    "nopix": (25, {"q201": 24, "q261": 25}),
    "rowsmissing": (0, dict(STAGES, q201=24)),
    "cmdrefused": (4, {"q201": 4}),
    "rejected": (4, {"q201": 0, "q261": 4}),
    "farfault": (4, dict(STAGES, far=4)),
    "farnojob": (0, dict(STAGES, far=24)),
}
USAGE = "usage: sgxfive-test [--mock[=rev1|harness|none]] ... (mock world: %s)\n"
GREEN, BG = 0xFF00FF00, 0xFF203040
FAULT = "sgxfive: BIF fault 0x90020 at 0x3e10000c (PD 0xf4f2000) stalls job 7, recovering"
PROBE_OPTS = {"--tri": 1, "--temps": 1, "--pixels": 0, "--width": 1, "--height": 1, "--tri-v": 1,
              "--vtx-coords": 1, "--cmd": 1, "--slot": 1}
TRI_OPTS = {"--keep-going": 0, "--wait-ms": 1, "--width": 1, "--height": 1, "--max-width": 1,
            "--max-height": 1, "--tri-v": 1, "--tri-unit": 1, "--pixels": 0}


def usage(why):
    return dict(rc=2, err=USAGE % why)


def parse(argv, table, positional=0):
    """(opts {name: [values]}, positionals) or None for an option the tool would refuse here"""
    opts, pos, i = {}, [], 1
    while i < len(argv):
        a = argv[i]
        if not a.startswith("--") and len(pos) < positional:
            pos.append(a)
            i += 1
            continue
        if a not in table or i + table[a] >= len(argv):
            return None
        opts.setdefault(a, []).append(argv[i + 1] if table[a] else True)
        i += 1 + table[a]
    return opts, pos


def f32hex(x):
    return struct.unpack("<I", struct.pack("<f", float(x)))[0]


# ---- q201: t10 probe --tri ----------------------------------------------------------------------
def probe(argv, world):
    p = parse(argv, PROBE_OPTS, positional=1)
    if p is None:
        return usage("probe: an option t10 does not take here")
    o, pos = p
    if o.get("--tri") != ["pixpds:12"] or len(pos) != 1 or "--pixels" not in o:
        return usage("probe --tri pixpds:12 FILE --pixels")
    w, h = int(o["--width"][0]), int(o["--height"][0])
    slots = dict(s.split("=", 1) for s in o.get("--slot", []))
    for f in list(slots.values()) + pos:
        if not os.path.isfile(f):
            return dict(rc=1, out="sgxfive-test: cannot open %s: No such file or directory\n" % f)
    if o.get("--vtx-coords") != ["2"] or "vtxuse" not in slots or "pixel" not in slots:
        return usage("probe: --vtx-coords 2 with a vtxuse and a pixel slot")
    cmds = dict(c.split("=", 1) for c in o.get("--cmd", []))
    if set(cmds) != {"16"}:
        return usage("probe: --cmd 16= only")
    b = int(cmds["16"], 0)
    if b >> 8:
        return usage("probe: bytes 1 to 3 of word 16 stay 0")
    tri = tuple(int(t) for t in o["--tri-v"][0].split(","))
    name = os.path.basename(pos[0])[:-4]
    head = ["programs asm", "probe %s: scratch at 0x3e01a000 (64 KiB)" % name,
            "probe %s: tri %dx%d (2 coordinates, command words 16), vtxuse pixel pixpds replaced" % (name, w, h),
            "probe %s: vertices256 %s" % (name, " ".join(map(str, tri)))]
    if "cmdrefused" in world and b != 0x88:
        head.append("probe %s: failed: Invalid argument" % name)
        return dict(rc=3, out="\n".join(head) + "\n", err="sgxfive-test: render: Invalid argument\n")
    prog = "cset" if os.path.basename(pos[0]) == "cset.bin" else "src0"
    comp = "x" if os.path.basename(slots["pixel"]) == "pix_pa0.bin" else "y"
    model = ("H-CENTRE" if "centre" in world else "H-SWAP" if "swap" in world else
             "H-SPLIT" if "split" in world else "H-SAMPLE0")
    s = Q.offset(model, b, prog, comp)
    cov = Q.coverage(b, tri, w, h)
    px = []
    for i, c in enumerate(cov):
        if not c:
            px.append(BG)
            continue
        pos_ = (i % w if comp == "x" else i // w) + s
        px.append(f32hex(pos_ / Fraction(w, 2) - 1 if prog == "cset" else pos_))
    out = head + ["probe %s: o0 mixed other x%d" % (name, w * h)]
    nrows = h - 1 if "rowsmissing" in world and b not in (0x88, 0x26) else h
    if "nopix" not in world:
        out += ["probe %s: row %d: %s" % (name, y, " ".join("%08x" % v for v in px[y * w:(y + 1) * w]))
                for y in range(nrows)]
    return dict(rc=0, out="\n".join(out) + "\n")


# ---- q261, far: t10 tri --tri-v ----------------------------------------------------------------
def tri(argv, world):
    p = parse(argv, TRI_OPTS)
    if p is None:
        return usage("tri: an option t10 does not take here")
    o, _ = p
    w, h = int(o["--width"][0]), int(o["--height"][0])
    if "--tri-v" not in o:
        return usage("tri: --tri-v")
    unit = int(o.get("--tri-unit", ["8"])[0])
    if not 0 <= unit <= 20:
        return usage("tri: bad option --tri-unit (0 to 20)")
    v = [int(t) for t in o["--tri-v"][0].split(",")]
    if len(v) != 6 or any(not -(1 << 31) <= t < (1 << 31) for t in v):
        return usage("tri: bad option --tri-v (six integers, an int32 each)")
    V3 = [(v[0], v[1]), (v[2], v[3]), (v[4], v[5])]
    V = C.variants(V3, unit, w)[0]
    far = max(max(abs(x), abs(y)) for x, y in V) > 256 * (1 << 25)
    out = ["tri: render context for targets up to %dx%d" % (w, h),
           "tri: vertices%d %s" % (1 << unit, " ".join(map(str, v)))]
    if far and "farfault" in world:
        out.append("job: failed: job faulted, context lost (Input/output error)")
        return dict(rc=1, out="\n".join(out) + "\n", kmsg=[FAULT], latch=(0x90020, 0x3e10000c))
    if "rejected" in world:
        out += ["job: rejected (Invalid argument)", "diff: %d of %d pixels" % (w * h, w * h)]
        return dict(rc=1, out="\n".join(out) + "\n", err="sgxfive-test: render: Invalid argument\n")
    if "exact" in world:
        b = None
    elif "abs" in world:
        b = C.bounds("abs", 82, w)
    else:
        G = 20 if "g20" in world else 18
        b = (-20, w + G, -16, w + 16)
    drawn = C.image(V, b, w)
    job = "job: lost" if far and "farnojob" in world else "job: ok"
    out += [job, "target: %dx%d hash 0x%016x" % (w, h, hash(tuple(drawn)) & (2 ** 64 - 1)),
            "diff: %d of %d pixels" % (sum(drawn) % 7, w * h)]
    if "nopix" not in world:
        out += ["row %d: %s" % (y, " ".join("0x%08x" % (GREEN if drawn[y * w + x] else BG) for x in range(w)))
                for y in range(h)]
    out += ["tri %dx%d #1: %d triangle, %d background, 0 other" % (w, h, sum(drawn), w * h - sum(drawn)),
            "tri: 0 of 1 renders ok"]
    return dict(rc=0 if job != "job: ok" else 1, out="\n".join(out) + "\n")


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if tool != "t10":
        return usage("tool %s" % tool)
    if argv[0] == "probe":
        return probe(argv, world)
    if argv[0] == "tri":
        return tri(argv, world)
    return usage(argv[0])
