# SPDX-License-Identifier: MIT
"""mock/world.py: r15-tex's argv-driven fake laptop for kit/session.py mock (r14-tex's world, fill
probes only). answer() sees the tool's name, the argv and the world's tokens, never a case name:
a fill probe's program is named by its file in argv (the generator's program of that name). As
strict as sgxfive-test (resgx545 a581c06) on this form: an option the command does not take, a
missing value, a --scratch-pages outside 16 to 64, more than one program or a file that is not
there is refused (rc 2, usage); a fill program whose named reads pass the scratch the row maps
faults (a BIF fault latched).

The image a fill probe prints is a frozen prediction of the session (predictions/STAGE/
NAME.MODEL.txt, written by gen/make.py): `h:` tokens print their half as the dword (a u16 read),
`-` dword 0xD0000000; a ty 32 x 32 mode 4 row prints names c + U halved (c 2000, U = 32 + x mod
32: H-HALF and H-LIN1) in the model world and its reference's image in the alt world (H-MODE0).

Worlds:
  model     chain A (A-TX, A-TX-BL8), ty H-AS-U4, NAME-U, R-W / R-2W and H-LIN1, the controls their
            kept images: every stage 0
  alt       the rivals (chain B, B-TX, B-TX-BL8; ty H-MODE0, NAME-WRAP, R-16 / R-32): every stage
            0, the rows FAILED
  nopix     no held-out ty row prints pixel rows: the second stops ty by its rule (rc 24)
  ctlnopix  chain's first control prints no pixel rows: the premise stops the session (rc 25)
  fault     the first held-out chain row faults (a BIF fault latched): the session stops (rc 4)
  hang      the first held-out ty row never returns (timeout rc 124): the session stops (rc 6)
"""
import os

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGES = ("chain", "ty")
EXPECT = {"model": (0, {"chain": 0, "ty": 0}),
          "alt": (0, {"chain": 0, "ty": 0}),
          "nopix": (0, {"chain": 0, "ty": 24}),
          "ctlnopix": (25, {"chain": 25}),
          "fault": (4, {"chain": 4}),
          "hang": (6, {"chain": 0, "ty": 6})}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
PROBE_VAL = {"--temps", "--scratch-pages"}
PROBE_FLAG = {"--coords", "--pixels"}
PICK = {"model": ("H-E562", "H-E1000", "H-E1039", "A", "A-TX", "A-TX-BL8", "H-AS-U4", "NAME-U",
                  "R-W", "R-2W"),
        "alt": ("H-E562", "H-E1000", "H-E1039", "B", "B-TX", "B-TX-BL8", "H-MODE0", "NAME-WRAP",
                "R-16", "R-32")}


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
    d = os.path.join(KP, "predictions", stage)
    return sorted(f[len(name) + 1:-4] for f in os.listdir(d)
                  if f.startswith(name + ".") and f[len(name) + 1:-4].count(".") == 0)


def toks(stage, name, model):
    return open(os.path.join(KP, "predictions", stage, f"{name}.{model}.txt")).read().split()


def value(tok):
    if tok == "-":
        return 0xD0000000
    if tok.startswith("h:"):
        return int(tok[2:], 16)
    return int(tok, 16)


def half(d):
    return sum(((d >> 8 * i & 255) + 1) >> 1 << 8 * i for i in range(4))


def image(stage, name, world):
    pick = "alt" if "alt" in world else "model"
    if name.startswith("ty-32-") and name.endswith("-u4"):
        if pick == "alt":
            return image(stage, name[:-1] + "0", world)
        return [half(0xD0000000 | (2000 + 32 + x % 32)) for y in range(32) for x in range(64)]
    ms = models(stage, name)
    for m in PICK[pick]:
        if m in ms:
            return [value(t) for t in toks(stage, name, m)]
    raise SystemExit(f"world {world}: no model for {name} ({ms})")


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
    if "fault" in world and stage == "chain" and name == first_held("chain"):
        return dict(rc=3, out="probe %s: failed: job faulted\n" % name,
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016 stalls job 9"],
                    latch=(4, 0x1000c016))
    if "hang" in world and stage == "ty" and name == first_held("ty"):
        return dict(rc=124, out="")
    img = image(stage, name, world)
    top = max(((v & 0x0FFFFFFF) for v in img if v >> 28 == 0xD), default=0)
    if top >= pages * 1024:
        return dict(rc=3, out="probe %s: failed: job faulted\n" % name,
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016"], latch=(4, 0x1000c016))
    if ("nopix" in world and stage == "ty" and held) or (
            "ctlnopix" in world and name == "chain-ctl32"):
        return dict(out="\n".join(out) + "\n")
    return dict(out="\n".join(out + rows_out(name, img)) + "\n")


def answer(tool, argv, world):
    """t10 answers the health pair (the kit's) and the probe fills."""
    if tool != "t10" or not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe" and "--tri" not in argv:
        return fill_probe(argv, world)
    return USAGE
