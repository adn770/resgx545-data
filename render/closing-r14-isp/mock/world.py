# SPDX-License-Identifier: MIT
"""mock/world.py: r14-isp's argv-driven fake laptop for kit/session.py mock. answer(tool, argv,
world) sees the tool's name, the argv and the world's tokens, never a case name; it returns None
(the health pair) or dict(rc, out, err, files, kmsg, latch).

As strict as t10 (sgxfive-test at a581c06) on the options the rows use: `tri --keep-going
--wait-ms N --width W --height H --max-width W --max-height H [--tri-unit 0..20] --tri-v X0,..,Y2
[--tri-z A,B,C (-1 to 2)] [--depth --depth-ctl V --depth-fill F --depth-dump DIR] [--poke
blk:N=V]... --pixels` (--tri-unit needs --tri-v; six int32 coordinates; the depth options need
--depth; a poke other than blk:N=V is refused; targets up to 4096 x 4096). Any other option is a
usage refusal (rc 2). Every row is also replayed on t10's library mock by the kit first.

Truths: g14 and clipr, H-VP (a quarter of the viewport past each edge) with the clip vertex
rounded half up and the vertices as E607 (gen/guard.py's engine, the vertices as the tool submits
them, through the poked viewport); wind, H-CULL (bits 15 to 17 remove the forward winding only)
and H-CLAMP. The dump: the buffer's 20 pages pre-filled, the tile dwords the plane's float32.

Worlds (EXPECT: the driver's status, {stage: the runner's status}):
  model     every stage 0
  nopix     no tool prints pixel rows: hook_check stops every stage at its first row (24); clipr's
            stop ends the session (24, on_stop = "end")
  nodepth   tri prints no `depth #1` line: wind's first control has no depth_changed reading, the
            premise stops the session (25)
  rejected  every tri prints `job: rejected` and a diff line (E934): wind's first row is a failure,
            the stage and the session stop (4)
  vpfault   a row poking the viewport faults the job: g14's first poked row is an unexpected fault,
            g14 and the session stop there (4)
  vplost    a row poking the viewport ends rc 0 with `job: lost`: hook_check stops g14 (24) at its
            first poked row, the driver goes on to clipr (0)
  i32fault  a vertex at 2^31 - 1 or -2^31 pixels faults: clipr's first int32 row stops it and the
            session (4)
  i32lost   the same rows end rc 0 with `job: lost`: hook_check stops clipr (24), the session ends
  wide      a 4096-wide target prints 15 of its 16 rows: hook_check stops clipr at w4-d (24), the
            session ends (on_stop = "end")
Tokens for the scorer's tests only (tests/test_score.py, not EXPECT): tgt (the guard of the
target), min4, kill (H-KILL), zclip, raw (the z models), ha, rne, tr (the clip vertex's rounding),
inhu (vertices half up at both signs)."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
sys.dont_write_bytecode = True
import guard as G  # noqa: E402
import wind as WD  # noqa: E402

STAGES = {"wind": 0, "g14": 0, "clipr": 0}
EXPECT = {
    "model": (0, STAGES),
    "nopix": (24, {"wind": 24, "g14": 24, "clipr": 24}),
    "nodepth": (25, {"wind": 25}),
    "rejected": (4, {"wind": 4}),
    "vpfault": (4, {"wind": 0, "g14": 4}),
    "vplost": (0, dict(STAGES, g14=24)),
    "i32fault": (4, dict(STAGES, clipr=4)),
    "i32lost": (24, dict(STAGES, clipr=24)),
    "wide": (24, dict(STAGES, clipr=24)),
}
USAGE = "usage: sgxfive-test [--mock[=rev1|harness|none]] ... (mock world: %s)\n"
GREEN, BG = 0xFF00FF00, 0xFF203040
FAULT = "sgxfive: BIF fault 0x90020 at 0x3e10000c (PD 0xf4f2000) stalls job 7, recovering"
TRI_OPTS = {"--keep-going": 0, "--wait-ms": 1, "--width": 1, "--height": 1, "--max-width": 1,
            "--max-height": 1, "--tri-v": 1, "--tri-unit": 1, "--tri-z": 1, "--depth": 0,
            "--depth-ctl": 1, "--depth-fill": 1, "--depth-dump": 1, "--poke": 1, "--pixels": 0}
PAGES = 20


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


def f32(u):
    return struct.unpack("<f", struct.pack("<I", u))[0]


def dump_words(depths, model):
    w = [0xDEADBEEF] * (PAGES * 1024)
    m = WD.zmodel(depths, model)
    for i, (k, v) in m["dwords"].items():
        w[i] = v if k == "eq" else WD.bits_of(v)
    return w, m["drawn"]


def wind_job(o, world, w, h, out):
    """a depth row: (drawn image, dump words, hash)"""
    v = [int(t) for t in o["--tri-v"][0].split(",")]
    z = [float(t) for t in o["--tri-z"][0].split(",")]
    order = "rev" if v == [0, 0, 0, 20480, 40960, 0] else "fwd"
    depths = z if order == "fwd" else [z[0], z[2], z[1]]
    isp0 = int([p for p in o.get("--poke", []) if p.startswith("blk:1=")][0][6:], 0)
    culled = bool(isp0 & 0x38000) and (order == "fwd" or "kill" in world)
    model = "H-ZCLIP" if "zclip" in world else "H-RAW" if "raw" in world else "H-CLAMP"
    words, drawn = dump_words(depths, model)
    if culled:
        words = [0xDEADBEEF] * (PAGES * 1024)
        for y in range(WD.TH):
            for x in range(WD.TW):
                words[WD.store_dword(x, y)] = WD.ONE
        drawn = [False] * (w * h)
        hsh = WD.HASH_BG
    else:
        hsh = WD.HASH_RAMP if all(drawn) else "0x%016x" % (hash(tuple(drawn)) & (2 ** 64 - 1))
    return drawn, words, hsh


def tri(argv, world):
    o = parse(argv, TRI_OPTS)
    if o is None:
        return usage("tri: an option t10 does not take here")
    w, h = int(o["--width"][0]), int(o["--height"][0])
    if not (0 < w <= 4096 and 0 < h <= 4096) or "--tri-v" not in o:
        return usage("tri: a target up to 4096 x 4096 and --tri-v")
    unit = int(o.get("--tri-unit", ["8"])[0])
    if not 0 <= unit <= 20:
        return usage("tri: bad option --tri-unit (0 to 20)")
    v = [int(t) for t in o["--tri-v"][0].split(",")]
    if len(v) != 6 or any(not -(1 << 31) <= t < (1 << 31) for t in v):
        return usage("tri: bad option --tri-v (six integers, an int32 each)")
    if "--tri-z" in o:
        z = [float(t) for t in o["--tri-z"][0].split(",")]
        if len(z) != 3 or any(not -1 <= t <= 2 for t in z):
            return usage("tri: bad option --tri-z")
    if any(k in o for k in ("--depth-ctl", "--depth-fill", "--depth-dump")) and "--depth" not in o:
        return usage("tri: a depth option without --depth")
    vp = list(G.default_vp(w, h))
    for p in o.get("--poke", []):
        sp, _, rest = p.partition(":")
        n, _, val = rest.partition("=")
        if sp != "blk" or not n.isdigit() or not val:
            return usage("tri: bad option --poke")
        if 6 <= int(n) <= 9:
            vp[int(n) - 6] = G.F(f32(int(val, 0)))
    poked = any(p.startswith(("blk:6=", "blk:7=", "blk:8=", "blk:9=")) for p in o.get("--poke", []))
    i32 = any(abs(t) >= (1 << 31) - 1 for t in v)
    out = ["tri: render context for targets up to %dx%d" % (w, h)]
    if "--depth" in o:
        out.append("depth: 0x3e001000 %d pages, fill 0xdeadbeef, base 0x3e000000, control %s"
                   % (PAGES, o["--depth-ctl"][0]))
    out.append("tri: vertices%d %s" % (1 << unit, " ".join(map(str, v))))
    if (poked and "vpfault" in world) or (i32 and "i32fault" in world):
        out.append("job: failed: job faulted, context lost (Input/output error)")
        return dict(rc=1, out="\n".join(out) + "\n", kmsg=[FAULT], latch=(0x90020, 0x3e10000c))
    if "rejected" in world:
        out += ["job: rejected (Invalid argument)", "diff: %d of %d pixels" % (w * h, w * h)]
        return dict(rc=1, out="\n".join(out) + "\n", err="sgxfive-test: render: Invalid argument\n")
    files = {}
    if "--depth" in o:
        drawn, words, hsh = wind_job(o, world, w, h, out)
        if "nodepth" not in world:
            ch = sum(1 for x in words if x != 0xDEADBEEF)
            out.append("depth #1: %d dwords, %d changed, %d distinct" % (len(words), ch, len(set(words))))
        if "--depth-dump" in o:
            files[os.path.join(o["--depth-dump"][0], "depth.1.bin")] = struct.pack("<%dI" % len(words), *words)
    else:
        b = G.boxes(w, h, tuple(vp))
        box = b["H-TGT"] if "tgt" in world else b["H-MIN4"] if "min4" in world else b["H-VP"]
        rule = "HA" if "ha" in world else "RNE" if "rne" in world else "TR" if "tr" in world else "HU"
        vs = G.variants(v, unit, w, h, tuple(vp), "HU" if "inhu" in world else "E607")
        drawn = G.image(vs[0], box, w, h, rule)
        hsh = "0x%016x" % (hash(tuple(drawn)) & (2 ** 64 - 1))
    lost = (poked and "vplost" in world) or (i32 and "i32lost" in world)
    out += ["job: lost" if lost else "job: ok", "target: %dx%d hash %s" % (w, h, hsh),
            "diff: %d of %d pixels" % (sum(drawn) % 7, w * h)]
    rows = h - 1 if w == 4096 and "wide" in world else h
    if "nopix" not in world:
        out += ["row %d: %s" % (y, " ".join("0x%08x" % (GREEN if drawn[y * w + x] else BG) for x in range(w)))
                for y in range(rows)]
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
