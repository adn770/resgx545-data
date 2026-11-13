# SPDX-License-Identifier: MIT
"""mock/world.py: r10-zls's argv-driven fake laptop for kit/session.py mock. answer(tool, argv,
world) sees the tool's name, the argv and the world's tokens, never a case name. It is as strict
as the bound tools on the options the rows use: t4 (sgxfive-test at 4623753) takes the zst2
options and no --kpoke-render, t9 (97447b04) the zbg/zw options and no stencil buffer; any other
option, a --tri-z depth outside [0, 1] (t4) or [-1, 2] (t9), --tri-v with --tri-full,
--depth-* or --stencil without --depth, --stencil-* without --stencil, and --depth-pages below
the target's own pages (depth_min_pages) are refused (rc 2, usage). Every row is also replayed
on its tool's library mock by the kit (session.py libmock) and with the kpoke file by
lead/dryrun_checks.sh.

The dumps are made from the plane the argv draws (tri-full: (0,0) (3W,0) (0,3H); --tri-v: its
vertices in 1/256 px), depth less against the clear value (render details dword 16 from
--kpoke-render 1:rd:16=V, else 1.0; a negative one stored as 0, H-CLAMP0), word 10 by H-LIN, then
stored as zls.rs says (formats 0 to 2) or by gen/zst2.predict (formats 3 to 6; format 7 as 4).
Outputs follow E978's kept tri forms (`depth #1: D dwords, C changed, ...`, `stencil #1`,
`stencil store #1`, `job: ok`, `diff:`, `tri WxH #1: N triangle, ...`).

Worlds (EXPECT: the driver's status, {stage: the runner's status}; a stage a gate shut is absent):
  model      every job completes, every control passes: 0, all four stages 0
  nodepth    tri prints no `depth #1` line: zst2's first control has no reading, the premise
             stops (25)
  rejected   every tri with --depth prints `job: rejected` and a diff line (E934): a failure
             under expectdiff, the session stops at zst2 (4)
  bgoff      the kernel ignores rd:16 (the background stays 1.0): zbg-c25 FAILS, zbg's gate is
             shut (zbg absent), zw runs: 0
  negfault   a render with a negative background depth faults: unexpected, zbg stops (4)"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import zst2 as Z  # noqa: E402

EXPECT = {
    "model": (0, {"zst2": 0, "zbgc": 0, "zbg": 0, "zw": 0}),
    "nodepth": (25, {"zst2": 25}),
    "rejected": (4, {"zst2": 4}),
    "bgoff": (0, {"zst2": 0, "zbgc": 0, "zw": 0}),
    "negfault": (4, {"zst2": 0, "zbgc": 0, "zbg": 4}),
}
COMMON_FLAGS = {"--keep-going", "--depth", "--tri-full"}
COMMON_VALUED = {"--wait-ms", "--width", "--height", "--max-width", "--max-height", "--tri-v",
                 "--tri-z", "--depth-ctl", "--depth-fill", "--depth-dump", "--poke"}
TOOL_OPTS = {
    "t4": (COMMON_FLAGS | {"--stencil", "--stencil-store"},
           COMMON_VALUED | {"--stencil-fill", "--depth-pages"}, (0.0, 1.0)),
    "t9": (COMMON_FLAGS, COMMON_VALUED | {"--kpoke-render"}, (-1.0, 2.0)),
}
USAGE = dict(rc=2, out="", err="usage: sgxfive-test ...\n")
PAGE = 4096
FILL = 0xDEADBEEF


def parse(argv, flags, valued):
    o, i = {"pokes": [], "kpokes": []}, 0
    while i < len(argv):
        a = argv[i]
        if a in flags:
            o[a] = True
        elif a in valued and i + 1 < len(argv):
            if a == "--poke":
                o["pokes"].append(argv[i + 1])
            elif a == "--kpoke-render":
                o["kpokes"].append(argv[i + 1])
            else:
                o[a] = argv[i + 1]
            i += 1
        else:
            return None
        i += 1
    return o


def fb(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def bf(v):
    return struct.unpack("<f", struct.pack("<I", v))[0]


def plane(o, w, h):
    """z(x, y) at pixel centres, None outside the triangle"""
    if "--tri-v" in o:
        v = [int(t) / 256 for t in o["--tri-v"].split(",")]
        X, Y = v[2], v[5]
    else:
        X, Y = 3 * w, 3 * h
    a, b, c = (float(t) for t in o.get("--tri-z", "0.5,0.5,0.5").split(","))

    def z(x, y):
        px, py = x + 0.5, y + 0.5
        if px / X + py / Y > 1:
            return None
        return a + (b - a) * px / X + (c - a) * py / Y
    return z


def store(o, w, h, world):
    """(depth dump bytes, stencil dump bytes, stencil store bytes or None, drawn, pages)"""
    tw, th = Z.tiles(w, h)
    ctl = int(o["--depth-ctl"], 16)
    fmt, b19 = ctl >> 24 & 7, bool(ctl >> 19 & 1)
    g = ctl >> 3 & 0x1FF
    pages = int(o.get("--depth-pages", 0)) or (w * h * 4 + PAGE - 1) // PAGE + 16
    n = pages * 1024
    bg = 0x3F800000
    for k in o["kpokes"]:
        if k.startswith("1:rd:16=") and "bgoff" not in world:
            bg = int(k.split("=")[1], 16)
    bgz = max(bf(bg), 0.0)
    w10 = [bf(int(p.split("=")[1], 16)) for p in o["pokes"] if p.startswith("blk:10=")]
    f = 1.6 * w10[0] + 0.2 if w10 else 1.0
    zf = plane(o, w, h)
    ref = [FILL] * n
    drawn = 0
    for ty in range(th):
        for tx in range(tw):
            for k in range(512):
                x = (k >> 8 & 1) << 4
                y = 0
                for bb in range(4):
                    y |= (k >> (2 * bb) & 1) << bb
                    x |= (k >> (2 * bb + 1) & 1) << bb
                px, py = 32 * tx + x, 16 * ty + y
                z = zf(px, py)
                z = None if z is None else f * z
                d = z if z is not None and z < bgz else bgz
                if z is not None and z < bgz and px < w and py < h:
                    drawn += 1
                ref[512 * (ty * (g + 1) + tx) + k] = fb(d)
    if "--stencil" in o:
        fill = o.get("--stencil-fill", "0xdeadbeef")
        st = [i if fill == "index" else int(fill, 16) for i in range(n)]
    else:
        st = None
    sbytes = None if st is None else struct.pack("<%dI" % n, *st)
    if fmt == 0:
        dump = [v ^ (0x80000000 if b19 else 0) for v in ref]
    elif fmt in (1, 2):
        dump = [FILL] * n
        for i, v in enumerate(ref):
            if v == FILL:
                continue
            iv = min(int(bf(v) * 16777216), 0xFFFFFF)
            if fmt == 1:
                dump[i] = iv
        if fmt == 2:
            for ty in range(th):
                for tx in range(tw):
                    for y in range(0, 16, 2):
                        for x in range(32):
                            lo = ref[512 * (ty * (g + 1) + tx) + Z.in_tile_index(x, y)]
                            hi = ref[512 * (ty * (g + 1) + tx) + Z.in_tile_index(x, y + 1)]
                            k16 = 0
                            for bb in range(4):
                                k16 |= (x >> bb & 1) << (2 * bb)
                                if bb < 3:
                                    k16 |= (y >> (bb + 1) & 1) << (2 * bb + 1)
                            k16 |= (x >> 4 & 1) << 7
                            enc = lambda v: min(int(bf(v) * 16777216), 0xFFFFFF) >> 8  # noqa: E731
                            dump[256 * (ty * (g + 1) + tx) + k16] = enc(lo) | enc(hi) << 16
    else:
        b = bytearray(struct.pack("<%dI" % n, *([FILL] * n)))
        for off, v in Z.predict(4 if fmt == 7 else fmt, "H-E985", ref, sbytes, w, h).items():
            b[off] = v
        dump = list(struct.unpack("<%dI" % n, bytes(b)))
    sst = None
    if "--stencil-store" in o:
        sst = [FILL] * n
        if fmt == 0:
            for s in range(tw * th):
                for i in range(128):
                    sst[s * 128 + i] = st[s * 128 + i]
    return dump, st, sst, drawn, pages


def summary(label, vals, before):
    ch = sum(1 for v, b in zip(vals, before) if v != b)
    return f"{label} #1: {len(vals)} dwords, {ch} changed, {len(set(vals))} distinct"


def tri(tool, argv, world):
    flags, valued, (zlo, zhi) = TOOL_OPTS[tool]
    o = parse(argv, flags, valued)
    if o is None:
        return USAGE
    w, h = int(o.get("--width", 64)), int(o.get("--height", 64))
    if "--tri-v" in o and "--tri-full" in o:
        return USAGE
    if "--tri-z" in o:
        z = [float(t) for t in o["--tri-z"].split(",")]
        if len(z) != 3 or any(not zlo <= t <= zhi for t in z):
            return USAGE
    zopts = ("--depth-ctl", "--depth-fill", "--depth-dump", "--depth-pages", "--stencil")
    if any(k in o for k in zopts) and "--depth" not in o:
        return USAGE
    if ("--stencil-store" in o or "--stencil-fill" in o) and "--stencil" not in o:
        return USAGE
    if "--depth-pages" in o and int(o["--depth-pages"]) < (w * h * 4 + PAGE - 1) // PAGE:
        return USAGE
    out, files = [f"tri: render context for targets up to {w}x{h}"], {}
    neg = any(k.startswith("1:rd:16=") and int(k.split("=")[1], 16) >> 31 for k in o["kpokes"])
    if neg and "negfault" in world:
        out.append("job: failed: job faulted, context lost (Input/output error)")
        return dict(rc=1, out="\n".join(out) + "\n", err="",
                    kmsg=["sgxfive: BIF fault 0x90020 at 0x3e10000c (PD 0xf4f2000) stalls job 7, "
                          "recovering"], latch=(0x90020, 0x3e10000c))
    rejected = "--depth" in o and "rejected" in world
    out.append("job: rejected (Invalid argument)" if rejected else "job: ok")
    drawn = 0
    if "--depth" in o and not rejected:
        dump, st, sst, drawn, pages = store(o, w, h, world)
        n = pages * 1024
        bufs = [("depth", "depth", dump, [FILL] * n)]
        if st is not None:
            bufs.append(("stencil", "stencil", st, st))
        if sst is not None:
            bufs.append(("stencil store", "stencil-store", sst, [FILL] * n))
        for label, fname, vals, before in bufs:
            if "nodepth" not in world:
                out.append(summary(label, vals, before))
            if "--depth-dump" in o:
                files[f"{o['--depth-dump']}/{fname}.1.bin"] = struct.pack("<%dI" % n, *vals)
    out += [f"target: {w}x{h} hash 0x0123456789abcdef",
            f"diff: {w * h - drawn} of {w * h} pixels",
            f"tri {w}x{h} #1: {drawn} triangle, {w * h - drawn} background, 0 other",
            "tri: 1 renders ok"]
    return dict(rc=1 if rejected or drawn != w * h else 0, out="\n".join(out) + "\n", err="",
                files=files)


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "tri" and tool in TOOL_OPTS:
        return tri(tool, argv[1:], world)
    return USAGE
