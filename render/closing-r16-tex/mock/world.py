# SPDX-License-Identifier: MIT
"""mock/world.py: r16-tex's argv-driven fake laptop for kit/session.py mock (r15-tex's world, the ty
stage only). answer() sees the tool's name, the argv and the world's tokens, never a case name: a
fill probe's program is named by its file in argv (the generator's program of that name). As strict
as sgxfive-test (resgx545 a581c06) on this form: an option the command does not take, a missing
value, a --scratch-pages outside 16 to 64, more than one program or a file that is not there is
refused (rc 2, usage); a fill program whose named reads pass the scratch the row maps faults (a BIF
fault latched).

The image a fill probe prints is a frozen prediction of the session (predictions/ty/NAME.MODEL.txt,
written by gen/make.py): the first model the row lists in predictions/ty.tsv in the model world
(the tested one: N13 / N4, L13, R-W / R-32, the control's kept image), the second in the alt world
(the rival: NQ13 / NQ4, LQ13, R-16 / R-2W); a mode 5 row (one pixel model, H-AS-U4) prints one flat
halved name in the model world and the mode 4 image in the alt world.

Worlds:
  model     the tested models (every row 0): the stage 0
  alt       the rivals: the stage 0, the rows FAILED
  nopix     no held-out row prints pixel rows: the second stops the stage by its rule (rc 24)
  ctlnopix  the control prints no pixel rows: the premise stops the session (rc 25)
  fault     the first held-out row faults (a BIF fault latched): the session stops (rc 4)
  hang      the first held-out row never returns (timeout rc 124): the session stops (rc 6)
"""
import os

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGES = ("ty",)
EXPECT = {"model": (0, {"ty": 0}),
          "alt": (0, {"ty": 0}),
          "nopix": (0, {"ty": 24}),
          "ctlnopix": (25, {"ty": 25}),
          "fault": (4, {"ty": 4}),
          "hang": (6, {"ty": 6})}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
PROBE_VAL = {"--temps", "--scratch-pages"}
PROBE_FLAG = {"--coords", "--pixels"}


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
    """{row name: (stage, set, args)} from the session's tables, in file order."""
    out = {}
    for st in STAGES:
        for ln in open(os.path.join(KP, "tables", st + ".txt")):
            if ln.strip() and not ln.startswith("#"):
                name, s, _, _, _, args = ln.rstrip("\n").split("|", 5)
                out[name] = (st, s, args)
    return out


def models(stage, name):
    """The row's pixel models in the order predictions/STAGE.tsv lists them (the tested first)."""
    out = []
    for ln in open(os.path.join(KP, "predictions", stage + ".tsv")).read().splitlines()[1:]:
        f = ln.split("\t")
        if f[0] == name and f[1] == "pixels":
            out.append(f[3])
    return out


def toks(stage, name, model):
    return open(os.path.join(KP, "predictions", stage, f"{name}.{model}.txt")).read().split()


def half(d):
    return sum(((d >> 8 * i & 255) + 1) >> 1 << 8 * i for i in range(4))


def image(stage, name, world):
    ms = models(stage, name)
    alt = "alt" in world
    if len(ms) == 1 and name.endswith("-u5"):
        if alt:
            return [int(t, 16) for t in toks(stage, name, ms[0])]
        return [half(0xD0000000 | 163)] * 2048
    if not ms:
        raise SystemExit(f"world {world}: no model for {name}")
    m = ms[1] if alt and len(ms) > 1 else ms[0]
    return [int(t, 16) for t in toks(stage, name, m)]


def first_held(stage):
    return next(n for n, (st, s, _) in tables().items() if st == stage and s == "heldout")


def rows_out(case, img):
    w = 64
    return ["probe %s: row %d: " % (case, y) + " ".join("%08x" % v for v in img[w * y:w * y + w])
            for y in range(len(img) // w)]


def fill_probe(argv, world):
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
    stage, st, _ = rows[name]
    out = ["programs asm", "probe %s: scratch at 0x3e003000 (%d KiB)" % (name, 4 * pages),
           "probe %s: job time: 512 us" % name]
    held = st == "heldout"
    if "fault" in world and name == first_held(stage):
        return dict(rc=3, out="probe %s: failed: job faulted\n" % name,
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016 stalls job 9"],
                    latch=(4, 0x1000c016))
    if "hang" in world and name == first_held(stage):
        return dict(rc=124, out="")
    img = image(stage, name, world)
    top = max(((v & 0x0FFFFFFF) for v in img if v >> 28 == 0xD), default=0)
    if top >= pages * 1024:
        return dict(rc=3, out="probe %s: failed: job faulted\n" % name,
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016"], latch=(4, 0x1000c016))
    if ("nopix" in world and held) or ("ctlnopix" in world and st == "control"):
        return dict(out="\n".join(out) + "\n")
    return dict(out="\n".join(out + rows_out(name, img)) + "\n")


def answer(tool, argv, world):
    """t10 answers the health pair (the kit's) and the probe fills."""
    if tool != "t10" or not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe" and "--tri" not in argv:
        return fill_probe(argv, world)
    return USAGE
