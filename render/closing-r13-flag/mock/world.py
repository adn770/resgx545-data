# SPDX-License-Identifier: MIT
"""mock/world.py: r13-flag's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv, the world's tokens and the fake kernel's state ($FAKE_DIR: the debugfs
writes, so the resets), never a case name:

- f1 (t10p, `probe --temps 32 --coords --pixels PROG`): the program is named by its file (the
  generator's program of that name); an ok job prints the scratch line and the 32 rows of the
  world's model image (predictions/f1/NAME.MODEL.txt); a fault prints the tool's `failed: job
  faulted` line, the kernel's `BIF fault S at A` line and latches the fault (the next reset clears
  it); the fault address of H-TWX is the scratch + 0x40000 (+ 0x21).
- f2 (t10, `probe --tri pixel ... --sideband SB`): SB 0x1200 draws E383's mode 0 words; 0x0a0m
  faults 0x91000 at 0x37001003 (H-E383-PAGE) or draws (H-NOFAULT).
- f3 (t10): the VDM counter run on the fake kernel's state: c is 0 after any reset the runner
  wrote (debugfs reset, logged in $FAKE_DIR/writes) and after a hang; a job adds g(v) = v - 2 a
  block (g(1) = -1) and hangs iff c + add > 8 (E700's M1), a block-2 v = 1 job at c = 0 hangs
  (M3; the alt world: also at c = 5, H-C05). A hang prints the tool's `job hung` line and the
  kernel's `job N hung, recovering`; the bare `fill` and `tri` (the health pair, f3-fill-m and
  f3-rst-m) draw and add nothing (the alt world: a fill clears c, H-FILLCLR).

Worlds (EXPECT: the driver's status and each stage's runner status):
  model       F1 H-TWX (f1-tw32 faults at scratch + 0x40000, f1-small H-TWX's image), F2
              H-E383-PAGE, F3 M3 with M1's clauses: every stage 0
  alt         F1 H-TWIDX (no fault), F2 H-NOFAULT, F3 H-C05 and H-FILLCLR: every stage 0
  faultany    both f1 bit-14 rows fault: the second is the #limit's last row, f1 0
  ctlnopix    f1-ref-a prints no pixel rows: hook_check stops f1 (24), f2 and f3 run
  f1hang      f1-tw32 hangs instead of faulting: hook_fault stops f1 (24), f2 and f3 run
  recovfail   f1-tw32's fault logs `SGX recovery failed: -110`, the health still draws:
              hook_fault stops f1 (24), the gates of f2 and f3 are closed (skipped), driver 0
  unplanned   f2's control faults (no expectfault): the session stops (4)
  nobifline   f2-b11-m0 faults without the kernel's BIF line: hook_fault stops f2 (24)
  hang1st     the counter's threshold is 4: f3-c-a (no expectfault) hangs, the session stops (4)
  nocounter   no VDM job hangs: the control f3-c-b completes, hook_check stops f3 (24)
  nojobline   f3-c-b hangs without a `job:` line: no reading, the premise stops f3 (25)
  f3fault     the first block-2 v = 1 job faults instead of hanging: hook_fault stops f3 (24)
  recovfail3  the first block-2 v = 1 job's hang logs `SGX recovery failed: -110`: f3 stops (24)
  wedge       as recovfail3, and the first health draw after it fails (the retry draws):
              strict health stops the session (16)
"""
import os
import re

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECT = {
    "model": (0, {"f1": 0, "f2": 0, "f3": 0}),
    "alt": (0, {"f1": 0, "f2": 0, "f3": 0}),
    "faultany": (0, {"f1": 0, "f2": 0, "f3": 0}),
    "ctlnopix": (0, {"f1": 24, "f2": 0, "f3": 0}),
    "f1hang": (0, {"f1": 24, "f2": 0, "f3": 0}),
    "recovfail": (0, {"f1": 24}),
    "unplanned": (4, {"f1": 0, "f2": 4}),
    "nobifline": (0, {"f1": 0, "f2": 24, "f3": 0}),
    "hang1st": (4, {"f1": 0, "f2": 0, "f3": 4}),
    "nocounter": (0, {"f1": 0, "f2": 0, "f3": 24}),
    "nojobline": (25, {"f1": 0, "f2": 0, "f3": 25}),
    "f3fault": (0, {"f1": 0, "f2": 0, "f3": 24}),
    "recovfail3": (0, {"f1": 0, "f2": 0, "f3": 24}),
    "wedge": (16, {"f1": 0, "f2": 0, "f3": 16}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
SCRATCH = 0x3E003000
R110 = "SGX recovery failed: -110"
F1_FIRST = {"model": "H-TWX", "alt": "H-TWIDX"}


def state(name, default="0"):
    d = os.environ.get("FAKE_DIR")
    p = os.path.join(d, name) if d else None
    return open(p).read().strip() if p and os.path.exists(p) else default


def put(name, value):
    d = os.environ.get("FAKE_DIR")
    if d:
        with open(os.path.join(d, name), "w") as f:
            f.write(str(value))


def resets():
    d = os.environ.get("FAKE_DIR")
    p = os.path.join(d, "writes") if d else None
    return sum(1 for ln in open(p) if ln.startswith("reset ")) if p and os.path.exists(p) else 0


def image(name, model):
    p = os.path.join(KP, "predictions/f1", f"{name}.{model}.txt")
    if not os.path.exists(p):
        p = next(os.path.join(KP, "predictions/f1", f) for f in sorted(os.listdir(
            os.path.join(KP, "predictions/f1"))) if f.startswith(name + "."))
    return open(p).read().split()


def rows(prog, toks, w):
    return "".join(f"probe {prog}: row {y}: {' '.join(toks[y * w:(y + 1) * w])}\n"
                   for y in range(len(toks) // w))


def fault(prog, stat, addr, world):
    kmsg = [f"sgxfive: BIF fault {stat} at {addr:#010x} (PD 0x5736000) stalls job 7, recovering"]
    if "recovfail" in world:
        kmsg.append(R110)
    out = f"probe {prog}: scratch at {SCRATCH:#010x} (64 KiB)\n" \
          f"probe {prog}: failed: job faulted, context lost (Input/output error)\n"
    if "nobifline" in world:
        kmsg = []
    return dict(out=out, kmsg=kmsg, latch=(int(stat, 16) & 0xFFFF or 0x1000, addr))


def hang(out, world, rc):
    kmsg = ["sgxfive: job 12 hung, recovering"]
    if "recovfail3" in world or "wedge" in world:
        kmsg.append(R110)
    if "wedge" in world:
        put("r13f_wedge", 2)
    return dict(rc=rc, out=out, kmsg=kmsg)


def f1(argv, world):
    if argv[:5] != ["probe", "--temps", "32", "--coords", "--pixels"] or len(argv) != 6:
        return USAGE
    prog = os.path.basename(argv[5])[:-4]
    if not os.path.exists(argv[5]):
        return dict(rc=1, err=f"sgxfive-test: {argv[5]}: No such file or directory\n")
    head = f"probe {prog}: scratch at {SCRATCH:#010x} (64 KiB)\n"
    if prog == "f1-ref-a":
        return dict(out=head + ("" if "ctlnopix" in world else rows(prog, image(prog, "H-E566"), 64)))
    if prog == "f1-ref-b":
        return dict(out=head + rows(prog, image(prog, "H-E561"), 64))
    if prog == "f1-tw32" and "f1hang" in world:
        return hang(head + f"probe {prog}: failed: job hung, context lost (Connection timed out)\n",
                    world, 0)
    if prog == "f1-tw32" and ("faultany" in world or "alt" not in world):
        return fault(prog, "0x91000", SCRATCH + 0x40000 + 0x21, world - {"nobifline"})
    if prog == "f1-small" and "faultany" in world:
        return fault(prog, "0x91000", SCRATCH + 0x21, world - {"nobifline"})
    return dict(out=head + rows(prog, image(prog, F1_FIRST["alt" if "alt" in world else "model"]), 64))


def f2(argv, world):
    if len(argv) != 9 or argv[:5] != ["probe", "--tri", "pixel", "--pixels", "--slot"] or \
            not argv[5].startswith("eot=") or argv[6] != "--sideband":
        return USAGE
    sb = int(argv[7], 16)
    prog = os.path.basename(argv[8])[:-4]
    head = f"probe {prog}: scratch at 0x3e00e000 (64 KiB)\nprobe {prog}: tri 64x64 (sideband {sb:#010x}), eot pixel replaced\n"
    words = open(os.path.join(KP, "predictions/f2/words-m0.txt")).read().split()
    if sb == 0x1200 and "unplanned" in world:
        return fault(prog, "0x91000", 0x37001003, world)
    if sb & 0x0800 and "alt" not in world:
        return fault(prog, "0x91000", 0x37001003, world)
    return dict(out=head + rows(prog, [words[0]] * 4096, 64))


def vdm_blocks(argv):
    """(v1, v2) of a two-block probe or (v,) of a one-block tri, from the argv's xor words."""
    if argv[0] == "tri":
        v = 2
        for i, a in enumerate(argv):
            if a == "--poke":
                m = re.fullmatch(r"vdm:1\^=(0x[0-9a-f]+)", argv[i + 1])
                if not m:
                    return None
                v = 2 ^ (int(m.group(1), 16) >> 9 & 7)
        return (v,)
    v = {1: 2, 9: 2}
    for i, a in enumerate(argv):
        if a == "--vdm":
            m = re.fullmatch(r"([19])\^=(0x[0-9a-f]+)", argv[i + 1])
            if not m:
                return None
            v[int(m.group(1))] = 2 ^ (int(m.group(2), 16) >> 9 & 7)
    return (v[1], v[9])


def g(v):
    return -1 if v == 1 else 0 if v == 0 else v - 2


def f3(argv, world):
    blocks = vdm_blocks(argv)
    if blocks is None:
        return USAGE
    r = resets()
    seen, c = (int(x) for x in state("r13f_counter", "0 0").split())
    if r != seen:
        c = 0
    add = sum(g(v) for v in blocks)
    t = 4 if "hang1st" in world else 8
    hung = c + add > t and "nocounter" not in world
    v1blk2 = len(blocks) == 2 and blocks[1] == 1
    if v1blk2 and "nocounter" not in world and (c == 0 or ("alt" in world and c == 5)):
        hung = True
    first_v1 = v1blk2 and state("r13f_v1", "0") == "0"
    if v1blk2:
        put("r13f_v1", 1)
    put("r13f_counter", f"{r} {0 if hung else c + add}")
    if argv[0] == "tri":
        head = "tri: render context for targets up to 64x64\n"
        if hung:
            out = head if "nojobline" in world else \
                head + "job: failed: job hung, context lost (Connection timed out)\n"
            return hang(out, world if first_v1 or "hang1st" in world else set(), 1)
        return dict(out=head + "job: ok\ntarget: 64x64 hash 0x84752da507b30205\n"
                    "diff: 0 of 4096 pixels\ntri: 1 renders ok\n")
    prog = os.path.basename(argv[-1])[:-4]
    if hung and first_v1 and "f3fault" in world:
        return fault(prog, "0x91000", 0x3e0e0021, set())
    if hung:
        out = f"probe {prog}: failed: job hung, context lost (Connection timed out)\n"
        return hang(out, world if first_v1 else set(), 3)
    return dict(out=f"probe {prog}: tri 64x64 (12 vertices), pixel replaced\n"
                f"probe {prog}: o0 mixed 0xff0000ff x638 0xff00ff00 x1054\n")


def health(argv, world):
    """The bare fill and tri (the health pair, f3's fill and plain triangle): an exact draw,
    unless a wedged recovery left failing draws (the count is used up one by one); a fill clears
    the counter in the alt world (H-FILLCLR)."""
    if int(state("r13f_wedge", "0")) > 0:
        put("r13f_wedge", int(state("r13f_wedge")) - 1)
        return dict(rc=1, out="job: failed: job hung, context lost (Connection timed out)\n"
                    "diff: 4096 of 4096 pixels\n")
    if argv == ["fill"] and "alt" in world:
        put("r13f_counter", f"{resets()} 0")
    return None


def answer(tool, argv, world):
    """t10 and t10p are one binary (one path): the fake tool may get either name, so the form of
    the argv decides, as it does for the real tool."""
    if tool not in ("t10", "t10p"):
        return USAGE
    if argv in (["fill"], ["tri"]):
        return health(argv, world)
    if argv[:2] == ["probe", "--temps"] and "--tri" not in argv:
        return f1(argv, world)
    if argv[:2] == ["probe", "--tri"] and "--sideband" in argv:
        return f2(argv, world)
    if argv[:2] == ["probe", "--tri"] and "--obj2" in argv or argv[:1] == ["tri"]:
        return f3(argv, world)
    return USAGE
