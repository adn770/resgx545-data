# SPDX-License-Identifier: MIT
"""mock/world.py: r10-x's argv-driven fake laptop for kit/session.py mock. answer(tool, argv, world)
sees the tool's name, the argv and the world's tokens, never a case name; it returns None (the
health pair, or a refusal) or dict(rc, out, err, files, kmsg). It is as strict as tool t4
(sgxfive-test at 4623753) on the options the session uses: any other option is refused (rc 2,
usage), as are a --tri-z depth outside [0, 1], a --depth-ctl, --depth-fill, --depth-store or
--depth-dump without --depth, a --poke other than blk:N=V or blk:N^=V, a probe --tri slot other
than pixel or pixpds:12, a --cmd or --slot of another form and a probe without exactly one program.
Every row is also replayed on the real tool's library mock by the kit (session.py libmock) and by
lead/dryrun_checks.sh (with the kpoke file the depth rows write).

The outputs follow the kept outputs' forms (E977's tri `depth #1: D dwords, C changed` lines,
`target: WxH hash`, `diff:`, `tri WxH #1: N triangle`, `row N:` with --pixels; E383's and E502's
`probe NAME: row N:` lines) and the dumps the tool writes (--depth-dump DIR: depth.1.bin,
depth-store.1.bin, each the buffer's pages).

Worlds:
  model       every job completes: every stage 0
  nopix       the probe prints no pixel rows: hook_check stops sb and win0 at their first row (24);
              the tri stages run (0)
  nodepth     tri prints no `depth #1` line: dcmp's controls read drawn and run (0); zov's first
              control has no reading, the premise stops the session (25)
  rejected    every tri with --depth prints `job: rejected` and a diff line (r8-geo's E934): the
              runner takes it as a failure under expectdiff and stops the session (4) at dcmp
  winrefused  the kernel refuses a TE_AA with bit 31 or 30 (the knob not taken: E934's twin for
              the probe): win0's first row fails, the session stops (4) after the other stages
EXPECT: {world: (the driver's status, {stage: the runner's status})}."""
EXPECT = {
    "model": (0, {"dcmp": 0, "zov": 0, "zbits": 0, "isp0x": 0, "sb": 0, "win0": 0}),
    "nopix": (0, {"dcmp": 0, "zov": 0, "zbits": 0, "isp0x": 0, "sb": 24, "win0": 24}),
    "nodepth": (25, {"dcmp": 0, "zov": 25}),
    "rejected": (4, {"dcmp": 4}),
    "winrefused": (4, {"dcmp": 0, "zov": 0, "zbits": 0, "isp0x": 0, "sb": 0, "win0": 4}),
}

FLAGS = {"--keep-going", "--depth", "--depth-store", "--tri-full", "--pixels"}
VALUED = {"--wait-ms", "--width", "--height", "--max-width", "--max-height", "--tri-v", "--tri-z",
          "--depth-ctl", "--depth-fill", "--depth-dump"}
REPEAT = {"--poke"}
PROBE_FLAGS = {"--pixels", "--tri-full"}
PROBE_VALUED = {"--tri", "--temps", "--width", "--height", "--sideband"}
PROBE_REPEAT = {"--cmd", "--slot"}
USAGE = dict(rc=2, out="", err="usage: sgxfive-test ...\n")
PAGE = 4096


def parse(argv, flags, valued, repeat):
    o, i, files = {}, 0, []
    while i < len(argv):
        a = argv[i]
        if a in flags:
            o[a] = True
        elif a in valued and i + 1 < len(argv):
            o[a] = argv[i + 1]
            i += 1
        elif a in repeat and i + 1 < len(argv):
            o.setdefault(a, []).append(argv[i + 1])
            i += 1
        elif a.startswith("--"):
            return None, None
        else:
            files.append(a)
        i += 1
    return o, files


def word(s):
    try:
        v = int(s, 0)
    except ValueError:
        return None
    return v if 0 <= v <= 0xFFFFFFFF else None


def probe(argv, world):
    o, files = parse(argv, PROBE_FLAGS, PROBE_VALUED, PROBE_REPEAT)
    if o is None or len(files) != 1 or o.get("--tri") not in ("pixel", "pixpds:12"):
        return USAGE
    cmd = {}
    for c in o.get("--cmd", []):
        n, _, v = c.partition("=")
        if not n.isdigit() or word(v) is None:
            return USAGE
        cmd[int(n)] = word(v)
    for s in o.get("--slot", []):
        n, _, f = s.partition("=")
        if n not in ("pixel", "eot") or not f:
            return USAGE
    if "--sideband" in o and word(o["--sideband"]) is None:
        return USAGE
    w, h = int(o.get("--width", 64)), int(o.get("--height", 64))
    name = files[0].rsplit("/", 1)[-1][:-4]
    out = ["programs asm", f"probe {name}: scratch at 0x3e00e000 (64 KiB)",
           f"probe {name}: tri {w}x{h}, pixel pixpds replaced"]
    if cmd.get(1, 0x20000000) & 0xC0000000 and "winrefused" in world:
        out.append(f"probe {name}: failed: Invalid argument")
        return dict(rc=3, out="\n".join(out) + "\n", err="")
    if "nopix" not in world:
        out += [f"probe {name}: row {y}: " + " ".join("%08x" % (0x3EC00000 + x) for x in range(w))
                for y in range(h)]
    return dict(rc=0, out="\n".join(out) + "\n", err="")


def tri(argv, world):
    o, files = parse(argv, FLAGS, VALUED, REPEAT)
    if o is None or files:
        return USAGE
    w, h = int(o.get("--width", 64)), int(o.get("--height", 64))
    if "--tri-v" in o:
        v = [int(t) for t in o["--tri-v"].split(",")]
        if len(v) != 6 or any(not -(1 << 30) <= t < 1 << 30 for t in v) or "--tri-full" in o:
            return USAGE
    if "--tri-z" in o:
        z = [float(t) for t in o["--tri-z"].split(",")]
        if len(z) != 3 or any(not 0 <= t <= 1 for t in z):
            return USAGE
    for p in o.get("--poke", []):
        sp, _, rest = p.partition(":")
        n, _, v = rest.replace("^=", "=").partition("=")
        if sp != "blk" or not n.isdigit() or word(v) is None:
            return USAGE
    zopts = ("--depth-ctl", "--depth-fill", "--depth-dump", "--depth-store")
    if any(k in o for k in zopts) and "--depth" not in o:
        return USAGE
    out, files = [f"tri: render context for targets up to {w}x{h}"], {}
    rejected = "--depth" in o and "rejected" in world
    out.append("job: rejected (Invalid argument)" if rejected else "job: ok")
    if "--depth" in o and not rejected:
        pages = (w * h * 4 + PAGE - 1) // PAGE + 16
        tiles = -(-w // 32) * -(-h // 16)
        bufs = [("depth", "depth", 512 * tiles)]
        if "--depth-store" in o:
            bufs.append(("depth store", "depth-store", 512 * tiles))
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
