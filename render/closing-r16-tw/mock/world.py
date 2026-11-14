# SPDX-License-Identifier: MIT
"""mock/world.py: r16-tw's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; it returns None (the health
pair) or dict(rc, out, err, files, kmsg, latch).

tw16 (t14, `probe --temps 32 --coords --pixels --scratch-pages 256 PROG`): t14 takes 16 to 256
scratch pages (257 is a usage refusal); the program is named by its file (the generator's program
of that name); an ok job prints the scratch line (pages x 4 KiB) and the 32 rows of the image of
the world's model on that row (a control's frozen image always); a fault prints the tool's `failed:
job faulted` line, the kernel's `BIF fault S at A` line and latches the fault (the next reset
clears it); a hang the tool's timeout line. A token becomes a value as the tool would print it:
`XXXXXXXX` itself, `t:B0,B1,B2,B3` the four bytes. Health pair (bare `fill`, `tri`): an exact draw.

Worlds (EXPECT: the driver's status and the stage's runner status):
  model     point rows H-TWP-H, bilinear rows F-FRAC: 0, 0
  alt       H-TWP-T16 (H 8), H-TWP-H (H 16), H-TWP-V32 (H 64); H-FOOT-SHIFT: 0, 0
  alt2      H-TWP-H (H 8, 16), H-TWP-STRIP (H 64); H-FOOT-TW: 0, 0
  alt3      H-MOVEH (H 8), H-TWP-H (H 16), H-TWP4128 (H 64); F-VNEXT: 0, 0
  alt4      H-TWP-H; H-POINT: 0, 0
  moveh     the H 16 rows read H-MOVEH (no sentinel): hook_check stops tw16 before the bilinear
            and H 64 rows (24), on_stop = end: driver 24
  ctlfault  ref32h8 (the first row) faults: an unplanned fault stops the stage (4), and the
            session with it (4)
  rowfault  pt64h64u1 (the last, farthest row) faults: 4, 4
  rowhang   bl64in hangs: 4, 4
  nopix     ref32h8 prints no pixel rows: hook_check stops tw16 (24), on_stop = end: driver 24
  short     bl128vedge prints 31 pixel rows: hook_check 24, the session ends (24)
  small     pt16h64u0 prints a 64 KiB scratch line (the option not taken): hook_check 24, ends
"""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True

EXPECT = {
    "model": (0, {"tw16": 0}),
    "alt": (0, {"tw16": 0}),
    "alt2": (0, {"tw16": 0}),
    "alt3": (0, {"tw16": 0}),
    "alt4": (0, {"tw16": 0}),
    "moveh": (24, {"tw16": 24}),
    "ctlfault": (4, {"tw16": 4}),
    "rowfault": (4, {"tw16": 4}),
    "rowhang": (4, {"tw16": 4}),
    "nopix": (24, {"tw16": 24}),
    "short": (24, {"tw16": 24}),
    "small": (24, {"tw16": 24}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
SCRATCH = 0x3E003000
CTL = {"ref32h8": "REF", "ref16h64": "REF", "bl32r": "H-E1049"}
H = {"pt32h8": 8, "pt128h8": 8, "pt32h16": 16, "pt128h16": 16, "pt16h64u0": 64,
     "pt16h64u1": 64, "pt64h64u0": 64, "pt64h64u1": 64}
# world: ({H: point model}, bilinear model)
WORLD_MODELS = {
    "model": ({8: "H-TWP-H", 16: "H-TWP-H", 64: "H-TWP-H"}, "F-FRAC"),
    "alt": ({8: "H-TWP-T16", 16: "H-TWP-H", 64: "H-TWP-V32"}, "H-FOOT-SHIFT"),
    "alt2": ({8: "H-TWP-H", 16: "H-TWP-H", 64: "H-TWP-STRIP"}, "H-FOOT-TW"),
    "alt3": ({8: "H-MOVEH", 16: "H-TWP-H", 64: "H-TWP4128"}, "F-VNEXT"),
    "alt4": ({8: "H-TWP-H", 16: "H-TWP-H", 64: "H-TWP-H"}, "H-POINT"),
    "moveh": ({8: "H-TWP-H", 16: "H-MOVEH", 64: "H-TWP-H"}, "F-FRAC"),
}


def frozen(name, model):
    return open(os.path.join(KP, "predictions/tw16", f"{name}.{model}.txt")).read().split()


def value(tok):
    if tok.startswith("t:"):
        b = [int(x) for x in tok[2:].split(",")]
        return b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24
    return int(tok, 16)


def model_of(prog, world):
    if prog in CTL:
        return CTL[prog]
    w = next((k for k in WORLD_MODELS if k in world), "model")
    point, bil = WORLD_MODELS[w]
    return point[H[prog]] if prog in H else bil


def fault(head, hung=False):
    if hung:
        return dict(rc=3, out=head + "failed: job hung, context lost (Connection timed out)\n",
                    kmsg=["sgxfive: job 12 hung, recovering"], latch=None)
    addr = SCRATCH + 0x100000
    return dict(rc=3, out=head + "failed: job faulted, context lost (Input/output error)\n",
                kmsg=[f"sgxfive: BIF fault 0x90002 at {addr:#010x} (PD 0x5736000) stalls job 7, "
                      "recovering"], latch=(0x0002, addr))


def tw16(argv, world):
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
    kib = 64 if prog == "pt16h64u0" and "small" in world else pages * 4
    head = f"probe {prog}: scratch at {SCRATCH:#010x} ({kib} KiB)\n"
    if (prog == "ref32h8" and "ctlfault" in world) or (prog == "pt64h64u1" and "rowfault" in world):
        return fault(head + f"probe {prog}: ")
    if prog == "bl64in" and "rowhang" in world:
        return fault(head + f"probe {prog}: ", hung=True)
    if prog == "ref32h8" and "nopix" in world:
        return dict(out=head + f"probe {prog}: scratch unchanged\n")
    toks = frozen(prog, model_of(prog, world))
    n = 31 if prog == "bl128vedge" and "short" in world else 32
    rows = "".join(f"probe {prog}: row {y}: "
                   + " ".join("%08x" % value(t) for t in toks[y * 64:(y + 1) * 64]) + "\n"
                   for y in range(n))
    return dict(out=head + rows + f"probe {prog}: scratch unchanged\n")


def answer(tool, argv, world):
    if argv in (["fill"], ["tri"]):
        return None
    if tool == "t14" and argv[:1] == ["probe"]:
        return tw16(argv, world)
    return USAGE
