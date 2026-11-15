# SPDX-License-Identifier: MIT
"""mock/world.py: r26-sa0's fake laptop for kit/session.py mock. answer() sees the tool's name, the
argv and the world's tokens, never a case name; it returns None (the health pair) or dict(rc, out,
err, kmsg, latch). A probe's NAME is its FILE's base name as the tool prints it, and what its
world prints is read from the frozen predictions of that name (predictions/STAGE.tsv).

As strict as t24 (resgx545 1341034) on this session's rows: `probe` with --coords, --pixels,
--stamp, --temps N (1 to 124), --scratch-pages N (16 to 64), --scratch-show N (1 to 64), one FILE
that is there and is 1 to 256 USSE words; anything else is refused (rc 2). It prints the scratch
dwords the world's model changes (a dword equal to its fill is not printed, at most 32).

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  zx        every row reads H-ZX (the controls their values): all run (0)
  sx        the held-out rows read H-SX: all run (0), the rows FAILED in the scorer
  mix       the held-out rows read E1061's mixture (dwords 4 and 5 the values of pairs 6 and 7):
            all run (0)
  ctlfail   c-one-r10 reads H-SX: uc runs (0) and its gate shuts us (None)
  ctlnoread c-e521 prints no scratch line: the premise stops the session (25)
  nobranch  no writer quad (the held-out rows print no scratch line): us stops by its rule (24)
  fault     the first held-out row faults (a BIF fault latched): the session stops (4)
  hang      the first held-out row never returns (rc 124): the session stops (6)
"""
import os

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGES = ("uc", "us")
EXPECT = {"zx": (0, {"uc": 0, "us": 0}),
          "sx": (0, {"uc": 0, "us": 0}),
          "mix": (0, {"uc": 0, "us": 0}),
          "ctlfail": (0, {"uc": 0, "us": None}),
          "ctlnoread": (25, {"uc": 25}),
          "nobranch": (0, {"uc": 0, "us": 24}),
          "fault": (4, {"uc": 0, "us": 4}),
          "hang": (6, {"uc": 0, "us": 6})}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
VAL = {"--temps", "--scratch-pages", "--scratch-show"}
FLAG = {"--stamp", "--coords", "--pixels"}


def parse(argv):
    o, pos, i = {}, [], 1
    while i < len(argv):
        a = argv[i]
        if a in FLAG:
            o.setdefault(a, []).append(True)
            i += 1
        elif a in VAL and i + 1 < len(argv):
            o.setdefault(a, []).append(argv[i + 1])
            i += 2
        elif a.startswith("--"):
            return None
        else:
            pos.append(a)
            i += 1
    return o, pos


def tables():
    """{row name: (stage, set)} in file order."""
    out = {}
    for st in STAGES:
        for ln in open(os.path.join(KP, "tables", st + ".txt")):
            if ln.strip() and not ln.startswith("#"):
                name, s, _ = ln.split("|", 2)
                out[name] = (st, s)
    return out


def preds(stage, name):
    """{(quantity, model): {offset: value}} of a row (the mix set is by position)."""
    out = {}
    for ln in open(os.path.join(KP, "predictions", stage + ".tsv")).read().splitlines()[1:]:
        f = ln.split("\t")
        if f[0] != name:
            continue
        if f[1] == "mix":
            out[(f[1], f[3])] = {4 * k: int(v, 16) for k, v in enumerate(f[2].split(","))}
        else:
            out[(f[1], f[3])] = {int(k, 16): int(v, 16)
                                 for k, v in (p.split("=") for p in f[2].split(","))}
    return out


def dwords(stage, name, world):
    p = preds(stage, name)
    if "H-E521" in {m for _, m in p}:
        return dict(p[("dwords", "H-E521")])
    sx = ("sx" in world and name.startswith("s-")) or ("ctlfail" in world and name == "c-one-r10")
    d = dict(p[("dwords", "H-SX" if sx else "H-ZX")])
    if "mix" in world and p.get(("mix", "H-MIX")) and name.startswith("s-"):
        d[0x10], d[0x14] = d[0x18], d[0x1c]          # E1061: dwords 4, 5 read pairs 6, 7
    return d


def held(k):
    return [n for n, (st, s) in tables().items() if st == "us"][k]


def fill_probe(argv, world):
    r = parse(argv)
    if r is None or len(r[1]) != 1:
        return USAGE
    o, (path,) = r
    temps = int(o.get("--temps", ["32"])[0], 0)
    pages = int(o.get("--scratch-pages", ["16"])[0], 0)
    show = o.get("--scratch-show", ["32"])[0]
    if not 1 <= temps <= 124 or not 16 <= pages <= 64 or not show.isdigit() \
            or not 1 <= int(show) <= 64:
        return USAGE
    if not os.path.isfile(path):
        return dict(rc=2, err="sgxfive-test: %s: No such file or directory\n" % path)
    size = os.path.getsize(path)
    if not size or size % 8 or size > 256 * 8:
        return dict(rc=2, err="sgxfive-test: %s: not 1 to 256 USSE words\n" % path)
    name = os.path.basename(path).split(".")[0]
    rows = tables()
    if name not in rows:
        return USAGE
    stage, st = rows[name]
    out = ["programs asm", "probe %s: scratch at 0x3e003000 (%d KiB)" % (name, 4 * pages),
           "probe %s: job time: 812 us" % name]
    if "fault" in world and name == held(0):
        return dict(rc=3, out="\n".join(out + ["probe %s: failed: job faulted" % name]) + "\n",
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016 stalls job 9"],
                    latch=(4, 0x1000c016))
    if "hang" in world and name == held(0):
        return dict(rc=124, out="")
    d = dwords(stage, name, world)
    if ("ctlnoread" in world and name == "c-e521") or ("nobranch" in world and st == "heldout"):
        d = {}
    out.append("probe %s: o0 0xc0de0001 (2048 of 2048)" % name)
    shown = sorted(d)
    out += ["probe %s: scratch +0x%03x 0x%08x" % (name, k, d[k]) for k in shown[:int(show)]]
    if len(shown) > int(show):
        out.append("probe %s: scratch %d more changed" % (name, len(shown) - int(show)))
    return dict(out="\n".join(out) + "\n")


def answer(tool, argv, world):
    """t24 answers the probe fills; the health pair (t10) is the kit's."""
    if tool != "t24" or not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe" and "--tri" not in argv:
        return fill_probe(argv, world)
    return USAGE
