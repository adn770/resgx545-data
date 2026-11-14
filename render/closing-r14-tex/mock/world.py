# SPDX-License-Identifier: MIT
"""mock/world.py: r14-tex's argv-driven fake laptop for kit/session.py mock (r13-tex's world, fill
probes only). answer() sees the tool's name, the argv and the world's tokens, never a case name:
a fill probe's program is named by its file in argv (the generator's program of that name). As
strict as sgxfive-test (resgx545 a581c06) on this form: an option the command does not take, a
missing value, a --scratch-pages outside 16 to 64, more than one program or a file that is not
there is refused (rc 2, usage); a fill program whose reads pass the scratch the row maps faults
(a BIF fault latched).

The image a fill probe prints is a frozen prediction of the session (predictions/STAGE/
NAME.MODEL.txt, written by gen/make.py): `h:` and `u:` tokens print their half (srgb4's alpha rows
join B2-FTZ-OUT's low half and the world's alpha model's high half), `-` dword 0xD0000000; a type
row (addr5-tyN-u4) prints its reference's kept image (H-E567), plus 180 in the model world.

Worlds:
  model     srgb4 TRI-RNTU and A-LIN, addr5 C-LOG4 with the M regions and T-OFFSET, the controls
            their kept images: every stage 0
  alt       the rivals (srgb4 TRI-OUT and A-SRGB, addr5 CO-WH2 with the W regions and T-MODE0):
            every stage 0, the rows FAILED
  nopix     no held-out addr5 row prints pixel rows: the second stops addr5 by its rule (rc 24)
  ctlnopix  srgb4's first control prints no pixel rows: the premise stops the session (rc 25)
  fault     the first held-out addr5 row faults (a BIF fault latched): addr5 stops (rc 4)
  hang      the first held-out srgb4 row never returns (timeout rc 124): the session stops (rc 6)
"""
import os

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGES = ("srgb4", "addr5")
EXPECT = {"model": (0, {"srgb4": 0, "addr5": 0}),
          "alt": (0, {"srgb4": 0, "addr5": 0}),
          "nopix": (0, {"srgb4": 0, "addr5": 24}),
          "ctlnopix": (25, {"srgb4": 25}),
          "fault": (4, {"srgb4": 0, "addr5": 4}),
          "hang": (6, {"srgb4": 6})}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
PROBE_VAL = {"--temps", "--scratch-pages"}
PROBE_FLAG = {"--coords", "--pixels"}
FIRST = {"model": ("TRI-RNTU", "IN-M", "H-E723", "H-R13", "H-X1", "H-E1000", "H-E565",
                   "H-E567"),
         "alt": ("TRI-OUT", "IN-W", "H-E723", "H-R13", "H-X1", "H-E1000", "H-E565", "H-E567")}
ALPHA = {"model": "A-LIN", "alt": "A-SRGB"}
REGIONS = {"model": ("IN-M", "LR-M", "AB-M", "C-LOG4"), "alt": ("IN-W", "LR-W", "AB-W", "CO-WH2")}
TYPE_OFF = {"model": 180, "alt": 0}


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


def value(tok, fill=0xD0000000):
    if tok == "-":
        return fill
    if tok.startswith("h:"):
        return 0xBEEF0000 | int(tok[2:], 16)
    if tok.startswith("u:"):
        return int(tok[2:], 16) << 16 | 0xBEEF
    return int(tok, 16)


def image(stage, name, world):
    pick = "alt" if "alt" in world else "model"
    ms = models(stage, name)
    if name.startswith("addr5-ty") and name.endswith("-u4"):
        ref = [value(t) for t in toks(stage, name[:-1] + "0", "H-E567")]
        return [v + TYPE_OFF[pick] for v in ref]
    if "B2-FTZ-OUT" in ms:                           # an alpha row: byte 2 low, byte 3 high
        lo = toks(stage, name, "B2-FTZ-OUT")
        hi = toks(stage, name, ALPHA[pick])
        return [int(a[2:], 16) | int(b[2:], 16) << 16 for a, b in zip(lo, hi)]
    group = REGIONS[pick]
    if all(m in ms for m in group):                  # a uv5 row: its regions, one a model
        out = [0xD0000000] * 2048
        for m in group:
            for p, t in enumerate(toks(stage, name, m)):
                if t != "-":
                    out[p] = value(t)
        return out
    for m in FIRST[pick]:
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
    if "fault" in world and stage == "addr5" and name == first_held("addr5"):
        return dict(rc=3, out="probe %s: failed: job faulted\n" % name,
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016 stalls job 9"],
                    latch=(4, 0x1000c016))
    if "hang" in world and stage == "srgb4" and name == first_held("srgb4"):
        return dict(rc=124, out="")
    img = image(stage, name, world)
    top = max(((v & 0x0FFFFFFF) for v in img if v >> 28 == 0xD), default=0)
    if top >= pages * 1024:
        return dict(rc=3, out="probe %s: failed: job faulted\n" % name,
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016"], latch=(4, 0x1000c016))
    if ("nopix" in world and stage == "addr5" and held) or (
            "ctlnopix" in world and name == "srgb4-ctl"):
        return dict(out="\n".join(out) + "\n")
    return dict(out="\n".join(out + rows_out(name, img)) + "\n")


def answer(tool, argv, world):
    """t10 answers the health pair (the kit's) and the probe fills."""
    if tool != "t10" or not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe" and "--tri" not in argv:
        return fill_probe(argv, world)
    return USAGE
