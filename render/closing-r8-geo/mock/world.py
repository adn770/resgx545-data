# SPDX-License-Identifier: MIT
"""mock/world.py: r8-geo's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name: a probe's program is named by its
file in argv (the generator's program of that name, gen/), a tri render by its options. As strict
as sgxfive-test (resgx545 4623753): an option the command does not take, a missing value, a
--tri-z outside 0 to 1, a --scratch-pages outside 16 to 64 or a program file that is not there is
refused (rc 2, usage), as the real tool does.

Worlds (the hypotheses the scorer must tell apart, and the stops the plan relies on):
  model     cube: the q284 rule, filter clamped at edges; seam: H-REGION; addr: H-MASK-V;
            vdm: H-LAYOUT (a forced row changes the image unless it is the natural value)
  alt       cube: taps from the neighbour face at edges; seam: H-UNION (the controls fail);
            addr: H-NOMASK-PAGE; vdm: H-COUNT
  nopix     no cube row but the control prints pixel rows: the second stops cube by its rule
            (rc 24), the driver goes on and the later stages run
  ctlnopix  the cube control prints no pixel rows: the premise stops the session (rc 25)
  fault     the first forced vdm row faults (a BIF fault latched): vdm stops (rc 4), driver 4
  hang      the first forced vdm row never returns (timeout rc 124): vdm stops (rc 6), driver 6
"""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
import addr as A  # noqa: E402
import cube as C  # noqa: E402
import seam as S  # noqa: E402
import texprog as T  # noqa: E402
import vdm as V  # noqa: E402

EXPECT = {"model": (0, {"cube": 0, "seam": 0, "addr": 0, "vdm": 0}),
          "alt": (0, {"cube": 0, "seam": 0, "addr": 0, "vdm": 0}),
          "nopix": (0, {"cube": 24, "seam": 0, "addr": 0, "vdm": 0}),
          "ctlnopix": (25, {"cube": 25}),
          "fault": (4, {"cube": 0, "seam": 0, "addr": 0, "vdm": 4}),
          "hang": (6, {"cube": 0, "seam": 0, "addr": 0, "vdm": 6})}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
PROBE_VAL = {"--temps", "--scratch-pages", "--tri", "--width", "--height", "--vertices",
             "--vtx-coords", "--vdm", "--dump-render", "--slot"}
PROBE_FLAG = {"--coords", "--pixels"}
TRI_VAL = {"--wait-ms", "--width", "--height", "--max-width", "--max-height", "--poke",
           "--tri-v", "--tri-z"}
TRI_FLAG = {"--tri-full", "--keep-going", "--pixels"}
_RULE = []
_JOBS = {}


def parse(argv, vals, flags):
    """(options as {name: [values]}, positional) or None for a usage error."""
    o, pos, i = {}, [], 1
    while i < len(argv):
        a = argv[i]
        if a in flags:
            o.setdefault(a, []).append(True)
            i += 1
        elif a in vals and i + 1 < len(argv):
            o.setdefault(a, []).append(argv[i + 1])
            i += 2
        elif a.startswith("--"):
            return None
        else:
            pos.append(a)
            i += 1
    return o, pos


def rows_text(prefix, img, w, h, hexfmt):
    return "".join(prefix + "row %d: " % y + " ".join(hexfmt % img[(x, y)] for x in range(w))
                   + "\n" for y in range(h))


def rule():
    if not _RULE:
        _RULE.append(C.rule())
    return _RULE[0]


def jobs_by_bin():
    if not _JOBS:
        for name, st, spec, n, t0, kind in C.jobs():
            _JOBS[name + ".bin"] = ("cube", spec, n, kind)
        for name, st, axis, mode in A.jobs():
            _JOBS[name + ".bin"] = ("addr", axis, mode, None)
    return _JOBS


def cube_image(spec, n, kind, world):
    R = rule()
    img = {}
    for p, c in C.coords_of(spec).items():
        q = C.st(R, c, n)
        if q is None:               # a face tie: the world takes the lower axis
            a = [abs(t) for t in c]
            ax = min(i for i in range(3) if a[i] == max(a))
            c = tuple(t * 2 if i == ax else t for i, t in enumerate(c))
            q = C.st(R, c, n)
        face, vs, vt, ma, order = q
        s = min(max(vs.numerator // vs.denominator, 0), n - 1)
        t = min(max(vt.numerator // vt.denominator, 0), n - 1)
        img[p] = 0xD0000000 | (face * n * n + C.twid(s, t, order, n.bit_length() - 1))
    if kind == "edge":
        for p, (f, k) in C.edge_cells(R, spec, n).items():
            if k == "in":
                img[p] ^= 1 if (img[p] & 0xff) % 4 else 2
            elif "alt" in world:
                img[p] = (img[p] & 0xffff00ff) | ((f + 2) % 6) << 8
    return img


def probe(argv, world):
    r = parse(argv, PROBE_VAL, PROBE_FLAG)
    if r is None or len(r[1]) != 1:
        return USAGE
    o, (path,) = r
    if "--scratch-pages" in o and not 16 <= int(o["--scratch-pages"][0], 0) <= 64:
        return USAGE
    if not os.path.isfile(path):
        return dict(rc=2, err="sgxfive-test: %s: No such file or directory\n" % path)
    base = os.path.basename(path)
    name = base[:-4]
    if "--tri" in o:
        return vdm(o, base, world)
    j = jobs_by_bin().get(base)
    if j is None:
        return USAGE
    out = ["programs asm", "probe %s: scratch at 0x3e00e000 (%d KiB)" % (
        name, 4 * int(o.get("--scratch-pages", ["16"])[0], 0))]
    nopix = ("nopix" in world and j[0] == "cube" and name != "cube-ctl-xn") \
        or ("ctlnopix" in world and name == "cube-ctl-xn")
    if j[0] == "cube":
        img = cube_image(j[1], j[2], j[3], world)
    else:
        model = "H-NOMASK-PAGE" if "alt" in world else "H-MASK-V"
        im = A.image(j[1], j[2], model)
        img = {p: 0xA0A1A2A3 if v is None else 0xD0000000 | v for p, v in im.items()}
    if not nopix:
        out.append(rows_text("probe %s: " % name, img, T.W, T.H, "%08x").rstrip("\n"))
    return dict(out="\n".join(out) + "\n")


def vdm(o, base, world):
    n = int(o["--vtx-coords"][0])
    words = {}
    for v in o.get("--vdm", []):
        k, val = (v.split("^=") if "^=" in v else v.split("="))
        words[(int(k), "^=" in v)] = int(val, 0)
    vv = 15 ^ (words.get((6, True), 0) >> 28)
    rows = words[(7, False)] >> 24 if (7, False) in words else V.ROWS[n]
    for f in o.get("--slot", []):
        if not os.path.isfile(f.split("=", 1)[1]):
            return dict(rc=2, err="sgxfive-test: %s: No such file or directory\n" % f)
    forced = rows != V.ROWS[n]
    if forced and "fault" in world:
        return dict(rc=3, out="probe %s: failed: job faulted\n" % base[:-4],
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x10000016 stalls job 9"],
                    latch=(4, 0x10000016))
    if forced and "hang" in world:
        return dict(rc=124, out="")
    changed = forced and (rows < V.ROWS[n] or "alt" not in world)
    seed = (n * 31 + vv) * 7 + (rows if changed else 0)
    img = {(x, y): 0xff203040 if (x * y + seed) % 5 else 0x44000000 | seed
           for y in range(64) for x in range(64)}
    name = base[:-4]
    out = ["programs asm", "probe %s: tri 64x64 (126 vertices) (%d coordinates)" % (name, n),
           rows_text("probe %s: " % name, img, 64, 64, "%08x").rstrip("\n")]
    files = {}
    if "--dump-render" in o:
        d = o["--dump-render"][0]
        files = {os.path.join(d, name + ".param.bin"): bytes(64),
                 os.path.join(d, name + ".tadata.bin"): bytes(16)}
    return dict(out="\n".join(out) + "\n", files=files)


def tri(argv, world):
    r = parse(argv, TRI_VAL, TRI_FLAG)
    if r is None or r[1]:
        return USAGE
    o = r[0]
    w, h = int(o["--width"][0]), int(o["--height"][0])
    pokes = dict(p.split("=", 1) for p in o.get("--poke", []) if "^=" not in p)
    if "--tri-z" in o and not all(0 <= float(z) <= 1 for z in o["--tri-z"][0].split(",")):
        return dict(rc=2, err="sgxfive-test: bad option --tri-z (three screen depths, 0 to 1, "
                              "comma separated)\n")
    te, mode = int(pokes["cmd:1"], 16), int(pokes["cmd:13"], 16) & 3
    verts = None
    if "--tri-v" in o:
        c = [int(v) // 256 for v in o["--tri-v"][0].split(",")]
        verts = ((c[0], c[1]), (c[2], c[3]), (c[4], c[5]))
    elif "--tri-full" not in o:
        return USAGE
    st = S.stored(S.model(), w, h, mode, te, verts, halves="alt" not in world)
    img = {(x, y): S.TRI if (x, y) in st else S.BG for y in range(h) for x in range(w)}
    wrong = w * h - len(st) if verts is None else 0
    out = ["tri: render context for targets up to %dx%d" % (w, h), "job: ok",
           "target: %dx%d hash 0x0123456789abcdef" % (w, h),
           "diff: %d of %d pixels" % (wrong, w * h), "outside: 0 dwords",
           rows_text("", img, w, h, "0x%08x").rstrip("\n")]
    return dict(rc=1 if wrong else 0, out="\n".join(out) + "\n")


def answer(tool, argv, world):
    if tool != "t4" or not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe":
        return probe(argv, world)
    if argv[0] == "tri":
        return tri(argv, world)
    return None
