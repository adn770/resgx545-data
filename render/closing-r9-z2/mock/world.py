# SPDX-License-Identifier: MIT
"""mock/world.py: r9-z2's argv-driven fake laptop for kit/session.py mock (r9-x's fake, tri only).
answer(tool, argv, world) sees the tool's name, the argv and the world's tokens, never a case name;
it is as strict as tool t9 (sgxfive-test at 97447b04) on the options the session uses: any other
option is refused (rc 2, usage), as are a --tri-z depth outside [-1, 2], --depth-* without --depth
and a probe. Every row is also replayed on t9's library mock by the kit (session.py libmock).
Outputs follow E466/E831's kept tri forms (`depth #1: D dwords, C changed`, `tri WxH #1: N
triangle`) and --depth-dump DIR writes DIR/depth.1.bin of the buffer's pages.

Worlds:
  model     every job completes: z2 0
  nodepth   tri prints no `depth #1` line: the first control has no reading, the premise stops (25)
  rejected  every tri with --depth prints `job: rejected` and a diff line (E934): a failure under
            expectdiff, the session stops (4)
  negfault  a job whose viewport z offset is negative faults: unexpected, the session stops (4)
EXPECT: {world: (the driver's status, {stage: the runner's status})}."""
EXPECT = {
    "model": (0, {"z2": 0}),
    "nodepth": (25, {"z2": 25}),
    "rejected": (4, {"z2": 4}),
    "negfault": (4, {"z2": 4}),
}

FLAGS = {"--keep-going", "--depth", "--depth-store", "--stencil", "--stencil-store", "--tri-full",
         "--pixels"}
VALUED = {"--wait-ms", "--width", "--height", "--max-width", "--max-height", "--tri-v", "--tri-z",
          "--tri-unit", "--depth-ctl", "--depth-fill", "--depth-dump", "--poke", "--stencil-fill"}
USAGE = dict(rc=2, out="", err="usage: sgxfive-test ...\n")
PAGE = 4096


def parse(argv, flags, valued):
    o, i, files = {}, 0, []
    while i < len(argv):
        a = argv[i]
        if a in flags:
            o[a] = True
        elif a in valued and i + 1 < len(argv):
            o[a] = argv[i + 1]
            if a == "--poke":
                o.setdefault("pokes", []).append(argv[i + 1])
            i += 1
        elif a.startswith("--"):
            return None, None
        else:
            files.append(a)
        i += 1
    return o, files


def tri(argv, world):
    o, files = parse(argv, FLAGS, VALUED)
    if o is None or files:
        return USAGE
    w, h = int(o.get("--width", 64)), int(o.get("--height", 64))
    if "--tri-unit" in o:
        if "--tri-v" not in o or not 5 <= int(o["--tri-unit"]) <= 20:
            return USAGE
    far = False
    if "--tri-v" in o:
        v = [int(t) for t in o["--tri-v"].split(",")]
        if len(v) != 6 or any(not -(1 << 30) <= t < 1 << 30 for t in v) or "--tri-full" in o:
            return USAGE
        far = max(abs(t) for t in v) >> int(o.get("--tri-unit", 8)) > 1 << 23
    if "--tri-z" in o:
        z = [float(t) for t in o["--tri-z"].split(",")]
        if len(z) != 3 or any(not -1 <= t <= 2 for t in z):
            return USAGE
    zopts = ("--depth-ctl", "--depth-fill", "--depth-dump", "--depth-store", "--stencil")
    if any(k in o for k in zopts) and "--depth" not in o:
        return USAGE
    if ("--stencil-store" in o or "--stencil-fill" in o) and "--stencil" not in o:
        return USAGE
    pokes = o.get("pokes", [])
    out, files = [f"tri: render context for targets up to {w}x{h}"], {}
    neg = any(p == "blk:10=0xbe800000" for p in pokes)
    if (far and "farfault" in world) or (neg and "negfault" in world):
        out.append("job: failed: job faulted, context lost (Input/output error)")
        return dict(rc=1, out="\n".join(out) + "\n", err="",
                    kmsg=["sgxfive: BIF fault 0x90020 at 0x3e10000c (PD 0xf4f2000) stalls job 7, "
                          "recovering"], latch=(0x90020, 0x3e10000c))
    rejected = "--depth" in o and "rejected" in world
    out.append("job: rejected (Invalid argument)" if rejected else "job: ok")
    if "--depth" in o and not rejected:
        pages = (w * h * 4 + PAGE - 1) // PAGE + 16
        tiles = -(-w // 32) * -(-h // 16)
        bufs = [("depth", "depth", 512 * tiles)]
        if "--depth-store" in o:
            bufs.append(("depth store", "depth-store", 512 * tiles))
        if "--stencil" in o:
            bufs.append(("stencil", "stencil", 0))
        if "--stencil-store" in o:
            bufs.append(("stencil store", "stencil-store", 128 * tiles))
        for label, fname, n in bufs:
            if "nodepth" not in world:
                out.append(f"{label} #1: {pages * 1024} dwords, {n} changed, 2 distinct; "
                           f"0xdeadbeef x {pages * 1024 - n}")
            if "--depth-dump" in o:
                files[f"{o['--depth-dump']}/{fname}.1.bin"] = bytes(pages * PAGE)
    drawn = 0 if rejected else w * h
    out += [f"target: {w}x{h} hash 0x0123456789abcdef",
            f"diff: {w * h - drawn} of {w * h} pixels"]
    if "--pixels" in o:
        out += [f"row {y}: " + " ".join(["0xff00ff00"] * w) for y in range(h)]
    out += [f"tri {w}x{h} #1: {drawn} triangle, {w * h - drawn} background, 0 other",
            "tri: 1 renders ok"]
    return dict(rc=1 if rejected else 0, out="\n".join(out) + "\n", err="", files=files)


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "tri":
        return tri(argv[1:], world)
    return USAGE
