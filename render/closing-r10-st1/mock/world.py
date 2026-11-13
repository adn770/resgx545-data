# SPDX-License-Identifier: MIT
"""mock/world.py: r10-st1's argv-driven fake laptop for kit/session.py mock. answer(tool, argv,
world) sees the tool's name, the argv and the world's tokens, never a case name. It is as strict
as t10 (sgxfive-test at a581c06) on the options the rows use: any other option, --isp2 or a
stencil option without --depth --stencil, --stencil-store or --stencil-fill without --stencil,
a fill that is not a value or bytes[:S], --depth-pages below the target's pages are refused (rc 2,
usage). Every row is also replayed on t10's library mock by the kit (session.py libmock).

The image and the stencil store follow gen/st1.predict_from under H-DEPTHORD (EQUAL, ALWAYS, NEVER
and no --isp2); the ISP word 0 reference is 0. Outputs follow E977's kept tri forms (`job: ok`,
`depth #1`, `stencil #1`, `stencil store #1`, `diff:`, `row N:` lines, `tri WxH #1: N triangle`).

Worlds (EXPECT: the driver's status, {stage: the runner's status}):
  model     every job completes, the controls pass: 0
  nopixels  no `row N:` lines and no `tri WxH #1` line: the first control has no reading (25)
  rejected  every tri with --isp2 prints `job: rejected` and a diff line (E934): the first such
            row fails under expectdiff, the session stops (4)
  ispfault  a render with --isp2 faults: unexpected, the session stops (4)"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import st1 as S  # noqa: E402

EXPECT = {
    "model": (0, {"st1": 0}),
    "nopixels": (25, {"st1": 25}),
    "rejected": (4, {"st1": 4}),
    "ispfault": (4, {"st1": 4}),
}
FLAGS = {"--keep-going", "--depth", "--tri-full", "--stencil", "--stencil-store", "--pixels"}
VALUED = {"--wait-ms", "--width", "--height", "--max-width", "--max-height", "--depth-ctl",
          "--depth-fill", "--stencil-fill", "--isp2", "--depth-dump", "--depth-pages"}
USAGE = dict(rc=2, out="", err="usage: sgxfive-test ...\n")
PAGE = 4096
FILL = 0xDEADBEEF
BG = 0xFF203040


def parse(argv):
    o, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a in FLAGS:
            o[a] = True
        elif a in VALUED and i + 1 < len(argv):
            o[a] = argv[i + 1]
            i += 1
        else:
            return None
        i += 1
    return o


def tri(argv, world):
    o = parse(argv)
    if o is None:
        return USAGE
    w, h = int(o.get("--width", 64)), int(o.get("--height", 64))
    if any(k in o for k in ("--depth-ctl", "--depth-fill", "--depth-dump", "--stencil",
                            "--depth-pages")) and "--depth" not in o:
        return USAGE
    if ("--stencil-store" in o or "--stencil-fill" in o or "--isp2" in o) and "--stencil" not in o:
        return USAGE
    fill = o.get("--stencil-fill", "0xdeadbeef")
    if not (fill == "bytes" or fill.startswith("bytes:") or fill.startswith("0x")):
        return USAGE
    pages = int(o.get("--depth-pages", 0)) or (w * h * 4 + PAGE - 1) // PAGE + 16
    if pages < (w * h * 4 + PAGE - 1) // PAGE:
        return USAGE
    out, files = [f"tri: render context for targets up to {w}x{h}"], {}
    if "--isp2" in o:
        out.append(f"tri: isp2 {int(o['--isp2'], 16):#010x}")
        if "ispfault" in world:
            out.append("job: failed: job faulted, context lost (Input/output error)")
            return dict(rc=1, out="\n".join(out) + "\n", err="",
                        kmsg=["sgxfive: BIF fault 0x90020 at 0x3e10000c (PD 0xf4f2000) stalls "
                              "job 7, recovering"], latch=(0x90020, 0x3e10000c))
    rejected = "--isp2" in o and "rejected" in world
    out.append("job: rejected (Invalid argument)" if rejected else "job: ok")
    n = pages * 1024
    if "--isp2" in o:
        v = int(o["--isp2"], 16)
        mode, m = v >> 25 & 7, v >> 8 & 0xFF
    else:
        mode, m = None, 0
    drawn, sst = S.predict_from(w, h, fill, mode, m, "H-DEPTHORD") if not rejected else (set(), {})
    sten = bytes(S.fill_byte(fill, b) for b in range(4 * n))
    store = bytearray(struct.pack("<%dI" % n, *([FILL] * n)))
    tw, th = S.tiles(w, h)
    if not rejected:
        store[:512 * tw * th] = sten[:512 * tw * th]
        for off, val in sst.items():
            store[off] = val
    depth = struct.pack("<%dI" % n, *([0x3F800000] * n))
    if "nopixels" not in world:
        out += ["depth #1: %d dwords, 0 changed, 1 distinct" % n,
                "stencil #1: %d dwords, 0 changed" % n,
                "stencil store #1: %d dwords, %d changed" % (n, 128 * tw * th)]
    if "--depth-dump" in o:
        d = o["--depth-dump"]
        files.update({f"{d}/depth.1.bin": depth, f"{d}/stencil.1.bin": sten,
                      f"{d}/stencil-store.1.bin": bytes(store)})
    out += [f"target: {w}x{h} hash 0x0123456789abcdef", f"diff: {w * h - len(drawn)} of {w * h} pixels"]
    if "--pixels" in o and "nopixels" not in world:
        out += [f"row {y}: " + " ".join(f"{S.TRI_COLOUR if (x, y) in drawn else BG:#010x}"
                                        for x in range(w)) for y in range(h)]
    if "nopixels" not in world:
        out.append(f"tri {w}x{h} #1: {len(drawn)} triangle, {w * h - len(drawn)} background, 0 other")
    out.append("tri: 1 renders ok")
    return dict(rc=1 if rejected or len(drawn) != w * h else 0, out="\n".join(out) + "\n", err="",
                files=files)


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "tri" and tool == "t10":
        return tri(argv[1:], world)
    return USAGE
