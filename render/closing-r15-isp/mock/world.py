# SPDX-License-Identifier: MIT
"""mock/world.py: r15-isp's argv-driven fake laptop for kit/session.py mock. answer(tool, argv,
world) sees the tool's name, the argv and the world's tokens, never a case name; it returns None
(the health pair) or dict(rc, out, err, files, kmsg, latch).

As strict as t10 (sgxfive-test at a581c06) on the options the rows use: `tri --keep-going
--wait-ms N [--width W --height H --max-width W --max-height H] [--tri-unit 0..20] [--tri-v
X0,..,Y2] [--tri-z A,B,C (-1 to 2)] [--depth --depth-ctl V --depth-fill F --depth-dump DIR]
[--poke blk:N=V | blk:N^=V]... --pixels` (the depth options need --depth; six int32 coordinates;
targets up to 4096 x 4096; E065's rows name no size: the library's 64 x 64 triangle). Any other
option is a usage refusal (rc 2). Every row is also replayed on t10's library mock by the kit first.

Truths: a depth row (80 x 40, --tri-v, --tri-z, ISP word 0 by --poke blk:1=V) is H-POLYCLIP
(gen/zcut.py: the polygon clipped at z = 1 and 0, the made vertices rounded half away from zero,
E606's coverage); the dump: the buffer's 20 pages pre-filled, the band's dwords the form's (1.0
past the cut, the plane's float32 where drawn); E1045's two rows give their kept hash and depth
line. A library triangle (64 x 64, no --tri-v): 1062 pixels, ISP word 0 bit 15 xor-ed leaves 48 of
them, bits 16 and 17 none (E065, H-NONE), with E065's hashes.

Worlds (EXPECT: the driver's status, {stage: the runner's status}):
  model     the stage runs, 0
  nopix     no tool prints pixel rows: hook_check stops zcut at its first row (24); on_stop = "end"
            ends the session (24)
  nodepth   tri prints no `depth #1` line: zcut-ctl-zhi has no depth_changed reading, the premise
            stops the session (25)
  nohash    tri prints no `target:` line: zcut-ctl-b15 reads no hash, the premise stops (25)
  rejected  every tri prints `job: rejected` and a diff line (E934): zcut's first row is a failure,
            the stage and the session stop (4)
  cutfault  a depth row past [0, 1] other than E1045's two faults the job: zcut-hi1 is an unexpected
            fault, the stage and the session stop (4)
  lost      a cut row ends rc 0 with `job: lost`: hook_check stops zcut at zcut-hi1 (24), the
            session ends
  short     a 64 x 64 row prints 4095 of its 4096 values: hook_check stops zcut at zcut-ctl-b15 (24)
Tokens for the scorer's tests only (tests/test_score.py, not EXPECT): pixcut, nr (the other two
forms), equiv (bits 16 and 17 leave bit 15's 48 pixels), old (the library triangle ignores bit 15:
the control fails)."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
sys.dont_write_bytecode = True
import zcut as Z  # noqa: E402

EXPECT = {
    "model": (0, {"zcut": 0}),
    "nopix": (24, {"zcut": 24}),
    "nodepth": (25, {"zcut": 25}),
    "nohash": (25, {"zcut": 25}),
    "rejected": (4, {"zcut": 4}),
    "cutfault": (4, {"zcut": 4}),
    "lost": (24, {"zcut": 24}),
    "short": (24, {"zcut": 24}),
}
USAGE = "usage: sgxfive-test [--mock[=rev1|harness|none]] ... (mock world: %s)\n"
GREEN, BG = 0xFF00FF00, 0xFF203040
FAULT = "sgxfive: BIF fault 0x90020 at 0x3e10000c (PD 0xf4f2000) stalls job 7, recovering"
TRI_OPTS = {"--keep-going": 0, "--wait-ms": 1, "--width": 1, "--height": 1, "--max-width": 1,
            "--max-height": 1, "--tri-v": 1, "--tri-unit": 1, "--tri-z": 1, "--depth": 0,
            "--depth-ctl": 1, "--depth-fill": 1, "--depth-dump": 1, "--poke": 1, "--pixels": 0}
PAGES = 20
# E1045's two rows (kept): vertices, depths -> hash, the depth line
KEPT = {
    ("0,0,40960,0,0,20480", "1.25,0.25,1.25"): (
        "0x1ae0dc9078287f25",
        "depth #1: 20480 dwords, 4608 changed, 90 distinct; 0xdeadbeef x 15872, 0x3f800000 x 2176, "
        "0x3f7d9998 x 48, 0x3f7a6665 x 48"),
    ("0,0,40960,0,0,20480", "0.25,-0.75,0.25"): (
        "0xead5832ba1f27f25",
        "depth #1: 20480 dwords, 4608 changed, 249 distinct; 0xdeadbeef x 15872, 0x3f800000 x 2688, "
        "0x3e7ccccc x 48, 0x3e766666 x 48"),
}
E065 = {48: "0x7e7562918f5b5125", 0: "0xfc5ff15e0434a325", 1062: "0x99385a04ee01c585"}


def usage(why):
    return dict(rc=2, err=USAGE % why)


def parse(argv, table):
    opts, i = {}, 1
    while i < len(argv):
        a = argv[i]
        if a not in table or i + table[a] >= len(argv):
            return None
        opts.setdefault(a, []).append(argv[i + 1] if table[a] else True)
        i += 1 + table[a]
    return opts


def f32bits(f):
    return struct.unpack("<I", struct.pack("<f", f))[0]


def library_set(n):
    """a stand-in for the library triangle: the first n pixels by x + y, then x"""
    order = sorted(range(4096), key=lambda i: (i % 64 + i // 64, i % 64))
    s = set(order[:n])
    return [i in s for i in range(4096)]


def depth_job(o, world):
    """(drawn image of 80 x 40, dump words, hash, depth line) of a depth row"""
    vt, zt = o["--tri-v"][0], o["--tri-z"][0]
    flat = [int(t) for t in vt.split(",")]
    depths = [float(t) for t in zt.split(",")]
    label = "H-PIXCUT" if "pixcut" in world else "H-POLYCLIP-NR" if "nr" in world else "H-POLYCLIP"
    m = Z.model_of(flat, depths, label)
    words = [0xDEADBEEF] * (PAGES * 1024)
    for i, (k, v) in m["dwords"].items():
        words[i] = v if k == "eq" else f32bits(v)
    drawn = [bool(v) for v in m["drawn"]]
    if (vt, zt) in KEPT:
        hsh, line = KEPT[(vt, zt)]
        return drawn, words, hsh, line
    cnt = {}
    for w in words:
        cnt[w] = cnt.get(w, 0) + 1
    top = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:4]
    line = "depth #1: %d dwords, %d changed, %d distinct; %s" % (
        len(words), sum(1 for w in words if w != 0xDEADBEEF), len(cnt),
        ", ".join("0x%08x x %d" % kv for kv in top))
    return drawn, words, "0x%016x" % (hash(tuple(drawn)) & (2 ** 64 - 1)), line


def tri(argv, world):
    o = parse(argv, TRI_OPTS)
    if o is None:
        return usage("tri: an option t10 does not take here")
    w, h = int(o.get("--width", ["64"])[0]), int(o.get("--height", ["64"])[0])
    if not (0 < w <= 4096 and 0 < h <= 4096):
        return usage("tri: a target up to 4096 x 4096")
    unit = int(o.get("--tri-unit", ["8"])[0])
    if not 0 <= unit <= 20:
        return usage("tri: bad option --tri-unit (0 to 20)")
    if "--tri-v" in o:
        v = [int(t) for t in o["--tri-v"][0].split(",")]
        if len(v) != 6 or any(not -(1 << 31) <= t < (1 << 31) for t in v):
            return usage("tri: bad option --tri-v (six integers, an int32 each)")
    if "--tri-z" in o:
        z = [float(t) for t in o["--tri-z"][0].split(",")]
        if len(z) != 3 or any(not -1 <= t <= 2 for t in z):
            return usage("tri: bad option --tri-z")
    if any(k in o for k in ("--depth-ctl", "--depth-fill", "--depth-dump")) and "--depth" not in o:
        return usage("tri: a depth option without --depth")
    isp0, flips = None, 0
    for p in o.get("--poke", []):
        sp, _, rest = p.partition(":")
        n, _, val = rest.partition("=")
        flip = n.endswith("^")
        n = n.rstrip("^")
        if sp != "blk" or not n.isdigit() or not val:
            return usage("tri: bad option --poke")
        if int(n) == 1:
            if flip:
                flips ^= int(val, 0)
            else:
                isp0 = int(val, 0)
    out = ["tri: render context for targets up to %dx%d" % (w, h)]
    if "--depth" in o:
        out.append("depth: 0x3e001000 %d pages, fill 0xdeadbeef, base 0x3e000000, control %s"
                   % (PAGES, o["--depth-ctl"][0]))
    if "--tri-v" in o:
        out.append("tri: vertices%d %s" % (1 << unit, " ".join(map(str, v))))
    past = "--tri-z" in o and any(t < 0 or t > 1 for t in z)
    ctl = "--tri-v" in o and "--tri-z" in o and (o["--tri-v"][0], o["--tri-z"][0]) in KEPT
    if "cutfault" in world and past and not ctl:
        out.append("job: failed: job faulted, context lost (Input/output error)")
        return dict(rc=1, out="\n".join(out) + "\n", kmsg=[FAULT], latch=(0x90020, 0x3e10000c))
    if "rejected" in world:
        out += ["job: rejected (Invalid argument)", "diff: %d of %d pixels" % (w * h, w * h)]
        return dict(rc=1, out="\n".join(out) + "\n", err="sgxfive-test: render: Invalid argument\n")
    files, line = {}, None
    if "--depth" in o:
        drawn, words, hsh, line = depth_job(o, world)
        if "--depth-dump" in o:
            files[os.path.join(o["--depth-dump"][0], "depth.1.bin")] = struct.pack("<%dI" % len(words), *words)
    else:
        n = 1062
        if flips & 0x8000:
            n = 48 if "old" not in world else 1062
        if flips & 0x30000:
            n = 48 if "equiv" in world else 0
        drawn = library_set(n)
        hsh = E065[n]
    lost = "lost" in world and "--depth" in o and not ctl
    if "nodepth" in world:
        line = None
    out += ["job: lost" if lost else "job: ok"]
    if line:
        out.append(line)
    if "nohash" not in world:
        out.append("target: %dx%d hash %s" % (w, h, hsh))
    out.append("diff: %d of %d pixels" % (sum(drawn) % 7 + 1, w * h))
    n_rows = h
    if "short" in world and w == 64:
        n_px = w * h - 1
    else:
        n_px = w * h
    if "nopix" not in world:
        px = ["0x%08x" % (GREEN if drawn[y * w + x] else BG) for y in range(h) for x in range(w)][:n_px]
        out += ["row %d: %s" % (y, " ".join(px[y * w:(y + 1) * w])) for y in range(n_rows) if px[y * w:(y + 1) * w]]
    out += ["tri %dx%d #1: %d triangle, %d background, 0 other" % (w, h, sum(drawn), w * h - sum(drawn)),
            "tri: 0 of 1 renders ok"]
    return dict(rc=0 if lost else 1, out="\n".join(out) + "\n", files=files)


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if tool != "t10":
        return usage("tool %s" % tool)
    if argv[0] == "tri":
        return tri(argv, world)
    return usage(argv[0])
