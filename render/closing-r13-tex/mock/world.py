# SPDX-License-Identifier: MIT
"""mock/world.py: r13-tex's argv-driven fake laptop for kit/session.py mock (r10-tex's world, with
r10-x's `probe --tri` rows). answer() sees the tool's name, the argv and the world's tokens, never
a case name: a fill probe's program is named by its file in argv (the generator's program of that
name); an sb12 row by its sideband, its colour program (sb-c0.bin or sb-c1.bin) and --tri-v. As
strict as sgxfive-test (resgx545 a581c06) on these forms: an option the command does not take, a
missing value, a --scratch-pages outside 16 to 64, a --sideband without an eot slot, more than one
program or a file that is not there is refused (rc 2, usage); a fill program whose reads pass the
scratch the row maps faults (a BIF fault latched).

The image a fill probe prints is a frozen prediction of the session (predictions/STAGE/
NAME.MODEL.txt, written by gen/make.py): `h:` tokens print the half, `t:` tokens their bytes, `-`
dword 0xD0000000. An sb12 row prints E383's words of its mode (predictions/sb12/words-mN.txt), or
E383's mode 0 image where a pixel model is frozen; the alt world's colour 1 rows print words of no
set (the colour), its moved row H-SHIFT's image.

Worlds:
  model     srgb3 FTZ-OUT / TRI-OUT, addr4 H-MAX and the uv5 M models with CO-WH2, t3c B11-LEVEL0
            / B12-CAPLVL / AS-00 / H-FOOT, sb12 H-FIXED, the controls their kept images: every
            stage 0
  alt       the rivals (srgb3 FTZ-IN / TRI-LO, addr4 H-W / CO-12M4, t3c B11-NORMAL /
            B12-CHAINLAST / AS-01 / H-TAP, sb12 H-O0 and H-SHIFT): every stage 0, rows FAILED
  nopix     no t3c row but the control prints pixel rows: the second stops t3c by its rule (rc 24),
            the driver goes on and sb12 runs
  ctlnopix  srgb3's first control prints no pixel rows: the premise stops the session (rc 25)
  fault     the first held-out addr4 row faults (a BIF fault latched): addr4 stops (rc 4)
  hang      the first held-out sb12 row never returns (timeout rc 124): sb12 stops (rc 6)
"""
import os

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGES = ("srgb3", "addr4", "t3c", "sb12")
EXPECT = {"model": (0, {"srgb3": 0, "addr4": 0, "t3c": 0, "sb12": 0}),
          "alt": (0, {"srgb3": 0, "addr4": 0, "t3c": 0, "sb12": 0}),
          "nopix": (0, {"srgb3": 0, "addr4": 0, "t3c": 24, "sb12": 0}),
          "ctlnopix": (25, {"srgb3": 25}),
          "fault": (4, {"srgb3": 0, "addr4": 4}),
          "hang": (6, {"srgb3": 0, "addr4": 0, "t3c": 0, "sb12": 6})}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
PROBE_VAL = {"--temps", "--scratch-pages"}
PROBE_FLAG = {"--coords", "--pixels"}
TRI_VAL = {"--tri", "--slot", "--sideband", "--tri-v"}
TRI_FLAG = {"--pixels"}
FIRST = {"model": ("FTZ-OUT", "TRI-OUT", "H-MAX", "H-MAX-TX", "IN-M", "LR-M", "AB-M", "CO-WH2",
                   "B11-LEVEL0", "B12-CAPLVL", "AS-00", "H-FOOT", "H-BILIN",
                   "H-E723", "H-KEPT", "H-E1000", "H-E565", "H-E564", "H-E383", "H-FIXED-PX"),
         "alt": ("FTZ-IN", "TRI-LO", "H-W", "H-W-TX", "IN-W", "LR-W", "AB-W", "CO-12M4",
                 "B11-NORMAL", "B12-CHAINLAST", "AS-01", "H-TAP", "H-BILIN",
                 "H-E723", "H-KEPT", "H-E1000", "H-E565", "H-E564", "H-E383", "H-SHIFT")}
REGIONS = (("IN-M", "LR-M", "AB-M", "CO-WH2"), ("IN-W", "LR-W", "AB-W", "CO-12M4"))


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
    if tok.startswith("t:"):
        return sum(int(b) << 8 * i for i, b in enumerate(tok[2:].split(",")))
    return int(tok, 16)


def image(stage, name, world):
    ms = models(stage, name)
    pick = "alt" if "alt" in world else "model"
    group = REGIONS[pick == "alt"]
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
    held = st != "control"
    if "fault" in world and stage == "addr4" and name == first_held("addr4"):
        return dict(rc=3, out="probe %s: failed: job faulted\n" % name,
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016 stalls job 9"],
                    latch=(4, 0x1000c016))
    img = image(stage, name, world)
    top = max(((v & 0x0FFFFFFF) for v in img if v >> 28 == 0xD), default=0)
    if top >= pages * 1024:
        return dict(rc=3, out="probe %s: failed: job faulted\n" % name,
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016"], latch=(4, 0x1000c016))
    if ("nopix" in world and stage == "t3c" and held) or (
            "ctlnopix" in world and stage == "srgb3" and name == "srgb3-ctl"):
        return dict(out="\n".join(out) + "\n")
    return dict(out="\n".join(out + rows_out(name, img)) + "\n")


def words(mode):
    with open(os.path.join(KP, "predictions", "sb12", f"words-m{mode}.txt")) as f:
        return [int(t, 16) for t in f.read().split()]


def tri_probe(argv, world):
    r = parse(argv, TRI_VAL, TRI_FLAG)
    if r is None or len(r[1]) != 1 or "--pixels" not in r[0] or o_get(r[0], "--tri") != "pixel":
        return USAGE
    o, (path,) = r
    slots = dict(s.split("=", 1) for s in o.get("--slot", []) if "=" in s)
    if set(slots) != {"eot"} or "--sideband" not in o:
        return USAGE
    for f in (path, slots["eot"]):
        if not os.path.isfile(f):
            return dict(rc=2, err="sgxfive-test: %s: No such file or directory\n" % f)
    sb = int(o["--sideband"][0], 0)
    tv = o.get("--tri-v", [None])[0]
    if tv is not None and len(tv.split(",")) != 6:
        return USAGE
    colour = {"sb-c0.bin": 0, "sb-c1.bin": 1}.get(os.path.basename(path))
    if colour is None:
        return USAGE
    # the row this argv is (the table's own args, the names of the sb12 rows)
    case = os.path.basename(path)[:-4]
    hit = [n for n, (st, s, a) in tables().items() if st == "sb12" and
           f"--sideband {sb:#x}" in a and f"sb-c{colour}.bin" in a and
           (("--tri-v" in a) == (tv is not None))]
    if len(hit) != 1:
        return USAGE
    name = hit[0]
    if "hang" in world and name == first_held("sb12"):
        return dict(rc=124, out="")
    out = ["programs asm", "probe %s: tri 64x64 (sideband 0x%08x), eot pixel replaced" % (case, sb)]
    ms = models("sb12", name)
    if sb == 0x208:
        img = [value(t) for t in toks("sb12", name, "H-E383")]
    elif "alt" in world and colour == 1:
        img = [0x13579BDF] * 4096
    elif "alt" in world and "H-SHIFT" in ms:
        img = [value(t, words(0)[0]) for t in toks("sb12", name, "H-SHIFT")]
    elif "H-FIXED-PX" in ms:
        img = [value(t) for t in toks("sb12", name, "H-FIXED-PX")]
    else:
        w = words(sb & 0xF)
        img = [w[p % len(w)] for p in range(4096)]
    return dict(out="\n".join(out + rows_out(case, img)) + "\n")


def o_get(o, k):
    v = o.get(k)
    return v[0] if v else None


def answer(tool, argv, world):
    """t10 and t10p are one binary (one file on the laptop, so the fake laptop cannot tell the
    names apart): either answers the health pair, the probe fills and sb12's `probe --tri`."""
    if tool not in ("t10", "t10p") or not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe":
        return tri_probe(argv, world) if "--tri" in argv else fill_probe(argv, world)
    return USAGE
