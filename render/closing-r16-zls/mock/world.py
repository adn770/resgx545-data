# SPDX-License-Identifier: MIT
"""mock/world.py: r16-zls's argv-driven fake laptop for kit/session.py mock (r15-zls's, adapted).
answer(tool, argv, world) sees the tool's name, the argv and the world's tokens, never a case
name. It is as strict as t10 (sgxfive-test at a581c06) on the options the rows use: any other
option, a --depth-* or --stencil option without --depth, --depth-store-fill without --depth-store,
a stencil option or --isp2 without --stencil, --tri-v with --tri-full, --depth-pages below the
target's pages or above 0x100000, a --kpoke-render that is not N:rd:index=V with N >= 1 and index
<= 122, a --poke that is not SPACE:INDEX=V or SPACE:INDEX^=V, a fill that is not a value, index,
bit:K (K <= 31) or bytes[:S] are refused (rc 2, usage). Every row is also replayed on t10's
library mock by the kit (session.py libmock) and by lead/dryrun_checks.sh.

The buffers sit where t10 maps them (depth 0x3e001000, each next buffer right after it, base
0x3e000000); a depth-store row's load reads from rd:12 rounded down to 16 bytes, stencil rows
draw half the pixels, and the dumps are synthetic: the mock checks statuses, the scorer's tests
check verdicts on kept records and on rows built from z16's own predictions.

Worlds (EXPECT: the driver's status, {stage: the runner's status}):
  model     every job completes, the controls have their readings: 0
  noread    no `tri WxH #1` and no `depth store #1` lines: zpass2's first control has no reading
            (25)
  rejected  a row with --kpoke-render prints `job: rejected` and a diff line (E934): zbits4's
            last row (zb4-23-bg) fails under expectdiff, the session stops (4)
  moved     the tool maps the depth buffer a page higher (0x3e002000): hook_check stops zovp at
            zb4-20-d12 (24, the next stage runs); zoff runs (0)
  nobg      the tool prints no line for an rd:17 poke: hook_check stops zbits4 at zb4-23-bg (24);
            zovp and zoff run (0)
  f7fault   a format-7 render faults: unexpected, zbits4 stops (4) and the session with it
  w0fault   a render with the z offset 0 (--poke blk:10=0x00000000, zw2-w0, the last row) faults:
            zoff stops (4)"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import z16 as Z  # noqa: E402

EXPECT = {
    "model": (0, {"zpass2": 0, "zbits4": 0, "zovp": 0, "zoff": 0}),
    "noread": (25, {"zpass2": 25}),
    "rejected": (4, {"zpass2": 0, "zbits4": 4}),
    "moved": (0, {"zpass2": 0, "zbits4": 0, "zovp": 24, "zoff": 0}),
    "nobg": (0, {"zpass2": 0, "zbits4": 24, "zovp": 0, "zoff": 0}),
    "f7fault": (4, {"zpass2": 0, "zbits4": 4}),
    "w0fault": (4, {"zpass2": 0, "zbits4": 0, "zovp": 0, "zoff": 4}),
}
FLAGS = {"--keep-going", "--tri-full", "--depth", "--depth-store", "--stencil", "--stencil-store",
         "--pixels"}
VALUED = {"--wait-ms", "--width", "--height", "--max-width", "--max-height", "--tri-z", "--tri-v",
          "--depth-ctl", "--depth-fill", "--depth-store-fill", "--depth-pages", "--depth-dump",
          "--poke", "--kpoke-render", "--stencil-fill", "--isp2"}
MULTI = {"--poke", "--kpoke-render"}
USAGE = dict(rc=2, out="", err="usage: sgxfive-test ...\n")
PAGE = 4096
BG = 0xFF203040
DEPTH_AT, BASE = 0x3E001000, 0x3E000000     # where t10 maps the depth buffer, the ZLS base


def parse(argv):
    o, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a in FLAGS:
            o[a] = True
        elif a in VALUED and i + 1 < len(argv):
            if a in MULTI:
                o.setdefault(a, []).append(argv[i + 1])
            else:
                o[a] = argv[i + 1]
            i += 1
        else:
            return None
        i += 1
    return o


def fill_ok(f):
    if f == "index" or f == "bytes":
        return True
    try:
        if f.startswith("bit:"):
            return 0 <= int(f[4:]) <= 31
        if f.startswith("bytes:"):
            return 0 <= int(f[6:]) <= 255
        int(f, 0)
        return True
    except ValueError:
        return False


def pack(v):
    return struct.pack("<%dI" % len(v), *v)


def tri(argv, world):
    o = parse(argv)
    if o is None:
        return USAGE
    w, h = int(o.get("--width", 64)), int(o.get("--height", 64))
    depth_opts = ("--depth-ctl", "--depth-fill", "--depth-dump", "--depth-pages", "--depth-store",
                  "--stencil")
    if any(k in o for k in depth_opts) and "--depth" not in o:
        return USAGE
    if "--depth-store-fill" in o and "--depth-store" not in o:
        return USAGE
    if any(k in o for k in ("--stencil-store", "--stencil-fill", "--isp2")) and "--stencil" not in o:
        return USAGE
    if "--tri-v" in o and "--tri-full" in o:
        return USAGE
    for k in ("--depth-fill", "--depth-store-fill", "--stencil-fill"):
        if k in o and not fill_ok(o[k]):
            return USAGE
    for spec in o.get("--poke", []):
        sp, _, rest = spec.partition(":")
        idx, op, val = rest.partition("=")
        if sp not in ("blk", "ta", "rd") or not idx.rstrip("^").isdigit() or not val:
            return USAGE
        try:
            int(val, 0)
        except ValueError:
            return USAGE
    kp = {}
    for spec in o.get("--kpoke-render", []):
        n, _, rest = spec.partition(":")
        sp, _, rest = rest.partition(":")
        idx, _, val = rest.partition("=")
        if (not n.isdigit() or int(n) < 1 or sp != "rd" or not idx.isdigit() or int(idx) > 122
                or not val):
            return USAGE
        kp[int(idx)] = int(val, 0)
    minp = (w * h * 4 + PAGE - 1) // PAGE
    pages = int(o.get("--depth-pages", 0)) or minp + 16
    if pages < minp or pages > 0x100000:
        return USAGE
    ctl = int(o.get("--depth-ctl", "0"), 16)
    out, files = [f"tri: render context for targets up to {w}x{h}"], {}
    at = 0x3E002000 if "moved" in world else DEPTH_AT
    bufs = [("depth", o.get("--depth-fill", "0xdeadbeef"))]
    if "--depth-store" in o:
        bufs.append(("depth store", o.get("--depth-store-fill", "0xdeadbeef")))
    if "--stencil" in o:
        bufs.append(("stencil", o.get("--stencil-fill", "0xdeadbeef")))
    if "--stencil-store" in o:
        bufs.append(("stencil store", "0xdeadbeef"))
    n = pages * 1024
    addr = {}
    for k, (name, f) in enumerate(bufs):
        addr[name] = at + k * pages * PAGE
        out.append(f"{name}: {addr[name]:#010x} {pages} pages, fill {f}"
                   + (f", base {BASE:#010x}, control {ctl:#010x}" if not k else ""))
    if "--isp2" in o:
        out.append(f"tri: isp2 {int(o['--isp2'], 16):#010x}")
    for spec in o.get("--kpoke-render", []):
        if "nobg" in world and ":rd:17=" in spec:
            continue
        out.append(f"tri: kpoke before render {spec.split(':')[0]}: {spec.split(':', 1)[1]}")
    if "rejected" in world and "--kpoke-render" in o:
        out += ["job: rejected (Invalid argument)", f"diff: {w * h} of {w * h} pixels"]
        return dict(rc=1, out="\n".join(out) + "\n", err="")
    if ("f7fault" in world and ctl >> 24 & 7 == 7) or (
            "w0fault" in world and "blk:10=0x00000000" in o.get("--poke", [])):
        out.append("job: failed: job faulted, context lost (Input/output error)")
        return dict(rc=1, out="\n".join(out) + "\n", err="",
                    kmsg=["sgxfive: BIF fault 0x90020 at 0x3e10000c (PD 0xf4f2000) stalls job 7, "
                          "recovering"], latch=(0x90020, 0x3E10000C))
    out.append("job: ok")
    tw, th = Z.tiles(w, h)
    ext = Z.TILE_DW * tw * th
    depth = [Z.fill_at(bufs[0][1], i) for i in range(n)]
    dump = {"depth.1.bin": None}
    drawn = w * h
    if "--depth-store" in o:
        sf = o.get("--depth-store-fill", "0xdeadbeef")
        store = [Z.fill_at(sf, i) for i in range(n)]
        rd12 = kp.get(12, addr["depth"] - BASE) & ~0xF
        off = (rd12 - (addr["depth"] - BASE)) // 4
        load_on = ctl & 0x4002 == 0x4002
        for k in range(min(ext, n)):
            store[k] = (depth[off + k] if load_on and 0 <= off + k < n else 0x3F800000) & 0x7FFFFFFF
        drawn = 0
        ch = sum(1 for i in range(n) if store[i] != Z.fill_at(sf, i))
        dump["depth-store.1.bin"] = pack(store)
        if "noread" not in world:
            out.append(f"depth store #1: {n} dwords, {ch} changed, 2 distinct")
    else:
        for k in range(min(ext, n)):
            depth[k] = (k * 2654435761) & 0x3FFFFFFF
    if "--stencil" in o:
        drawn = w * h // 2
        sbytes = bytearray(4 * n)
        for k in range(len(sbytes)):
            sbytes[k] = Z.fill_byte(o["--stencil-fill"], k)
        if "--stencil-store" in o:
            sstore = bytearray(b"\xef\xbe\xad\xde" * n)
            for k in range(min(4 * ext // 4, 4 * n)):
                sstore[k] = sbytes[k] ^ (0xFF if k & 1 else 0)
            dump["stencil-store.1.bin"] = bytes(sstore)
            if "noread" not in world:
                out.append(f"stencil store #1: {n} dwords, {ext // 4} changed")
        dump["stencil.1.bin"] = bytes(sbytes)
    dump["depth.1.bin"] = pack(depth)
    if "noread" not in world:
        out.append(f"depth #1: {n} dwords, {ext} changed, 9 distinct")
    if "--pixels" in o:
        out.append("target: %dx%d hash 0x0123456789abcdef" % (w, h))
        out += [f"row {y}: " + " ".join(
            f"{Z.TRI_COLOUR if (y * w + x) < drawn else BG:#010x}" for x in range(w)) for y in range(h)]
    if "--depth-dump" in o:
        d = o["--depth-dump"]
        files.update({f"{d}/{k}": v for k, v in dump.items()})
    out.append(f"diff: {w * h - drawn} of {w * h} pixels")
    if "noread" not in world:
        out.append(f"tri {w}x{h} #1: {drawn} triangle, {w * h - drawn} background, 0 other")
    out.append("tri: 1 renders ok")
    return dict(rc=0 if drawn == w * h else 1, out="\n".join(out) + "\n", err="", files=files)


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "tri" and tool == "t10":
        return tri(argv[1:], world)
    return USAGE
