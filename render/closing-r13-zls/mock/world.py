# SPDX-License-Identifier: MIT
"""mock/world.py: r13-zls's argv-driven fake laptop for kit/session.py mock. answer(tool, argv,
world) sees the tool's name, the argv and the world's tokens, never a case name. It is as strict
as t10 (sgxfive-test at a581c06) on the options the rows use: any other option, a --depth-* or
--stencil option without --depth, --depth-store-fill without --depth-store, a stencil option or
--isp2 without --stencil, --tri-v with --tri-full, --depth-pages below the target's pages, a
--kpoke-render that is not N:space:index=V with N >= 1, a fill that is not a value, index or
bytes[:S] are refused (rc 2, usage). Every row is also replayed on t10's library mock by the kit
(session.py libmock) and by lead/dryrun_checks.sh.

The depth buffers sit where t10 maps them (depth 0x3e001000, each next buffer right after it,
base 0x3e000000); rd:12 (--kpoke-render 1:rd:12=V) moves the load as H-MOVED says. The compare
is the --poke blk:1 word's (0x00000200 never, 0x00400200 less), the triangle at 0.5. Stencil rows
draw as Z-BIT-16 (the test reads 0 when bit 16 is clear) over E988's byte order; ramp and format
rows write a synthetic dump (the scorer reads them as `other`: the mock checks statuses, the
scorer's tests check verdicts on kept records).

Worlds (EXPECT: the driver's status, {stage: the runner's status}):
  model     every job completes, the controls have their readings: 0
  noread    no `tri WxH #1` and no `depth store #1` lines: zbase's first control has no reading (25)
  rejected  a row with --kpoke-render prints `job: rejected` and a diff line (E934): zbase's first
            row fails under expectdiff, the session stops (4)
  moved     the tool maps the depth buffer a page higher (0x3e002000): hook_check stops zbase at
            zb-c-id (24), zbits and zfmt run (0)
  f7fault   a format-7 render faults: unexpected, zfmt stops (4) after zbase and zbits (0)"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import z13 as Z  # noqa: E402

EXPECT = {
    "model": (0, {"zbase": 0, "zbits": 0, "zfmt": 0}),
    "noread": (25, {"zbase": 25}),
    "rejected": (4, {"zbase": 4}),
    "moved": (0, {"zbase": 24, "zbits": 0, "zfmt": 0}),
    "f7fault": (4, {"zbase": 0, "zbits": 0, "zfmt": 4}),
}
FLAGS = {"--keep-going", "--tri-full", "--depth", "--depth-store", "--stencil", "--stencil-store",
         "--pixels"}
VALUED = {"--wait-ms", "--width", "--height", "--max-width", "--max-height", "--tri-z", "--tri-v",
          "--depth-ctl", "--depth-fill", "--depth-store-fill", "--depth-pages", "--depth-dump",
          "--poke", "--kpoke-render", "--stencil-fill", "--isp2"}
MULTI = {"--poke", "--kpoke-render"}
USAGE = dict(rc=2, out="", err="usage: sgxfive-test ...\n")
PAGE = 4096
BG, TRI = 0xFF203040, 0xFF00FF00


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
    if f in ("index", "bytes") or f.startswith("bytes:"):
        return True
    try:
        int(f, 0)
        return True
    except ValueError:
        return False


def fill_at(f, i):
    if f == "index":
        return i
    if f.startswith("bytes"):
        s = int(f.split(":")[1]) if ":" in f else 0
        b = 4 * i + s
        return (b & 0xFF) | ((b + 1) & 0xFF) << 8 | ((b + 2) & 0xFF) << 16 | ((b + 3) & 0xFF) << 24
    return int(f, 0)


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
    kp = {}
    for spec in o.get("--kpoke-render", []):
        n, _, rest = spec.partition(":")
        sp, _, rest = rest.partition(":")
        idx, _, val = rest.partition("=")
        if not n.isdigit() or int(n) < 1 or sp not in ("rd", "ta") or not idx.isdigit() or not val:
            return USAGE
        kp[(sp, int(idx))] = int(val, 0)
    minp = (w * h * 4 + PAGE - 1) // PAGE
    pages = int(o.get("--depth-pages", 0)) or minp + 16
    if pages < minp:
        return USAGE
    ctl = int(o.get("--depth-ctl", "0"), 16)
    out, files = [f"tri: render context for targets up to {w}x{h}"], {}
    at = 0x3E002000 if "moved" in world else Z.ZB_DEPTH
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
                   + (f", base {Z.ZB_BASE:#010x}, control {ctl:#010x}" if not k else ""))
    if "--tri-full" in o:
        out.append("tri: triangle (0,0) (%d,0) (0,%d), depth %s" % (3 * w, 3 * h,
                                                                     o.get("--tri-z", "0.5,0.5,0.5")))
    for spec in o.get("--kpoke-render", []):
        out.append(f"tri: kpoke before render {spec.split(':')[0]}: {spec.split(':', 1)[1]}")
    if "--isp2" in o:
        out.append(f"tri: isp2 {int(o['--isp2'], 16):#010x}")
    if "rejected" in world and "--kpoke-render" in o:
        out += ["job: rejected (Invalid argument)", f"diff: {w * h} of {w * h} pixels"]
        return dict(rc=1, out="\n".join(out) + "\n", err="")
    if "f7fault" in world and ctl >> 24 & 7 == 7:
        out.append("job: failed: job faulted, context lost (Input/output error)")
        return dict(rc=1, out="\n".join(out) + "\n", err="",
                    kmsg=["sgxfive: BIF fault 0x90020 at 0x3e10000c (PD 0xf4f2000) stalls job 7, "
                          "recovering"], latch=(0x90020, 0x3E10000C))
    out.append("job: ok")
    dfill = o.get("--depth-fill", "0xdeadbeef")
    depth = [fill_at(dfill, i) for i in range(n)]
    tiles = Z.tiles(w, h)[0] * Z.tiles(w, h)[1]
    ext = Z.TILE_DW * tiles
    pokes = [p for p in o.get("--poke", []) if p.startswith("blk:1=")]
    cmp_never = bool(pokes) and int(pokes[0].split("=")[1], 16) == 0x00000200
    drawn = w * h
    dump = None
    if "--depth-store" in o:
        sfill = o.get("--depth-store-fill", "0xdeadbeef")
        store = [fill_at(sfill, i) for i in range(n)]
        rd12 = kp.get(("rd", 12), addr["depth"] - Z.ZB_BASE)
        loaded = []
        src, base = (store, addr["depth store"] - Z.ZB_BASE) if rd12 >= addr["depth store"] - Z.ZB_BASE \
            else (depth, addr["depth"] - Z.ZB_BASE)
        off = (rd12 - base) // 4
        for k in range(ext):
            loaded.append((src[off + k] if 0 <= off + k < n else 0) & 0x7FFFFFFF)
        load_on = ctl & 0x4002 == 0x4002
        new, npass = [], 0
        for k in range(ext):
            lv = loaded[k] if load_on else Z.ZB_CLEAR
            passed = not cmp_never and 0x3F000000 < lv
            npass += passed
            new.append(0x3F000000 if passed else lv)
        drawn = min(npass, w * h)
        store[:ext] = new
        files_store = pack(store)
        ch = sum(1 for i in range(n) if store[i] != fill_at(sfill, i))
        if "noread" not in world:
            out.append(f"depth #1: {n} dwords, 0 changed, 1 distinct")
            out.append(f"depth store #1: {n} dwords, {ch} changed, 2 distinct")
        dump = {"depth.1.bin": pack(depth), "depth-store.1.bin": files_store}
    else:
        img_drawn = None
        if "--isp2" in o:
            if not ctl & 1 << 16:                       # Z-BIT-16: the test reads 0
                img_drawn = {(x, y) for y in range(h) for x in range(w)}
            else:
                img_drawn = {(x, y) for y in range(h) for x in range(w)
                             if not (Z.in_tile_index(x, y) & 1)}
            drawn = len(img_drawn)
        synth = [(i * 2654435761) & 0x3FFFFFFF if i < ext else fill_at(dfill, i) for i in range(n)]
        ch = ext
        if ctl >> 24 & 7 in (6, 7):
            synth = [v if i % 256 < 12 else fill_at(dfill, i) for i, v in enumerate(synth)]
            ch = sum(1 for i in range(n) if i < ext and i % 256 < 12)
        if "noread" not in world:
            out.append(f"depth #1: {n} dwords, {ch} changed, 9 distinct")
            if "--stencil-store" in o:
                out.append(f"stencil store #1: {n} dwords, {128 * tiles} changed")
        dump = {"depth.1.bin": pack(synth)}
        if "--stencil" in o:
            dump["stencil.1.bin"] = pack([fill_at(o["--stencil-fill"], i) for i in range(n)])
        if "--stencil-store" in o:
            dump["stencil-store.1.bin"] = pack([0xDEADBEEF] * n)
        if "--pixels" in o:
            out.append("target: %dx%d hash 0x0123456789abcdef" % (w, h))
            out += [f"row {y}: " + " ".join(
                f"{TRI if img_drawn is None or (x, y) in img_drawn else BG:#010x}"
                for x in range(w)) for y in range(h)]
    if "--depth-store" in o and "--pixels" in o:
        out += [f"row {y}: " + " ".join(f"{TRI if drawn else BG:#010x}" for _ in range(w))
                for y in range(h)]
    if "--depth-dump" in o and dump:
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
