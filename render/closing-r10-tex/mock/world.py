# SPDX-License-Identifier: MIT
"""mock/world.py: r10-tex's argv-driven fake laptop for kit/session.py mock (r9-geo's world, cut to
probes). answer() sees the tool's name, the argv and the world's tokens, never a case name: a
probe's program is named by its file in argv (the generator's program of that name). As strict as
sgxfive-test (resgx545 4623753) on the probe: an option the command does not take, a missing
value, a --scratch-pages outside 16 to 64, more than one program or a program file that is not
there is refused (rc 2, usage); a program whose reads pass the scratch the row maps faults (a BIF
fault latched), as E743 and E787's did.

The image a probe prints is a frozen prediction of the session (predictions/STAGE/NAME.MODEL.txt,
written by gen/make.py), so the worlds are the hypotheses: `h:` tokens print the half, `aN` a dword
of a face of axis N, edge tokens their rounded bytes, `-` dword 0.

Worlds:
  model     addr3 H-W / H-B5, cube3 H-HIGHAXIS (the replay H-FMADNE) and H-SEAM-FLOAT, t3b R-4096,
            srgb2 R10-BF11, the controls their kept images: every stage 0
  alt       the other rivals (addr3 H-H / H-B5H, cube3 lower-axis ties and H-SEAM-ADJ, t3b H-U01,
            srgb2 R10-BF11-ROUND or H-K0FLOOR where frozen): every stage 0, the rows FAILED
  nopix     no cube3 row but the control prints pixel rows: the second stops cube3 by its rule
            (rc 24), the driver goes on and t3b, srgb2 run
  ctlnopix  addr3's control prints no pixel rows: the premise stops the session (rc 25)
  fault     the first held-out t3b row faults (a BIF fault latched): t3b stops (rc 4)
  hang      the first held-out srgb2 row never returns (timeout rc 124): srgb2 stops (rc 6)
"""
import os

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGES = ("addr3", "cube3", "t3b", "srgb2")
EXPECT = {"model": (0, {"addr3": 0, "cube3": 0, "t3b": 0, "srgb2": 0}),
          "alt": (0, {"addr3": 0, "cube3": 0, "t3b": 0, "srgb2": 0}),
          "nopix": (0, {"addr3": 0, "cube3": 24, "t3b": 0, "srgb2": 0}),
          "ctlnopix": (25, {"addr3": 25}),
          "fault": (4, {"addr3": 0, "cube3": 0, "t3b": 4}),
          "hang": (6, {"addr3": 0, "cube3": 0, "t3b": 0, "srgb2": 6})}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
PROBE_VAL = {"--temps", "--scratch-pages"}
PROBE_FLAG = {"--coords", "--pixels"}
FIRST = {"model": ("H-W", "H-B5", "REPEAT", "E726", "H-FMADNE", "H-HIGHAXIS", "H-SEAM-FLOAT",
                   "R-4096", "H-TEXMODEL", "H-E566", "R10-BF11", "H-E723"),
         "alt": ("H-H", "H-B5H", "REPEAT", "E726", "LOWAXIS", "H-FMADNE", "H-SEAM-ADJ", "H-U01", "H-TEXMODEL",
                 "H-E566", "R10-BF11-ROUND", "H-K0FLOOR", "R10-BF11", "H-E723")}


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


def tables():
    """{program name: (stage, set)} from the session's tables, in file order."""
    out = {}
    for st in STAGES:
        for ln in open(os.path.join(KP, "tables", st + ".txt")):
            if ln.strip() and not ln.startswith("#"):
                name, s = ln.split("|")[:2]
                out[name] = (st, s)
    return out


def models(stage, name):
    d = os.path.join(KP, "predictions", stage)
    return sorted(f[len(name) + 1:-4] for f in os.listdir(d)
                  if f.startswith(name + ".") and f[len(name) + 1:-4].count(".") == 0)


def value(tok, lower=False):
    if tok == "-":
        return 0xD0000000
    if tok.startswith("h:"):
        return int(tok[2:], 16)
    if tok[0] == "a":
        ax = int(tok[1:])
        if lower:
            ax = 0 if ax else 1
        return 0xD0000000 | (2 * ax * 256)
    if tok[:2] in ("i:", "o:"):
        return sum(int(float(b) + 0.5) << 8 * i for i, b in enumerate(tok[2:].split(",")))
    return int(tok, 16)


def image(stage, name, world):
    ms = models(stage, name)
    pick = "alt" if "alt" in world else "model"
    for m in FIRST[pick]:
        if m == "LOWAXIS" and "H-HIGHAXIS" in ms and "-a2-" not in name:
            toks = open(os.path.join(KP, "predictions", stage, name + ".H-HIGHAXIS.txt")).read()
            return [value(t, lower=True) for t in toks.split()]
        if m in ms:
            toks = open(os.path.join(KP, "predictions", stage, f"{name}.{m}.txt")).read()
            return [value(t) for t in toks.split()]
    raise SystemExit(f"world {world}: no model for {name} ({ms})")


def first_held(stage):
    return next(n for n, (st, s) in tables().items() if st == stage and s == "heldout")


def probe(argv, world):
    r = parse(argv, PROBE_VAL, PROBE_FLAG)
    if r is None or len(r[1]) != 1 or "--coords" not in r[0] or "--pixels" not in r[0]:
        return USAGE
    o, (path,) = r
    pages = int(o.get("--scratch-pages", ["16"])[0], 0)
    if not 16 <= pages <= 64:
        return USAGE
    if not os.path.isfile(path):
        return dict(rc=2, err="sgxfive-test: %s: No such file or directory\n" % path)
    name = os.path.basename(path)[:-4]
    rows = tables()
    if name not in rows:
        return USAGE
    stage, st = rows[name]
    out = ["programs asm", "probe %s: scratch at 0x3e003000 (%d KiB)" % (name, 4 * pages),
           "probe %s: job time: 512 us" % name]
    held = st != "control"
    if "hang" in world and stage == "srgb2" and name == first_held("srgb2"):
        return dict(rc=124, out="")
    if "fault" in world and stage == "t3b" and name == first_held("t3b"):
        return dict(rc=3, out="probe %s: failed: job faulted\n" % name,
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016 stalls job 9"],
                    latch=(4, 0x1000c016))
    img = image(stage, name, world)
    top = max(((v & 0x0FFFFFFF) for v in img if v >> 28 == 0xD), default=0)
    if top >= pages * 1024:
        return dict(rc=3, out="probe %s: failed: job faulted\n" % name,
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016"], latch=(4, 0x1000c016))
    if ("nopix" in world and stage == "cube3" and held) or (
            "ctlnopix" in world and stage == "addr3" and not held):
        return dict(out="\n".join(out) + "\n")
    out += ["probe %s: row %d: " % (name, y) + " ".join("%08x" % v for v in img[64 * y:64 * y + 64])
            for y in range(32)]
    return dict(out="\n".join(out) + "\n")


def answer(tool, argv, world):
    if tool != "t4" or not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe":
        return probe(argv, world)
    return USAGE
