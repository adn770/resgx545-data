# SPDX-License-Identifier: MIT
"""mock/world.py: r16-usse's argv-driven fake laptop for kit/session.py mock (fill probes only).
answer() sees the tool's name, the argv and the world's tokens, never a case name: a fill probe's
program is named by its file in argv (the generator's program of that name). As strict as
sgxfive-test (resgx545 a581c06) on this form: an option `probe` does not take, a missing value,
--temps outside 1 to 124, more than one program, a file that is not there or that is not 1 to 256
USSE words (PROBE_MAX_WORDS) is refused (rc 2, usage, or the tool's own line).

A probe prints `probe NAME: o0 ...` and the scratch dwords its world's model changes (the frozen
predictions, predictions/STAGE.tsv), one `scratch +0xOFF 0xVALUE` line each as probe_scratch does
(a dword equal to its fill is not printed, at most 32).

Worlds:
  model     the controls their kept tables, the held-out rows H-ZX / H-ZX-ADV / H-RULE (and H-SIM's values):
            every stage 0
  alt       the rivals (uadd H-SX, utest H-SETAND / H-AJOIN, the a join lane rows H-CHAN0):
            every stage 0, those rows FAILED
  ctlnoread uadd's first control prints no scratch line: the premise stops the session (rc 25)
  uaddstop  two held-out uadd rows print no o0 line: uadd stops by its rule (rc 24) and the
            session goes on to utest (rc 0)
  unread    two held-out utest rows print no o0 line: utest stops by its rule (rc 24) and the
            session goes on to urpt (rc 0)
  rptstop   both write-mask rows print no o0 line: urpt stops by its rule (rc 24) and, as its
            on_stop = "end" says, the session ends there (rc 24)
  fault     the first held-out uadd row faults (a BIF fault latched): the session stops (rc 4)
  hang      the first held-out utest row never returns (timeout rc 124): the session stops (rc 6)
  rpthang   the first write-mask row never returns: the session stops at its last stage (rc 6)
"""
import os

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGES = ("uadd", "utest", "urpt")
EXPECT = {"model": (0, {"uadd": 0, "utest": 0, "urpt": 0}),
          "alt": (0, {"uadd": 0, "utest": 0, "urpt": 0}),
          "ctlnoread": (25, {"uadd": 25}),
          "uaddstop": (0, {"uadd": 24, "utest": 0, "urpt": 0}),
          "unread": (0, {"uadd": 0, "utest": 24, "urpt": 0}),
          "rptstop": (24, {"uadd": 0, "utest": 0, "urpt": 24}),
          "fault": (4, {"uadd": 4}),
          "hang": (6, {"uadd": 0, "utest": 6}),
          "rpthang": (6, {"uadd": 0, "utest": 0, "urpt": 6})}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
PROBE_VAL = {"--temps", "--scratch-pages"}
PROBE_FLAG = {"--stamp", "--coords", "--pixels"}
PICK = {"model": ("H-E521", "H-E498", "H-E499", "H-E529", "H-ZX", "H-ZX-ADV", "H-RULE", "H-SIM"),
        "alt": ("H-E521", "H-E498", "H-E499", "H-E529", "H-SX", "H-SETAND", "H-AJOIN", "H-CHAN0",
                "H-SIM")}


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
    """{row name: (stage, set)} from the session's tables, in file order."""
    out = {}
    for st in STAGES:
        for ln in open(os.path.join(KP, "tables", st + ".txt")):
            if ln.strip() and not ln.startswith("#"):
                name, s, _ = ln.split("|", 2)
                out[name] = (st, s)
    return out


def preds(stage, name):
    """{(quantity, model): {offset: value}} of a row."""
    out = {}
    for ln in open(os.path.join(KP, "predictions", stage + ".tsv")).read().splitlines()[1:]:
        f = ln.split("\t")
        if f[0] == name:
            out[(f[1], f[3])] = {int(k, 16): int(v, 16)
                                 for k, v in (p.split("=") for p in f[2].split(","))}
    return out


def dwords(stage, name, world):
    pick = PICK["alt" if "alt" in world else "model"]
    p = preds(stage, name)
    got = {}
    for q in sorted({q for q, _ in p}):
        m = next((m for m in pick if (q, m) in p), None)
        if m is None:
            raise SystemExit(f"world {world}: no model for {name} {q} ({sorted(p)})")
        got.update(p[(q, m)])
    return {k: v for k, v in got.items() if v != (0xD0000000 | k // 4)}


def held(stage, k):
    return [n for n, (st, s) in tables().items() if st == stage and s == "heldout"][k]


def fill_probe(argv, world):
    r = parse(argv, PROBE_VAL, PROBE_FLAG)
    if r is None or len(r[1]) != 1:
        return USAGE
    o, (path,) = r
    temps = int(o.get("--temps", ["32"])[0], 0)
    pages = int(o.get("--scratch-pages", ["16"])[0], 0)
    if not 1 <= temps <= 124 or not 16 <= pages <= 64:
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
    if "fault" in world and name == held("uadd", 0):
        return dict(rc=3, out="\n".join(out + ["probe %s: failed: job faulted" % name]) + "\n",
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016 stalls job 9"],
                    latch=(4, 0x1000c016))
    if ("hang" in world and name == held("utest", 0)) or (
            "rpthang" in world and name == held("urpt", 0)):
        return dict(rc=124, out="")
    d = dwords(stage, name, world)
    if ("ctlnoread" in world and name == "u-ctl-e521"):
        d = {}
    if ("uaddstop" in world and name in (held("uadd", 1), held("uadd", 3))) or (
            "unread" in world and name in (held("utest", 2), held("utest", 5))) or (
            "rptstop" in world and stage == "urpt" and st == "heldout"):
        return dict(out="\n".join(out) + "\n")
    out.append("probe %s: o0 0x%08x (2048 of 2048)" % (name, d.get(0, 0xD0000000)))
    shown = sorted(d)
    out += ["probe %s: scratch +0x%03x 0x%08x" % (name, k, d[k]) for k in shown[:32]]
    if len(shown) > 32:
        out.append("probe %s: scratch %d more changed" % (name, len(shown) - 32))
    return dict(out="\n".join(out) + "\n")


def answer(tool, argv, world):
    """t10 answers the health pair (the kit's) and the probe fills."""
    if tool != "t10" or not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe" and "--tri" not in argv:
        return fill_probe(argv, world)
    return USAGE
