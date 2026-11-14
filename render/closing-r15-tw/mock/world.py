# SPDX-License-Identifier: MIT
"""mock/world.py: r15-tw's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; it returns None (the health
pair) or dict(rc, out, err, files, kmsg, latch).

tw14 (t14, `probe --temps 32 --coords --pixels --scratch-pages 256 PROG`): t14 takes 16 to 256
scratch pages (257 is a usage refusal); the program is named by its file (the generator's program
of that name); an ok job prints the scratch line (pages x 4 KiB) and the 32 rows of the image of
the world's model (a control's frozen image always); a fault prints the tool's `failed: job
faulted` line, the kernel's `BIF fault S at A` line and latches the fault (the next reset clears
it); a hang the tool's timeout line. A token becomes a value as the tool would print it: `XXXXXXXX`
itself, `h:XXXX` 0xFFFFXXXX (the high half is not predicted), `t:B0,B1,B2,B3` the four bytes.
Health pair (bare `fill`, `tri`): an exact draw.

Worlds (EXPECT: the driver's status and the stage's runner status):
  model      point rows H-TWP, the u16 row U16-TX, the bilinear rows H-FOOT-TW: 0, 0
  alt        H-TWP4128, U16-T32, H-FOOT-SHIFT: 0, 0
  alt2       H-WRAPW, U16-DW, H-POINT: 0, 0
  ctlfault   tw-ref16 (the first row) faults: an unplanned fault stops the stage (4), and the
             session with it (4)
  rowfault   tw128-u2 (the last, farthest row) faults: 4, 4
  rowhang    tw16-u0 hangs: 4, 4
  nopix      tw-ref16 prints no pixel rows: hook_check stops tw14 (24), on_stop = end: driver 24
  short      tw-bl32 prints 31 pixel rows: hook_check 24, the session ends (24)
  small      tw64-u0 prints a 64 KiB scratch line (the option not taken): hook_check 24, ends (24)
"""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True

EXPECT = {
    "model": (0, {"tw14": 0}),
    "alt": (0, {"tw14": 0}),
    "alt2": (0, {"tw14": 0}),
    "ctlfault": (4, {"tw14": 4}),
    "rowfault": (4, {"tw14": 4}),
    "rowhang": (4, {"tw14": 4}),
    "nopix": (24, {"tw14": 24}),
    "short": (24, {"tw14": 24}),
    "small": (24, {"tw14": 24}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
SCRATCH = 0x3E003000
CTL = {"tw-ref16": "REF", "tw-ref64": "REF", "tw-ref128": "REF", "tw-refu16": "REF",
       "tw-zero": "H-E1047"}
WORLD_MODELS = {"model": ("H-TWP", "U16-TX", "H-FOOT-TW"),
                "alt": ("H-TWP4128", "U16-T32", "H-FOOT-SHIFT"),
                "alt2": ("H-WRAPW", "U16-DW", "H-POINT")}


def frozen(name, model):
    return open(os.path.join(KP, "predictions/tw14", f"{name}.{model}.txt")).read().split()


def value(tok):
    if tok.startswith("h:"):
        return 0xFFFF0000 | int(tok[2:], 16)
    if tok.startswith("t:"):
        b = [int(x) for x in tok[2:].split(",")]
        return b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24
    return int(tok, 16)


def model_of(prog, world):
    if prog in CTL:
        return CTL[prog]
    names = next((WORLD_MODELS[w] for w in ("alt", "alt2") if w in world), WORLD_MODELS["model"])
    have = set(os.listdir(os.path.join(KP, "predictions/tw14")))
    return next(m for m in names if f"{prog}.{m}.txt" in have)


def fault(head, hung=False):
    if hung:
        return dict(rc=3, out=head + "failed: job hung, context lost (Connection timed out)\n",
                    kmsg=["sgxfive: job 12 hung, recovering"], latch=None)
    addr = SCRATCH + 0x100000
    return dict(rc=3, out=head + "failed: job faulted, context lost (Input/output error)\n",
                kmsg=[f"sgxfive: BIF fault 0x90002 at {addr:#010x} (PD 0x5736000) stalls job 7, "
                      "recovering"], latch=(0x0002, addr))


def tw14(argv, world):
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
    kib = 64 if prog == "tw64-u0" and "small" in world else pages * 4
    head = f"probe {prog}: scratch at {SCRATCH:#010x} ({kib} KiB)\n"
    if (prog == "tw-ref16" and "ctlfault" in world) or (prog == "tw128-u2" and "rowfault" in world):
        return fault(head + f"probe {prog}: ")
    if prog == "tw16-u0" and "rowhang" in world:
        return fault(head + f"probe {prog}: ", hung=True)
    if prog == "tw-ref16" and "nopix" in world:
        return dict(out=head + f"probe {prog}: scratch unchanged\n")
    toks = frozen(prog, model_of(prog, world))
    n = 31 if prog == "tw-bl32" and "short" in world else 32
    rows = "".join(f"probe {prog}: row {y}: "
                   + " ".join("%08x" % value(t) for t in toks[y * 64:(y + 1) * 64]) + "\n"
                   for y in range(n))
    return dict(out=head + rows + f"probe {prog}: scratch unchanged\n")


def answer(tool, argv, world):
    if argv in (["fill"], ["tri"]):
        return None
    if tool == "t14" and argv[:1] == ["probe"]:
        return tw14(argv, world)
    return USAGE
