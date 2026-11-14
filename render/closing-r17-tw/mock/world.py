# SPDX-License-Identifier: MIT
"""mock/world.py: r17-tw's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; it returns None (the health
pair) or dict(rc, out, err, files, kmsg, latch).

tw17 (t14, `probe --temps 32 --coords --pixels --scratch-pages 256 PROG`): t14 takes 16 to 256
scratch pages (257 is a usage refusal); the program is named by its file (the generator's program
of that name); an ok job prints the scratch line (pages x 4 KiB) and the 32 rows of the image of
the world's model on that row (a control's frozen image always, but in world reflaw); a fault
prints the tool's `failed: job faulted` line, the kernel's `BIF fault S at A` line and latches the
fault (the next reset clears it); a hang the tool's timeout line. A token becomes a value as the
tool would print it: `XXXXXXXX` itself, `t:B0,B1,B2,B3` the four bytes. Health pair (bare `fill`,
`tri`): an exact draw.

Worlds (EXPECT: the driver's status and the stage's runner status):
  model     point rows H-WIDE-PT, bilinear rows H-WIDE: 0, 0
  wideg     H-WIDE-PT; H-WIDE-G (the left wrap at W - 1): 0, 0
  next      H-WIDE-PT; H-WIDE-NEXT (the right wrap to the next tile row): 0, 0
  unwrap    H-TWP; UNWRAP-G (E1058's post hoc reading): 0, 0
  ffrac     H-TWP; F-FRAC: 0, 0
  point     H-WIDE-PT; H-POINT: 0, 0
  reflaw    ref256 prints H-WIDE-PT's image of its coordinates (not E561's law, no sentinel):
            hook_check stops tw17 before the W 256 rows (24), on_stop = end: driver 24
  ctlfault  bl64leftr (the first row) faults: an unplanned fault stops the stage (4), and the
            session with it (4)
  rowfault  bl2048edge (the last, widest row) faults: 4, 4
  rowhang   bl128off3 hangs: 4, 4
  nopix     bl64leftr prints no pixel rows: hook_check stops tw17 (24), on_stop = end: driver 24
  short     bl512edge prints 31 pixel rows: hook_check 24, the session ends (24)
  small     bl256edge prints a 64 KiB scratch line (the option not taken): hook_check 24, ends
"""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True

EXPECT = {
    "model": (0, {"tw17": 0}),
    "wideg": (0, {"tw17": 0}),
    "next": (0, {"tw17": 0}),
    "unwrap": (0, {"tw17": 0}),
    "ffrac": (0, {"tw17": 0}),
    "point": (0, {"tw17": 0}),
    "reflaw": (24, {"tw17": 24}),
    "ctlfault": (4, {"tw17": 4}),
    "rowfault": (4, {"tw17": 4}),
    "rowhang": (4, {"tw17": 4}),
    "nopix": (24, {"tw17": 24}),
    "short": (24, {"tw17": 24}),
    "small": (24, {"tw17": 24}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
SCRATCH = 0x3E003000
CTL = {"bl64leftr": "H-E1058", "ref256": "REF", "ref512h16": "REF", "ref2048h16": "REF"}
POINT_ROWS = ("pt128off", "pt256off", "pt512off")
# world: (point model, bilinear model)
WORLD_MODELS = {
    "model": ("H-WIDE-PT", "H-WIDE"),
    "wideg": ("H-WIDE-PT", "H-WIDE-G"),
    "next": ("H-WIDE-PT", "H-WIDE-NEXT"),
    "unwrap": ("H-TWP", "UNWRAP-G"),
    "ffrac": ("H-TWP", "F-FRAC"),
    "point": ("H-WIDE-PT", "H-POINT"),
}


def frozen(name, model):
    return open(os.path.join(KP, "predictions/tw17", f"{name}.{model}.txt")).read().split()


def value(tok):
    if tok.startswith("t:"):
        b = [int(x) for x in tok[2:].split(",")]
        return b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24
    return int(tok, 16)


def image(prog, world):
    """The tokens the world's hardware prints for a program."""
    if prog == "ref256" and "reflaw" in world:
        # the bit-14 point form's names for the reference's coordinates: not E561's law
        return ["%08x" % (value(t) + 0x10000) for t in frozen(prog, "REF")]
    if prog in CTL:
        return frozen(prog, CTL[prog])
    w = next((k for k in WORLD_MODELS if k in world), "model")
    point, bil = WORLD_MODELS[w]
    return frozen(prog, point if prog in POINT_ROWS else bil)


def fault(head, hung=False):
    if hung:
        return dict(rc=3, out=head + "failed: job hung, context lost (Connection timed out)\n",
                    kmsg=["sgxfive: job 12 hung, recovering"], latch=None)
    addr = SCRATCH + 0x100000
    return dict(rc=3, out=head + "failed: job faulted, context lost (Input/output error)\n",
                kmsg=[f"sgxfive: BIF fault 0x90002 at {addr:#010x} (PD 0x5736000) stalls job 7, "
                      "recovering"], latch=(0x0002, addr))


def tw17(argv, world):
    if argv[:5] != ["probe", "--temps", "32", "--coords", "--pixels"] or len(argv) != 8 or \
            argv[5] != "--scratch-pages":
        return USAGE
    try:
        pages = int(argv[6])
    except ValueError:
        return USAGE
    if not 16 <= pages <= 256:
        return USAGE
    if not os.path.exists(argv[7]):
        return dict(rc=1, err=f"sgxfive-test: {argv[7]}: No such file or directory\n")
    prog = os.path.basename(argv[7])[:-4]
    kib = 64 if prog == "bl256edge" and "small" in world else pages * 4
    head = f"probe {prog}: scratch at {SCRATCH:#010x} ({kib} KiB)\n"
    if (prog == "bl64leftr" and "ctlfault" in world) or \
            (prog == "bl2048edge" and "rowfault" in world):
        return fault(head + f"probe {prog}: ")
    if prog == "bl128off3" and "rowhang" in world:
        return fault(head + f"probe {prog}: ", hung=True)
    if prog == "bl64leftr" and "nopix" in world:
        return dict(out=head + f"probe {prog}: scratch unchanged\n")
    toks = image(prog, world)
    n = 31 if prog == "bl512edge" and "short" in world else 32
    rows = "".join(f"probe {prog}: row {y}: "
                   + " ".join("%08x" % value(t) for t in toks[y * 64:(y + 1) * 64]) + "\n"
                   for y in range(n))
    return dict(out=head + rows + f"probe {prog}: scratch unchanged\n")


def answer(tool, argv, world):
    if argv in (["fill"], ["tri"]):
        return None
    if tool == "t14" and argv[:1] == ["probe"]:
        return tw17(argv, world)
    return USAGE
