# SPDX-License-Identifier: MIT
"""mock/world.py: r9-x's argv-driven fake laptop for kit/session.py mock. answer(tool, argv, world)
sees the tool's name, the argv and the world's tokens, never a case name; it returns None (the
health pair, or a refusal) or dict(rc, out, err, files, kmsg). It is as strict as tool t4
(sgxfive-test at 4623753) on the options the session uses: any other option is refused (rc 2,
usage), as are --tri-unit outside 5 to 20, a --tri-v coordinate outside [-2^30, 2^30), a --tri-z
depth outside [0, 1], --depth-pages under the target, --stencil-store without --stencil and
--scratch-pages outside 16 to 64. Every row is also replayed on the real tool's library mock by
the kit (session.py libmock) before any world runs.

The outputs follow the kept outputs' forms (E566 probe `probe NAME: row N:` lines; E831/E467 tri
`depth #1: D dwords, C changed` lines, `tri WxH #1: N triangle`, `row N:` with --pixels) and the
dumps the tool writes (--depth-dump DIR: depth.1.bin, depth-store.1.bin, stencil.1.bin,
stencil-store.1.bin, each the buffer's pages).

Worlds:
  model     every job completes: every stage 0
  nopix     the probe prints no pixel rows: hook_check stops t3 at its first row (24); the other
            stages run (0)
  nodepth   tri prints no `depth #1` line: zls's first control has no reading, the premise stops
            the session (25) after t3 and srgb
  rejected  every tri with --depth prints `job: rejected` and a diff line (r8-geo's E934): the
            runner takes it as a failure under expectdiff and stops the session (4)
  farfault  a vertex past 2^23 pixels faults the job: far's first such row is an unexpected
            fault, the session stops (4) after the other stages
EXPECT: {world: (the driver's status, {stage: the runner's status})}."""
EXPECT = {
    "model": (0, {"t3": 0, "srgb": 0, "zls": 0, "zst": 0, "far": 0}),
    "nopix": (0, {"t3": 24, "srgb": 24, "zls": 0, "zst": 0, "far": 0}),
    "nodepth": (25, {"t3": 0, "srgb": 0, "zls": 25}),
    "rejected": (4, {"t3": 0, "srgb": 0, "zls": 4}),
    "farfault": (4, {"t3": 0, "srgb": 0, "zls": 0, "zst": 0, "far": 4}),
}

FLAGS = {"--keep-going", "--depth", "--depth-store", "--stencil", "--stencil-store", "--tri-full",
         "--pixels"}
VALUED = {"--wait-ms", "--width", "--height", "--max-width", "--max-height", "--tri-v", "--tri-z",
          "--tri-unit", "--depth-ctl", "--depth-fill", "--depth-dump", "--poke", "--stencil-fill"}
PROBE_FLAGS = {"--coords", "--pixels"}
PROBE_VALUED = {"--temps", "--scratch-pages"}
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
            i += 1
        elif a.startswith("--"):
            return None, None
        else:
            files.append(a)
        i += 1
    return o, files


def probe(argv, world):
    o, files = parse(argv, PROBE_FLAGS, PROBE_VALUED)
    if o is None or len(files) != 1:
        return USAGE
    pages = int(o.get("--scratch-pages", 16))
    if not 16 <= pages <= 64:
        return USAGE
    name = files[0].rsplit("/", 1)[-1][:-4]
    out = ["programs asm", f"probe {name}: scratch at 0x3e003000 ({pages * 4} KiB)",
           f"probe {name}: job time: 640 us"]
    if "nopix" not in world:
        out += [f"probe {name}: row {y}: " + " ".join("d%07x" % (y * 64 + x) for x in range(64))
                for y in range(32)]
    return dict(rc=0, out="\n".join(out) + "\n", err="")


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
        if len(z) != 3 or any(not 0 <= t <= 1 for t in z):
            return USAGE
    zopts = ("--depth-ctl", "--depth-fill", "--depth-dump", "--depth-store", "--stencil")
    if any(k in o for k in zopts) and "--depth" not in o:
        return USAGE
    if ("--stencil-store" in o or "--stencil-fill" in o) and "--stencil" not in o:
        return USAGE
    out, files = [f"tri: render context for targets up to {w}x{h}"], {}
    if far and "farfault" in world:
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
    if argv[0] == "probe":
        return probe(argv[1:], world)
    if argv[0] == "tri":
        return tri(argv[1:], world)
    return USAGE
